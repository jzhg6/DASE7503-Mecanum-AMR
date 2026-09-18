cmake_minimum_required(VERSION 3.8)
project(mecanum_hw_bridge)

find_package(ament_cmake REQUIRED)
find_package(rclpy REQUIRED)

install(
  DIRECTORY mecanum_hw_bridge launch config
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS
    mecanum_hw_bridge/hardware_supervisor.py
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
