#!/usr/bin/env python3
"""infovis.py - attendance visualisation for a given student.

Reads the attendance database produced by ``sams.py`` and draws a summary of a
student's attendance using the data-visualisation techniques covered in CS402.3.

Usage
-----
    python infovis.py 10000409
    python infovis.py 0409                # a trailing part of an index also works
    python infovis.py 10000409 --save-only
    python infovis.py --class             # whole-batch attendance matrix

CS402.3 Computer Graphics and Visualization - coursework prototype.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from attendance.config import DEFAULT_DATABASE, DEFAULT_SETTINGS, FIGURE_DIR
from attendance.database import AttendanceRepository
from attendance.visualize import ClassHeatmap, StudentDashboard, StudentSummary, save_figure, show


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="infovis.py",
        description="Visualise the attendance of one student, or of the whole batch.",
        epilog="Example:  python infovis.py 10000409",
    )
    parser.add_argument("index", nargs="?", help="student index (full or the trailing digits)")
    parser.add_argument("--db", default=str(DEFAULT_DATABASE), help="SQLite database file")
    parser.add_argument("--out", default=str(FIGURE_DIR), help="directory for the rendered PNG")
    parser.add_argument("--class", dest="whole_class", action="store_true", help="draw the batch attendance matrix")
    parser.add_argument("--save-only", action="store_true", help="write the PNG without opening a window")
    parser.add_argument("--dpi", type=int, default=200, help="output resolution")
    return parser


def print_history(repository: AttendanceRepository, index_no: str) -> None:
    history = repository.history(index_no)
    print(f"\n{repository.student_name(index_no)}   ({index_no})")
    print(f"{'date':<12}{'status':<10}{'ink %':>8}{'conf.':>8}   sheet")
    print("-" * 74)
    for row in history:
        print(
            f"{row.session_date:<12}{row.status:<10}{row.ink_ratio * 100:>8.2f}"
            f"{row.confidence:>8.2f}   {Path(row.source_image).name}"
        )
    present = sum(1 for row in history if row.present)
    total = len(history)
    rate = present / total * 100 if total else 0.0
    print("-" * 74)
    print(f"{'total':<12}{present}/{total} present{'':<4}{rate:>7.1f}%")


def main(argv: list[str] | None = None) -> int:
    arguments = build_argument_parser().parse_args(argv)

    database = Path(arguments.db)
    if not database.exists():
        print(f"error: no attendance database at '{database}' - run sams.py first", file=sys.stderr)
        return 2

    with AttendanceRepository(database) as repository:
        if arguments.whole_class:
            figure = ClassHeatmap(repository.all_attendance()).build()
            path = save_figure(figure, Path(arguments.out) / "attendance_matrix.png", arguments.dpi)
            print(f"Saved: {path}")
            if not arguments.save_only:
                show(figure)
            return 0

        if not arguments.index:
            print("error: give a student index, or use --class", file=sys.stderr)
            return 2

        candidates = repository.resolve_index(arguments.index)
        if not candidates:
            known = ", ".join(student.index_no for student in repository.students())
            print(f"error: '{arguments.index}' matches no student. Known indices: {known}", file=sys.stderr)
            return 2
        if len(candidates) > 1:
            print(f"error: '{arguments.index}' is ambiguous: {', '.join(candidates)}", file=sys.stderr)
            return 2

        index_no = candidates[0]
        summary = StudentSummary.load(repository, index_no)
        if not summary.history:
            print(f"error: no sessions recorded for {index_no}", file=sys.stderr)
            return 2

        print_history(repository, index_no)
        figure = StudentDashboard(summary, ink_threshold=DEFAULT_SETTINGS.min_ink_ratio).build()
        path = save_figure(figure, Path(arguments.out) / f"attendance_{index_no}.png", arguments.dpi)
        print(f"\nSaved: {path}")
        if not arguments.save_only:
            show(figure)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
