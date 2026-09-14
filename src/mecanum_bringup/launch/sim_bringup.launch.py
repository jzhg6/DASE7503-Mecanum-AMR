import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg_sim     = get_package_share_directory('mecanum_simulation')
    pkg_nav     = get_package_share_directory('mecanum_navigation')
    pkg_control = get_package_share_directory('mecanum_control')
    pkg_task    = get_package_share_directory('mecanum_task_manager')

    default_stations = os.path.join(pkg_task, 'config', 'stations.yaml')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    world = LaunchConfiguration('world', default='warehouse')
    launch_navigation = LaunchConfiguration('launch_navigation', default='false')
    launch_control = LaunchConfiguration('launch_control', default='true')
    launch_task_manager = LaunchConfiguration('launch_task_manager', default='false')
    stations_yaml = LaunchConfiguration('stations_yaml', default=default_stations)

    # 1) Gazebo + robot spawn. world:= minimal | empty | warehouse
    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_sim, 'launch', 'gazebo.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time, 'world': world}.items()
    )

    # 2) Navigation (SLAM + Nav2) — nav2_bringup ve slam_toolbox gerekir
    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_nav, 'launch', 'navigation.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
        condition=IfCondition(launch_navigation)
    )

    # 3) Control (lift + mecanum kinematics)
    control = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_control, 'launch', 'control.launch.py')
        ),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
        condition=IfCondition(launch_control)
    )

    # 4) QR transport mission manager (requires Nav2 and lift services)
    task_manager = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_task, 'launch', 'task_manager.launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'stations_yaml': stations_yaml,
            'allow_mock_lift': 'true',
        }.items(),
        condition=IfCondition(launch_task_manager)
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation clock if true'
        ),
        DeclareLaunchArgument(
            'world',
            default_value='warehouse',
            description='World: warehouse (default), minimal, empty'
        ),
        DeclareLaunchArgument(
            'launch_navigation',
            default_value='false',
            description='Launch Nav2 + SLAM (requires ros-humble-nav2-bringup, ros-humble-slam-toolbox)'
        ),
        DeclareLaunchArgument(
            'launch_control',
            default_value='true',
            description='Launch control nodes (lift, mecanum kinematics)'
        ),
        DeclareLaunchArgument(
            'launch_task_manager',
            default_value='false',
            description='Launch task manager and QR reader (requires Nav2)'
        ),
        DeclareLaunchArgument(
            'stations_yaml',
            default_value=default_stations,
            description='Whitelisted station pose YAML for QR transport missions'
        ),
        simulation,
        navigation,
        control,
        task_manager,
    ])
