"""受控场景实验：原版 Reeds–Shepp + 轻量 Pure Pursuit 适配 + 同源 C 速度环。
不是已验证实车算法；不连接任何串口。坐标参考点为后轴中心。
Pure Pursuit 公式参考 PythonRobotics，MIT 许可见 third_party/PythonRobotics/LICENSE。
上游示例的车辆尺寸、中心点/倒车符号和无界索引搜索不适合此接口，因此不原样调用。
"""
from dataclasses import dataclass, asdict
import math
from pathlib import Path
import sys
import numpy as np
from .native_motor import NativeMotor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "third_party/PythonRobotics"))
from PathPlanning.ReedsSheppPath import reeds_shepp_path_planning as rs
rs.show_animation = False

def wrap(a): return (a + math.pi) % (2 * math.pi) - math.pi

@dataclass(frozen=True)
class Config:
    wheelbase_m: float = .26
    length_m: float = .42
    width_m: float = .24
    rear_overhang_m: float = .08
    max_steer_rad: float = .52
    max_steer_rate_radps: float = 1.4
    speed_mps: float = .12
    lookahead_m: float = .08
    dt_s: float = .02
    pose_timeout_s: float = .25
    position_tolerance_m: float = .045
    yaw_tolerance_rad: float = .12
    time_limit_s: float = 120

def collision(pose, obstacles, cfg, margin=.03):
    x, y, yaw = pose
    c, s = math.cos(yaw), math.sin(yaw)
    for ox, oy, radius in obstacles:
        dx, dy = ox-x, oy-y
        lx, ly = c*dx+s*dy, -s*dx+c*dy
        near_x = np.clip(lx, -cfg.rear_overhang_m, cfg.length_m-cfg.rear_overhang_m)
        near_y = np.clip(ly, -cfg.width_m/2, cfg.width_m/2)
        if math.hypot(lx-near_x, ly-near_y) <= radius+margin:
            return True
    return False

def _sections(path):
    sections = []
    first = 0
    for i in range(1, len(path.x)+1):
        if i == len(path.x) or path.directions[i] != path.directions[first]:
            pts = np.array(list(zip(path.x[first:i],path.y[first:i],path.yaw[first:i])))
            if len(pts)>1:
                sections.append((pts, path.directions[first]))
            first = i
    return sections


def plan(start, goal, obstacles, cfg, terminal_direction=None):
    """可选约束最后的实际路径段方向；不是车位入口跨越/整个任务保证。"""
    if terminal_direction not in (None, -1, 1):
        raise ValueError("末段方向只能为 -1（倒车）、+1（前进）或 None")
    if collision(start, obstacles, cfg, .055) or collision(goal, obstacles, cfg, .055):
        return []
    if np.linalg.norm(np.array(goal[:2])-start[:2]) < 1e-6 and abs(wrap(goal[2]-start[2])) < 1e-6:
        return [(np.array([start], dtype=float), 1)] if terminal_direction is None else []
    # 给跟踪纠偏留 15% 曲率余量，避免规划全程贴着执行器极限。
    candidates = rs.calc_paths(*start, *goal, .85*math.tan(cfg.max_steer_rad)/cfg.wheelbase_m, .015)
    valid = []
    for p in candidates:
        sections = _sections(p)
        if not sections or (terminal_direction is not None and sections[-1][1] != terminal_direction):
            continue
        if not any(collision(pose, obstacles, cfg, .055) for pose in zip(p.x,p.y,p.yaw)):
            valid.append((p, sections))
    if not valid:
        return []  # 只搜索 RS 候选，不声称完成任意障碍环境搜索。
    _, sections = min(valid, key=lambda item: item[0].L + .12 * sum(
        a*b<0 for a,b in zip(item[0].lengths,item[0].lengths[1:])))
    return sections

def run_scenario(name, start, goal, obstacles=(), fault=None, cfg=Config(), terminal_direction=None):
    sections = plan(start,goal,obstacles,cfg,terminal_direction)
    result = dict(name=name, start=start, goal=goal, obstacles=obstacles,
                  config=asdict(cfg), model_status="EXPERIMENTAL：全部尺寸与电机参数为仿真假设",
                  injected_fault=fault, terminal_direction=terminal_direction,
                  path_directions=[int(d) for _,d in sections],
                  path=[p.tolist() for p,_ in sections], trace=[])
    if not sections:
        result.update(status="NO_PATH", position_error_m=None, yaw_error_rad=None, stop_time_s=0)
        return result
    pose=np.array(start,dtype=float); velocity=steer=0.0
    segment=nearest=0; status="TRACKING"; last_pose_time=0.0
    observed=pose.copy(); reason=""; stationary=0
    motor=NativeMotor()
    try:
        for step in range(int(cfg.time_limit_s/cfg.dt_s)):
            t=step*cfg.dt_s
            if not (fault=="pose_loss" and t>=2):
                observed=pose.copy(); last_pose_time=t
                if fault=="pose_jump" and t>=2: observed[1]+=1
            if status=="TRACKING" and t-last_pose_time>cfg.pose_timeout_s:
                status="FAULT"; reason="POSE_TIMEOUT"
            if collision(pose,obstacles,cfg): status="FAULT"; reason="COLLISION"
            target_speed=0.0; target_steer=steer
            if status=="TRACKING":
                points,direction=sections[segment]
                distances=np.linalg.norm(points[:,:2]-observed[:2],axis=1)
                nearest=max(nearest,int(np.argmin(distances)))
                if distances[nearest]>.25:
                    status="FAULT"; reason="TRACKING_ERROR"
                else:
                    remaining=float(np.linalg.norm(points[-1,:2]-observed[:2]))
                    if remaining<.018 and nearest>=len(points)-3:
                        stationary = stationary+1 if abs(velocity)<.006 else 0
                        if stationary>=10:
                            if segment==len(sections)-1:
                                status="PARKED"
                            else:
                                segment+=1; nearest=0; stationary=0
                    else:
                        aim=nearest
                        while aim+1<len(points) and np.linalg.norm(points[aim,:2]-observed[:2])<cfg.lookahead_m:
                            aim+=1
                        dx,dy=points[aim,:2]-observed[:2]
                        distance=max(math.hypot(dx,dy),.005)
                        alpha=wrap(math.atan2(dy,dx)-observed[2])
                        # 有符号速度 + 后轴中心：曲率公式不额外翻转倒车符号。
                        target_steer=math.atan2(2*cfg.wheelbase_m*math.sin(alpha),distance)
                        target_steer=float(np.clip(target_steer,-cfg.max_steer_rad,cfg.max_steer_rad))
                        target_speed=direction*min(cfg.speed_mps,max(.025,remaining*.8))
            if status!="TRACKING": target_speed=0.0
            # 起步/换向先对齐转向，避免执行器仍在另一侧时直接加速。
            if abs(velocity)<.01 and abs(target_steer-steer)>.08:
                target_speed=0.0
            steer+=float(np.clip(target_steer-steer,-cfg.max_steer_rate_radps*cfg.dt_s,cfg.max_steer_rate_radps*cfg.dt_s))
            velocity=motor.step(target_speed,cfg.dt_s,disconnect=(fault=="link_loss" and t>=2))
            if motor.fault:
                status="FAULT"; reason=f"MCU_FAULT_{motor.fault}"
            pose[0]+=velocity*math.cos(pose[2])*cfg.dt_s
            pose[1]+=velocity*math.sin(pose[2])*cfg.dt_s
            pose[2]=wrap(pose[2]+velocity/cfg.wheelbase_m*math.tan(steer)*cfg.dt_s)
            result["trace"].append(dict(t_s=round(t,3),x=float(pose[0]),y=float(pose[1]),yaw=float(pose[2]),
                speed_mps=velocity,steer_rad=steer,target_speed_mps=target_speed,
                duty=motor.duty,encoder_delta=int(motor.frame[8]),fault_flags=motor.fault,
                state=status,segment=segment))
            if status!="TRACKING" and abs(velocity)<.003:
                break
        else:
            status="FAULT"; reason="TIME_LIMIT"
        error=float(np.linalg.norm(pose[:2]-goal[:2])); yaw_error=abs(wrap(float(pose[2]-goal[2])))
        if status=="PARKED" and (error>cfg.position_tolerance_m or yaw_error>cfg.yaw_tolerance_rad):
            status="FAULT"; reason="FINAL_POSE_ERROR"
        result.update(status=status,reason=reason,position_error_m=error,yaw_error_rad=yaw_error,
                      stop_time_s=result["trace"][-1]["t_s"])
    finally:
        motor.close()
    return result


def run_exit_scenario(name, start, exit_goal, obstacles=(), cfg=Config()):
    """从停稳位姿重新规划出库实验；不倒放入库路径，不感知真实通路。"""
    result = run_scenario(name, start, exit_goal, obstacles, cfg=cfg, terminal_direction=1)
    result["task"] = "EXIT_EXPERIMENT"
    if result["status"] == "PARKED":
        result["status"] = "EXITED"
        for point in result["trace"]:
            if point["state"] == "PARKED":
                point["state"] = "EXITED"
    return result
