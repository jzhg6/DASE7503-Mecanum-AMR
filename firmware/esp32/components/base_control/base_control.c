#include "base_control.h"

#include <math.h>
#include <stddef.h>

static float clampf(float value, float lower, float upper) {
  if (value < lower) return lower;
  if (value > upper) return upper;
  return value;
}

bool base_values_are_finite(body_velocity_t velocity) {
  return isfinite(velocity.vx) && isfinite(velocity.vy) &&
         isfinite(velocity.wz);
}

wheel_speeds_t base_inverse_kinematics(float vx, float vy, float wz,
                                       float half_wheelbase,
                                       float half_track,
                                       float max_wheel_speed) {
  wheel_speeds_t result = {0};
  body_velocity_t requested = {.vx = vx, .vy = vy, .wz = wz};
  if (!base_values_are_finite(requested) || !isfinite(half_wheelbase) ||
      !isfinite(half_track) || !isfinite(max_wheel_speed) ||
      half_wheelbase <= 0.0f || half_track <= 0.0f ||
      max_wheel_speed <= 0.0f) {
    return result;
  }

  const float arm = half_wheelbase + half_track;
  result.fl = vx - vy - arm * wz;
  result.fr = vx + vy + arm * wz;
  result.rl = vx + vy - arm * wz;
  result.rr = vx - vy + arm * wz;

  float peak = fabsf(result.fl);
  if (fabsf(result.fr) > peak) peak = fabsf(result.fr);
  if (fabsf(result.rl) > peak) peak = fabsf(result.rl);
  if (fabsf(result.rr) > peak) peak = fabsf(result.rr);
  if (peak > max_wheel_speed) {
    const float scale = max_wheel_speed / peak;
    result.fl *= scale;
    result.fr *= scale;
    result.rl *= scale;
    result.rr *= scale;
  }
  return result;
}

body_velocity_t base_forward_kinematics(wheel_speeds_t wheels,
                                        float half_wheelbase,
                                        float half_track) {
  body_velocity_t result = {0};
  const float arm = half_wheelbase + half_track;
  if (!isfinite(wheels.fl) || !isfinite(wheels.fr) || !isfinite(wheels.rl) ||
      !isfinite(wheels.rr) || !isfinite(arm) || arm <= 0.0f) {
    return result;
  }
  result.vx = (wheels.fl + wheels.fr + wheels.rl + wheels.rr) * 0.25f;
  result.vy = (-wheels.fl + wheels.fr + wheels.rl - wheels.rr) * 0.25f;
  result.wz = (-wheels.fl + wheels.fr - wheels.rl + wheels.rr) /
              (4.0f * arm);
  return result;
}

float encoder_delta_to_speed(int delta_counts, float circumference_m,
                             float counts_per_revolution, float dt_seconds) {
  if (!isfinite(circumference_m) || !isfinite(counts_per_revolution) ||
      !isfinite(dt_seconds) || circumference_m <= 0.0f ||
      counts_per_revolution <= 0.0f || dt_seconds <= 0.0f) {
    return 0.0f;
  }
  return ((float)delta_counts * circumference_m) /
         (counts_per_revolution * dt_seconds);
}

void wheel_pid_reset(wheel_pid_t *pid) {
  if (pid == NULL) return;
  pid->integral = 0.0f;
  pid->previous_error = 0.0f;
}

float wheel_pid_step(wheel_pid_t *pid, float target, float measured,
                     float dt_seconds, float output_limit) {
  if (pid == NULL || !isfinite(target) || !isfinite(measured) ||
      !isfinite(dt_seconds) || !isfinite(output_limit) ||
      dt_seconds <= 0.0f || output_limit <= 0.0f) {
    return 0.0f;
  }
  const float error = target - measured;
  pid->integral += error * dt_seconds;
  pid->integral = clampf(pid->integral, -pid->integral_limit,
                         pid->integral_limit);
  const float derivative = (error - pid->previous_error) / dt_seconds;
  pid->previous_error = error;
  return clampf(pid->kp * error + pid->ki * pid->integral +
                    pid->kd * derivative,
                -output_limit, output_limit);
}
