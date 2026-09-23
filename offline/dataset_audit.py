"""检查开发/验证场景和重复图像泄漏；不是识别精度评估器。"""
import argparse
import json
from pathlib import Path


def audit(manifests):
    scenes, images, issues = {}, {}, []
    for data in manifests:
        if data.get("schema") != "slot-dataset-v1" or data.get("status") != "COMPLETED_CANDIDATES_ONLY":
            issues.append("无效或未完成的 manifest")
            continue
        split, scene = data.get("split"), data.get("scene_id")
        if split not in ("dev", "validation") or not isinstance(scene, str) or not scene.strip():
            issues.append("缺少有效场景或 split")
            continue
        scenes.setdefault(scene, set()).add(split)
        if not data.get("records"):
            issues.append(f"空数据集：{scene}")
        for record in data.get("records", []):
            digest = record.get("image_sha256", "")
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                issues.append(f"图像哈希无效：{scene}")
                continue
            images.setdefault(digest, set()).add(split)
    issues.extend(f"同一场景跨开发/验证集：{s}" for s, splits in scenes.items() if len(splits) > 1)
    issues.extend("相同图像跨开发/验证集：" + h[:12] for h, splits in images.items() if len(splits) > 1)
    if {s for splits in scenes.values() for s in splits} != {"dev", "validation"}:
        issues.append("必须同时提供开发集与独立验证集")
    return dict(passed=not issues, issues=issues, scene_count=len(scenes), image_count=len(images),
                limitation="仅检测同名场景/完全相同图像；不能识别改名场景、相邻帧或裁切图泄漏")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("manifests", nargs="+", type=Path)
    a = p.parse_args()
    result = audit([json.loads(f.read_text()) for f in a.manifests])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
