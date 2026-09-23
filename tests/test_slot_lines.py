import json
from pathlib import Path
import tempfile
import unittest

import cv2
import numpy as np

from offline.slot_lines import analyze, detect_lines, ground_view, LineConfig
from offline.slot_cli import run
from offline.dataset_audit import audit


def fixture(angle=0, close=False, cap=True):
    image = np.full((480, 640, 3), 30, np.uint8)
    cv2.line(image, (240, 120), (240, 360), (230, 230, 230), 4)
    cv2.line(image, (400, 120), (400, 360), (230, 230, 230), 4)
    if cap:
        cv2.line(image, (240, 120), (400, 120), (230, 230, 230), 4)
    if close:
        cv2.line(image, (240, 360), (400, 360), (230, 230, 230), 4)
    return cv2.warpAffine(image, cv2.getRotationMatrix2D((320, 240), angle, 1), (640, 480), borderValue=(30, 30, 30))


def profile():
    return dict(schema="ground-profile-v1", camera_model="pinhole", image_size=[640, 480],
                calibration_id="SYNTHETIC_ONLY", camera_id="synthetic", mount_id="fixed",
                camera_matrix=[[500, 0, 320], [0, 500, 240], [0, 0, 1]], dist_coeffs=[0] * 5,
                image_points_px=[[20, 20], [620, 20], [620, 460], [20, 460]],
                ground_points_m=[[2.2, 1.5], [2.2, -1.5], [0, -1.5], [0, 1.5]], meters_per_px=.005)


class SlotTests(unittest.TestCase):
    def test_u_and_rotated_u(self):
        for angle in (0, 18, -30, 90):
            with self.subTest(angle=angle):
                result = detect_lines(fixture(angle))
                self.assertGreaterEqual(len(result["candidates"]), 1)
                self.assertFalse(result["valid_for_control"])
                self.assertEqual(result["occupancy"], "UNKNOWN")

    def test_blank_parallel_and_closed(self):
        for image in (np.zeros((480, 640), np.uint8), fixture(cap=False), fixture(close=True)):
            self.assertEqual(detect_lines(image)["candidates"], [])

    def test_invalid_inputs(self):
        for image in (None, np.zeros((20, 20), float), np.zeros((20, 20, 4), np.uint8)):
            with self.assertRaises(ValueError):
                detect_lines(image)
        with self.assertRaises(ValueError):
            LineConfig(max_lines=1000)

    def test_ground_geometry(self):
        result, _ = analyze(fixture(), profile())
        self.assertTrue(result["candidates"])
        c = result["candidates"][0]
        self.assertAlmostEqual(c["width_m"], .8, delta=.05)
        self.assertAlmostEqual(c["depth_m"], 1.2, delta=.05)
        self.assertAlmostEqual(c["slot_inward_yaw_rad"], 0, delta=.05)
        self.assertFalse(result["valid_for_control"])

    def test_profile_failures(self):
        for key, value in [("image_size", [320, 240]), ("camera_model", "fisheye"),
                           ("ground_points_m", [[0, 0]] * 4), ("meters_per_px", float("nan")),
                           ("camera_id", ""), ("dist_coeffs", [float("nan")] * 5)]:
            p = profile()
            p[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                ground_view(fixture(), p)

    def test_perspective_rectification(self):
        original = np.array([[20, 20], [620, 20], [620, 460], [20, 460]], np.float32)
        projected = np.array([[180, 40], [460, 50], [600, 450], [40, 440]], np.float32)
        transform = cv2.getPerspectiveTransform(original, projected)
        image = cv2.warpPerspective(fixture(), transform, (640, 480))
        p = profile()
        p["image_points_px"] = projected.tolist()
        result, _ = analyze(image, p)
        self.assertTrue(result["candidates"])
        self.assertAlmostEqual(result["candidates"][0]["width_m"], .8, delta=.05)
        self.assertAlmostEqual(result["candidates"][0]["depth_m"], 1.2, delta=.05)

    def test_crossed_correspondences_rejected(self):
        p = profile()
        p["ground_points_m"][1], p["ground_points_m"][2] = p["ground_points_m"][2], p["ground_points_m"][1]
        with self.assertRaises(ValueError):
            ground_view(fixture(), p)

    def test_border_and_oversize_rejected(self):
        image = np.full((480, 640, 3), 30, np.uint8)
        for a, b in (((240, 22), (240, 260)), ((400, 22), (400, 260)), ((240, 22), (400, 22))):
            cv2.line(image, a, b, (230, 230, 230), 4)
        self.assertEqual(analyze(image, profile())[0]["candidates"], [])
        p = profile()
        p["image_size"] = [20, 5000]
        with self.assertRaises(ValueError):
            ground_view(np.zeros((5000, 20, 3), np.uint8), p)

    def test_video_bounded_sampling(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "input.avi"
            writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 10, (640, 480))
            self.assertTrue(writer.isOpened(), "测试环境需支持 MJPG，不能静默跳过")
            try:
                for _ in range(8):
                    writer.write(fixture())
            finally:
                writer.release()
            result = run(video, root / "out", "video-session-a", "dev", limit=3, stride=2)
            self.assertEqual([r["frame_index"] for r in result["records"]], [0, 2, 4])

    def test_cli_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "input.png"
            cv2.imwrite(str(image), fixture())
            result = run(image, root / "out", "room-session-a", "dev", profile())
            self.assertEqual(len(result["records"]), 1)
            self.assertTrue((root / "out/frame_0000.png").exists())
            self.assertEqual(json.loads((root / "out/manifest.json").read_text())["status"], "COMPLETED_CANDIDATES_ONLY")
            with self.assertRaises(FileExistsError):
                run(image, root / "out", "room-session-a", "dev")
            with self.assertRaises(ValueError):
                run(root, root / "nested", "room-session-a", "dev")
            with self.assertRaises(ValueError):
                run(image, root / "bad-profile", "room-session-a", "dev", {"value": float("nan")})
            self.assertFalse((root / "bad-profile").exists())

    def test_dataset_leak(self):
        def data(scene, split, digest):
            return dict(schema="slot-dataset-v1", status="COMPLETED_CANDIDATES_ONLY", scene_id=scene,
                        split=split, records=[dict(image_sha256=digest)])
        a = data("a", "dev", "a" * 64)
        self.assertTrue(audit([a, data("b", "validation", "b" * 64)])["passed"])
        self.assertFalse(audit([a, data("a", "validation", "b" * 64)])["passed"])
        self.assertFalse(audit([a, data("b", "validation", "a" * 64)])["passed"])
        self.assertFalse(audit([a])["passed"])


if __name__ == "__main__":
    unittest.main()
