# Validation record

Validation date: 2026-09-14

This repository is a development starter for the course project. The checks
below verify source consistency and the safe-default ESP32 build; they do not
constitute acceptance testing of a physical robot.

## Checks completed locally

- ESP32 firmware compiled for the `esp32dev` PlatformIO environment with all
  motor and servo outputs disabled by default.
- Python source compiled with `compileall`.
- Mecanum kinematics unit tests passed.
- QR mission-payload parser unit tests passed.
- YAML and ROS package XML files parsed successfully.
- `git diff --check` reported no whitespace errors in first-party files. The
  pinned, unmodified `references/minibot/` snapshots retain upstream formatting.

## Checks deferred to ROS CI or physical hardware

- A full ROS 2/colcon build and Gazebo launch were not run locally because the
  available Ubuntu 24.04 WSL environment does not have ROS installed and no
  Docker runtime is available. GitHub Actions performs the ROS 2 Humble build.
- Motor polarity, encoder counts, wheel radius, wheelbase, track width, serial
  device, LiDAR driver, camera calibration and servo travel must be measured on
  the supplied hardware.
- Closed-loop wheel PID, encoder odometry, TF validation, docking accuracy,
  load detection and end-to-end transport/QR missions remain physical-robot
  acceptance criteria.

## Safety gate

The ESP32 configuration intentionally contains placeholder pins and sets
`MOTOR_OUTPUT_ENABLED` and `SERVO_OUTPUT_ENABLED` to `0`. Do not enable either
output until the wiring and emergency-stop behavior have been verified with
the chassis lifted and the motor power supply current-limited.
