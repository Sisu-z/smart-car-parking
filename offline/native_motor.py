"""通过管道调用 MCU 同源 C 代码；所有电机参数都是模拟参数。"""
from pathlib import Path
import math
import subprocess
import select

ROOT = Path(__file__).resolve().parents[1]

class NativeMotor:
    def __init__(self):
        self.process = subprocess.Popen([str(ROOT / "build/host/bench_host")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1)
        self.now_ms = 0
        self.counts = self.rpm = self.duty = 0.0
        self.direction = 0
        self.enabled = False
        self.fault = 0
        self.frame = []
        try:
            for _ in range(10):
                self.step(0.0, .02)
        except Exception:
            self.close()
            raise

    def exchange(self, line):
        self.process.stdin.write(line + "\n")
        self.process.stdin.flush()
        if not select.select([self.process.stdout],[],[],3)[0]:
            raise TimeoutError("C 虚拟台架 3 秒无响应，停止本案例，不无限重试")
        reply = self.process.stdout.readline().strip()
        if not reply:
            raise RuntimeError("C 虚拟台架进程退出：" + self.process.stderr.read()[-2000:])
        return reply.split(",")

    def command(self, command):
        row = self.exchange(f"C,{self.now_ms},{command}")
        self.fault = int(row[3])
        return row[2] == "1"

    def step(self, speed_mps, dt, disconnect=False):
        self.now_ms += round(dt * 1000)
        self.counts += self.rpm / 60 * 1000 * dt
        row = self.exchange(f"T,{self.now_ms},{round(self.counts) % 65536}")
        self.frame = row
        self.enabled = bool(int(row[2])); self.fault = int(row[9])
        self.duty = float(row[7])
        direction = (speed_mps > 0) - (speed_mps < 0)
        if not disconnect and not self.fault:
            if direction and self.direction and direction != self.direction:
                self.command("MOTOR:DISABLE")
                self.enabled = False
            if direction:
                self.direction = direction
            if not self.enabled:
                self.enabled = self.command("MOTOR:ENABLE")
            if self.enabled:
                self.command(f"SPEED_RPM:{speed_mps / (2 * math.pi * .03) * 60:.6f}")
        # 一阶模拟电机；绝非 XP28 的已辨识模型。
        self.rpm += (self.duty * 220 - self.rpm) * (1 - math.exp(-dt / .18))
        return self.rpm / 60 * (2 * math.pi * .03)

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                self.process.wait(timeout=3)
        self.process.stdout.close(); self.process.stderr.close()
