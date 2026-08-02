#!/usr/bin/env python3
"""tools/evaluate.py - measure the prototype against hand-labelled ground truth.

Two evaluations are produced:

**Attendance.**  Every signature cell of the five reference sheets was read by
eye and recorded in ``data/ground_truth.csv``.  The tool re-processes the sheets,
compares cell by cell, and reports accuracy together with the confusion matrix
and the margin between the ink measured in signed and unsigned cells.

**Signature verification.**  Every stored specimen is compared with every other.
Pairs from the same student are *genuine*, pairs from different students are
*impostor*.  The tool reports the separation between the two distributions
(mean, standard deviation, d'), the threshold that maximises accuracy, and the
equal error rate - the honest measure of how far the module can be trusted.

Usage
-----
    python tools/evaluate.py
    python tools/evaluate.py --attendance-only
"""

from __future__ import annotations

import argparse
import csv
import itertools
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from attendance.config import DEFAULT_SETTINGS, FIGURE_DIR, Settings  # noqa: E402
from attendance.database import AttendanceRepository  # noqa: E402
from attendance.pipeline import AttendancePipeline, format_table  # noqa: E402
from attendance.progress import NullReporter  # noqa: E402
from attendance.records import load_roster  # noqa: E402
from attendance.verify import SignatureVerifier  # noqa: E402
from attendance.visualize import Palette, apply_house_style, save_figure  # noqa: E402

GROUND_TRUTH = PROJECT_ROOT / "data" / "ground_truth.csv"
SHEET_DIR = PROJECT_ROOT / "data" / "sheets"
INFO_XML = PROJECT_ROOT / "data" / "info.xml"


# --------------------------------------------------------------------------- #
#  Attendance accuracy
# --------------------------------------------------------------------------- #


def load_ground_truth(path: Path) -> dict[tuple[str, str], str]:
    truth: dict[tuple[str, str], str] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for record in csv.DictReader(handle):
            truth[(record["sheet"].strip(), record["index_no"].strip())] = record["status"].strip().upper()
    return truth


def evaluate_attendance(settings: Settings) -> dict[str, object]:
    truth = load_ground_truth(GROUND_TRUTH)
    roster = load_roster(INFO_XML)

    matrix = {"TP": 0, "TN": 0, "FP": 0, "FN": 0}
    present_ratios: list[float] = []
    absent_ratios: list[float] = []
    disagreements: list[list[str]] = []
    per_sheet: dict[str, tuple[int, int]] = {}

    for sheet in sorted(SHEET_DIR.glob("*.jpeg")):
        pipeline = AttendancePipeline(settings, roster, NullReporter())
        result = pipeline.process(sheet)
        correct = 0
        for outcome in result.outcomes:
            expected = truth.get((sheet.name, outcome.student.index_no))
            if expected is None:
                continue
            actual = outcome.status
            ratio = outcome.verdict.features.ink_ratio
            (present_ratios if expected == "PRESENT" else absent_ratios).append(ratio)

            if expected == "PRESENT" and actual == "PRESENT":
                matrix["TP"] += 1
            elif expected == "ABSENT" and actual == "ABSENT":
                matrix["TN"] += 1
            elif expected == "ABSENT" and actual == "PRESENT":
                matrix["FP"] += 1
            else:
                matrix["FN"] += 1

            if expected == actual:
                correct += 1
            else:
                disagreements.append(
                    [sheet.name, outcome.student.index_no, expected, actual, f"{ratio * 100:.2f}%"]
                )
        per_sheet[sheet.name] = (correct, len(result.outcomes))

    total = sum(matrix.values())
    accuracy = (matrix["TP"] + matrix["TN"]) / total * 100.0 if total else 0.0
    return {
        "matrix": matrix,
        "accuracy": accuracy,
        "total": total,
        "per_sheet": per_sheet,
        "disagreements": disagreements,
        "present_ratios": np.array(present_ratios),
        "absent_ratios": np.array(absent_ratios),
    }


def report_attendance(results: dict[str, object]) -> None:
    matrix = results["matrix"]  # type: ignore[index]
    present = results["present_ratios"]  # type: ignore[index]
    absent = results["absent_ratios"]  # type: ignore[index]

    print()
    print("=" * 78)
    print("  ATTENDANCE ACCURACY  (cell-level, against hand-labelled ground truth)")
    print("=" * 78)

    rows = [["sheet", "correct", "cells", "accuracy"]]
    for sheet, (correct, cells) in results["per_sheet"].items():  # type: ignore[index]
        rows.append([sheet, str(correct), str(cells), f"{correct / cells * 100:.1f}%" if cells else "-"])
    print(format_table(rows))

    print()
    print(f"  overall accuracy      {results['accuracy']:.1f}%  ({matrix['TP'] + matrix['TN']}/{results['total']})")
    print(f"  true present  (TP)    {matrix['TP']}")
    print(f"  true absent   (TN)    {matrix['TN']}")
    print(f"  false present (FP)    {matrix['FP']}")
    print(f"  false absent  (FN)    {matrix['FN']}")

    if present.size and absent.size:
        print()
        print(f"  ink in signed cells    mean {present.mean() * 100:6.2f}%   min {present.min() * 100:6.2f}%")
        print(f"  ink in unsigned cells  mean {absent.mean() * 100:6.2f}%   max {absent.max() * 100:6.2f}%")
        print(f"  separation margin      {present.min() / max(absent.max(), 1e-9):.1f}x")
        print(f"  decision threshold     {DEFAULT_SETTINGS.min_ink_ratio * 100:.2f}%")

    disagreements = results["disagreements"]  # type: ignore[index]
    if disagreements:
        print()
        print("  disagreements:")
        print(format_table([["sheet", "index", "expected", "actual", "ink"]] + list(disagreements)))
    else:
        print("\n  no disagreements")


def plot_separation(results: dict[str, object], out_dir: Path) -> Path:
    """Ink measured in signed vs unsigned cells, against the decision threshold."""
    apply_house_style()
    import matplotlib.pyplot as plt

    present = np.asarray(results["present_ratios"]) * 100.0  # type: ignore[index]
    absent = np.asarray(results["absent_ratios"]) * 100.0  # type: ignore[index]

    figure, axes = plt.subplots(figsize=(9.2, 4.4))
    generator = np.random.default_rng(7)
    axes.scatter(
        absent,
        generator.normal(0.0, 0.045, absent.size),
        s=64,
        color=Palette.ABSENT,
        zorder=3,
        edgecolors=Palette.SURFACE,
        linewidths=1.4,
        label=f"unsigned cells (n={absent.size})",
    )
    axes.scatter(
        present,
        generator.normal(1.0, 0.045, present.size),
        s=64,
        color=Palette.PRESENT,
        zorder=3,
        edgecolors=Palette.SURFACE,
        linewidths=1.4,
        label=f"signed cells (n={present.size})",
    )
    threshold = DEFAULT_SETTINGS.min_ink_ratio * 100.0
    axes.axvline(threshold, color=Palette.INK_SECONDARY, linewidth=1.3, linestyle=(0, (5, 4)), zorder=4)
    axes.text(
        threshold * 1.15,
        1.42,
        f"decision threshold {threshold:.2f}%",
        fontsize=8.5,
        color=Palette.INK_SECONDARY,
    )

    axes.set_xscale("log")
    axes.set_xlabel("ink in the signature cell (per cent of cell area, log scale)")
    axes.set_yticks([0, 1])
    axes.set_yticklabels(["unsigned", "signed"])
    axes.set_ylim(-0.55, 1.6)
    axes.set_title("Separation between signed and unsigned signature cells")
    axes.legend(loc="lower right")
    axes.grid(axis="y", visible=False)
    for side, spine in axes.spines.items():
        spine.set_visible(side == "bottom")
    figure.tight_layout()
    return save_figure(figure, out_dir / "ink_separation.png")


# --------------------------------------------------------------------------- #
#  Signature verification accuracy
# --------------------------------------------------------------------------- #


def evaluate_signatures(settings: Settings, database: Path) -> dict[str, object] | None:
    if not database.exists():
        print(f"(skipping signature evaluation - no database at {database})")
        return None

    verifier = SignatureVerifier(settings)
    with AttendanceRepository(database) as repository:
        cohort = {}
        for student in repository.students():
            samples = repository.signature_specimens(student.index_no)
            described = [verifier.describe(f"{student.index_no}@{date}", image, mask) for date, image, mask in samples]
            if described:
                cohort[student.index_no] = described

    genuine: list[float] = []
    impostor: list[float] = []
    for specimens in cohort.values():
        for left, right in itertools.combinations(specimens, 2):
            genuine.append(verifier.similarity(left, right))
    for left_key, right_key in itertools.combinations(cohort, 2):
        for left in cohort[left_key]:
            for right in cohort[right_key]:
                impostor.append(verifier.similarity(left, right))

    genuine_array = np.array(genuine)
    impostor_array = np.array(impostor)
    if genuine_array.size == 0 or impostor_array.size == 0:
        return None

    thresholds = np.arange(0.0, 1.0, 0.002)
    accuracies = [
        ((genuine_array >= t).sum() + (impostor_array < t).sum()) / (genuine_array.size + impostor_array.size)
        for t in thresholds
    ]
    # Impostor pairs outnumber genuine ones six to one, so plain accuracy is
    # flattered by simply calling everything an impostor.  Balanced accuracy -
    # the mean of the two class recalls - is the honest headline number.
    balanced = [
        0.5 * float((genuine_array >= t).mean()) + 0.5 * float((impostor_array < t).mean()) for t in thresholds
    ]
    best = int(np.argmax(balanced))

    equal_error = (1.0, 0.0)
    for t in thresholds:
        false_accept = float((impostor_array >= t).mean())
        false_reject = float((genuine_array < t).mean())
        if false_accept <= false_reject:
            equal_error = ((false_accept + false_reject) / 2.0, float(t))
            break

    pooled = np.sqrt((genuine_array.var() + impostor_array.var()) / 2.0)
    return {
        "genuine": genuine_array,
        "impostor": impostor_array,
        "sensitivity": float((genuine_array.mean() - impostor_array.mean()) / pooled) if pooled else 0.0,
        "best_threshold": float(thresholds[best]),
        "best_accuracy": float(accuracies[best] * 100.0),
        "balanced_accuracy": float(balanced[best] * 100.0),
        "equal_error_rate": equal_error[0] * 100.0,
        "equal_error_threshold": equal_error[1],
        "students": len(cohort),
    }


def report_signatures(results: dict[str, object]) -> None:
    genuine = results["genuine"]  # type: ignore[index]
    impostor = results["impostor"]  # type: ignore[index]
    print()
    print("=" * 78)
    print("  SIGNATURE VERIFICATION  (genuine vs impostor specimen pairs)")
    print("=" * 78)
    print(f"  students                {results['students']}")
    print(f"  genuine pairs           n={genuine.size:<4} mean {genuine.mean():.3f}  sd {genuine.std():.3f}")
    print(f"  impostor pairs          n={impostor.size:<4} mean {impostor.mean():.3f}  sd {impostor.std():.3f}")
    print(f"  sensitivity index d'    {results['sensitivity']:.2f}")
    print(f"  best threshold          {results['best_threshold']:.3f}")
    print(f"    balanced accuracy     {results['balanced_accuracy']:.1f}%   (mean of the two class recalls)")
    print(f"    plain accuracy        {results['best_accuracy']:.1f}%   (flattered by 6:1 class imbalance)")
    print(f"  equal error rate        {results['equal_error_rate']:.1f}%  at t = {results['equal_error_threshold']:.3f}")
    print()
    print("  Interpretation: the genuine and impostor distributions overlap heavily,")
    print("  so this module is a screening aid that ranks specimens for human review,")
    print("  not an authority that should mark attendance fraudulent on its own.")


def evaluate_intrusion(settings: Settings, database: Path) -> dict[str, object] | None:
    """Random-forgery test: can ``investigate.py`` spot a planted specimen?

    No forged signatures were collected for this coursework, so detection power
    cannot be measured directly.  The standard substitute in the signature
    verification literature is the *random forgery*: another writer's genuine
    signature is offered as if it were this writer's.  For every student, each of
    the other students' specimens is planted in turn and the module is asked
    whether anything is wrong.  The unmodified sets are scored too, which gives
    the false-alarm rate on the same footing.
    """
    if not database.exists():
        return None

    verifier = SignatureVerifier(settings)
    with AttendanceRepository(database) as repository:
        raw = {student.index_no: repository.signature_specimens(student.index_no) for student in repository.students()}

    usable = {index: samples for index, samples in raw.items() if len(samples) >= 4}
    if len(usable) < 2:
        return None

    detected = 0
    trials = 0
    false_alarms = 0
    clean_runs = 0

    for index, samples in usable.items():
        genuine = [(f"{index}@{date}", image, mask) for date, image, mask in samples]

        report = verifier.verify(index, genuine)
        clean_runs += 1
        false_alarms += len(report.flagged)

        for other, other_samples in raw.items():
            if other == index:
                continue
            for date, image, mask in other_samples:
                planted = list(genuine) + [(f"INTRUDER({other})@{date}", image, mask)]
                outcome = verifier.verify(index, planted)
                trials += 1
                if len(planted) - 1 in outcome.flagged:
                    detected += 1

    return {
        "students": len(usable),
        "trials": trials,
        "detected": detected,
        "detection_rate": (detected / trials * 100.0) if trials else 0.0,
        "false_alarms": false_alarms,
        "clean_specimens": sum(len(samples) for samples in usable.values()),
        "false_alarm_rate": (false_alarms / max(1, sum(len(s) for s in usable.values())) * 100.0),
        "clean_runs": clean_runs,
    }


def report_intrusion(results: dict[str, object]) -> None:
    print()
    print("=" * 78)
    print("  RANDOM-FORGERY TEST  (another writer's signature planted in a student's set)")
    print("=" * 78)
    print(f"  students with >= 4 specimens   {results['students']}")
    print(f"  planted specimens tested       {results['trials']}")
    print(f"  planted specimens detected     {results['detected']}   ({results['detection_rate']:.1f}%)")
    print(f"  false alarms on clean sets     {results['false_alarms']} of {results['clean_specimens']} "
          f"genuine specimens   ({results['false_alarm_rate']:.1f}%)")


def plot_similarity_distributions(results: dict[str, object], out_dir: Path) -> Path:
    apply_house_style()
    import matplotlib.pyplot as plt

    genuine = np.asarray(results["genuine"])  # type: ignore[index]
    impostor = np.asarray(results["impostor"])  # type: ignore[index]

    figure, axes = plt.subplots(figsize=(9.2, 4.6))
    bins = np.linspace(0.0, 1.0, 31)
    axes.hist(impostor, bins=bins, color=Palette.SERIES[1], alpha=0.85, label=f"impostor pairs (n={impostor.size})", zorder=3)
    axes.hist(genuine, bins=bins, color=Palette.SERIES[0], alpha=0.85, label=f"genuine pairs (n={genuine.size})", zorder=4)
    axes.axvline(
        float(results["best_threshold"]),  # type: ignore[index]
        color=Palette.INK_SECONDARY,
        linewidth=1.3,
        linestyle=(0, (5, 4)),
        zorder=5,
    )
    axes.text(
        float(results["best_threshold"]) + 0.012,  # type: ignore[index]
        axes.get_ylim()[1] * 0.92,
        f"operating point {results['best_threshold']:.2f}",
        fontsize=8.5,
        color=Palette.INK_SECONDARY,
    )
    axes.set_xlabel("fused similarity")
    axes.set_ylabel("pairs")
    axes.set_title(
        f"Signature similarity: genuine vs impostor  (d' = {results['sensitivity']:.2f}, "
        f"EER = {results['equal_error_rate']:.0f}%)"
    )
    axes.legend()
    for side, spine in axes.spines.items():
        spine.set_visible(side == "bottom")
    figure.tight_layout()
    return save_figure(figure, out_dir / "signature_separation.png")


# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="evaluate.py", description="Evaluate the SAMS prototype.")
    parser.add_argument("--db", default=str(PROJECT_ROOT / "data" / "attendance.db"))
    parser.add_argument("--out", default=str(FIGURE_DIR))
    parser.add_argument("--attendance-only", action="store_true")
    parser.add_argument("--signatures-only", action="store_true")
    arguments = parser.parse_args(argv)

    settings = DEFAULT_SETTINGS.evolve(save_stages=False, show_windows=False)
    out_dir = Path(arguments.out)

    if not arguments.signatures_only:
        attendance = evaluate_attendance(settings)
        report_attendance(attendance)
        print(f"\n  figure: {plot_separation(attendance, out_dir)}")

    if not arguments.attendance_only:
        signatures = evaluate_signatures(settings, Path(arguments.db))
        if signatures is not None:
            report_signatures(signatures)
            print(f"\n  figure: {plot_similarity_distributions(signatures, out_dir)}")
        intrusion = evaluate_intrusion(settings, Path(arguments.db))
        if intrusion is not None:
            report_intrusion(intrusion)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
