#include <Arduino.h>
#include <math.h>
#include <stdio.h>

#include "robot_config.h"

namespace {

struct MotorConfig {
  int in1;
  int in2;
  int channel1;
  int channel2;
  bool invert;
};

MotorConfig motors[4] = {
    {MOTOR_FL_IN1, MOTOR_FL_IN2, 0, 1, MOTOR_FL_INVERT != 0},
    {MOTOR_FR_IN1, MOTOR_FR_IN2, 2, 3, MOTOR_FR_INVERT != 0},
    {MOTOR_RL_IN1, MOTOR_RL_IN2, 4, 5, MOTOR_RL_INVERT != 0},
    {MOTOR_RR_IN1, MOTOR_RR_IN2, 6, 7, MOTOR_RR_INVERT != 0},
};

String inputLine;
bool discardLine = false;
bool controlEnabled = false;
bool watchdogStopped = true;
unsigned long lastMotionMs = 0;
unsigned long lastTelemetryMs = 0;
int servoAngleDeg = SERVO_SAFE_ANGLE_DEG;

void writeServo(int angle) {
  if (SERVO_OUTPUT_ENABLED == 0 || SERVO_0_PIN < 0) return;
  const int pulse = SERVO_MIN_US + (SERVO_MAX_US - SERVO_MIN_US) * angle / 180;
  ledcWrite(SERVO_PWM_CHANNEL, static_cast<uint32_t>(pulse * 65535UL / 20000UL));
}

bool motorConfigured(const MotorConfig &motor) {
  return motor.in1 >= 0 && motor.in2 >= 0;
}

void configureMotor(const MotorConfig &motor) {
  if (!motorConfigured(motor)) {
    return;
  }
  ledcSetup(motor.channel1, MOTOR_PWM_FREQUENCY,
            MOTOR_PWM_RESOLUTION_BITS);
  ledcSetup(motor.channel2, MOTOR_PWM_FREQUENCY,
            MOTOR_PWM_RESOLUTION_BITS);
  ledcAttachPin(motor.in1, motor.channel1);
  ledcAttachPin(motor.in2, motor.channel2);
  ledcWrite(motor.channel1, 0);
  ledcWrite(motor.channel2, 0);
}

void writeMotor(const MotorConfig &motor, float wheelSpeedRadS) {
  if (!motorConfigured(motor)) {
    return;
  }

  float command = wheelSpeedRadS / MAX_WHEEL_SPEED_RAD_S;
  command = fmaxf(-1.0F, fminf(1.0F, command));
  if (motor.invert) {
    command = -command;
  }

  const int duty = static_cast<int>(roundf(fabsf(command) * 255.0F));
  if (command > 0.0F) {
    ledcWrite(motor.channel1, duty);
    ledcWrite(motor.channel2, 0);
  } else if (command < 0.0F) {
    ledcWrite(motor.channel1, 0);
    ledcWrite(motor.channel2, duty);
  } else {
    ledcWrite(motor.channel1, 0);
    ledcWrite(motor.channel2, 0);
  }
}

void stopAllMotors() {
  for (const MotorConfig &motor : motors) {
    writeMotor(motor, 0.0F);
  }
}

void applyWheelSpeeds(const float speeds[4]) {
  if (!controlEnabled || MOTOR_OUTPUT_ENABLED == 0) {
    stopAllMotors();
    return;
  }
  for (int index = 0; index < 4; ++index) {
    writeMotor(motors[index], speeds[index]);
  }
}

bool parseMotion(const String &line) {
  float speeds[4] = {};
  char extra = '\0';
  const int fields = sscanf(line.c_str(), "M,%f,%f,%f,%f%c", &speeds[0],
                            &speeds[1], &speeds[2], &speeds[3], &extra);
  if (fields != 4) {
    return false;
  }
  for (float speed : speeds) {
    if (!isfinite(speed)) {
      return false;
    }
  }
  applyWheelSpeeds(speeds);
  lastMotionMs = millis();
  watchdogStopped = false;
  return true;
}

bool parseServo(const String &line) {
  if (!controlEnabled) return false;
  int channel = -1;
  float angle = 0.0F;
  char extra = '\0';
  if (sscanf(line.c_str(), "S,%d,%f%c", &channel, &angle, &extra) != 2 ||
      channel != 0 || !isfinite(angle)) {
    return false;
  }
  angle = fmaxf(0.0F, fminf(180.0F, angle));
  servoAngleDeg = static_cast<int>(roundf(angle));
  writeServo(servoAngleDeg);
  return true;
}

bool parseEnable(const String &line) {
  int enabled = -1;
  char extra = '\0';
  if (sscanf(line.c_str(), "E,%d%c", &enabled, &extra) != 1 ||
      (enabled != 0 && enabled != 1)) {
    return false;
  }
  controlEnabled = enabled == 1;
  if (!controlEnabled) {
    stopAllMotors();
    watchdogStopped = true;
  } else {
    // Enabling never replays an old motion command.
    lastMotionMs = millis();
    stopAllMotors();
  }
  return true;
}

void handleLine(String line) {
  line.trim();
  if (line.isEmpty()) {
    return;
  }

  bool valid = false;
  if (line.startsWith("M,")) {
    valid = parseMotion(line);
  } else if (line.startsWith("S,")) {
    valid = parseServo(line);
  } else if (line.startsWith("E,")) {
    valid = parseEnable(line);
  } else if (line == "H") {
    valid = true;
  }

  if (!valid) {
    Serial.println("ERR,BAD_FRAME");
  }
}

void pollSerial() {
  // Bound work per loop so a flooded UART cannot starve the watchdog.
  for (int budget = 256; budget > 0 && Serial.available() > 0; --budget) {
    const char value = static_cast<char>(Serial.read());
    if (value == '\n') {
      if (!discardLine) handleLine(inputLine);
      inputLine = "";
      discardLine = false;
    } else if (value != '\r' && !discardLine) {
      if (inputLine.length() < 127) {
        inputLine += value;
      } else {
        inputLine = "";
        discardLine = true;
        Serial.println("ERR,LINE_TOO_LONG");
      }
    }
  }
}

void applyWatchdog() {
  if (millis() - lastMotionMs > COMMAND_WATCHDOG_MS) {
    if (!watchdogStopped) {
      stopAllMotors();
      watchdogStopped = true;
      controlEnabled = false;
    }
  }
}

void publishTelemetry() {
  if (millis() - lastTelemetryMs < TELEMETRY_PERIOD_MS) {
    return;
  }
  lastTelemetryMs = millis();
  Serial.printf("T,%lu,%d,%d,%d\n", millis(), controlEnabled ? 1 : 0,
                watchdogStopped ? 1 : 0, servoAngleDeg);
}

}  // namespace

void setup() {
  Serial.begin(SERIAL_BAUD);
  inputLine.reserve(128);
  for (const MotorConfig &motor : motors) {
    configureMotor(motor);
  }
  stopAllMotors();

  if (SERVO_OUTPUT_ENABLED != 0 && SERVO_0_PIN >= 0) {
    ledcSetup(SERVO_PWM_CHANNEL, 50, 16);
    ledcAttachPin(SERVO_0_PIN, SERVO_PWM_CHANNEL);
    writeServo(SERVO_SAFE_ANGLE_DEG);
  }

  lastMotionMs = millis();
  Serial.println("READY,DASE7503_MECANUM_V1");
#if MOTOR_OUTPUT_ENABLED == 0
  Serial.println("WARN,MOTOR_OUTPUT_COMPILE_DISABLED");
#endif
}

void loop() {
  pollSerial();
  applyWatchdog();
  publishTelemetry();
  delay(1);
}
