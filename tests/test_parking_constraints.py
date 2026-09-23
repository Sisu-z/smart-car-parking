import math
import unittest

import numpy as np

from offline.parking import Config, collision, plan, run_scenario, run_exit_scenario


class ConstraintTests(unittest.TestCase):
    def test_reverse_terminal_and_random_geometry(self):
        rng = np.random.default_rng(20260923)
        accepted = 0
        for _ in range(24):
            start = (float(rng.uniform(-.3, .5)), float(rng.uniform(-.6, .6)), float(rng.uniform(-math.pi, math.pi)))
            sections = plan(start, (-1.2, 0, 0), (), Config(), terminal_direction=-1)
            if not sections:
                continue
            accepted += 1
            self.assertEqual(sections[-1][1], -1)
            self.assertGreater(len(sections[-1][0]), 1)
            np.testing.assert_allclose(sections[-1][0][-1], [-1.2, 0, 0], atol=1e-5)
            for points, _ in sections:
                self.assertTrue(np.isfinite(points).all())
        self.assertGreater(accepted, 0)  # 只是几何性质，不宣称随机起点完整跟踪成功率。

    def test_blocked_start_goal_and_zero_motion(self):
        cfg = Config()
        self.assertTrue(collision((0, 0, 0), [(0, 0, .2)], cfg))
        self.assertEqual(plan((0, 0, 0), (0, 0, 0), [(0, 0, .2)], cfg), [])
        self.assertEqual(plan((0, 0, 0), (0, 0, 0), (), cfg, -1), [])
        self.assertEqual(plan((0, 0, 0), (-1, 0, 0), [(-1, 0, .2)], cfg, -1), [])
        with self.assertRaises(ValueError):
            plan((0, 0, 0), (-1, 0, 0), (), cfg, 0)

    def test_closed_loop_park_then_replan_exit(self):
        parked = run_scenario("测试倒库", (0, 0, 0), (-1, 0, 0), terminal_direction=-1)
        self.assertEqual(parked["status"], "PARKED")
        self.assertEqual(parked["path_directions"][-1], -1)
        last = parked["trace"][-1]
        start = (last["x"], last["y"], last["yaw"])
        exited = run_exit_scenario("测试出库", start, (0, 0, 0))
        self.assertEqual(exited["status"], "EXITED")
        self.assertEqual(exited["path_directions"][-1], 1)
        self.assertLess(abs(exited["trace"][-1]["speed_mps"]), .003)
        blocked = run_exit_scenario("通路目标被占", start, (0, 0, 0), ((0, 0, .2),))
        self.assertEqual(blocked["status"], "NO_PATH")


if __name__ == "__main__":
    unittest.main()
