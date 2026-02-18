#include <kernel.h>
#include <sys/printk.h>
#include <sys/byteorder.h>
#include <zephyr/types.h>
#include <random/rand32.h>

#include <bluetooth/bluetooth.h>
#include <bluetooth/hci.h>
#include <bluetooth/conn.h>
#include <bluetooth/gatt.h>
#include <stdlib.h>
#include <time.h>

#define DEVICE_NAME CONFIG_BT_DEVICE_NAME
#define DEVICE_NAME_LEN (sizeof(DEVICE_NAME) - 1)

// Advertising
static const struct bt_data ad[] = {
		BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR))};

// Char UUID:    7e2a2b11-5b9a-4c8f-9d6a-2f6f2a4f8b01

static struct bt_uuid_128 svc_uuid = BT_UUID_INIT_128(
		0x01, 0x8b, 0x4f, 0x2a, 0x6f, 0x2f, 0x6a, 0x9d, 0x8f, 0x4c, 0x9a, 0x5b, 0x10, 0x2b, 0x2a, 0x7e);

static struct bt_uuid_128 chr_uuid = BT_UUID_INIT_128(
		0x01, 0x8b, 0x4f, 0x2a, 0x6f, 0x2f, 0x6a, 0x9d, 0x8f, 0x4c, 0x9a, 0x5b, 0x11, 0x2b, 0x2a, 0x7e);

struct __packed sensor_frame
{
	uint32_t t_s; // device uptime in s

	uint32_t flex1;
	uint32_t flex2;
	uint32_t flex3;
	uint32_t flex4;
	uint32_t flex5;

	uint32_t AccelX;
	uint32_t AccelY;
	uint32_t AccelZ;
	uint32_t GyroX;
	uint32_t GyroY;
	uint32_t GyroZ;
	uint32_t Pitch;
	uint32_t Roll;
	uint32_t Yaw;
};

static struct sensor_frame frame;
static bool notify_enabled;

// Called when the client enables/disables notifications */
static void ccc_cfg_changed(const struct bt_gatt_attr *attr, uint16_t value)
{
	notify_enabled = (value == BT_GATT_CCC_NOTIFY);
	printk("Notify %s\n", notify_enabled ? "ENABLED" : "DISABLED");
}

// Read handler (lets you read the last frame)
static ssize_t read_frame(struct bt_conn *conn,
													const struct bt_gatt_attr *attr,
													void *buf, uint16_t len, uint16_t offset)
{
	const struct sensor_frame *f = attr->user_data;
	return bt_gatt_attr_read(conn, attr, buf, len, offset, f, sizeof(*f));
}

// Define the BT service. attr order matters for bt_gatt_notify() pointer later.
BT_GATT_SERVICE_DEFINE(sensor_svc,
											 BT_GATT_PRIMARY_SERVICE(&svc_uuid),
											 BT_GATT_CHARACTERISTIC(&chr_uuid.uuid,
																							BT_GATT_CHRC_NOTIFY | BT_GATT_CHRC_READ,
																							BT_GATT_PERM_READ,
																							read_frame, NULL, &frame),
											 BT_GATT_CCC(ccc_cfg_changed, BT_GATT_PERM_READ | BT_GATT_PERM_WRITE));

/* Attribute index helper:
 * attrs[0] = primary service
 * attrs[1] = characteristic declaration
 * attrs[2] = characteristic value (THIS is what we notify)
 * attrs[3] = CCC descriptor
 */
#define SENSOR_CHAR_VALUE_ATTR (&sensor_svc.attrs[2])

// Connection callbacks (debugging)
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

// Bluetooth ready + main loop
static void bt_ready(int err)
{
	if (err)
	{
		printk("Bluetooth init failed (err %d)\n", err);
		return;
	}

	printk("Bluetooth initialized\n");

	// Connectable advertising with name included
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
	int err;

	printk("Starting BLE Sensor Peripheral\n");

	err = bt_enable(bt_ready);
	if (err)
	{
		printk("Bluetooth init failed (err %d)\n", err);
		return;
	}

	// Periodically update and notify
	while (1)
	{
		// k_uptime_get() returns the time in milliseconds, but the deivce is currently only
		//  broadcasting once per second, so it displays the time in uptime seconds
		frame.t_s = ((uint32_t)k_uptime_get() / 1000);

		// Sensor Value Readings, currently randomized just to show functionality of BLEAK connection
		frame.flex1 = (uint32_t)(sys_rand32_get() % 10000);
		frame.flex2 = (uint32_t)(sys_rand32_get() % 10000);
		frame.flex3 = (uint32_t)(sys_rand32_get() % 10000);
		frame.flex4 = (uint32_t)(sys_rand32_get() % 10000);
		frame.flex5 = (uint32_t)(sys_rand32_get() % 10000);

		frame.AccelX = (uint32_t)(sys_rand32_get() % 10000);
		frame.AccelY = (uint32_t)(sys_rand32_get() % 10000);
		frame.AccelZ = (uint32_t)(sys_rand32_get() % 10000);

		frame.GyroX = (uint32_t)(sys_rand32_get() % 10000);
		frame.GyroY = (uint32_t)(sys_rand32_get() % 10000);
		frame.GyroZ = (uint32_t)(sys_rand32_get() % 10000);

		frame.Pitch = (uint32_t)(sys_rand32_get() % 10000);
		frame.Roll = (uint32_t)(sys_rand32_get() % 10000);
		frame.Yaw = (uint32_t)(sys_rand32_get() % 10000);

		if (notify_enabled)
		{
			int nerr = bt_gatt_notify(
					NULL, SENSOR_CHAR_VALUE_ATTR,
					&frame, sizeof(frame));

			if (nerr)
			{
				printk("Notify failed (err %d)\n", nerr);
			}
		}

		// 1000 ms pause --> 1 Hz; adjust as needed
		k_sleep(K_MSEC(1000));
	}
}
