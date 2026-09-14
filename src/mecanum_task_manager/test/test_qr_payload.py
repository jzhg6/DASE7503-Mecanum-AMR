#!/usr/bin/env python3
"""Unit tests for the transport-mission QR schema."""

import os
import sys


TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_ROOT = os.path.dirname(TEST_DIR)
if PACKAGE_ROOT not in sys.path:
    sys.path.insert(0, PACKAGE_ROOT)

from mecanum_task_manager.qr_payload import parse_transport_mission


def test_json_payload():
    mission = parse_transport_mission(
        '{"mission_id":"M001","pickup":"RACK_A",'
        '"dropoff":"RACK_B","item":"BOX_01"}'
    )
    assert mission.mission_id == "M001"
    assert mission.pickup == "RACK_A"
    assert mission.dropoff == "RACK_B"
    assert mission.item == "BOX_01"


def test_key_value_payload_and_aliases():
    mission = parse_transport_mission("id:M002;from:RACK_C;to:RACK_D")
    assert mission.mission_id == "M002"
    assert mission.pickup == "RACK_C"
    assert mission.dropoff == "RACK_D"


def test_rejects_missing_and_unsafe_tokens():
    for payload in (
        "mission_id:M003;pickup:RACK_A",
        "mission_id:../../../x;pickup:RACK_A;dropoff:RACK_B",
        "[]",
        "",
    ):
        try:
            parse_transport_mission(payload)
            assert False, f"expected rejection: {payload!r}"
        except ValueError:
            pass


def run_tests():
    test_json_payload()
    test_key_value_payload_and_aliases()
    test_rejects_missing_and_unsafe_tokens()
    print("All QR payload tests passed.")


if __name__ == "__main__":
    run_tests()
