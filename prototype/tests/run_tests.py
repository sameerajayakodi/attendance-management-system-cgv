#!/usr/bin/env python3
"""Run the whole SAMS test suite and print a transcript.

    python tests/run_tests.py           # everything
    python tests/run_tests.py -q        # quiet
    python tests/run_tests.py test_records

Uses only the standard library's ``unittest``, so no test runner has to be
installed before the prototype can be marked.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent
for path in (str(PROJECT_ROOT), str(TESTS_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)


def main(argv: list[str]) -> int:
    verbosity = 1 if "-q" in argv else 2
    names = [argument for argument in argv if not argument.startswith("-")]

    loader = unittest.TestLoader()
    if names:
        suite = loader.loadTestsFromNames(names)
    else:
        suite = loader.discover(str(TESTS_DIR), pattern="test_*.py", top_level_dir=str(TESTS_DIR))

    print("=" * 78)
    print("  SAMS test suite - CS402.3 Computer Graphics and Visualization")
    print("=" * 78)
    result = unittest.TextTestRunner(verbosity=verbosity).run(suite)

    print()
    print("=" * 78)
    print(f"  ran {result.testsRun} tests   failures {len(result.failures)}   errors {len(result.errors)}   skipped {len(result.skipped)}")
    print("=" * 78)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
