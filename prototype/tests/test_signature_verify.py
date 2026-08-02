"""Tests for the ink classifier and the signature verifier."""

from __future__ import annotations

import unittest

import cv2
import numpy as np

from support import synthetic_sheet  # noqa: F401

from attendance.config import DEFAULT_SETTINGS
from attendance.signature import ABSENT, PRESENT, SignatureAnalyzer, SignatureFeatures
from attendance.stages import photometric_chain
from attendance.table import TableDetector
from attendance.verify import HistogramOfOrientedGradients, SignatureVerifier


def analyse(signed_rows, **kwargs):
    image, expected = synthetic_sheet(signed_rows=signed_rows, **kwargs)
    _, _, _, binary = photometric_chain(image, DEFAULT_SETTINGS)
    detection = TableDetector(DEFAULT_SETTINGS).detect(binary)
    verdicts = SignatureAnalyzer(DEFAULT_SETTINGS).analyse(image, binary, detection.masks, detection.roster)
    return verdicts, expected


class InkClassificationTests(unittest.TestCase):
    def test_only_the_signed_rows_are_marked_present(self):
        verdicts, expected = analyse((0, 2, 4))
        statuses = [verdict.status for verdict in verdicts]
        self.assertEqual(
            statuses,
            [PRESENT if index in expected["signed_rows"] else ABSENT for index in range(len(verdicts))],
        )

    def test_a_fully_signed_sheet_has_no_absences(self):
        verdicts, _ = analyse(tuple(range(6)))
        self.assertTrue(all(verdict.present for verdict in verdicts))

    def test_an_unsigned_sheet_has_no_attendances(self):
        verdicts, _ = analyse(())
        self.assertTrue(all(not verdict.present for verdict in verdicts))

    def test_signed_cells_hold_far_more_ink_than_unsigned_ones(self):
        verdicts, expected = analyse((1, 3))
        signed = [v.features.ink_ratio for i, v in enumerate(verdicts) if i in expected["signed_rows"]]
        unsigned = [v.features.ink_ratio for i, v in enumerate(verdicts) if i not in expected["signed_rows"]]
        self.assertGreater(min(signed), max(unsigned) * 5)

    def test_a_present_verdict_carries_a_tight_specimen_box(self):
        verdicts, expected = analyse((0, 2, 4))
        for index, verdict in enumerate(verdicts):
            if index in expected["signed_rows"]:
                self.assertIsNotNone(verdict.ink_box)
                self.assertIsNotNone(verdict.crop)
                self.assertEqual(verdict.crop.shape[:2], verdict.mask.shape[:2])

    def test_the_specimen_mask_holds_only_this_rows_ink(self):
        verdicts, expected = analyse((0, 1, 2, 3, 4, 5))
        for verdict in verdicts:
            self.assertGreater(cv2.countNonZero(verdict.mask), 0)

    def test_detection_survives_a_rotated_sheet(self):
        image, expected = synthetic_sheet(signed_rows=(0, 3), skew_degrees=2.0)
        from attendance import imaging

        _, _, _, binary = photometric_chain(image, DEFAULT_SETTINGS)
        rectified = imaging.rotate_bound(image, imaging.estimate_skew(binary, DEFAULT_SETTINGS))
        _, _, _, binary = photometric_chain(rectified, DEFAULT_SETTINGS)
        detection = TableDetector(DEFAULT_SETTINGS).detect(binary)
        verdicts = SignatureAnalyzer(DEFAULT_SETTINGS).analyse(rectified, binary, detection.masks, detection.roster)
        present = [index for index, verdict in enumerate(verdicts) if verdict.present]
        self.assertEqual(present, list(expected["signed_rows"]))


class DecisionRuleTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = SignatureAnalyzer(DEFAULT_SETTINGS)

    def _features(self, ink_pixels: int, cell_area: int = 100_000) -> SignatureFeatures:
        return SignatureFeatures(
            ink_pixels=ink_pixels, cell_area=cell_area, components=1,
            largest_component=ink_pixels, fill_ratio=0.2, pen_colour="blue",
        )

    def test_ink_above_the_threshold_is_present(self):
        status, confidence = self.analyzer._decide(self._features(2000))
        self.assertEqual(status, PRESENT)
        self.assertGreater(confidence, 0.3)

    def test_an_empty_cell_is_absent_with_full_confidence(self):
        status, confidence = self.analyzer._decide(self._features(0))
        self.assertEqual(status, ABSENT)
        self.assertEqual(confidence, 1.0)

    def test_a_speck_of_ink_is_still_absent(self):
        self.assertEqual(self.analyzer._decide(self._features(60))[0], ABSENT)

    def test_the_absolute_pixel_floor_overrides_a_high_ratio_in_a_tiny_cell(self):
        # 3 per cent of a very small cell is still only a handful of pixels.
        status, _ = self.analyzer._decide(self._features(ink_pixels=60, cell_area=2000))
        self.assertEqual(status, ABSENT)

    def test_residual_rules_are_rejected_as_ink(self):
        self.assertTrue(self.analyzer._is_residual_rule(width=400, height=2, area=800))
        self.assertTrue(self.analyzer._is_residual_rule(width=1, height=200, area=200))
        self.assertFalse(self.analyzer._is_residual_rule(width=80, height=40, area=900))

    def test_ink_ratio_is_the_ratio_of_pixels_to_cell_area(self):
        self.assertAlmostEqual(self._features(1000, 50_000).ink_ratio, 0.02)

    def test_features_serialise_for_the_database(self):
        payload = self._features(1000).as_dict()
        self.assertEqual(payload["ink_pixels"], 1000)
        self.assertIn("pen_colour", payload)


class HogTests(unittest.TestCase):
    def setUp(self):
        self.hog = HistogramOfOrientedGradients(cell=8, bins=9, block=2)

    def test_descriptor_length_matches_the_dalal_triggs_formula(self):
        # (rows-1) x (cols-1) blocks, each block = block^2 cells x bins
        image = np.zeros((64, 128), np.uint8)
        expected = (64 // 8 - 1) * (128 // 8 - 1) * 2 * 2 * 9
        self.assertEqual(self.hog.compute(image).size, expected)

    def test_blocks_are_l2_normalised(self):
        image = np.zeros((64, 128), np.uint8)
        cv2.line(image, (10, 10), (110, 50), 255, 3)
        vector = self.hog.compute(image)
        block = vector[:36]
        self.assertAlmostEqual(float(np.linalg.norm(block)), 1.0, places=3)

    def test_a_rotated_edge_moves_the_dominant_orientation(self):
        horizontal = np.zeros((64, 128), np.uint8)
        cv2.line(horizontal, (5, 32), (120, 32), 255, 4)
        vertical = np.zeros((64, 128), np.uint8)
        cv2.line(vertical, (64, 5), (64, 58), 255, 4)
        self.assertLess(SignatureVerifier.cosine(self.hog.compute(horizontal), self.hog.compute(vertical)), 0.75)

    def test_an_image_too_small_for_one_block_returns_a_stub(self):
        self.assertEqual(self.hog.compute(np.zeros((8, 8), np.uint8)).size, 1)


class VerifierTests(unittest.TestCase):
    def setUp(self):
        self.verifier = SignatureVerifier(DEFAULT_SETTINGS)

    def _scribble(self, seed: int, size=(80, 220)) -> tuple[np.ndarray, np.ndarray]:
        generator = np.random.default_rng(seed)
        mask = np.zeros(size, np.uint8)
        points = [(20, size[0] // 2)]
        for step in range(1, 8):
            points.append((20 + step * 25, size[0] // 2 + int(generator.integers(-25, 25))))
        cv2.polylines(mask, [np.array(points, np.int32)], False, 255, 4)
        colour = cv2.cvtColor(cv2.bitwise_not(mask), cv2.COLOR_GRAY2BGR)
        return colour, mask

    def test_a_specimen_is_identical_to_itself(self):
        colour, mask = self._scribble(1)
        specimen = self.verifier.describe("a", colour, mask)
        self.assertAlmostEqual(self.verifier.similarity(specimen, specimen), 1.0, places=6)

    def test_similarity_is_symmetric(self):
        left = self.verifier.describe("a", *self._scribble(1))
        right = self.verifier.describe("b", *self._scribble(2))
        self.assertAlmostEqual(self.verifier.similarity(left, right), self.verifier.similarity(right, left), places=9)

    def test_similarity_stays_within_zero_and_one(self):
        left = self.verifier.describe("a", *self._scribble(3))
        right = self.verifier.describe("b", *self._scribble(9))
        self.assertGreaterEqual(self.verifier.similarity(left, right), 0.0)
        self.assertLessEqual(self.verifier.similarity(left, right), 1.0)

    def test_an_empty_specimen_is_invalid_and_never_matches(self):
        blank = np.zeros((60, 160), np.uint8)
        specimen = self.verifier.describe("blank", cv2.cvtColor(blank, cv2.COLOR_GRAY2BGR), blank)
        self.assertFalse(specimen.valid)
        self.assertEqual(self.verifier.similarity(specimen, specimen), 0.0)

    def test_scale_does_not_change_the_specimen(self):
        colour, mask = self._scribble(5)
        big_colour = cv2.resize(colour, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_NEAREST)
        big_mask = cv2.resize(mask, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_NEAREST)
        small = self.verifier.describe("small", colour, mask)
        large = self.verifier.describe("large", big_colour, big_mask)
        self.assertGreater(self.verifier.similarity(small, large), 0.85)

    def test_neighbouring_specks_are_dropped_before_description(self):
        colour, mask = self._scribble(7)
        cv2.circle(mask, (mask.shape[1] - 6, 6), 2, 255, -1)  # a speck in the corner
        kept = self.verifier.keep_dominant_components(mask)
        self.assertEqual(kept[6, mask.shape[1] - 6], 0)

    def test_aspect_agreement_is_one_for_equal_ratios_and_symmetric(self):
        from attendance.verify import Specimen

        wide = Specimen("w", np.zeros((1, 1, 3), np.uint8), aspect=4.0)
        also_wide = Specimen("w2", np.zeros((1, 1, 3), np.uint8), aspect=4.0)
        narrow = Specimen("n", np.zeros((1, 1, 3), np.uint8), aspect=2.0)
        self.assertAlmostEqual(SignatureVerifier.aspect_agreement(wide, also_wide), 1.0)
        self.assertAlmostEqual(
            SignatureVerifier.aspect_agreement(wide, narrow),
            SignatureVerifier.aspect_agreement(narrow, wide),
        )
        self.assertLess(SignatureVerifier.aspect_agreement(wide, narrow), 1.0)

    def test_cosine_of_orthogonal_vectors_is_zero(self):
        self.assertAlmostEqual(SignatureVerifier.cosine(np.array([1.0, 0.0]), np.array([0.0, 1.0])), 0.0)

    def test_cosine_handles_a_zero_vector(self):
        self.assertEqual(SignatureVerifier.cosine(np.zeros(3), np.ones(3)), 0.0)


class RobustOutlierTests(unittest.TestCase):
    """The mismatch rule must not flag one specimen per student by construction."""

    def test_an_even_spread_produces_no_large_scores(self):
        scores = SignatureVerifier.modified_z_scores([0.50, 0.51, 0.49, 0.52, 0.48])
        self.assertTrue(all(abs(score) < 3.5 for score in scores))

    def test_a_true_outlier_is_isolated(self):
        scores = SignatureVerifier.modified_z_scores([0.50, 0.51, 0.49, 0.52, 0.10])
        self.assertLess(scores[-1], -3.5)
        self.assertTrue(all(abs(score) < 3.5 for score in scores[:-1]))

    def test_identical_values_give_zero_scores_not_a_division_by_zero(self):
        self.assertEqual(SignatureVerifier.modified_z_scores([0.4] * 5), [0.0] * 5)

    def test_empty_input(self):
        self.assertEqual(SignatureVerifier.modified_z_scores([]), [])

    def test_a_consistent_set_is_reported_as_consistent(self):
        verifier = SignatureVerifier(DEFAULT_SETTINGS)
        generator = np.random.default_rng(11)
        samples = []
        for index in range(5):
            mask = np.zeros((80, 220), np.uint8)
            points = [(20, 40)]
            for step in range(1, 8):
                points.append((20 + step * 25, 40 + int(generator.integers(-4, 4)) + (step % 3) * 9))
            cv2.polylines(mask, [np.array(points, np.int32)], False, 255, 4)
            samples.append((f"s{index}", cv2.cvtColor(cv2.bitwise_not(mask), cv2.COLOR_GRAY2BGR), mask))
        report = verifier.verify("10000001", samples)
        self.assertTrue(report.consistent, msg=report.summary())


if __name__ == "__main__":
    unittest.main()
