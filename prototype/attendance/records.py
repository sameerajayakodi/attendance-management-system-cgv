"""Parsing of the ``info.xml`` roster supplied by the administrative staff.

The coursework brief (Figure 1) shows a document whose batch element is a bare
number::

    <nsbm><students><batches><15><student>...</student></15></batches></students></nsbm>

An element name may not begin with a digit, so that document is not well-formed
XML and no conforming parser will read it.  Rather than reject the very format
the brief specifies, :class:`RosterParser` normalises numeric element names into
``<batch id="15">`` before parsing, and therefore accepts both the literal
Figure-1 layout and a schema-valid equivalent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Sequence
from xml.etree import ElementTree

# ``<15>`` / ``</15>`` -> ``<batch id="15">`` / ``</batch>``
_NUMERIC_TAG = re.compile(r"<(/?)(\d[\w.\-]*)\s*(/?)>")


@dataclass(frozen=True)
class Student:
    """One row of the signing sheet's roster."""

    index_no: str
    name: str
    title: str = ""
    batch: str = ""

    @property
    def display_name(self) -> str:
        return f"{self.title} {self.name}".strip()

    def matches(self, query: str) -> bool:
        """Whether ``query`` identifies this student.

        The brief's examples use short indices (``python infovis.py 001``) while
        the real sheets carry eight-digit numbers, so an exact match, a numeric
        match ignoring leading zeros, and a unique suffix match are all accepted.
        """
        query = query.strip()
        if not query:
            return False
        if query == self.index_no:
            return True
        if query.isdigit() and self.index_no.isdigit():
            if int(query) == int(self.index_no):
                return True
        return self.index_no.endswith(query) and len(query) >= 3


@dataclass
class Subject:
    """Subject metadata carried alongside the roster."""

    code: str = "CS402.3"
    title: str = "Computer Graphics and Visualization"
    lecturer: str = ""
    programme: str = ""


@dataclass
class Roster:
    """An ordered collection of :class:`Student` records.

    The *order* is significant: row *n* of the signing sheet corresponds to entry
    *n* of the roster, which is what lets the pipeline map an anonymous signature
    cell back to a student index.
    """

    students: list[Student] = field(default_factory=list)
    subject: Subject = field(default_factory=Subject)
    batch: str = ""
    source: Path | None = None

    def __len__(self) -> int:
        return len(self.students)

    def __iter__(self) -> Iterator[Student]:
        return iter(self.students)

    def __getitem__(self, position: int) -> Student:
        return self.students[position]

    def find(self, query: str) -> Student | None:
        """Return the single student identified by ``query``, else ``None``."""
        hits = [student for student in self.students if student.matches(query)]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            exact = [student for student in hits if student.index_no == query.strip()]
            if len(exact) == 1:
                return exact[0]
            raise AmbiguousStudentError(query, [student.index_no for student in hits])
        return None

    def indices(self) -> list[str]:
        return [student.index_no for student in self.students]


class RosterError(RuntimeError):
    """Raised when ``info.xml`` cannot be turned into a usable roster."""


class AmbiguousStudentError(RosterError):
    def __init__(self, query: str, candidates: Sequence[str]) -> None:
        super().__init__(f"'{query}' matches {len(candidates)} students: {', '.join(candidates)}")
        self.query = query
        self.candidates = list(candidates)


class RosterParser:
    """Reads ``info.xml`` into a :class:`Roster`."""

    #: element names searched, in order, for a student's index number
    INDEX_TAGS = ("index", "index_no", "studentno", "student_no", "number", "no")
    #: element names searched, in order, for a student's name
    NAME_TAGS = ("name", "student_name", "fullname")

    def parse_file(self, path: str | Path) -> Roster:
        path = Path(path)
        if not path.exists():
            raise RosterError(f"roster file not found: {path}")
        roster = self.parse_string(path.read_text(encoding="utf-8"))
        roster.source = path
        return roster

    def parse_string(self, text: str) -> Roster:
        sanitised = self.sanitise(text)
        try:
            root = ElementTree.fromstring(sanitised)
        except ElementTree.ParseError as error:  # pragma: no cover - defensive
            raise RosterError(f"info.xml is not well-formed: {error}") from error

        roster = Roster()
        self._read_subject(root, roster)

        # Built once and reused for every student - walking the whole tree per
        # student made parsing O(students x elements) instead of O(elements).
        parents = {child: parent for parent in root.iter() for child in parent}

        for element in root.iter():
            if self._localname(element.tag) != "student":
                continue
            index_no = self._first_child_text(element, self.INDEX_TAGS)
            name = self._first_child_text(element, self.NAME_TAGS)
            if not index_no:
                continue
            title = self._first_child_text(element, ("title", "salutation")) or ""
            batch = self._batch_of(parents, element) or roster.batch
            roster.students.append(
                Student(index_no=index_no, name=name or "(unknown)", title=title, batch=batch)
            )

        if not roster.students:
            raise RosterError("info.xml contains no <student> records")
        if not roster.batch and roster.students:
            roster.batch = roster.students[0].batch
        return roster

    # ------------------------------------------------------------------ #
    #  Internals
    # ------------------------------------------------------------------ #

    @staticmethod
    def sanitise(text: str) -> str:
        """Rewrite Figure-1's numeric batch tags into schema-valid elements."""

        def rewrite(match: re.Match[str]) -> str:
            closing, name, self_closing = match.groups()
            if closing:
                return "</batch>"
            return f'<batch id="{name}"{"/" if self_closing else ""}>'

        return _NUMERIC_TAG.sub(rewrite, text)

    @staticmethod
    def _localname(tag: str) -> str:
        """Strip any XML namespace and normalise the case."""
        if isinstance(tag, str) and "}" in tag:
            tag = tag.split("}", 1)[1]
        return str(tag).strip().lower()

    def _first_child_text(self, element: ElementTree.Element, names: Sequence[str]) -> str:
        for name in names:
            for child in element:
                if self._localname(child.tag) == name and child.text:
                    return child.text.strip()
        for name in names:
            if name in element.attrib:
                return str(element.attrib[name]).strip()
        return ""

    def _batch_of(
        self, parents: dict[ElementTree.Element, ElementTree.Element], student: ElementTree.Element
    ) -> str:
        """Walk up from ``student`` looking for the enclosing batch element.

        ``parents`` is the whole document's ``{child: parent}`` map, built once
        by the caller and reused for every student.
        """
        node: ElementTree.Element | None = student
        while node is not None:
            if self._localname(node.tag) == "batch":
                return str(node.attrib.get("id", node.attrib.get("name", ""))).strip()
            node = parents.get(node)
        return ""

    def _read_subject(self, root: ElementTree.Element, roster: Roster) -> None:
        for element in root.iter():
            name = self._localname(element.tag)
            if name == "subject":
                roster.subject = Subject(
                    code=self._first_child_text(element, ("code",)) or roster.subject.code,
                    title=self._first_child_text(element, ("title", "name")) or roster.subject.title,
                    lecturer=self._first_child_text(element, ("lecturer", "lecture")) or "",
                    programme=self._first_child_text(element, ("programme", "program", "degree")) or "",
                )
            elif name == "batch" and not roster.batch:
                roster.batch = str(element.attrib.get("id", element.attrib.get("name", ""))).strip()


def load_roster(path: str | Path) -> Roster:
    """Convenience wrapper around :class:`RosterParser`."""
    return RosterParser().parse_file(path)
