#pragma once

// Keep disabled until the wiring and wheel-direction bench tests are complete.
#define MOTOR_OUTPUT_ENABLED 0

#define SERIAL_BAUD 115200
#define COMMAND_WATCHDOG_MS 500
#define TELEMETRY_PERIOD_MS 1000
#define MAX_WHEEL_SPEED_RAD_S 10.0F

#define MOTOR_PWM_FREQUENCY 20000
#define MOTOR_PWM_RESOLUTION_BITS 8

// Replace -1 with the actual H-bridge input pins after checking the board.
// Do not use ESP32 boot-strapping pins without verifying their required levels.
#define MOTOR_FL_IN1 -1
#define MOTOR_FL_IN2 -1
#define MOTOR_FR_IN1 -1
#define MOTOR_FR_IN2 -1
#define MOTOR_RL_IN1 -1
#define MOTOR_RL_IN2 -1
#define MOTOR_RR_IN1 -1
#define MOTOR_RR_IN2 -1

#define MOTOR_FL_INVERT 0
#define MOTOR_FR_INVERT 0
#define MOTOR_RL_INVERT 0
#define MOTOR_RR_INVERT 0

#define SERVO_0_PIN -1
// Low-speed LEDC group: separate timers from motor channels 0-7.
#define SERVO_PWM_CHANNEL 8
#define SERVO_OUTPUT_ENABLED 0
#define SERVO_MIN_US 500
#define SERVO_MAX_US 2500
#define SERVO_SAFE_ANGLE_DEG 35
