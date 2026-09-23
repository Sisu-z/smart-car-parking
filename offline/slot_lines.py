"""普通 U 形线框候选实验；复用 OpenCV，不连接设备，不输出可执行目标。

像素线不是语义车位；占用永远 UNKNOWN，valid_for_control 永远 False。
仅支持三边可见、近似矩形的线框；标定投影后可处理平面透视图像。
来源/限制见 offline/README.md；不复制 OpenCV 算法实现。
"""
from dataclasses import dataclass
from itertools import combinations
import math

import cv2
import numpy as np


@dataclass(frozen=True)
class LineConfig:
    min_length_px: int = 40
    min_width_px: int = 24
    min_depth_px: int = 60
    merge_distance_px: float = 6.0
    endpoint_tolerance_px: float = 12.0
    max_raw_lines: int = 160
    max_lines: int = 80

    def __post_init__(self):
        values = list(vars(self).values())
        if not all(np.isfinite(v) and v > 0 for v in values):
            raise ValueError("线框参数必须为有限正数")
        if self.max_raw_lines > 500 or self.max_lines > 100:
            raise ValueError("线段上限过大；禁止无界组合搜索")


def _segment(points):
    p = np.asarray(points, dtype=float).reshape(2, 2)
    d = p[1] - p[0]
    length = np.linalg.norm(d)
    if length < 1:
        return None
    d /= length
    if d[0] < -1e-9 or (abs(d[0]) < 1e-9 and d[1] < 0):
        d = -d
    n = np.array([-d[1], d[0]])
    return p, d, n


def _merge(raw, cfg):
    """只合并近共线的条纹边缘，防止一根粗线产生多个假车位。"""
    lines = []
    for item in raw:
        s = _segment(item)
        if s is None:
            continue
        p, d, n = s
        for i, (q, e, _) in enumerate(lines):
            if abs(d @ e) < math.cos(math.radians(5)):
                continue
            if max(abs((q - p.mean(axis=0)) @ n)) > cfg.merge_distance_px:
                continue
            a, b = sorted(p @ d), sorted(q @ d)
            if max(a[0], b[0]) - min(a[1], b[1]) > 20:
                continue
            center = (p.mean(axis=0) + q.mean(axis=0)) / 2
            merged = np.array([d * min(a[0], b[0]) + n * (center @ n),
                               d * max(a[1], b[1]) + n * (center @ n)])
            lines[i] = _segment(merged)
            break
        else:
            lines.append(s)
    return lines


def _cap_at(lines, d, n, end, low, high, tol):
    for p, e, _ in lines:
        if abs(e @ d) > math.sin(math.radians(8)):
            continue
        if max(abs(p @ d - end)) > tol:
            continue
        limits = sorted(p @ n)
        if limits[0] <= low + tol and limits[1] >= high - tol:
            return True
    return False


def _validate_image(image):
    if not isinstance(image, np.ndarray) or image.dtype != np.uint8 or image.ndim not in (2, 3):
        raise ValueError("输入必须是 uint8 灰度或 BGR 图像")
    if image.ndim == 3 and image.shape[2] != 3:
        raise ValueError("只支持 BGR 三通道")
    if min(image.shape[:2]) < 16 or max(image.shape[:2]) > 4096:
        raise ValueError("图像边长须在 16～4096 内")


def detect_lines(image, cfg=LineConfig()):
    """返回候选和诊断；没有语义/入口通路/占用有效性保证。"""
    _validate_image(image)
    gray = image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # 直接复用 OpenCV LSD，避免 Hough 对透视重采样后像素量化的碎线敏感。
    raw = cv2.createLineSegmentDetector(cv2.LSD_REFINE_STD).detect(gray)[0]
    raw = [] if raw is None else raw.reshape(-1, 2, 2)
    result = dict(schema="slot-lines-experiment-v1", status="NO_CANDIDATE",
                  valid_for_control=False, occupancy="UNKNOWN", coordinate_space="image_px",
                  raw_line_count=len(raw), candidates=[])
    if len(raw) > cfg.max_raw_lines:
        result["status"] = "TOO_MANY_LINES"
        return result
    lines = _merge([p for p in raw if np.linalg.norm(p[1] - p[0]) >= cfg.min_length_px], cfg)
    result["merged_line_count"] = len(lines)
    if len(lines) > cfg.max_lines:
        result["status"] = "TOO_MANY_LINES"
        return result
    candidates = []
    for (p, d, n), (q, e, _) in combinations(lines, 2):
        if abs(d @ e) < math.cos(math.radians(5)):
            continue
        low, high = sorted([float(p.mean(axis=0) @ n), float(q.mean(axis=0) @ n)])
        width = high - low
        a, b = sorted(p @ d), sorted(q @ d)
        start, end = max(a[0], b[0]), min(a[1], b[1])
        depth = end - start
        tol = cfg.endpoint_tolerance_px
        if width < cfg.min_width_px or depth < cfg.min_depth_px or not .8 <= depth / width <= 4.5:
            continue
        if max(abs(a[0] - b[0]), abs(a[1] - b[1])) > tol:
            continue
        caps = [_cap_at(lines, d, n, t, low, high, tol) for t in (start, end)]
        if caps[0] == caps[1]:
            continue  # 两条平行线无法确定入口；封闭矩形也不能直接判成车位。
        back, entrance = (start, end) if caps[0] else (end, start)
        corners = np.array([d * entrance + n * low, d * entrance + n * high,
                            d * back + n * high, d * back + n * low])
        center = corners.mean(axis=0)
        if any(np.linalg.norm(center - np.array(c["corners_px"]).mean(axis=0)) < tol
               for c in candidates):
            continue
        inward = d * np.sign(back - entrance)
        candidates.append(dict(corners_px=corners.tolist(), entrance_px=corners[:2].tolist(),
                               inward_image_angle_rad=float(math.atan2(inward[1], inward[0])),
                               width_px=width, depth_px=float(depth),
                               geometry="U_SHAPE_HYPOTHESIS", occupancy="UNKNOWN"))
    result["candidates"] = candidates
    if candidates:
        result["status"] = "CANDIDATES_ONLY"
    return result


def ground_view(image, profile):
    """固定相机：去畸变后映射至标定地面。仅在标定凸包内分析，禁止外推。

    标定点只能来自离线测量；不是运行时输入车位坐标。
    x 对应前，y 对应左。鸟瞰画布 u=-y，v=-x。
    """
    _validate_image(image)
    if not isinstance(profile, dict) or profile.get("schema") != "ground-profile-v1":
        raise ValueError("未知标定 schema")
    if profile.get("camera_model") != "pinhole":
        raise ValueError("仅支持 pinhole；鱼眼/镜面/运动相机不能套用")
    if list(profile["image_size"]) != [image.shape[1], image.shape[0]]:
        raise ValueError("图像与标定分辨率不同")
    for key in ("calibration_id", "camera_id", "mount_id"):
        if not isinstance(profile.get(key), str) or not profile[key].strip():
            raise ValueError(f"缺少 {key}")
    k = np.asarray(profile["camera_matrix"], dtype=float)
    dist = np.asarray(profile["dist_coeffs"], dtype=float).reshape(-1)
    src = np.asarray(profile["image_points_px"], dtype=float)
    dst = np.asarray(profile["ground_points_m"], dtype=float)
    if (k.shape != (3, 3) or not np.isfinite(k).all() or min(k[0, 0], k[1, 1]) <= 0
            or not np.allclose(k[2], [0, 0, 1]) or np.linalg.det(k) <= 0):
        raise ValueError("相机内参无效")
    if dist.size not in (4, 5, 8, 12, 14) or not np.isfinite(dist).all():
        raise ValueError("畸变参数无效")
    if src.ndim != 2 or src.shape[1] != 2 or src.shape != dst.shape or not 4 <= len(src) <= 100:
        raise ValueError("至少 4 对、最多 100 对像素/地面标定点")
    if not np.isfinite(src).all() or not np.isfinite(dst).all():
        raise ValueError("标定点非有限")
    if (src < 0).any() or (src >= np.array(profile["image_size"])).any():
        raise ValueError("标定点超出图像")
    meters_per_px = float(profile["meters_per_px"])
    if not np.isfinite(meters_per_px) or not .001 <= meters_per_px <= .1:
        raise ValueError("鸟瞰分辨率须为 0.001～0.1 m/px")
    undistorted_points = cv2.undistortPoints(src.reshape(-1, 1, 2), k, dist, P=k).reshape(-1, 2)
    for points in (undistorted_points, dst):
        if np.linalg.matrix_rank(points - points.mean(axis=0)) < 2:
            raise ValueError("标定点共线")
    h, mask = cv2.findHomography(undistorted_points, dst, cv2.RANSAC, .015)
    if h is None or not np.isfinite(h).all() or mask is None or not mask.all():
        raise ValueError("地面拟合失败或存在异常标定点，需重测")
    if np.linalg.matrix_rank(h) < 3 or np.linalg.cond(h) > 1e12:
        raise ValueError("地面变换退化")
    # 错配的四点仍能零误差拟合；必须拒绝覆盖内分母过零/无穷远的变换。
    for matrix, points in ((h, undistorted_points), (np.linalg.inv(h), dst)):
        homogeneous = np.column_stack([points, np.ones(len(points))])
        denominator = homogeneous @ matrix[2]
        tolerance = 1e-8 * np.maximum(1, np.abs(homogeneous) @ np.abs(matrix[2]))
        if not (np.all(denominator > tolerance) or np.all(denominator < -tolerance)):
            raise ValueError("标定覆盖穿越投影地平线，点配对/相机姿态无效")
    fit = cv2.perspectiveTransform(undistorted_points.reshape(-1, 1, 2), h).reshape(-1, 2)
    if max(np.linalg.norm(fit - dst, axis=1)) > .015:
        raise ValueError("标定点重投影误差超出实验上限；低误差仍非独立验证")
    xmin, ymin = dst.min(axis=0)
    xmax, ymax = dst.max(axis=0)
    size = (int(math.ceil((ymax - ymin) / meters_per_px)) + 1,
            int(math.ceil((xmax - xmin) / meters_per_px)) + 1)
    if min(size) < 16 or max(size) > 2048:
        raise ValueError("标定地面范围过小或鸟瞰图过大")
    canvas = np.array([[0, -1 / meters_per_px, ymax / meters_per_px],
                       [-1 / meters_per_px, 0, xmax / meters_per_px], [0, 0, 1]])
    clean = cv2.undistort(image, k, dist)
    bird = cv2.warpPerspective(clean, canvas @ h, size)
    hull = cv2.convexHull(cv2.perspectiveTransform(dst.reshape(-1, 1, 2), canvas).astype(np.float32))
    coverage = np.zeros(bird.shape[:2], np.uint8)
    cv2.fillConvexPoly(coverage, np.rint(hull).astype(np.int32), 255)
    # 避免把标定覆盖边界产生的人造线当车位边框，检测后再排除边缘候选。
    bird[coverage == 0] = 0
    return bird, np.linalg.inv(canvas), coverage


def analyze(image, profile=None, cfg=LineConfig()):
    _validate_image(image)
    if profile is None:
        result = detect_lines(image, cfg)
        result["metric_status"] = "UNCALIBRATED"
        return result, image.copy()
    bird, to_ground, coverage = ground_view(image, profile)
    result = detect_lines(bird, cfg)
    accepted = []
    distance = cv2.distanceTransform(np.pad(coverage, 1), cv2.DIST_L2, 3)[1:-1, 1:-1]
    for candidate in result["candidates"]:
        pts = np.asarray(candidate["corners_px"], dtype=float)
        # 四角及四边中点都必须位于覆盖内，远离裁切伪边缘。
        samples = np.vstack([pts, (pts + np.roll(pts, -1, axis=0)) / 2])
        if any(not (0 <= x < coverage.shape[1] and 0 <= y < coverage.shape[0]) or
               distance[int(y), int(x)] < 10 for x, y in samples):
            continue
        ground = cv2.perspectiveTransform(pts.reshape(-1, 1, 2), to_ground).reshape(-1, 2)
        inward = (ground[2] + ground[3] - ground[0] - ground[1]) / 2
        candidate.update(corners_ground_m=ground.tolist(), entrance_ground_m=ground[:2].tolist(),
                         width_m=float(np.linalg.norm(ground[1] - ground[0])),
                         depth_m=float(np.linalg.norm(inward)),
                         slot_inward_yaw_rad=float(math.atan2(inward[1], inward[0])))
        accepted.append(candidate)
    result.update(candidates=accepted, coordinate_space="birdseye_px_and_ground_m",
                  metric_status="CALIBRATION_SUPPLIED_UNVERIFIED",
                  calibration_id=profile["calibration_id"], camera_id=profile["camera_id"],
                  mount_id=profile["mount_id"])
    if result["status"] != "TOO_MANY_LINES":
        result["status"] = "CANDIDATES_ONLY" if accepted else "NO_CANDIDATE"
    return result, bird


def overlay(image, result):
    canvas = image.copy()
    if canvas.ndim == 2:
        canvas = cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)
    for c in result["candidates"]:
        pts = np.rint(c["corners_px"]).astype(np.int32)
        cv2.polylines(canvas, [pts], True, (0, 180, 255), 2)
        cv2.line(canvas, tuple(pts[0]), tuple(pts[1]), (255, 80, 20), 3)
    cv2.putText(canvas, "EXPERIMENT / OCCUPANCY UNKNOWN / NO CONTROL", (8, 20),
                cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 0, 255), 1)
    return canvas
