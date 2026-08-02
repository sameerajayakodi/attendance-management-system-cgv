"""Orchestration: photograph in, attendance records out.

:class:`AttendancePipeline` runs the ordered list of stages from
:mod:`attendance.stages`, maps the resulting per-row verdicts onto the roster read from
``info.xml``, and writes the outcome to the SQLite database.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Sequence

import numpy as np

from .config import Settings
from .database import AttendanceRepository
from .imaging import imread_unicode, imwrite_unicode
from .progress import CompositeReporter, ConsoleReporter, NullReporter, ProgressReporter, StageArtifact, StageWriter, WindowReporter
from .records import Roster, Student
from .signature import SignatureVerdict
from .stages import DEFAULT_STAGES, PipelineContext, ProcessingStage

# 31.05.2019 / 2019-05-31 / 31-05-2019 / 05_07_2019 ...
_DATE_PATTERNS = (
    (re.compile(r"(\d{4})[.\-_](\d{1,2})[.\-_](\d{1,2})"), ("year", "month", "day")),
    (re.compile(r"(\d{1,2})[.\-_](\d{1,2})[.\-_](\d{4})"), ("day", "month", "year")),
)


@dataclass
class StudentOutcome:
    """One student's result for one session."""

    student: Student
    row: int
    verdict: SignatureVerdict

    @property
    def status(self) -> str:
        return self.verdict.status

    @property
    def present(self) -> bool:
        return self.verdict.present


@dataclass
class SessionResult:
    """Everything the pipeline learned about one signing sheet."""

    source: Path
    session_date: date
    subject_code: str
    outcomes: list[StudentOutcome] = field(default_factory=list)
    artifacts: list[StageArtifact] = field(default_factory=list)
    context: PipelineContext | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def present_count(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.present)

    @property
    def absent_count(self) -> int:
        return len(self.outcomes) - self.present_count

    @property
    def total_ms(self) -> float:
        return sum(artifact.elapsed_ms for artifact in self.artifacts)

    def to_table(self) -> list[list[str]]:
        """Console-friendly rendering of the per-student result."""
        rows = [["#", "Index", "Student", "Ink %", "Blobs", "Pen", "Status", "Conf."]]
        for position, outcome in enumerate(self.outcomes, start=1):
            features = outcome.verdict.features
            rows.append(
                [
                    str(position),
                    outcome.student.index_no,
                    outcome.student.name[:34],
                    f"{features.ink_ratio * 100:.2f}",
                    str(features.components),
                    features.pen_colour,
                    outcome.status,
                    f"{outcome.verdict.confidence:.2f}",
                ]
            )
        return rows


class PipelineError(RuntimeError):
    """Raised when a sheet cannot be processed at all."""


class AttendancePipeline:
    """Runs the processing stages and persists the result."""

    def __init__(
        self,
        settings: Settings,
        roster: Roster,
        reporter: ProgressReporter | None = None,
        stages: Sequence[type[ProcessingStage]] | None = None,
    ) -> None:
        self._settings = settings
        self._roster = roster
        self._stage_types = tuple(stages or DEFAULT_STAGES)
        self._reporter = reporter or NullReporter()

    # ------------------------------------------------------------------ #
    #  Construction helper
    # ------------------------------------------------------------------ #

    @classmethod
    def with_default_reporters(cls, settings: Settings, roster: Roster, image_path: Path) -> "AttendancePipeline":
        """Build a pipeline wired to the console, the stage writer and (optionally) windows."""
        reporters: list[ProgressReporter] = [ConsoleReporter(len(DEFAULT_STAGES))]
        if settings.save_stages:
            reporters.append(StageWriter(settings.stage_dir, image_path.stem))
        if settings.show_windows:
            reporters.append(WindowReporter(settings.window_delay_ms))
        return cls(settings, roster, CompositeReporter(*reporters))

    # ------------------------------------------------------------------ #
    #  Execution
    # ------------------------------------------------------------------ #

    def process(self, image_path: str | Path, session_date: date | None = None) -> SessionResult:
        image_path = Path(image_path)
        original = imread_unicode(image_path)

        context = PipelineContext(
            source=image_path,
            settings=self._settings,
            original=original,
            expected_rows=len(self._roster),
        )
        self._reporter.begin(f"SAMS  |  {image_path.name}  |  {self._roster.subject.code}")

        artifacts: list[StageArtifact] = []
        for order, stage_type in enumerate(self._stage_types, start=1):
            stage = stage_type()
            self._reporter.stage_started(order, stage.name, stage.description)
            artifact = stage.run(order, context)
            artifacts.append(artifact)
            self._reporter.stage_finished(artifact)
        self._reporter.end(artifacts)

        result = SessionResult(
            source=image_path,
            session_date=session_date or infer_session_date(image_path),
            subject_code=self._roster.subject.code,
            artifacts=artifacts,
            context=context,
        )
        self._map_to_roster(context.verdicts, result)
        return result

    # ------------------------------------------------------------------ #
    #  Roster mapping
    # ------------------------------------------------------------------ #

    def _map_to_roster(self, verdicts: Sequence[SignatureVerdict], result: SessionResult) -> None:
        """Pair detected rows with roster entries, top to bottom."""
        detected, expected = len(verdicts), len(self._roster)
        if detected != expected:
            result.warnings.append(
                f"the sheet yielded {detected} data rows but info.xml lists {expected} students; "
                f"the first {min(detected, expected)} rows were matched"
            )
            self._reporter.message(f"WARNING: {result.warnings[-1]}")

        for position in range(min(detected, expected)):
            result.outcomes.append(
                StudentOutcome(student=self._roster[position], row=verdicts[position].row, verdict=verdicts[position])
            )

    # ------------------------------------------------------------------ #
    #  Persistence
    # ------------------------------------------------------------------ #

    def persist(self, result: SessionResult, repository: AttendanceRepository) -> int:
        """Write ``result`` to the database and return the session id."""
        repository.upsert_students(self._roster.students)
        session_id = repository.upsert_session(
            subject_code=result.subject_code,
            session_date=result.session_date.isoformat(),
            source_image=str(result.source),
        )
        for outcome in result.outcomes:
            features = outcome.verdict.features
            repository.record_attendance(
                session_id=session_id,
                index_no=outcome.student.index_no,
                row_no=outcome.row,
                status=outcome.status,
                confidence=outcome.verdict.confidence,
                ink_ratio=features.ink_ratio,
                ink_pixels=features.ink_pixels,
                components=features.components,
                pen_colour=features.pen_colour,
                signature=outcome.verdict.crop,
                ink_mask=outcome.verdict.mask,
            )
        return session_id

    def export_signature_crops(self, result: SessionResult, directory: Path) -> list[Path]:
        """Save every signature cell as a PNG (used by the report's figures)."""
        directory = Path(directory) / result.session_date.isoformat()
        written: list[Path] = []
        for outcome in result.outcomes:
            crop = outcome.verdict.crop
            if crop is None or crop.size == 0:
                continue
            name = f"{outcome.student.index_no}_{outcome.status.lower()}.png"
            written.append(imwrite_unicode(directory / name, crop))
        return written


# --------------------------------------------------------------------------- #
#  Free functions
# --------------------------------------------------------------------------- #


def infer_session_date(image_path: Path) -> date:
    """Read the lecture date out of the file name, as the brief's example implies.

    ``python sams.py 10.07.2019.png info.xml`` names the sheet after the session,
    so the file name is the primary source.  If it carries no date the file's
    modification time is used and the caller is free to override with ``--date``.
    """
    stem = Path(image_path).stem
    for pattern, order in _DATE_PATTERNS:
        match = pattern.search(stem)
        if not match:
            continue
        parts = dict(zip(order, (int(value) for value in match.groups())))
        try:
            return date(parts["year"], parts["month"], parts["day"])
        except ValueError:
            continue
    return datetime.fromtimestamp(Path(image_path).stat().st_mtime).date()


def format_table(rows: Sequence[Sequence[str]]) -> str:
    """Render a list of rows as a fixed-width console table."""
    if not rows:
        return ""
    widths = [max(len(str(row[column])) for row in rows) for column in range(len(rows[0]))]
    lines = []
    for position, row in enumerate(rows):
        line = "  ".join(str(cell).ljust(widths[column]) for column, cell in enumerate(row))
        lines.append(line.rstrip())
        if position == 0:
            lines.append("-" * len(line.rstrip()))
    return "\n".join(lines)
