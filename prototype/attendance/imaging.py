"""Low-level image-processing primitives used by the SAMS pipeline.

The functions in this module are deliberately pure: they take an image, they
return a new image, and they never mutate their argument.  Keeping them free of
side effects makes them straightforward to unit-test and lets the pipeline
record every intermediate result for the report.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, Sequence

import cv2
import numpy as np

from .config import Settings

# --------------------------------------------------------------------------- #
#  I/O helpers
# --------------------------------------------------------------------------- #


def imread_unicode(path: str | Path) -> np.ndarray:
    """Read an image, tolerating non-ASCII and space-bearing Windows paths.

    ``cv2.imread`` delegates to the platform ``fopen`` and silently returns
    ``None`` for paths it cannot encode.  Decoding from a NumPy buffer avoids the
    problem entirely.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"image not found: {path}")
    buffer = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"'{path}' is not a readable image file")
    return image


def imwrite_unicode(path: str | Path, image: np.ndarray) -> Path:
    """Write an image through a NumPy buffer (counterpart of :func:`imread_unicode`)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    success, encoded = cv2.imencode(path.suffix or ".png", image)
    if not success:
        raise ValueError(f"could not encode image for '{path}'")
    encoded.tofile(str(path))
    return path


# --------------------------------------------------------------------------- #
#  Geometry
# --------------------------------------------------------------------------- #


def resize_to_width(image: np.ndarray, width: int) -> tuple[np.ndarray, float]:
    """Scale ``image`` so that it is ``width`` pixels wide.

    Returns the resized image together with the scale factor, so that any
    geometry measured on the working image can be mapped back onto the original
    photograph.
    """
    height, current = image.shape[:2]
    if current == width:
        return image.copy(), 1.0
    scale = width / float(current)
    interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
    resized = cv2.resize(image, (width, int(round(height * scale))), interpolation=interpolation)
    return resized, scale


def rotate_bound(image: np.ndarray, angle_degrees: float, border: int = 255) -> np.ndarray:
    """Rotate about the centre while growing the canvas so nothing is clipped."""
    height, width = image.shape[:2]
    centre = (width / 2.0, height / 2.0)
    matrix = cv2.getRotationMatrix2D(centre, angle_degrees, 1.0)

    cos, sin = abs(matrix[0, 0]), abs(matrix[0, 1])
    new_width = int((height * sin) + (width * cos))
    new_height = int((height * cos) + (width * sin))
    matrix[0, 2] += (new_width / 2.0) - centre[0]
    matrix[1, 2] += (new_height / 2.0) - centre[1]

    value: float | Sequence[float] = border if image.ndim == 2 else (border, border, border)
    return cv2.warpAffine(
        image,
        matrix,
        (new_width, new_height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=value,
    )


def estimate_skew(binary: np.ndarray, settings: Settings) -> float:
    """Estimate the page rotation from the long printed rules of the tables.

    The signing sheet is dominated by near-horizontal rules, so the median angle
    of the long Hough segments is a robust estimate of the skew.  Returns the
    angle in degrees; positive means the page is rotated anti-clockwise.
    """
    height, width = binary.shape[:2]
    min_length = int(width * settings.hough_min_line_ratio)
    segments = cv2.HoughLinesP(
        binary,
        rho=1,
        theta=np.pi / 720.0,
        threshold=settings.hough_threshold,
        minLineLength=min_length,
        maxLineGap=int(width * 0.02),
    )
    if segments is None or len(segments) == 0:
        return 0.0

    # OpenCV 4.x returns (N, 1, 4); OpenCV 5.x returns (N, 4).  Normalise both.
    segments = np.asarray(segments).reshape(-1, 4)

    angles: list[float] = []
    for x1, y1, x2, y2 in segments:
        angle = math.degrees(math.atan2(float(y2 - y1), float(x2 - x1)))
        # Keep only segments that are *meant* to be horizontal.
        if abs(angle) <= settings.max_skew_degrees:
            angles.append(angle)

    if not angles:
        return 0.0
    return float(np.median(angles))


# --------------------------------------------------------------------------- #
#  Photometric correction and binarisation
# --------------------------------------------------------------------------- #


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """ITU-R BT.601 luma conversion (the standard OpenCV weighting)."""
    if image.ndim == 2:
        return image.copy()
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def flatten_illumination(gray: np.ndarray, settings: Settings) -> np.ndarray:
    """Remove the shading gradient introduced by hand-held phone photography.

    A morphological *closing* with a kernel wider than any glyph keeps only the
    paper, which is an estimate ``B`` of the illumination field.  Dividing the
    original by that estimate,

        ``F(x, y) = 255 * I(x, y) / B(x, y)``

    yields a flat-field image in which the paper is uniformly white regardless of
    the shadow cast by the photographer.
    """
    size = settings.background_kernel_for(gray.shape[1])
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
    background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    background = cv2.GaussianBlur(background, (0, 0), sigmaX=size / 6.0)
    flattened = cv2.divide(gray, background, scale=255)
    return flattened


def denoise(gray: np.ndarray, settings: Settings) -> np.ndarray:
    """Edge-preserving smoothing that suppresses paper texture and JPEG noise."""
    return cv2.bilateralFilter(
        gray,
        settings.bilateral_diameter,
        settings.bilateral_sigma_colour,
        settings.bilateral_sigma_space,
    )


def binarize_adaptive(gray: np.ndarray, settings: Settings) -> np.ndarray:
    """Adaptive Gaussian thresholding; ink becomes 255, paper becomes 0."""
    block = settings.adaptive_block_for(gray.shape[1])
    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        block,
        settings.adaptive_c,
    )


def binarize_otsu(gray: np.ndarray) -> tuple[np.ndarray, float]:
    """Global Otsu thresholding, kept for the comparison figure in the report."""
    threshold, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return binary, float(threshold)


def clean_binary(binary: np.ndarray) -> np.ndarray:
    """Close 1-pixel gaps in strokes and drop isolated specks."""
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    return cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel, iterations=1)


# --------------------------------------------------------------------------- #
#  Colour analysis (students sign with different coloured pens)
# --------------------------------------------------------------------------- #


def chromatic_ink_mask(bgr: np.ndarray) -> np.ndarray:
    """Isolate *coloured* ink (blue/black/red pens) from the printed sheet.

    Printed text on the form is neutral black on white; ball-point ink is almost
    always chromatic.  Working in HSV, any pixel that is both reasonably
    saturated and not too bright is a strong pen-ink candidate.  The mask is used
    as supporting evidence, never on its own, because black pens are achromatic.
    """
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    mask = ((saturation > 60) & (value < 220)).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)


def dominant_ink_colour(bgr: np.ndarray, mask: np.ndarray) -> tuple[int, int, int]:
    """Mean BGR of the pixels selected by ``mask`` (used to label pen colour)."""
    if cv2.countNonZero(mask) == 0:
        return (0, 0, 0)
    mean = cv2.mean(bgr, mask=mask)[:3]
    return tuple(int(round(channel)) for channel in mean)  # type: ignore[return-value]


def describe_pen_colour(bgr_colour: tuple[int, int, int]) -> str:
    """Map a mean BGR triple onto a human-readable pen colour name."""
    blue, green, red = bgr_colour
    if max(bgr_colour) < 90:
        return "black"
    if blue > red + 25 and blue > green + 15:
        return "blue"
    if red > blue + 30 and red > green + 20:
        return "red"
    if green > blue + 25 and green > red + 15:
        return "green"
    return "dark"


# --------------------------------------------------------------------------- #
#  Presentation helpers
# --------------------------------------------------------------------------- #


def as_bgr(image: np.ndarray) -> np.ndarray:
    """Promote a single-channel image to three channels for annotation."""
    if image.ndim == 3:
        return image.copy()
    return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)


def label(image: np.ndarray, text: str) -> np.ndarray:
    """Draw a caption bar across the top of a copy of ``image``."""
    canvas = as_bgr(image)
    height, width = canvas.shape[:2]
    bar = max(26, height // 22)
    cv2.rectangle(canvas, (0, 0), (width, bar), (32, 32, 32), thickness=-1)
    scale = max(0.45, bar / 40.0)
    cv2.putText(
        canvas,
        text,
        (8, int(bar * 0.72)),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    return canvas


def montage(images: Iterable[np.ndarray], columns: int = 3, tile_width: int = 460) -> np.ndarray:
    """Tile labelled stage images into a single contact sheet."""
    tiles: list[np.ndarray] = []
    for image in images:
        tile, _ = resize_to_width(as_bgr(image), tile_width)
        tiles.append(tile)
    if not tiles:
        return np.zeros((10, 10, 3), np.uint8)

    tile_height = max(tile.shape[0] for tile in tiles)
    padded = []
    for tile in tiles:
        pad = tile_height - tile.shape[0]
        padded.append(cv2.copyMakeBorder(tile, 0, pad, 0, 0, cv2.BORDER_CONSTANT, value=(24, 24, 24)))

    rows = []
    for start in range(0, len(padded), columns):
        chunk = padded[start : start + columns]
        while len(chunk) < columns:
            chunk.append(np.full_like(padded[0], 24))
        rows.append(np.hstack(chunk))
    return np.vstack(rows)
