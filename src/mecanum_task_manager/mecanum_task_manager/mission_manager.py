#!/usr/bin/env python3
# Copyright (c) 2026 DASE7503 project contributors
# SPDX-License-Identifier: MIT
"""Event-driven QR transport mission coordinator for Nav2 and the lift servo."""

from __future__ import annotations

import math
import os
import time
from typing import Callable, Optional

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node
from std_msgs.msg import Bool, String
from std_srvs.srv import Trigger
import yaml

from qr_payload import TransportMission, parse_transport_mission
from state_machine import RobotState, StateMachine


class MissionManager(Node):
    """Runs one whitelisted pickup/drop-off mission at a time."""

    def __init__(self) -> None:
        super().__init__("mission_manager")
        self.declare_parameter("stations_yaml", os.path.expanduser("~/stations.yaml"))
        self.declare_parameter("home_station", "HOME")
        self.declare_parameter("map_frame", "map")
        self.declare_parameter("allow_mock_lift", False)
        self.declare_parameter("allow_pose_only_docking", False)
        self.declare_parameter("require_base_enabled", True)
        self.declare_parameter("operation_timeout_sec", 120.0)

        self._stations = self._load_stations(
            str(self.get_parameter("stations_yaml").value)
        )
        self._home_station = str(self.get_parameter("home_station").value)
        self._map_frame = str(self.get_parameter("map_frame").value)
        self._machine = StateMachine()
        self._active: Optional[TransportMission] = None
        self._completed_ids: set[str] = set()
        self._generation = 0
        self._goal_handle = None
        self._deadline = 0.0
        self._base_enabled = False
        self._timeout = float(self.get_parameter("operation_timeout_sec").value)
        if not math.isfinite(self._timeout) or self._timeout <= 0:
            raise ValueError("operation_timeout_sec must be finite and positive")

        self._nav = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self._lift_up = self.create_client(Trigger, "lift/up")
        self._lift_down = self.create_client(Trigger, "lift/down")
        self._safety_stop = self.create_client(Trigger, "safety/stop")

        self.create_subscription(String, "/qr/data", self._qr_callback, 10)
        self.create_subscription(Bool, "/base/enabled", self._base_callback, 10)
        self._state_pub = self.create_publisher(String, "/robot_state", 10)
        self._status_pub = self.create_publisher(String, "/mission/status", 10)
        self.create_service(Trigger, "mission/reset", self._reset_callback)
        self.create_timer(0.5, self._publish_state)
        self.create_timer(0.1, self._check_timeout)
        self.get_logger().info(
            f"Mission manager ready with {len(self._stations)} stations"
        )

    def _load_stations(self, path: str) -> dict[str, dict[str, float]]:
        if not os.path.exists(path):
            raise RuntimeError(f"stations file not found: {path}")
        with open(path, "r", encoding="utf-8") as stream:
            document = yaml.safe_load(stream) or {}
        stations = document.get("stations", {})
        if not isinstance(stations, dict) or not stations:
            raise RuntimeError("stations YAML must contain a non-empty 'stations' map")
        for name, pose in stations.items():
            if not isinstance(pose, dict) or "x" not in pose or "y" not in pose:
                raise RuntimeError(f"station {name!r} needs x and y")
            if not all(math.isfinite(float(pose.get(key, 0.0)))
                       for key in ("x", "y", "yaw")):
                raise RuntimeError(f"station {name!r} has non-finite coordinates")
        return stations

    def _base_callback(self, message: Bool) -> None:
        was_enabled = self._base_enabled
        self._base_enabled = bool(message.data)
        if was_enabled and not self._base_enabled and self._active is not None:
            self._fail("base controller disarmed during mission")

    def _qr_callback(self, message: String) -> None:
        simulation_ready = bool(
            self.get_parameter("use_sim_time").value
            and self.get_parameter("allow_mock_lift").value
        )
        real_ready = bool(
            not self.get_parameter("use_sim_time").value
            and self.get_parameter("allow_pose_only_docking").value
            and (
                self._base_enabled
                or not self.get_parameter("require_base_enabled").value
            )
        )
        if not (simulation_ready or real_ready):
            self.get_logger().warning(
                "mission rejected: enable the base and explicitly allow "
                "pose-only docking after physical calibration"
            )
            return
        if self._machine.state != RobotState.IDLE:
            self.get_logger().warning("QR ignored while a mission is active")
            return
        try:
            mission = parse_transport_mission(message.data)
        except ValueError as exc:
            self.get_logger().warning(f"QR rejected: {exc}")
            return
        if mission.mission_id in self._completed_ids:
            self.get_logger().info(f"Mission already completed: {mission.mission_id}")
            return
        unknown = [
            station
            for station in (mission.pickup, mission.dropoff, self._home_station)
            if station not in self._stations
        ]
        if unknown:
            self.get_logger().error("Unknown station(s): " + ", ".join(unknown))
            return

        self._active = mission
        self._generation += 1
        self._transition(RobotState.READING_QR)
        self._transition(RobotState.NAVIGATING_TO_LOAD)
        self._publish_status(f"{mission.mission_id}: navigating to {mission.pickup}")
        self._navigate(mission.pickup, self._at_pickup)

    def _navigate(self, station: str, on_arrival: Callable[[], None]) -> None:
        self._deadline = time.monotonic() + self._timeout
        if not self._nav.wait_for_server(timeout_sec=1.0):
            self._fail("Nav2 action server unavailable")
            return
        goal = NavigateToPose.Goal()
        goal.pose = self._station_pose(station)
        future = self._nav.send_goal_async(goal)
        generation = self._generation
        future.add_done_callback(
            lambda completed: self._goal_response(completed, on_arrival, generation)
        )

    def _goal_response(self, future, on_arrival: Callable[[], None], generation) -> None:
        try:
            handle = future.result()
        except Exception as exc:
            self._fail(f"navigation request failed: {exc}")
            return
        if handle is None or not handle.accepted:
            if generation != self._generation:
                return
            self._fail("navigation goal rejected")
            return
        if generation != self._generation:
            handle.cancel_goal_async()
            return
        self._goal_handle = handle
        result_future = handle.get_result_async()
        result_future.add_done_callback(
            lambda completed: self._goal_result(completed, on_arrival, generation)
        )

    def _goal_result(self, future, on_arrival: Callable[[], None], generation) -> None:
        if generation != self._generation:
            return
        self._goal_handle = None
        try:
            result = future.result()
        except Exception as exc:
            self._fail(f"navigation result failed: {exc}")
            return
        if result.status != GoalStatus.STATUS_SUCCEEDED:
            self._fail(f"navigation ended with status {result.status}")
            return
        on_arrival()

    def _at_pickup(self) -> None:
        self._transition(RobotState.ALIGNING)
        # Fine alignment can be inserted here after the mechanical geometry is known.
        self._transition(RobotState.LIFTING)
        self._publish_status("pickup reached; lifting")
        self._call_trigger(self._lift_up, self._after_lift_up)

    def _after_lift_up(self) -> None:
        assert self._active is not None
        self._transition(RobotState.NAVIGATING_TO_DROP)
        self._publish_status(f"navigating to {self._active.dropoff}")
        self._navigate(self._active.dropoff, self._at_dropoff)

    def _at_dropoff(self) -> None:
        self._transition(RobotState.LOWERING)
        self._publish_status("drop-off reached; lowering")
        self._call_trigger(self._lift_down, self._after_lift_down)

    def _after_lift_down(self) -> None:
        self._transition(RobotState.RETURNING_HOME)
        self._publish_status(f"returning to {self._home_station}")
        self._navigate(self._home_station, self._finish)

    def _finish(self) -> None:
        assert self._active is not None
        mission_id = self._active.mission_id
        self._completed_ids.add(mission_id)
        self._transition(RobotState.IDLE)
        self._publish_status(f"{mission_id}: completed")
        self._active = None

    def _call_trigger(
        self, client, on_success: Callable[[], None]
    ) -> None:
        self._deadline = time.monotonic() + self._timeout
        if not client.wait_for_service(timeout_sec=1.0):
            self._fail(f"service unavailable: {client.srv_name}")
            return
        future = client.call_async(Trigger.Request())
        generation = self._generation
        future.add_done_callback(
            lambda completed: self._trigger_result(completed, on_success, generation)
        )

    def _trigger_result(self, future, on_success: Callable[[], None], generation) -> None:
        if generation != self._generation:
            return
        try:
            response = future.result()
        except Exception as exc:
            self._fail(f"actuator service failed: {exc}")
            return
        if response is None or not response.success:
            reason = response.message if response is not None else "no response"
            self._fail(f"actuator rejected command: {reason}")
            return
        on_success()

    def _station_pose(self, station: str) -> PoseStamped:
        source = self._stations[station]
        yaw = float(source.get("yaw", 0.0))
        pose = PoseStamped()
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.header.frame_id = self._map_frame
        pose.pose.position.x = float(source["x"])
        pose.pose.position.y = float(source["y"])
        pose.pose.orientation.z = math.sin(yaw / 2.0)
        pose.pose.orientation.w = math.cos(yaw / 2.0)
        return pose

    def _transition(self, target: RobotState) -> None:
        if not self._machine.transition(target):
            raise RuntimeError(
                f"invalid state transition: {self._machine.state.name} -> {target.name}"
            )
        self._publish_state()

    def _fail(self, reason: str) -> None:
        self._generation += 1
        self._deadline = 0.0
        if self._goal_handle is not None:
            self._goal_handle.cancel_goal_async()
            self._goal_handle = None
        self.get_logger().error(reason)
        if self._machine.can_transition(RobotState.ERROR):
            self._transition(RobotState.ERROR)
        self._publish_status("ERROR: " + reason)
        if self._safety_stop.service_is_ready():
            self._safety_stop.call_async(Trigger.Request())

    def _check_timeout(self) -> None:
        if (self._machine.state not in (RobotState.IDLE, RobotState.ERROR)
                and self._deadline and time.monotonic() > self._deadline):
            self._fail("operation timed out; operator reset required")

    def destroy_node(self):
        self._generation += 1
        if self._goal_handle is not None:
            self._goal_handle.cancel_goal_async()
        if self._safety_stop.service_is_ready():
            self._safety_stop.call_async(Trigger.Request())
        return super().destroy_node()

    def _reset_callback(
        self, request: Trigger.Request, response: Trigger.Response
    ) -> Trigger.Response:
        if self._machine.state != RobotState.ERROR:
            response.success = False
            response.message = "reset is only valid in ERROR"
            return response
        self._active = None
        self._transition(RobotState.IDLE)
        response.success = True
        response.message = "mission state reset; motors remain disabled"
        return response

    def _publish_state(self) -> None:
        message = String()
        message.data = self._machine.state.name
        self._state_pub.publish(message)

    def _publish_status(self, text: str) -> None:
        message = String()
        message.data = text
        self._status_pub.publish(message)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MissionManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
