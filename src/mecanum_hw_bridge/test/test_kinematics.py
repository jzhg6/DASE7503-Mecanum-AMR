#!/usr/bin/env python3
# Copyright (c) 2025 Tarik Kahraman
# SPDX-License-Identifier: MIT

"""Unit tests for hardware bridge kinematics (inverse and normalize)."""

import sys
import os

# Ensure package is importable (source tree or install)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_pkg_root = os.path.dirname(_script_dir)
_module_dir = os.path.join(_pkg_root, "mecanum_hw_bridge")
if os.path.isdir(_module_dir) and _module_dir not in sys.path:
    sys.path.insert(0, _pkg_root)
try:
    from mecanum_hw_bridge.kinematics import (
        inverse_kinematics,
        normalize,
        format_motion_frame,
        format_servo_frame,
        format_enable_frame,
    )
except ImportError:
    sys.path.insert(0, _module_dir)
    from kinematics import (
        inverse_kinematics,
        normalize,
        format_motion_frame,
        format_servo_frame,
        format_enable_frame,
    )


def test_inverse_kinematics_zero():
    r, lx, ly = 0.075, 0.25, 0.35
    ws = inverse_kinematics(0.0, 0.0, 0.0, r, lx, ly)
    assert len(ws) == 4
    assert all(abs(w) < 1e-9 for w in ws)


def test_inverse_kinematics_forward():
    r, lx, ly = 0.075, 0.25, 0.35
    ws = inverse_kinematics(1.0, 0.0, 0.0, r, lx, ly)
    assert len(ws) == 4
    assert all(w > 0 for w in ws)
    assert abs(ws[0] - ws[1]) < 1e-6 and abs(ws[0] - ws[2]) < 1e-6 and abs(ws[0] - ws[3]) < 1e-6


def test_inverse_kinematics_backward():
    r, lx, ly = 0.075, 0.25, 0.35
    ws_fwd = inverse_kinematics(1.0, 0.0, 0.0, r, lx, ly)
    ws_bwd = inverse_kinematics(-1.0, 0.0, 0.0, r, lx, ly)
    for a, b in zip(ws_fwd, ws_bwd):
        assert abs(a + b) < 1e-9


def test_normalize_caps():
    ws = [20.0, -10.0, 5.0, 15.0]
    out = normalize(ws, 10.0)
    assert max(abs(w) for w in out) <= 10.0 + 1e-9
    assert abs(out[0]) == 10.0


def test_normalize_unchanged():
    ws = [1.0, 2.0, 3.0, 4.0]
    out = normalize(ws, 10.0)
    assert out == ws


def test_format_motion_frame():
    ws = [1.0, -2.0, 0.5, 0.0]
    line = format_motion_frame(ws)
    assert line.startswith("M,")
    assert line.endswith("\n")
    parts = line.strip().split(",")
    assert len(parts) == 5
    assert parts[0] == "M"
    assert float(parts[1]) == 1.0
    assert float(parts[2]) == -2.0


def test_protocol_control_frames():
    assert format_servo_frame(0, 90) == "S,0,90.0\n"
    assert format_servo_frame(0, -20) == "S,0,0.0\n"
    assert format_servo_frame(0, 200) == "S,0,180.0\n"
    assert format_enable_frame(True) == "E,1\n"
    assert format_enable_frame(False) == "E,0\n"


def test_motion_frame_rejects_wrong_wheel_count():
    try:
        format_motion_frame([1.0, 2.0])
        assert False, "expected ValueError"
    except ValueError:
        pass


def run_tests():
    test_inverse_kinematics_zero()
    test_inverse_kinematics_forward()
    test_inverse_kinematics_backward()
    test_normalize_caps()
    test_normalize_unchanged()
    test_format_motion_frame()
    test_protocol_control_frames()
    test_motion_frame_rejects_wrong_wheel_count()
    print("All kinematics tests passed.")


if __name__ == "__main__":
    run_tests()
    sys.exit(0)
