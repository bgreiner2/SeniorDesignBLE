import asyncio
import struct
import csv
import os
from bleak import BleakClient, BleakScanner

DEVICE_NAME = "ASL_Glove"
CHAR_UUID = "7e2a2b11-5b9a-4c8f-9d6a-2f6f2a4f8b01"
ADDRESS = "EB:BC:F6:CB:17:09"  # Custom PCB address

SCAN_TIMEOUT_S = 15.0
CONNECT_TIMEOUT_S = 30.0
RECONNECT_DELAY_S = 2.0

file_path = "sensorOutputs.csv"

CSV_HEADER = [
    "t_ms",
    "imu_ok",
    "chip_id",
    "status",
    "acc_x",
    "acc_y",
    "acc_z",
    "gyr_x",
    "gyr_y",
    "gyr_z",
]

# imu_debug_frame layout from the current Arduino BLE code:
# uint32_t t_ms
# uint8_t  imu_ok
# uint8_t  chip_id
# uint16_t status
# int16_t  acc_x
# int16_t  acc_y
# int16_t  acc_z
# int16_t  gyr_x
# int16_t  gyr_y
# int16_t  gyr_z
FRAME_FMT = "<IBBHhhhhhh"
FRAME_LEN = struct.calcsize(FRAME_FMT)


def write_csv_header(path: str):
    needs_header = (not os.path.exists(path)) or (os.path.getsize(path) == 0)
    if needs_header:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)


def decode_sensor_frame(data: bytes):
    if len(data) != FRAME_LEN:
        return None
    return struct.unpack(FRAME_FMT, data)


async def find_target_device():
    # First try the known BLE address.
    device = await BleakScanner.find_device_by_address(ADDRESS, timeout=SCAN_TIMEOUT_S)
    if device is not None:
        return device

    # Fallback: scan by advertised name.
    devices = await BleakScanner.discover(timeout=SCAN_TIMEOUT_S)
    for dev in devices:
        if dev.name == DEVICE_NAME:
            return dev

    return None


async def run_session():
    disconnected_evt = asyncio.Event()

    def on_disconnect(client: BleakClient):
        print("\n*** DISCONNECTED from board ***\n")
        disconnected_evt.set()

    def on_notify(_handle, data: bytearray):
        decoded = decode_sensor_frame(bytes(data))
        if decoded is None:
            print(f"Notify ({len(data)}B): {data.hex()}")
            return

        with open(file_path, "a", newline="") as f:
            csv.writer(f).writerow(decoded)

        t_ms, imu_ok, chip_id, status, ax, ay, az, gx, gy, gz = decoded

        print(
            f"t_ms={t_ms} "
            f"imu_ok={imu_ok} "
            f"chip_id=0x{chip_id:02X} "
            f"status=0x{status:04X} "
            f"acc=({ax}, {ay}, {az}) "
            f"gyr=({gx}, {gy}, {gz})"
        )

    print(f"Scanning for {DEVICE_NAME}...")
    device = await find_target_device()

    if device is None:
        print(f"Could not find {DEVICE_NAME} at {ADDRESS}")
        return

    print(f"Found device: {device.name} ({device.address})")
    print("Connecting...")

    client = BleakClient(
        device,
        timeout=CONNECT_TIMEOUT_S,
        disconnected_callback=on_disconnect,
        winrt={
            "address_type": "random",
            "use_cached_services": False,
        },
    )

    try:
        await client.connect()
        print(f"Connected to {DEVICE_NAME}: {client.is_connected}")

        if not client.is_connected:
            print("Disconnected before GATT setup")
            return

        print("Reading characteristic once...")
        data = await client.read_gatt_char(CHAR_UUID)

        decoded = decode_sensor_frame(bytes(data))
        if decoded is None:
            print(f"Initial read ({len(data)}B): {bytes(data).hex()}")
        else:
            with open(file_path, "a", newline="") as f:
                csv.writer(f).writerow(decoded)

            t_ms, imu_ok, chip_id, status, ax, ay, az, gx, gy, gz = decoded
            print(
                "Initial read: "
                f"t_ms={t_ms} "
                f"imu_ok={imu_ok} "
                f"chip_id=0x{chip_id:02X} "
                f"status=0x{status:04X} "
                f"acc=({ax}, {ay}, {az}) "
                f"gyr=({gx}, {gy}, {gz})"
            )

        print("Starting notifications...")
        await client.start_notify(CHAR_UUID, on_notify)
        print("Listening (CTRL+C to stop)\n")

        while client.is_connected and not disconnected_evt.is_set():
            await asyncio.sleep(0.25)

    finally:
        if client.is_connected:
            try:
                await client.stop_notify(CHAR_UUID)
                print("Notifications stopped")
            except Exception as e:
                print(f"stop_notify failed: {e!r}")

            try:
                await client.disconnect()
                print("Disconnected cleanly")
            except Exception as e:
                print(f"disconnect failed: {e!r}")


async def main():
    write_csv_header(file_path)

    while True:
        try:
            await run_session()
        except Exception as e:
            print(f"Session failed: {e!r}")

        print(f"Waiting {RECONNECT_DELAY_S}s before reconnect attempt...\n")
        await asyncio.sleep(RECONNECT_DELAY_S)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
