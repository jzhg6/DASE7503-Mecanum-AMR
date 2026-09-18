#!/usr/bin/env python3
# Copyright (c) 2025 Tarik Kahraman
# SPDX-License-Identifier: MIT
"""Read task QR codes from a ROS image stream without trusting coordinates."""

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge
import cv2
import time


class QRReader(Node):

    def __init__(self):
        super().__init__('qr_reader')

        self.declare_parameter('image_topic', '/camera/image_raw')
        self.declare_parameter('qr_data_topic', '/qr/data')
        self.declare_parameter('dedupe_seconds', 2.0)
        self.declare_parameter('max_payload_bytes', 512)
        self.declare_parameter('sample_every_n_frames', 2)

        self.bridge = CvBridge()
        self.detector = cv2.QRCodeDetector()
        self.last_seen: dict[str, float] = {}
        self.dedupe_seconds = float(self.get_parameter('dedupe_seconds').value)
        self.max_payload_bytes = int(self.get_parameter('max_payload_bytes').value)
        self.sample_every_n_frames = int(
            self.get_parameter('sample_every_n_frames').value
        )
        if self.dedupe_seconds < 0.0:
            raise ValueError('dedupe_seconds must not be negative')
        if self.max_payload_bytes < 1 or self.sample_every_n_frames < 1:
            raise ValueError('payload and frame limits must be positive')
        self.frame_count = 0

        self.image_sub = self.create_subscription(
            Image, str(self.get_parameter('image_topic').value), self.image_callback,
            qos_profile_sensor_data
        )

        self.qr_pub = self.create_publisher(
            String, str(self.get_parameter('qr_data_topic').value), 10
        )
        self.get_logger().info('QR Reader started, waiting for camera...')

    # ------------------------------------------------------------------ #

    def image_callback(self, msg: Image):
        self.frame_count += 1
        if self.frame_count % self.sample_every_n_frames:
            return
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'Image conversion error: {e}')
            return

        try:
            found, decoded, _, _ = self.detector.detectAndDecodeMulti(frame)
            payloads = decoded if found else ()
        except cv2.error:
            data, _, _ = self.detector.detectAndDecode(frame)
            payloads = (data,) if data else ()

        now = time.monotonic()
        for data in payloads:
            if not data or len(data.encode('utf-8')) > self.max_payload_bytes:
                continue
            if any(ord(character) < 32 for character in data):
                self.get_logger().warning('QR payload contains control characters')
                continue
            last_time = self.last_seen.get(data, float('-inf'))
            if now - last_time < self.dedupe_seconds:
                continue
            self.last_seen[data] = now
            self.last_seen = {
                value: seen_at
                for value, seen_at in self.last_seen.items()
                if now - seen_at < max(60.0, self.dedupe_seconds)
            }
            str_msg = String()
            str_msg.data = data
            self.qr_pub.publish(str_msg)
            self.get_logger().info('published a bounded QR mission payload')


def main(args=None):
    rclpy.init(args=args)
    node = QRReader()
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
