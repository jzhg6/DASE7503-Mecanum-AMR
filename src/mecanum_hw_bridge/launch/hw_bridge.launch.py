# Copyright (c) 2025 Tarik Kahraman
# SPDX-License-Identifier: MIT

"""Launch the Raspberry Pi -> ESP32 UART bridge with configurable geometry."""

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
            description="ESP32 USB UART port or stable udev symlink",
        ),
        DeclareLaunchArgument("baud_rate", default_value="115200"),
        DeclareLaunchArgument("config_file", default_value=config_path,
                              description="Full path to hw_bridge YAML config"),
        Node(
            package="mecanum_hw_bridge",
            executable="hw_bridge_node.py",
            name="hw_bridge_node",
            parameters=[
                LaunchConfiguration("config_file"),
                {
                    "serial_port": LaunchConfiguration("serial_port"),
                    "baud_rate": LaunchConfiguration("baud_rate"),
                },
            ],
            output="screen",
        ),
    ])
