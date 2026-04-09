#include <kernel.h>
#include <sys/printk.h>
#include <nrfx_saadc.h>
#include <hal/nrf_saadc.h>

#define FLEX_CH_COUNT 5
#define FLEX_SAMPLE_INTERVAL_MS 10

static nrfx_saadc_channel_t channels[FLEX_CH_COUNT] = {
    NRFX_SAADC_DEFAULT_CHANNEL_SE(NRF_SAADC_INPUT_AIN1, 0),
    NRFX_SAADC_DEFAULT_CHANNEL_SE(NRF_SAADC_INPUT_AIN2, 1),
    NRFX_SAADC_DEFAULT_CHANNEL_SE(NRF_SAADC_INPUT_AIN4, 2),
    NRFX_SAADC_DEFAULT_CHANNEL_SE(NRF_SAADC_INPUT_AIN5, 3),
    NRFX_SAADC_DEFAULT_CHANNEL_SE(NRF_SAADC_INPUT_AIN6, 4),
};

static int16_t samples[FLEX_CH_COUNT];

void adc_get_latest_samples(int16_t out[FLEX_CH_COUNT])
{
  for (int i = 0; i < FLEX_CH_COUNT; i++)
  {
    out[i] = samples[i];
  }
}

static void saadc_event_handler(nrfx_saadc_evt_t const *p_event)
{
  if (p_event->type == NRFX_SAADC_EVT_DONE)
  {
    for (int i = 0; i < FLEX_CH_COUNT; i++)
    {
      samples[i] = p_event->data.done.p_buffer[i];
    }

    nrfx_saadc_buffer_set(samples, FLEX_CH_COUNT);
  }
}

static void flex_sample_timer_handler(struct k_timer *timer);
K_TIMER_DEFINE(flex_sample_timer, flex_sample_timer_handler, NULL);

void flex_sample_timer_handler(struct k_timer *timer)
{
  nrfx_err_t err = nrfx_saadc_mode_trigger();
  if (err != NRFX_SUCCESS)
  {
    printk("nrfx_saadc_mode_trigger err=%08x\n", err);
  }
}

void configure_saadc(void)
{
  IRQ_CONNECT(DT_IRQN(DT_NODELABEL(adc)),
              DT_IRQ(DT_NODELABEL(adc), priority),
              nrfx_isr, nrfx_saadc_irq_handler, 0);

  nrfx_err_t err = nrfx_saadc_init(DT_IRQ(DT_NODELABEL(adc), priority));
  if (err != NRFX_SUCCESS)
  {
    printk("nrfx_saadc_init error: %08x\n", err);
    return;
  }

  for (int i = 0; i < FLEX_CH_COUNT; i++)
  {
    channels[i].channel_config.gain = NRF_SAADC_GAIN1_6;
  }

  err = nrfx_saadc_channels_config(channels, FLEX_CH_COUNT);
  if (err != NRFX_SUCCESS)
  {
    printk("nrfx_saadc_channels_config error: %08x\n", err);
    return;
  }

  err = nrfx_saadc_simple_mode_set(
      BIT(0) | BIT(1) | BIT(2) | BIT(3) | BIT(4),
      NRF_SAADC_RESOLUTION_12BIT,
      NRF_SAADC_OVERSAMPLE_DISABLED,
      saadc_event_handler);
  if (err != NRFX_SUCCESS)
  {
    printk("nrfx_saadc_simple_mode_set error: %08x\n", err);
    return;
  }

  err = nrfx_saadc_buffer_set(samples, FLEX_CH_COUNT);
  if (err != NRFX_SUCCESS)
  {
    printk("nrfx_saadc_buffer_set error: %08x\n", err);
    return;
  }

  printk("5-channel SAADC configured\n");
  k_timer_start(&flex_sample_timer, K_NO_WAIT, K_MSEC(FLEX_SAMPLE_INTERVAL_MS));
}