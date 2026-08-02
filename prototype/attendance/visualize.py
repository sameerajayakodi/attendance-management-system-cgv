"""Attendance visualisation - the data-visualisation half of the coursework.

The module builds two products:

``StudentDashboard``  a five-panel summary for one student
``ClassHeatmap``      a student x session matrix for the whole batch

Design rules followed throughout (and justified in the report):

* the form is chosen from the data's job - a headline number is a stat tile, not
  a pie; magnitude over time is a line; comparison across students is a bar;
* status is never carried by colour alone - every present/absent mark also
  carries a ``P``/``A`` letter, so the figures survive greyscale printing and
  colour-vision deficiency;
* one measure per axis, never a second y-scale;
* grid and axes are recessive, the data is the darkest thing on the page.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")  # a backend is selected explicitly; interactive use re-selects below

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

from .database import AttendanceRepository, AttendanceRow, summarise


# --------------------------------------------------------------------------- #
#  Palette - a validated categorical/status set, light surface
# --------------------------------------------------------------------------- #


class Palette:
    """Colour roles.  Nothing in this module uses a raw hex literal."""

    SURFACE = "#fcfcfb"
    PANEL = "#f9f9f7"
    INK = "#0b0b0b"
    INK_SECONDARY = "#52514e"
    INK_MUTED = "#898781"
    GRID = "#e1e0d9"
    AXIS = "#c3c2b7"

    SERIES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948")

    PRESENT = "#0ca30c"   # status: good
    ABSENT = "#d03b3b"    # status: critical
    HIGHLIGHT = "#2a78d6"
    REFERENCE = "#898781"

    SEQUENTIAL = ("#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b")

    @classmethod
    def status(cls, present: bool) -> str:
        return cls.PRESENT if present else cls.ABSENT


def apply_house_style() -> None:
    """Global Matplotlib defaults shared by every figure the project produces."""
    plt.rcParams.update(
        {
            "figure.facecolor": Palette.SURFACE,
            "axes.facecolor": Palette.SURFACE,
            "savefig.facecolor": Palette.SURFACE,
            "font.family": "sans-serif",
            "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
            "font.size": 9.5,
            "axes.edgecolor": Palette.AXIS,
            "axes.labelcolor": Palette.INK_SECONDARY,
            "axes.titlecolor": Palette.INK,
            "axes.titlesize": 10.5,
            "axes.titleweight": "semibold",
            "axes.titlelocation": "left",
            "axes.titlepad": 9,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": Palette.GRID,
            "grid.linewidth": 0.7,
            "xtick.color": Palette.INK_MUTED,
            "ytick.color": Palette.INK_MUTED,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "legend.frameon": False,
            "legend.fontsize": 8.5,
            "lines.linewidth": 2.0,
            "lines.markersize": 8,
        }
    )


def _strip_spines(axes, keep: Sequence[str] = ("bottom",)) -> None:
    for side, spine in axes.spines.items():
        spine.set_visible(side in keep)


def _short_date(value: str) -> str:
    return datetime.strptime(value, "%Y-%m-%d").strftime("%d %b")


# --------------------------------------------------------------------------- #
#  Per-student dashboard
# --------------------------------------------------------------------------- #


@dataclass
class StudentSummary:
    """Everything the dashboard needs about one student."""

    index_no: str
    name: str
    history: list[AttendanceRow]
    class_rates: dict[str, float]
    class_names: dict[str, str]

    @property
    def present(self) -> int:
        return summarise(self.history)[0]

    @property
    def total(self) -> int:
        return summarise(self.history)[1]

    @property
    def percentage(self) -> float:
        return summarise(self.history)[2]

    @property
    def dates(self) -> list[str]:
        return [row.session_date for row in self.history]

    def cumulative_rate(self) -> list[float]:
        rates, seen, hit = [], 0, 0
        for row in self.history:
            seen += 1
            hit += 1 if row.present else 0
            rates.append(hit / seen * 100.0)
        return rates

    @classmethod
    def load(cls, repository: AttendanceRepository, index_no: str) -> "StudentSummary":
        history = repository.history(index_no)
        rates = repository.class_attendance_rates()
        names = {student.index_no: student.name for student in repository.students()}
        return cls(
            index_no=index_no,
            name=repository.student_name(index_no),
            history=history,
            class_rates=rates,
            class_names=names,
        )


class StudentDashboard:
    """Five-panel attendance summary for a single student."""

    REQUIRED_RATE = 80.0
    """The attendance percentage a student must reach to sit the examination -
    drawn as an annotated reference line rather than a second axis."""

    def __init__(self, summary: StudentSummary, ink_threshold: float = 0.0075) -> None:
        self._summary = summary
        self._ink_threshold = ink_threshold

    def build(self) -> Figure:
        apply_house_style()
        summary = self._summary
        if not summary.history:
            raise ValueError(f"no attendance has been recorded for {summary.index_no}")

        figure = plt.figure(figsize=(12.6, 9.4))
        grid = GridSpec(
            4,
            2,
            figure=figure,
            height_ratios=[0.52, 0.62, 1.20, 1.05],
            hspace=0.62,
            wspace=0.20,
            left=0.065,
            right=0.975,
            top=0.945,
            bottom=0.065,
        )

        self._draw_header(figure.add_subplot(grid[0, :]))
        self._draw_timeline(figure.add_subplot(grid[1, :]))
        self._draw_cumulative(figure.add_subplot(grid[2, 0]))
        self._draw_ink(figure.add_subplot(grid[2, 1]))
        self._draw_class_comparison(figure.add_subplot(grid[3, :]))
        return figure

    # ------------------------------------------------------------------ #

    def _draw_header(self, axes) -> None:
        """A stat tile: the headline number is a number, not a pie chart."""
        summary = self._summary
        axes.axis("off")
        axes.set_xlim(0, 1)
        axes.set_ylim(0, 1)

        axes.text(0, 0.94, summary.name, fontsize=17, weight="bold", color=Palette.INK, va="top")
        axes.text(
            0,
            0.46,
            f"Index {summary.index_no}   |   {len(summary.history)} recorded sessions   |   "
            f"CS402.3 Computer Graphics and Visualization",
            fontsize=9.5,
            color=Palette.INK_SECONDARY,
            va="top",
        )

        rate = summary.percentage
        colour = Palette.PRESENT if rate >= self.REQUIRED_RATE else Palette.ABSENT
        axes.text(1.0, 0.96, f"{rate:.0f}%", fontsize=34, weight="bold", color=colour, ha="right", va="top")
        axes.text(
            1.0,
            0.20,
            f"attended {summary.present} of {summary.total}",
            fontsize=9.5,
            color=Palette.INK_SECONDARY,
            ha="right",
            va="top",
        )

        # Progress meter: the same number, read as a proportion.
        axes.add_patch(plt.Rectangle((0.0, 0.02), 0.72, 0.09, color=Palette.GRID, zorder=1))
        axes.add_patch(plt.Rectangle((0.0, 0.02), 0.72 * rate / 100.0, 0.09, color=colour, zorder=2))
        axes.plot(
            [0.72 * self.REQUIRED_RATE / 100.0] * 2,
            [0.0, 0.13],
            color=Palette.INK_SECONDARY,
            linewidth=1.2,
            zorder=3,
        )
        axes.text(
            0.72 * self.REQUIRED_RATE / 100.0,
            -0.08,
            f"{self.REQUIRED_RATE:.0f}% required",
            fontsize=7.5,
            color=Palette.INK_SECONDARY,
            ha="center",
            va="top",
        )

    def _draw_timeline(self, axes) -> None:
        """Identity over time: one mark per session, letter-labelled."""
        summary = self._summary
        positions = np.arange(len(summary.history))

        axes.plot(positions, np.zeros_like(positions), color=Palette.AXIS, linewidth=1.2, zorder=1)
        for position, row in zip(positions, summary.history):
            colour = Palette.status(row.present)
            axes.scatter([position], [0], s=430, color=colour, zorder=2, edgecolors=Palette.SURFACE, linewidths=2)
            axes.text(
                position,
                0,
                "P" if row.present else "A",
                color="white",
                fontsize=11,
                weight="bold",
                ha="center",
                va="center",
                zorder=3,
            )
            axes.text(
                position,
                -0.55,
                _short_date(row.session_date),
                color=Palette.INK_SECONDARY,
                fontsize=8.5,
                ha="center",
                va="top",
            )

        axes.set_title("Session by session")
        axes.set_xlim(-0.6, len(positions) - 0.4)
        axes.set_ylim(-1.0, 0.7)
        axes.set_yticks([])
        axes.set_xticks([])
        axes.grid(False)
        _strip_spines(axes, keep=())

    def _draw_cumulative(self, axes) -> None:
        """Magnitude over time: a single series, so no legend box is needed."""
        summary = self._summary
        rates = summary.cumulative_rate()
        positions = np.arange(len(rates))

        axes.plot(positions, rates, color=Palette.HIGHLIGHT, linewidth=2.0, zorder=3)
        axes.scatter(
            positions,
            rates,
            s=52,
            zorder=4,
            color=[Palette.status(row.present) for row in summary.history],
            edgecolors=Palette.SURFACE,
            linewidths=1.8,
        )
        axes.axhline(self.REQUIRED_RATE, color=Palette.REFERENCE, linewidth=1.2, linestyle=(0, (5, 4)), zorder=2)
        axes.text(
            len(positions) - 1,
            self.REQUIRED_RATE + 2.5,
            f"{self.REQUIRED_RATE:.0f}% requirement",
            fontsize=8,
            color=Palette.INK_SECONDARY,
            ha="right",
        )
        axes.annotate(
            f"{rates[-1]:.0f}%",
            xy=(positions[-1], rates[-1]),
            xytext=(6, 8),
            textcoords="offset points",
            fontsize=9.5,
            weight="bold",
            color=Palette.INK,
        )

        axes.set_title("Cumulative attendance rate")
        axes.set_ylabel("per cent")
        axes.set_ylim(-4, 108)
        axes.set_xticks(positions)
        axes.set_xticklabels([_short_date(value) for value in summary.dates], rotation=0)
        axes.set_xlim(-0.4, len(positions) - 0.6 + 0.2)
        _strip_spines(axes)

    def _draw_ink(self, axes) -> None:
        """Why the system decided as it did: measured ink against the threshold."""
        summary = self._summary
        values = [row.ink_ratio * 100.0 for row in summary.history]
        positions = np.arange(len(values))
        colours = [Palette.status(row.present) for row in summary.history]

        ceiling = max(values + [1.0])
        axes.bar(positions, values, width=0.55, color=colours, zorder=3)
        threshold = self._ink_threshold * 100.0
        axes.axhline(threshold, color=Palette.REFERENCE, linewidth=1.2, linestyle=(0, (5, 4)), zorder=4)
        axes.text(
            len(positions) - 0.45,
            ceiling * 1.10,
            f"- - -  decision threshold {threshold:.2f}%",
            fontsize=8,
            color=Palette.INK_SECONDARY,
            ha="right",
            va="center",
        )
        for position, value, row in zip(positions, values, summary.history):
            axes.text(
                position,
                value + ceiling * 0.03,
                f"{value:.1f}",
                ha="center",
                fontsize=8,
                color=Palette.INK_SECONDARY,
            )

        axes.set_title("Ink measured in the signature cell")
        axes.set_ylabel("per cent of cell area")
        axes.set_xticks(positions)
        axes.set_xticklabels([_short_date(value) for value in summary.dates])
        axes.set_ylim(0, ceiling * 1.20)
        _strip_spines(axes)

    def _draw_class_comparison(self, axes) -> None:
        """Comparison across students: identity by position plus a highlight."""
        summary = self._summary
        items = sorted(summary.class_rates.items(), key=lambda item: item[1])
        values = [value for _, value in items]
        positions = np.arange(len(values))
        colours = [Palette.HIGHLIGHT if index == summary.index_no else Palette.GRID for index, _ in items]

        axes.barh(positions, values, height=0.62, color=colours, zorder=3)
        for position, (index, value) in zip(positions, items):
            selected = index == summary.index_no
            weight = "bold" if selected else "normal"
            # The name rides inside its own bar, which removes the need for a
            # wide left margin and keeps every panel on the same grid.
            axes.text(
                1.5,
                position,
                f"{index}   {summary.class_names.get(index, '')[:30]}",
                va="center",
                fontsize=8.5,
                weight=weight,
                color="white" if selected else Palette.INK_SECONDARY,
                zorder=4,
            )
            axes.text(
                value + 1.2,
                position,
                f"{value:.0f}%",
                va="center",
                fontsize=8.5,
                weight=weight,
                color=Palette.INK if selected else Palette.INK_SECONDARY,
            )

        axes.axvline(
            float(np.mean(values)),
            color=Palette.REFERENCE,
            linewidth=1.2,
            linestyle=(0, (5, 4)),
            zorder=4,
        )
        axes.text(
            float(np.mean(values)),
            len(values) - 0.35,
            f" batch mean {np.mean(values):.0f}%",
            fontsize=8,
            color=Palette.INK_SECONDARY,
            va="bottom",
        )

        axes.set_title("How this student compares with the batch")
        axes.set_yticks(positions)
        axes.set_yticklabels([])
        axes.tick_params(axis="y", length=0)
        axes.set_xlim(0, 112)
        axes.set_ylim(-0.7, len(values) - 0.15)
        axes.set_xlabel("attendance (per cent)")
        axes.grid(axis="y", visible=False)
        _strip_spines(axes)


# --------------------------------------------------------------------------- #
#  Class-wide heat map
# --------------------------------------------------------------------------- #


class ClassHeatmap:
    """Student x session attendance matrix for the whole batch."""

    def __init__(self, rows: Sequence[AttendanceRow]) -> None:
        self._rows = list(rows)

    def build(self) -> Figure:
        apply_house_style()
        if not self._rows:
            raise ValueError("the database holds no attendance records")

        dates = sorted({row.session_date for row in self._rows})
        students = sorted({row.index_no for row in self._rows})
        names = {row.index_no: row.name for row in self._rows}
        lookup = {(row.index_no, row.session_date): row for row in self._rows}

        figure, axes = plt.subplots(figsize=(1.15 * len(dates) + 5.2, 0.56 * len(students) + 1.7))
        for column, session in enumerate(dates):
            for line, index in enumerate(students):
                row = lookup.get((index, session))
                if row is None:
                    continue
                colour = Palette.status(row.present)
                axes.add_patch(
                    plt.Rectangle(
                        (column - 0.45, line - 0.34),
                        0.90,
                        0.68,
                        color=colour,
                        zorder=2,
                    )
                )
                axes.text(
                    column,
                    line,
                    "P" if row.present else "A",
                    ha="center",
                    va="center",
                    color="white",
                    fontsize=11,
                    weight="bold",
                    zorder=3,
                )

        rates = {}
        for index in students:
            values = [lookup[(index, session)] for session in dates if (index, session) in lookup]
            rates[index] = summarise(values)[2]

        axes.set_xticks(range(len(dates)))
        axes.set_xticklabels([_short_date(value) for value in dates])
        axes.set_yticks(range(len(students)))
        axes.set_yticklabels([f"{index}  {names.get(index, '')[:34]}" for index in students], fontsize=9)
        for line, index in enumerate(students):
            axes.text(
                len(dates) - 0.35,
                line,
                f"{rates[index]:.0f}%",
                va="center",
                fontsize=9,
                weight="bold",
                color=Palette.INK_SECONDARY,
            )

        axes.set_xlim(-0.6, len(dates) - 0.1)
        axes.set_ylim(len(students) - 0.5, -0.7)
        axes.set_title("Attendance matrix  -  CS402.3, batch 2016.1")
        axes.grid(False)
        _strip_spines(axes, keep=())
        figure.tight_layout()
        return figure


# --------------------------------------------------------------------------- #
#  Signature similarity
# --------------------------------------------------------------------------- #


class SimilarityMatrixPlot:
    """Sequential heat map of a pairwise signature-similarity matrix.

    Magnitude, so a single-hue sequential ramp - never a rainbow - and every cell
    also carries its number, so the reading never depends on colour alone.
    """

    def __init__(self, matrix: np.ndarray, labels: Sequence[str], flagged: Sequence[int] = ()) -> None:
        self._matrix = np.asarray(matrix, dtype=float)
        self._labels = list(labels)
        self._flagged = set(flagged)

    def build(self, title: str = "Pairwise signature similarity") -> Figure:
        apply_house_style()
        from matplotlib.colors import LinearSegmentedColormap

        colours = LinearSegmentedColormap.from_list("sams_blue", Palette.SEQUENTIAL)
        size = len(self._labels)
        figure, axes = plt.subplots(figsize=(1.05 * size + 3.2, 1.05 * size + 2.4))
        axes.imshow(self._matrix, cmap=colours, vmin=0.0, vmax=1.0, zorder=2)

        for row in range(size):
            for column in range(size):
                value = self._matrix[row, column]
                axes.text(
                    column,
                    row,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    fontsize=9,
                    weight="bold" if row == column else "normal",
                    color="white" if value > 0.55 else Palette.INK,
                    zorder=3,
                )

        ticks = [
            f"{label}  *" if position in self._flagged else label
            for position, label in enumerate(self._labels)
        ]
        axes.set_xticks(range(size))
        axes.set_yticks(range(size))
        axes.set_xticklabels(ticks, rotation=35, ha="right", fontsize=8.5)
        axes.set_yticklabels(ticks, fontsize=8.5)
        axes.set_title(title)
        axes.grid(False)
        _strip_spines(axes, keep=())
        if self._flagged:
            axes.set_xlabel("*  flagged as a possible mismatch", fontsize=8.5, color=Palette.ABSENT)
        figure.tight_layout()
        return figure


# --------------------------------------------------------------------------- #
#  Output helpers
# --------------------------------------------------------------------------- #


def save_figure(figure: Figure, path: Path, dpi: int = 200) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, dpi=dpi, facecolor=figure.get_facecolor())
    return path


def show(figure: Figure) -> None:  # pragma: no cover - interactive only
    """Switch to an interactive backend (if one exists) and display ``figure``."""
    try:
        matplotlib.use("TkAgg", force=True)
        manager = plt.figure(figure.number).canvas.manager
        if manager is not None:
            manager.set_window_title("SAMS - attendance visualisation")
        plt.show()
    except Exception:
        print("(no interactive display available - the figure was saved instead)")
