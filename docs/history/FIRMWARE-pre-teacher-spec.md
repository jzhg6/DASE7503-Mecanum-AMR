# Historical ESP32-S3 notes - do not use Humble or UDP settings for this course

This is an independent ESP-IDF and micro-ROS implementation for the course
controller board. It does not contain source files from the previous student
repository. Only externally observable hardware facts (GPIO assignments,
encoder resolution, wheel circumference and ROS responsibilities) were used.

## Safety defaults

`MOTOR_OUTPUT_COMPILED_IN` and `LIFT_OUTPUT_COMPILED_IN` in
`components/robot_config/include/board_config.h` are both `0`. A runtime ROS
command cannot override these compile-time gates. Motor targets are forced to
zero when `/cmd_vel` is silent for 500 ms; losing the micro-ROS agent also
clears the runtime enable latch.

## ROS interface

| Direction | Topic | Type | Meaning |
|---|---|---|---|
| subscribe | `/cmd_vel` | `geometry_msgs/Twist` | body velocity request |
| subscribe | `/base/enable` | `std_msgs/Bool` | arm or disarm motors |
| subscribe | `/lift/command` | `std_msgs/Int32` | `0` lower, `1` raise |
| publish | `/wheel/odom` | `nav_msgs/Odometry` | encoder-integrated odometry |
| publish | `/base/enabled` | `std_msgs/Bool` | actual firmware arm state |
| publish | `/lift/state` | `std_msgs/Int32` | acknowledged open-loop command |

`/lift/state` is not load or position feedback. The supplied hardware has no
lift limit switch or position sensor, so the Raspberry Pi must not present it as
proof that a load was successfully picked up.

## Build on Linux

Use the ROS distribution chosen for the Raspberry Pi consistently. The current
repository baseline is Ubuntu 22.04 and ROS 2 Humble.

```bash
source ~/esp/esp-idf/export.sh
cd firmware/esp32
pip3 install catkin_pkg colcon-common-extensions lark "empy<4"
idf.py set-target esp32s3
idf.py menuconfig
idf.py build
idf.py flash monitor
```

`main/idf_component.yml` pins the Humble-compatible `22.x` micro-ROS component;
ESP-IDF downloads it into `managed_components` on Linux. In `menuconfig`,
configure the micro-ROS Wi-Fi transport, agent address, agent
port (the project default is 8090) and the same ROS domain ID used on the Pi.
Do not commit Wi-Fi credentials or a fixed local IP address.

## Required bench sequence

1. Run `make firmware-host-test` on a normal computer.
2. Flash with both compile gates at zero and confirm micro-ROS topics appear.
3. With motor power disconnected, rotate each wheel by hand and verify the sign
   and scale of `/wheel/odom`.
4. Raise the chassis, enable one motor at a time and correct the direction
   constants. Use a current-limited supply and a physical emergency stop.
5. Tune each wheel PID at low speed before testing lateral motion.
6. Detach the lift linkage, calibrate both servos, then update the four lift
   angles. Only after those checks should the output gates be changed to `1`.

The repository intentionally does not provide a ready-to-flash `sdkconfig`,
because it contains network settings and depends on the selected ESP-IDF and
micro-ROS versions.
