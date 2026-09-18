"""Start the micro-ROS agent and the host-side hardware supervisor."""

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
    launch_agent = LaunchConfiguration("launch_agent")
    agent_port = LaunchConfiguration("agent_port")

    return LaunchDescription([
        DeclareLaunchArgument("launch_agent", default_value="true"),
        DeclareLaunchArgument("agent_port", default_value="8090"),
        DeclareLaunchArgument("config_file", default_value=config),
        Node(
            package="micro_ros_agent",
            executable="micro_ros_agent",
            name="micro_ros_agent",
            arguments=["udp4", "--port", agent_port],
            output="screen",
            condition=IfCondition(launch_agent),
        ),
        Node(
            package="mecanum_hw_bridge",
            executable="hardware_supervisor.py",
            name="hardware_supervisor",
            parameters=[LaunchConfiguration("config_file")],
            output="screen",
        ),
    ])
