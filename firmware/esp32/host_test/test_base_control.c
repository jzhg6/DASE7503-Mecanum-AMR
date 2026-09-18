#include <assert.h>
#include <math.h>
#include <stdio.h>

#include "base_control.h"

static int close_enough(float a, float b) { return fabsf(a - b) < 1e-5f; }

int main(void) {
  wheel_speeds_t forward =
      base_inverse_kinematics(0.4f, 0.0f, 0.0f, 0.0475f, 0.0675f, 1.0f);
  assert(close_enough(forward.fl, 0.4f));
  assert(close_enough(forward.fr, 0.4f));
  assert(close_enough(forward.rl, 0.4f));
  assert(close_enough(forward.rr, 0.4f));

  wheel_speeds_t left =
      base_inverse_kinematics(0.0f, 0.3f, 0.0f, 0.0475f, 0.0675f, 1.0f);
  assert(close_enough(left.fl, -0.3f));
  assert(close_enough(left.fr, 0.3f));
  assert(close_enough(left.rl, 0.3f));
  assert(close_enough(left.rr, -0.3f));

  body_velocity_t recovered =
      base_forward_kinematics(left, 0.0475f, 0.0675f);
  assert(close_enough(recovered.vx, 0.0f));
  assert(close_enough(recovered.vy, 0.3f));
  assert(close_enough(recovered.wz, 0.0f));

  const float one_revolution =
      encoder_delta_to_speed(1040, 0.1508f, 1040.0f, 1.0f);
  assert(close_enough(one_revolution, 0.1508f));

  wheel_speeds_t limited =
      base_inverse_kinematics(2.0f, 0.0f, 0.0f, 0.0475f, 0.0675f, 1.0f);
  assert(close_enough(limited.fl, 1.0f));
  assert(close_enough(limited.rr, 1.0f));

  wheel_pid_t pid = {.kp = 1.0f, .ki = 0.2f, .kd = 0.0f,
                     .integral_limit = 0.5f};
  const float output = wheel_pid_step(&pid, 1.0f, 0.0f, 0.01f, 1.0f);
  assert(output > 0.0f && output <= 1.0f);
  wheel_pid_reset(&pid);
  assert(close_enough(pid.integral, 0.0f));

  puts("base_control host tests passed");
  return 0;
}
