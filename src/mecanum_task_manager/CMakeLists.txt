cmake_minimum_required(VERSION 3.8)
project(mecanum_task_manager)

find_package(ament_cmake REQUIRED)
find_package(rclpy REQUIRED)

install(
  DIRECTORY mecanum_task_manager launch config
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS
    mecanum_task_manager/qr_reader.py
    mecanum_task_manager/task_manager.py
    mecanum_task_manager/state_machine.py
    mecanum_task_manager/patrol_manager.py
    mecanum_task_manager/simple_patrol.py
    mecanum_task_manager/mission_manager.py
    mecanum_task_manager/course_mission_node.py
  DESTINATION lib/${PROJECT_NAME}
)

install(
  FILES
    mecanum_task_manager/qr_payload.py
    mecanum_task_manager/course_game.py
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(course_game test/test_course_game.py)
  ament_add_pytest_test(course_ros_graph test/test_ros_course.py TIMEOUT 60)
  ament_add_pytest_test(camera_qr_pixels test/test_qr_camera.py)
endif()
ament_package()
