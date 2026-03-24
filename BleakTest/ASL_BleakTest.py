import asyncio
import struct
import csv
import os
from bleak import BleakClient, BleakScanner

DEVICE_NAME = "ASL Glove"
CHAR_UUID = "7e2a2b11-5b9a-4c8f-9d6a-2f6f2a4f8b01"
ADDRESS = "DF:0B:74:62:D9:52"

SCAN_TIMEOUT_S = 15.0
CONNECT_TIMEOUT_S = 30.0
RECONNECT_DELAY_S = 2.0

file_path = "sensorOutputs.csv"

CSV_HEADER = [
    "t_s",
    "Flex1",
    "Flex2",
    "Flex3",
    "Flex4",
    "Flex5",
    "AccelX",
    "AccelY",
    "AccelZ",
    "GyroX",
    "GyroY",
    "GyroZ",
    "Pitch",
    "Roll",
    "Yaw",
]

FRAME_FMT = "<IiiiiiIIIIIIIII"
FRAME_LEN = struct.calcsize(FRAME_FMT)


# Check for csv header, if it is a new file add one. If not, do nothing.
def writeCSVHeader(path: str):
    needsHeader = (not os.path.exists(path)) or (os.path.getsize(path) == 0)
    if needsHeader:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)


# Convert the notification payload (raw bytes) into 15 Python integers.
def decode_sensor_frame(data: bytes):
    if len(data) != FRAME_LEN:
        return None
    return struct.unpack(FRAME_FMT, data)


async def run_session():
    disconnected_evt = asyncio.Event()

    # Used to exit read loop if the device disconnects.
    def on_disconnect(client: BleakClient):
        print("\n*** DISCONNECTED from board ***\n")
        disconnected_evt.set()

    # Called when the nRF sends a GATT notification on the UUID.
    # Decodes bytes from the notification and appends them to the csv.
    def on_notify(_handle, data: bytearray):
        decoded = decode_sensor_frame(bytes(data))
        if decoded is None:
            print(f"Notify ({len(data)}B): {data.hex()}")
            return

        with open(file_path, "a", newline="") as f:
            csv.writer(f).writerow(decoded)

        t_s = decoded[0]
        print(f"Appended reading at t={t_s}s to {file_path}")

    # Find the exact device by address before each connection attempt.
    device = await BleakScanner.find_device_by_address(ADDRESS, timeout=SCAN_TIMEOUT_S)

    if device is None:
        print(f"Could not find device at {ADDRESS}")
        return

    print(f"Found device: {device.name} ({device.address})")

    async with BleakClient(
        device,
        timeout=CONNECT_TIMEOUT_S,
        disconnected_callback=on_disconnect,
    ) as client:
        print(f"Connected to {DEVICE_NAME}: {client.is_connected}")

        if not client.is_connected:
            print("Disconnected before notifications could start")
            return

        await client.start_notify(CHAR_UUID, on_notify)
        print("Listening (CTRL+C to stop)\n")

        try:
            while client.is_connected and not disconnected_evt.is_set():
                await asyncio.sleep(0.25)
        finally:
            try:
                if client.is_connected:
                    await client.stop_notify(CHAR_UUID)
                    print("Notifications stopped")
            except Exception as e:
                print(f"stop_notify failed after disconnect {e!r}")


async def main():
    writeCSVHeader(file_path)

    while True:
        try:
            await run_session()
        except Exception as e:
            print(f"Session failed: {e!r}")

        # Give Windows and the peripheral a moment before reconnecting.
        print(f"Waiting {RECONNECT_DELAY_S}s before reconnect attempt...\n")
        await asyncio.sleep(RECONNECT_DELAY_S)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass