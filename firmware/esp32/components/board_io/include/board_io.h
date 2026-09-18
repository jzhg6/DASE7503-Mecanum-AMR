#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "base_control.h"

#ifdef __cplusplus
extern "C" {
#endif

void board_io_init(void);
void board_set_motor_duty(unsigned int index, float signed_duty);
void board_stop_all_motors(bool brake);
int board_take_encoder_delta(unsigned int index);
bool board_set_lift(bool raised);

#ifdef __cplusplus
}
#endif
