import asyncio
from bleak import BleakScanner, BleakClient
import struct
import socketio
import json

# Server
sio = socketio.AsyncClient()
SERVER_URL = "http://172.16.0.166:5000"

# UUIDs
MAIN_CHARACTERISTIC_UUID = "003bbdf2-c634-4b3d-ab56-7ec889b89a37"
OPERATION_MODE_UUID = "3f0afd88-7770-46b0-b5e7-9fc099598964"
LOCATION_DATA_MODE_UUID = "a02b947e-df97-4516-996a-1882521e0ead"
READ_INTERVAL = 2  # Interval in seconds to read data
SELECTED_DEVICE_ADDRESS = "EB:52:53:F5:D5:90"


async def send_data_to_server(data):
    """Gửi dữ liệu vị trí lên server qua Socket.IO."""
    try:
        await sio.emit("test send data to server", data)
    except Exception as e:
        print(f"Error sending data: {e}")


def bytearray_to_binary_list(byte_array):
    return [format(byte, '08b') for byte in byte_array]


def parse_position_data(data):
    x, y, z = struct.unpack('<fff', data[1:13])
    quality_factor = data[13]
    # return {"position": {"x": round(x, 2), "y": round(y, 2), "z": round(z, 2)}, "position_quality": quality_factor}
    return {"position": {"x": format(x, ".2f"), "y": format(y, ".2f")}, "position_quality": quality_factor}


def parse_distance_data(data, offset):
    distances = []
    distance_count = data[offset]
    offset += 1
    for _ in range(distance_count):
        if offset + 7 > len(data):
            break
        node_id = struct.unpack('<H', data[offset:offset + 2])[0]
        distance = struct.unpack('<f', data[offset + 2:offset + 6])[0]
        quality = data[offset + 6]
        distances.append({"node_id": node_id, "distance": f"{distance:.2f} m", "quality": quality})
        offset += 7
    return {"distance_count": distance_count, "distances": distances}


def decode_raw_data(data):
    try:
        data_type = data[0]
        if data_type == 2:
            decoded = parse_position_data(data)
            decoded.update(parse_distance_data(data, 14))
        elif data_type == 1:
            decoded = parse_distance_data(data, 1)
        elif data_type == 0:
            decoded = parse_position_data(data)
        else:
            print(f"Unknown or invalid data type: {data_type}")
            return None
        return decoded
    except Exception as e:
        print(f"Error decoding data: {e}")
        return None


async def connect_and_read(device):
    async with BleakClient(device.address) as client:
        if not client.is_connected:
            print(f"Failed to connect to {device.name or 'Unknown'} ({device.address})")
            return
        print(f"Connected to {device.name or 'Unknown'} ({device.address})")

        while True:
            try:
                await client.write_gatt_char(LOCATION_DATA_MODE_UUID, bytearray(b'\x02'))
                data = await client.read_gatt_char(MAIN_CHARACTERISTIC_UUID)
                decoded_data = decode_raw_data(data)
                if decoded_data:
                    print(f"Decoded Data: {decoded_data}")
                    # await send_data_to_server(decoded_data)
            except Exception as e:
                print(f"Error reading characteristic: {e}")
                break
            await asyncio.sleep(READ_INTERVAL)


async def main():
    """Kết nối với server & quét thiết bị."""
    # try:
    #     await sio.connect(SERVER_URL)
    #     print("Connected to server")
    # except Exception as e:
    #     print(f"Failed to connect: {e}")

    print(f"Scanning for device {SELECTED_DEVICE_ADDRESS}...")
    while True:
        devices = await BleakScanner.discover()
        selected_device = next((d for d in devices if d.address == SELECTED_DEVICE_ADDRESS), None)
        if not selected_device:
            print(f"Device {SELECTED_DEVICE_ADDRESS} not found. Rescanning...")
            await asyncio.sleep(READ_INTERVAL)
            continue
        print(f"Found device {selected_device.name} ({selected_device.address}), attempting connection...")
        await connect_and_read(selected_device)


if __name__ == "_main_":
    asyncio.run(main())
