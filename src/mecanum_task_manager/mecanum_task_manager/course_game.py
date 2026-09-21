# Copyright (c) 2026 DASE7503 project contributors
# SPDX-License-Identifier: MIT
"""Deterministic course game rules; no ROS, wall clock or hardware dependencies."""
from dataclasses import dataclass
import itertools
import math
import re

RACKS = ("RACKA", "RACKB", "RACKC", "RACKD")


def parse_course_qr(text):
    if text in ("START", "END"):
        return text, ""
    match = re.fullmatch(r"(RACK[A-D])_([A-Za-z0-9]{4})", text)
    if not match:
        raise ValueError("expected START, END or RACK[A-D]_XXXX (4 alphanumeric characters)")
    return match.groups()


def validate_config(config, *, real=False):
    poses = config["stations"]
    required = ["START", "END_SCAN"]
    required += [f"{rack}_{part}" for rack in RACKS for part in ("APPROACH", "DOCK", "EXIT")]
    required += [f"DROP{i}_{part}" for i in range(1, 5) for part in ("POSE", "EXIT")]
    for name in required:
        pose = poses[name]
        if not all(math.isfinite(float(pose[key])) for key in ("x", "y", "yaw")):
            raise ValueError(f"invalid pose: {name}")
    if sorted(config["rack_order"]) != list(RACKS):
        raise ValueError("rack_order must contain A-D exactly once")
    codes = config.get("rack_codes", {})
    for rack, code in codes.items():
        if rack not in RACKS or parse_course_qr(code)[0] != rack:
            raise ValueError("rack_codes must map each rack to its complete printed QR")
    if real:
        if config.get("calibrated") is not True or set(codes) != set(RACKS):
            raise ValueError("real game requires calibrated poses and all four team QR codes")
        size = config["measured_robot_size_m"]
        if len(size) != 3 or any(not math.isfinite(v) or v <= 0 for v in size):
            raise ValueError("record measured physical robot dimensions")
        if any(v > limit for v, limit in zip(size, (0.30, 0.30, 0.18))):
            raise ValueError("robot exceeds the teacher's 300 x 300 x 180 mm limit")
    return config


@dataclass(frozen=True)
class Step:
    kind: str
    target: str


class CourseGame:
    """Every completion must refer to the current token; late callbacks are harmless.

    Delivered is an actuator-sequence count, not proof of physical placement.
    Timer uses the caller's monotonic seconds and includes QR/lift/nav waiting.
    """
    duration = 180.0

    def __init__(self, config):
        self.config = validate_config(config)
        self.state = "IDLE"
        self.step = None
        self.token = 0
        self.started = None
        self.delivered = []
        self.verified = {}
        self.reason = ""
        self._steps = []

    @property
    def active(self):
        return self.state in ("NAV", "SCAN", "LIFT")

    def tick(self, now):
        if self.active and now - self.started >= self.duration:
            self.stop("TIMEOUT", "180-second game limit reached")

    def stop(self, state, reason):
        self.state, self.reason = state, reason
        self.step = Step("STOP", reason)
        self.token += 1

    def qr(self, text, now):
        self.tick(now)
        try:
            kind, _ = parse_course_qr(text)
        except ValueError:
            return False
        if self.state == "IDLE" and kind == "START":
            self.started = now
            # Known, calibrated positions; QR never supplies arbitrary coordinates.
            for i, rack in enumerate(self.config["rack_order"], 1):
                self._steps.extend([
                    Step("NAV", rack + "_APPROACH"), Step("SCAN", rack),
                    Step("NAV", rack + "_DOCK"), Step("LIFT", "up"),
                    Step("NAV", rack + "_EXIT"), Step("NAV", "END_SCAN"),
                    Step("SCAN", "END"), Step("NAV", f"DROP{i}_POSE"),
                    Step("LIFT", "down"), Step("NAV", f"DROP{i}_EXIT"),
                    Step("DELIVERED", rack),
                ])
            self._advance()
            return True
        if self.state != "SCAN" or kind != self.step.target:
            return False
        expected = self.config.get("rack_codes", {}).get(kind)
        if expected is not None and expected != text:
            return False
        self.verified[kind] = text
        self._advance()
        return True

    def complete(self, token, now, success=True, reason="operation failed"):
        self.tick(now)
        if not self.active or token != self.token or self.state == "SCAN":
            return
        if not success:
            self.stop("ERROR", reason)
        else:
            self._advance()

    def _advance(self):
        self.token += 1
        while self._steps:
            self.step = self._steps.pop(0)
            if self.step.kind == "DELIVERED":
                self.delivered.append(self.step.target)
                continue
            self.state = self.step.kind
            return
        self.stop("DONE", "all four delivery sequences finished")

    def status(self, now):
        elapsed = 0.0 if self.started is None else max(0.0, now - self.started)
        return {"state": self.state, "target": self.step.target if self.step else "START",
                "elapsed_sec": round(elapsed, 2), "remaining_sec": max(0, round(180-elapsed, 2)),
                "delivery_sequences": self.delivered[:], "verified_qr": dict(self.verified),
                "reason": self.reason}
