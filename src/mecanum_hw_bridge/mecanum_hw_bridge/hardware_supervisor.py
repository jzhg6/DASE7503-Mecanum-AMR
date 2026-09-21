#!/usr/bin/env python3
"""Host-side safety, actuator and odometry adapter for the micro-ROS base."""

from __future__ import annotations

import math
import threading
import time

import rclpy
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import Bool, Int32
from std_srvs.srv import Trigger
from tf2_ros import TransformBroadcaster


class HardwareSupervisor(Node):
    """Convert MCU topics to stable robot interfaces and require acknowledgements."""

    def __init__(self) -> None:
        super().__init__("hardware_supervisor")
        self.declare_parameter("command_ack_timeout_sec", 4.0)
        self.declare_parameter("wheel_odom_topic", "/wheel/odom")
        self.declare_parameter("odom_topic", "/odom")
        self.declare_parameter("odom_frame", "odom")
        self.declare_parameter("base_frame", "base_footprint")
        self.declare_parameter("publish_odom_tf", True)

        self._ack_timeout = float(
            self.get_parameter("command_ack_timeout_sec").value
        )
        if not math.isfinite(self._ack_timeout) or self._ack_timeout <= 0.0:
            raise ValueError("command_ack_timeout_sec must be finite and positive")

        self._odom_frame = str(self.get_parameter("odom_frame").value)
        self._base_frame = str(self.get_parameter("base_frame").value)
        self._publish_tf = bool(self.get_parameter("publish_odom_tf").value)
        self._condition = threading.Condition()
        self._base_enabled: bool | None = None
        self._lift_state: int | None = None
        self._base_sequence = 0
        self._lift_sequence = 0
        self._base_seen = float('-inf')
        self._odom_seen = float('-inf')
        self._stationary_since = None
        self._stop_generation = 0
        self._operation_lock = threading.Lock()
        self._callbacks = ReentrantCallbackGroup()

        self._enable_pub = self.create_publisher(Bool, "/base/enable", 10)
        self._lift_pub = self.create_publisher(Int32, "/lift/command", 10)
        self._odom_pub = self.create_publisher(
            Odometry, str(self.get_parameter("odom_topic").value), 20
        )
        self._tf = TransformBroadcaster(self)

        self.create_subscription(
            Bool,
            "/base/enabled",
            self._enabled_callback,
            10,
            callback_group=self._callbacks,
        )
        self.create_subscription(
            Int32,
            "/lift/state",
            self._lift_state_callback,
            10,
            callback_group=self._callbacks,
        )
        self.create_subscription(
            Odometry,
            str(self.get_parameter("wheel_odom_topic").value),
            self._odom_callback,
            20,
            callback_group=self._callbacks,
        )

        self.create_service(
            Trigger,
            "safety/enable",
            self._enable_service,
            callback_group=self._callbacks,
        )
        self.create_service(
            Trigger,
            "safety/stop",
            self._stop_service,
            callback_group=self._callbacks,
        )
        self.create_service(
            Trigger,
            "lift/up",
            self._lift_up_service,
            callback_group=self._callbacks,
        )
        self.create_service(
            Trigger,
            "lift/down",
            self._lift_down_service,
            callback_group=self._callbacks,
        )

        self._publish_enable(False)
        self.get_logger().info(
            "micro-ROS hardware supervisor started; motors requested OFF"
        )

    def _enabled_callback(self, message: Bool) -> None:
        with self._condition:
            self._base_enabled = bool(message.data)
            self._base_sequence += 1
            self._base_seen = time.monotonic()
            self._condition.notify_all()

    def _lift_state_callback(self, message: Int32) -> None:
        if message.data not in (-1, 0, 1):
            self.get_logger().warning(f"ignored invalid lift state: {message.data}")
            return
        with self._condition:
            self._lift_state = int(message.data)
            self._lift_sequence += 1
            self._condition.notify_all()

    @staticmethod
    def _odom_is_finite(message: Odometry) -> bool:
        values = (
            message.pose.pose.position.x,
            message.pose.pose.position.y,
            message.pose.pose.position.z,
            message.pose.pose.orientation.x,
            message.pose.pose.orientation.y,
            message.pose.pose.orientation.z,
            message.pose.pose.orientation.w,
            message.twist.twist.linear.x,
            message.twist.twist.linear.y,
            message.twist.twist.angular.z,
        )
        return all(math.isfinite(value) for value in values)

    def _odom_callback(self, message: Odometry) -> None:
        if not self._odom_is_finite(message):
            self.get_logger().error("rejected non-finite wheel odometry")
            return
        quaternion = message.pose.pose.orientation
        norm = math.sqrt(
            quaternion.x**2
            + quaternion.y**2
            + quaternion.z**2
            + quaternion.w**2
        )
        if norm < 0.5 or norm > 1.5:
            self.get_logger().error("rejected wheel odometry with invalid quaternion")
            return

        with self._condition:
            now = time.monotonic()
            velocity = message.twist.twist
            stationary = (abs(velocity.linear.x) < 0.01 and abs(velocity.linear.y) < 0.01
                          and abs(velocity.angular.z) < 0.03)
            if not stationary or now - self._odom_seen > 0.5:
                self._stationary_since = None
            if stationary and self._stationary_since is None:
                self._stationary_since = now
            self._odom_seen = now
            self._condition.notify_all()

        message.header.frame_id = self._odom_frame
        message.child_frame_id = self._base_frame
        self._odom_pub.publish(message)
        if not self._publish_tf:
            return
        transform = TransformStamped()
        transform.header = message.header
        transform.child_frame_id = self._base_frame
        transform.transform.translation.x = message.pose.pose.position.x
        transform.transform.translation.y = message.pose.pose.position.y
        transform.transform.translation.z = message.pose.pose.position.z
        transform.transform.rotation = message.pose.pose.orientation
        self._tf.sendTransform(transform)

    def _publish_enable(self, enabled: bool) -> None:
        message = Bool()
        message.data = enabled
        self._enable_pub.publish(message)

    def _request_enable(self, requested: bool) -> tuple[bool, str]:
        deadline = time.monotonic() + self._ack_timeout
        sequence = self._base_sequence
        generation = self._stop_generation
        while rclpy.ok() and time.monotonic() < deadline:
            if requested and generation != self._stop_generation:
                return False, "enable preempted by stop"
            self._publish_enable(requested)
            with self._condition:
                if self._base_enabled is requested and self._base_sequence > sequence:
                    state = "enabled" if requested else "disabled"
                    return True, f"base firmware acknowledged {state}"
                self._condition.wait(timeout=0.1)
        return False, "no matching /base/enabled acknowledgement"

    def _request_lift(self, requested: int) -> tuple[bool, str]:
        deadline = time.monotonic() + self._ack_timeout
        sequence = self._lift_sequence
        generation = self._stop_generation
        while rclpy.ok() and time.monotonic() < deadline:
            now = time.monotonic()
            if (generation != self._stop_generation or not self._base_enabled
                    or now - self._base_seen > 0.5):
                return False, "lift requires fresh enabled base; stop preempts lift"
            if (now - self._odom_seen > 0.5 or self._stationary_since is None
                    or now - self._stationary_since < 0.3):
                with self._condition:
                    self._condition.wait(timeout=0.05)
                continue
            message = Int32()
            message.data = requested
            self._lift_pub.publish(message)
            with self._condition:
                if self._lift_state == requested and self._lift_sequence > sequence:
                    label = "raised" if requested else "lowered"
                    return True, (
                        f"lift command acknowledged as {label}; "
                        "this is open-loop servo status, not load feedback"
                    )
                self._condition.wait(timeout=0.1)
        return False, "no matching /lift/state acknowledgement"

    def _enable_service(self, _request, response):
        if not self._operation_lock.acquire(blocking=False):
            response.success, response.message = False, "another actuator request is active"
            return response
        try:
            response.success, response.message = self._request_enable(True)
        finally:
            self._operation_lock.release()
        return response

    def _stop_service(self, _request, response):
        self._stop_generation += 1
        response.success, response.message = self._request_enable(False)
        return response

    def _lift_up_service(self, _request, response):
        return self._lift_service(1, response)

    def _lift_down_service(self, _request, response):
        return self._lift_service(0, response)

    def _lift_service(self, requested, response):
        if not self._operation_lock.acquire(blocking=False):
            response.success, response.message = False, "another actuator request is active"
            return response
        try:
            response.success, response.message = self._request_lift(requested)
        finally:
            self._operation_lock.release()
        return response

    def destroy_node(self):
        self._publish_enable(False)
        time.sleep(0.05)
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = HardwareSupervisor()
    executor = MultiThreadedExecutor(num_threads=3)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
