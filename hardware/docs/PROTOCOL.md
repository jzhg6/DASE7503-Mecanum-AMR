# Raspberry Pi - ESP32 serial protocol

Default link: USB UART, 115200 baud, 8N1. Each ASCII frame ends in LF (`\n`). The format is intentionally readable during bench testing. It is not intended for a noisy, long-distance cable; add a checksum or use CAN/RS-485 if the final wiring requires it.

## Raspberry Pi to ESP32

### Motion command

```text
M,w_fl,w_fr,w_rl,w_rr\n
```

Wheel speeds are rad/s in the order front-left, front-right, rear-left, rear-right. The Raspberry Pi sends at 25 Hz. The ESP32 stops all wheels if no valid `M` frame arrives for 500 ms.

### Servo command

```text
S,channel,angle_deg\n
```

- `channel` is currently `0` for the lift/gripper servo.
- `angle_deg` is clamped to 0-180 by both endpoints.
- Calibrate unloaded `servo_down_deg` and `servo_up_deg` before attaching the linkage.

### Safety latch

```text
E,0\n   disable motor outputs immediately
E,1\n   permit motor commands after physical checks
```

The ESP32 boots disabled. The Raspberry Pi bridge also sends `E,0` whenever it opens the port and when it shuts down. This software latch supplements, but does not replace, a physical emergency stop.

### Heartbeat

```text
H\n
```

The heartbeat confirms link activity but does not keep motion alive. Only a valid `M` frame resets the motion watchdog.

## ESP32 to Raspberry Pi

The starter firmware emits:

```text
T,uptime_ms,enabled,watchdog_stopped,servo_angle\n
```

This is diagnostic telemetry, not wheel odometry. A closed-loop version should extend telemetry with encoder counts, measured wheel speed, battery voltage and fault flags.

## Invalid input

- Unknown frame types, missing fields, non-finite values and overlong lines are ignored.
- An invalid line never changes the current motor command.
- Any serial disconnect or parser failure must ultimately result in the independent ESP32 watchdog stopping the motors.

## Example session

```text
ESP32> READY,DASE7503_MECANUM_V1
Pi>    E,1
Pi>    M,2.0,2.0,2.0,2.0
ESP32> T,1000,1,0,35
Pi>    S,0,120
Pi>    M,0.0,0.0,0.0,0.0
Pi>    E,0
```
