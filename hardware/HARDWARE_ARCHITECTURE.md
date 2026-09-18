# Raspberry Pi / ESP32-S3 architecture

The Raspberry Pi owns perception, localization, planning and mission policy.
The ESP32-S3 owns deterministic wheel control, encoder sampling, servo pulses
and the final software watchdog. A physical emergency stop remains outside both
computers and must interrupt motor power or driver enable.

## Failure boundaries

- ESP32 boots disarmed and cannot drive outputs while its compile-time gate is
  zero.
- Enabling motion requires a `/base/enable=true` command and a matching
  `/base/enabled=true` acknowledgement.
- Missing `/cmd_vel` for 500 ms forces all wheel targets to zero.
- Losing the micro-ROS agent disarms the base in firmware.
- Invalid or non-finite velocity commands disarm the base.
- The host rejects non-finite odometry and invalid quaternions before publishing
  `/odom` or TF.
- Lift state reports the accepted servo command, not physical position or load.

## Active packages

| Path | Responsibility |
|---|---|
| `firmware/esp32` | ESP-IDF motor, encoder, PID, odometry, servos and micro-ROS |
| `src/mecanum_hw_bridge` | agent launch, acknowledgements, services, odom and TF |
| `src/mecanum_description` | independently modelled collision/TF geometry |
| `src/mecanum_navigation` | full-holonomic Nav2 and SLAM/AMCL |
| `src/mecanum_task_manager` | bounded QR payload and transport state machine |
