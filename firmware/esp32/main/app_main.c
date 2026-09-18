#include <math.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

#include "board_config.h"
#include "board_io.h"
#include "base_control.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "geometry_msgs/msg/twist.h"
#include "micro_ros_utilities/string_utilities.h"
#include "nav_msgs/msg/odometry.h"
#include "rcl/rcl.h"
#include "rclc/executor.h"
#include "rclc/rclc.h"
#include "rmw_microros/rmw_microros.h"
#include "std_msgs/msg/bool.h"
#include "std_msgs/msg/int32.h"
#include "uros_network_interfaces.h"

static const char *TAG = "mecanum_base";
static portMUX_TYPE state_lock = portMUX_INITIALIZER_UNLOCKED;

static wheel_speeds_t target_wheels;
static body_velocity_t measured_body;
static float odom_x;
static float odom_y;
static float odom_yaw;
static int64_t last_command_us;
static bool base_enabled;
static int32_t lift_state = -1;

static rcl_publisher_t odom_publisher;
static rcl_publisher_t enabled_publisher;
static rcl_publisher_t lift_state_publisher;
static nav_msgs__msg__Odometry odom_message;
static std_msgs__msg__Bool enabled_message;
static std_msgs__msg__Int32 lift_state_message;

static void stop_and_disarm(void) {
  portENTER_CRITICAL(&state_lock);
  base_enabled = false;
  target_wheels = (wheel_speeds_t){0};
  portEXIT_CRITICAL(&state_lock);
  board_stop_all_motors(true);
}

static void command_callback(const void *input) {
  const geometry_msgs__msg__Twist *message = input;
  const body_velocity_t requested = {
      .vx = (float)message->linear.x,
      .vy = (float)message->linear.y,
      .wz = (float)message->angular.z,
  };
  if (!base_values_are_finite(requested)) {
    stop_and_disarm();
    return;
  }
  const wheel_speeds_t wheels = base_inverse_kinematics(
      requested.vx, requested.vy, requested.wz, HALF_WHEELBASE_M,
      HALF_TRACK_M, MAX_WHEEL_LINEAR_SPEED_MPS);
  portENTER_CRITICAL(&state_lock);
  if (base_enabled) target_wheels = wheels;
  last_command_us = esp_timer_get_time();
  portEXIT_CRITICAL(&state_lock);
}

static void enable_callback(const void *input) {
  const std_msgs__msg__Bool *message = input;
  if (!message->data) {
    stop_and_disarm();
    return;
  }
  portENTER_CRITICAL(&state_lock);
  base_enabled = MOTOR_OUTPUT_COMPILED_IN != 0;
  last_command_us = esp_timer_get_time();
  target_wheels = (wheel_speeds_t){0};
  portEXIT_CRITICAL(&state_lock);
}

static void lift_callback(const void *input) {
  const std_msgs__msg__Int32 *message = input;
  if (message->data != 0 && message->data != 1) return;
  if (board_set_lift(message->data == 1)) {
    portENTER_CRITICAL(&state_lock);
    lift_state = message->data;
    portEXIT_CRITICAL(&state_lock);
  }
}

static void control_task(void *argument) {
  (void)argument;
  const float dt = MOTOR_CONTROL_PERIOD_MS / 1000.0f;
  wheel_pid_t pid[4];
  for (unsigned int index = 0; index < 4; ++index) {
    pid[index] = (wheel_pid_t){
        .kp = PID_KP,
        .ki = PID_KI,
        .kd = PID_KD,
        .integral_limit = PID_INTEGRAL_LIMIT,
    };
  }
  TickType_t wake = xTaskGetTickCount();
  while (true) {
    const wheel_speeds_t sample = {
        .fl = encoder_delta_to_speed(board_take_encoder_delta(0),
                                     WHEEL_CIRCUMFERENCE_M,
                                     ENCODER_COUNTS_PER_REVOLUTION, dt),
        .fr = encoder_delta_to_speed(board_take_encoder_delta(1),
                                     WHEEL_CIRCUMFERENCE_M,
                                     ENCODER_COUNTS_PER_REVOLUTION, dt),
        .rl = encoder_delta_to_speed(board_take_encoder_delta(2),
                                     WHEEL_CIRCUMFERENCE_M,
                                     ENCODER_COUNTS_PER_REVOLUTION, dt),
        .rr = encoder_delta_to_speed(board_take_encoder_delta(3),
                                     WHEEL_CIRCUMFERENCE_M,
                                     ENCODER_COUNTS_PER_REVOLUTION, dt),
    };
    const body_velocity_t body = base_forward_kinematics(
        sample, HALF_WHEELBASE_M, HALF_TRACK_M);

    wheel_speeds_t requested;
    bool enabled;
    portENTER_CRITICAL(&state_lock);
    const int64_t now = esp_timer_get_time();
    if (base_enabled && now - last_command_us > COMMAND_WATCHDOG_MS * 1000LL) {
      target_wheels = (wheel_speeds_t){0};
    }
    enabled = base_enabled;
    requested = target_wheels;
    measured_body = body;
    const float cosine = cosf(odom_yaw);
    const float sine = sinf(odom_yaw);
    odom_x += (body.vx * cosine - body.vy * sine) * dt;
    odom_y += (body.vx * sine + body.vy * cosine) * dt;
    odom_yaw += body.wz * dt;
    portEXIT_CRITICAL(&state_lock);

    const float targets[4] = {requested.fl, requested.fr, requested.rl,
                              requested.rr};
    const float measured[4] = {sample.fl, sample.fr, sample.rl, sample.rr};
    for (unsigned int index = 0; index < 4; ++index) {
      if (!enabled) {
        wheel_pid_reset(&pid[index]);
        board_set_motor_duty(index, 0.0f);
      } else {
        board_set_motor_duty(index, wheel_pid_step(
                                        &pid[index], targets[index],
                                        measured[index], dt, 1.0f));
      }
    }
    vTaskDelayUntil(&wake, pdMS_TO_TICKS(MOTOR_CONTROL_PERIOD_MS));
  }
}

static void fill_and_publish_state(rcl_timer_t *timer, int64_t last_call_time) {
  (void)timer;
  (void)last_call_time;
  float x, y, yaw;
  body_velocity_t body;
  bool enabled;
  int32_t lift;
  portENTER_CRITICAL(&state_lock);
  x = odom_x;
  y = odom_y;
  yaw = odom_yaw;
  body = measured_body;
  enabled = base_enabled;
  lift = lift_state;
  portEXIT_CRITICAL(&state_lock);

  const int64_t now_ns = rmw_uros_epoch_nanos();
  odom_message.header.stamp.sec = now_ns / 1000000000LL;
  odom_message.header.stamp.nanosec = now_ns % 1000000000LL;
  odom_message.pose.pose.position.x = x;
  odom_message.pose.pose.position.y = y;
  odom_message.pose.pose.orientation.z = sinf(yaw * 0.5f);
  odom_message.pose.pose.orientation.w = cosf(yaw * 0.5f);
  odom_message.twist.twist.linear.x = body.vx;
  odom_message.twist.twist.linear.y = body.vy;
  odom_message.twist.twist.angular.z = body.wz;
  enabled_message.data = enabled;
  lift_state_message.data = lift;
  rcl_publish(&odom_publisher, &odom_message, NULL);
  rcl_publish(&enabled_publisher, &enabled_message, NULL);
  rcl_publish(&lift_state_publisher, &lift_state_message, NULL);
}

static bool create_ros_entities(rclc_support_t *support, rcl_node_t *node,
                                rcl_timer_t *timer,
                                rcl_subscription_t *command_subscription,
                                rcl_subscription_t *enable_subscription,
                                rcl_subscription_t *lift_subscription,
                                rclc_executor_t *executor,
                                geometry_msgs__msg__Twist *command_message,
                                std_msgs__msg__Bool *enable_command,
                                std_msgs__msg__Int32 *lift_command) {
  rcl_allocator_t allocator = rcl_get_default_allocator();
  if (rclc_support_init(support, 0, NULL, &allocator) != RCL_RET_OK) return false;
  if (rclc_node_init_default(node, "mecanum_base", "", support) != RCL_RET_OK)
    return false;
  if (rclc_publisher_init_default(
          &odom_publisher, node,
          ROSIDL_GET_MSG_TYPE_SUPPORT(nav_msgs, msg, Odometry),
          "/wheel/odom") != RCL_RET_OK)
    return false;
  if (rclc_publisher_init_default(
          &enabled_publisher, node,
          ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Bool),
          "/base/enabled") != RCL_RET_OK)
    return false;
  if (rclc_publisher_init_default(
          &lift_state_publisher, node,
          ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
          "/lift/state") != RCL_RET_OK)
    return false;
  if (rclc_subscription_init_default(
          command_subscription, node,
          ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Twist),
          "/cmd_vel") != RCL_RET_OK)
    return false;
  if (rclc_subscription_init_default(
          enable_subscription, node,
          ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Bool),
          "/base/enable") != RCL_RET_OK)
    return false;
  if (rclc_subscription_init_default(
          lift_subscription, node,
          ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
          "/lift/command") != RCL_RET_OK)
    return false;
  if (rclc_timer_init_default(timer, support, RCL_MS_TO_NS(50),
                              fill_and_publish_state) !=
      RCL_RET_OK)
    return false;
  if (rclc_executor_init(executor, &support->context, 4, &allocator) != RCL_RET_OK)
    return false;
  if (rclc_executor_add_timer(executor, timer) != RCL_RET_OK) return false;
  if (rclc_executor_add_subscription(executor, command_subscription,
                                     command_message, command_callback,
                                     ON_NEW_DATA) != RCL_RET_OK)
    return false;
  if (rclc_executor_add_subscription(executor, enable_subscription,
                                     enable_command, enable_callback,
                                     ON_NEW_DATA) != RCL_RET_OK)
    return false;
  return rclc_executor_add_subscription(executor, lift_subscription,
                                        lift_command, lift_callback,
                                        ON_NEW_DATA) == RCL_RET_OK;
}

static void micro_ros_task(void *argument) {
  (void)argument;
  while (true) {
    while (rmw_uros_ping_agent(500, 1) != RMW_RET_OK) {
      stop_and_disarm();
      vTaskDelay(pdMS_TO_TICKS(500));
    }
    rclc_support_t support = {0};
    rcl_node_t node = rcl_get_zero_initialized_node();
    rcl_timer_t timer = rcl_get_zero_initialized_timer();
    rcl_subscription_t command_subscription =
        rcl_get_zero_initialized_subscription();
    rcl_subscription_t enable_subscription =
        rcl_get_zero_initialized_subscription();
    rcl_subscription_t lift_subscription =
        rcl_get_zero_initialized_subscription();
    rclc_executor_t executor = rclc_executor_get_zero_initialized_executor();
    geometry_msgs__msg__Twist command_message;
    std_msgs__msg__Bool enable_command;
    std_msgs__msg__Int32 lift_command;

    if (!create_ros_entities(&support, &node, &timer, &command_subscription,
                             &enable_subscription, &lift_subscription, &executor,
                             &command_message, &enable_command, &lift_command)) {
      ESP_LOGE(TAG, "failed to create ROS entities");
      stop_and_disarm();
      vTaskDelay(pdMS_TO_TICKS(1000));
      continue;
    }
    rmw_uros_sync_session(1000);
    ESP_LOGI(TAG, "micro-ROS connected");
    int ping_divider = 0;
    while (true) {
      rclc_executor_spin_some(&executor, RCL_MS_TO_NS(20));
      if (++ping_divider >= 25) {
        ping_divider = 0;
        if (rmw_uros_ping_agent(100, 1) != RMW_RET_OK) break;
      }
      vTaskDelay(pdMS_TO_TICKS(20));
    }
    ESP_LOGW(TAG, "micro-ROS disconnected; motors disarmed");
    stop_and_disarm();
    rclc_executor_fini(&executor);
    rcl_timer_fini(&timer);
    rcl_subscription_fini(&command_subscription, &node);
    rcl_subscription_fini(&enable_subscription, &node);
    rcl_subscription_fini(&lift_subscription, &node);
    rcl_publisher_fini(&odom_publisher, &node);
    rcl_publisher_fini(&enabled_publisher, &node);
    rcl_publisher_fini(&lift_state_publisher, &node);
    rcl_node_fini(&node);
    rclc_support_fini(&support);
  }
}

void app_main(void) {
  board_io_init();
  stop_and_disarm();
  odom_message.header.frame_id = micro_ros_string_utilities_set(
      odom_message.header.frame_id, "odom");
  odom_message.child_frame_id = micro_ros_string_utilities_set(
      odom_message.child_frame_id, "base_footprint");
  odom_message.pose.covariance[0] = 0.02;
  odom_message.pose.covariance[7] = 0.02;
  odom_message.pose.covariance[14] = 1000000.0;
  odom_message.pose.covariance[21] = 1000000.0;
  odom_message.pose.covariance[28] = 1000000.0;
  odom_message.pose.covariance[35] = 0.05;
  odom_message.twist.covariance[0] = 0.01;
  odom_message.twist.covariance[7] = 0.01;
  odom_message.twist.covariance[14] = 1000000.0;
  odom_message.twist.covariance[21] = 1000000.0;
  odom_message.twist.covariance[28] = 1000000.0;
  odom_message.twist.covariance[35] = 0.02;

  ESP_ERROR_CHECK(uros_network_interface_initialize());
  xTaskCreatePinnedToCore(control_task, "wheel_control", 6144, NULL, 12, NULL, 1);
  xTaskCreate(micro_ros_task, "micro_ros", 16384, NULL, 10, NULL);
}
