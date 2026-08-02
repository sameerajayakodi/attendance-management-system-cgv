"""Progress reporting for the image-processing pipeline.

The brief requires the program to *show the progress of the image processing*
while it runs.  Rather than sprinkle ``print`` and ``cv2.imshow`` calls through
the algorithms, reporting is expressed as a small polymorphic hierarchy:

``ProgressReporter``            abstract interface
  |- ``ConsoleReporter``        timed textual trace on stdout
  |- ``WindowReporter``         live OpenCV windows, one per stage
  |- ``StageWriter``            writes every stage to ``output/stages`` as PNG
  \\- ``CompositeReporter``      fans a single call out to several reporters

The pipeline talks only to the abstract interface, so adding a new presentation
(a GUI, a log file, a web socket) needs no change to the processing code.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .imaging import imwrite_unicode, label


@dataclass
class StageArtifact:
    """The visual by-product of one processing stage."""

    order: int
    name: str
    description: str
    image: np.ndarray | None = None
    elapsed_ms: float = 0.0
    notes: dict[str, object] = field(default_factory=dict)

    @property
    def slug(self) -> str:
        return f"{self.order:02d}_{self.name.lower().replace(' ', '_')}"

    @property
    def caption(self) -> str:
        return f"{self.order}. {self.name}  [{self.elapsed_ms:.0f} ms]"


class ProgressReporter(ABC):
    """Receives pipeline events.  Subclasses decide how to present them."""

    def begin(self, title: str) -> None:  # pragma: no cover - presentation only
        """Called once, before the first stage."""

    @abstractmethod
    def stage_started(self, order: int, name: str, description: str) -> None:
        """Called when a stage starts."""

    @abstractmethod
    def stage_finished(self, artifact: StageArtifact) -> None:
        """Called when a stage has produced its result."""

    def message(self, text: str) -> None:  # pragma: no cover - presentation only
        """Free-form informational text."""

    def end(self, artifacts: list[StageArtifact]) -> None:  # pragma: no cover
        """Called once, after the last stage."""


class NullReporter(ProgressReporter):
    """Silent reporter, used by the unit tests."""

    def stage_started(self, order: int, name: str, description: str) -> None:
        return None

    def stage_finished(self, artifact: StageArtifact) -> None:
        return None


class ConsoleReporter(ProgressReporter):
    """Textual progress trace with per-stage timings."""

    BAR_WIDTH = 24

    def __init__(self, total_stages: int, stream=None) -> None:
        self._total = max(1, total_stages)
        self._stream = stream
        self._started = time.perf_counter()

    def _write(self, text: str) -> None:
        if self._stream is None:
            print(text, flush=True)
        else:  # pragma: no cover - only used when redirecting
            self._stream.write(text + "\n")

    def begin(self, title: str) -> None:
        self._started = time.perf_counter()
        self._write("")
        self._write("=" * 74)
        self._write(f"  {title}")
        self._write("=" * 74)

    def stage_started(self, order: int, name: str, description: str) -> None:
        filled = int(self.BAR_WIDTH * (order - 1) / self._total)
        bar = "#" * filled + "." * (self.BAR_WIDTH - filled)
        self._write(f"[{bar}] {order}/{self._total}  {name}")
        self._write(f"{'':>13}{description}")

    def stage_finished(self, artifact: StageArtifact) -> None:
        detail = "  ".join(f"{key}={value}" for key, value in artifact.notes.items())
        suffix = f"  ({detail})" if detail else ""
        self._write(f"{'':>13}-> done in {artifact.elapsed_ms:6.1f} ms{suffix}")

    def message(self, text: str) -> None:
        self._write(f"{'':>13}{text}")

    def end(self, artifacts: list[StageArtifact]) -> None:
        total = (time.perf_counter() - self._started) * 1000.0
        bar = "#" * self.BAR_WIDTH
        self._write(f"[{bar}] {self._total}/{self._total}  complete in {total:.0f} ms")


class StageWriter(ProgressReporter):
    """Persists every stage image so the report can quote them verbatim."""

    def __init__(self, directory: Path, prefix: str) -> None:
        self.directory = Path(directory) / prefix
        self.directory.mkdir(parents=True, exist_ok=True)
        self.written: list[Path] = []

    def stage_started(self, order: int, name: str, description: str) -> None:
        return None

    def stage_finished(self, artifact: StageArtifact) -> None:
        if artifact.image is None:
            return
        path = self.directory / f"{artifact.slug}.png"
        imwrite_unicode(path, artifact.image)
        self.written.append(path)

    def end(self, artifacts: list[StageArtifact]) -> None:
        from .imaging import montage  # local import keeps the module graph shallow

        tiles = [label(a.image, a.caption) for a in artifacts if a.image is not None]
        if tiles:
            sheet = montage(tiles, columns=3)
            imwrite_unicode(self.directory / "00_pipeline_contact_sheet.png", sheet)


class WindowReporter(ProgressReporter):
    """Live OpenCV windows - the on-screen 'progress of the image processing'."""

    WINDOW = "SAMS - image processing"

    def __init__(self, delay_ms: int = 700, max_width: int = 900) -> None:
        self._delay = max(1, delay_ms)
        self._max_width = max_width

    def begin(self, title: str) -> None:
        cv2.namedWindow(self.WINDOW, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.WINDOW, self._max_width, int(self._max_width * 1.25))

    def stage_started(self, order: int, name: str, description: str) -> None:
        return None

    def stage_finished(self, artifact: StageArtifact) -> None:
        if artifact.image is None:
            return
        from .imaging import resize_to_width

        preview, _ = resize_to_width(label(artifact.image, artifact.caption), self._max_width)
        cv2.imshow(self.WINDOW, preview)
        cv2.waitKey(self._delay)

    def end(self, artifacts: list[StageArtifact]) -> None:
        cv2.waitKey(max(600, self._delay))
        cv2.destroyWindow(self.WINDOW)


class CompositeReporter(ProgressReporter):
    """Broadcasts every event to a list of reporters (composite pattern)."""

    def __init__(self, *reporters: ProgressReporter) -> None:
        self._reporters = [reporter for reporter in reporters if reporter is not None]

    def add(self, reporter: ProgressReporter) -> None:
        self._reporters.append(reporter)

    def begin(self, title: str) -> None:
        for reporter in self._reporters:
            reporter.begin(title)

    def stage_started(self, order: int, name: str, description: str) -> None:
        for reporter in self._reporters:
            reporter.stage_started(order, name, description)

    def stage_finished(self, artifact: StageArtifact) -> None:
        for reporter in self._reporters:
            reporter.stage_finished(artifact)

    def message(self, text: str) -> None:
        for reporter in self._reporters:
            reporter.message(text)

    def end(self, artifacts: list[StageArtifact]) -> None:
        for reporter in self._reporters:
            reporter.end(artifacts)
