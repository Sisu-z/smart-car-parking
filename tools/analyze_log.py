"""分析本项目 V0 T,... 遥测日志；只给候选原因，不自动宣称堵转/故障根因。"""
import argparse
import csv
import json
import math
from pathlib import Path

FIELDS=["timestamp_ms","enabled","target_rpm","actual_rpm","error_rpm","controller_output","pwm_duty","encoder_delta","fault_flags"]

def analyze(text):
    rows=[];bad=0
    for line in text.splitlines():
        if not line.startswith("T,"):continue
        try:
            parts=next(csv.reader([line]))
            if len(parts)!=10:raise ValueError("字段数")
            r=dict(zip(FIELDS,map(float,parts[1:])))
            if any(not math.isfinite(r[k]) for k in ("timestamp_ms","enabled","pwm_duty","encoder_delta","fault_flags")):raise ValueError("非法数值")
            rows.append(r)
        except ValueError:bad+=1
    intervals=[(int(b["timestamp_ms"])-int(a["timestamp_ms"]))%(2**32) for a,b in zip(rows,rows[1:])]
    unknown=sum(not math.isfinite(r["actual_rpm"]) for r in rows)
    flags=sorted(set(int(r["fault_flags"]) for r in rows if r["fault_flags"]))
    driven_no_delta=sum(abs(r["pwm_duty"])>.05 and r["encoder_delta"]==0 for r in rows)
    notes=[]
    if unknown:notes.append("RPM 含无效值：检查计数标定与测速状态，不按 0 RPM 处理。")
    if driven_no_delta:notes.append("存在有输出但计数为零的采样：需区分低速量化、接线、供电、机械负载；不能仅凭此认定堵转。")
    if flags:notes.append("存在故障位：1超时/2输入/4调度/8标定/16换向/32硬件审核门控。")
    if intervals and max(intervals)>100:notes.append("遥测间隔超过 100 ms；检查丢行/传输，不能单凭遥测周期断言控制周期异常。")
    return dict(samples=len(rows),malformed_lines=bad,invalid_rpm_samples=unknown,fault_masks=flags,
        max_telemetry_gap_ms=max(intervals,default=None),driven_zero_delta_samples=driven_no_delta,
        notes=notes or ["此日志未命中已有规则；不代表全部硬件正常。"])

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("log");a=p.parse_args()
    print(json.dumps(analyze(Path(a.log).read_text()),ensure_ascii=False,indent=2))
