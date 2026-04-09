import asyncio
import struct
import csv
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk

from bleak import BleakClient, BleakScanner

DEVICE_NAME = "ASL Glove"
CHAR_UUID = "7e2a2b11-5b9a-4c8f-9d6a-2f6f2a4f8b01"
ADDRESS = "DF:0B:74:62:D9:52"  # nrf52 Dev Kit Address
# ADDRESS = "EB:BC:F6:CB:17:09"  # Custom PCB Address

SCAN_TIMEOUT_S = 15.0
CONNECT_TIMEOUT_S = 30.0
RECONNECT_DELAY_S = 2.0

LOG_TO_CSV = True
OUTPUT_DIR = "ASL_Recordings"

CSV_HEADER = [
    "t_ms",
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
]

FIELD_NAMES = [
    "t_ms",
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
    "DoneCount",
]

# FRAME_FMT = "<IiiiiiiiiiiiiI"
FRAME_FMT = "<IiiiiiiiiiiiiiI"
FRAME_LEN = struct.calcsize(FRAME_FMT)


def sanitize_sign_name(name: str) -> str:
    cleaned = "".join(
        ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in name.strip()
    )
    return cleaned if cleaned else "Sign"


def get_sign_dir(sign_name: str) -> str:
    return os.path.join(OUTPUT_DIR, sign_name)


def ensure_output_dir(sign_name: str):
    os.makedirs(get_sign_dir(sign_name), exist_ok=True)


def build_csv_path(sign_name: str, file_number: int) -> str:
    sign_dir = get_sign_dir(sign_name)
    filename = f"{sign_name}_{file_number}.csv"
    return os.path.join(sign_dir, filename)


def write_csv_header(path: str):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)


def append_csv_row(path: str, row):
    with open(path, "a", newline="") as f:
        csv.writer(f).writerow(row)


def decode_sensor_frame(data: bytes):
    if len(data) != FRAME_LEN:
        return None
    return struct.unpack(FRAME_FMT, data)


class SensorGUI:
    def __init__(self, root: tk.Tk, sign_name: str):
        self.root = root
        self.root.title("ASL Glove Realtime Monitor")
        self.root.geometry("700x760")

        self.sign_name = sanitize_sign_name(sign_name)
        self.ui_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.packet_count = 0

        self.current_file_number = 1
        self.current_csv_path = ""
        self.last_done_count = None

        self.status_var = tk.StringVar(value="Status: Idle")
        self.packet_var = tk.StringVar(value="Packets received: 0")
        self.file_var = tk.StringVar(value="Current file: ---")
        self.sign_var = tk.StringVar(value=f"Sign: {self.sign_name}")

        self.value_vars = {}
        for field in FIELD_NAMES:
            self.value_vars[field] = tk.StringVar(value="---")

        ensure_output_dir(self.sign_name)
        self.start_new_csv_file()

        self.build_gui()

        self.worker_thread = threading.Thread(
            target=self.start_ble_worker,
            daemon=True,
        )
        self.worker_thread.start()

        self.root.after(50, self.process_queue)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_gui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        title = ttk.Label(
            main, text="ASL Glove Sensor Values", font=("Segoe UI", 20, "bold")
        )
        title.pack(pady=(0, 10))

        status_label = ttk.Label(
            main, textvariable=self.status_var, font=("Segoe UI", 12)
        )
        status_label.pack(anchor="w")

        packet_label = ttk.Label(
            main, textvariable=self.packet_var, font=("Segoe UI", 12)
        )
        packet_label.pack(anchor="w")

        sign_label = ttk.Label(main, textvariable=self.sign_var, font=("Segoe UI", 12))
        sign_label.pack(anchor="w")

        file_label = ttk.Label(main, textvariable=self.file_var, font=("Segoe UI", 12))
        file_label.pack(anchor="w", pady=(0, 10))

        grid = ttk.Frame(main)
        grid.pack(fill="both", expand=True)

        for row, field in enumerate(FIELD_NAMES):
            ttk.Label(
                grid,
                text=f"{field}:",
                width=12,
                font=("Segoe UI", 14, "bold"),
            ).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)

            ttk.Label(
                grid,
                textvariable=self.value_vars[field],
                width=20,
                font=("Segoe UI", 14),
            ).grid(row=row, column=1, sticky="w", pady=4)

    def start_new_csv_file(self):
        self.current_csv_path = build_csv_path(self.sign_name, self.current_file_number)
        write_csv_header(self.current_csv_path)
        self.file_var.set(f"Current file: {self.current_csv_path}")

    def rollover_csv_file(self):
        self.current_file_number += 1
        self.start_new_csv_file()
        self.status_var.set(f"Status: New file created -> {self.current_csv_path}")

    def process_queue(self):
        while True:
            try:
                msg_type, payload = self.ui_queue.get_nowait()
            except queue.Empty:
                break

            if msg_type == "status":
                self.status_var.set(f"Status: {payload}")

            elif msg_type == "frame":
                self.packet_count += 1
                self.packet_var.set(f"Packets received: {self.packet_count}")

                for i, field in enumerate(FIELD_NAMES):
                    self.value_vars[field].set(str(payload[i]))

                done_count = payload[-1]

                if self.last_done_count is None:
                    self.last_done_count = done_count
                elif done_count > self.last_done_count:
                    self.last_done_count = done_count
                    self.rollover_csv_file()

                if LOG_TO_CSV:
                    append_csv_row(self.current_csv_path, payload[:-1])

            elif msg_type == "error":
                self.status_var.set(f"Status: ERROR - {payload}")

        if not self.stop_event.is_set():
            self.root.after(50, self.process_queue)

    def on_close(self):
        self.stop_event.set()
        self.root.destroy()

    def start_ble_worker(self):
        asyncio.run(self.ble_main())

    async def run_session(self):
        disconnected_evt = asyncio.Event()

        def on_disconnect(client: BleakClient):
            self.ui_queue.put(("status", "Disconnected"))
            disconnected_evt.set()

        def on_notify(_handle, data: bytearray):
            decoded = decode_sensor_frame(bytes(data))
            if decoded is None:
                return

            self.ui_queue.put(("frame", decoded))

        self.ui_queue.put(("status", f"Scanning for {ADDRESS}"))
        device = await BleakScanner.find_device_by_address(
            ADDRESS, timeout=SCAN_TIMEOUT_S
        )

        if device is None:
            self.ui_queue.put(("status", f"Could not find device at {ADDRESS}"))
            return

        self.ui_queue.put(("status", f"Found {device.name} ({device.address})"))

        async with BleakClient(
            device,
            timeout=CONNECT_TIMEOUT_S,
            disconnected_callback=on_disconnect,
        ) as client:
            if not client.is_connected:
                self.ui_queue.put(("status", "Disconnected before notify start"))
                return

            self.ui_queue.put(("status", f"Connected to {DEVICE_NAME}"))
            await client.start_notify(CHAR_UUID, on_notify)
            self.ui_queue.put(("status", "Receiving notifications"))

            try:
                while (
                    client.is_connected
                    and not disconnected_evt.is_set()
                    and not self.stop_event.is_set()
                ):
                    await asyncio.sleep(0.1)
            finally:
                try:
                    if client.is_connected:
                        await client.stop_notify(CHAR_UUID)
                except Exception:
                    pass

    async def ble_main(self):
        while not self.stop_event.is_set():
            try:
                await self.run_session()
            except Exception as e:
                self.ui_queue.put(("error", repr(e)))

            if self.stop_event.is_set():
                break

            self.ui_queue.put(("status", f"Reconnecting in {RECONNECT_DELAY_S}s"))
            await asyncio.sleep(RECONNECT_DELAY_S)


def main():
    sign_name = input("Enter ASL sign name: ").strip()
    if not sign_name:
        sign_name = "Sign"

    root = tk.Tk()
    app = SensorGUI(root, sign_name)
    root.mainloop()


if __name__ == "__main__":
    main()
