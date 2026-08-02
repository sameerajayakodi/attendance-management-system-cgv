"""Central configuration for the Student Attendance Management System (SAMS).

Every tunable constant used by the image-processing pipeline lives here so that
the algorithms themselves stay free of magic numbers and so that a single
:class:`Settings` instance can be threaded through the whole application.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path

# --------------------------------------------------------------------------- #
#  Project level paths
# --------------------------------------------------------------------------- #

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent

DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
STAGE_DIR = OUTPUT_DIR / "stages"
FIGURE_DIR = OUTPUT_DIR / "figures"
CROP_DIR = OUTPUT_DIR / "signatures"

DEFAULT_DATABASE = DATA_DIR / "attendance.db"
DEFAULT_INFO_XML = DATA_DIR / "info.xml"


@dataclass(frozen=True)
class Settings:
    """Immutable bundle of pipeline parameters.

    The values were tuned on the five reference signing sheets supplied with the
    coursework (3024 x 4032 smart-phone photographs, mixed pen colours, moderate
    perspective skew and uneven illumination).
    """

    # -- acquisition ------------------------------------------------------- #
    working_width: int = 1700
    """Every photograph is rescaled to this width before processing.

    Working at a fixed width makes all downstream kernel sizes resolution
    independent, and cuts the run time of the morphology by roughly 3x compared
    with the native 3024 px images.
    """

    # -- illumination / denoising ------------------------------------------ #
    background_kernel: int = 41
    """Size of the morphological closing kernel used to estimate the
    illumination field (must be larger than the thickest glyph stroke)."""

    bilateral_diameter: int = 7
    bilateral_sigma_colour: float = 45.0
    bilateral_sigma_space: float = 45.0

    # -- binarisation ------------------------------------------------------ #
    adaptive_block: int = 31
    """Neighbourhood size of the adaptive (Gaussian) threshold. Odd, > 1."""
    adaptive_c: int = 12
    """Constant subtracted from the local weighted mean."""

    # -- skew correction --------------------------------------------------- #
    max_skew_degrees: float = 12.0
    """Rotations larger than this are assumed to be a detection error and are
    ignored rather than applied."""
    hough_threshold: int = 150
    hough_min_line_ratio: float = 0.25
    """A Hough segment must span at least this fraction of the image width to be
    accepted as a table rule."""

    # -- table / grid detection -------------------------------------------- #
    horizontal_scale: int = 28
    """Width of the horizontal structuring element expressed as
    ``image_width / horizontal_scale``."""
    vertical_scale: int = 42
    """Height of the vertical structuring element expressed as
    ``image_height / vertical_scale``."""
    min_table_area_ratio: float = 0.012
    """Smallest contour (as a fraction of the frame) that may be a table."""
    min_rule_separation: int = 12
    """Two detected rules closer than this (in working pixels) are merged."""
    projection_ratio: float = 0.35
    """A projection profile peak must reach this fraction of its maximum before
    it is accepted as a rule."""
    min_data_rows: int = 3
    """The roster table must yield at least this many data rows."""

    # -- signature region -------------------------------------------------- #
    cell_margin_ratio: float = 0.10
    """Fraction of the cell trimmed on every side to discard the printed rules
    and any bleed from the neighbouring column."""
    overflow_ratio: float = 0.22
    """Signatures routinely run past the right-hand border of the sheet.  The
    analysis strip is widened by this fraction of the signature-column width to
    recover that ink."""
    rule_removal_dilate: int = 3
    """Dilation applied to the detected rule mask before it is subtracted from
    the ink mask."""

    # -- ink classification ------------------------------------------------- #
    min_component_area_ratio: float = 0.0016
    """Connected components smaller than this fraction of one signature cell are
    treated as speckle (dust, JPEG ringing, stray dots)."""
    min_ink_ratio: float = 0.0075
    """A row is declared PRESENT when the ink it owns covers at least this
    fraction of its signature cell."""
    min_ink_pixels: int = 110
    """Absolute safety net so that very small cells cannot pass on ratio alone."""
    line_aspect_reject: float = 14.0
    """Components thinner than 1/``line_aspect_reject`` of their length are
    residual printed rules, not pen strokes."""
    confidence_span: float = 3.0
    """Ink ratio (as a multiple of ``min_ink_ratio``) at which the classifier
    reports full confidence."""

    # -- signature verification -------------------------------------------- #
    verify_size: tuple[int, int] = (128, 64)
    """Canonical (width, height) that every signature crop is warped to before
    descriptors are computed."""
    orb_features: int = 400
    lowe_ratio: float = 0.75
    zoning_grid: tuple[int, int] = (8, 16)
    """Rows x columns of the ink-density (zoning) descriptor."""
    specimen_component_ratio: float = 0.12
    """Components smaller than this fraction of a specimen's largest component
    are dropped before the descriptors are computed - they are almost always a
    neighbouring signature's overflow rather than part of this signature."""
    fusion_weights: tuple[float, float, float, float] = (0.35, 0.35, 0.10, 0.20)
    """Blend of (zoning, HOG, ORB, aspect-agreement).  Chosen by measuring the
    separation between genuine and impostor pairs on the reference sheets; see
    ``tools/evaluate.py``."""
    mismatch_threshold: float = 0.35
    """Conservative absolute floor for reporting a specimen as a mismatch.

    Measured on the reference set, genuine pairs average 0.47 and impostor pairs
    0.39, so an absolute threshold placed between the two means would flag almost
    every student.  The floor is therefore set below the impostor mean and only
    catches specimens that are anomalous by any reading; the *primary* signal is
    the within-student outlier test governed by ``outlier_sigma``."""
    outlier_z: float = 3.5
    """Modified z-score (Iglewicz & Hoaglin) below which a specimen counts as an
    outlier among its own peers.

    A mean-minus-k-standard-deviations rule cannot be used here: with only a
    handful of specimens per student the sample standard deviation is small and
    the *lowest* specimen falls below the cut almost every time, so such a rule
    reports one 'mismatch' per student whatever the data says.  The modified
    z-score is built on the median and the median absolute deviation, neither of
    which is dragged by the point being tested, and 3.5 is the conventional
    cut-off."""
    outlier_relative_gap: float = 0.20
    """A flagged specimen must *also* sit this far below the cohort median, in
    relative terms.

    The modified z-score alone is hair-triggered when a cohort is very tight: if
    four specimens agree to within a hundredth, the median absolute deviation is
    almost zero and an ordinary fifth specimen scores an enormous z.  Requiring a
    material gap as well means a specimen has to be both statistically unusual
    *and* practically different before it is reported."""

    # -- presentation ------------------------------------------------------- #
    stage_dir: Path = field(default=STAGE_DIR)
    figure_dir: Path = field(default=FIGURE_DIR)
    crop_dir: Path = field(default=CROP_DIR)
    show_windows: bool = False
    window_delay_ms: int = 700
    save_stages: bool = True

    # ------------------------------------------------------------------ #
    def evolve(self, **changes) -> "Settings":
        """Return a copy of these settings with ``changes`` applied."""
        return replace(self, **changes)

    def kernel_for_horizontal_rules(self, width: int) -> tuple[int, int]:
        """Structuring element that survives only near-horizontal runs."""
        return (max(12, width // self.horizontal_scale), 1)

    def kernel_for_vertical_rules(self, height: int) -> tuple[int, int]:
        """Structuring element that survives only near-vertical runs."""
        return (1, max(12, height // self.vertical_scale))

    # ------------------------------------------------------------------ #
    #  Resolution-relative parameters
    #
    #  The neighbourhood sizes below were tuned at REFERENCE_WIDTH.  They
    #  describe a *physical* size on the page - "wider than a pen stroke",
    #  "about one character tall" - so they have to grow with the working
    #  resolution.  Leaving them fixed in pixels makes the pipeline silently
    #  resolution-dependent: at twice the width a 31 px adaptive window is only
    #  half a character wide, thick printed rules binarise as hollow outlines,
    #  and the rule masks fall apart.
    # ------------------------------------------------------------------ #

    REFERENCE_WIDTH: int = 1700

    def _scaled_odd(self, value: int, width: int, minimum: int) -> int:
        scaled = int(round(value * width / float(self.REFERENCE_WIDTH)))
        return max(minimum, scaled | 1)

    def adaptive_block_for(self, width: int) -> int:
        return self._scaled_odd(self.adaptive_block, width, 11)

    def background_kernel_for(self, width: int) -> int:
        return self._scaled_odd(self.background_kernel, width, 15)

    def rule_separation_for(self, width: int) -> int:
        return max(6, int(round(self.min_rule_separation * width / float(self.REFERENCE_WIDTH))))


DEFAULT_SETTINGS = Settings()
