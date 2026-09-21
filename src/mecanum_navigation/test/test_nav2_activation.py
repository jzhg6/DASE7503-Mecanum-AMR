#!/usr/bin/env python3
"""Exercise real Jazzy plugins/lifecycles with synthetic scan, map, TF and odom.

This is not a robot dynamics or navigation-accuracy test.
"""
import math
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest
import rclpy
from geometry_msgs.msg import TransformStamped
from lifecycle_msgs.srv import GetState
from nav_msgs.msg import OccupancyGrid, Odometry
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from sensor_msgs.msg import LaserScan
from tf2_ros import StaticTransformBroadcaster, TransformBroadcaster


class Nav2ActivationTest(unittest.TestCase):
    def test_all_course_servers_activate(self):
        rclpy.init()
        node = Node('course_nav_test_inputs')
        transforms = StaticTransformBroadcaster(node)
        dynamic = TransformBroadcaster(node)
        pairs = [('map', 'odom'), ('base_footprint', 'base_link'), ('base_link', 'lidar_link')]
        fixed = []
        for parent, child in pairs:
            tf = TransformStamped()
            tf.header.frame_id, tf.child_frame_id = parent, child
            tf.transform.rotation.w = 1.0
            fixed.append(tf)
        transforms.sendTransform(fixed)
        scan_pub = node.create_publisher(LaserScan, '/scan', 10)
        odom_pub = node.create_publisher(Odometry, '/odom', 10)
        map_pub = node.create_publisher(OccupancyGrid, '/map', QoSProfile(
            depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
        grid = OccupancyGrid()
        grid.header.frame_id = 'map'
        grid.info.resolution, grid.info.width, grid.info.height = 0.05, 120, 120
        grid.info.origin.position.x = grid.info.origin.position.y = -3.0
        grid.info.origin.orientation.w = 1.0
        grid.data = [0] * (120*120)
        names = ['controller_server', 'planner_server', 'smoother_server',
                 'behavior_server', 'bt_navigator', 'velocity_smoother', 'collision_monitor']
        clients = {n: node.create_client(GetState, '/' + n + '/get_state') for n in names}
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='course-nav-test-') as output:
            with open(Path(output) / 'nav.log', 'w+') as log:
                process = subprocess.Popen(['ros2', 'launch', str(source / 'launch/course_nav_stack.launch.py'),
                    'params_file:=' + str(source / 'config/nav2_params.yaml'), 'use_sim_time:=false'],
                    stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                active, pending = set(), {}
                deadline = time.monotonic() + 55
                try:
                    while time.monotonic() < deadline and len(active) != len(names):
                        stamp = node.get_clock().now().to_msg()
                        tf = TransformStamped()
                        tf.header.stamp, tf.header.frame_id, tf.child_frame_id = stamp, 'odom', 'base_footprint'
                        tf.transform.rotation.w = 1.0
                        dynamic.sendTransform(tf)
                        odom = Odometry()
                        odom.header.stamp, odom.header.frame_id = stamp, 'odom'
                        odom.child_frame_id, odom.pose.pose.orientation.w = 'base_footprint', 1.0
                        odom_pub.publish(odom)
                        scan = LaserScan()
                        scan.header.stamp, scan.header.frame_id = stamp, 'lidar_link'
                        scan.angle_min, scan.angle_max, scan.angle_increment = -math.pi, math.pi, math.pi/180
                        scan.range_min, scan.range_max, scan.scan_time = 0.05, 10.0, 0.05
                        scan.ranges = [2.0] * 361
                        scan_pub.publish(scan)
                        grid.header.stamp = stamp
                        map_pub.publish(grid)
                        for name, client in clients.items():
                            if name in active:
                                continue
                            future = pending.get(name)
                            if future is not None and future.done():
                                if future.result().current_state.id == 3:
                                    active.add(name)
                                pending.pop(name)
                            if name not in pending and client.service_is_ready():
                                pending[name] = client.call_async(GetState.Request())
                        rclpy.spin_once(node, timeout_sec=0.02)
                        time.sleep(0.02)
                    log.flush()
                    log.seek(0)
                    details = log.read()
                    self.assertEqual(active, set(names), details[-20000:])
                finally:
                    os.killpg(process.pid, signal.SIGINT)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                    node.destroy_node()
                    rclpy.shutdown()


if __name__ == '__main__':
    unittest.main()
