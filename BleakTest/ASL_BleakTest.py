import asyncio
import struct
from bleak import BleakScanner, BleakClient

DEVICE_NAME = "ASL Glove Testing"
CHAR_UUID = "7e2a2b11-5b9a-4c8f-9d6a-2f6f2a4f8b01"  # set to your notify char UUID once you see it printed
SCAN_TIMEOUT_S = 3.0

listenMsg = 0


def decode_sensor_frame(data: bytes):
    # uint32 t_s + 3*int16 = 10 bytes
    if len(data) < 10:
        return None
    return struct.unpack_from("<Ihhh", data, 0)


async def main():
    print(f"Scanning for '{DEVICE_NAME}' for {SCAN_TIMEOUT_S:.1f}s...")
    devices = await BleakScanner.discover(timeout=SCAN_TIMEOUT_S)

    # Uncomment below lines if you want to see all possbile BT connections
    # for d in devices:
    #     print(f"  - {d.name!r:20}  {d.address}")

    dev = next((d for d in devices if d.name == DEVICE_NAME), None)
    if not dev:
        print("Device not found.")
        return

    print(f"Found target: {dev.name} @ {dev.address}")
    print("Connecting...")

    # Used to exit read loop if the device disconnects
    disconnected_evt = asyncio.Event()

    def on_disconnect(client: BleakClient):
        print("\n*** DISCONNECTED from board ***\n")
        disconnected_evt.set()

    def on_notify(_, data: bytearray):
        decoded = decode_sensor_frame(bytes(data))
        if decoded is None:
            print(f"Notify ({len(data)}B): {data.hex()}")
            return
        if listenMsg == 1:
            t_s, s0, s1, s2 = decoded
            print(f"t={t_s:>4} s | s0={s0:>6} s1={s1:>6} s2={s2:>6}")

    async with BleakClient(
        dev.address, timeout=10.0, disconnected_callback=on_disconnect
    ) as client:
        print("Connected:", client.is_connected)

        # List available services from device
        services = client.services
        if services is None:
            # give a pause if discovery is still finishing
            await asyncio.sleep(0.5)
            services = client.services

        print("\nServices/Characteristics discovered:")
        for svc in services:
            print(f"Service {svc.uuid}")
            for ch in svc.characteristics:
                props = ",".join(ch.properties)
                print(f"  Char {ch.uuid}  [{props}]")

        print(f"\nSubscribing to notifications on {CHAR_UUID} ...")
        try:
            await client.start_notify(CHAR_UUID, on_notify)
        except Exception as e:
            print(
                f"\n*** Failed to start notifications (likely disconnected): {e!r} ***\n"
            )
            return

        print("Listening (Ctrl+C to stop)...\n")
        listenMsg = 1
        try:
            while True:
                # Wake up every 0.25s or immediately if we get disconnected
                if disconnected_evt.is_set() or not client.is_connected:
                    print("Exiting listen loop")
                    break
                await asyncio.sleep(0.25)

        finally:
            try:
                await client.stop_notify(CHAR_UUID)
                print("Stopped Notifications.")
            except Exception as e:
                print(f"stop_notify falied after disconnect: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
