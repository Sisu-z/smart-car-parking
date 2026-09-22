import unittest
from tools.analyze_log import analyze
class LogTests(unittest.TestCase):
    def test_invalid_speed_is_not_zero(self):
        r=analyze("T,0,0,0,nan,nan,0,0,0,0\nT,50,1,10,0,10,.1,.1,0,0\nT,500,0,0,0,0,0,0,0,1\nT,bad")
        self.assertEqual(r["samples"],3);self.assertEqual(r["invalid_rpm_samples"],1)
        self.assertEqual(r["fault_masks"],[1]);self.assertEqual(r["malformed_lines"],1)
        self.assertEqual(r["max_telemetry_gap_ms"],450)
    def test_wrap(self):
        r=analyze("T,4294967290,0,0,0,0,0,0,0,0\nT,4,0,0,0,0,0,0,0,0")
        self.assertEqual(r["max_telemetry_gap_ms"],10)
