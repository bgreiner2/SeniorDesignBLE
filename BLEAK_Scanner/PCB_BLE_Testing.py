# # Working 5 ADC Channel, no IMU script
# import asyncio
# import struct
# from bleak import BleakClient, BleakScanner

# DEVICE_NAME = "ASL Glove BLE"
# CHAR_UUID = "7e2a2b11-5b9a-4c8f-9d6a-2f6f2a4f8b01"

# ADDRESS = "EB:BC:F6:CB:17:09"

# SCAN_TIMEOUT_S = 15.0
# CONNECT_TIMEOUT_S = 30.0
# RECONNECT_DELAY_S = 2.0

# # uint32_t t_ms + 6 int16_t values
# FRAME_FMT = "<Ihhhhhh"
# FRAME_LEN = struct.calcsize(FRAME_FMT)


# def decode_frame(data: bytes):
#     if len(data) != FRAME_LEN:
#         return None
#     return struct.unpack(FRAME_FMT, data)


# async def find_device():
#     if ADDRESS:
#         print(f"Scanning for device at address {ADDRESS}...")
#         return await BleakScanner.find_device_by_address(
#             ADDRESS, timeout=SCAN_TIMEOUT_S
#         )

#     print(f"Scanning for device named '{DEVICE_NAME}'...")
#     devices = await BleakScanner.discover(timeout=SCAN_TIMEOUT_S)

#     for device in devices:
#         if device.name == DEVICE_NAME:
#             return device

#     return None


# async def run_session():
#     disconnected_evt = asyncio.Event()

#     def on_disconnect(client: BleakClient):
#         print("Disconnected")
#         disconnected_evt.set()

#     def on_notify(_handle: int, data: bytearray):
#         decoded = decode_frame(bytes(data))
#         if decoded is None:
#             print(f"Bad frame length: got {len(data)} bytes, expected {FRAME_LEN}")
#             print(f"Raw data: {data.hex()}")
#             return

#         t_ms, ain0, ain1, ain2, ain3, ain4, ain5 = decoded
#         print(
#             f"t_ms={t_ms:10d}  "
#             f"AIN0={ain0:6d}  "
#             f"AIN1={ain1:6d}  "
#             f"AIN2={ain2:6d}  "
#             f"AIN3={ain3:6d}  "
#             f"AIN4={ain4:6d}  "
#             f"AIN5={ain5:6d}"
#         )

#     device = await find_device()
#     if device is None:
#         print("Could not find the custom PCB over BLE.")
#         return

#     print(f"Found device: {device.name} ({device.address})")

#     async with BleakClient(
#         device,
#         timeout=CONNECT_TIMEOUT_S,
#         disconnected_callback=on_disconnect,
#     ) as client:
#         if not client.is_connected:
#             print("Failed to connect")
#             return

#         print("Connected")
#         await client.start_notify(CHAR_UUID, on_notify)
#         print("Receiving notifications... Press Ctrl+C to stop.")

#         try:
#             while client.is_connected and not disconnected_evt.is_set():
#                 await asyncio.sleep(0.1)
#         finally:
#             try:
#                 if client.is_connected:
#                     await client.stop_notify(CHAR_UUID)
#             except Exception:
#                 pass


# async def main():
#     while True:
#         try:
#             await run_session()
#         except KeyboardInterrupt:
#             print("\nStopped by user")
#             break
#         except Exception as e:
#             print(f"Error: {e!r}")

#         print(f"Reconnecting in {RECONNECT_DELAY_S} seconds...")
#         await asyncio.sleep(RECONNECT_DELAY_S)


# if __name__ == "__main__":
#     asyncio.run(main())

import asyncio
import struct
from bleak import BleakClient, BleakScanner

DEVICE_NAME = "ASL Glove BLE"
CHAR_UUID = "7e2a2b11-5b9a-4c8f-9d6a-2f6f2a4f8b01"

ADDRESS = "EB:BC:F6:CB:17:09"

SCAN_TIMEOUT_S = 15.0
CONNECT_TIMEOUT_S = 30.0
RECONNECT_DELAY_S = 2.0
READ_INTERVAL_S = 0.2

FRAME_FMT = "<Ihh"
FRAME_LEN = struct.calcsize(FRAME_FMT)


def decode_frame(data: bytes):
    if len(data) != FRAME_LEN:
        return None
    return struct.unpack(FRAME_FMT, data)


async def find_device():
    print(f"Scanning for device at address {ADDRESS}...")
    return await BleakScanner.find_device_by_address(
        ADDRESS,
        timeout=SCAN_TIMEOUT_S,
    )


async def run_session():
    device = await find_device()
    if device is None:
        print("Could not find the custom PCB over BLE.")
        return

    print(f"Found device: {device.name} ({device.address})")

    async with BleakClient(device, timeout=CONNECT_TIMEOUT_S) as client:
        if not client.is_connected:
            print("Failed to connect")
            return

        print("Connected")
        print("Reading characteristic... Press Ctrl+C to stop.")

        while client.is_connected:
            data = await client.read_gatt_char(CHAR_UUID)
            decoded = decode_frame(bytes(data))

            if decoded is None:
                print(f"Bad frame length: got {len(data)} bytes, expected {FRAME_LEN}")
                print(f"Raw data: {data.hex()}")
            else:
                t_ms, status, ain0 = decoded
                print(f"t_ms={t_ms:10d}  " f"STATUS={status:6d}  " f"AIN0={ain0:6d}")

            await asyncio.sleep(READ_INTERVAL_S)


async def main():
    while True:
        try:
            await run_session()
        except KeyboardInterrupt:
            print("\nStopped by user")
            break
        except Exception as e:
            print(f"Error: {e!r}")

        print(f"Reconnecting in {RECONNECT_DELAY_S} seconds...")
        await asyncio.sleep(RECONNECT_DELAY_S)


if __name__ == "__main__":
    asyncio.run(main())
