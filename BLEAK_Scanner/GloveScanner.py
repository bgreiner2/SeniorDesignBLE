import asyncio
from bleak import BleakScanner

TARGET_NAME = "ASL_Glove_Test"


async def main():
    print("Scanning...\n")

    scanner = BleakScanner()
    await scanner.start()
    await asyncio.sleep(8.0)
    await scanner.stop()

    found = False

    for device, adv in scanner.discovered_devices_and_advertisement_data.values():
        name = device.name or "(no name)"
        print(f"name={name}")
        print(f"  address: {device.address}")
        print(f"  rssi:    {adv.rssi}")
        print(f"  uuids:   {adv.service_uuids}")
        print()

        if device.name == TARGET_NAME:
            found = True
            print("Matched target device:")
            print(f"  name:    {device.name}")
            print(f"  address: {device.address}")
            print(f"  rssi:    {adv.rssi}")
            print()

    if not found:
        print(f"Did not find device named {TARGET_NAME}")


asyncio.run(main())
