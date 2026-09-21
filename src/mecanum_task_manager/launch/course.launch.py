import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    course = os.path.join(get_package_share_directory('mecanum_task_manager'), 'config', 'course.yaml')
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('course_yaml', default_value=course),
        DeclareLaunchArgument('evidence_dir', default_value='evidence'),
        DeclareLaunchArgument('image_topic', default_value='/camera/image_raw'),
        Node(package='mecanum_task_manager', executable='qr_reader.py', output='screen',
             parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time'),
                          'image_topic': LaunchConfiguration('image_topic'),
                          'evidence_dir': LaunchConfiguration('evidence_dir')}]),
        Node(package='mecanum_task_manager', executable='course_mission_node.py', output='screen',
             parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time'),
                          'course_yaml': LaunchConfiguration('course_yaml'),
                          'evidence_dir': LaunchConfiguration('evidence_dir')}]),
    ])
