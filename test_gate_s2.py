"""Tests for the whitespace-tolerant amendment gate (stdlib only). Apache-2.0, MV2, Munim, Inc."""
import unittest

import gate_s2


class TestGate(unittest.TestCase):
    def test_wrapped_marker_found(self):
        text = "registered BEFORE any stage-1\nresult came back and before X"
        self.assertTrue(gate_s2.has_mark(text))

    def test_crlf_and_spaces(self):
        self.assertTrue(gate_s2.has_mark("BEFORE  any\r\nstage-1 result   came back"))

    def test_missing(self):
        self.assertFalse(gate_s2.has_mark("before any stage-1 result came back"))
        self.assertFalse(gate_s2.has_mark("BEFORE any stage-2 result came back"))


if __name__ == "__main__":
    unittest.main()
