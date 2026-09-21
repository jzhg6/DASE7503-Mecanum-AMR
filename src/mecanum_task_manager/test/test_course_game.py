#!/usr/bin/env python3
"""Tests exercise official samples, negative inputs and complete game sequences."""
import copy
from pathlib import Path
import sys
import unittest
import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'mecanum_task_manager'))
from course_game import CourseGame, RACKS, parse_course_qr, validate_config

SAMPLES = {'RACKA': 'RACKA_4X6M', 'RACKB': 'RACKB_AM9L',
           'RACKC': 'RACKC_K8Y3', 'RACKD': 'RACKD_R983'}


class CourseTests(unittest.TestCase):
    def setUp(self):
        self.config = yaml.safe_load((Path(__file__).resolve().parents[1] / 'config/course.yaml').read_text())
        self.config['rack_codes'] = SAMPLES
        self.game = CourseGame(self.config)

    def test_official_samples(self):
        for code in ['START', *SAMPLES.values(), 'END']:
            self.assertEqual(parse_course_qr(code)[0], code.split('_')[0])

    def test_bad_payloads(self):
        for code in ['start', ' START', 'RACKA_123', 'RACKA_12345', 'RACKE_1234',
                     'RACKA_../x', 'RACKA_中文中文', 'END\n', '{"pickup":"A"}']:
            with self.subTest(code=code), self.assertRaises(ValueError):
                parse_course_qr(code)

    def test_only_start_starts(self):
        for code in SAMPLES.values():
            self.assertFalse(self.game.qr(code, 0))
        self.assertEqual(self.game.state, 'IDLE')
        self.assertTrue(self.game.qr('START', 10))
        self.assertEqual(self.game.started, 10)
        self.assertFalse(self.game.qr('START', 50))
        self.assertEqual(self.game.started, 10)

    def test_qr_at_expected_station_only(self):
        self.game.qr('START', 0)
        rack = self.config['rack_order'][0]
        self.assertFalse(self.game.qr(SAMPLES[rack], 1))
        self.game.complete(self.game.token, 2)
        self.assertEqual(self.game.state, 'SCAN')
        self.assertFalse(self.game.qr(rack + '_ZZZZ', 3))
        self.assertFalse(self.game.qr('END', 3))
        self.assertTrue(self.game.qr(SAMPLES[rack], 4))
        self.assertEqual(self.game.step.target, rack + '_DOCK')

    def test_four_deliveries_with_unique_slots_and_no_return_home(self):
        self.game.qr('START', 0)
        steps = []
        for now in range(1, 80):
            if not self.game.active:
                break
            steps.append(self.game.step)
            if self.game.state == 'SCAN':
                code = SAMPLES.get(self.game.step.target, 'END')
                self.assertTrue(self.game.qr(code, now))
            else:
                self.game.complete(self.game.token, now)
        self.assertEqual(self.game.state, 'DONE')
        self.assertEqual(self.game.delivered, self.config['rack_order'])
        self.assertEqual([s.target for s in steps if s.kind == 'LIFT'], ['up', 'down'] * 4)
        self.assertEqual(len([s for s in steps if s.kind == 'SCAN' and s.target == 'END']), 4)
        self.assertEqual({s.target for s in steps if s.target.startswith('DROP') and s.target.endswith('POSE')},
                         {f'DROP{i}_POSE' for i in range(1, 5)})
        self.assertFalse(any(s.target in ('START', 'HOME') for s in steps))

    def test_timeout_exact_boundary_and_stale_completion(self):
        self.game.qr('START', 100)
        token = self.game.token
        self.game.tick(279.999)
        self.assertTrue(self.game.active)
        self.game.complete(token, 280)
        self.assertEqual(self.game.state, 'TIMEOUT')
        self.game.complete(token, 281)
        self.assertEqual(self.game.state, 'TIMEOUT')
        self.assertEqual(self.game.delivered, [])

    def test_failure_cannot_continue(self):
        self.game.qr('START', 0)
        token = self.game.token
        self.game.complete(token, 1, False, 'blocked route')
        self.game.qr('START', 2)
        self.game.complete(token, 3)
        self.assertEqual(self.game.state, 'ERROR')
        self.assertEqual(self.game.reason, 'blocked route')

    def test_old_token_does_not_complete_new_step(self):
        self.game.qr('START', 0)
        token = self.game.token
        self.game.complete(token, 1)
        self.game.complete(token, 2)
        self.assertEqual(self.game.state, 'SCAN')

    def test_real_calibration_gate(self):
        with self.assertRaises(ValueError):
            validate_config(self.config, real=True)
        self.config['calibrated'] = True
        self.config['measured_robot_size_m'] = [0.28, 0.26, 0.17]
        validate_config(self.config, real=True)
        self.config['measured_robot_size_m'][2] = 0.181
        with self.assertRaises(ValueError):
            validate_config(self.config, real=True)

    def test_missing_codes_and_nonfinite_pose(self):
        self.config['calibrated'] = True
        self.config['rack_codes'] = {}
        with self.assertRaises(ValueError):
            validate_config(self.config, real=True)
        self.config['stations']['START']['x'] = float('nan')
        with self.assertRaises(ValueError):
            validate_config(self.config)


if __name__ == '__main__':
    unittest.main()
