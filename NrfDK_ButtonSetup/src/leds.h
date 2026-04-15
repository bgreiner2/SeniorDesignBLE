/*
 * @file leds.h
 * @brief LED control module for the nRF52840 DK.
 *
 * This header file contains function declarations for LED initialization and control.
 * It allows the application to initialize the LEDs and toggle their states.
 *
 * @author Ameed Othman
 * @date 2024-11-29
 *
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef __LEDS_H__
#define __LEDS_H__

void init_leds(void);
void toggle_led(int led_num);

#endif