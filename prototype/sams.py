#!/usr/bin/env python3
"""sams.py - Student Attendance Management System (image-processing front end).

Reads a photograph of a signing sheet together with the ``info.xml`` roster,
shows the progress of the image processing, decides who signed, and stores the
result in a local SQLite database.

Usage
-----
    python sams.py 31.05.2019.jpeg info.xml
    python sams.py data/sheets/*.jpeg info.xml --show
    python sams.py sheet.jpg info.xml --date 2019-07-05 --db data/attendance.db

CS402.3 Computer Graphics and Visualization - coursework prototype.
"""

from __future__ import annotations

import argparse
import glob
import sys
from datetime import date, datetime
from pathlib import Path

from attendance.config import CROP_DIR, DEFAULT_DATABASE, DEFAULT_INFO_XML, DEFAULT_SETTINGS, Settings
from attendance.database import AttendanceRepository
from attendance.pipeline import AttendancePipeline, PipelineError, SessionResult, format_table
from attendance.records import RosterError, load_roster
from attendance.table import TableDetectionError


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sams.py",
        description="Process signing-sheet photographs into attendance records.",
        epilog="Example:  python sams.py data/sheets/31.05.2019.jpeg data/info.xml --show",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        metavar="IMAGE [IMAGE ...] [INFO.XML]",
        help="signing-sheet photograph(s) followed by the roster XML; wildcards are expanded",
    )
    parser.add_argument("--db", default=str(DEFAULT_DATABASE), help="SQLite database file")
    parser.add_argument("--date", help="session date as YYYY-MM-DD (default: read from the file name)")
    parser.add_argument("--show", action="store_true", help="display each processing stage in a window")
    parser.add_argument("--delay", type=int, default=700, help="milliseconds each stage window is held")
    parser.add_argument("--no-stages", action="store_true", help="do not write stage images to output/stages")
    parser.add_argument("--save-crops", action="store_true", help="also export every signature cell as a PNG")
    parser.add_argument("--width", type=int, default=DEFAULT_SETTINGS.working_width, help="working resolution")
    parser.add_argument(
        "--ink-threshold",
        type=float,
        default=DEFAULT_SETTINGS.min_ink_ratio,
        help="minimum fraction of a signature cell that must be ink for PRESENT",
    )
    parser.add_argument("--dry-run", action="store_true", help="process but do not write to the database")
    return parser


def split_arguments(paths: list[str]) -> tuple[list[Path], str]:
    """Separate the image operands from the roster file.

    The brief's invocation is ``python sams.py 10.07.2019.png info.xml``, so the
    roster is simply the trailing ``.xml`` operand; everything before it is an
    image (or a wildcard standing for several).
    """
    operands = list(paths)
    info = str(DEFAULT_INFO_XML)
    if operands and operands[-1].lower().endswith(".xml"):
        info = operands.pop()
    return expand_images(operands), info


def expand_images(patterns: list[str]) -> list[Path]:
    """Expand wildcards (the Windows shell does not do it for us) and sort."""
    paths: list[Path] = []
    for pattern in patterns:
        matches = [Path(match) for match in glob.glob(pattern)]
        if matches:
            paths.extend(sorted(matches))
        else:
            paths.append(Path(pattern))
    return paths


def settings_from_arguments(arguments: argparse.Namespace) -> Settings:
    return DEFAULT_SETTINGS.evolve(
        working_width=arguments.width,
        min_ink_ratio=arguments.ink_threshold,
        show_windows=bool(arguments.show),
        window_delay_ms=arguments.delay,
        save_stages=not arguments.no_stages,
    )


def print_result(result: SessionResult) -> None:
    print()
    print(f"Session   : {result.session_date.isoformat()}   ({result.subject_code})")
    print(f"Sheet     : {result.source.name}")
    print(f"Processing: {result.total_ms:.0f} ms over {len(result.artifacts)} stages")
    print()
    print(format_table(result.to_table()))
    print()
    print(f"PRESENT {result.present_count}/{len(result.outcomes)}   ABSENT {result.absent_count}/{len(result.outcomes)}")
    for warning in result.warnings:
        print(f"  ! {warning}")


def main(argv: list[str] | None = None) -> int:
    arguments = build_argument_parser().parse_args(argv)
    images, info_path = split_arguments(arguments.paths)

    try:
        roster = load_roster(info_path)
    except RosterError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    session_date: date | None = None
    if arguments.date:
        try:
            session_date = datetime.strptime(arguments.date, "%Y-%m-%d").date()
        except ValueError:
            print("error: --date must be formatted as YYYY-MM-DD", file=sys.stderr)
            return 2

    settings = settings_from_arguments(arguments)
    print(f"Roster    : {len(roster)} students, batch {roster.batch or 'n/a'}  <- {info_path}")
    print(f"Sheets    : {len(images)}")
    if not images:
        print("error: no signing-sheet image was given", file=sys.stderr)
        return 2

    failures = 0
    repository = None if arguments.dry_run else AttendanceRepository(arguments.db)
    try:
        for image_path in images:
            try:
                pipeline = AttendancePipeline.with_default_reporters(settings, roster, image_path)
                result = pipeline.process(image_path, session_date=session_date)
                print_result(result)

                if repository is not None:
                    session_id = pipeline.persist(result, repository)
                    print(f"Stored    : session #{session_id} in {arguments.db}")
                if arguments.save_crops:
                    written = pipeline.export_signature_crops(result, CROP_DIR)
                    print(f"Crops     : {len(written)} signature cells written to {CROP_DIR}")
                if settings.save_stages:
                    print(f"Stages    : {settings.stage_dir / image_path.stem}")
            except (FileNotFoundError, ValueError, TableDetectionError, PipelineError) as error:
                failures += 1
                print(f"error: {image_path.name}: {error}", file=sys.stderr)
    finally:
        if repository is not None:
            repository.close()

    if failures:
        print(f"\n{failures} of {len(images)} sheet(s) failed", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
