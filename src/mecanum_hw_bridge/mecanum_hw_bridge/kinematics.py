# Copyright (c) 2025 Tarik Kahraman
# SPDX-License-Identifier: MIT

"""
Mecanum inverse/forward kinematics and wheel speed normalization.
Used by the hardware bridge to convert /cmd_vel to wheel commands for the ESP32.
"""

from __future__ import annotations

import math


def inverse_kinematics(
    vx: float,
    vy: float,
    omega: float,
    wheel_radius: float,
    lx: float,
    ly: float,
) -> list[float]:
    """
    Map body velocity to wheel angular speeds (rad/s).

    Args:
        vx: Forward velocity (m/s).
        vy: Lateral velocity (m/s).
        omega: Angular velocity (rad/s).
        wheel_radius: Wheel radius in metres.
        lx: Half front-rear axle distance (m).
        ly: Half left-right axle distance (m).

    Returns:
        [w_fl, w_fr, w_rl, w_rr] in rad/s (front_left, front_right, rear_left, rear_right).
    """
    if not all(math.isfinite(v) for v in (vx, vy, omega, wheel_radius, lx, ly)):
        raise ValueError("velocity and geometry must be finite")
    if min(wheel_radius, lx, ly) <= 0:
        raise ValueError("wheel radius and axle half-distances must be positive")
    k = lx + ly
    r = wheel_radius
    inv_r = 1.0 / r
    w_fl = inv_r * (vx - vy - k * omega)
    w_fr = inv_r * (vx + vy + k * omega)
    w_rl = inv_r * (vx + vy - k * omega)
    w_rr = inv_r * (vx - vy + k * omega)
    return [w_fl, w_fr, w_rl, w_rr]


def normalize(wheel_speeds: list[float], max_speed: float) -> list[float]:
    """
    Scale wheel speeds so the maximum magnitude is at most max_speed, preserving ratios.

    Args:
        wheel_speeds: List of four wheel speeds (rad/s).
        max_speed: Maximum allowed magnitude (rad/s).

    Returns:
        New list of same length with magnitudes capped at max_speed.
    """
    if len(wheel_speeds) != 4 or not all(math.isfinite(v) for v in wheel_speeds):
        raise ValueError("four finite wheel speeds required")
    if not math.isfinite(max_speed) or max_speed <= 0:
        raise ValueError("max wheel speed must be finite and positive")
    max_w = max(abs(w) for w in wheel_speeds)
    if max_w <= 1e-9 or max_w <= max_speed:
        return list(wheel_speeds)
    factor = max_speed / max_w
    return [w * factor for w in wheel_speeds]


def format_motion_frame(wheel_speeds: list[float], decimal_places: int = 4) -> str:
    """Format wheel speeds as protocol line: M,w_fl,w_fr,w_rl,w_rr\\n."""
    if len(wheel_speeds) != 4:
        raise ValueError("exactly four wheel speeds are required")
    if not all(math.isfinite(v) for v in wheel_speeds):
        raise ValueError("wheel speeds must be finite")
    fmt = ",".join([f"{{:.{decimal_places}f}}" for _ in range(4)])
    return "M," + fmt.format(*wheel_speeds) + "\n"


def format_servo_frame(channel: int, angle_deg: float) -> str:
    """Format a bounded servo command: S,<channel>,<angle-deg>\\n."""
    if channel != 0:
        raise ValueError("only servo channel 0 is implemented")
    if not math.isfinite(angle_deg):
        raise ValueError("servo angle must be finite")
    angle = max(0.0, min(180.0, float(angle_deg)))
    return f"S,{channel},{angle:.1f}\n"


def format_enable_frame(enabled: bool) -> str:
    """Format the motor safety latch command."""
    return f"E,{1 if enabled else 0}\n"
