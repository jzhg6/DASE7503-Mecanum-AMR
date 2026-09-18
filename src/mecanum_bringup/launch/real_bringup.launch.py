# Copyright (c) 2026 DASE7503 project contributors
# SPDX-License-Identifier: MIT
"""Bring up the real Raspberry Pi, ESP32-S3 and sensor stack."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    description_dir = get_package_share_directory('mecanum_description')
    hardware_dir = get_package_share_directory('mecanum_hw_bridge')
    navigation_dir = get_package_share_directory('mecanum_navigation')
    task_dir = get_package_share_directory('mecanum_task_manager')

    launch_agent = LaunchConfiguration('launch_agent')
    launch_sensors = LaunchConfiguration('launch_sensors')
    launch_lidar = LaunchConfiguration('launch_lidar')
    launch_camera = LaunchConfiguration('launch_camera')
    launch_navigation = LaunchConfiguration('launch_navigation')
    launch_task_manager = LaunchConfiguration('launch_task_manager')
    slam_mode = LaunchConfiguration('slam_mode')
    map_yaml = LaunchConfiguration('map_yaml')
    stations_yaml = LaunchConfiguration('stations_yaml')
    allow_pose_only_docking = LaunchConfiguration('allow_pose_only_docking')

    robot_description = ParameterValue(
        Command([
            'xacro ',
            os.path.join(description_dir, 'urdf', 'mecanum_amr.urdf.xacro'),
        ]),
        value_type=str,
    )

    hardware = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(hardware_dir, 'launch', 'hardware.launch.py')
        ),
        launch_arguments={'launch_agent': launch_agent}.items(),
    )
    sensors = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(hardware_dir, 'launch', 'sensors.launch.py')
        ),
        launch_arguments={
            'launch_lidar': launch_lidar,
            'launch_camera': launch_camera,
        }.items(),
        condition=IfCondition(launch_sensors),
    )
    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(navigation_dir, 'launch', 'navigation.launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'false',
            'slam_mode': slam_mode,
            'map_yaml': map_yaml,
        }.items(),
        condition=IfCondition(launch_navigation),
    )
    tasks = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(task_dir, 'launch', 'task_manager.launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'false',
            'stations_yaml': stations_yaml,
            'allow_pose_only_docking': allow_pose_only_docking,
        }.items(),
        condition=IfCondition(launch_task_manager),
    )

    return LaunchDescription([
        DeclareLaunchArgument('launch_agent', default_value='true'),
        DeclareLaunchArgument('launch_sensors', default_value='true'),
        DeclareLaunchArgument('launch_lidar', default_value='true'),
        DeclareLaunchArgument('launch_camera', default_value='true'),
        DeclareLaunchArgument('launch_navigation', default_value='false'),
        DeclareLaunchArgument('launch_task_manager', default_value='false'),
        DeclareLaunchArgument('slam_mode', default_value='true'),
        DeclareLaunchArgument('map_yaml', default_value=''),
        DeclareLaunchArgument(
            'stations_yaml',
            default_value=os.path.join(task_dir, 'config', 'stations.yaml'),
        ),
        DeclareLaunchArgument(
            'allow_pose_only_docking',
            default_value='false',
            description=(
                'Allow real missions without a docking/contact sensor only after '
                'station and lift calibration'
            ),
        ),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': False,
            }],
            output='screen',
        ),
        hardware,
        sensors,
        navigation,
        tasks,
    ])
