cmake_minimum_required(VERSION 3.8)
project(mecanum_navigation)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY launch config maps worlds
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(nav2_activation test/test_nav2_activation.py TIMEOUT 80)
endif()
ament_package()
