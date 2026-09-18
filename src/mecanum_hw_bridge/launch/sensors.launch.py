"""Start the ORADAR MS200 and Raspberry Pi camera drivers."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_dir = get_package_share_directory("mecanum_hw_bridge")
    config = os.path.join(package_dir, "config", "hardware.yaml")
    return LaunchDescription([
        DeclareLaunchArgument("launch_lidar", default_value="true"),
        DeclareLaunchArgument("launch_camera", default_value="true"),
        DeclareLaunchArgument("lidar_config", default_value=config),
        Node(
            package="oradar_lidar",
            executable="oradar_scan",
            name="oradar_ms200",
            parameters=[LaunchConfiguration("lidar_config")],
            output="screen",
            condition=IfCondition(LaunchConfiguration("launch_lidar")),
        ),
        Node(
            package="camera_ros",
            executable="camera_node",
            name="camera",
            parameters=[{
                "camera": 0,
                "role": "viewfinder",
                "width": 640,
                "height": 480,
            }],
            output="screen",
            condition=IfCondition(LaunchConfiguration("launch_camera")),
        ),
    ])
