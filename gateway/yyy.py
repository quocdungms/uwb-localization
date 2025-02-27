import asyncio
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
def load_modules(filename="md.json"):
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


async def process_location_notify(mac_address, name, location_uuid):
    async with BleakClient(mac_address) as client:
        if not await client.is_connected():
            print(f"Failed to connect to {name} ({mac_address})")
            return

        print(f"Connected to {name} ({mac_address}), subscribing to location data...")

        # Buffer lưu giá trị X, Y, Z, Quality Factor
        buffer_x = []
        buffer_y = []
        buffer_z = []
        buffer_quality = []

        def notification_handler(_, data):
            location_decoded = decode_location_data(data)
            if location_decoded:
                # Thêm dữ liệu vào buffer
                buffer_x.append(location_decoded["X"])
                buffer_y.append(location_decoded["Y"])
                buffer_z.append(location_decoded["Z"])
                buffer_quality.append(location_decoded["Quality Factor"])

                # Giữ tối đa 5 giá trị
                if len(buffer_x) > 5:
                    buffer_x.pop(0)
                    buffer_y.pop(0)
                    buffer_z.pop(0)
                    buffer_quality.pop(0)

        # Đăng ký notify
        await client.start_notify(location_uuid, notification_handler)

        while True:
            await asyncio.sleep(1)  # Cứ mỗi giây kiểm tra buffer
            if len(buffer_x) >= 5:
                avg_x = sum(buffer_x) / 5
                avg_y = sum(buffer_y) / 5
                avg_z = sum(buffer_z) / 5
                avg_quality = sum(buffer_quality) // 5

                timestamp = datetime.now().isoformat()
                data = {
                    "name": name,
                    "id": mac_address,
                    "location": {
                        "X": avg_x,
                        "Y": avg_y,
                        "Z": avg_z,
                        "Quality Factor": avg_quality
                    },
                    "status": "active",
                    "time": timestamp
                }

                send_to_server(data)
# Chương trình chính
async def main():
    modules = load_modules()
    tasks = []

    for module in modules:
        if module["type"] == "tag":  # Chỉ nhận notify từ TAG
            mac = module["id"]
            name = module["name"]
            location_uuid = LOCATION_DATA_UUID  # Cần thay UUID đúng
            tasks.append(process_location_notify(mac, name, location_uuid))

    await asyncio.gather(*tasks)

# Chạy chương trình
asyncio.run(main())



# Chương trình chính
# async def main():
#     modules = load_modules()
#
#     for module in modules:
#         mac = module["id"]
#         name = module["name"]
#
#         print(f"Scanning {name} ({mac})...")
#         data = await get_module_data(mac)
#
#         if data:
#             data["name"] = name
#             send_to_server(data)
#
#
# # Chạy chương trình
# import asyncio
#
# asyncio.run(main())


