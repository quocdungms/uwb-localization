import json
import time
import requests
from datetime import datetime
from bleak import BleakClient, BleakScanner
from init import *
from dotenv import load_dotenv
import os
from location import *
load_dotenv()
sv_url = os.getenv("SV_URL") + ":" + os.getenv("PORT") + "/" + os.getenv("TOPIC")
# Đọc danh sách module từ file JSON
def load_modules(filename="module.json"):
    with open(filename, "r") as f:
        return json.load(f)


# Gửi dữ liệu lên server qua REST API
def send_to_server(data, server_url=sv_url):
    try:
        response = requests.post(server_url, json=data)
        print(f"Server Response: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Failed to send data: {e}")


# Hàm lấy dữ liệu từ module
async def get_module_data(mac_address):
    async with BleakClient(mac_address) as client:
        if await client.is_connected():
            # Đánh dấu module là active
            status = "active"

            # Đọc operation mode (ví dụ UUID của đặc tính BLE)
            operation_mode_uuid = OPERATION_MODE_UUID
            operation_mode_raw = await client.read_gatt_char(operation_mode_uuid)
            operation_mode_hex = operation_mode_raw.hex()

            # Đọc location data (ví dụ UUID của đặc tính BLE)
            location_uuid = LOCATION_DATA_UUID
            location_raw = await client.read_gatt_char(location_uuid)
            # location_hex = location_raw.hex()
            location_decoded = decode_location_data(location_raw)
            # # Kiểm tra số byte của location data
            # if len(location_raw) == 13 or len(location_raw) == 14:
            #     location_mode = location_raw[0]  # Byte đầu tiên là location mode
            # else:
            #     location_mode = None

            # Định dạng thời gian
            timestamp = datetime.now().isoformat()

            return {
                "id": mac_address,
                "operation": operation_mode_hex,
                "location": location_decoded,
                "status": status,
                "time": timestamp
            }
    return None


# Chương trình chính
async def main():
    modules = load_modules()

    for module in modules:
        mac = module["id"]
        name = module["name"]

        print(f"Scanning {name} ({mac})...")
        data = await get_module_data(mac)

        if data:
            data["name"] = name
            send_to_server(data)


# Chạy chương trình
import asyncio

asyncio.run(main())
