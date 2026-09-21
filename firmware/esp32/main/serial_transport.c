/* Original UART0 transport using the documented micro-ROS custom transport API.
 * USB-C data socket is bridged to GPIO43 TX / GPIO44 RX on the supplied board.
 * No application console output may share this UART. */
#include <stdbool.h>
#include <stdint.h>
#include "driver/uart.h"
#include "esp_check.h"
#include "rmw_microros/rmw_microros.h"
#include "board_config.h"
#include "serial_transport.h"

static bool serial_open(struct uxrCustomTransport *transport) {
  (void)transport;
  return true;
}
static bool serial_close(struct uxrCustomTransport *transport) {
  (void)transport;
  return true; /* UART stays installed across agent reconnects. */
}
static size_t serial_write(struct uxrCustomTransport *transport,
                           const uint8_t *buffer, size_t length, uint8_t *error) {
  (void)transport;
  int written = uart_write_bytes(UART_NUM_0, buffer, length);
  *error = written < 0 ? 1 : 0;
  return written < 0 ? 0 : (size_t)written;
}
static size_t serial_read(struct uxrCustomTransport *transport, uint8_t *buffer,
                          size_t length, int timeout, uint8_t *error) {
  (void)transport;
  TickType_t ticks = pdMS_TO_TICKS(timeout > 0 ? timeout : 0);
  if (timeout > 0 && ticks == 0) ticks = 1;
  int received = uart_read_bytes(UART_NUM_0, buffer, length, ticks);
  *error = received < 0 ? 1 : 0;
  return received < 0 ? 0 : (size_t)received;
}
void course_serial_transport_init(void) {
  const uart_config_t config = {
      .baud_rate = MICROROS_UART_BAUD, .data_bits = UART_DATA_8_BITS,
      .parity = UART_PARITY_DISABLE, .stop_bits = UART_STOP_BITS_1,
      .flow_ctrl = UART_HW_FLOWCTRL_DISABLE, .source_clk = UART_SCLK_DEFAULT};
  ESP_ERROR_CHECK(uart_param_config(UART_NUM_0, &config));
  ESP_ERROR_CHECK(uart_set_pin(UART_NUM_0, MICROROS_UART_TX_GPIO,
      MICROROS_UART_RX_GPIO, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
  ESP_ERROR_CHECK(uart_driver_install(UART_NUM_0, 4096, 4096, 0, NULL, 0));
  rmw_uros_set_custom_transport(true, NULL, serial_open, serial_close,
                                serial_write, serial_read);
}
