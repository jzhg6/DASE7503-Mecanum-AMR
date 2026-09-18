# Copyright (c) 2026 DASE7503 project contributors
# SPDX-License-Identifier: MIT

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_dir = get_package_share_directory('mecanum_task_manager')
    default_stations = os.path.join(package_dir, 'config', 'stations.yaml')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    stations_yaml = LaunchConfiguration('stations_yaml', default=default_stations)
    home_station = LaunchConfiguration('home_station', default='HOME')
    allow_mock_lift = LaunchConfiguration('allow_mock_lift', default='false')
    allow_pose_only_docking = LaunchConfiguration(
        'allow_pose_only_docking', default='false'
    )
    image_topic = LaunchConfiguration('image_topic', default='/camera/image_raw')

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument(
            'stations_yaml',
            default_value=default_stations,
            description='Whitelisted pickup, drop-off and home poses',
        ),
        DeclareLaunchArgument('home_station', default_value='HOME'),
        DeclareLaunchArgument('allow_mock_lift', default_value='false'),
        DeclareLaunchArgument('allow_pose_only_docking', default_value='false'),
        DeclareLaunchArgument('image_topic', default_value='/camera/image_raw'),
        Node(
            package='mecanum_task_manager',
            executable='qr_reader.py',
            name='qr_reader',
            parameters=[{
                'use_sim_time': use_sim_time,
                'image_topic': image_topic,
            }],
            output='screen',
        ),
        Node(
            package='mecanum_task_manager',
            executable='mission_manager.py',
            name='mission_manager',
            parameters=[{
                'use_sim_time': use_sim_time,
                'stations_yaml': stations_yaml,
                'home_station': home_station,
                'allow_mock_lift': allow_mock_lift,
                'allow_pose_only_docking': allow_pose_only_docking,
            }],
            output='screen',
        ),
    ])
