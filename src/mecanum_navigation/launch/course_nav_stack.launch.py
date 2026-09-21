"""Jazzy Nav2 nodes used by this game; no unrelated charging/route servers."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    sim = LaunchConfiguration('use_sim_time')
    config = RewrittenYaml(source_file=LaunchConfiguration('params_file'),
                           param_rewrites={'use_sim_time': sim}, convert_types=True)
    components = [
        ('nav2_controller', 'controller_server'),
        ('nav2_planner', 'planner_server'),
        ('nav2_smoother', 'smoother_server'),
        ('nav2_behaviors', 'behavior_server'),
        ('nav2_bt_navigator', 'bt_navigator'),
        ('nav2_velocity_smoother', 'velocity_smoother'),
        ('nav2_collision_monitor', 'collision_monitor'),
    ]
    actions = [DeclareLaunchArgument('params_file'),
               DeclareLaunchArgument('use_sim_time', default_value='false')]
    for package, name in components:
        remaps = [('cmd_vel', 'cmd_vel_nav')] if name in (
            'controller_server', 'behavior_server', 'velocity_smoother') else []
        actions.append(Node(package=package, executable=name, name=name,
                            parameters=[config, {'use_sim_time': sim}],
                            remappings=remaps, output='screen'))
    actions.append(Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
                        name='lifecycle_manager_navigation', output='screen',
                        parameters=[{'autostart': True, 'use_sim_time': sim,
                                     'node_names': [name for _, name in components]}]))
    return LaunchDescription(actions)
