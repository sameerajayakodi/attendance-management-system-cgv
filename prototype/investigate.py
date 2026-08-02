#!/usr/bin/env python3
"""investigate.py - signature recognition and mismatch reporting.

Collects every signature specimen recorded for a student, compares them with one
another using HOG and ORB descriptors, and reports any specimen that does not
match the rest - the case the brief describes as a signature that is "not
matching", i.e. a possible proxy signing.

Usage
-----
    python investigate.py 10000409
    python investigate.py 9301 --save-only
    python investigate.py --all

CS402.3 Computer Graphics and Visualization - coursework prototype.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from attendance.config import DEFAULT_DATABASE, DEFAULT_SETTINGS, FIGURE_DIR
from attendance.database import AttendanceRepository
from attendance.imaging import imwrite_unicode
from attendance.verify import SignatureVerifier, VerificationReport
from attendance.visualize import SimilarityMatrixPlot, save_figure, show


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="investigate.py",
        description="Compare a student's signature specimens and report mismatches.",
        epilog="Example:  python investigate.py 10009301",
    )
    parser.add_argument("index", nargs="?", help="student index (full or the trailing digits)")
    parser.add_argument("--all", dest="everyone", action="store_true", help="investigate every student")
    parser.add_argument("--db", default=str(DEFAULT_DATABASE), help="SQLite database file")
    parser.add_argument("--out", default=str(FIGURE_DIR), help="directory for the rendered figures")
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_SETTINGS.mismatch_threshold,
        help="absolute similarity below which a specimen is reported",
    )
    parser.add_argument("--save-only", action="store_true", help="write figures without opening a window")
    return parser


def print_report(report: VerificationReport, name: str) -> None:
    print()
    print("=" * 78)
    print(f"  Signature investigation   {name}   ({report.index_no})")
    print("=" * 78)

    if len(report.specimens) < 2:
        print(f"  only {len(report.specimens)} specimen on record - nothing to compare against")
        return

    print(f"  {'specimen':<14}{'ink':>8}{'aspect':>9}{'key pts':>9}{'mean sim':>11}{'mod. z':>9}   verdict")
    print("  " + "-" * 82)
    for position, specimen in enumerate(report.specimens):
        print(
            f"  {specimen.label:<14}{specimen.ink_ratio:>8.3f}{specimen.aspect:>9.2f}"
            f"{len(specimen.keypoints):>9}{report.mean_similarity[position]:>11.3f}"
            f"{report.modified_z[position]:>9.2f}   {report.verdict_for(position)}"
        )

    print("  " + "-" * 82)
    print(
        f"  cohort mean {report.cohort_mean:.3f}   sd {report.cohort_sd:.3f}   "
        f"absolute floor {report.threshold:.3f}"
    )
    print()
    print("  pairwise similarity")
    header = "".join(f"{specimen.label[-5:]:>9}" for specimen in report.specimens)
    print(f"  {'':<12}{header}")
    for position, specimen in enumerate(report.specimens):
        row = "".join(f"{value:>9.3f}" for value in report.similarity[position])
        print(f"  {specimen.label[-10:]:<12}{row}")
    print()
    print(f"  RESULT: {report.summary()}")


def investigate(
    repository: AttendanceRepository,
    verifier: SignatureVerifier,
    index_no: str,
    out_dir: Path,
) -> VerificationReport | None:
    specimens = repository.signature_specimens(index_no)
    if not specimens:
        print(f"error: no signature specimens stored for {index_no}", file=sys.stderr)
        return None

    report = verifier.verify(index_no, specimens)
    print_report(report, repository.student_name(index_no))

    out_dir = Path(out_dir)
    imwrite_unicode(out_dir / f"signatures_{index_no}.png", SignatureVerifier.contact_sheet(report))
    imwrite_unicode(out_dir / f"signatures_{index_no}_normalised.png", SignatureVerifier.normalised_sheet(report))
    print(f"\n  figures: {out_dir / f'signatures_{index_no}.png'}")
    return report


def main(argv: list[str] | None = None) -> int:
    arguments = build_argument_parser().parse_args(argv)

    database = Path(arguments.db)
    if not database.exists():
        print(f"error: no attendance database at '{database}' - run sams.py first", file=sys.stderr)
        return 2

    settings = DEFAULT_SETTINGS.evolve(mismatch_threshold=arguments.threshold)
    verifier = SignatureVerifier(settings)
    out_dir = Path(arguments.out)

    with AttendanceRepository(database) as repository:
        if arguments.everyone:
            flagged_students = []
            for student in repository.students():
                report = investigate(repository, verifier, student.index_no, out_dir)
                if report is not None and not report.consistent:
                    flagged_students.append(student.index_no)
            print()
            print("=" * 78)
            if flagged_students:
                print(f"  {len(flagged_students)} student(s) need manual review: {', '.join(flagged_students)}")
            else:
                print("  every student's specimens are mutually consistent")
            return 0

        if not arguments.index:
            print("error: give a student index, or use --all", file=sys.stderr)
            return 2

        candidates = repository.resolve_index(arguments.index)
        if len(candidates) != 1:
            detail = ", ".join(candidates) if candidates else "no match"
            print(f"error: '{arguments.index}' does not identify one student ({detail})", file=sys.stderr)
            return 2

        index_no = candidates[0]
        report = investigate(repository, verifier, index_no, out_dir)
        if report is None:
            return 2

        if len(report.specimens) >= 2:
            labels = [specimen.label for specimen in report.specimens]
            figure = SimilarityMatrixPlot(report.similarity, labels, report.flagged).build(
                f"Pairwise signature similarity  -  {repository.student_name(index_no)}"
            )
            path = save_figure(figure, out_dir / f"similarity_{index_no}.png")
            print(f"  figures: {path}")
            if not arguments.save_only:
                show(figure)

        return 0 if report.consistent else 1


if __name__ == "__main__":
    raise SystemExit(main())
