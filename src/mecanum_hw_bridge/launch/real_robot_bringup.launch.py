# Copyright (c) 2025 Tarik Kahraman
# SPDX-License-Identifier: MIT

"""
Launch the hardware bridge for the real robot (Raspberry Pi + ESP32).
Use this on the Raspberry Pi when the ESP32 is connected via USB UART.
Optionally override serial_port and baud_rate.
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_dir = get_package_share_directory("mecanum_hw_bridge")
    config_path = os.path.join(pkg_dir, "config", "hw_bridge.yaml")

    return LaunchDescription([
        DeclareLaunchArgument(
            "serial_port",
            default_value="/dev/ttyUSB0",
            description="ESP32 USB UART device; prefer a stable udev symlink",
        ),
        DeclareLaunchArgument("baud_rate", default_value="115200"),
        Node(
            package="mecanum_hw_bridge",
            executable="hw_bridge_node.py",
            name="hw_bridge_node",
            parameters=[
                config_path,
                {
                    "serial_port": LaunchConfiguration("serial_port"),
                    "baud_rate": LaunchConfiguration("baud_rate"),
                },
            ],
            output="screen",
        ),
    ])
