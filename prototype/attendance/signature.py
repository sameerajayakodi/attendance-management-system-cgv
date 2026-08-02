"""Signature-cell analysis: deciding whether a student actually signed.

Reading the signature column is harder than it first looks.  Signatures are not
polite: they start above their row, they trail underlines across the neighbouring
cell, they run off the right-hand edge of the table, and they are drawn with pens
of different colours and thicknesses.  A naive "is this cell blank?" test
therefore mis-classifies a substantial fraction of the reference sheets.

The approach used here works on *ink*, not on cells:

1.  the printed rules are subtracted from the binary image, leaving only pen;
2.  the remaining ink is grouped into connected components;
3.  every component is charged to the row that owns most of its pixel mass;
4.  a row is PRESENT when the ink charged to it exceeds an area threshold.

Because ownership is decided by mass rather than by containment, a signature that
straddles a rule is still credited to the correct student.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import cv2
import numpy as np

from .config import Settings
from .imaging import chromatic_ink_mask, describe_pen_colour, dominant_ink_colour
from .table import LineMasks, TableGrid

PRESENT = "PRESENT"
ABSENT = "ABSENT"


@dataclass(frozen=True)
class SignatureFeatures:
    """Quantitative description of the ink charged to one signature cell."""

    ink_pixels: int
    cell_area: int
    components: int
    largest_component: int
    fill_ratio: float
    """Ink pixels divided by the area of the ink's own bounding box - a measure
    of how 'stroke-like' the mark is."""
    pen_colour: str

    @property
    def ink_ratio(self) -> float:
        """Fraction of the nominal signature cell covered by pen ink."""
        return self.ink_pixels / float(self.cell_area) if self.cell_area else 0.0

    def as_dict(self) -> dict[str, float | int | str]:
        return {
            "ink_pixels": self.ink_pixels,
            "cell_area": self.cell_area,
            "ink_ratio": round(self.ink_ratio, 5),
            "components": self.components,
            "largest_component": self.largest_component,
            "fill_ratio": round(self.fill_ratio, 4),
            "pen_colour": self.pen_colour,
        }


@dataclass
class SignatureVerdict:
    """The decision taken for one roster row."""

    row: int
    status: str
    confidence: float
    features: SignatureFeatures
    box: tuple[int, int, int, int]
    """The row's signature cell - what the progress overlay draws."""
    ink_box: tuple[int, int, int, int] | None = None
    """Tight bounding box of the ink that belongs to *this* row, if any."""
    crop: np.ndarray | None = None
    """Colour specimen, cropped to :attr:`ink_box`."""
    mask: np.ndarray | None = None
    """Ink mask of the specimen, containing only this row's own strokes."""

    @property
    def present(self) -> bool:
        return self.status == PRESENT


class SignatureAnalyzer:
    """Classifies every data row of a roster table as PRESENT or ABSENT."""

    #: a component taller than this many rows is shared between rows instead of
    #: being charged in full to a single one
    SPLIT_HEIGHT_IN_ROWS = 1.6

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # ------------------------------------------------------------------ #
    #  Region of interest
    # ------------------------------------------------------------------ #

    def signature_strip(self, grid: TableGrid, frame_shape: Sequence[int]) -> tuple[int, int, int, int]:
        """Pixel box covering the signature column of every data row.

        The box is widened to the right by ``Settings.overflow_ratio`` so that the
        part of a signature written past the table border is still recovered.
        """
        column = grid.column_count - 1
        x0, x1 = grid.column_band(column)
        margin = int(round((x1 - x0) * self._settings.cell_margin_ratio))
        overflow = int(round((x1 - x0) * self._settings.overflow_ratio))

        left = min(x0 + margin, x1 - 5)
        right = min(int(frame_shape[1]) - 1, x1 + overflow)
        top = grid.row_edges[grid.header_row + 1]
        bottom = grid.row_edges[-1]
        return (left, top, right, bottom)

    # ------------------------------------------------------------------ #
    #  Ink isolation
    # ------------------------------------------------------------------ #

    def ink_mask(self, binary: np.ndarray, masks: LineMasks) -> np.ndarray:
        """Binary image with the printed rules removed, leaving only pen strokes.

        The rule mask is dilated before subtraction so that the anti-aliased
        shoulder of each printed line disappears along with its core.
        """
        size = self._settings.rule_removal_dilate | 1
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (size, size))
        rules = cv2.dilate(masks.grid, kernel, iterations=1)
        ink = cv2.subtract(binary, rules)
        # Re-connect strokes that the subtraction cut where they crossed a rule.
        ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        return cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2)))

    # ------------------------------------------------------------------ #
    #  Classification
    # ------------------------------------------------------------------ #

    def analyse(
        self,
        colour: np.ndarray,
        binary: np.ndarray,
        masks: LineMasks,
        grid: TableGrid,
    ) -> list[SignatureVerdict]:
        """Produce one :class:`SignatureVerdict` per data row of ``grid``."""
        settings = self._settings
        strip_x0, strip_y0, strip_x1, strip_y1 = self.signature_strip(grid, binary.shape)

        ink = self.ink_mask(binary, masks)
        window = ink[strip_y0:strip_y1, strip_x0:strip_x1]

        rows = grid.data_rows
        column = grid.column_count - 1
        nominal_width = grid.column_band(column)[1] - grid.column_band(column)[0]
        row_height = grid.median_row_height()
        nominal_area = max(1, int(round(nominal_width * row_height)))
        min_component = max(12, int(round(nominal_area * settings.min_component_area_ratio)))

        charged = {row: 0 for row in rows}
        component_count = {row: 0 for row in rows}
        largest = {row: 0 for row in rows}
        bboxes: dict[int, list[tuple[int, int, int, int]]] = {row: [] for row in rows}
        # Per-row ink canvases: only the strokes that belong to a row are painted
        # onto that row's canvas, so a specimen never carries its neighbour's ink.
        owned = {row: np.zeros(window.shape, np.uint8) for row in rows}

        if window.size:
            count, labels, stats, _ = cv2.connectedComponentsWithStats(window, connectivity=8)
            for component in range(1, count):
                area = int(stats[component, cv2.CC_STAT_AREA])
                if area < min_component:
                    continue
                width = int(stats[component, cv2.CC_STAT_WIDTH])
                height = int(stats[component, cv2.CC_STAT_HEIGHT])
                if self._is_residual_rule(width, height, area):
                    continue

                top = int(stats[component, cv2.CC_STAT_TOP]) + strip_y0
                left = int(stats[component, cv2.CC_STAT_LEFT]) + strip_x0
                pixels_of = labels == component
                mass = self._mass_per_row(pixels_of, grid, rows, strip_y0)
                if not mass:
                    continue

                if height > self.SPLIT_HEIGHT_IN_ROWS * row_height:
                    # A tall mark is shared: two students' signatures have run
                    # into one another, so credit each row with what it holds.
                    for row, pixels in mass.items():
                        band_top, band_bottom = grid.row_band(row)
                        band = np.zeros_like(pixels_of)
                        band[max(0, band_top - strip_y0) : max(0, band_bottom - strip_y0), :] = True
                        share = pixels_of & band
                        owned[row][share] = 255
                        charged[row] += pixels
                        component_count[row] += 1
                        largest[row] = max(largest[row], pixels)
                        bboxes[row].append((left, max(band_top, top), left + width, min(band_bottom, top + height)))
                else:
                    row = max(mass, key=lambda key: mass[key])
                    owned[row][pixels_of] = 255
                    charged[row] += area
                    component_count[row] += 1
                    largest[row] = max(largest[row], area)
                    bboxes[row].append((left, top, left + width, top + height))

        verdicts: list[SignatureVerdict] = []
        for row in rows:
            band_top, band_bottom = grid.row_band(row)
            cell_box = (strip_x0, band_top, strip_x1, band_bottom)
            ink_box = self._tight_box(owned[row], strip_x0, strip_y0)
            crop_box = ink_box or cell_box

            crop = colour[crop_box[1] : crop_box[3], crop_box[0] : crop_box[2]].copy()
            row_mask = owned[row][
                crop_box[1] - strip_y0 : crop_box[3] - strip_y0,
                crop_box[0] - strip_x0 : crop_box[2] - strip_x0,
            ].copy()

            features = SignatureFeatures(
                ink_pixels=int(charged[row]),
                cell_area=nominal_area,
                components=int(component_count[row]),
                largest_component=int(largest[row]),
                fill_ratio=self._fill_ratio(charged[row], bboxes[row]),
                pen_colour=self._pen_colour(crop, row_mask),
            )
            status, confidence = self._decide(features)
            verdicts.append(
                SignatureVerdict(
                    row=row,
                    status=status,
                    confidence=confidence,
                    features=features,
                    box=cell_box,
                    ink_box=ink_box,
                    crop=crop,
                    mask=row_mask,
                )
            )
        return verdicts

    @staticmethod
    def _tight_box(row_ink: np.ndarray, strip_x0: int, strip_y0: int) -> tuple[int, int, int, int] | None:
        """Padded bounding box of one row's own ink, in frame coordinates.

        The box is clamped to the analysis strip before the strip's origin is
        added back, so the result always indexes both the strip-sized ink canvas
        and the full frame consistently.
        """
        points = cv2.findNonZero(row_ink)
        if points is None:
            return None
        x, y, width, height = cv2.boundingRect(points)
        pad = max(4, int(round(0.06 * max(width, height))))

        left = max(0, x - pad)
        top = max(0, y - pad)
        right = min(row_ink.shape[1], x + width + pad)
        bottom = min(row_ink.shape[0], y + height + pad)
        if right - left < 8 or bottom - top < 8:
            return None
        return (left + strip_x0, top + strip_y0, right + strip_x0, bottom + strip_y0)

    # ------------------------------------------------------------------ #
    #  Internals
    # ------------------------------------------------------------------ #

    def _is_residual_rule(self, width: int, height: int, area: int) -> bool:
        """Reject long, thin, dense components left over by rule subtraction."""
        aspect = self._settings.line_aspect_reject
        if height <= 2 and width > height * aspect:
            return True
        if width <= 2 and height > width * aspect:
            return True
        return area == 0

    @staticmethod
    def _mass_per_row(
        component_pixels: np.ndarray,
        grid: TableGrid,
        rows: Sequence[int],
        strip_y0: int,
    ) -> dict[int, int]:
        """How many pixels of one component fall inside each row band."""
        row_sums = component_pixels.sum(axis=1)
        mass: dict[int, int] = {}
        for row in rows:
            top, bottom = grid.row_band(row)
            local_top = max(0, top - strip_y0)
            local_bottom = min(len(row_sums), bottom - strip_y0)
            if local_bottom <= local_top:
                continue
            pixels = int(row_sums[local_top:local_bottom].sum())
            if pixels:
                mass[row] = pixels
        return mass

    @staticmethod
    def _fill_ratio(ink_pixels: int, boxes: Sequence[tuple[int, int, int, int]]) -> float:
        if not boxes or ink_pixels == 0:
            return 0.0
        x0 = min(box[0] for box in boxes)
        y0 = min(box[1] for box in boxes)
        x1 = max(box[2] for box in boxes)
        y1 = max(box[3] for box in boxes)
        area = max(1, (x1 - x0) * (y1 - y0))
        return float(ink_pixels) / area

    @staticmethod
    def _pen_colour(crop: np.ndarray, mask: np.ndarray) -> str:
        if crop.size == 0 or mask.size == 0 or cv2.countNonZero(mask) < 20:
            return "none"
        chroma = chromatic_ink_mask(crop)
        combined = cv2.bitwise_and(mask, chroma)
        if cv2.countNonZero(combined) < 20:
            combined = mask
        return describe_pen_colour(dominant_ink_colour(crop, combined))

    def _decide(self, features: SignatureFeatures) -> tuple[str, float]:
        """Threshold the measured ink and attach a confidence in [0, 1]."""
        settings = self._settings
        ratio = features.ink_ratio
        enough_area = ratio >= settings.min_ink_ratio
        enough_pixels = features.ink_pixels >= settings.min_ink_pixels

        if enough_area and enough_pixels:
            span = settings.min_ink_ratio * settings.confidence_span
            confidence = float(np.clip(ratio / span, 0.35, 1.0))
            return PRESENT, round(confidence, 3)

        headroom = ratio / settings.min_ink_ratio if settings.min_ink_ratio else 0.0
        confidence = float(np.clip(1.0 - headroom, 0.35, 1.0))
        return ABSENT, round(confidence, 3)

    # ------------------------------------------------------------------ #
    #  Presentation
    # ------------------------------------------------------------------ #

    @staticmethod
    def render(image: np.ndarray, verdicts: Sequence[SignatureVerdict]) -> np.ndarray:
        """Annotate ``image`` with the per-row decision, for the progress display."""
        canvas = image.copy() if image.ndim == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        for verdict in verdicts:
            x0, y0, x1, y1 = verdict.box
            colour = (60, 190, 60) if verdict.present else (60, 60, 220)
            cv2.rectangle(canvas, (x0, y0), (x1, y1), colour, 2)
            if verdict.ink_box is not None:
                # The tight box shows exactly which strokes were charged to this
                # row - the specimen that is stored for signature verification.
                ix0, iy0, ix1, iy1 = verdict.ink_box
                cv2.rectangle(canvas, (ix0, iy0), (ix1, iy1), (200, 140, 0), 1)
            caption = f"{verdict.status[:3]} {verdict.features.ink_ratio * 100:.1f}%"
            cv2.putText(
                canvas,
                caption,
                (x1 + 6, y1 - 6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                colour,
                1,
                cv2.LINE_AA,
            )
        return canvas
