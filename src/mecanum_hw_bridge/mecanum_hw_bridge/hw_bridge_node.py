#!/usr/bin/env python3
# Copyright (c) 2025 Tarik Kahraman
# SPDX-License-Identifier: MIT

"""
Hardware bridge node: runs on Raspberry Pi, forwards /cmd_vel, servo and
safety requests to the ESP32 over UART. See hardware/docs/PROTOCOL.md.
"""

from __future__ import annotations

import time
import math
from typing import Optional

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_srvs.srv import Trigger

from kinematics import (
    format_enable_frame,
    format_motion_frame,
    format_servo_frame,
    inverse_kinematics,
    normalize,
)

try:
    import serial
    HAS_SERIAL = True
except ImportError:
    serial = None  # type: ignore
    HAS_SERIAL = False


class HwBridgeNode(Node):
    """
    ROS 2 node that bridges /cmd_vel and lift services to the ESP32 over UART.
    Motors start disabled and both sides implement independent watchdogs.
    """

    def __init__(self) -> None:
        super().__init__("hw_bridge_node")

        self._declare_parameters()
        self._load_parameters()
        self._enabled = False
        self._serial: Optional[serial.Serial] = None
        self._next_reconnect_time = 0.0
        self._open_serial()
        self._last_cmd_time = 0.0
        self._last_twist = Twist()

        self._cmd_vel_sub = self.create_subscription(
            Twist, "/cmd_vel", self._cmd_vel_cb, 10
        )
        self._lift_up_srv = self.create_service(
            Trigger, "lift/up", self._lift_up_cb
        )
        self._lift_down_srv = self.create_service(
            Trigger, "lift/down", self._lift_down_cb
        )
        self._enable_srv = self.create_service(
            Trigger, "safety/enable", self._enable_cb
        )
        self._stop_srv = self.create_service(
            Trigger, "safety/stop", self._stop_cb
        )
        motion_rate = self._motion_rate_hz
        self._timer = self.create_timer(1.0 / motion_rate, self._timer_cb)

        self.get_logger().info(
            "hw_bridge_node started (serial=%s, timeout=%.2fs, rate=%.0f Hz)"
            % (
                self._serial_port,
                self._cmd_timeout_sec,
                self._motion_rate_hz,
            )
        )

    def _declare_parameters(self) -> None:
        self.declare_parameter("serial_port", "/dev/ttyUSB0")
        self.declare_parameter("baud_rate", 115200)
        self.declare_parameter("wheel_radius", 0.05)
        self.declare_parameter("lx", 0.115)
        self.declare_parameter("ly", 0.125)
        self.declare_parameter("max_wheel_speed", 10.0)
        self.declare_parameter("cmd_timeout_sec", 0.5)
        self.declare_parameter("motion_rate_hz", 25.0)
        self.declare_parameter("servo_channel", 0)
        self.declare_parameter("servo_up_deg", 120.0)
        self.declare_parameter("servo_down_deg", 35.0)
        self.declare_parameter("reconnect_interval_sec", 2.0)

    def _load_parameters(self) -> None:
        self._serial_port = self.get_parameter("serial_port").value
        self._baud_rate = self.get_parameter("baud_rate").value
        self._wheel_radius = self.get_parameter("wheel_radius").value
        self._lx = self.get_parameter("lx").value
        self._ly = self.get_parameter("ly").value
        self._max_wheel_speed = self.get_parameter("max_wheel_speed").value
        self._cmd_timeout_sec = self.get_parameter("cmd_timeout_sec").value
        self._motion_rate_hz = self.get_parameter("motion_rate_hz").value
        self._servo_channel = self.get_parameter("servo_channel").value
        self._servo_up_deg = self.get_parameter("servo_up_deg").value
        self._servo_down_deg = self.get_parameter("servo_down_deg").value
        self._reconnect_interval_sec = self.get_parameter(
            "reconnect_interval_sec"
        ).value
        for value in (self._wheel_radius, self._lx, self._ly,
                      self._max_wheel_speed, self._cmd_timeout_sec,
                      self._motion_rate_hz, self._reconnect_interval_sec):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("geometry, limits and timing must be finite and positive")
        format_servo_frame(self._servo_channel, self._servo_up_deg)
        format_servo_frame(self._servo_channel, self._servo_down_deg)

    def _open_serial(self) -> None:
        self._enabled = False
        self._last_cmd_time = 0.0
        if not HAS_SERIAL:
            self.get_logger().warn(
                "pyserial not installed; install with: pip install pyserial"
            )
            self._next_reconnect_time = time.monotonic() + self._reconnect_interval_sec
            return
        try:
            self._serial = serial.Serial(
                port=self._serial_port,
                baudrate=self._baud_rate,
                timeout=0.02,
                write_timeout=0.1,
            )
            self.get_logger().info(
                "Serial opened: %s @ %d" % (self._serial_port, self._baud_rate)
            )
            self._write_serial(format_enable_frame(False))
            self._send_motion(0.0, 0.0, 0.0)
        except Exception as e:
            self.get_logger().error(
                "Serial open failed: %s. Check port and permissions." % e
            )
            self._serial = None
            self._next_reconnect_time = (
                time.monotonic() + self._reconnect_interval_sec
            )

    def _cmd_vel_cb(self, msg: Twist) -> None:
        if not self._enabled:
            return
        if not all(math.isfinite(v) for v in
                   (msg.linear.x, msg.linear.y, msg.angular.z)):
            self._enabled = False
            self._last_cmd_time = 0.0
            self._write_serial(format_enable_frame(False))
            return
        self._last_twist = msg
        self._last_cmd_time = time.monotonic()

    def _timer_cb(self) -> None:
        if self._serial is None or not self._serial.is_open:
            if time.monotonic() >= self._next_reconnect_time:
                self._open_serial()
            return
        now = time.monotonic()
        if not self._enabled or now - self._last_cmd_time > self._cmd_timeout_sec:
            self._send_motion(0.0, 0.0, 0.0)
            return
        t = self._last_twist
        self._send_motion(
            float(t.linear.x),
            float(t.linear.y),
            float(t.angular.z),
        )

    def _send_motion(self, vx: float, vy: float, omega: float) -> None:
        ws = inverse_kinematics(
            vx, vy, omega,
            self._wheel_radius, self._lx, self._ly,
        )
        ws = normalize(ws, self._max_wheel_speed)
        line = format_motion_frame(ws)
        self._write_serial(line)

    def _write_serial(self, s: str) -> bool:
        if self._serial is None or not self._serial.is_open:
            return False
        try:
            self._serial.write(s.encode("ascii"))
            return True
        except Exception as e:
            self.get_logger().error("Serial write failed: %s" % e)
            self._enabled = False
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
            self._next_reconnect_time = (
                time.monotonic() + self._reconnect_interval_sec
            )
            return False

    def _lift_up_cb(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        if not self._enabled:
            response.success = False
            response.message = "Safety latch disabled"
            return response
        response.success = self._write_serial(
            format_servo_frame(self._servo_channel, self._servo_up_deg)
        )
        response.message = "Lift up sent" if response.success else "ESP32 offline"
        return response

    def _lift_down_cb(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        if not self._enabled:
            response.success = False
            response.message = "Safety latch disabled"
            return response
        response.success = self._write_serial(
            format_servo_frame(self._servo_channel, self._servo_down_deg)
        )
        response.message = "Lift down sent" if response.success else "ESP32 offline"
        return response

    def _enable_cb(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        self._last_cmd_time = 0.0
        self._last_twist = Twist()
        response.success = self._write_serial(format_enable_frame(True))
        self._enabled = response.success
        response.message = (
            "Enable frame sent; physical outputs/MCU acceptance not verified"
            if response.success else "ESP32 offline"
        )
        return response

    def _stop_cb(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        self._enabled = False
        self._last_cmd_time = 0.0
        motion_ok = self._write_serial("M,0.0000,0.0000,0.0000,0.0000\n")
        stop_ok = self._write_serial(format_enable_frame(False))
        response.success = motion_ok and stop_ok
        response.message = (
            "Disable frame sent" if response.success else "ESP32 offline"
        )
        return response

    def destroy_node(self, *args, **kwargs) -> None:
        if self._serial is not None and self._serial.is_open:
            try:
                self._serial.write(format_enable_frame(False).encode("ascii"))
                self._serial.close()
            except Exception:
                pass
            self._serial = None
        super().destroy_node(*args, **kwargs)


def main(args: Optional[list] = None) -> None:
    rclpy.init(args=args)
    node = HwBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
