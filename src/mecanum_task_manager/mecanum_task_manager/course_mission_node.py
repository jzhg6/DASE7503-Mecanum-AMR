#!/usr/bin/env python3
# Copyright (c) 2026 DASE7503 project contributors
# SPDX-License-Identifier: MIT
"""ROS adapter for the course game, with camera START and fresh base feedback."""
import json
import math
from pathlib import Path
import time
import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, Twist
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import Bool, String
from std_srvs.srv import Trigger
import yaml
from course_game import CourseGame, validate_config


class CourseMissionNode(Node):
    def __init__(self):
        super().__init__('course_mission')
        for name, default in [('course_yaml', ''), ('evidence_dir', 'evidence'),
                              ('operation_timeout_sec', 30.0),
                              ('base_state_timeout_sec', 1.0), ('map_frame', 'map')]:
            self.declare_parameter(name, default)
        with open(self.get_parameter('course_yaml').value, encoding='utf-8') as stream:
            config = yaml.safe_load(stream)
        self._real = not self.get_parameter('use_sim_time').value
        self.config = validate_config(config, real=self._real)
        self.game = CourseGame(self.config)
        self._timeout = float(self.get_parameter('operation_timeout_sec').value)
        self._heartbeat = float(self.get_parameter('base_state_timeout_sec').value)
        if not all(math.isfinite(v) and v > 0 for v in (self._timeout, self._heartbeat)):
            raise ValueError('timeouts must be finite and positive')
        self._enabled, self._base_seen = False, float('-inf')
        self._dispatched, self._deadline, self._goal = -1, 0.0, None
        self._stop_requested = False
        self._nav = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self._up = self.create_client(Trigger, 'lift/up')
        self._down = self.create_client(Trigger, 'lift/down')
        self._stop = self.create_client(Trigger, 'safety/stop')
        self._velocity = self.create_publisher(Twist, '/cmd_vel', 10)
        self._status = self.create_publisher(String, '/mission/status', 10)
        self._state = self.create_publisher(String, '/robot_state', 10)
        self.create_subscription(Bool, '/base/enabled', self._base, 10)
        self.create_subscription(String, '/qr/data', self._qr, 10)
        self.create_service(Trigger, 'mission/reset', self._reset)
        self.create_service(Trigger, 'mission/abort', self._abort)
        evidence = Path(self.get_parameter('evidence_dir').value)
        evidence.mkdir(parents=True, exist_ok=True)
        self._log = (evidence / f'game-{time.time_ns()}.jsonl').open('x', encoding='utf-8')
        self.create_timer(0.05, self._tick)
        self.create_timer(0.5, self._publish)
        self._publish()

    def _base(self, msg):
        self._enabled, self._base_seen = bool(msg.data), time.monotonic()

    def _ready(self):
        return not self._real or (self._enabled and time.monotonic()-self._base_seen < self._heartbeat)

    def _qr(self, msg):
        if self.game.state == 'IDLE' and not self._ready():
            return
        self.game.qr(msg.data, time.monotonic())
        self._tick()

    def _tick(self):
        now = time.monotonic()
        self.game.tick(now)
        if self.game.active and not self._ready():
            self.game.stop('ERROR', 'base disabled or heartbeat lost')
        if self.game.active and self._dispatched == self.game.token and now >= self._deadline:
            self.game.stop('ERROR', 'navigation, QR or lift operation timed out')
        if self._dispatched == self.game.token:
            if self.game.state in ('DONE', 'ERROR', 'TIMEOUT'):
                self._request_stop()
            return
        self._dispatched = self.game.token
        self._deadline = now + self._timeout
        self._publish()
        step = self.game.step
        if step is None:
            return
        if step.kind == 'STOP':
            self._request_stop()
        elif step.kind == 'NAV':
            self._navigate(step.target, self.game.token)
        elif step.kind == 'LIFT':
            self._velocity.publish(Twist())
            client = self._up if step.target == 'up' else self._down
            if not client.service_is_ready():
                self._complete(self.game.token, False, 'lift service unavailable')
            else:
                token = self.game.token
                client.call_async(Trigger.Request()).add_done_callback(lambda f: self._lift_result(f, token))
        elif step.kind == 'SCAN':
            self._velocity.publish(Twist())

    def _navigate(self, station, token):
        if not self._nav.server_is_ready():
            self._complete(token, False, 'Nav2 server unavailable')
            return
        source = self.config['stations'][station]
        pose = PoseStamped()
        pose.header.frame_id = self.get_parameter('map_frame').value
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x, pose.pose.position.y = float(source['x']), float(source['y'])
        pose.pose.orientation.z = math.sin(float(source['yaw'])/2)
        pose.pose.orientation.w = math.cos(float(source['yaw'])/2)
        goal = NavigateToPose.Goal()
        goal.pose = pose
        self._nav.send_goal_async(goal).add_done_callback(lambda f: self._accepted(f, token))

    def _accepted(self, future, token):
        try:
            goal = future.result()
        except Exception as exc:
            self._complete(token, False, str(exc))
            return
        if token != self.game.token or not self.game.active:
            if goal and goal.accepted:
                goal.cancel_goal_async()
            return
        if goal is None or not goal.accepted:
            self._complete(token, False, 'Nav2 goal rejected')
            return
        self._goal = goal
        goal.get_result_async().add_done_callback(lambda f: self._arrived(f, token))

    def _arrived(self, future, token):
        if token != self.game.token:
            return
        self._goal = None
        try:
            success = future.result().status == GoalStatus.STATUS_SUCCEEDED
            self._complete(token, success, 'Nav2 navigation failed')
        except Exception as exc:
            self._complete(token, False, str(exc))

    def _lift_result(self, future, token):
        try:
            result = future.result()
            self._complete(token, result is not None and result.success,
                           result.message if result else 'no lift response')
        except Exception as exc:
            self._complete(token, False, str(exc))

    def _complete(self, token, success, reason):
        self.game.complete(token, time.monotonic(), success, reason)

    def _request_stop(self):
        self._velocity.publish(Twist())
        if self._goal:
            self._goal.cancel_goal_async()
            self._goal = None
        if not self._stop_requested and self._stop.service_is_ready():
            self._stop_requested = True
            self._stop.call_async(Trigger.Request()).add_done_callback(self._stopped)

    def _stopped(self, future):
        try:
            self._stop_requested = bool(future.result().success)
        except Exception:
            self._stop_requested = False

    def _abort(self, request, response):
        self.game.stop('ERROR', 'operator abort')
        self._request_stop()
        response.success, response.message = True, 'stop requested; lift position retained'
        return response

    def _reset(self, request, response):
        if self.game.active or (self._real and (self._enabled or time.monotonic()-self._base_seen > self._heartbeat)):
            response.success, response.message = False, 'abort and verify fresh disabled base first'
            return response
        token = self.game.token + 1
        self.game = CourseGame(self.config)
        self.game.token = token
        self._stop_requested = False
        response.success, response.message = True, 'reset; position robot, enable base, scan START'
        return response

    def _publish(self):
        data = self.game.status(time.monotonic())
        data['wall_time_ns'] = time.time_ns()
        message = String(data=json.dumps(data, ensure_ascii=False))
        self._status.publish(message)
        self._state.publish(String(data=self.game.state))
        self._log.write(message.data + '\n')
        self._log.flush()

    def destroy_node(self):
        self._request_stop()
        self._log.close()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = CourseMissionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
