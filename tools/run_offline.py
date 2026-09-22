"""统一复跑入口。编译/测试失败会记录并继续独立步骤，单步最长 120 秒。
生成的结果位于 results；不扫描设备，不烧录，不连接串口。
"""
import json
import argparse
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description="电脑端复跑；显式启用才构建 STM32，绝不烧录")
    parser.add_argument("--with-stm32",action="store_true",help="增加 STM32 编译，需外部 HAL 基线和 ARM 工具链")
    parser.add_argument("--baseline",type=Path,help="仓库外只读 test01 基线；也可设置 STM32_BASELINE_DIR")
    args=parser.parse_args()
    baseline=args.baseline or os.environ.get("STM32_BASELINE_DIR")
    if args.with_stm32 and not baseline:
        parser.error("--with-stm32 必须提供 --baseline 或 STM32_BASELINE_DIR；电脑端默认不需要它")
    if baseline:
        baseline=str(Path(baseline).expanduser().resolve())
    os.chdir(ROOT)
    out=ROOT/"results";out.mkdir(exist_ok=True)
    env=dict(os.environ,MPLBACKEND="Agg",PYTHONUNBUFFERED="1")
    steps=[
        ("C配置",["cmake","-S","tests","-B","build/host","-DENABLE_SANITIZERS=ON","-DCMAKE_BUILD_TYPE=Debug"]),
        ("C构建",["cmake","--build","build/host","-j","4"]),
        ("C安全与数值测试",["ctest","--test-dir","build/host","--output-on-failure"]),
        ("Python视觉与集成测试",[sys.executable,"-m","unittest","discover","-s","tests","-p","test_*.py","-v"]),
        ("泊车与故障场景",[sys.executable,"-m","offline.run"]),
    ]
    if args.with_stm32:
        steps.extend([
            ("STM32配置",["cmake","-S","firmware/platform/stm32f103_hal","-B","build/stm32","-DCMAKE_TOOLCHAIN_FILE=arm-toolchain.cmake",f"-DBASELINE={baseline}"]),
            ("STM32链接",["cmake","--build","build/stm32","-j","4"]),
        ])
    results=[]; failed=set()
    for index,(name,command) in enumerate(steps):
        dependency={1:{0},2:{0,1},3:{0,1},4:{0,1},6:{5}}.get(index,set())
        if dependency & failed:
            results.append(dict(step=name,passed=False,status="SKIPPED_DEPENDENCY"));failed.add(index);continue
        print("执行："+name,flush=True)
        try:
            p=subprocess.run(command,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
            record=dict(step=name,passed=p.returncode==0,exit_code=p.returncode,output=p.stdout)
        except (subprocess.TimeoutExpired,OSError) as e:
            record=dict(step=name,passed=False,error=str(e))
        if not record["passed"]: failed.add(index)
        (out/f"step_{index+1:02}.log").write_text(record.get("output",record.get("error","")))
        results.append(record)
        print("通过" if record["passed"] else "未通过，记录后继续",flush=True)
    report=dict(timestamp_utc=datetime.now(timezone.utc).isoformat(),hardware_tested=False,
                stm32_requested=args.with_stm32,stm32_status="REQUESTED" if args.with_stm32 else "NOT_REQUESTED",steps=results)
    (out/"verification.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print("结果：results/离线验证结果.html；完整日志：results/verification.json")
    return bool(failed)

if __name__=="__main__":raise SystemExit(main())
