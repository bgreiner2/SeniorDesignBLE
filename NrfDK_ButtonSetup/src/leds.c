/*
 * @file leds.c
 * @brief LED control implementation for the nRF52840 DK.
 *
 * This file contains implementations of functions for initializing LEDs
 * and controlling their states. It sets up the GPIO pins for the LEDs and
 * provides a function to toggle an LED by index.
 *
 * @author Ameed Othman
 * @date 2024-11-29
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include <device.h>
#include <drivers/gpio.h>
#include "leds.h"

#define NUM_LEDS 4

static const struct gpio_dt_spec led_specs[NUM_LEDS] = {
    GPIO_DT_SPEC_GET_OR(DT_ALIAS(led0), gpios, {0}),
    GPIO_DT_SPEC_GET_OR(DT_ALIAS(led1), gpios, {0}),
    GPIO_DT_SPEC_GET_OR(DT_ALIAS(led2), gpios, {0}),
    GPIO_DT_SPEC_GET_OR(DT_ALIAS(led3), gpios, {0}),
};

void init_leds(void)
{
  for (int i = 0; i < NUM_LEDS; i++)
  {
    if (!device_is_ready(led_specs[i].port))
    {
      return;
    }
    gpio_pin_configure_dt(&led_specs[i], GPIO_OUTPUT_INACTIVE);
  }
}

void toggle_led(int led_num)
{
  if (led_num < NUM_LEDS)
  {
    gpio_pin_toggle_dt(&led_specs[led_num]);
  }
}