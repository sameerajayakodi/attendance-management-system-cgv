"""The individual stages of the signing-sheet processing pipeline.

Each stage is a small object with one responsibility.  It reads from and writes
to a shared :class:`PipelineContext`, returns the image it wants displayed, and
knows nothing about the stages on either side of it.  New processing steps can
therefore be inserted, reordered or removed without touching the orchestration
code in :mod:`attendance.pipeline`.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from . import imaging
from .config import Settings
from .progress import StageArtifact
from .signature import SignatureAnalyzer, SignatureVerdict
from .table import DetectionResult, TableDetector


# --------------------------------------------------------------------------- #
#  Shared state
# --------------------------------------------------------------------------- #


@dataclass
class PipelineContext:
    """Mutable state handed from one stage to the next."""

    source: Path
    settings: Settings
    original: np.ndarray

    working: np.ndarray | None = None          # colour, rescaled and rectified
    gray: np.ndarray | None = None
    flattened: np.ndarray | None = None
    denoised: np.ndarray | None = None
    binary: np.ndarray | None = None
    otsu: np.ndarray | None = None

    scale: float = 1.0
    skew_degrees: float = 0.0
    otsu_threshold: float = 0.0
    expected_rows: int = 0
    """How many students ``info.xml`` lists - used to validate and, where the
    printed pitch allows it, repair the recovered grid."""
    repaired_rules: int = 0

    detection: DetectionResult | None = None
    verdicts: list[SignatureVerdict] = field(default_factory=list)
    notes: dict[str, object] = field(default_factory=dict)

    def require(self, attribute: str) -> np.ndarray:
        value = getattr(self, attribute)
        if value is None:
            raise RuntimeError(f"pipeline stage ran out of order: '{attribute}' is not available yet")
        return value


def photometric_chain(colour: np.ndarray, settings: Settings) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """grayscale -> flat field -> denoise -> adaptive binary.

    Extracted as a function because the deskew stage has to re-run it on the
    rectified image.
    """
    gray = imaging.to_grayscale(colour)
    flattened = imaging.flatten_illumination(gray, settings)
    denoised = imaging.denoise(flattened, settings)
    binary = imaging.clean_binary(imaging.binarize_adaptive(denoised, settings))
    return gray, flattened, denoised, binary


# --------------------------------------------------------------------------- #
#  Stage base class
# --------------------------------------------------------------------------- #


class ProcessingStage(ABC):
    """One step of the pipeline."""

    #: short human-readable name, used in the progress trace and figure captions
    name: str = "stage"
    #: one-line explanation of what the stage does and why
    description: str = ""

    @abstractmethod
    def apply(self, context: PipelineContext) -> np.ndarray | None:
        """Perform the work and return the image to display (or ``None``)."""

    def notes(self, context: PipelineContext) -> dict[str, object]:
        """Optional measurements to show beside the timing."""
        return {}

    def run(self, order: int, context: PipelineContext) -> StageArtifact:
        """Time :meth:`apply` and wrap its output in a :class:`StageArtifact`."""
        started = time.perf_counter()
        image = self.apply(context)
        elapsed = (time.perf_counter() - started) * 1000.0
        return StageArtifact(
            order=order,
            name=self.name,
            description=self.description,
            image=image,
            elapsed_ms=elapsed,
            notes=self.notes(context),
        )


# --------------------------------------------------------------------------- #
#  Concrete stages
# --------------------------------------------------------------------------- #


class AcquisitionStage(ProcessingStage):
    name = "Acquisition"
    description = "Load the photograph and rescale it to the working resolution."

    def apply(self, context: PipelineContext) -> np.ndarray:
        working, scale = imaging.resize_to_width(context.original, context.settings.working_width)
        context.working = working
        context.scale = scale
        return working

    def notes(self, context: PipelineContext) -> dict[str, object]:
        height, width = context.original.shape[:2]
        return {"input": f"{width}x{height}", "scale": f"{context.scale:.3f}"}


class GrayscaleStage(ProcessingStage):
    name = "Greyscale"
    description = "Convert BGR to luma (Y = 0.299R + 0.587G + 0.114B); colour is not needed to find ink."

    def apply(self, context: PipelineContext) -> np.ndarray:
        context.gray = imaging.to_grayscale(context.require("working"))
        return context.gray


class IlluminationStage(ProcessingStage):
    name = "Illumination correction"
    description = "Estimate the shading field by morphological closing and divide it out."

    def apply(self, context: PipelineContext) -> np.ndarray:
        context.flattened = imaging.flatten_illumination(context.require("gray"), context.settings)
        return context.flattened

    def notes(self, context: PipelineContext) -> dict[str, object]:
        before = float(np.std(context.require("gray")))
        after = float(np.std(context.require("flattened")))
        return {"sd_before": f"{before:.1f}", "sd_after": f"{after:.1f}"}


class DenoiseStage(ProcessingStage):
    name = "Edge-preserving denoise"
    description = "Bilateral filter: removes paper texture and JPEG artefacts but keeps stroke edges sharp."

    def apply(self, context: PipelineContext) -> np.ndarray:
        context.denoised = imaging.denoise(context.require("flattened"), context.settings)
        return context.denoised


class BinarizationStage(ProcessingStage):
    name = "Binarisation"
    description = "Adaptive Gaussian thresholding; Otsu is computed alongside it for comparison."

    def apply(self, context: PipelineContext) -> np.ndarray:
        denoised = context.require("denoised")
        context.binary = imaging.clean_binary(imaging.binarize_adaptive(denoised, context.settings))
        context.otsu, context.otsu_threshold = imaging.binarize_otsu(denoised)
        return context.binary

    def notes(self, context: PipelineContext) -> dict[str, object]:
        binary = context.require("binary")
        ink = float(cv2.countNonZero(binary)) / binary.size * 100.0
        return {"otsu_T": f"{context.otsu_threshold:.0f}", "ink": f"{ink:.2f}%"}


class DeskewStage(ProcessingStage):
    name = "Skew correction"
    description = "Estimate the page rotation from the long printed rules and rectify the image."

    def apply(self, context: PipelineContext) -> np.ndarray | None:
        settings = context.settings
        angle = imaging.estimate_skew(context.require("binary"), settings)
        context.skew_degrees = angle

        if abs(angle) < 0.15 or abs(angle) > settings.max_skew_degrees:
            return imaging.as_bgr(context.require("working"))

        rectified = imaging.rotate_bound(context.require("working"), angle)
        context.working = rectified
        context.gray, context.flattened, context.denoised, context.binary = photometric_chain(rectified, settings)
        context.otsu, context.otsu_threshold = imaging.binarize_otsu(context.denoised)
        return rectified

    def notes(self, context: PipelineContext) -> dict[str, object]:
        return {"skew": f"{context.skew_degrees:+.2f} deg"}


class LineExtractionStage(ProcessingStage):
    name = "Rule extraction"
    description = "Morphological opening with long thin kernels isolates the printed horizontal and vertical rules."

    def apply(self, context: PipelineContext) -> np.ndarray:
        detector = TableDetector(context.settings)
        masks = detector.extract_lines(context.require("binary"))
        context.notes["masks"] = masks

        canvas = np.zeros((*masks.horizontal.shape, 3), np.uint8)
        canvas[:, :, 1] = masks.horizontal      # horizontal rules in green
        canvas[:, :, 2] = masks.vertical        # vertical rules in red
        canvas[:, :, 0] = masks.intersections   # crossings turn white
        return canvas

    def notes(self, context: PipelineContext) -> dict[str, object]:
        masks = context.notes.get("masks")
        if masks is None:
            return {}
        return {
            "h_px": int(cv2.countNonZero(masks.horizontal)),
            "v_px": int(cv2.countNonZero(masks.vertical)),
        }


class TableDetectionStage(ProcessingStage):
    name = "Table reconstruction"
    description = "Group the rules into grids and select the roster table (the one with the most rows)."

    def apply(self, context: PipelineContext) -> np.ndarray:
        detector = TableDetector(context.settings)
        context.detection = detector.detect(context.require("binary"), context.notes.get("masks"))
        if context.detection.roster is not None and context.expected_rows:
            context.repaired_rules = context.detection.roster.repair(context.expected_rows)
        return TableDetector.render(context.require("working"), context.detection)

    def notes(self, context: PipelineContext) -> dict[str, object]:
        detection = context.detection
        if detection is None or detection.roster is None:
            return {}
        roster = detection.roster
        notes: dict[str, object] = {
            "tables": len(detection.tables),
            "rows": len(roster.data_rows),
            "cols": roster.column_count,
            "cv": f"{roster.uniformity():.3f}",
        }
        if context.repaired_rules:
            notes["repaired"] = context.repaired_rules
        return notes


class SignatureAnalysisStage(ProcessingStage):
    name = "Signature analysis"
    description = "Subtract the rules, group the remaining ink and charge each blob to the row that owns it."

    def apply(self, context: PipelineContext) -> np.ndarray:
        detection = context.detection
        if detection is None or detection.roster is None:
            raise RuntimeError("signature analysis needs a detected roster table")

        analyzer = SignatureAnalyzer(context.settings)
        context.verdicts = analyzer.analyse(
            context.require("working"),
            context.require("binary"),
            detection.masks,
            detection.roster,
        )
        return SignatureAnalyzer.render(context.require("working"), context.verdicts)

    def notes(self, context: PipelineContext) -> dict[str, object]:
        present = sum(1 for verdict in context.verdicts if verdict.present)
        return {"present": present, "absent": len(context.verdicts) - present}


#: The pipeline, in order.  Changing this list changes the program's behaviour.
DEFAULT_STAGES: tuple[type[ProcessingStage], ...] = (
    AcquisitionStage,
    GrayscaleStage,
    IlluminationStage,
    DenoiseStage,
    BinarizationStage,
    DeskewStage,
    LineExtractionStage,
    TableDetectionStage,
    SignatureAnalysisStage,
)
