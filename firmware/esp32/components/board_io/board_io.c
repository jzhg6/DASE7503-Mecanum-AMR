#include "board_io.h"

#include <math.h>

#include "board_config.h"
#include "driver/ledc.h"
#include "driver/mcpwm_prelude.h"
#include "driver/pulse_cnt.h"
#include "esp_check.h"
#include "esp_log.h"

static const char *TAG = "board_io";

static const int motor_pins[4][2] = {
    {MOTOR_FL_IN_A, MOTOR_FL_IN_B}, {MOTOR_FR_IN_A, MOTOR_FR_IN_B},
    {MOTOR_RL_IN_A, MOTOR_RL_IN_B}, {MOTOR_RR_IN_A, MOTOR_RR_IN_B}};
static const int motor_direction[4] = {
    MOTOR_FL_DIRECTION, MOTOR_FR_DIRECTION, MOTOR_RL_DIRECTION,
    MOTOR_RR_DIRECTION};
static const int encoder_pins[4][2] = {
    {ENCODER_FL_A, ENCODER_FL_B}, {ENCODER_FR_A, ENCODER_FR_B},
    {ENCODER_RL_A, ENCODER_RL_B}, {ENCODER_RR_A, ENCODER_RR_B}};
static const int encoder_direction[4] = {
    ENCODER_FL_DIRECTION, ENCODER_FR_DIRECTION, ENCODER_RL_DIRECTION,
    ENCODER_RR_DIRECTION};

static pcnt_unit_handle_t encoder_units[4];
static mcpwm_cmpr_handle_t servo_comparators[2];

static uint32_t duty_ticks(float duty) {
  const float bounded = fminf(fmaxf(fabsf(duty), 0.0f), 1.0f);
  return (uint32_t)lroundf(bounded * 255.0f);
}

static void configure_motor_pwm(void) {
  const ledc_timer_config_t timer = {
      .speed_mode = LEDC_LOW_SPEED_MODE,
      .duty_resolution = LEDC_TIMER_8_BIT,
      .timer_num = LEDC_TIMER_0,
      .freq_hz = MOTOR_PWM_FREQUENCY_HZ,
      .clk_cfg = LEDC_AUTO_CLK,
  };
  ESP_ERROR_CHECK(ledc_timer_config(&timer));
  for (unsigned int motor = 0; motor < 4; ++motor) {
    for (unsigned int side = 0; side < 2; ++side) {
      const ledc_channel_t channel = (ledc_channel_t)(motor * 2 + side);
      const ledc_channel_config_t output = {
          .gpio_num = motor_pins[motor][side],
          .speed_mode = LEDC_LOW_SPEED_MODE,
          .channel = channel,
          .intr_type = LEDC_INTR_DISABLE,
          .timer_sel = LEDC_TIMER_0,
          .duty = 0,
          .hpoint = 0,
      };
      ESP_ERROR_CHECK(ledc_channel_config(&output));
    }
  }
}

static void configure_encoders(void) {
  for (unsigned int index = 0; index < 4; ++index) {
    const pcnt_unit_config_t unit_config = {
        .low_limit = -32767,
        .high_limit = 32767,
    };
    ESP_ERROR_CHECK(pcnt_new_unit(&unit_config, &encoder_units[index]));

    pcnt_channel_handle_t channel_a = NULL;
    pcnt_channel_handle_t channel_b = NULL;
    const pcnt_chan_config_t channel_a_config = {
        .edge_gpio_num = encoder_pins[index][0],
        .level_gpio_num = encoder_pins[index][1],
    };
    const pcnt_chan_config_t channel_b_config = {
        .edge_gpio_num = encoder_pins[index][1],
        .level_gpio_num = encoder_pins[index][0],
    };
    ESP_ERROR_CHECK(
        pcnt_new_channel(encoder_units[index], &channel_a_config, &channel_a));
    ESP_ERROR_CHECK(
        pcnt_new_channel(encoder_units[index], &channel_b_config, &channel_b));
    ESP_ERROR_CHECK(pcnt_channel_set_edge_action(
        channel_a, PCNT_CHANNEL_EDGE_ACTION_INCREASE,
        PCNT_CHANNEL_EDGE_ACTION_DECREASE));
    ESP_ERROR_CHECK(pcnt_channel_set_level_action(
        channel_a, PCNT_CHANNEL_LEVEL_ACTION_KEEP,
        PCNT_CHANNEL_LEVEL_ACTION_INVERSE));
    ESP_ERROR_CHECK(pcnt_channel_set_edge_action(
        channel_b, PCNT_CHANNEL_EDGE_ACTION_DECREASE,
        PCNT_CHANNEL_EDGE_ACTION_INCREASE));
    ESP_ERROR_CHECK(pcnt_channel_set_level_action(
        channel_b, PCNT_CHANNEL_LEVEL_ACTION_KEEP,
        PCNT_CHANNEL_LEVEL_ACTION_INVERSE));
    const pcnt_glitch_filter_config_t filter = {.max_glitch_ns = 1000};
    ESP_ERROR_CHECK(pcnt_unit_set_glitch_filter(encoder_units[index], &filter));
    ESP_ERROR_CHECK(pcnt_unit_enable(encoder_units[index]));
    ESP_ERROR_CHECK(pcnt_unit_clear_count(encoder_units[index]));
    ESP_ERROR_CHECK(pcnt_unit_start(encoder_units[index]));
  }
}

static uint32_t servo_pulse_for_angle(int angle_deg) {
  if (angle_deg < SERVO_MIN_ANGLE_DEG) angle_deg = SERVO_MIN_ANGLE_DEG;
  if (angle_deg > SERVO_MAX_ANGLE_DEG) angle_deg = SERVO_MAX_ANGLE_DEG;
  const float fraction =
      (float)(angle_deg - SERVO_MIN_ANGLE_DEG) /
      (float)(SERVO_MAX_ANGLE_DEG - SERVO_MIN_ANGLE_DEG);
  return (uint32_t)lroundf(SERVO_MIN_PULSE_US +
                           fraction * (SERVO_MAX_PULSE_US -
                                       SERVO_MIN_PULSE_US));
}

static void configure_servos(void) {
  mcpwm_timer_handle_t timer = NULL;
  mcpwm_oper_handle_t oper = NULL;
  const mcpwm_timer_config_t timer_config = {
      .group_id = 0,
      .clk_src = MCPWM_TIMER_CLK_SRC_DEFAULT,
      .resolution_hz = 1000000,
      .count_mode = MCPWM_TIMER_COUNT_MODE_UP,
      .period_ticks = 20000,
  };
  ESP_ERROR_CHECK(mcpwm_new_timer(&timer_config, &timer));
  const mcpwm_operator_config_t operator_config = {.group_id = 0};
  ESP_ERROR_CHECK(mcpwm_new_operator(&operator_config, &oper));
  ESP_ERROR_CHECK(mcpwm_operator_connect_timer(oper, timer));

  const int servo_pins[2] = {SERVO_LEFT_GPIO, SERVO_RIGHT_GPIO};
  for (unsigned int index = 0; index < 2; ++index) {
    const mcpwm_comparator_config_t comparator_config = {
        .flags.update_cmp_on_tez = true,
    };
    ESP_ERROR_CHECK(mcpwm_new_comparator(
        oper, &comparator_config, &servo_comparators[index]));
    mcpwm_gen_handle_t generator = NULL;
    const mcpwm_generator_config_t generator_config = {
        .gen_gpio_num = servo_pins[index],
    };
    ESP_ERROR_CHECK(mcpwm_new_generator(oper, &generator_config, &generator));
    ESP_ERROR_CHECK(mcpwm_generator_set_action_on_timer_event(
        generator, MCPWM_GEN_TIMER_EVENT_ACTION(
                       MCPWM_TIMER_DIRECTION_UP, MCPWM_TIMER_EVENT_EMPTY,
                       MCPWM_GEN_ACTION_HIGH)));
    ESP_ERROR_CHECK(mcpwm_generator_set_action_on_compare_event(
        generator, MCPWM_GEN_COMPARE_EVENT_ACTION(
                       MCPWM_TIMER_DIRECTION_UP, servo_comparators[index],
                       MCPWM_GEN_ACTION_LOW)));
  }
  ESP_ERROR_CHECK(mcpwm_timer_enable(timer));
  ESP_ERROR_CHECK(
      mcpwm_timer_start_stop(timer, MCPWM_TIMER_START_NO_STOP));
}

void board_io_init(void) {
  configure_motor_pwm();
  configure_encoders();
  configure_servos();
  board_stop_all_motors(true);
  if (!MOTOR_OUTPUT_COMPILED_IN) {
    ESP_LOGW(TAG, "motor output compile gate is OFF");
  }
  if (!LIFT_OUTPUT_COMPILED_IN) {
    ESP_LOGW(TAG, "lift output compile gate is OFF");
  }
}

void board_set_motor_duty(unsigned int index, float signed_duty) {
  if (index >= 4) return;
  if (!MOTOR_OUTPUT_COMPILED_IN || !isfinite(signed_duty)) signed_duty = 0.0f;
  signed_duty *= (float)motor_direction[index];
  const uint32_t forward = signed_duty > 0.0f ? duty_ticks(signed_duty) : 0;
  const uint32_t reverse = signed_duty < 0.0f ? duty_ticks(signed_duty) : 0;
  const ledc_channel_t channel_a = (ledc_channel_t)(index * 2);
  const ledc_channel_t channel_b = (ledc_channel_t)(index * 2 + 1);
  ESP_ERROR_CHECK(ledc_set_duty(LEDC_LOW_SPEED_MODE, channel_a, forward));
  ESP_ERROR_CHECK(ledc_update_duty(LEDC_LOW_SPEED_MODE, channel_a));
  ESP_ERROR_CHECK(ledc_set_duty(LEDC_LOW_SPEED_MODE, channel_b, reverse));
  ESP_ERROR_CHECK(ledc_update_duty(LEDC_LOW_SPEED_MODE, channel_b));
}

void board_stop_all_motors(bool brake) {
  const uint32_t duty = brake && MOTOR_OUTPUT_COMPILED_IN ? 255 : 0;
  for (unsigned int channel = 0; channel < 8; ++channel) {
    ESP_ERROR_CHECK(ledc_set_duty(LEDC_LOW_SPEED_MODE,
                                  (ledc_channel_t)channel, duty));
    ESP_ERROR_CHECK(
        ledc_update_duty(LEDC_LOW_SPEED_MODE, (ledc_channel_t)channel));
  }
}

int board_take_encoder_delta(unsigned int index) {
  if (index >= 4 || encoder_units[index] == NULL) return 0;
  int count = 0;
  ESP_ERROR_CHECK(pcnt_unit_get_count(encoder_units[index], &count));
  ESP_ERROR_CHECK(pcnt_unit_clear_count(encoder_units[index]));
  return count * encoder_direction[index];
}

bool board_set_lift(bool raised) {
  if (!LIFT_OUTPUT_COMPILED_IN) return false;
  const int left = raised ? LIFT_RAISE_LEFT_DEG : LIFT_LOWER_LEFT_DEG;
  const int right = raised ? LIFT_RAISE_RIGHT_DEG : LIFT_LOWER_RIGHT_DEG;
  ESP_ERROR_CHECK(mcpwm_comparator_set_compare_value(
      servo_comparators[0], servo_pulse_for_angle(left)));
  ESP_ERROR_CHECK(mcpwm_comparator_set_compare_value(
      servo_comparators[1], servo_pulse_for_angle(right)));
  return true;
}
