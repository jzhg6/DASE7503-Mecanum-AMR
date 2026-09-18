# Validation record

Validation date: 2026-09-18

These checks validate source consistency and safe defaults. They do not claim
that the physical robot has completed a navigation or transport mission.

## Automated checks

- Pure-C mecanum forward/inverse kinematics, wheel-speed limiting, encoder
  conversion and PID core are compiled with warnings-as-errors and unit tested.
- The hardware-profile test verifies the documented GPIO facts and ensures both
  physical-output compile gates remain zero in committed code.
- Python source is syntax checked and QR mission-schema tests run without ROS.
- ROS 2 Humble CI resolves dependencies, performs a colcon build and runs tests.
- XML, YAML and launch-source parsing are checked before release.
- `git diff --check` rejects new whitespace errors.

## Not yet physically verified

- GPIO continuity and actual board revision.
- Motor/encoder signs, 1040 count/rev and loaded wheel circumference.
- PID gains, current limits and 500 ms physical stop time.
- Acrylic dimensions, camera/LiDAR transforms and loaded footprint.
- MS200 driver compatibility with the selected Linux image.
- Raspberry Pi camera/libcamera compatibility and recognition range.
- Safe dual-servo angles, payload retention and repeatable docking accuracy.
- End-to-end `QR -> pickup -> lift -> drop-off -> lower -> home` evidence.

## Release gate

Committed firmware must keep `MOTOR_OUTPUT_COMPILED_IN=0` and
`LIFT_OUTPUT_COMPILED_IN=0`. Enabling either is a per-robot calibration change
and requires the checklist in `docs/HARDWARE_BRINGUP.md`, a physical emergency
stop and current-limited, raised-chassis testing.
