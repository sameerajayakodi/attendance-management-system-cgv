"""Shared helpers for the SAMS test suite.

The image-processing tests run against a *synthetic* signing sheet rather than a
photograph, so that the expected answer is known exactly and the tests stay
deterministic.  The five real photographs are exercised separately, by the
integration test, against the hand-labelled ground truth.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data"
SHEET_DIR = DATA_DIR / "sheets"


def synthetic_sheet(
    signed_rows: tuple[int, ...] = (0, 2, 4),
    rows: int = 6,
    width: int = 1200,
    skew_degrees: float = 0.0,
    with_session_table: bool = True,
) -> tuple[np.ndarray, dict[str, object]]:
    """Draw a signing sheet with a known set of signed rows.

    ``signed_rows`` are zero-based *data* row indices.  Returns the BGR image and
    a dictionary describing what was drawn, so a test can assert against it.
    """
    height = 1500
    image = np.full((height, width, 3), 248, np.uint8)

    left, right = 120, width - 120
    columns = [left, left + 90, left + 320, left + 420, left + 760, right]

    if with_session_table:
        # A small two-row table above the roster, exactly as the real form has.
        session_top, session_bottom = 210, 310
        for y in (session_top, session_top + 50, session_bottom):
            cv2.line(image, (left, y), (right, y), (30, 30, 30), 2)
        for x in (left, left + 300, left + 700, right):
            cv2.line(image, (x, session_top), (x, session_bottom), (30, 30, 30), 2)

    top = 400
    row_height = 90
    edges = [top + index * row_height for index in range(rows + 2)]  # header + data rows

    for y in edges:
        cv2.line(image, (left, y), (right, y), (30, 30, 30), 2)
    for x in columns:
        cv2.line(image, (x, edges[0]), (x, edges[-1]), (30, 30, 30), 2)

    cv2.putText(image, "Signature", (columns[-2] + 40, edges[0] + 58), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (20, 20, 20), 2)
    for index in range(rows):
        band_top = edges[index + 1]
        cv2.putText(image, f"1000{index:04d}", (columns[1] + 12, band_top + 58), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 20), 2)
        cv2.putText(image, f"Student {index + 1}", (columns[3] + 12, band_top + 58), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 2)

    generator = np.random.default_rng(1234 + rows)
    for index in signed_rows:
        band_top = edges[index + 1]
        centre_y = band_top + row_height // 2
        start_x = columns[-2] + 40
        points = [(start_x, centre_y)]
        for step in range(1, 9):
            points.append(
                (
                    start_x + step * 24 + int(generator.integers(-6, 6)),
                    centre_y + int(generator.integers(-26, 26)),
                )
            )
        cv2.polylines(image, [np.array(points, np.int32)], False, (170, 60, 30), 4, cv2.LINE_AA)
        # A trailing underline, which real signatures nearly always have.
        cv2.line(image, (start_x - 10, centre_y + 24), (start_x + 210, centre_y + 18), (170, 60, 30), 3, cv2.LINE_AA)

    if skew_degrees:
        matrix = cv2.getRotationMatrix2D((width / 2, height / 2), skew_degrees, 1.0)
        image = cv2.warpAffine(
            image, matrix, (width, height), flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT, borderValue=(248, 248, 248),
        )

    expectation = {
        "rows": rows,
        "signed_rows": tuple(signed_rows),
        "row_edges": edges,
        "column_edges": columns,
        "skew_degrees": skew_degrees,
    }
    return image, expectation


def reference_sheets_available() -> bool:
    return SHEET_DIR.exists() and any(SHEET_DIR.glob("*.jpeg"))
