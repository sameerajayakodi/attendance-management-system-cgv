#!/usr/bin/env python3
"""SAMS web API - a thin REST layer over the coursework prototype.

The image processing, the roster parsing, the database and the signature
verification all live in ``prototype/attendance``; nothing is reimplemented
here.  This module only translates HTTP requests into calls on that package and
its results into JSON, so the command-line programs and the web interface can
never disagree about what the system does.

    python web/api/main.py            # http://127.0.0.1:8000
    uvicorn main:app --reload         # from inside web/api
"""

from __future__ import annotations

import re
import shutil
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

# --- make the coursework package importable ------------------------------- #
API_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = API_DIR.parent.parent
PROTOTYPE = PROJECT_ROOT / "prototype"
if str(PROTOTYPE) not in sys.path:
    sys.path.insert(0, str(PROTOTYPE))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from fastapi import FastAPI, File, Form, HTTPException, UploadFile  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import Response  # noqa: E402

from attendance.config import DEFAULT_DATABASE, DEFAULT_INFO_XML, DEFAULT_SETTINGS, STAGE_DIR  # noqa: E402
from attendance.database import AttendanceRepository, summarise  # noqa: E402
from attendance.imaging import imread_unicode, resize_to_width  # noqa: E402
from attendance.pipeline import AttendancePipeline, SessionResult  # noqa: E402
from attendance.progress import StageWriter  # noqa: E402
from attendance.records import RosterError, load_roster  # noqa: E402
from attendance.table import TableDetectionError  # noqa: E402
from attendance.verify import SignatureVerifier  # noqa: E402

UPLOAD_DIR = API_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SHEET_DIR = PROTOTYPE / "data" / "sheets"

app = FastAPI(
    title="SAMS API",
    version="1.0.0",
    description="Student Attendance Management System - CS402.3 coursework prototype",
)

# The Vite dev server runs on a different origin during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5180", "http://127.0.0.1:5180"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #


def repository() -> AttendanceRepository:
    return AttendanceRepository(DEFAULT_DATABASE)


def roster():
    try:
        return load_roster(DEFAULT_INFO_XML)
    except RosterError as error:  # pragma: no cover - configuration failure
        raise HTTPException(status_code=500, detail=f"roster: {error}") from error


def subject_code() -> str:
    """The subject code this deployment is configured for.

    Sessions are only unique per ``(subject_code, session_date)``, so any route
    that looks up a single session by date must scope the query to this code -
    otherwise, if the database ever held more than one subject, it would pick
    whichever session happened to be first rather than the intended one.
    """
    return roster().subject.code


def png_response(image: np.ndarray, max_age: int = 3600) -> Response:
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        raise HTTPException(status_code=500, detail="could not encode image")
    return Response(
        content=encoded.tobytes(),
        media_type="image/png",
        headers={"Cache-Control": f"public, max-age={max_age}"},
    )


def sheet_stem(source_image: str) -> str:
    return Path(source_image).stem


#: characters kept in an uploaded file name.  Everything else becomes "_".
_UNSAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def safe_upload_name(filename: str, exists: Callable[[str], bool]) -> str:
    """Reduce an uploaded file name to something safe to put on disk and in a URL.

    Real photographs arrive with names like
    ``WhatsApp Image 2026-07-19 at 09.25.09.jpeg``.  The stem becomes the name of
    the stage-image directory and therefore part of a URL path, so the spaces
    have to go; taking only ``Path(...).name`` first also drops any directory
    component a client might have put in the field.

    Two different photographs can sanitise to the same stem (two phones both
    naming a file ``IMG_0001.jpg``), so ``exists`` is consulted and a numeric
    suffix is appended until the name is free - the second upload never
    silently overwrites the first.
    """
    base = Path(filename).name
    stem, suffix = Path(base).stem, Path(base).suffix
    cleaned = _UNSAFE_NAME.sub("_", stem).strip("._-")
    if not cleaned:
        cleaned = f"sheet_{int(time.time())}"
    suffix = suffix.lower()
    candidate = f"{cleaned}{suffix}"
    attempt = 1
    while exists(candidate):
        attempt += 1
        candidate = f"{cleaned}_{attempt}{suffix}"
    return candidate


STAGE_LABELS = [
    ("01_acquisition", "Acquisition", "Rescale to the working resolution"),
    ("02_greyscale", "Greyscale", "BT.601 luma conversion"),
    ("03_illumination_correction", "Illumination correction", "Divide out the estimated shading field"),
    ("04_edge-preserving_denoise", "Edge-preserving denoise", "Bilateral filter"),
    ("05_binarisation", "Binarisation", "Adaptive Gaussian threshold"),
    ("06_skew_correction", "Skew correction", "Hough line angle, then rotate"),
    ("07_rule_extraction", "Rule extraction", "Morphological opening, two orientations"),
    ("08_table_reconstruction", "Table reconstruction", "Projection profiles into a grid"),
    ("09_signature_analysis", "Signature analysis", "Ink ownership and thresholding"),
]


def stage_list(stem: str) -> list[dict[str, Any]]:
    """Stage images on disk for one processed sheet, in pipeline order."""
    directory = STAGE_DIR / stem
    if not directory.exists():
        return []
    stages = []
    for order, (slug, name, description) in enumerate(STAGE_LABELS, start=1):
        path = directory / f"{slug}.png"
        if path.exists():
            stages.append({
                "order": order,
                "slug": slug,
                "name": name,
                "description": description,
                "url": f"/api/media/stage/{stem}/{slug}",
            })
    return stages


def session_payload(record, outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    present = sum(1 for o in outcomes if o["status"] == "PRESENT")
    stem = sheet_stem(record["source_image"])
    return {
        "date": record["session_date"],
        "subjectCode": record["subject_code"],
        "sourceImage": Path(record["source_image"]).name,
        "sheetUrl": f"/api/media/sheet/{record['session_date']}",
        "processedAt": record["processed_at"],
        "present": present,
        "absent": len(outcomes) - present,
        "total": len(outcomes),
        "rate": round(present / len(outcomes) * 100, 1) if outcomes else 0.0,
        "stages": stage_list(stem),
        "outcomes": outcomes,
    }


def outcomes_for(repo: AttendanceRepository, session_date: str) -> list[dict[str, Any]]:
    cursor = repo._connection.execute(  # noqa: SLF001 - internal read for the API layer
        """
        SELECT a.index_no, a.row_no, a.status, a.confidence, a.ink_ratio,
               a.ink_pixels, a.components, a.pen_colour,
               st.name, st.title,
               sig.id AS signature_id
        FROM attendance a
        JOIN sessions  s  ON s.id = a.session_id
        JOIN students  st ON st.index_no = a.index_no
        LEFT JOIN signatures sig ON sig.attendance_id = a.id
        WHERE s.session_date = ?
        ORDER BY a.row_no
        """,
        (session_date,),
    )
    return [
        {
            "indexNo": r["index_no"],
            "name": r["name"],
            "title": r["title"],
            "row": r["row_no"],
            "status": r["status"],
            "confidence": round(float(r["confidence"]), 3),
            "inkRatio": round(float(r["ink_ratio"]), 5),
            "inkPixels": int(r["ink_pixels"]),
            "components": int(r["components"]),
            # A pen colour measured in an unsigned cell describes residual
            # noise, not a signature, so it is not reported as one.
            "penColour": r["pen_colour"] if r["status"] == "PRESENT" else None,
            # The media endpoint only serves specimens for rows that were
            # signed; offering a URL for an absent row would 404.
            "signatureUrl": (
                f"/api/media/signature/{r['index_no']}/{session_date}"
                if r["signature_id"] and r["status"] == "PRESENT"
                else None
            ),
        }
        for r in cursor
    ]


# --------------------------------------------------------------------------- #
#  Meta
# --------------------------------------------------------------------------- #


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "database": str(DEFAULT_DATABASE),
        "databaseExists": DEFAULT_DATABASE.exists(),
        "roster": str(DEFAULT_INFO_XML),
    }


@app.get("/api/settings")
def settings() -> dict[str, Any]:
    s = DEFAULT_SETTINGS
    return {
        "workingWidth": s.working_width,
        "inkThreshold": s.min_ink_ratio,
        "minInkPixels": s.min_ink_pixels,
        "adaptiveBlock": s.adaptive_block,
        "adaptiveC": s.adaptive_c,
        "maxSkewDegrees": s.max_skew_degrees,
        "overflowRatio": s.overflow_ratio,
        "mismatchThreshold": s.mismatch_threshold,
        "outlierZ": s.outlier_z,
    }


@app.get("/api/overview")
def overview() -> dict[str, Any]:
    """Everything the dashboard needs, in one round trip."""
    with repository() as repo:
        sessions = repo.sessions()
        rows = repo.all_attendance()
        students = repo.students()

        rates = repo.class_attendance_rates()
        overall = sum(1 for r in rows if r.present) / len(rows) * 100 if rows else 0.0

        by_session: dict[str, dict[str, int]] = {}
        by_student: dict[str, list] = {}
        for row in rows:
            bucket = by_session.setdefault(row.session_date, {"present": 0, "absent": 0})
            bucket["present" if row.present else "absent"] += 1
            by_student.setdefault(row.index_no, []).append(row)

        matrix = [
            {
                "indexNo": student.index_no,
                "name": student.name,
                "rate": round(rates.get(student.index_no, 0.0), 1),
                "cells": [
                    {
                        "date": row.session_date,
                        "status": row.status,
                        "inkRatio": round(row.ink_ratio, 5),
                    }
                    for row in by_student.get(student.index_no, [])
                ],
            }
            for student in students
        ]

        at_risk = [
            {"indexNo": index, "name": repo.student_name(index), "rate": round(rate, 1)}
            for index, rate in sorted(rates.items(), key=lambda kv: kv[1])
            if rate < 80.0
        ]

        return {
            "sessionCount": len(sessions),
            "studentCount": len(students),
            "recordCount": len(rows),
            "overallRate": round(overall, 1),
            "presentCount": sum(1 for r in rows if r.present),
            "absentCount": sum(1 for r in rows if not r.present),
            "dates": sorted({row.session_date for row in rows}),
            "trend": [
                {
                    "date": session_date,
                    "present": counts["present"],
                    "absent": counts["absent"],
                    "rate": round(counts["present"] / (counts["present"] + counts["absent"]) * 100, 1),
                }
                for session_date, counts in sorted(by_session.items())
            ],
            "matrix": matrix,
            "atRisk": at_risk,
        }


# --------------------------------------------------------------------------- #
#  Sessions
# --------------------------------------------------------------------------- #


@app.get("/api/sessions")
def list_sessions() -> list[dict[str, Any]]:
    code = subject_code()
    with repository() as repo:
        return [
            session_payload(record, outcomes_for(repo, record["session_date"]))
            for record in reversed(repo.sessions())
            if record["subject_code"] == code
        ]


@app.get("/api/sessions/{session_date}")
def get_session(session_date: str) -> dict[str, Any]:
    with repository() as repo:
        record = repo.session_by_date(subject_code(), session_date)
        if record is None:
            raise HTTPException(status_code=404, detail=f"no session on {session_date}")
        return session_payload(record, outcomes_for(repo, session_date))


@app.post("/api/sessions", status_code=201)
def process_sheet(
    file: UploadFile = File(...),
    session_date: str | None = Form(default=None),
) -> dict[str, Any]:
    """Upload a signing-sheet photograph, run the pipeline, store the result.

    A plain ``def`` route (not ``async def``): the pipeline is CPU-bound
    OpenCV work, and FastAPI only offloads plain ``def`` routes to a
    threadpool.  An ``async def`` version of this handler would run the whole
    imaging pipeline on the single event-loop thread and stall every other
    request - health checks, dashboard polling, other students' pages - for
    however long one sheet takes to process.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="no file was uploaded")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}:
        raise HTTPException(status_code=400, detail=f"'{suffix}' is not a supported image type")

    payload = file.file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="the uploaded file is empty")

    chosen: date | None = None
    if session_date:
        try:
            chosen = datetime.strptime(session_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="date must be formatted as YYYY-MM-DD") from None

    decoded = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
    if decoded is None:
        raise HTTPException(status_code=400, detail="the uploaded file is not a readable image")

    target = UPLOAD_DIR / safe_upload_name(file.filename, exists=lambda name: (UPLOAD_DIR / name).exists())
    target.write_bytes(payload)

    try:
        book = roster()
        stem = target.stem
        reporter = StageWriter(DEFAULT_SETTINGS.stage_dir, stem)
        pipeline = AttendancePipeline(DEFAULT_SETTINGS, book, reporter)

        started = time.perf_counter()
        try:
            result: SessionResult = pipeline.process(target, session_date=chosen)
        except TableDetectionError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except (ValueError, FileNotFoundError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        reporter.end(result.artifacts)
        elapsed = (time.perf_counter() - started) * 1000.0

        with repository() as repo:
            pipeline.persist(result, repo)
            record = repo.session_by_date(result.subject_code, result.session_date.isoformat())
            payload_out = session_payload(record, outcomes_for(repo, record["session_date"]))
    except Exception:
        # The photo and any per-stage images are only worth keeping once a
        # session row references them; on any failure they are orphaned disk
        # usage with nothing pointing at them. The reporter writes stage PNGs
        # incrementally as each stage completes, so a failure partway through
        # (e.g. TableDetectionError) can still leave a stage directory behind.
        target.unlink(missing_ok=True)
        stage_dir = STAGE_DIR / target.stem
        if stage_dir.is_dir() and STAGE_DIR.resolve() in stage_dir.resolve().parents:
            shutil.rmtree(stage_dir, ignore_errors=True)
        raise

    payload_out["warnings"] = result.warnings
    payload_out["elapsedMs"] = round(elapsed, 1)
    payload_out["skewDegrees"] = round(result.context.skew_degrees, 2) if result.context else 0.0
    payload_out["stageTimings"] = [
        {"order": a.order, "name": a.name, "description": a.description,
         "elapsedMs": round(a.elapsed_ms, 1), "notes": {k: str(v) for k, v in a.notes.items()}}
        for a in result.artifacts
    ]
    return payload_out


def _remove_session_stage_images(stem: str) -> None:
    """Best-effort cleanup of the derived stage-image cache for a session.

    The source photograph is deliberately left alone: it is not owned by the
    session record (an upload or a reference sheet under ``SHEET_DIR`` can be
    the source for other sessions, or just worth keeping), and the UI's delete
    confirmation promises the photograph is untouched so the sheet can be
    processed again.
    """
    stage_dir = STAGE_DIR / stem
    if stage_dir.is_dir() and STAGE_DIR.resolve() in stage_dir.resolve().parents:
        shutil.rmtree(stage_dir, ignore_errors=True)


@app.delete("/api/sessions/{session_date}", status_code=204)
def delete_session(session_date: str) -> Response:
    code = subject_code()
    with repository() as repo:
        record = repo.session_by_date(code, session_date)
        if record is None:
            raise HTTPException(status_code=404, detail=f"no session on {session_date}")
        source_image = record["source_image"]
        with repo.transaction() as connection:
            connection.execute(
                "DELETE FROM sessions WHERE subject_code = ? AND session_date = ?", (code, session_date)
            )
    _remove_session_stage_images(sheet_stem(source_image))
    return Response(status_code=204)


# --------------------------------------------------------------------------- #
#  Students
# --------------------------------------------------------------------------- #


@app.get("/api/students")
def list_students() -> list[dict[str, Any]]:
    with repository() as repo:
        rates = repo.class_attendance_rates()
        counts = repo.signature_counts()
        payload = []
        for student in repo.students():
            history = repo.history(student.index_no)
            present, total, rate = summarise(history)
            payload.append({
                "indexNo": student.index_no,
                "name": student.name,
                "title": student.title,
                "batch": student.batch,
                "present": present,
                "total": total,
                "rate": round(rates.get(student.index_no, rate), 1),
                "specimens": counts.get(student.index_no, 0),
                "lastSession": history[-1].session_date if history else None,
                "lastStatus": history[-1].status if history else None,
            })
        return payload


@app.get("/api/students/{index_no}")
def get_student(index_no: str) -> dict[str, Any]:
    with repository() as repo:
        matches = repo.resolve_index(index_no)
        if len(matches) != 1:
            raise HTTPException(
                status_code=404 if not matches else 409,
                detail=f"'{index_no}' does not identify one student",
            )
        resolved = matches[0]
        history = repo.history(resolved)
        present, total, rate = summarise(history)

        running: list[dict[str, Any]] = []
        seen = hit = 0
        for row in history:
            seen += 1
            hit += 1 if row.present else 0
            running.append({
                "date": row.session_date,
                "status": row.status,
                "inkRatio": round(row.ink_ratio, 5),
                "confidence": round(row.confidence, 3),
                "cumulativeRate": round(hit / seen * 100, 1),
                "sheet": Path(row.source_image).name,
                "signatureUrl": f"/api/media/signature/{resolved}/{row.session_date}" if row.present else None,
            })

        return {
            "indexNo": resolved,
            "name": repo.student_name(resolved),
            "present": present,
            "total": total,
            "rate": round(rate, 1),
            "required": 80.0,
            "history": running,
            "classRates": [
                {"indexNo": index, "name": repo.student_name(index), "rate": round(value, 1)}
                for index, value in sorted(repo.class_attendance_rates().items(), key=lambda kv: kv[1])
            ],
        }


@app.get("/api/students/{index_no}/verify")
def verify_student(index_no: str) -> dict[str, Any]:
    """Compare the student's stored signature specimens with one another."""
    verifier = SignatureVerifier(DEFAULT_SETTINGS)
    with repository() as repo:
        matches = repo.resolve_index(index_no)
        if len(matches) != 1:
            raise HTTPException(status_code=404, detail=f"'{index_no}' does not identify one student")
        resolved = matches[0]
        specimens = repo.signature_specimens(resolved)
        name = repo.student_name(resolved)

    if not specimens:
        return {
            "indexNo": resolved, "name": name, "specimens": [], "matrix": [],
            "flagged": [], "consistent": True, "cohortMean": 0.0, "cohortSd": 0.0,
            "threshold": DEFAULT_SETTINGS.mismatch_threshold,
            "summary": "no signature specimens are on record for this student",
        }

    report = verifier.verify(resolved, specimens)
    return {
        "indexNo": resolved,
        "name": name,
        "threshold": round(report.threshold, 3),
        "cohortMean": round(report.cohort_mean, 3),
        "cohortSd": round(report.cohort_sd, 3),
        "consistent": report.consistent,
        "summary": report.summary(),
        "flagged": list(report.flagged),
        "specimens": [
            {
                "label": specimen.label,
                "date": specimen.label,
                "inkRatio": round(specimen.ink_ratio, 3),
                "aspect": round(specimen.aspect, 2),
                "keypoints": len(specimen.keypoints),
                "meanSimilarity": round(report.mean_similarity[position], 3),
                "modifiedZ": round(report.modified_z[position], 2),
                "verdict": report.verdict_for(position),
                "url": f"/api/media/signature/{resolved}/{specimen.label}",
                "normalisedUrl": f"/api/media/signature/{resolved}/{specimen.label}/normalised",
            }
            for position, specimen in enumerate(report.specimens)
        ],
        "matrix": [[round(float(value), 3) for value in row] for row in report.similarity],
    }


# --------------------------------------------------------------------------- #
#  Media
# --------------------------------------------------------------------------- #


#: Path components accepted by the media routes.  Spaces and parentheses are
#: allowed because sheets processed before uploads were sanitised (and any
#: processed from the command line) can legitimately carry them; separators and
#: ".." are not, and the resolved path is checked against STAGE_DIR as well.
_SAFE = re.compile(r"^[\w .()\-]+$", re.UNICODE)


def safe_component(value: str) -> bool:
    return bool(_SAFE.match(value)) and ".." not in value


def encode_for_web(image: np.ndarray, width: int) -> tuple[bytes, str]:
    """Rescale for the browser and pick the format the content deserves.

    The stage images are a mix of photographs and binary masks.  A downscaled
    photograph is far smaller as JPEG, but JPEG puts ringing around every stroke
    of a binary mask - exactly the detail the mask exists to show.  The format is
    therefore chosen from the content: near-two-tone images stay PNG.
    """
    # Measure the levels on the SOURCE, not on the rescaled copy: area
    # interpolation anti-aliases a two-tone mask into a continuous-tone image,
    # so testing after the resize would classify every mask as a photograph.
    levels = int(np.unique(image[::4, ::4]).size)
    resized, _ = resize_to_width(image, max(240, min(width, 2400)))
    if levels <= 8:
        ok, buffer = cv2.imencode(".png", resized, [int(cv2.IMWRITE_PNG_COMPRESSION), 6])
        return (buffer.tobytes() if ok else b""), "image/png"
    ok, buffer = cv2.imencode(".jpg", resized, [int(cv2.IMWRITE_JPEG_QUALITY), 84])
    return (buffer.tobytes() if ok else b""), "image/jpeg"


@app.get("/api/media/stage/{stem}/{slug}")
def stage_image(stem: str, slug: str, width: int = 1100, v: str | None = None) -> Response:
    """One pipeline stage image.  ``v`` is a cache-buster the client supplies."""
    if not (safe_component(stem) and safe_component(slug)):
        raise HTTPException(status_code=400, detail="invalid image name")
    path = (STAGE_DIR / stem / f"{slug}.png").resolve()
    if not path.is_file() or STAGE_DIR.resolve() not in path.parents:
        raise HTTPException(status_code=404, detail="stage image not found")

    content, media_type = encode_for_web(imread_unicode(path), width)
    if not content:
        raise HTTPException(status_code=500, detail="could not encode the stage image")
    return Response(content=content, media_type=media_type,
                    headers={"Cache-Control": "public, max-age=3600"})


@app.get("/api/media/sheet/{session_date}")
def sheet_image(session_date: str, width: int = 1000) -> Response:
    """The original photograph for a session, rescaled for the browser."""
    with repository() as repo:
        record = repo.session_by_date(subject_code(), session_date)
    if record is None:
        raise HTTPException(status_code=404, detail="session not found")

    source = Path(record["source_image"])
    if not source.exists():
        # The sheet may have been processed from a path that has since moved.
        for candidate in (SHEET_DIR / source.name, UPLOAD_DIR / source.name):
            if candidate.exists():
                source = candidate
                break
        else:
            raise HTTPException(status_code=404, detail="the original photograph is no longer on disk")

    image = imread_unicode(source)
    resized, _ = resize_to_width(image, max(240, min(width, 2000)))
    ok, encoded = cv2.imencode(".jpg", resized, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
    if not ok:
        raise HTTPException(status_code=500, detail="could not encode the photograph")
    return Response(content=encoded.tobytes(), media_type="image/jpeg",
                    headers={"Cache-Control": "public, max-age=3600"})


@app.get("/api/media/signature/{index_no}/{session_date}")
def signature_image(index_no: str, session_date: str) -> Response:
    with repository() as repo:
        specimen = repo.signature_specimen(index_no, session_date)
    if specimen is None:
        raise HTTPException(status_code=404, detail="signature specimen not found")
    _label, colour, _mask = specimen
    return png_response(colour)


@app.get("/api/media/signature/{index_no}/{session_date}/normalised")
def normalised_signature(index_no: str, session_date: str) -> Response:
    """The specimen as the descriptors see it: cropped, warped, binarised."""
    verifier = SignatureVerifier(DEFAULT_SETTINGS)
    with repository() as repo:
        specimen = repo.signature_specimen(index_no, session_date)
    if specimen is None:
        raise HTTPException(status_code=404, detail="signature specimen not found")
    label, colour, mask = specimen
    described = verifier.describe(label, colour, mask)
    canvas = cv2.cvtColor(cv2.bitwise_not(described.normalised), cv2.COLOR_GRAY2BGR)
    return png_response(canvas)


# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import uvicorn

    print(f"prototype package : {PROTOTYPE}")
    print(f"database          : {DEFAULT_DATABASE}")
    print(f"roster            : {DEFAULT_INFO_XML}")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
