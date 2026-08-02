#!/usr/bin/env python3
"""package.py - build the two ZIP files the coursework asks to be uploaded.

    python package.py

Produces:
    prototype.zip                        the prototype (CLI + web interface)
    CS402.3_Coursework_Submission.zip    prototype.zip + the report .docx

Generated and installed artefacts (output/, __pycache__, node_modules/, dist/)
are excluded; the five reference sheets and a populated attendance database are
included so that infovis.py, investigate.py and the web interface all work
straight out of the archive.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROTOTYPE = ROOT / "prototype"
WEB = ROOT / "web"
REPORT = ROOT / "report" / "CS402.3_CGV_Coursework_Report.docx"
PROTOTYPE_ZIP = ROOT / "prototype.zip"
SUBMISSION_ZIP = ROOT / "CS402.3_Coursework_Submission.zip"

EXCLUDED_DIRS = {
    "__pycache__", "output", ".pytest_cache", ".git", ".idea", ".vscode",
    "node_modules", "dist", "uploads", ".vite",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".tsbuildinfo"}
EXCLUDED_NAMES = {"package-lock.json", ".DS_Store"}


def add_tree(archive: zipfile.ZipFile, source: Path, prefix: str) -> int:
    """Add every file under ``source`` to the archive beneath ``prefix``."""
    written = 0
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if path.name in EXCLUDED_NAMES or path.suffix in EXCLUDED_SUFFIXES or not path.is_file():
            continue
        archive.write(path, Path(prefix) / relative)
        written += 1
    return written


def build_prototype_zip() -> int:
    with zipfile.ZipFile(PROTOTYPE_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        written = add_tree(archive, PROTOTYPE, "prototype")
        if WEB.is_dir():
            written += add_tree(archive, WEB, "web")
    return written


def build_submission_zip() -> None:
    with zipfile.ZipFile(SUBMISSION_ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.write(PROTOTYPE_ZIP, PROTOTYPE_ZIP.name)
        archive.write(REPORT, REPORT.name)


def main() -> int:
    if not PROTOTYPE.is_dir():
        print(f"error: {PROTOTYPE} not found", file=sys.stderr)
        return 2
    if not REPORT.exists():
        print(f"error: {REPORT} not found - run 'node build_report.js' in report/ first", file=sys.stderr)
        return 2

    files = build_prototype_zip()
    print(f"{PROTOTYPE_ZIP.name:38s} {files:3d} files   {PROTOTYPE_ZIP.stat().st_size / 1048576:5.1f} MB")
    build_submission_zip()
    print(f"{SUBMISSION_ZIP.name:38s}   2 files   {SUBMISSION_ZIP.stat().st_size / 1048576:5.1f} MB")
    print("\nUpload CS402.3_Coursework_Submission.zip to the LMS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
