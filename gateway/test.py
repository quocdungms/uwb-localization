import asyncio
from queue import PriorityQueue

from bleak import BleakScanner, BleakClient
import struct
import socketio
import json
from datetime import datetime


from location import *
from utils import *
sio = socketio.AsyncClient()
SERVER_URL = "http://172.16.0.166:5000"

# UUIDs
LOCATION_DATA_UUID = "003bbdf2-c634-4b3d-ab56-7ec889b89a37"  # Location data UUID
OPERATION_MODE_UUID = "3f0afd88-7770-46b0-b5e7-9fc099598964"  # Operation mode UUID
LOCATION_DATA_MODE_UUID = "a02b947e-df97-4516-996a-1882521e0ead"  # Location data mode UUID for writing (0, 1, 2)
READ_INTERVAL = 2  # Interval in seconds to read data


async def send_data_to_server(data):
    """Gửi dữ liệu vị trí lên server qua Socket.IO."""
    try:
        await sio.emit("test send data to server", data)
    except Exception as e:
        print(f"Error sending data: {e}")


def bytearray_to_binary_list(byte_array):
    return [format(byte, '08b') for byte in byte_array]


def decode_raw_data(data):
    """
    Decode raw data based on the given format.
    :param data: Raw byte array from the characteristic.
    :return: Decoded data as a dictionary.
    """
    try:
        result = {}
        data_type = data[0]
        result["type"] = data_type

        if data_type == 2:  # Type 2: Position and Distances
            result.update(decode_location_mode_2(data))

        elif data_type == 1:  # Type 1: Distances Only
            result.update(decode_location_mode_1(data))

        elif data_type == 0:  # Type 0: Position Only
            if len(data) <= 13:
                print("Invalid Type 0 data: Expected 13 bytes")
                return None
            result.update(decode_location_mode_0(data))
        else:
            print(f"Unknown data type: {data_type}")

        return result

    except Exception as e:
        print(f"Error decoding data: {e}")
        return None


# async def write_value(client, value):
#     """
#     Write a single byte (0, 1, or 2) to the LOCATION_DATA_MODE_UUID characteristic.
#     """
#     try:
#         byte_value = bytes([value])  # Convert integer to 1-byte format
#         await client.write_gatt_char(LOCATION_DATA_MODE_UUID, byte_value)
#         print(f"Successfully wrote {value} to {LOCATION_DATA_MODE_UUID}")
#     except Exception as e:
#         print(f"Failed to write value {value} to {LOCATION_DATA_MODE_UUID}: {e}")

async def periodic_read(device):
    """
    Periodically read data from the specified characteristics.
    Reconnect to the device if disconnected.
    :param device: BLEDevice instance.
    """
    filename = f"ble_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    while True:
        try:
            async with BleakClient(device.address) as client:
                if not client.is_connected:
                    print(f"Failed to connect to {device.name or 'Unknown Device'} ({device.address})")
                    await asyncio.sleep(READ_INTERVAL)
                    continue

                print(f"Connected to {device.name or 'Unknown Device'} ({device.address})")

                writeData = bytearray(b'\x02')
                await client.write_gatt_char(LOCATION_DATA_MODE_UUID, writeData, response=True)
                print("Ghi dữ liệu thành công!")
                await client.disconnect()
                await asyncio.sleep(2)
                await client.connect()

                while True:
                    try:
                        # Đọc dữ liệu như trước
                        operation_mode_data = await client.read_gatt_char(OPERATION_MODE_UUID)
                        location_mode_data = await client.read_gatt_char(LOCATION_DATA_MODE_UUID)
                        data = await client.read_gatt_char(LOCATION_DATA_UUID)

                        decoded_data = decode_raw_data(data)
                        if decoded_data:
                            # Ghi dữ liệu vào file txt thay vì in ra màn hình
                            with open(filename, 'a', encoding='utf-8') as f:
                                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                f.write(f"[{timestamp}]\n")
                                f.write(f"Raw Data from {LOCATION_DATA_UUID}: {data}\n")
                                f.write(f"Decoded Data: {decoded_data}\n")
                                f.write("===========================================\n\n")

                            # Chỉ in thông báo cơ bản lên console
                            print(f"[{timestamp}] Data saved to {filename}")

                    except Exception as e:
                        print(f"Error reading characteristic: {e}")
                        break

                    await asyncio.sleep(READ_INTERVAL)

        except Exception as e:
            print(f"Reconnection failed for {device.name or 'Unknown Device'}: {e}")
            print("Retrying connection...")
            await asyncio.sleep(READ_INTERVAL)


async def main():
    """Kết nối với server & bắt đầu quét thiết bị."""
    try:
        await sio.connect(SERVER_URL)
        print("Connected to server")
    except Exception as e:
        print(f"Failed to connect: {e}")

    """
    Scan for BLE devices, allow the user to choose a device, write a value, and start periodic read.
    """
    while True:
        print("\nScanning for devices...")
        devices = await BleakScanner.discover()

        dw_devices = [d for d in devices if d.name and "DWCE07" in d.name]

        if not dw_devices:
            continue

        print(f"\nFound {len(dw_devices)} devices:")
        for i, device in enumerate(dw_devices, 1):
            print(f"{i}. {device.name} - {device.address}")

        try:
            selected_device = dw_devices[0]

            # Connect to the device and write a value before periodic reading
            async with BleakClient(selected_device.address) as client:
                if not client.is_connected:
                    print(f"Failed to connect to {selected_device.name} ({selected_device.address})")
                    continue

                # Ask user for a value to write
                # user_input = input("Enter 0, 1, or 2 to write before starting periodic read: ").strip()
                # if user_input in ["0", "1", "2"]:
                #     await write_value(client, int(user_input))

            print(f"\nStarting periodic read for device {selected_device.name} ({selected_device.address})...")
            await periodic_read(selected_device)
        except ValueError:
            print("Invalid input! Please enter a valid number or 'r' to rescan.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())
