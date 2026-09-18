# ROS 2 hardware interface

The old newline-delimited serial protocol has been removed. The ESP32-S3 is a
micro-ROS node reached through a UDP agent on port 8090 by default.

| Topic | Type | Publisher | Subscriber |
|---|---|---|---|
| `/cmd_vel` | `geometry_msgs/Twist` | Nav2/teleop | ESP32 |
| `/base/enable` | `std_msgs/Bool` | supervisor | ESP32 |
| `/base/enabled` | `std_msgs/Bool` | ESP32 | supervisor/mission manager |
| `/lift/command` | `std_msgs/Int32` | supervisor | ESP32 |
| `/lift/state` | `std_msgs/Int32` | ESP32 | supervisor |
| `/wheel/odom` | `nav_msgs/Odometry` | ESP32 | supervisor |
| `/odom` | `nav_msgs/Odometry` | supervisor | Nav2 |

Lift values are `0=lower` and `1=raise`. The host exposes acknowledged service
wrappers at `/lift/down`, `/lift/up`, `/safety/enable` and `/safety/stop`.
Because the supplied lift has no position or load sensor, an acknowledgement
only confirms that the firmware accepted and applied the configured servo
pulses.
