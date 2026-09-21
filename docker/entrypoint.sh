#!/bin/bash
set -e
. /opt/ros/jazzy/setup.sh
[ -f /ros2_ws/install/setup.sh ] && . /ros2_ws/install/setup.sh
exec "$@"
