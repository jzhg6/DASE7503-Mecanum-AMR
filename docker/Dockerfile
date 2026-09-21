FROM osrf/ros:jazzy-desktop

# Gerekli sistem bağımlılıkları
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-opencv \
    ros-jazzy-nav2-bringup \
    ros-jazzy-slam-toolbox \
    ros-jazzy-cv-bridge \
    ros-jazzy-joint-state-publisher \
    ros-jazzy-robot-state-publisher \
    ros-jazzy-xacro \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıkları
# Use the system OpenCV and numpy shared by cv_bridge.

# Workspace oluştur
WORKDIR /ros2_ws
COPY src/ src/

# Build
RUN . /opt/ros/jazzy/setup.sh && \
    colcon build --symlink-install

# Entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]
