"""Tests for the SQLite persistence layer (attendance.database)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from support import PROJECT_ROOT  # noqa: F401

from attendance.database import AttendanceRepository, summarise
from attendance.records import Student


def specimen(value: int = 200) -> np.ndarray:
    image = np.full((40, 90, 3), 250, np.uint8)
    image[10:30, 10:80] = value
    return image


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        self.repository = AttendanceRepository(Path(self._directory.name) / "test.db")
        self.students = [
            Student("10000001", "Alpha One", "Ms", "2016.1"),
            Student("10000002", "Beta Two", "Mr", "2016.1"),
        ]
        self.repository.upsert_students(self.students)

    def tearDown(self):
        self.repository.close()
        self._directory.cleanup()

    # -- students ------------------------------------------------------- #

    def test_students_round_trip(self):
        stored = self.repository.students()
        self.assertEqual([student.index_no for student in stored], ["10000001", "10000002"])
        self.assertEqual(stored[0].title, "Ms")

    def test_upserting_a_student_updates_rather_than_duplicates(self):
        self.repository.upsert_students([Student("10000001", "Alpha Renamed", "Ms", "2016.1")])
        stored = self.repository.students()
        self.assertEqual(len(stored), 2)
        self.assertEqual(stored[0].name, "Alpha Renamed")

    # -- sessions ------------------------------------------------------- #

    def test_reprocessing_the_same_sheet_reuses_its_session(self):
        first = self.repository.upsert_session("CS402.3", "2019-05-31", "a.jpeg")
        second = self.repository.upsert_session("CS402.3", "2019-05-31", "a-rescanned.jpeg")
        self.assertEqual(first, second)
        self.assertEqual(len(self.repository.sessions()), 1)
        self.assertEqual(self.repository.sessions()[0]["source_image"], "a-rescanned.jpeg")

    def test_different_dates_are_different_sessions(self):
        self.repository.upsert_session("CS402.3", "2019-05-31", "a.jpeg")
        self.repository.upsert_session("CS402.3", "2019-06-21", "b.jpeg")
        self.assertEqual(len(self.repository.sessions()), 2)

    # -- attendance ----------------------------------------------------- #

    def _record(self, date: str, index_no: str, status: str, ratio: float = 0.1, image=None):
        session = self.repository.upsert_session("CS402.3", date, f"{date}.jpeg")
        return self.repository.record_attendance(
            session_id=session,
            index_no=index_no,
            row_no=1,
            status=status,
            confidence=0.9,
            ink_ratio=ratio,
            ink_pixels=int(ratio * 10000),
            components=2,
            pen_colour="blue",
            signature=image,
            ink_mask=None if image is None else np.full(image.shape[:2], 255, np.uint8),
        )

    def test_attendance_history_is_ordered_by_date(self):
        self._record("2019-06-21", "10000001", "PRESENT")
        self._record("2019-05-31", "10000001", "ABSENT")
        history = self.repository.history("10000001")
        self.assertEqual([row.session_date for row in history], ["2019-05-31", "2019-06-21"])
        self.assertFalse(history[0].present)
        self.assertTrue(history[1].present)

    def test_re_recording_updates_in_place(self):
        first = self._record("2019-05-31", "10000001", "ABSENT")
        second = self._record("2019-05-31", "10000001", "PRESENT")
        self.assertEqual(first, second)
        history = self.repository.history("10000001")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].status, "PRESENT")

    def test_class_attendance_rates(self):
        self._record("2019-05-31", "10000001", "PRESENT")
        self._record("2019-06-21", "10000001", "ABSENT")
        self._record("2019-05-31", "10000002", "PRESENT")
        rates = self.repository.class_attendance_rates()
        self.assertAlmostEqual(rates["10000001"], 50.0)
        self.assertAlmostEqual(rates["10000002"], 100.0)

    def test_invalid_status_is_rejected_by_the_schema(self):
        with self.assertRaises(Exception):
            self._record("2019-05-31", "10000001", "MAYBE")

    # -- signatures ----------------------------------------------------- #

    def test_signature_specimens_round_trip_as_images(self):
        self._record("2019-05-31", "10000001", "PRESENT", image=specimen())
        specimens = self.repository.signature_specimens("10000001")
        self.assertEqual(len(specimens), 1)
        date, image, mask = specimens[0]
        self.assertEqual(date, "2019-05-31")
        self.assertEqual(image.shape, (40, 90, 3))
        self.assertEqual(mask.shape, (40, 90))

    def test_absent_rows_are_not_offered_as_specimens(self):
        self._record("2019-05-31", "10000001", "ABSENT", image=specimen())
        self.assertEqual(self.repository.signature_specimens("10000001"), [])

    # -- lookups -------------------------------------------------------- #

    def test_resolve_index_prefers_an_exact_match(self):
        self.assertEqual(self.repository.resolve_index("10000001"), ["10000001"])

    def test_resolve_index_accepts_a_suffix(self):
        self.assertEqual(self.repository.resolve_index("0002"), ["10000002"])

    def test_resolve_index_returns_empty_for_unknown(self):
        self.assertEqual(self.repository.resolve_index("99999999"), [])

    def test_resolve_index_refuses_a_suffix_that_is_too_short(self):
        # "01" would match 10000001 out of a whole batch essentially at random;
        # the database lookup applies the same three-character rule as Roster.find.
        self.assertEqual(self.repository.resolve_index("01"), [])
        self.assertEqual(self.repository.resolve_index("001"), ["10000001"])

    def test_resolve_index_ignores_blank_input(self):
        self.assertEqual(self.repository.resolve_index("   "), [])

    def test_student_name_falls_back_to_the_index(self):
        self.assertEqual(self.repository.student_name("10000001"), "Ms Alpha One")
        self.assertEqual(self.repository.student_name("unknown"), "unknown")

    def test_context_manager_closes_the_connection(self):
        directory = tempfile.TemporaryDirectory()
        with AttendanceRepository(Path(directory.name) / "ctx.db") as repository:
            repository.upsert_students([Student("1", "N")])
        with self.assertRaises(Exception):
            repository.students()
        directory.cleanup()


class SummariseTests(unittest.TestCase):
    def test_empty_history_is_zero_per_cent_not_a_crash(self):
        self.assertEqual(summarise([]), (0, 0, 0.0))


if __name__ == "__main__":
    unittest.main()
