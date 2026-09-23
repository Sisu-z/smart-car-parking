"""本地图片/录像分析：python -m offline.slot_cli --help。拒绝设备编号和网络流。"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2

from .slot_lines import analyze, overlay, LineConfig

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv"}


def frames(source, limit, stride):
    if source.is_dir():
        files = sorted(p for p in source.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
        if not files:
            raise ValueError("目录内没有支持的图片")
        for index, file in enumerate(files[:limit]):
            image = cv2.imread(str(file))
            if image is None:
                raise ValueError(f"无法读取图片：{file.name}")
            yield image, dict(source_name=file.name, frame_index=index, media_timestamp_ms=None)
    elif source.suffix.lower() in IMAGE_SUFFIXES:
        image = cv2.imread(str(source))
        if image is None:
            raise ValueError("无法读取图片")
        yield image, dict(source_name=source.name, frame_index=0, media_timestamp_ms=None)
    elif source.is_file() and source.suffix.lower() in VIDEO_SUFFIXES:
        capture = cv2.VideoCapture(str(source))
        try:
            if not capture.isOpened():
                raise ValueError("录像无法打开或编解码器不支持")
            emitted = 0
            for index in range(limit * stride):
                ok, image = capture.read()
                if not ok:
                    break
                if index % stride == 0:
                    emitted += 1
                    yield image, dict(source_name=source.name, frame_index=index,
                                      media_timestamp_ms=float(capture.get(cv2.CAP_PROP_POS_MSEC)))
            if not emitted:
                raise ValueError("录像没有可读取的帧")
        finally:
            capture.release()
    else:
        raise ValueError("只接受本地图片、图片目录或录像，不打开摄像头/网络流")


def run(source, output, scene_id, split, profile=None, limit=30, stride=15):
    source, output = Path(source), Path(output)
    if not source.exists() or not scene_id.strip() or split not in ("dev", "validation"):
        raise ValueError("输入不存在，或场景/数据集标识无效")
    if not 1 <= limit <= 200 or not 1 <= stride <= 300:
        raise ValueError("帧数 1～200、间隔 1～300，避免无界处理")
    if source.is_dir() and output.resolve().is_relative_to(source.resolve()):
        raise ValueError("输出不能位于输入目录内，避免再次检测自己的结果")
    profile_digest = (hashlib.sha256(json.dumps(profile, sort_keys=True, allow_nan=False).encode()).hexdigest()
                      if profile is not None else None)
    output.mkdir(parents=True, exist_ok=False)
    report = dict(schema="slot-dataset-v1", scene_id=scene_id, split=split, status="RUNNING",
                  detector="opencv-lsd-u-v1", opencv_version=cv2.__version__,
                  detector_config=vars(LineConfig()),
                  ground_profile_sha256=profile_digest, hardware_tested=False, records=[])
    try:
        for index, (frame, metadata) in enumerate(frames(source, limit, stride)):
            digest = hashlib.sha256(str(frame.shape).encode() + frame.tobytes()).hexdigest()
            result, view = analyze(frame, profile)
            metadata.update(image_sha256=digest, result=result, overlay=f"frame_{index:04}.png")
            if not cv2.imwrite(str(output / metadata["overlay"]), overlay(view, result)):
                raise OSError("诊断图片写入失败")
            report["records"].append(metadata)
        report["status"] = "COMPLETED_CANDIDATES_ONLY"
    except Exception as exc:
        report.update(status="FAILED", error=str(exc))
        raise
    finally:
        # 本地结果可能包含场景图像，必须保留在 gitignore 覆盖的 results/ 或 local/。
        (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    p.add_argument("--output", type=Path, required=True, help="新的输出目录，建议 results/ 下")
    p.add_argument("--scene-id", required=True, help="按房间/采集会话标识，不要按图片拆场景")
    p.add_argument("--split", choices=["dev", "validation"], required=True)
    p.add_argument("--ground-profile", type=Path)
    p.add_argument("--max-frames", type=int, default=30)
    p.add_argument("--stride", type=int, default=15)
    a = p.parse_args()
    try:
        profile = json.loads(a.ground_profile.read_text()) if a.ground_profile else None
        report = run(a.input, a.output, a.scene_id, a.split, profile, a.max_frames, a.stride)
    except (ValueError, OSError, KeyError, cv2.error) as exc:
        p.exit(2, f"处理失败：{exc}\n")
    print(f"处理 {len(report['records'])} 帧；只生成候选/诊断，不能驱动车辆：{a.output}")


if __name__ == "__main__":
    main()
