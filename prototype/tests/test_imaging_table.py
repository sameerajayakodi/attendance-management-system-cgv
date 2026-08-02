"""Tests for the image primitives and the table detector.

These run against the synthetic signing sheet from ``support.py``, whose geometry
is known exactly, so every assertion has a ground truth that does not depend on
any photograph.
"""

from __future__ import annotations

import unittest

import cv2
import numpy as np

from support import synthetic_sheet  # noqa: F401

from attendance import imaging
from attendance.config import DEFAULT_SETTINGS
from attendance.stages import photometric_chain
from attendance.table import Cell, TableDetectionError, TableDetector, TableGrid


class ImagingTests(unittest.TestCase):
    def test_resize_to_width_reports_the_scale_it_used(self):
        image = np.zeros((400, 800, 3), np.uint8)
        resized, scale = imaging.resize_to_width(image, 400)
        self.assertEqual(resized.shape[1], 400)
        self.assertAlmostEqual(scale, 0.5)
        self.assertEqual(resized.shape[0], 200)

    def test_resize_to_width_is_a_no_op_at_the_same_width(self):
        image = np.zeros((10, 20, 3), np.uint8)
        resized, scale = imaging.resize_to_width(image, 20)
        self.assertEqual(scale, 1.0)
        self.assertEqual(resized.shape, image.shape)

    def test_rotate_bound_grows_the_canvas_so_nothing_is_clipped(self):
        image = np.full((100, 200, 3), 255, np.uint8)
        rotated = imaging.rotate_bound(image, 30.0)
        self.assertGreater(rotated.shape[0], 100)
        self.assertGreater(rotated.shape[1], 200)

    def test_grayscale_is_idempotent_on_a_single_channel_image(self):
        gray = np.zeros((5, 5), np.uint8)
        self.assertEqual(imaging.to_grayscale(gray).shape, (5, 5))

    def test_illumination_correction_flattens_a_shading_gradient(self):
        ramp = np.tile(np.linspace(120, 255, 400, dtype=np.uint8), (300, 1))
        flattened = imaging.flatten_illumination(ramp, DEFAULT_SETTINGS)
        self.assertLess(float(np.std(flattened)), float(np.std(ramp)) / 4.0)

    def test_binarisation_marks_ink_white_and_paper_black(self):
        page = np.full((200, 200), 245, np.uint8)
        cv2.line(page, (20, 100), (180, 100), 20, 3)
        binary = imaging.binarize_adaptive(page, DEFAULT_SETTINGS)
        self.assertGreater(binary[100, 100], 128)   # on the stroke
        self.assertLess(binary[20, 20], 128)        # on blank paper

    def test_otsu_separates_a_two_tone_page_exactly(self):
        page = np.full((100, 100), 240, np.uint8)
        page[40:60, 40:60] = 30
        binary, threshold = imaging.binarize_otsu(page)
        # On a strictly two-valued image Otsu settles on the darker mode itself,
        # so the assertion is about the segmentation, not about a magic number.
        self.assertTrue(30 <= threshold < 240)
        self.assertEqual(cv2.countNonZero(binary), 20 * 20)

    def test_skew_estimation_recovers_a_known_rotation(self):
        image, _ = synthetic_sheet(skew_degrees=3.0)
        _, _, _, binary = photometric_chain(image, DEFAULT_SETTINGS)
        angle = imaging.estimate_skew(binary, DEFAULT_SETTINGS)
        # A page rotated by +3 degrees must be corrected by about -3.
        self.assertAlmostEqual(angle, -3.0, delta=0.6)

    def test_skew_estimation_returns_zero_on_a_blank_page(self):
        blank = np.zeros((300, 300), np.uint8)
        self.assertEqual(imaging.estimate_skew(blank, DEFAULT_SETTINGS), 0.0)

    def test_pen_colour_naming(self):
        self.assertEqual(imaging.describe_pen_colour((200, 90, 70)), "blue")
        self.assertEqual(imaging.describe_pen_colour((60, 70, 200)), "red")
        self.assertEqual(imaging.describe_pen_colour((30, 30, 30)), "black")


class TableGridTests(unittest.TestCase):
    def setUp(self):
        self.grid = TableGrid(row_edges=[0, 50, 100, 150, 200], column_edges=[0, 100, 200])

    def test_row_and_column_counts_are_the_gaps_not_the_rules(self):
        self.assertEqual(self.grid.row_count, 4)
        self.assertEqual(self.grid.column_count, 2)

    def test_the_first_band_is_the_header(self):
        self.assertEqual(self.grid.data_rows, [1, 2, 3])

    def test_cell_geometry(self):
        cell = self.grid.cell(1, 1)
        self.assertEqual(cell.box, (100, 50, 200, 100))
        self.assertEqual(cell.width, 100)
        self.assertEqual(cell.height, 50)
        self.assertEqual(cell.area, 5000)

    def test_inset_shrinks_symmetrically(self):
        self.assertEqual(Cell(0, 0, 0, 0, 100, 100).inset(0.1), (10, 10, 90, 90))

    def test_uniformity_is_zero_for_even_rows(self):
        self.assertAlmostEqual(self.grid.uniformity(), 0.0)

    def test_uniformity_rises_when_a_row_is_the_wrong_height(self):
        uneven = TableGrid(row_edges=[0, 50, 100, 200, 250], column_edges=[0, 100])
        self.assertGreater(uneven.uniformity(), 0.2)

    def test_bbox_spans_the_outer_rules(self):
        self.assertEqual(self.grid.bbox, (0, 0, 200, 200))


class GridRepairTests(unittest.TestCase):
    """A missed rule is interpolated back from the form's uniform row pitch."""

    def test_a_single_missing_rule_is_reinstated(self):
        grid = TableGrid(row_edges=[0, 50, 100, 150, 250], column_edges=[0, 100])
        self.assertEqual(grid.repair(expected_data_rows=4), 1)
        self.assertEqual(grid.row_edges, [0, 50, 100, 150, 200, 250])
        self.assertEqual(len(grid.data_rows), 4)

    def test_two_consecutive_missing_rules_are_reinstated(self):
        grid = TableGrid(row_edges=[0, 50, 100, 250], column_edges=[0, 100])
        self.assertEqual(grid.repair(expected_data_rows=4), 2)
        self.assertEqual(grid.row_edges, [0, 50, 100, 150, 200, 250])

    def test_nothing_is_invented_when_the_grid_is_already_complete(self):
        grid = TableGrid(row_edges=[0, 50, 100, 150], column_edges=[0, 100])
        self.assertEqual(grid.repair(expected_data_rows=2), 0)

    def test_a_band_that_is_not_a_whole_multiple_is_left_alone(self):
        grid = TableGrid(row_edges=[0, 50, 100, 175], column_edges=[0, 100])
        self.assertEqual(grid.repair(expected_data_rows=4), 0)
        self.assertEqual(grid.row_edges, [0, 50, 100, 175])


class TableDetectorTests(unittest.TestCase):
    def setUp(self):
        self.detector = TableDetector(DEFAULT_SETTINGS)
        self.image, self.expected = synthetic_sheet(signed_rows=(0, 2, 4))
        _, _, _, self.binary = photometric_chain(self.image, DEFAULT_SETTINGS)

    def test_line_extraction_separates_the_two_orientations(self):
        masks = self.detector.extract_lines(self.binary)
        self.assertGreater(cv2.countNonZero(masks.horizontal), 0)
        self.assertGreater(cv2.countNonZero(masks.vertical), 0)
        self.assertGreater(cv2.countNonZero(masks.intersections), 0)

    def test_the_roster_is_selected_over_the_session_table(self):
        result = self.detector.detect(self.binary)
        self.assertIsNotNone(result.roster)
        self.assertIsNotNone(result.session)
        self.assertGreater(result.roster.row_count, result.session.row_count)

    def test_all_six_data_rows_are_recovered(self):
        result = self.detector.detect(self.binary)
        self.assertEqual(len(result.roster.data_rows), self.expected["rows"])

    def test_recovered_rows_are_uniform(self):
        result = self.detector.detect(self.binary)
        self.assertLess(result.roster.uniformity(), 0.05)

    def test_row_edges_land_on_the_drawn_rules(self):
        result = self.detector.detect(self.binary)
        drawn = self.expected["row_edges"]
        for edge in result.roster.row_edges:
            self.assertTrue(
                any(abs(edge - target) <= 4 for target in drawn),
                msg=f"detected rule at y={edge} matches no drawn rule",
            )

    def test_detection_survives_a_rotated_page(self):
        image, expected = synthetic_sheet(signed_rows=(1, 3), skew_degrees=-2.5)
        _, _, _, binary = photometric_chain(image, DEFAULT_SETTINGS)
        angle = imaging.estimate_skew(binary, DEFAULT_SETTINGS)
        rectified = imaging.rotate_bound(image, angle)
        _, _, _, binary = photometric_chain(rectified, DEFAULT_SETTINGS)
        result = self.detector.detect(binary)
        self.assertEqual(len(result.roster.data_rows), expected["rows"])

    def test_a_blank_page_raises_a_helpful_error(self):
        blank = np.zeros((800, 800), np.uint8)
        with self.assertRaises(TableDetectionError):
            self.detector.detect(blank)


if __name__ == "__main__":
    unittest.main()
