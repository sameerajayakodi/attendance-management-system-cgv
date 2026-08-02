"""Detection of the ruled tables printed on the signing sheet.

The signing sheet carries two tables: a two-row *session* table (date, lecturer,
lecturer's signature) and the *roster* table that holds one row per student.  The
roster table is located by morphological line extraction rather than by fixed
coordinates, so the system tolerates the translation, scale and rotation that
come with hand-held photography.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import cv2
import numpy as np

from .config import Settings

BBox = tuple[int, int, int, int]


# --------------------------------------------------------------------------- #
#  Value objects
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Cell:
    """A single grid cell, addressed by (row, column) and bounded by pixels."""

    row: int
    column: int
    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0

    @property
    def area(self) -> int:
        return max(0, self.width) * max(0, self.height)

    @property
    def box(self) -> BBox:
        return (self.x0, self.y0, self.x1, self.y1)

    def inset(self, ratio: float) -> BBox:
        """Shrink the cell by ``ratio`` on every side to drop the printed rules."""
        dx = int(round(self.width * ratio))
        dy = int(round(self.height * ratio))
        return (self.x0 + dx, self.y0 + dy, max(self.x0 + dx + 1, self.x1 - dx), max(self.y0 + dy + 1, self.y1 - dy))

    def crop(self, image: np.ndarray) -> np.ndarray:
        return image[self.y0 : self.y1, self.x0 : self.x1]


@dataclass
class TableGrid:
    """A reconstructed table: an ordered set of horizontal and vertical rules."""

    row_edges: list[int]
    column_edges: list[int]
    #: index of the band that holds the column captions
    header_row: int = 0

    @property
    def bbox(self) -> BBox:
        return (self.column_edges[0], self.row_edges[0], self.column_edges[-1], self.row_edges[-1])

    @property
    def row_count(self) -> int:
        return max(0, len(self.row_edges) - 1)

    @property
    def column_count(self) -> int:
        return max(0, len(self.column_edges) - 1)

    @property
    def data_rows(self) -> list[int]:
        """Band indices that hold student records (everything below the header)."""
        return list(range(self.header_row + 1, self.row_count))

    def row_band(self, row: int) -> tuple[int, int]:
        return (self.row_edges[row], self.row_edges[row + 1])

    def column_band(self, column: int) -> tuple[int, int]:
        return (self.column_edges[column], self.column_edges[column + 1])

    def cell(self, row: int, column: int) -> Cell:
        x0, x1 = self.column_band(column)
        y0, y1 = self.row_band(row)
        return Cell(row=row, column=column, x0=x0, y0=y0, x1=x1, y1=y1)

    def repair(self, expected_data_rows: int, tolerance: float = 0.30) -> int:
        """Reinstate rules the detector missed, using the form's uniform pitch.

        The signing sheet is a printed form, so every data row has the same
        height.  If the detector loses a faint or bowed rule, the band it should
        have divided is left at (approximately) an integer multiple of that
        pitch, and the missing rules can be interpolated back with confidence.
        Nothing is inserted unless the band's height really is close to a whole
        multiple - a genuinely tall band is left alone.

        Returns the number of rules inserted.
        """
        if expected_data_rows <= 0 or len(self.data_rows) >= expected_data_rows:
            return 0

        heights = np.diff(self.row_edges).astype(float)
        if heights.size == 0:
            return 0
        rough = float(np.median(heights))
        core = heights[(heights >= 0.70 * rough) & (heights <= 1.40 * rough)]
        pitch = float(np.median(core)) if core.size else rough
        if pitch <= 1.0:
            return 0

        edges = [self.row_edges[0]]
        inserted = 0
        for top, bottom in zip(self.row_edges, self.row_edges[1:]):
            span = float(bottom - top)
            multiple = int(round(span / pitch))
            if multiple >= 2 and abs(span - multiple * pitch) <= tolerance * pitch:
                for step in range(1, multiple):
                    edges.append(int(round(top + step * span / multiple)))
                    inserted += 1
            edges.append(bottom)

        if inserted:
            self.row_edges = sorted(set(edges))
        return inserted

    def median_row_height(self) -> float:
        heights = np.diff(self.row_edges)
        return float(np.median(heights)) if heights.size else 0.0

    def uniformity(self) -> float:
        """Coefficient of variation of the data-row heights (0 = perfectly even).

        A well-detected roster table has near-identical row heights, so this is a
        cheap self-check that a spurious rule has not been inserted.
        """
        if len(self.data_rows) < 2:
            return 0.0
        heights = np.array([self.row_band(row)[1] - self.row_band(row)[0] for row in self.data_rows], float)
        mean = heights.mean()
        return float(heights.std() / mean) if mean else 0.0


@dataclass
class LineMasks:
    """The morphological by-products of table detection, kept for the report."""

    horizontal: np.ndarray
    vertical: np.ndarray

    @property
    def grid(self) -> np.ndarray:
        return cv2.bitwise_or(self.horizontal, self.vertical)

    @property
    def intersections(self) -> np.ndarray:
        return cv2.bitwise_and(self.horizontal, self.vertical)


@dataclass
class DetectionResult:
    """Everything :class:`TableDetector` produces for one sheet."""

    masks: LineMasks
    tables: list[TableGrid] = field(default_factory=list)
    roster: TableGrid | None = None
    session: TableGrid | None = None


class TableDetectionError(RuntimeError):
    """Raised when no plausible roster table can be recovered from a sheet."""


# --------------------------------------------------------------------------- #
#  Detector
# --------------------------------------------------------------------------- #


class TableDetector:
    """Recovers :class:`TableGrid` objects from a binarised signing sheet."""

    #: absolute floor: below this fraction of the table's span a run of ink is
    #: not a printed rule at all (it is a signature underline or a stray mark)
    HORIZONTAL_COVERAGE = 0.30
    VERTICAL_COVERAGE = 0.28
    #: relative gate: a rule must also reach this fraction of the *median* rule
    #: of its own table.  Loose sheets photographed on a desk bow slightly, so
    #: the lower rules of a page are systematically less well covered than the
    #: upper ones; judging each rule against its own table absorbs that, where a
    #: single absolute threshold has to be re-tuned for every capture geometry.
    RELATIVE_COVERAGE = 0.62

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # ------------------------------------------------------------------ #
    #  Stage 1 - morphological line extraction
    # ------------------------------------------------------------------ #

    def extract_lines(self, binary: np.ndarray) -> LineMasks:
        """Split the binary image into its horizontal and vertical rule masks.

        Eroding with a long thin structuring element destroys everything that is
        not a run of that shape - handwriting included - and the matching
        dilation restores the surviving rules to their original length.
        """
        height, width = binary.shape[:2]

        h_size = self._settings.kernel_for_horizontal_rules(width)
        v_size = self._settings.kernel_for_vertical_rules(height)

        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, h_size)
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, v_size)

        horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel, iterations=1)
        vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel, iterations=1)

        # Bridge the small gaps left where a rule crosses a staple hole or fold.
        horizontal = cv2.dilate(horizontal, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 1)))
        vertical = cv2.dilate(vertical, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 9)))
        return LineMasks(horizontal=horizontal, vertical=vertical)

    # ------------------------------------------------------------------ #
    #  Stage 2 - candidate regions
    # ------------------------------------------------------------------ #

    def candidate_boxes(self, masks: LineMasks, frame_shape: Sequence[int]) -> list[BBox]:
        """Bounding boxes of connected grid structures, largest first."""
        grid = cv2.dilate(masks.grid, cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)))
        contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        frame_area = float(frame_shape[0] * frame_shape[1])
        boxes: list[BBox] = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w * h < frame_area * self._settings.min_table_area_ratio:
                continue
            if w < frame_shape[1] * 0.2 or h < 20:
                continue
            boxes.append((x, y, x + w, y + h))
        boxes.sort(key=lambda box: (box[2] - box[0]) * (box[3] - box[1]), reverse=True)
        return boxes

    # ------------------------------------------------------------------ #
    #  Stage 3 - rule positions inside a candidate
    # ------------------------------------------------------------------ #

    def _rule_positions(self, mask: np.ndarray, box: BBox, axis: int, coverage: float) -> list[int]:
        """Locate rules inside ``box`` along ``axis`` (0 = rows, 1 = columns).

        A row of the mask is a *rule candidate* when the proportion of ink it
        contains exceeds ``coverage``.  Adjacent candidates are then collapsed to
        their centre of mass, which gives one integer position per printed rule.
        """
        x0, y0, x1, y1 = box
        window = mask[y0:y1, x0:x1]
        if window.size == 0:
            return []

        # Skew correction never removes the last fraction of a degree, and the
        # residual tilt smears a long rule across several rows of the mask - the
        # wider the image, the more rows.  Closing the window across that smear
        # (and only for the purpose of measuring coverage) restores a single
        # densely-covered band per printed rule, and keeps the measurement
        # independent of the working resolution.
        smear = max(3, int(round(mask.shape[1] / 400.0)))
        span = (1, smear) if axis == 0 else (smear, 1)
        window = cv2.morphologyEx(window, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, span))

        if axis == 0:
            profile = (window > 0).sum(axis=1) / float(max(1, window.shape[1]))
            offset = y0
        else:
            profile = (window > 0).sum(axis=0) / float(max(1, window.shape[0]))
            offset = x0

        hits = np.flatnonzero(profile >= coverage)
        if hits.size == 0:
            return []

        separation = self._settings.rule_separation_for(mask.shape[1])
        groups: list[list[int]] = [[int(hits[0])]]
        for value in hits[1:]:
            if value - groups[-1][-1] <= separation:
                groups[-1].append(int(value))
            else:
                groups.append([int(value)])

        peaks = np.array([float(profile[group].max()) for group in groups])
        gate = max(coverage, self.RELATIVE_COVERAGE * float(np.median(peaks)))

        positions = []
        for group, peak in zip(groups, peaks):
            if peak < gate:
                continue
            weights = profile[group]
            centre = float(np.average(group, weights=weights)) if weights.sum() else float(np.mean(group))
            positions.append(int(round(centre)) + offset)
        return positions

    def build_grid(self, masks: LineMasks, box: BBox) -> TableGrid | None:
        """Turn a candidate box into a :class:`TableGrid`, or ``None`` if it is not one."""
        rows = self._rule_positions(masks.horizontal, box, axis=0, coverage=self.HORIZONTAL_COVERAGE)
        columns = self._rule_positions(masks.vertical, box, axis=1, coverage=self.VERTICAL_COVERAGE)
        if len(rows) < 2 or len(columns) < 2:
            return None
        return TableGrid(row_edges=rows, column_edges=columns)

    # ------------------------------------------------------------------ #
    #  Stage 4 - pick the roster
    # ------------------------------------------------------------------ #

    def detect(self, binary: np.ndarray, masks: LineMasks | None = None) -> DetectionResult:
        """Full detection: masks -> candidates -> grids -> roster selection.

        ``masks`` may be supplied when the caller has already run
        :meth:`extract_lines` (the pipeline does, so that the morphology is not
        paid for twice).
        """
        masks = masks if masks is not None else self.extract_lines(binary)
        grids: list[TableGrid] = []
        for box in self.candidate_boxes(masks, binary.shape):
            grid = self.build_grid(masks, box)
            if grid is not None:
                grids.append(grid)

        result = DetectionResult(masks=masks, tables=grids)
        usable = [grid for grid in grids if len(grid.data_rows) >= self._settings.min_data_rows]
        if not usable:
            raise TableDetectionError(
                "no table with at least "
                f"{self._settings.min_data_rows} data rows was found - check focus, "
                "lighting and that the whole sheet is inside the frame"
            )

        # The roster is the table with the most rows; ties go to the lower table,
        # because the session table is always printed above the roster.
        result.roster = max(usable, key=lambda grid: (grid.row_count, grid.bbox[1]))
        others = [grid for grid in grids if grid is not result.roster]
        if others:
            result.session = min(others, key=lambda grid: grid.bbox[1])
        return result

    # ------------------------------------------------------------------ #
    #  Presentation
    # ------------------------------------------------------------------ #

    @staticmethod
    def render(image: np.ndarray, result: DetectionResult) -> np.ndarray:
        """Draw the detected grids over ``image`` for the progress display."""
        canvas = image.copy() if image.ndim == 3 else cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        for grid in result.tables:
            colour = (0, 200, 255) if grid is not result.roster else (40, 200, 60)
            thickness = 1 if grid is not result.roster else 2
            x0, y0, x1, y1 = grid.bbox
            cv2.rectangle(canvas, (x0, y0), (x1, y1), colour, thickness)
            for y in grid.row_edges:
                cv2.line(canvas, (x0, y), (x1, y), colour, 1)
            for x in grid.column_edges:
                cv2.line(canvas, (x, y0), (x, y1), colour, 1)
        if result.roster is not None:
            for row in result.roster.data_rows:
                cell = result.roster.cell(row, result.roster.column_count - 1)
                cv2.rectangle(canvas, (cell.x0, cell.y0), (cell.x1, cell.y1), (255, 90, 0), 2)
        return canvas
