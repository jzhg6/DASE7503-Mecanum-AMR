#pragma once

/*
 * Hardware profile for the course ESP32-S3 mecanum controller.
 *
 * Values here were independently transcribed from the public interface and
 * hardware facts in 118ovo/DASE7503-Sem1-Group2 at commit d96b607. No source
 * implementation from that repository is included. Keep both output gates at
 * zero until every channel has been checked with the chassis raised.
 */

#define MOTOR_OUTPUT_COMPILED_IN 0
#define LIFT_OUTPUT_COMPILED_IN 0

#define MOTOR_PWM_FREQUENCY_HZ 25000
#define MOTOR_PWM_RESOLUTION_BITS 8
#define MOTOR_CONTROL_PERIOD_MS 10
#define COMMAND_WATCHDOG_MS 500

#define WHEEL_CIRCUMFERENCE_M 0.1508f
#define ENCODER_COUNTS_PER_REVOLUTION 1040.0f
#define HALF_WHEELBASE_M 0.0475f
#define HALF_TRACK_M 0.0675f
#define MAX_WHEEL_LINEAR_SPEED_MPS 1.0f

/* FL, FR, RL, RR. Confirm signs during the one-wheel bench test. */
#define MOTOR_FL_IN_A 4
#define MOTOR_FL_IN_B 5
#define MOTOR_FR_IN_A 15
#define MOTOR_FR_IN_B 16
#define MOTOR_RL_IN_A 9
#define MOTOR_RL_IN_B 10
#define MOTOR_RR_IN_A 13
#define MOTOR_RR_IN_B 14

#define ENCODER_FL_A 6
#define ENCODER_FL_B 7
#define ENCODER_FR_A 47
#define ENCODER_FR_B 48
#define ENCODER_RL_A 11
#define ENCODER_RL_B 12
#define ENCODER_RR_A 1
#define ENCODER_RR_B 2

#define MOTOR_FL_DIRECTION 1
#define MOTOR_FR_DIRECTION 1
#define MOTOR_RL_DIRECTION 1
#define MOTOR_RR_DIRECTION 1

#define ENCODER_FL_DIRECTION 1
#define ENCODER_FR_DIRECTION 1
#define ENCODER_RL_DIRECTION 1
#define ENCODER_RR_DIRECTION 1

#define SERVO_LEFT_GPIO 8
#define SERVO_RIGHT_GPIO 21
#define SERVO_MIN_PULSE_US 500
#define SERVO_MAX_PULSE_US 2500
#define SERVO_MIN_ANGLE_DEG (-90)
#define SERVO_MAX_ANGLE_DEG 90

/* Deliberately conservative placeholders. Calibrate with the linkage detached. */
#define LIFT_LOWER_LEFT_DEG 60
#define LIFT_LOWER_RIGHT_DEG 20
#define LIFT_RAISE_LEFT_DEG 0
#define LIFT_RAISE_RIGHT_DEG (-20)

#define PID_KP 0.85f
#define PID_KI 0.20f
#define PID_KD 0.005f
#define PID_INTEGRAL_LIMIT 0.60f
