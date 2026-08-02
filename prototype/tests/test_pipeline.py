"""End-to-end tests: the pipeline, the CLI helpers, and the five real sheets."""

from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from support import PROJECT_ROOT, SHEET_DIR, reference_sheets_available, synthetic_sheet  # noqa: F401

from attendance.config import DEFAULT_SETTINGS
from attendance.database import AttendanceRepository
from attendance.imaging import imwrite_unicode
from attendance.pipeline import AttendancePipeline, format_table, infer_session_date
from attendance.progress import ConsoleReporter, NullReporter, StageArtifact, StageWriter
from attendance.records import load_roster

INFO_XML = PROJECT_ROOT / "data" / "info.xml"
GROUND_TRUTH = PROJECT_ROOT / "data" / "ground_truth.csv"


class SessionDateTests(unittest.TestCase):
    """The brief names sheets after the session: ``sams.py 10.07.2019.png``."""

    def test_day_first_dotted(self):
        self.assertEqual(infer_session_date(Path("10.07.2019.png")), date(2019, 7, 10))

    def test_iso_style(self):
        self.assertEqual(infer_session_date(Path("2019-07-10.jpeg")), date(2019, 7, 10))

    def test_underscores_and_hyphens(self):
        self.assertEqual(infer_session_date(Path("05_07_2019.jpg")), date(2019, 7, 5))
        self.assertEqual(infer_session_date(Path("28-06-2019.jpg")), date(2019, 6, 28))

    def test_a_name_with_no_date_falls_back_to_the_file_time(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scan.png"
            path.write_bytes(b"x")
            self.assertIsInstance(infer_session_date(path), date)

    def test_an_impossible_date_is_not_accepted(self):
        # 32 is not a day, so the pattern must be rejected rather than crash.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "32.13.2019.png"
            path.write_bytes(b"x")
            self.assertIsInstance(infer_session_date(path), date)


class FormatTableTests(unittest.TestCase):
    def test_columns_are_padded_to_a_common_width(self):
        rendered = format_table([["a", "bbbb"], ["cccc", "d"]]).splitlines()
        self.assertEqual(len(rendered), 3)          # header, rule, one row
        self.assertTrue(set(rendered[1]) == {"-"})

    def test_empty_input(self):
        self.assertEqual(format_table([]), "")


class ProgressTests(unittest.TestCase):
    def test_stage_writer_saves_every_stage_and_a_contact_sheet(self):
        import numpy as np

        with tempfile.TemporaryDirectory() as directory:
            writer = StageWriter(Path(directory), "sheet")
            artifacts = [
                StageArtifact(order=index, name=f"Stage {index}", description="", image=np.zeros((40, 60, 3), np.uint8))
                for index in (1, 2)
            ]
            for artifact in artifacts:
                writer.stage_finished(artifact)
            writer.end(artifacts)
            written = sorted(path.name for path in (Path(directory) / "sheet").glob("*.png"))
            self.assertIn("00_pipeline_contact_sheet.png", written)
            self.assertEqual(len(written), 3)

    def test_a_stage_with_no_image_is_skipped_silently(self):
        with tempfile.TemporaryDirectory() as directory:
            writer = StageWriter(Path(directory), "sheet")
            writer.stage_finished(StageArtifact(order=1, name="none", description="", image=None))
            self.assertEqual(list((Path(directory) / "sheet").glob("*.png")), [])

    def test_console_reporter_writes_a_line_per_stage(self):
        lines: list[str] = []

        class Capture:
            def write(self, text):
                lines.append(text)

        reporter = ConsoleReporter(2, stream=Capture())
        reporter.begin("t")
        reporter.stage_started(1, "One", "does a thing")
        reporter.stage_finished(StageArtifact(order=1, name="One", description="", elapsed_ms=1.0))
        reporter.end([])
        self.assertTrue(any("One" in line for line in lines))
        self.assertTrue(any("complete" in line for line in lines))


class SyntheticPipelineTests(unittest.TestCase):
    """The whole pipeline, on a sheet whose answer is known by construction."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        image, self.expected = synthetic_sheet(signed_rows=(0, 2, 3, 5))
        self.sheet = imwrite_unicode(self.root / "01.02.2020.png", image)
        (self.root / "info.xml").write_text(
            "<nsbm><subject><code>CS402.3</code></subject><students><batch id='t'>"
            + "".join(
                f"<student><index>2000000{index}</index><name>Student {index + 1}</name></student>"
                for index in range(6)
            )
            + "</batch></students></nsbm>",
            encoding="utf-8",
        )
        self.roster = load_roster(self.root / "info.xml")
        self.settings = DEFAULT_SETTINGS.evolve(save_stages=False, show_windows=False)

    def tearDown(self):
        self.directory.cleanup()

    def test_the_pipeline_reproduces_the_drawn_attendance(self):
        pipeline = AttendancePipeline(self.settings, self.roster, NullReporter())
        result = pipeline.process(self.sheet)
        signed = {self.roster[index].index_no for index in self.expected["signed_rows"]}
        present = {outcome.student.index_no for outcome in result.outcomes if outcome.present}
        self.assertEqual(present, signed)
        self.assertEqual(result.warnings, [])

    def test_the_session_date_comes_from_the_file_name(self):
        result = AttendancePipeline(self.settings, self.roster, NullReporter()).process(self.sheet)
        self.assertEqual(result.session_date, date(2020, 2, 1))

    def test_every_stage_produces_a_timed_artifact(self):
        result = AttendancePipeline(self.settings, self.roster, NullReporter()).process(self.sheet)
        self.assertEqual(len(result.artifacts), 9)
        self.assertTrue(all(artifact.elapsed_ms >= 0 for artifact in result.artifacts))
        self.assertTrue(all(artifact.image is not None for artifact in result.artifacts))

    def test_persisting_twice_does_not_duplicate_records(self):
        pipeline = AttendancePipeline(self.settings, self.roster, NullReporter())
        result = pipeline.process(self.sheet)
        with AttendanceRepository(self.root / "a.db") as repository:
            first = pipeline.persist(result, repository)
            second = pipeline.persist(result, repository)
            self.assertEqual(first, second)
            self.assertEqual(len(repository.all_attendance()), len(self.roster))

    def test_a_roster_longer_than_the_sheet_is_reported_not_hidden(self):
        (self.root / "long.xml").write_text(
            "<nsbm><students><batch id='t'>"
            + "".join(f"<student><index>300000{i}</index><name>S{i}</name></student>" for i in range(9))
            + "</batch></students></nsbm>",
            encoding="utf-8",
        )
        roster = load_roster(self.root / "long.xml")
        result = AttendancePipeline(self.settings, roster, NullReporter()).process(self.sheet)
        self.assertTrue(result.warnings)
        self.assertIn("6 data rows", result.warnings[0])


@unittest.skipUnless(reference_sheets_available(), "the five reference photographs are not present")
class ReferenceSheetTests(unittest.TestCase):
    """The five supplied photographs, against the hand-labelled ground truth."""

    @classmethod
    def setUpClass(cls):
        cls.roster = load_roster(INFO_XML)
        cls.settings = DEFAULT_SETTINGS.evolve(save_stages=False, show_windows=False)
        cls.truth: dict[tuple[str, str], str] = {}
        with GROUND_TRUTH.open(encoding="utf-8", newline="") as handle:
            for record in csv.DictReader(handle):
                cls.truth[(record["sheet"].strip(), record["index_no"].strip())] = record["status"].strip()

        cls.results = {}
        for sheet in sorted(SHEET_DIR.glob("*.jpeg")):
            pipeline = AttendancePipeline(cls.settings, cls.roster, NullReporter())
            cls.results[sheet.name] = pipeline.process(sheet)

    def test_all_five_sheets_were_processed(self):
        self.assertEqual(len(self.results), 5)

    def test_every_sheet_yields_one_row_per_student(self):
        for name, result in self.results.items():
            with self.subTest(sheet=name):
                self.assertEqual(len(result.outcomes), len(self.roster))
                self.assertEqual(result.warnings, [])

    def test_every_cell_matches_the_ground_truth(self):
        for name, result in self.results.items():
            for outcome in result.outcomes:
                expected = self.truth[(name, outcome.student.index_no)]
                with self.subTest(sheet=name, student=outcome.student.index_no):
                    self.assertEqual(outcome.status, expected)

    def test_signed_and_unsigned_cells_are_separated_by_a_wide_margin(self):
        signed, unsigned = [], []
        for name, result in self.results.items():
            for outcome in result.outcomes:
                ratio = outcome.verdict.features.ink_ratio
                (signed if self.truth[(name, outcome.student.index_no)] == "PRESENT" else unsigned).append(ratio)
        self.assertGreater(min(signed), max(unsigned) * 3.0)
        self.assertGreater(min(signed), DEFAULT_SETTINGS.min_ink_ratio * 2.0)
        self.assertLess(max(unsigned), DEFAULT_SETTINGS.min_ink_ratio)

    def test_the_detected_grid_is_uniform_on_every_sheet(self):
        for name, result in self.results.items():
            with self.subTest(sheet=name):
                self.assertLess(result.context.detection.roster.uniformity(), 0.12)

    def test_skew_is_detected_and_stays_within_the_plausible_range(self):
        for name, result in self.results.items():
            with self.subTest(sheet=name):
                self.assertLess(abs(result.context.skew_degrees), DEFAULT_SETTINGS.max_skew_degrees)

    def test_every_present_row_stores_a_usable_specimen(self):
        for result in self.results.values():
            for outcome in result.outcomes:
                if outcome.present:
                    self.assertIsNotNone(outcome.verdict.crop)
                    self.assertGreater(outcome.verdict.crop.size, 0)


if __name__ == "__main__":
    unittest.main()
