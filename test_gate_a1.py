"""Tests for the whitespace-tolerant comparison in gate_a1 (stdlib only). Apache-2.0, MV2, Munim, Inc."""
import unittest

import gate_a1


class TestSquash(unittest.TestCase):
    def test_wrapped_marker(self):
        text = "registered BEFORE any stage-1\nresult came back"
        self.assertIn(gate_a1.squash(gate_a1.A0[1]), gate_a1.squash(text))

    def test_line_endings_and_trailing_space(self):
        self.assertEqual(gate_a1.squash("a b\r\nc  \n"), gate_a1.squash("a b\nc"))

    def test_real_difference_kept(self):
        self.assertNotEqual(gate_a1.squash("prior 0.75"), gate_a1.squash("prior 0.70"))


if __name__ == "__main__":
    unittest.main()
