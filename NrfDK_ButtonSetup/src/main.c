// /*
//  * @file main.c
//  * @brief Button interrupt example for the nRF52840 DK.
//  *
//  * This file contains the source code for a sample application that demonstrates
//  * how to use the GPIO driver to configure a button as an input and an LED as an output.
//  * The application will toggle the LED state when the button is pressed.
//  *
//  * @author Ameed Othman
//  * @date 2024-11-29
//  *
//  * SPDX-License-Identifier: Apache-2.0
//  */

// #include <kernel.h>
// #include "buttons.h"
// #include "leds.h"

// #define SLEEP_TIME_MS (10 * 60 * 1000) // 10 minutes

// void main(void)
// {
//   init_leds();
//   init_buttons();

//   while (1)
//   {
//     k_msleep(SLEEP_TIME_MS);
//   }
// }
#include <kernel.h>
#include <drivers/gpio.h>
#include <sys/printk.h>

#define BUTTON_NODE DT_ALIAS(sw0)

#if !DT_NODE_HAS_STATUS(BUTTON_NODE, okay)
#error "Unsupported board: sw0 alias is not defined"
#endif

static const struct gpio_dt_spec button = GPIO_DT_SPEC_GET(BUTTON_NODE, gpios);
static const struct device *gpio0_dev = DEVICE_DT_GET(DT_NODELABEL(gpio0));

static struct gpio_callback button_cb_data;
static uint8_t pin19_state = 0;

static void button_pressed(const struct device *dev, struct gpio_callback *cb, uint32_t pins)
{
  ARG_UNUSED(dev);
  ARG_UNUSED(cb);

  if (pins & BIT(button.pin))
  {
    pin19_state ^= 1;
    gpio_pin_set(gpio0_dev, 19, pin19_state);
    printk("P0.19 = %s\n", pin19_state ? "HIGH" : "LOW");
  }
}

void main(void)
{
  int ret;

  printk("nRF52840 DK button to P0.19 toggle example starting...\n");

  if (!device_is_ready(button.port))
  {
    printk("Button device not ready\n");
    return;
  }

  if (!device_is_ready(gpio0_dev))
  {
    printk("GPIO0 device not ready\n");
    return;
  }

  // Configure BUTTON1 from the board DeviceTree
  ret = gpio_pin_configure_dt(&button, GPIO_INPUT);
  if (ret < 0)
  {
    printk("Failed to configure button\n");
    return;
  }

  ret = gpio_pin_interrupt_configure_dt(&button, GPIO_INT_EDGE_TO_ACTIVE);
  if (ret < 0)
  {
    printk("Failed to configure button interrupt\n");
    return;
  }

  gpio_init_callback(&button_cb_data, button_pressed, BIT(button.pin));
  gpio_add_callback(button.port, &button_cb_data);

  // Configure P0.19 as output, start LOW
  ret = gpio_pin_configure(gpio0_dev, 19, GPIO_OUTPUT_INACTIVE);
  if (ret < 0)
  {
    printk("Failed to configure P0.19\n");
    return;
  }

  gpio_pin_set(gpio0_dev, 19, 0);
  printk("Ready. Press BUTTON1 to toggle P0.19.\n");

  while (1)
  {
    k_msleep(1000);
  }
}