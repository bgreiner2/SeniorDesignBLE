#ifndef ADC_TEST_H
#define ADC_TEST_H

#include <stdint.h>

#define FLEX_CH_COUNT 5

void configure_saadc(void);
void adc_get_latest_samples(int16_t out[FLEX_CH_COUNT]);

#endif