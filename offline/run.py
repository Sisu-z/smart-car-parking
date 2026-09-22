"""python -m offline.run：运行实际 C 核心参与的离线场景并保存证据。"""
import csv
import json
import math
from pathlib import Path
from .parking import run_scenario

ROOT=Path(__file__).resolve().parents[1]

def run_all():
    cases=[
        ("直线倒车",(0,0,0),(-1.0,0,0),(),None,"PARKED"),
        ("侧移泊车",(0,0,0),(-1.4,.45,0),(),None,"PARKED"),
        ("垂直泊车",(0,0,0),(-.8,.8,math.pi/2),(),None,"PARKED"),
        ("目标被占用",(0,0,0),(-1,0,0),((-1,0,.2),),None,"NO_PATH"),
        ("定位丢失",(0,0,0),(-1,0,0),(),"pose_loss","FAULT"),
        ("定位跳变",(0,0,0),(-1,0,0),(),"pose_jump","FAULT"),
        ("上位机断连",(0,0,0),(-1,0,0),(),"link_loss","FAULT"),
    ]
    results=[]; output=ROOT/"results"; output.mkdir(exist_ok=True)
    for i,(name,start,goal,obstacles,fault,expected) in enumerate(cases):
        r=run_scenario(name,start,goal,obstacles,fault)
        expected_reason={"pose_loss":"POSE_TIMEOUT","pose_jump":"TRACKING_ERROR","link_loss":"MCU_FAULT_1"}.get(fault,"")
        r["expected_status"]=expected; r["expected_reason"]=expected_reason
        checks={"terminal_status":r["status"]==expected,
                "fault_reason":r.get("reason","")==expected_reason,
                "output_limits":all(abs(p["duty"])<=.30001 and abs(p["steer_rad"])<=r["config"]["max_steer_rad"]+.00001 for p in r["trace"])}
        if fault:
            failure=next((p for p in r["trace"] if p["state"]=="FAULT"),None)
            r["fault_detected_s"]=failure["t_s"] if failure else None
            deadline={"pose_loss":2.28,"pose_jump":2.02,"link_loss":2.32}[fault]
            checks["bounded_fault_response"]=failure is not None and failure["t_s"]<=deadline
            checks["zero_command_and_stopped"]=abs(r["trace"][-1]["duty"])<1e-8 and abs(r["trace"][-1]["speed_mps"])<.003
        r["checks"]=checks; r["passed"]=all(checks.values())
        results.append(r)
        if r["trace"]:
            with (output/f"scenario_{i+1:02}.csv").open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=r["trace"][0].keys()); w.writeheader(); w.writerows(r["trace"])
        print(name,r["status"],r.get("reason"),r["position_error_m"],r["yaw_error_rad"],flush=True)
    (output/"parking_results.json").write_text(json.dumps(results,ensure_ascii=False,indent=2))
    from .report import write_report
    write_report(results,output/"离线验证结果.html")
    return results

if __name__=="__main__":
    results=run_all()
    raise SystemExit(0 if all(r["passed"] for r in results) else 1)
