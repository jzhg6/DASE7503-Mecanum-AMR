#!/usr/bin/env python3
"""Ensure safety gates and duplicated physical constants do not drift."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "components" / "robot_config" / "include" / "board_config.h"


def macro(text: str, name: str) -> str:
    match = re.search(rf"^#define\s+{re.escape(name)}\s+(.+?)\s*$", text, re.MULTILINE)
    if not match:
        raise AssertionError(f"missing macro: {name}")
    return match.group(1)


def main() -> None:
    text = CONFIG.read_text(encoding="utf-8")
    expected = {
        "MOTOR_OUTPUT_COMPILED_IN": "0",
        "LIFT_OUTPUT_COMPILED_IN": "0",
        "WHEEL_CIRCUMFERENCE_M": "0.1508f",
        "ENCODER_COUNTS_PER_REVOLUTION": "1040.0f",
        "MOTOR_FL_IN_A": "4",
        "MOTOR_FL_IN_B": "5",
        "MOTOR_FR_IN_A": "15",
        "MOTOR_FR_IN_B": "16",
        "MOTOR_RL_IN_A": "9",
        "MOTOR_RL_IN_B": "10",
        "MOTOR_RR_IN_A": "13",
        "MOTOR_RR_IN_B": "14",
        "SERVO_LEFT_GPIO": "8",
        "SERVO_RIGHT_GPIO": "21",
    }
    for name, value in expected.items():
        actual = macro(text, name)
        if actual != value:
            raise AssertionError(f"{name}: expected {value}, got {actual}")
    print("hardware profile and output gates verified")


if __name__ == "__main__":
    main()
