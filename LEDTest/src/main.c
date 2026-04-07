#include <kernel.h>
#include <device.h>
#include <drivers/gpio.h>
#include <devicetree.h>

#define LED2 19
#define LED3 20

int main(void)
{
	const struct device *gpio0 = DEVICE_DT_GET(DT_NODELABEL(gpio0));

	if (!device_is_ready(gpio0))
	{
		return 0;
	}

	gpio_pin_configure(gpio0, LED2, GPIO_OUTPUT_INACTIVE);
	gpio_pin_configure(gpio0, LED3, GPIO_OUTPUT_INACTIVE);

	while (1)
	{
		gpio_pin_set(gpio0, LED2, 1);
		gpio_pin_set(gpio0, LED3, 0);
		k_sleep(K_MSEC(500));

		gpio_pin_set(gpio0, LED2, 0);
		gpio_pin_set(gpio0, LED3, 1);
		k_sleep(K_MSEC(500));
	}
}