/*
 * @file buttons.c
 * @brief Button handling implementation for the nRF52840 DK.
 *
 * This file contains implementations of functions for initializing buttons
 * and handling button interrupts. It sets up the GPIO pins for the buttons and
 * configures interrupt callbacks to toggle the corresponding LEDs.
 *
 * @author Ameed Othman
 * @date 2024-11-29
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#include <device.h>
#include <drivers/gpio.h>
#include "buttons.h"
#include "leds.h"

#define NUM_BUTTONS 4

static const struct gpio_dt_spec button_specs[NUM_BUTTONS] = {
    GPIO_DT_SPEC_GET_OR(DT_ALIAS(sw0), gpios, {0}),
    GPIO_DT_SPEC_GET_OR(DT_ALIAS(sw1), gpios, {0}),
    GPIO_DT_SPEC_GET_OR(DT_ALIAS(sw2), gpios, {0}),
    GPIO_DT_SPEC_GET_OR(DT_ALIAS(sw3), gpios, {0}),
};

static struct gpio_callback button_cbs[NUM_BUTTONS];

static void button_pressed(const struct device *dev, struct gpio_callback *cb, uint32_t pins)
{
  for (int i = 0; i < NUM_BUTTONS; i++)
  {
    if (pins & BIT(button_specs[i].pin))
    {
      toggle_led(i);
    }
  }
}

void init_buttons(void)
{
  for (int i = 0; i < NUM_BUTTONS; i++)
  {
    if (!device_is_ready(button_specs[i].port))
    {
      return;
    }

    gpio_pin_configure_dt(&button_specs[i], GPIO_INPUT);
    gpio_pin_interrupt_configure_dt(&button_specs[i], GPIO_INT_EDGE_TO_ACTIVE);

    gpio_init_callback(&button_cbs[i], button_pressed, BIT(button_specs[i].pin));
    gpio_add_callback(button_specs[i].port, &button_cbs[i]);
  }
}