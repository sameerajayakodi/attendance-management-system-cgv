"""Tests for info.xml parsing (attendance.records)."""

from __future__ import annotations

import unittest

from support import PROJECT_ROOT  # noqa: F401  (puts the project on sys.path)

from attendance.records import AmbiguousStudentError, RosterError, RosterParser, Student, load_roster

FIGURE_1_XML = """<?xml version="1.0"?>
<nsbm>
    <students>
        <batches>
            <15>
                <student><index>001</index><name>John Snow</name></student>
                <student><index>007</index><name>James Bond</name></student>
                <student><index>009</index><name>Andre</name></student>
            </15>
        </batches>
    </students>
</nsbm>
"""


class SanitiseTests(unittest.TestCase):
    """The brief's Figure 1 is not well-formed XML; the parser repairs it."""

    def test_numeric_open_and_close_tags_are_rewritten(self):
        sanitised = RosterParser.sanitise("<a><15><b/></15></a>")
        self.assertIn('<batch id="15">', sanitised)
        self.assertIn("</batch>", sanitised)
        self.assertNotIn("<15>", sanitised)

    def test_ordinary_tags_are_left_alone(self):
        source = "<nsbm><student><index>001</index></student></nsbm>"
        self.assertEqual(RosterParser.sanitise(source), source)

    def test_self_closing_numeric_tag(self):
        self.assertIn('<batch id="2016"/>', RosterParser.sanitise("<a><2016/></a>"))


class ParseTests(unittest.TestCase):
    def test_parses_the_briefs_figure_1_layout(self):
        roster = RosterParser().parse_string(FIGURE_1_XML)
        self.assertEqual(len(roster), 3)
        self.assertEqual(roster.indices(), ["001", "007", "009"])
        self.assertEqual(roster[1].name, "James Bond")
        self.assertEqual(roster.batch, "15")

    def test_order_is_preserved_because_it_maps_to_sheet_rows(self):
        roster = RosterParser().parse_string(FIGURE_1_XML)
        self.assertEqual([student.name for student in roster], ["John Snow", "James Bond", "Andre"])

    def test_reads_subject_metadata(self):
        roster = RosterParser().parse_string(
            """<nsbm>
                 <subject><code>CS402.3</code><title>CGV</title><lecturer>Dr X</lecturer></subject>
                 <students><batch id="2016.1">
                   <student><index>10000409</index><title>Ms</title><name>A B</name></student>
                 </batch></students>
               </nsbm>"""
        )
        self.assertEqual(roster.subject.code, "CS402.3")
        self.assertEqual(roster.subject.lecturer, "Dr X")
        self.assertEqual(roster[0].title, "Ms")
        self.assertEqual(roster[0].display_name, "Ms A B")
        self.assertEqual(roster[0].batch, "2016.1")

    def test_accepts_alternative_element_names(self):
        roster = RosterParser().parse_string(
            "<r><student><student_no>77</student_no><fullname>X Y</fullname></student></r>"
        )
        self.assertEqual(roster[0].index_no, "77")
        self.assertEqual(roster[0].name, "X Y")

    def test_ignores_xml_namespaces(self):
        roster = RosterParser().parse_string(
            '<nsbm xmlns="urn:nsbm"><student><index>5</index><name>N</name></student></nsbm>'
        )
        self.assertEqual(len(roster), 1)

    def test_rejects_a_document_with_no_students(self):
        with self.assertRaises(RosterError):
            RosterParser().parse_string("<nsbm><students/></nsbm>")

    def test_rejects_malformed_xml(self):
        with self.assertRaises(RosterError):
            RosterParser().parse_string("<nsbm><student>")

    def test_missing_file_is_reported_clearly(self):
        with self.assertRaises(RosterError):
            load_roster(PROJECT_ROOT / "data" / "does-not-exist.xml")


class StudentMatchingTests(unittest.TestCase):
    """``python infovis.py 001`` must resolve against eight-digit indices."""

    def setUp(self):
        self.roster = RosterParser().parse_string(
            """<r>
                 <student><index>10000409</index><name>A</name></student>
                 <student><index>10009301</index><name>B</name></student>
                 <student><index>10009302</index><name>C</name></student>
               </r>"""
        )

    def test_exact_index(self):
        self.assertEqual(self.roster.find("10009301").name, "B")

    def test_suffix_match(self):
        self.assertEqual(self.roster.find("9301").name, "B")

    def test_numeric_equality_ignores_leading_zeros(self):
        self.assertTrue(Student("001", "John").matches("1"))

    def test_short_queries_do_not_match_by_suffix(self):
        self.assertIsNone(self.roster.find("1"))

    def test_ambiguous_query_is_an_error_not_a_guess(self):
        # Two batches can share the trailing digits of an index.
        roster = RosterParser().parse_string(
            """<r>
                 <student><index>10009301</index><name>B</name></student>
                 <student><index>20009301</index><name>D</name></student>
               </r>"""
        )
        with self.assertRaises(AmbiguousStudentError):
            roster.find("9301")

    def test_an_exact_index_wins_over_an_ambiguous_suffix(self):
        roster = RosterParser().parse_string(
            """<r>
                 <student><index>9301</index><name>B</name></student>
                 <student><index>20009301</index><name>D</name></student>
               </r>"""
        )
        self.assertEqual(roster.find("9301").name, "B")

    def test_unknown_query_returns_none(self):
        self.assertIsNone(self.roster.find("55555"))


class ProjectRosterTests(unittest.TestCase):
    """The roster shipped with the prototype must match the printed sheets."""

    def test_project_info_xml_lists_the_six_students_in_sheet_order(self):
        roster = load_roster(PROJECT_ROOT / "data" / "info.xml")
        self.assertEqual(
            roster.indices(),
            ["10000409", "10009301", "10009302", "10009303", "10009304", "10009306"],
        )
        self.assertEqual(roster.subject.code, "CS402.3")


if __name__ == "__main__":
    unittest.main()
