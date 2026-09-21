"""Actual ROS graph test with mock navigation/actuators (not a physics test)."""
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

import rclpy
from rclpy.action import ActionServer
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import String
from std_srvs.srv import Trigger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mecanum_task_manager'))
from course_mission_node import CourseMissionNode


class RosCourseTest(unittest.TestCase):
    def test_complete_graph_and_abort(self):
        rclpy.init()
        with tempfile.TemporaryDirectory(prefix='course-ros-') as evidence:
            course = str(Path(__file__).resolve().parents[1] / 'config/course.yaml')
            mission = CourseMissionNode(parameter_overrides=[
                Parameter('use_sim_time', value=True),
                Parameter('course_yaml', value=course),
                Parameter('evidence_dir', value=evidence)])
            mock = Node('course_test_hardware')
            calls = []
            def navigate(handle):
                calls.append('nav')
                handle.succeed()
                return NavigateToPose.Result()
            server = ActionServer(mock, NavigateToPose, 'navigate_to_pose', navigate)
            def actuator(label):
                def callback(request, response):
                    calls.append(label)
                    response.success = True
                    return response
                return callback
            services = [mock.create_service(Trigger, name, actuator(label)) for name, label in
                        [('lift/up', 'up'), ('lift/down', 'down'), ('safety/stop', 'stop')]]
            qr = mock.create_publisher(String, '/qr/data', 10)
            executor = SingleThreadedExecutor()
            executor.add_node(mock)
            executor.add_node(mission)
            try:
                deadline = time.monotonic() + 40
                while time.monotonic() < deadline and mission.game.state != 'DONE':
                    executor.spin_once(timeout_sec=0.01)
                    if not mission._nav.server_is_ready():
                        continue
                    if mission.game.state == 'IDLE':
                        qr.publish(String(data='START'))
                    elif mission.game.state == 'SCAN':
                        target = mission.game.step.target
                        qr.publish(String(data=target if target == 'END' else target + '_1234'))
                self.assertEqual(mission.game.state, 'DONE', mission.game.reason)
                self.assertEqual(calls.count('up'), 4)
                self.assertEqual(calls.count('down'), 4)
                self.assertEqual(len(mission.game.delivered), 4)
                self.assertEqual(calls.count('nav'), 24)
                end = time.monotonic() + 2
                while 'stop' not in calls and time.monotonic() < end:
                    executor.spin_once(timeout_sec=0.05)
                self.assertIn('stop', calls)
                self.assertTrue(list(Path(evidence).glob('game-*.jsonl')))
            finally:
                mission.destroy_node()
                server.destroy()
                mock.destroy_node()
                executor.shutdown()
                rclpy.shutdown()


if __name__ == '__main__':
    unittest.main()
