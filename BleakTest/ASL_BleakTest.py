import asyncio
import struct
import csv
import os
from bleak import BleakClient

DEVICE_NAME = "ASL Glove"
CHAR_UUID = "7e2a2b11-5b9a-4c8f-9d6a-2f6f2a4f8b01"  # set to your notify char UUID once you see it printed
ADDRESS = "DF:0B:74:62:D9:52"  # Address of the DK board for BLE connection
SCAN_TIMEOUT_S = 3.0
file_path = "sensorOutputs.csv"

CSV_HEARER = [
    "t_s",
    "Flex1",
    "Flex2",
    "Flex3",
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

listenMsg = 0

FRAME_FMT = "<" + "I" * 15  # 15 uint32 little-endian
FRAME_LEN = struct.calcsize(FRAME_FMT)  # 60


# Check for csv header, if its a new file add one. If not, does nothing
def writeCSVHeader(path: str):
    # Checks to see if the file already has a csv header.
    needsHeader = (not os.path.exists(path)) or (os.path.getsize(path) == 0)
    if needsHeader:
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEARER)


# Convert the notifcation payload (raw bytes) into 15 python integers
def decode_sensor_frame(data: bytes):
    # uint32 t_s + 3*int16 = 10 bytes
    if len(data) != FRAME_LEN:
        return None
    return struct.unpack(FRAME_FMT, data)


async def main():
    writeCSVHeader(file_path)

    disconnected_evt = asyncio.Event()

    # Used to exit read loop if the device disconnects
    def on_disconnect(client: BleakClient):
        print("\n*** DISCONNECTED from board ***\n")
        disconnected_evt.set()

    # Called when nrf sends a GATT notification on the UUID. Decodes bytes
    # from notification and appends them to the csv
    def on_notify(_handle, data: bytearray):
        decoded = decode_sensor_frame(bytes(data))
        if decoded is None:
            print(f"Notify ({len(data)}B): {data.hex()}")
            return

        # Append the decoded data onto the csv
        with open(file_path, "a", newline="") as f:
            csv.writer(f).writerow(decoded)

        # Proof of csv updated in console log
        t_s = decoded[0]
        print(f"Appended reading at t={t_s}s to {file_path}")

    # Connect to specific dev kit using its {ADDRESS}
    # Start notifications when connected
    # Stop notifications when disconnected
    async with BleakClient(
        ADDRESS, timeout=10.0, disconnected_callback=on_disconnect
    ) as client:
        print(f"Connected to {DEVICE_NAME}:", client.is_connected)

        try:
            await client.start_notify(CHAR_UUID, on_notify)
        except Exception as e:
            print(f"\n*** Failed to start notifications: {e!r} ***\n")
            return

        print("Listening (CTRL+C to stop) \n")

        try:
            while (client.is_connected) and (not disconnected_evt.is_set()):
                await asyncio.sleep(0.25)
        finally:
            # Log to console when the device disconnects and notifications stop
            try:
                await client.stop_notify(CHAR_UUID)
                print("Notifications Stopped")

            except Exception as e:
                # If the device disconnects from hardware disconnect
                print(f"Stop_notify failed from disconnect {e!r}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
