import contextlib
import copy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import main


class SimulatorTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(Path(__file__).with_name("data.json").read_text(encoding="utf-8"))

    def analyze(self, data):
        with contextlib.redirect_stdout(io.StringIO()):
            return main.analyze(data)

    def test_mac_and_verdict(self):
        cross, diagonal = main.generate_patterns(3)
        self.assertEqual(main.mac(cross, cross), 5.0)
        self.assertEqual(main.mac(cross, diagonal), 1.0)
        self.assertEqual(main.decide(1, 5, ("A", "B")), "B")
        self.assertEqual(main.decide(0.9, 0.8999999999999999), "UNDECIDED")
        self.assertEqual(main.decide(1e-9, 0), "Cross")

    def test_normalization(self):
        for label in ("+", "cross", "Cross", " CROSS "):
            self.assertEqual(main.normalize_label(label), "Cross")
        for label in ("x", "X"):
            self.assertEqual(main.normalize_label(label), "X")
        with self.assertRaises(ValueError):
            main.normalize_label("unknown")

    def test_sample(self):
        results = self.analyze(self.data)
        self.assertEqual(len(results), 9)
        self.assertEqual(sum(item["passed"] for item in results), 6)
        self.assertEqual(results[6]["verdict"], "UNDECIDED")
        self.assertIn("행 수", results[7]["reason"])
        self.assertIn("라벨", results[8]["reason"])

    def test_bad_case_continues(self):
        for invalid in (None, {}, {"input": [], "expected": "+"}):
            data = copy.deepcopy(self.data)
            data["patterns"]["size_5_1"] = invalid
            results = self.analyze(data)
            self.assertFalse(results[0]["passed"])
            self.assertTrue(results[1]["passed"])

    def test_bad_filter_continues(self):
        data = copy.deepcopy(self.data)
        data["filters"]["size_5"]["Cross"] = data["filters"]["size_5"]["cross"]
        results = self.analyze(data)
        self.assertFalse(results[0]["passed"])
        self.assertIn("중복", results[0]["reason"])
        self.assertTrue(results[2]["passed"])

    def test_invalid_matrices(self):
        for invalid in ([], [[0] * 2] * 3, [[True] * 3] * 3,
                        [[float("nan")] * 3] * 3, [[float("inf")] * 3] * 3,
                        [["1"] * 3] * 3, [[10 ** 400] * 3] * 3):
            with self.subTest(value=repr(invalid)[:40]):
                with self.assertRaises(ValueError):
                    main.validate_matrix(invalid, 3)

    def test_overflow(self):
        with self.assertRaises(ValueError):
            main.mac([[1e308]], [[1e308]])

    def test_reprompt(self):
        values = ["1 2", "a b c", "nan 0 0", "0 1 0", "1 1 1", "0 1 0"]
        output = io.StringIO()
        with patch("builtins.input", side_effect=values), contextlib.redirect_stdout(output):
            matrix = main.read_matrix("테스트")
        self.assertEqual(matrix, main.generate_patterns(3)[0])
        self.assertEqual(output.getvalue().count("입력 형식 오류"), 3)

    def test_schema_and_keys(self):
        for data in (None, {}, {"filters": [], "patterns": {}}):
            with self.assertRaises(ValueError):
                self.analyze(data)
        data = copy.deepcopy(self.data)
        data["patterns"]["bad_key"] = {}
        data["patterns"]["size_7_1"] = {}
        results = self.analyze(data)
        self.assertIn("키 형식", results[-2]["reason"])
        self.assertIn("필터가 없습니다", results[-1]["reason"])

    def test_benchmark(self):
        cross, diagonal = main.generate_patterns(3)
        self.assertGreater(main.benchmark(cross, diagonal, 10), 0)
        with self.assertRaises(ValueError):
            main.benchmark(cross, diagonal, 9)


if __name__ == "__main__":
    unittest.main()
