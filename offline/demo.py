"""生成可查看的合成图像与模拟倒库/出库证据，不读取相机或控制设备。"""
import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import tempfile

import cv2
import numpy as np

from .parking import run_scenario, run_exit_scenario, plan, Config
from .report import write_report
from .slot_lines import analyze, overlay

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    root = args.output_root
    root.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix="phase1-demo-", dir=root))
    image_cases = []
    for index, (name, angle, cap) in enumerate((("正向 U 形线框", 0, True),
                                               ("旋转线框", 25, True),
                                               ("仅平行线：无法确定入口", 0, False))):
        image = np.full((480, 640, 3), 30, np.uint8)
        for a, b in (((240, 120), (240, 360)), ((400, 120), (400, 360))):
            cv2.line(image, a, b, (230, 230, 230), 4)
        if cap:
            cv2.line(image, (240, 120), (400, 120), (230, 230, 230), 4)
        image = cv2.warpAffine(image, cv2.getRotationMatrix2D((320, 240), angle, 1), (640, 480),
                               borderValue=(30, 30, 30))
        result, view = analyze(image)
        result.update(name=name, synthetic=True, expected_has_candidate=cap,
                      passed=bool(result["candidates"]) == cap)
        filename = f"vision_{index:02}.png"
        if not cv2.imwrite(str(out / filename), overlay(view, result)):
            raise OSError("演示图片写入失败")
        result["image"] = filename
        image_cases.append(result)
    parked = run_scenario("末段倒车停车实验", (0, 0, 0), (-1, 0, 0), terminal_direction=-1)
    parked["passed"] = parked["status"] == "PARKED" and parked["path_directions"][-1] == -1
    results = [parked]
    if parked["status"] == "PARKED":
        p = parked["trace"][-1]
        start = (p["x"], p["y"], p["yaw"])
        exited = run_exit_scenario("从模拟停稳点重新规划出库", start, (0, 0, 0))
        exited["passed"] = exited["status"] == "EXITED" and exited["path_directions"][-1] == 1
        blocked = run_exit_scenario("出库目标占用：拒绝", start, (0, 0, 0), ((0, 0, .2),))
        blocked["passed"] = blocked["status"] == "NO_PATH"
        results += [exited, blocked]
    rng = np.random.default_rng(20260923)
    geometry = []
    for i in range(24):
        start = (float(rng.uniform(-.3, .5)), float(rng.uniform(-.6, .6)), float(rng.uniform(-np.pi, np.pi)))
        sections = plan(start, (-1.2, 0, 0), (), Config(), terminal_direction=-1)
        geometry.append(dict(index=i, start=start, planned=bool(sections),
                             reverse_terminal=bool(sections) and sections[-1][1] == -1))
    summary = dict(timestamp_utc=datetime.now(timezone.utc).isoformat(), hardware_tested=False,
                   real_images_tested=False, random_search_implemented=False,
                   images=image_cases, tasks=results, random_geometry=geometry,
                   scope="合成 U 形候选 + 真值位姿控制；随机项只测规划，不是自主找位成功率")
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(results, out / "轨迹回放.html")
    cards = "".join(f'<section><h2>{html.escape(r["name"])}</h2><img width="640" src="{out.name}/{r["image"]}"><p>候选数：{len(r["candidates"])}；不可用于控制；占用未知。</p></section>' for r in image_cases)
    document = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>第一阶段软件实验</title>
<style>body{{font:16px system-ui;max-width:900px;margin:30px auto;padding:0 16px;background:#f6f8fa;color:#18212b}}section{{background:white;padding:16px;margin:16px 0;border-radius:8px}}img{{max-width:100%}}</style>
<h1>第一阶段软件实验：非实车结果</h1><p>复用 OpenCV 与 PythonRobotics；图像为合成，控制位姿为模拟真值。未实现自主找位、语义车位判断、占用判断或真实视觉闭环。</p>
<p><a href="{out.name}/轨迹回放.html">查看倒库、重新规划出库与阻挡拒绝轨迹</a> · <a href="{out.name}/summary.json">完整证据 JSON</a></p>
<p>固定种子 24 个随机位置/朝向：{sum(g['planned'] for g in geometry)} 个得到几何路径；这不是随机起点停车成功率。</p>{cards}</html>'''
    (root / "阶段一软件实验.html").write_text(document, encoding="utf-8")
    passed = len(results) == 3 and all(r["passed"] for r in results + image_cases)
    passed = passed and all(not g["planned"] or g["reverse_terminal"] for g in geometry)
    print(json.dumps(dict(passed=passed, report=str(root / "阶段一软件实验.html"),
                          random_planned=sum(g["planned"] for g in geometry), random_total=24), ensure_ascii=False))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
