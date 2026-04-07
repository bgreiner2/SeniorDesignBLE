#include <kernel.h>
#include <device.h>
#include <sys/printk.h>
#include <sys/byteorder.h>
#include <zephyr/types.h>

#include <bluetooth/bluetooth.h>
#include <bluetooth/hci.h>
#include <bluetooth/conn.h>
#include <bluetooth/gatt.h>

#include "ADC_Test.h"

#include <drivers/adc.h>
#include <drivers/sensor.h>
#include <nrfx_saadc.h>
#include <devicetree.h>

#include <math.h>

#define DEVICE_NAME CONFIG_BT_DEVICE_NAME
#define DEVICE_NAME_LEN (sizeof(DEVICE_NAME) - 1)

static const struct device *imu = DEVICE_DT_GET(DT_NODELABEL(mpu6050));

// Advertising
static const struct bt_data ad[] = {
		BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR))};

// Char UUID: 7e2a2b11-5b9a-4c8f-9d6a-2f6f2a4f8b01

static struct bt_uuid_128 svc_uuid = BT_UUID_INIT_128(
		0x01, 0x8b, 0x4f, 0x2a, 0x6f, 0x2f, 0x6a, 0x9d,
		0x8f, 0x4c, 0x9a, 0x5b, 0x10, 0x2b, 0x2a, 0x7e);

static struct bt_uuid_128 chr_uuid = BT_UUID_INIT_128(
		0x01, 0x8b, 0x4f, 0x2a, 0x6f, 0x2f, 0x6a, 0x9d,
		0x8f, 0x4c, 0x9a, 0x5b, 0x11, 0x2b, 0x2a, 0x7e);

struct __packed sensor_frame
{
	uint32_t t_s; // Device uptime in seconds

	int32_t flex1;
	int32_t flex2;
	int32_t flex3;
	int32_t flex4;
	int32_t flex5;

	// Accel units: milli-m/s^2
	int32_t AccelX;
	int32_t AccelY;
	int32_t AccelZ;

	// Gyro units: milli-rad/s
	int32_t GyroX;
	int32_t GyroY;
	int32_t GyroZ;

	// Left at 0 for now
	int32_t Pitch;
	int32_t Roll;
};

static struct sensor_frame frame;
static bool notify_enabled;

// Convert Zephyr sensor_value to milli-units
static int32_t sensor_value_to_milli_i32(const struct sensor_value *val)
{
	int64_t micro = ((int64_t)val->val1 * 1000000LL) + val->val2;
	return (int32_t)(micro / 1000LL);
}

static void update_pitch_roll_from_accel(void)
{
	float ax = (float)frame.AccelX / 1000.0f;
	float ay = (float)frame.AccelY / 1000.0f;
	float az = (float)frame.AccelZ / 1000.0f;

	float pitch_deg = atan2f(-ax, sqrtf((ay * ay) + (az * az))) * (180.0f / 3.14159265f);
	float roll_deg = atan2f(ay, az) * (180.0f / 3.14159265f);

	// Store in milli-degrees so the BLE frame stays int32_t
	frame.Pitch = (int32_t)(pitch_deg * 1000.0f);
	frame.Roll = (int32_t)(roll_deg * 1000.0f);
}

static int read_mpu6050_frame(void)
{
	struct sensor_value accel[3];
	struct sensor_value gyro[3];
	int err;

	err = sensor_sample_fetch(imu);
	if (err)
	{
		return err;
	}

	err = sensor_channel_get(imu, SENSOR_CHAN_ACCEL_XYZ, accel);
	if (err)
	{
		return err;
	}

	err = sensor_channel_get(imu, SENSOR_CHAN_GYRO_XYZ, gyro);
	if (err)
	{
		return err;
	}

	frame.AccelX = sensor_value_to_milli_i32(&accel[0]);
	frame.AccelY = sensor_value_to_milli_i32(&accel[1]);
	frame.AccelZ = sensor_value_to_milli_i32(&accel[2]);

	frame.GyroX = sensor_value_to_milli_i32(&gyro[0]);
	frame.GyroY = sensor_value_to_milli_i32(&gyro[1]);
	frame.GyroZ = sensor_value_to_milli_i32(&gyro[2]);

	update_pitch_roll_from_accel();

	return 0;
}

// Called when the client enables/disables notifications
static void ccc_cfg_changed(const struct bt_gatt_attr *attr, uint16_t value)
{
	notify_enabled = (value == BT_GATT_CCC_NOTIFY);
	printk("Notify %s\n", notify_enabled ? "ENABLED" : "DISABLED");
}

// Read handler
static ssize_t read_frame(struct bt_conn *conn,
													const struct bt_gatt_attr *attr,
													void *buf, uint16_t len, uint16_t offset)
{
	const struct sensor_frame *f = attr->user_data;
	return bt_gatt_attr_read(conn, attr, buf, len, offset, f, sizeof(*f));
}

// BT service
BT_GATT_SERVICE_DEFINE(sensor_svc,
											 BT_GATT_PRIMARY_SERVICE(&svc_uuid),
											 BT_GATT_CHARACTERISTIC(&chr_uuid.uuid,
																							BT_GATT_CHRC_NOTIFY | BT_GATT_CHRC_READ,
																							BT_GATT_PERM_READ,
																							read_frame, NULL, &frame),
											 BT_GATT_CCC(ccc_cfg_changed, BT_GATT_PERM_READ | BT_GATT_PERM_WRITE));

#define SENSOR_CHAR_VALUE_ATTR (&sensor_svc.attrs[2])

static void connected(struct bt_conn *conn, uint8_t err)
{
	if (err)
	{
		printk("Connection failed (err %u)\n", err);
	}
	else
	{
		printk("Connected\n");
	}
}

static void disconnected(struct bt_conn *conn, uint8_t reason)
{
	printk("Disconnected (reason %u)\n", reason);
	notify_enabled = false;
}

BT_CONN_CB_DEFINE(conn_callbacks) = {
		.connected = connected,
		.disconnected = disconnected,
};

static void bt_ready(int err)
{
	if (err)
	{
		printk("Bluetooth init failed (err %d)\n", err);
		return;
	}

	printk("Bluetooth initialized\n");

	err = bt_le_adv_start(BT_LE_ADV_CONN_NAME, ad, ARRAY_SIZE(ad), NULL, 0);
	if (err)
	{
		printk("Advertising failed to start (err %d)\n", err);
		return;
	}

	printk("Advertising as \"%s\"\n", DEVICE_NAME);
}

void main(void)
{
	printk("Starting BLE Sensor Peripheral\n");

	if (!device_is_ready(imu))
	{
		printk("MPU6050 device not ready\n");
		return;
	}

	int err = bt_enable(bt_ready);
	if (err)
	{
		printk("Bluetooth init failed (err %d)\n", err);
		return;
	}

	configure_saadc();

	while (1)
	{
		frame.t_s = ((uint32_t)k_uptime_get() / 1000);

		int16_t flex[FLEX_CH_COUNT];
		adc_get_latest_samples(flex);

		frame.flex1 = flex[0];
		frame.flex2 = flex[1];
		frame.flex3 = flex[2];
		frame.flex4 = flex[3];
		frame.flex5 = flex[4];

		printk("ADC: %d, %d, %d, %d, %d\n",
					 flex[0], flex[1], flex[2], flex[3], flex[4]);

		err = read_mpu6050_frame();
		if (err)
		{
			// printk("MPU6050 read failed (err %d)\n", err);

			frame.AccelX = 0;
			frame.AccelY = 0;
			frame.AccelZ = 0;
			frame.GyroX = 0;
			frame.GyroY = 0;
			frame.GyroZ = 0;
			frame.Pitch = 0;
			frame.Roll = 0;
		}
		else
		{
			printk("IMU Accel: %d, %d, %d milli-m/s^2\n",
						 frame.AccelX, frame.AccelY, frame.AccelZ);

			printk("IMU Gyro: %d, %d, %d milli-rad/s\n",
						 frame.GyroX, frame.GyroY, frame.GyroZ);
		}

		if (notify_enabled)
		{
			int nerr = bt_gatt_notify(NULL, SENSOR_CHAR_VALUE_ATTR, &frame, sizeof(frame));
			if (nerr)
			{
				printk("Notify failed (err %d)\n", nerr);
			}
		}

		k_sleep(K_MSEC(1000));
	}
}