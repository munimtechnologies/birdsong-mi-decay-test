"""Tests for the stage-7 gate (stdlib only). Apache-2.0, MV2, Munim, Inc. Made with AI agents."""
import unittest

import gate_s7


class TestGate(unittest.TestCase):
    def test_wrapped_marker_found(self):
        text = "x registered BEFORE any starling\naudio was downloaded by this study (2026)"
        self.assertTrue(gate_s7.has_mark(text))

    def test_crlf_and_spaces(self):
        text = "registered  BEFORE any\r\nstarling audio   was downloaded by this study"
        self.assertTrue(gate_s7.has_mark(text))

    def test_missing(self):
        self.assertFalse(gate_s7.has_mark("registered before any starling audio was downloaded"))
        self.assertFalse(gate_s7.has_mark("registered BEFORE any finch audio was downloaded by "
                                          "this study"))

    def test_same_code_ignores_line_endings(self):
        a = "import os\r\nx = 1   \r\n\r\n"
        b = "import os\nx = 1\n"
        self.assertTrue(gate_s7.same_code(a, b))

    def test_same_code_detects_change(self):
        self.assertFalse(gate_s7.same_code("x = 1\n", "x = 2\n"))
        self.assertFalse(gate_s7.same_code("x = 1\n", "x  = 1\n"))


if __name__ == "__main__":
    unittest.main()
