# Physical hardware profile

The active robot is a Raspberry Pi plus ESP32-S3 mecanum platform. The ESP32
runs ESP-IDF and micro-ROS over Wi-Fi; there is no active ASCII UART bridge.

```text
Raspberry Pi                         ESP32-S3 course controller
-------------                        -------------------------
Nav2 -------- /cmd_vel ------------> closed-loop wheel PID
safety ------ /base/enable --------> compile gate + runtime latch
lift service  /lift/command -------> two calibrated servos
TF adapter <- /wheel/odom ---------- four quadrature encoders
status <----- /base/enabled -------- firmware acknowledgement
status <----- /lift/state ---------- open-loop command acknowledgement

MS200 -> /scan -> SLAM/AMCL/Nav2
Pi camera -> /camera/image_raw -> bounded QR task parser
```

The authoritative project-side values are in
`../firmware/esp32/components/robot_config/include/board_config.h`. See
`HARDWARE_PROFILE.md` for their provenance and verification state, and
`../docs/HARDWARE_BRINGUP.md` for the mandatory bench sequence.

`legacy_stm32_upstream/` and `legacy_jetson_upstream/` are retained only for
the history of the MIT base repository. They are not built or used by the
Raspberry Pi/ESP32-S3 stack.
