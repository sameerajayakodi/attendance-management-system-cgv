#!/usr/bin/env python3
"""tools/make_figures.py - build the figures the report needs.

Two kinds of figure are produced here:

* the **architecture diagram**, drawn from the same module list the code uses,
  so it cannot drift away from the implementation;
* **close-up crops** of individual pipeline stages, cut from the stage images
  that ``sams.py`` already wrote, so the report quotes real output rather than
  a redrawn illustration.

    python tools/make_figures.py
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from attendance.config import FIGURE_DIR, STAGE_DIR  # noqa: E402
from attendance.imaging import imread_unicode, imwrite_unicode  # noqa: E402
from attendance.visualize import Palette, apply_house_style, save_figure  # noqa: E402

REPORT_FIGURES = PROJECT_ROOT.parent / "report" / "figures"


# --------------------------------------------------------------------------- #
#  Architecture diagram
# --------------------------------------------------------------------------- #

LAYERS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Entry points",
        [
            ("sams.py", "process a sheet"),
            ("infovis.py", "visualise a student"),
            ("investigate.py", "compare signatures"),
        ],
    ),
    (
        "Orchestration",
        [
            ("pipeline.py", "run stages, map to roster"),
            ("progress.py", "console / windows / PNG"),
            ("config.py", "all tunable parameters"),
        ],
    ),
    (
        "Processing",
        [
            ("stages.py", "the nine steps"),
            ("imaging.py", "image primitives"),
            ("table.py", "grid reconstruction"),
            ("signature.py", "ink -> PRESENT/ABSENT"),
        ],
    ),
    (
        "Analysis and data",
        [
            ("records.py", "info.xml"),
            ("database.py", "SQLite"),
            ("visualize.py", "charts"),
            ("verify.py", "HOG / zoning / ORB"),
        ],
    ),
]


def architecture_diagram(out_dir: Path) -> Path:
    apply_house_style()
    figure, axes = plt.subplots(figsize=(10.6, 6.0))
    figure.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    axes.set_xlim(0, 100)
    axes.set_ylim(0, 94)
    axes.axis("off")

    band_height = 20.0
    top = 92.0
    for index, (title, modules) in enumerate(LAYERS):
        y = top - index * (band_height + 3.0)
        axes.add_patch(
            FancyBboxPatch(
                (2, y - band_height),
                96,
                band_height,
                boxstyle="round,pad=0.4,rounding_size=1.2",
                facecolor=Palette.PANEL,
                edgecolor=Palette.GRID,
                linewidth=1.0,
                zorder=1,
            )
        )
        axes.text(4.5, y - 3.6, title.upper(), fontsize=8.5, color=Palette.INK_MUTED, weight="bold", va="center")

        width = 92.0 / len(modules)
        for position, (name, caption) in enumerate(modules):
            left = 4.0 + position * width
            axes.add_patch(
                FancyBboxPatch(
                    (left, y - band_height + 3.0),
                    width - 3.0,
                    band_height - 10.0,
                    boxstyle="round,pad=0.3,rounding_size=1.0",
                    facecolor=Palette.SURFACE,
                    edgecolor=Palette.SERIES[index % len(Palette.SERIES)],
                    linewidth=1.6,
                    zorder=2,
                )
            )
            centre = left + (width - 3.0) / 2.0
            axes.text(
                centre,
                y - band_height + 9.4,
                name,
                fontsize=10,
                weight="bold",
                color=Palette.INK,
                ha="center",
                va="center",
                zorder=3,
            )
            axes.text(
                centre,
                y - band_height + 5.6,
                caption,
                fontsize=7.8,
                color=Palette.INK_SECONDARY,
                ha="center",
                va="center",
                zorder=3,
            )

        if index < len(LAYERS) - 1:
            axes.add_patch(
                FancyArrowPatch(
                    (50, y - band_height - 0.2),
                    (50, y - band_height - 2.8),
                    arrowstyle="-|>",
                    mutation_scale=13,
                    color=Palette.INK_MUTED,
                    linewidth=1.2,
                    zorder=4,
                )
            )

    axes.text(
        50,
        1.5,
        "each layer depends only on the layer below it",
        fontsize=8.5,
        color=Palette.INK_MUTED,
        ha="center",
    )
    return save_figure(figure, out_dir / "architecture.png")


# --------------------------------------------------------------------------- #
#  Ownership illustration
# --------------------------------------------------------------------------- #


def ownership_diagram(out_dir: Path) -> Path:
    """Why a signature is charged to a row by mass rather than by containment."""
    apply_house_style()
    figure, axes = plt.subplots(figsize=(9.0, 3.9))

    rows = [("row 2  (10009301)", 1), ("row 3  (10009302)", 0)]
    for label, y in rows:
        axes.add_patch(plt.Rectangle((0, y), 10, 1, facecolor=Palette.SURFACE, edgecolor=Palette.AXIS, linewidth=1.4))
        axes.text(-0.25, y + 0.5, label, ha="right", va="center", fontsize=9.5, color=Palette.INK_SECONDARY)

    # A stroke that starts in row 3 and reaches up into row 2.
    curve_x = np.linspace(1.2, 8.6, 300)
    curve_y = 0.28 + 1.25 * np.exp(-((curve_x - 3.1) ** 2) / 0.55) + 0.05 * np.sin(curve_x * 2.2)
    axes.plot(curve_x, np.clip(curve_y, 0.05, 1.85), color=Palette.SERIES[0], linewidth=3.4, solid_capstyle="round", zorder=3)
    axes.plot([1.0, 9.0], [0.44, 0.40], color=Palette.SERIES[0], linewidth=2.2, zorder=3)

    axes.annotate(
        "18 % of the stroke's pixels\nsit in row 2",
        xy=(3.1, 1.35),
        xytext=(5.4, 1.62),
        fontsize=8.8,
        color=Palette.INK_SECONDARY,
        arrowprops=dict(arrowstyle="->", color=Palette.INK_MUTED, linewidth=1.0),
    )
    axes.annotate(
        "82 % sit in row 3, so the whole\nstroke is charged to row 3",
        xy=(6.4, 0.42),
        xytext=(4.4, -0.42),
        fontsize=8.8,
        color=Palette.INK,
        arrowprops=dict(arrowstyle="->", color=Palette.INK_MUTED, linewidth=1.0),
    )

    axes.set_xlim(-3.2, 10.4)
    axes.set_ylim(-0.75, 2.15)
    axes.axis("off")
    axes.set_title("Row ownership is decided by pixel mass, not by containment", loc="left")
    figure.tight_layout()
    return save_figure(figure, out_dir / "row_ownership.png")


# --------------------------------------------------------------------------- #
#  Stage close-ups
# --------------------------------------------------------------------------- #


def stage_closeups(sheet: str, out_dir: Path) -> list[Path]:
    """Crop the roster table out of selected stage images."""
    source = STAGE_DIR / sheet
    if not source.exists():
        print(f"(no stage images for {sheet}; run sams.py first)")
        return []

    written: list[Path] = []
    wanted = {
        "05_binarisation.png": "closeup_binarisation.png",
        "07_rule_extraction.png": "closeup_rules.png",
        "08_table_reconstruction.png": "closeup_table.png",
        "09_signature_analysis.png": "closeup_decision.png",
    }
    for name, target in wanted.items():
        path = source / name
        if not path.exists():
            continue
        image = imread_unicode(path)
        height, width = image.shape[:2]
        # The roster table occupies roughly the middle-left of every sheet.
        crop = image[int(height * 0.345) : int(height * 0.53), int(width * 0.03) : int(width * 0.90)]
        written.append(imwrite_unicode(out_dir / target, crop))
    return written


# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="make_figures.py", description="Build the report's figures.")
    parser.add_argument("--sheet", default="28.06.2019", help="which processed sheet to crop close-ups from")
    parser.add_argument("--out", default=str(FIGURE_DIR))
    parser.add_argument("--copy-to-report", action="store_true", help="also copy every figure into ../report/figures")
    arguments = parser.parse_args(argv)

    out_dir = Path(arguments.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"architecture : {architecture_diagram(out_dir)}")
    print(f"ownership    : {ownership_diagram(out_dir)}")
    for path in stage_closeups(arguments.sheet, out_dir):
        print(f"close-up     : {path}")

    if arguments.copy_to_report:
        REPORT_FIGURES.mkdir(parents=True, exist_ok=True)
        copied = 0
        for path in sorted(out_dir.glob("*.png")):
            shutil.copy2(path, REPORT_FIGURES / path.name)
            copied += 1
        contact = STAGE_DIR / arguments.sheet / "00_pipeline_contact_sheet.png"
        if contact.exists():
            shutil.copy2(contact, REPORT_FIGURES / "pipeline_contact_sheet.png")
            copied += 1
        print(f"copied {copied} figures to {REPORT_FIGURES}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
