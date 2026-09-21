"""Synthetic camera images exercise real OpenCV decode and evidence persistence."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import cv2
import rclpy
from rclpy.parameter import Parameter
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mecanum_task_manager'))
from qr_reader import QRReader


class CameraQRTest(unittest.TestCase):
    def test_six_teacher_payloads_from_pixels(self):
        codes = ['START', 'RACKA_4X6M', 'RACKB_AM9L', 'RACKC_K8Y3', 'RACKD_R983', 'END']
        rclpy.init()
        with tempfile.TemporaryDirectory(prefix='synthetic-camera-') as output:
            reader = QRReader(parameter_overrides=[Parameter('evidence_dir', value=output),
                Parameter('sample_every_n_frames', value=1)])
            try:
                encoder = cv2.QRCodeEncoder_create()
                for code in codes:
                    pixels = encoder.encode(code)
                    pixels = cv2.copyMakeBorder(pixels, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=255)
                    pixels = cv2.resize(pixels, None, fx=10, fy=10, interpolation=cv2.INTER_NEAREST)
                    frame = cv2.cvtColor(pixels, cv2.COLOR_GRAY2BGR)
                    reader.image_callback(reader.bridge.cv2_to_imgmsg(frame, encoding='bgr8'))
                logs = list(Path(output).glob('qr-*.jsonl'))
                decoded = [json.loads(line)['decoded'] for line in logs[0].read_text().splitlines()]
                self.assertEqual(decoded, codes)
                self.assertEqual(len(list(Path(output).glob('*.png'))), 6)
            finally:
                reader.destroy_node()
                rclpy.shutdown()


if __name__ == '__main__':
    unittest.main()
