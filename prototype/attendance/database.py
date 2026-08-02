"""SQLite persistence for attendance records and signature specimens.

The schema is deliberately normalised around three entities - students, sessions
and attendance - with the raw signature crop stored as a PNG blob so that
``investigate.py`` can re-examine a specimen long after the photograph itself has
been archived.  Re-processing the same sheet twice updates the existing row
rather than duplicating it, which makes the tool safe to re-run.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import cv2
import numpy as np

from .records import Roster, Student

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS students (
    index_no   TEXT PRIMARY KEY,
    title      TEXT NOT NULL DEFAULT '',
    name       TEXT NOT NULL,
    batch      TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS sessions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_code  TEXT NOT NULL,
    session_date  TEXT NOT NULL,
    source_image  TEXT NOT NULL,
    processed_at  TEXT NOT NULL,
    UNIQUE (subject_code, session_date)
);

CREATE TABLE IF NOT EXISTS attendance (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    index_no     TEXT    NOT NULL REFERENCES students(index_no) ON DELETE CASCADE,
    row_no       INTEGER NOT NULL,
    status       TEXT    NOT NULL CHECK (status IN ('PRESENT', 'ABSENT')),
    confidence   REAL    NOT NULL DEFAULT 0.0,
    ink_ratio    REAL    NOT NULL DEFAULT 0.0,
    ink_pixels   INTEGER NOT NULL DEFAULT 0,
    components   INTEGER NOT NULL DEFAULT 0,
    pen_colour   TEXT    NOT NULL DEFAULT '',
    UNIQUE (session_id, index_no)
);

-- ``image_png`` is the colour crop as photographed (used for the figures);
-- ``mask_png`` is the ink mask the pipeline already isolated for that cell,
-- which is what the descriptors in investigate.py are computed from.
CREATE TABLE IF NOT EXISTS signatures (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    attendance_id INTEGER NOT NULL UNIQUE REFERENCES attendance(id) ON DELETE CASCADE,
    width         INTEGER NOT NULL,
    height        INTEGER NOT NULL,
    image_png     BLOB    NOT NULL,
    mask_png      BLOB
);

CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(index_no);
CREATE INDEX IF NOT EXISTS idx_sessions_date      ON sessions(session_date);
"""


@dataclass(frozen=True)
class AttendanceRow:
    """A joined attendance record as returned by the query helpers."""

    session_date: str
    subject_code: str
    index_no: str
    name: str
    status: str
    confidence: float
    ink_ratio: float
    source_image: str

    @property
    def present(self) -> bool:
        return self.status == "PRESENT"

    @property
    def as_date(self) -> date:
        return datetime.strptime(self.session_date, "%Y-%m-%d").date()


class AttendanceRepository:
    """Thin, explicit data-access layer over the SQLite file.

    Usable as a context manager::

        with AttendanceRepository(path) as repository:
            repository.upsert_students(roster)
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self.path))
        self._connection.row_factory = sqlite3.Row
        self._connection.executescript(SCHEMA)
        self._connection.commit()

    # ------------------------------------------------------------------ #
    #  Lifecycle
    # ------------------------------------------------------------------ #

    def __enter__(self) -> "AttendanceRepository":
        return self

    def __exit__(self, *_exception) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            yield self._connection
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

    # ------------------------------------------------------------------ #
    #  Writes
    # ------------------------------------------------------------------ #

    def upsert_students(self, students: Iterable[Student]) -> int:
        rows = [(s.index_no, s.title, s.name, s.batch) for s in students]
        with self.transaction() as connection:
            connection.executemany(
                """
                INSERT INTO students (index_no, title, name, batch)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(index_no) DO UPDATE SET
                    title = excluded.title,
                    name  = excluded.name,
                    batch = excluded.batch
                """,
                rows,
            )
        return len(rows)

    def upsert_session(self, subject_code: str, session_date: str, source_image: str) -> int:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO sessions (subject_code, session_date, source_image, processed_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(subject_code, session_date) DO UPDATE SET
                    source_image = excluded.source_image,
                    processed_at = excluded.processed_at
                """,
                (subject_code, session_date, source_image, datetime.now().isoformat(timespec="seconds")),
            )
            cursor = connection.execute(
                "SELECT id FROM sessions WHERE subject_code = ? AND session_date = ?",
                (subject_code, session_date),
            )
            return int(cursor.fetchone()["id"])

    def record_attendance(
        self,
        session_id: int,
        index_no: str,
        row_no: int,
        status: str,
        confidence: float,
        ink_ratio: float,
        ink_pixels: int,
        components: int,
        pen_colour: str,
        signature: np.ndarray | None = None,
        ink_mask: np.ndarray | None = None,
    ) -> int:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO attendance
                    (session_id, index_no, row_no, status, confidence,
                     ink_ratio, ink_pixels, components, pen_colour)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, index_no) DO UPDATE SET
                    row_no     = excluded.row_no,
                    status     = excluded.status,
                    confidence = excluded.confidence,
                    ink_ratio  = excluded.ink_ratio,
                    ink_pixels = excluded.ink_pixels,
                    components = excluded.components,
                    pen_colour = excluded.pen_colour
                """,
                (session_id, index_no, row_no, status, confidence, ink_ratio, ink_pixels, components, pen_colour),
            )
            cursor = connection.execute(
                "SELECT id FROM attendance WHERE session_id = ? AND index_no = ?",
                (session_id, index_no),
            )
            attendance_id = int(cursor.fetchone()["id"])

            if signature is not None and signature.size:
                ok, encoded = cv2.imencode(".png", signature)
                mask_blob = None
                if ink_mask is not None and ink_mask.size:
                    mask_ok, mask_encoded = cv2.imencode(".png", ink_mask)
                    mask_blob = sqlite3.Binary(mask_encoded.tobytes()) if mask_ok else None
                if ok:
                    connection.execute(
                        """
                        INSERT INTO signatures (attendance_id, width, height, image_png, mask_png)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(attendance_id) DO UPDATE SET
                            width = excluded.width,
                            height = excluded.height,
                            image_png = excluded.image_png,
                            mask_png = excluded.mask_png
                        """,
                        (
                            attendance_id,
                            signature.shape[1],
                            signature.shape[0],
                            sqlite3.Binary(encoded.tobytes()),
                            mask_blob,
                        ),
                    )
        return attendance_id

    # ------------------------------------------------------------------ #
    #  Reads
    # ------------------------------------------------------------------ #

    def sessions(self) -> list[sqlite3.Row]:
        return list(self._connection.execute("SELECT * FROM sessions ORDER BY session_date"))

    def students(self) -> list[Student]:
        rows = self._connection.execute("SELECT * FROM students ORDER BY index_no")
        return [Student(index_no=r["index_no"], name=r["name"], title=r["title"], batch=r["batch"]) for r in rows]

    def history(self, index_no: str) -> list[AttendanceRow]:
        """Every recorded session for one student, oldest first."""
        cursor = self._connection.execute(
            """
            SELECT s.session_date, s.subject_code, s.source_image,
                   a.index_no, a.status, a.confidence, a.ink_ratio,
                   st.name
            FROM attendance a
            JOIN sessions s  ON s.id = a.session_id
            JOIN students st ON st.index_no = a.index_no
            WHERE a.index_no = ?
            ORDER BY s.session_date
            """,
            (index_no,),
        )
        return [self._to_row(record) for record in cursor]

    def all_attendance(self) -> list[AttendanceRow]:
        cursor = self._connection.execute(
            """
            SELECT s.session_date, s.subject_code, s.source_image,
                   a.index_no, a.status, a.confidence, a.ink_ratio,
                   st.name
            FROM attendance a
            JOIN sessions s  ON s.id = a.session_id
            JOIN students st ON st.index_no = a.index_no
            ORDER BY s.session_date, a.index_no
            """
        )
        return [self._to_row(record) for record in cursor]

    def class_attendance_rates(self) -> dict[str, float]:
        """Attendance percentage for every student that has been recorded."""
        cursor = self._connection.execute(
            """
            SELECT index_no,
                   AVG(CASE WHEN status = 'PRESENT' THEN 1.0 ELSE 0.0 END) * 100 AS rate
            FROM attendance
            GROUP BY index_no
            """
        )
        return {record["index_no"]: float(record["rate"]) for record in cursor}

    def signature_specimens(self, index_no: str) -> list[tuple[str, np.ndarray, np.ndarray | None]]:
        """Signature specimens for one student: (session date, colour crop, ink mask)."""
        cursor = self._connection.execute(
            """
            SELECT s.session_date, sig.image_png, sig.mask_png
            FROM signatures sig
            JOIN attendance a ON a.id = sig.attendance_id
            JOIN sessions   s ON s.id = a.session_id
            WHERE a.index_no = ? AND a.status = 'PRESENT'
            ORDER BY s.session_date
            """,
            (index_no,),
        )
        specimens: list[tuple[str, np.ndarray, np.ndarray | None]] = []
        for record in cursor:
            image = self._decode(record["image_png"], cv2.IMREAD_COLOR)
            mask = self._decode(record["mask_png"], cv2.IMREAD_GRAYSCALE)
            if image is not None:
                specimens.append((record["session_date"], image, mask))
        return specimens

    @staticmethod
    def _decode(blob: bytes | None, flags: int) -> np.ndarray | None:
        if not blob:
            return None
        return cv2.imdecode(np.frombuffer(blob, dtype=np.uint8), flags)

    #: shortest suffix accepted as a partial index; the same rule as
    #: :meth:`attendance.records.Student.matches`, so both lookup paths agree
    MIN_SUFFIX_LENGTH = 3

    def resolve_index(self, query: str) -> list[str]:
        """Index numbers in the database that match a possibly partial query.

        An exact match always wins.  Failing that, a *trailing* portion of an
        index is accepted, but only if it is at least
        :attr:`MIN_SUFFIX_LENGTH` characters long - a one- or two-digit query
        would otherwise pick a student out of a batch essentially at random.
        """
        query = query.strip()
        if not query:
            return []
        exact = self._connection.execute(
            "SELECT index_no FROM students WHERE index_no = ?", (query,)
        ).fetchall()
        if exact:
            return [record["index_no"] for record in exact]
        if len(query) < self.MIN_SUFFIX_LENGTH:
            return []
        like = self._connection.execute(
            "SELECT index_no FROM students WHERE index_no LIKE ?", (f"%{query}",)
        ).fetchall()
        return [record["index_no"] for record in like]

    def student_name(self, index_no: str) -> str:
        record = self._connection.execute(
            "SELECT title, name FROM students WHERE index_no = ?", (index_no,)
        ).fetchone()
        if record is None:
            return index_no
        return f"{record['title']} {record['name']}".strip()

    # ------------------------------------------------------------------ #
    @staticmethod
    def _to_row(record: sqlite3.Row) -> AttendanceRow:
        return AttendanceRow(
            session_date=record["session_date"],
            subject_code=record["subject_code"],
            index_no=record["index_no"],
            name=record["name"],
            status=record["status"],
            confidence=float(record["confidence"]),
            ink_ratio=float(record["ink_ratio"]),
            source_image=record["source_image"],
        )


def seed_from_roster(repository: AttendanceRepository, roster: Roster) -> int:
    """Insert or refresh every student of ``roster``."""
    return repository.upsert_students(roster.students)


def summarise(rows: Sequence[AttendanceRow]) -> tuple[int, int, float]:
    """(present, total, percentage) for a sequence of attendance rows."""
    total = len(rows)
    present = sum(1 for row in rows if row.present)
    percentage = (present / total * 100.0) if total else 0.0
    return present, total, percentage
