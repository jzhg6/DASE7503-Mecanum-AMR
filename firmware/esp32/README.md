# ESP32 firmware

This is an independently written, fail-safe starter implementation for a four-channel H-bridge and one servo. It compiles with PlatformIO's Arduino framework.

## Before flashing

1. Identify the exact ESP32 board, motor driver, servo supply and pins.
2. Fill `include/robot_config.h`; keep both output-enable flags at `0`. All output pins default to `-1`. Select the correct board; `esp32dev` is not ESP32-S3.
3. Build and flash:

```bash
cd firmware/esp32
pio run
pio run --target upload
pio device monitor
```

4. Verify protocol parsing and servo limits with motor power disconnected.
5. Verify a physical emergency stop, raise the chassis, apply a current-limited motor supply, then set `MOTOR_OUTPUT_ENABLED` to `1`.

## Limitations

The starter controller maps requested rad/s to open-loop PWM. Replace this with per-wheel encoder feedback and PID before relying on wheel odometry or low-speed autonomous docking. The final driver implementation must be adapted to the motor driver provided by the course. Motor channels 0-7 use the high-speed LEDC group; servo channel 8 uses a separate low-speed group at 50 Hz on the classic ESP32. Servo output requires its own compile-time enable flag. A motion watchdog timeout clears the runtime enable latch; servo commands require that latch too. Telemetry is command/status data, not a physical measurement.
