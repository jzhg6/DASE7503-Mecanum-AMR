idf_component_register(
  SRCS "app_main.c" "serial_transport.c"
  INCLUDE_DIRS "."
  REQUIRES base_control board_io robot_config driver esp_timer
)
