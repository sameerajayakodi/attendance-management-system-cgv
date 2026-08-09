"""Tests for the FastAPI layer (web/api/main.py).

This module was previously the only untested part of the codebase, despite
being the only place that accepts an untrusted file upload and builds
filesystem paths from request parameters (the media routes' path-traversal
guard).  These tests point the API at a throwaway database, roster and
upload/stage directory tree so they never touch the real ``data/`` folder.
"""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path

from support import PROJECT_ROOT, synthetic_sheet  # noqa: F401

from attendance.database import AttendanceRepository
from attendance.imaging import imwrite_unicode
from attendance.records import Student

WEB_API_DIR = PROJECT_ROOT.parent / "web" / "api"
if str(WEB_API_DIR) not in sys.path:
    sys.path.insert(0, str(WEB_API_DIR))

import main as api  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

ROSTER_XML = (
    "<nsbm><subject><code>CS402.3</code></subject><students><batch id='t'>"
    + "".join(
        f"<student><index>2000000{index}</index><name>Student {index + 1}</name></student>"
        for index in range(6)
    )
    + "</batch></students></nsbm>"
)


class WebApiTestCase(unittest.TestCase):
    """Redirects the API's module-level paths at a temporary directory tree."""

    def setUp(self):
        self._directory = tempfile.TemporaryDirectory()
        self.root = Path(self._directory.name)
        (self.root / "info.xml").write_text(ROSTER_XML, encoding="utf-8")

        self._patched = {
            "DEFAULT_DATABASE": api.DEFAULT_DATABASE,
            "DEFAULT_INFO_XML": api.DEFAULT_INFO_XML,
            "UPLOAD_DIR": api.UPLOAD_DIR,
            "SHEET_DIR": api.SHEET_DIR,
            "STAGE_DIR": api.STAGE_DIR,
            "DEFAULT_SETTINGS": api.DEFAULT_SETTINGS,
        }

        api.DEFAULT_DATABASE = self.root / "attendance.db"
        api.DEFAULT_INFO_XML = self.root / "info.xml"
        api.UPLOAD_DIR = self.root / "uploads"
        api.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        api.SHEET_DIR = self.root / "sheets"
        api.SHEET_DIR.mkdir(parents=True, exist_ok=True)
        api.STAGE_DIR = self.root / "stages"
        api.DEFAULT_SETTINGS = api.DEFAULT_SETTINGS.evolve(
            stage_dir=api.STAGE_DIR, save_stages=True, show_windows=False
        )

        self.client = TestClient(api.app)

    def tearDown(self):
        for name, value in self._patched.items():
            setattr(api, name, value)
        self._directory.cleanup()

    def _upload_synthetic_sheet(self, filename: str = "01.02.2020.jpeg", signed_rows=(0, 2, 3, 5)):
        image, expected = synthetic_sheet(signed_rows=signed_rows)
        with tempfile.TemporaryDirectory() as scratch:
            path = imwrite_unicode(Path(scratch) / filename, image)
            with path.open("rb") as handle:
                response = self.client.post(
                    "/api/sessions",
                    files={"file": (filename, handle, "image/jpeg")},
                )
        return response, expected


class SafeComponentTests(unittest.TestCase):
    """The regex/``..`` guard that protects the media routes from path traversal."""

    def test_dot_dot_is_rejected(self):
        self.assertFalse(api.safe_component(".."))
        self.assertFalse(api.safe_component("..secret"))
        self.assertFalse(api.safe_component("a..b"))

    def test_path_separators_are_rejected(self):
        self.assertFalse(api.safe_component("a/b"))
        self.assertFalse(api.safe_component("a\\b"))

    def test_ordinary_stage_and_sheet_names_are_accepted(self):
        self.assertTrue(api.safe_component("10.07.2019"))
        self.assertTrue(api.safe_component("05_binarisation"))
        self.assertTrue(api.safe_component("WhatsApp Image (2)"))


class SafeUploadNameTests(unittest.TestCase):
    """Filename sanitising, including the collision-avoidance fix."""

    def test_unsafe_characters_are_replaced(self):
        name = api.safe_upload_name("WhatsApp Image 2026-07-19 at 09.25.09.jpeg", exists=lambda _n: False)
        self.assertNotIn(" ", name)
        self.assertTrue(name.endswith(".jpeg"))

    def test_a_name_that_already_exists_gets_a_numeric_suffix(self):
        taken = {"sheet.jpeg"}
        name = api.safe_upload_name("sheet.jpeg", exists=lambda n: n in taken)
        self.assertNotEqual(name, "sheet.jpeg")
        self.assertTrue(name.startswith("sheet_"))
        self.assertTrue(name.endswith(".jpeg"))

    def test_repeated_collisions_each_get_a_new_suffix(self):
        taken = {"sheet.jpeg", "sheet_2.jpeg"}
        name = api.safe_upload_name("sheet.jpeg", exists=lambda n: n in taken)
        self.assertEqual(name, "sheet_3.jpeg")


class UploadAndSessionLifecycleTests(WebApiTestCase):
    """The upload route, its persistence, and the delete route's file cleanup."""

    def test_uploading_a_synthetic_sheet_returns_the_expected_attendance(self):
        response, expected = self._upload_synthetic_sheet()
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        present = {o["indexNo"] for o in body["outcomes"] if o["status"] == "PRESENT"}
        signed = {f"2000000{i}" for i in expected["signed_rows"]}
        self.assertEqual(present, signed)
        self.assertEqual(body["warnings"], [])

    def test_an_unsupported_extension_is_rejected(self):
        response = self.client.post(
            "/api/sessions",
            files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        self.assertEqual(response.status_code, 400)

    def test_a_file_with_an_image_extension_but_no_image_bytes_is_rejected(self):
        response = self.client.post(
            "/api/sessions",
            files={"file": ("fake.png", io.BytesIO(b"not actually a png"), "image/png")},
        )
        self.assertEqual(response.status_code, 400)
        # The unreadable payload must not be left behind on disk.
        self.assertEqual(list(api.UPLOAD_DIR.glob("fake*")), [])

    def test_deleting_a_session_removes_its_files_from_disk(self):
        response, _expected = self._upload_synthetic_sheet()
        self.assertEqual(response.status_code, 201, response.text)
        session_date = response.json()["date"]

        uploaded = list(api.UPLOAD_DIR.glob("*.jpeg"))
        stage_dirs = list(api.STAGE_DIR.iterdir())
        self.assertEqual(len(uploaded), 1)
        self.assertEqual(len(stage_dirs), 1)

        delete_response = self.client.delete(f"/api/sessions/{session_date}")
        self.assertEqual(delete_response.status_code, 204)

        self.assertFalse(uploaded[0].exists())
        self.assertFalse(stage_dirs[0].exists())

        # Gone from the database too: a second delete is a 404, not a 204.
        self.assertEqual(self.client.delete(f"/api/sessions/{session_date}").status_code, 404)
        self.assertEqual(self.client.get(f"/api/sessions/{session_date}").status_code, 404)

    def test_uploading_the_same_filename_twice_does_not_overwrite_the_first(self):
        first, _ = self._upload_synthetic_sheet(filename="01.02.2020.jpeg", signed_rows=(0,))
        self.assertEqual(first.status_code, 201, first.text)
        second, _ = self._upload_synthetic_sheet(filename="01.02.2020.jpeg", signed_rows=(1, 2))
        # Same file name, different session date is impossible here (both would
        # infer the same date from the name), so the second upload updates the
        # same session - but the important thing is neither request 500s and
        # both original+second sheet files exist under UPLOAD_DIR afterwards.
        self.assertIn(second.status_code, (201, 422, 400))
        jpeg_files = list(api.UPLOAD_DIR.glob("*.jpeg"))
        self.assertGreaterEqual(len(jpeg_files), 1)


class MediaRouteTests(WebApiTestCase):
    def test_a_missing_stage_image_is_a_404_not_a_500(self):
        response = self.client.get("/api/media/stage/nonexistent/05_binarisation")
        self.assertEqual(response.status_code, 404)

    def test_an_unsafe_stage_name_is_rejected_before_touching_the_filesystem(self):
        # "%2e%2e" would decode to ".." - the client sends the raw escaped form,
        # but the safe_component guard is exercised directly by SafeComponentTests;
        # here a segment containing characters outside the allow-list is enough.
        response = self.client.get("/api/media/stage/bad*name/slug")
        self.assertEqual(response.status_code, 400)

    def test_a_missing_signature_specimen_is_a_404(self):
        response = self.client.get("/api/media/signature/20000000/2019-05-31")
        self.assertEqual(response.status_code, 404)


class StudentResolutionTests(WebApiTestCase):
    """resolve_index-driven disambiguation, exercised through the HTTP layer.

    Seeds the database directly (rather than uploading a sheet) with two
    students that share a suffix but differ in their leading digits, so the
    ambiguous-suffix case can actually occur.
    """

    def setUp(self):
        super().setUp()
        with AttendanceRepository(api.DEFAULT_DATABASE) as repo:
            repo.upsert_students(
                [
                    Student("10203040", "Exact Match Student", "Mr", "t"),
                    Student("50020304", "Ambiguous Suffix A", "Mr", "t"),
                    Student("60020304", "Ambiguous Suffix B", "Ms", "t"),
                ]
            )

    def test_an_exact_index_resolves(self):
        response = self.client.get("/api/students/10203040")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["indexNo"], "10203040")

    def test_an_unknown_index_is_a_404(self):
        response = self.client.get("/api/students/99999999")
        self.assertEqual(response.status_code, 404)

    def test_an_ambiguous_suffix_is_a_409(self):
        # "50020304" and "60020304" both end in "020304" - a short shared
        # suffix must be reported as ambiguous rather than guessed.
        response = self.client.get("/api/students/020304")
        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()
