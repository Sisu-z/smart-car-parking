#include "bench.h"
#include <math.h>
#include <stddef.h>
#include <string.h>

void Bench_Fault(Bench *b, uint32_t flags)
{
    if (!b) return;
    b->enabled = 0U;
    b->requested_duty = b->target_rpm = 0.0f;
    b->frame.enabled = 0U;
    b->frame.target_rpm = b->frame.controller_output = b->frame.pwm_duty = 0.0f;
    b->frame.fault_flags |= flags;
    Motor_Stop(&b->motor, MOTOR_STOP_COAST);
    PID_Reset(&b->pid);
}

int Bench_Init(Bench *b, const BenchConfig *c, uint32_t now, uint16_t count)
{
    if (!b) return 0;
    memset(b, 0, sizeof(*b));
    if (!c || !isfinite(c->duty_limit) || c->duty_limit <= 0 || c->duty_limit > 1 ||
        !isfinite(c->counts_per_rev) || c->counts_per_rev < 0 ||
        !isfinite(c->max_rpm) || c->max_rpm < 0 ||
        !c->timeout_ms || c->timeout_ms > 60000U ||
        !c->max_step_ms || c->max_step_ms > c->timeout_ms ||
        !c->quiet_ms || c->quiet_ms > 60000U) return 0;
    b->config = *c;
    PidConfig pc = c->pid;
    pc.output_min = fmaxf(pc.output_min, -c->duty_limit);
    pc.output_max = fminf(pc.output_max, c->duty_limit);
    if (Motor_Init(&b->motor, &c->motor) != MOTOR_OK ||
        PID_Init(&b->pid, &pc) != PID_OK) return 0;
    Encoder_Init(&b->encoder, count, 1);
    b->last_tick_ms = b->last_command_ms = b->quiet_since_ms = now;
    b->initialized = 1U;
    Bench_Fault(b, 0U);
    return 1;
}

int Bench_Command(Bench *b, const char *line, uint32_t now)
{
    if (!b || !b->initialized) return 0;
    RobotCommand cmd;
    if (Command_ParseLine(line, &cmd) != COMMAND_OK) {
        Bench_Fault(b, BENCH_INPUT); return 0;
    }
    if (cmd.type == COMMAND_GET_STATUS) return 1;
    if (cmd.type == COMMAND_MOTOR_STOP || cmd.type == COMMAND_MOTOR_DISABLE) {
        Bench_Fault(b, 0U);
        if (cmd.type == COMMAND_MOTOR_DISABLE) b->frame.fault_flags = 0U;
        b->quiet_since_ms = now;
        b->last_direction = 0;
        return 1;
    }
    if (cmd.type == COMMAND_MOTOR_ENABLE) {
        if (b->enabled) return 1; /* 重复 ENABLE 不能续租。 */
        if (!b->config.hardware_approved) { Bench_Fault(b, BENCH_PLATFORM); return 0; }
        if (b->frame.fault_flags || now - b->quiet_since_ms < b->config.quiet_ms ||
            now - b->last_tick_ms > b->config.max_step_ms) return 0;
        b->enabled = 1U;
        b->last_command_ms = now;
        return 1;
    }
    if (cmd.type == COMMAND_SET_KP || cmd.type == COMMAND_SET_KI || cmd.type == COMMAND_SET_KD) {
        if (b->enabled) { Bench_Fault(b, BENCH_INPUT); return 0; }
        PidConfig pc = b->pid.config;
        if (cmd.type == COMMAND_SET_KP) pc.kp = cmd.value;
        if (cmd.type == COMMAND_SET_KI) pc.ki = cmd.value;
        if (cmd.type == COMMAND_SET_KD) pc.kd = cmd.value;
        return PID_Init(&b->pid, &pc) == PID_OK;
    }
    if (cmd.type != COMMAND_SET_DUTY && cmd.type != COMMAND_SET_SPEED_RPM) {
        Bench_Fault(b, BENCH_INPUT); return 0; /* 此工程无舵机。 */
    }
    if (!b->enabled) return 0; /* 禁用期间不缓存运动命令。 */
    if (now - b->last_command_ms >= b->config.timeout_ms) {
        Bench_Fault(b, BENCH_TIMEOUT); return 0;
    }
    if (cmd.type == COMMAND_SET_SPEED_RPM &&
        (b->config.counts_per_rev <= 0 || b->config.max_rpm <= 0)) {
        Bench_Fault(b, BENCH_CALIBRATION); return 0;
    }
    float limit = cmd.type == COMMAND_SET_DUTY ? b->config.duty_limit : b->config.max_rpm;
    if (fabsf(cmd.value) > limit) { Bench_Fault(b, BENCH_INPUT); return 0; }
    int8_t dir = (cmd.value > 0) - (cmd.value < 0);
    if (dir && b->last_direction && dir != b->last_direction) {
        Bench_Fault(b, BENCH_REVERSAL); return 0;
    }
    if (dir) b->last_direction = dir;
    uint8_t speed = cmd.type == COMMAND_SET_SPEED_RPM;
    if (speed != b->speed_mode || cmd.value == 0) PID_Reset(&b->pid);
    b->speed_mode = speed;
    b->requested_duty = speed ? 0 : cmd.value;
    b->target_rpm = speed ? cmd.value : 0;
    b->last_command_ms = now;
    return 1;
}

MotorOutput Bench_Tick(Bench *b, uint32_t now, uint16_t count)
{
    MotorOutput zero = {0, 0U, 0, MOTOR_STOP_COAST};
    if (!b || !b->initialized) return zero;
    uint32_t elapsed = now - b->last_tick_ms;
    int32_t delta = Encoder_UpdateCounter(&b->encoder, count);
    b->last_tick_ms = now;
    if (delta || !elapsed || elapsed > b->config.max_step_ms) b->quiet_since_ms = now;
    if (!elapsed || elapsed > b->config.max_step_ms) Bench_Fault(b, BENCH_TIMING);
    if (b->enabled && now - b->last_command_ms >= b->config.timeout_ms) Bench_Fault(b, BENCH_TIMEOUT);
    float rpm = 0;
    EncoderSpeedResult sr = Encoder_DeltaToRpm(delta, elapsed * 0.001f, b->config.counts_per_rev, &rpm);
    if (b->enabled && b->speed_mode && sr != ENCODER_SPEED_OK) Bench_Fault(b, BENCH_CALIBRATION);
    float duty = b->requested_duty;
    if (b->enabled && b->speed_mode && b->target_rpm != 0) {
        if (PID_Update(&b->pid, b->target_rpm, rpm, elapsed * 0.001f, &duty) != PID_OK)
            Bench_Fault(b, BENCH_INPUT);
        /* 台架阶段不主动反接制动；过快时滑行。反向运行同理。 */
        if (duty * b->target_rpm < 0) duty = 0;
    }
    duty = fmaxf(-b->config.duty_limit, fminf(b->config.duty_limit, duty));
    if (b->enabled) {
        if (Motor_SetTargetDuty(&b->motor, duty) != MOTOR_OK) Bench_Fault(b, BENCH_INPUT);
    } else Motor_Stop(&b->motor, MOTOR_STOP_COAST);
    MotorOutput out = Motor_Update(&b->motor);
    b->frame.timestamp_ms = now;
    b->frame.enabled = b->enabled;
    b->frame.target_rpm = b->target_rpm;
    b->frame.actual_rpm = sr == ENCODER_SPEED_OK ? rpm : NAN;
    b->frame.error_rpm = sr == ENCODER_SPEED_OK ? b->target_rpm - rpm : NAN;
    b->frame.controller_output = b->enabled ? duty : 0;
    b->frame.pwm_duty = out.applied_duty;
    b->frame.encoder_delta = delta;
    return out;
}
