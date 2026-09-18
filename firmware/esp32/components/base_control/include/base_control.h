#pragma once

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
  float fl;
  float fr;
  float rl;
  float rr;
} wheel_speeds_t;

typedef struct {
  float vx;
  float vy;
  float wz;
} body_velocity_t;

typedef struct {
  float kp;
  float ki;
  float kd;
  float integral;
  float previous_error;
  float integral_limit;
} wheel_pid_t;

wheel_speeds_t base_inverse_kinematics(float vx, float vy, float wz,
                                       float half_wheelbase,
                                       float half_track,
                                       float max_wheel_speed);

body_velocity_t base_forward_kinematics(wheel_speeds_t wheels,
                                        float half_wheelbase,
                                        float half_track);

float encoder_delta_to_speed(int delta_counts, float circumference_m,
                             float counts_per_revolution, float dt_seconds);

void wheel_pid_reset(wheel_pid_t *pid);
float wheel_pid_step(wheel_pid_t *pid, float target, float measured,
                     float dt_seconds, float output_limit);

bool base_values_are_finite(body_velocity_t velocity);

#ifdef __cplusplus
}
#endif
