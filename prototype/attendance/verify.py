"""Signature comparison - the 'Recognition' extension of the brief.

The brief asks the system to *collect the signatures of a given student, compare
them, and report if they are not matching*.  That is a writer-dependent
verification problem with no negative training data: for each student we hold a
handful of genuine specimens and nothing else, so a trained classifier is not an
option.  The approach used here is therefore a classical, unsupervised one.

Each specimen is

1.  segmented from its cell and cropped to the ink,
2.  normalised for size, aspect ratio and stroke thickness,
3.  described by a *histogram of oriented gradients* (a global shape descriptor)
    and by *ORB* key points (a local, rotation-invariant descriptor),
4.  compared with every other specimen of the same student.

The two similarities are blended, and a specimen whose mean similarity to its
peers falls below an absolute threshold - or well below the cohort average - is
reported as a possible mismatch (a proxy signature).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Sequence

import cv2
import numpy as np

from .config import Settings


class HistogramOfOrientedGradients:
    """A self-contained HOG descriptor (Dalal & Triggs, 2005).

    OpenCV's own ``HOGDescriptor`` was withdrawn from the Python bindings in
    OpenCV 5, and implementing the descriptor directly also makes every step of
    it inspectable, which suits a coursework prototype:

    1.  gradients ``gx``, ``gy`` from a 1-D central-difference kernel;
    2.  magnitude ``m = sqrt(gx^2 + gy^2)`` and *unsigned* orientation
        ``theta = atan2(gy, gx) mod 180`` - unsigned, because a pen stroke and
        its reverse are the same shape;
    3.  each pixel votes its magnitude into the two nearest of ``bins``
        orientation bins of its ``cell x cell`` cell, weighted linearly by how
        close the angle is to each bin centre;
    4.  cells are grouped into overlapping ``block x block`` blocks which are
        L2-Hys normalised (L2 normalise, clip at 0.2, L2 normalise again) to
        cancel local contrast differences between pens;
    5.  the normalised blocks are concatenated into the feature vector.
    """

    def __init__(self, cell: int = 8, bins: int = 9, block: int = 2, clip: float = 0.2) -> None:
        self.cell = cell
        self.bins = bins
        self.block = block
        self.clip = clip
        self._epsilon = 1e-6

    def compute(self, image: np.ndarray) -> np.ndarray:
        gray = image.astype(np.float32) / 255.0
        gradient_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gradient_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        magnitude, angle = cv2.cartToPolar(gradient_x, gradient_y, angleInDegrees=True)
        angle = np.mod(angle, 180.0)

        height, width = gray.shape
        rows, columns = height // self.cell, width // self.cell
        if rows < self.block or columns < self.block:
            return np.zeros(1, np.float32)

        bin_width = 180.0 / self.bins
        position = angle / bin_width - 0.5
        lower = np.floor(position).astype(np.int32)
        fraction = (position - lower).astype(np.float32)
        lower_bin = np.mod(lower, self.bins)
        upper_bin = np.mod(lower + 1, self.bins)

        histogram = np.zeros((rows, columns, self.bins), np.float32)
        for row in range(rows):
            for column in range(columns):
                window = (slice(row * self.cell, (row + 1) * self.cell), slice(column * self.cell, (column + 1) * self.cell))
                weights = magnitude[window].ravel()
                np.add.at(histogram[row, column], lower_bin[window].ravel(), weights * (1.0 - fraction[window].ravel()))
                np.add.at(histogram[row, column], upper_bin[window].ravel(), weights * fraction[window].ravel())

        features: list[np.ndarray] = []
        for row in range(rows - self.block + 1):
            for column in range(columns - self.block + 1):
                vector = histogram[row : row + self.block, column : column + self.block].ravel()
                vector = vector / np.sqrt(np.sum(vector**2) + self._epsilon**2)
                vector = np.clip(vector, 0.0, self.clip)
                vector = vector / np.sqrt(np.sum(vector**2) + self._epsilon**2)
                features.append(vector.astype(np.float32))
        return np.concatenate(features) if features else np.zeros(1, np.float32)


@dataclass
class Specimen:
    """One normalised signature sample."""

    label: str
    image: np.ndarray                # colour crop as stored in the database
    normalised: np.ndarray = field(repr=False, default=None)  # type: ignore[assignment]
    hog: np.ndarray = field(repr=False, default=None)         # type: ignore[assignment]
    zoning: np.ndarray = field(repr=False, default=None)      # type: ignore[assignment]
    keypoints: tuple = field(repr=False, default=())
    descriptors: np.ndarray | None = field(repr=False, default=None)
    ink_ratio: float = 0.0
    aspect: float = 0.0
    valid: bool = True


@dataclass
class VerificationReport:
    """Outcome of comparing every specimen of one student."""

    index_no: str
    specimens: list[Specimen]
    similarity: np.ndarray
    mean_similarity: list[float]
    modified_z: list[float]
    flagged: list[int]
    threshold: float
    cohort_mean: float
    cohort_sd: float

    @property
    def consistent(self) -> bool:
        return not self.flagged

    def verdict_for(self, position: int) -> str:
        return "MISMATCH" if position in self.flagged else "consistent"

    def summary(self) -> str:
        if len(self.specimens) < 2:
            return "at least two specimens are needed before a comparison is meaningful"
        if self.consistent:
            return (
                f"all {len(self.specimens)} specimens are mutually consistent "
                f"(mean similarity {self.cohort_mean:.3f}, sd {self.cohort_sd:.3f})"
            )
        names = ", ".join(self.specimens[position].label for position in self.flagged)
        return f"{len(self.flagged)} specimen(s) do not match the rest: {names}"


class SignatureVerifier:
    """Compares the signature specimens collected for a single student."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # The canonical specimen is only 128 x 64, so ORB's defaults (a 31 px
        # patch and a 31 px border) would reject the whole image.  The patch and
        # border are scaled down to match, and FAST is made more sensitive
        # because pen strokes are thin, low-contrast structures.
        self._orb = cv2.ORB_create(
            nfeatures=settings.orb_features,
            scaleFactor=1.2,
            nlevels=6,
            edgeThreshold=6,
            patchSize=15,
            fastThreshold=8,
        )
        self._hog = HistogramOfOrientedGradients(cell=8, bins=9, block=2)

    # ------------------------------------------------------------------ #
    #  Normalisation
    # ------------------------------------------------------------------ #

    def zoning(self, image: np.ndarray) -> np.ndarray:
        """Ink-density (zoning) descriptor.

        The normalised specimen is divided into a fixed grid and the mean ink
        coverage of each cell becomes one feature.  It is the classic global
        descriptor for offline signature verification: coarse enough to survive
        the natural variation between two genuine signatures, fine enough to
        record where on the canvas a writer puts their weight.
        """
        rows, columns = self._settings.zoning_grid
        height, width = image.shape[:2]
        cell_h, cell_w = height // rows, width // columns
        if cell_h < 1 or cell_w < 1:
            return np.zeros(rows * columns, np.float32)
        return np.array(
            [
                image[row * cell_h : (row + 1) * cell_h, column * cell_w : (column + 1) * cell_w].mean() / 255.0
                for row in range(rows)
                for column in range(columns)
            ],
            np.float32,
        )

    def keep_dominant_components(self, mask: np.ndarray) -> np.ndarray:
        """Drop specks and neighbouring overflow, keeping the signature proper."""
        count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        if count <= 2:
            return mask
        largest = int(stats[1:, cv2.CC_STAT_AREA].max())
        floor = largest * self._settings.specimen_component_ratio
        kept = np.zeros_like(mask)
        for component in range(1, count):
            if stats[component, cv2.CC_STAT_AREA] >= floor:
                kept[labels == component] = 255
        return kept

    def segment(self, colour: np.ndarray) -> np.ndarray:
        """Binary ink mask of a signature crop (Otsu on the flattened luma)."""
        gray = cv2.cvtColor(colour, cv2.COLOR_BGR2GRAY) if colour.ndim == 3 else colour
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        return mask

    def normalise(self, colour: np.ndarray, mask: np.ndarray | None = None) -> tuple[np.ndarray, float, float]:
        """Crop to the ink and warp to the canonical size.

        ``mask`` is the ink mask that :mod:`attendance.signature` already isolated
        for this cell; it is far more reliable than re-thresholding the crop,
        because the pipeline had the whole page - and therefore the printed rules
        and the illumination field - available when it built it.  Otsu on the
        bare crop is kept as the fallback for images that arrive without a mask.

        The ink is warped to fill the canonical box, which normalises away the
        absolute size of the signature.  The aspect ratio that the warp destroys
        is measured first and returned, so that it can be compared separately
        instead of being lost.
        """
        mask = self.segment(colour) if mask is None else mask
        mask = self.keep_dominant_components(mask)
        points = cv2.findNonZero(mask)
        if points is None:
            width, height = self._settings.verify_size
            return np.zeros((height, width), np.uint8), 0.0, 0.0

        x, y, w, h = cv2.boundingRect(points)
        cropped = mask[y : y + h, x : x + w]
        aspect = w / float(h) if h else 0.0
        ink_ratio = float(cv2.countNonZero(cropped)) / max(1, cropped.size)

        width, height = self._settings.verify_size
        # Fit inside the canonical box *preserving the aspect ratio*, then centre
        # on a blank canvas.  Stretching each specimen to fill the box would
        # destroy exactly the proportion information that distinguishes one
        # writer from another.
        canvas = cv2.resize(cropped, (width, height), interpolation=cv2.INTER_AREA)
        _, canvas = cv2.threshold(canvas, 64, 255, cv2.THRESH_BINARY)
        # Equalise stroke weight so a thick pen and a thin pen compare fairly.
        canvas = cv2.morphologyEx(canvas, cv2.MORPH_CLOSE, np.ones((2, 2), np.uint8))
        return canvas, ink_ratio, aspect

    def describe(self, label: str, colour: np.ndarray, mask: np.ndarray | None = None) -> Specimen:
        """Build a fully described :class:`Specimen` from a stored crop."""
        normalised, ink_ratio, aspect = self.normalise(colour, mask)
        specimen = Specimen(
            label=label,
            image=colour,
            normalised=normalised,
            ink_ratio=ink_ratio,
            aspect=aspect,
            valid=cv2.countNonZero(normalised) > 40,
        )
        if specimen.valid:
            specimen.hog = self._hog.compute(normalised).flatten()
            specimen.zoning = self.zoning(normalised)
            # FAST needs a gradient; softening the hard binary edge gives ORB the
            # corner structure it looks for without moving any stroke.
            softened = cv2.GaussianBlur(normalised, (3, 3), 0)
            keypoints, descriptors = self._orb.detectAndCompute(softened, None)
            specimen.keypoints = tuple(keypoints)
            specimen.descriptors = descriptors
        return specimen

    # ------------------------------------------------------------------ #
    #  Similarity
    # ------------------------------------------------------------------ #

    @staticmethod
    def cosine(left: np.ndarray, right: np.ndarray) -> float:
        """Cosine similarity, clamped to [0, 1]."""
        if left is None or right is None or left.size == 0 or right.size == 0:
            return 0.0
        denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
        if denominator == 0.0:
            return 0.0
        return float(np.clip(np.dot(left, right) / denominator, 0.0, 1.0))

    def orb_score(self, left: Specimen, right: Specimen) -> float:
        """Fraction of key points that survive Lowe's ratio test, symmetrised.

        ORB produces binary descriptors, so the matcher uses the Hamming norm.
        Each descriptor of the query is matched against its two nearest
        neighbours in the train set; the match is kept only when the best
        distance is clearly smaller than the second best (``d1 < ratio * d2``),
        which discards the ambiguous matches that dominate repetitive pen
        strokes.

        Nearest-neighbour matching is *directional*: matching A against B does
        not give the same count as matching B against A, because "nearest" is
        asked of a different set each way.  A similarity that changes with
        argument order would make the comparison matrix depend on the loop
        order, so the two directions are averaged.
        """
        if left.descriptors is None or right.descriptors is None:
            return 0.0
        if len(left.descriptors) < 2 or len(right.descriptors) < 2:
            return 0.0

        forward = self._directional_orb_score(left.descriptors, right.descriptors)
        backward = self._directional_orb_score(right.descriptors, left.descriptors)
        return 0.5 * (forward + backward)

    def _directional_orb_score(self, query: np.ndarray, train: np.ndarray) -> float:
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        pairs = matcher.knnMatch(query, train, k=2)
        good = [
            best
            for best, second in (pair for pair in pairs if len(pair) == 2)
            if best.distance < self._settings.lowe_ratio * second.distance
        ]
        denominator = min(len(query), len(train))
        return float(len(good)) / denominator if denominator else 0.0

    @staticmethod
    def aspect_agreement(left: Specimen, right: Specimen) -> float:
        """How closely two specimens share a width-to-height ratio.

        Expressed as ``exp(-|ln(a1 / a2)|)``, which is 1 for identical ratios and
        falls off symmetrically whichever specimen is the wider - a plain
        difference would penalise the same relative discrepancy unevenly.
        """
        if left.aspect <= 0.0 or right.aspect <= 0.0:
            return 0.0
        return float(np.exp(-abs(np.log(left.aspect / right.aspect))))

    def similarity(self, left: Specimen, right: Specimen) -> float:
        """Fused similarity of two specimens, in [0, 1].

        Four views of the same pair are blended, because each one fails
        differently: the zoning grid captures *where* the ink sits, HOG captures
        *which way the strokes run*, ORB captures *repeated local structure*, and
        the aspect ratio captures the overall proportion that normalisation
        deliberately removed.  The weights are in ``Settings.fusion_weights``.
        """
        if not (left.valid and right.valid):
            return 0.0
        zoning_w, hog_w, orb_w, aspect_w = self._settings.fusion_weights
        return float(
            zoning_w * self.cosine(left.zoning, right.zoning)
            + hog_w * self.cosine(left.hog, right.hog)
            + orb_w * self.orb_score(left, right)
            + aspect_w * self.aspect_agreement(left, right)
        )

    # ------------------------------------------------------------------ #
    #  Reporting
    # ------------------------------------------------------------------ #

    def verify(self, index_no: str, samples: Sequence[tuple]) -> VerificationReport:
        """Compare every specimen of one student against every other.

        ``samples`` is a sequence of ``(label, colour_crop)`` or
        ``(label, colour_crop, ink_mask)`` tuples.
        """
        specimens = [
            self.describe(sample[0], sample[1], sample[2] if len(sample) > 2 else None) for sample in samples
        ]
        count = len(specimens)
        matrix = np.eye(count, dtype=float)

        for left, right in combinations(range(count), 2):
            score = self.similarity(specimens[left], specimens[right])
            matrix[left, right] = matrix[right, left] = score

        means: list[float] = []
        for position in range(count):
            others = [matrix[position, other] for other in range(count) if other != position]
            means.append(float(np.mean(others)) if others else 1.0)

        cohort_mean = float(np.mean(means)) if means else 0.0
        cohort_sd = float(np.std(means)) if means else 0.0
        scores = self.modified_z_scores(means)

        flagged: list[int] = []
        if count >= 4:
            median = float(np.median(means))
            gap = self._settings.outlier_relative_gap
            # Two independent reasons to report: an outlier among the student's
            # own specimens - statistically unusual *and* materially lower - or a
            # similarity so low that it is anomalous outright.
            flagged = [
                position
                for position in range(count)
                if (
                    scores[position] < -self._settings.outlier_z
                    and means[position] < median * (1.0 - gap)
                )
                or means[position] < self._settings.mismatch_threshold
            ]
        elif count in (2, 3):
            # Too few specimens for an outlier test to mean anything; only the
            # absolute floor applies.
            flagged = [
                position for position in range(count) if means[position] < self._settings.mismatch_threshold
            ]

        return VerificationReport(
            index_no=index_no,
            specimens=specimens,
            similarity=matrix,
            mean_similarity=means,
            modified_z=scores,
            flagged=flagged,
            threshold=self._settings.mismatch_threshold,
            cohort_mean=cohort_mean,
            cohort_sd=cohort_sd,
        )

    @staticmethod
    def modified_z_scores(values: Sequence[float]) -> list[float]:
        """Iglewicz & Hoaglin's robust z-score: ``0.6745 (x - median) / MAD``.

        The constant rescales the median absolute deviation so that, for normally
        distributed data, the score matches the ordinary z-score.  When the MAD
        is zero (every specimen equally similar) the sample standard deviation is
        used instead, and if that is zero too every score is zero.
        """
        if not values:
            return []
        array = np.asarray(values, dtype=float)
        median = float(np.median(array))
        deviation = float(np.median(np.abs(array - median)))
        if deviation == 0.0:
            deviation = float(np.std(array)) / 0.6745 if np.std(array) > 0 else 0.0
        if deviation == 0.0:
            return [0.0] * len(values)
        return [float(0.6745 * (value - median) / deviation) for value in array]

    # ------------------------------------------------------------------ #
    #  Figures
    # ------------------------------------------------------------------ #

    @staticmethod
    def contact_sheet(report: VerificationReport, tile: tuple[int, int] = (300, 150)) -> np.ndarray:
        """Side-by-side montage of the raw specimens, captioned with the verdict."""
        width, height = tile
        columns = []
        for position, specimen in enumerate(report.specimens):
            canvas = cv2.resize(specimen.image, (width, height), interpolation=cv2.INTER_AREA)
            canvas = cv2.copyMakeBorder(canvas, 34, 26, 4, 4, cv2.BORDER_CONSTANT, value=(252, 252, 251))
            mismatch = position in report.flagged
            colour = (59, 59, 208) if mismatch else (12, 163, 12)
            cv2.rectangle(canvas, (4, 34), (width + 3, height + 33), colour, 2)
            cv2.putText(canvas, specimen.label, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (11, 11, 11), 1, cv2.LINE_AA)
            cv2.putText(
                canvas,
                f"sim {report.mean_similarity[position]:.3f}  {report.verdict_for(position)}",
                (6, height + 54),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                colour,
                1,
                cv2.LINE_AA,
            )
            columns.append(canvas)
        if not columns:
            return np.zeros((10, 10, 3), np.uint8)
        return np.hstack(columns)

    @staticmethod
    def normalised_sheet(report: VerificationReport, tile: tuple[int, int] = (256, 128)) -> np.ndarray:
        """The same specimens after size/aspect normalisation - what the
        descriptors actually see."""
        width, height = tile
        columns = []
        for specimen in report.specimens:
            image = specimen.normalised if specimen.normalised is not None else np.zeros((height, width), np.uint8)
            canvas = cv2.cvtColor(cv2.resize(image, (width, height), interpolation=cv2.INTER_NEAREST), cv2.COLOR_GRAY2BGR)
            canvas = cv2.bitwise_not(canvas)
            canvas = cv2.copyMakeBorder(canvas, 26, 6, 4, 4, cv2.BORDER_CONSTANT, value=(252, 252, 251))
            cv2.putText(canvas, specimen.label, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (11, 11, 11), 1, cv2.LINE_AA)
            columns.append(canvas)
        if not columns:
            return np.zeros((10, 10, 3), np.uint8)
        return np.hstack(columns)
