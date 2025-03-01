import asyncio
import json
import time
from typing import Dict, List
import aiohttp
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError
from datetime import datetime
from global_var import *
from location import *
from dotenv import load_dotenv
import os

import pytz


load_dotenv()
sv_url = os.getenv("SV_URL") + ":" + os.getenv("PORT") + "/" + os.getenv("TOPIC")
# UUID của BLE service và characteristic
NETWORK_NODE_SERVICE_UUID = "680c21d9-c946-4c1f-9c11-baa1c21329e7"
LABEL_CHAR_UUID = "00002a00-0000-1000-8000-00805f9b34fb"
OPERATION_MODE_CHAR_UUID = "3f0afd88-7770-46b0-b5e7-9fc099598964"
LOCATION_DATA_CHAR_UUID = "003bbdf2-c634-4b3d-ab56-7ec889b89a37"

# Địa chỉ API endpoint
API_URL = sv_url

# Danh sách lưu trữ dữ liệu từ notify của các tag
tag_data_storage = {}
module_info = {}  # Thêm dictionary để lưu thông tin tĩnh

# Giới hạn số lượng kết nối đồng thời
MAX_CONCURRENT_CONNECTIONS = 2
semaphore = asyncio.Semaphore(MAX_CONCURRENT_CONNECTIONS)


# Hàm tải danh sách module từ file module.json
def load_modules() -> List[Dict]:
    try:
        with open("module.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Không tìm thấy file module.json. Bắt đầu với danh sách rỗng.")
        return []
    except json.JSONDecodeError:
        print("Lỗi khi giải mã file module.json.")
        return []


# Giải mã operation mode để xác định loại thiết bị
def decode_operation_mode(op_mode: bytes) -> str:
    first_byte = op_mode[0]
    tag_or_anchor_bit = (first_byte >> 7) & 0x01
    return "anchor" if tag_or_anchor_bit == 1 else "tag"


# Chuyển dữ liệu bytes thành chuỗi hex
def bytes_to_hex(data: bytes) -> str:
    return data.hex()


# Xử lý dữ liệu vị trí từ notify
def process_location_data(data: bytes) -> str:
    if not data or len(data) < 1:
        return "no_data"
    mode = data[0]
    if mode == 0 and len(data) == 14:
        return decode_location_mode_0(data)
    elif mode == 1:
        return decode_location_mode_1(data)
    elif mode == 2 and len(data) >= 14:
        return decode_location_mode_2(data)
    else:
        print(f"Định dạng dữ liệu không mong đợi: {bytes_to_hex(data)}")
        return "invalid_data"


# Gửi dữ liệu lên server qua API với kiểm tra lỗi chi tiết
async def send_to_api(payload: Dict):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(API_URL, json=payload) as response:
                if response.status == 200:
                    print(f"Gửi dữ liệu thành công cho {payload['name']}")
                else:
                    print(f"Gửi dữ liệu thất bại cho {payload['name']}: Mã lỗi {response.status}")
                    if response.status == 404:
                        print("Endpoint không tồn tại. Vui lòng kiểm tra cấu hình server.")
        except aiohttp.ClientError as e:
            print(f"Lỗi khi gửi dữ liệu tới API: {e}")


# Callback xử lý dữ liệu từ notify
def notify_callback(sender: int, data: bytearray, mac: str):
    location = process_location_data(data)
    tz = pytz.timezone('Asia/Ho_Chi_Minh')
    current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    tag_data_storage[mac] = {
        "location": location,
        "time": current_time
    }


# Task gửi dữ liệu lên server mỗi giây
async def send_tag_data_periodically(mac: str, name: str):
    while True:
        if mac in tag_data_storage and mac in module_info:
            data = tag_data_storage[mac]
            payload = {
                "name": module_info[mac]["name"],
                "id": mac,
                "type": module_info[mac]["type"],
                "operation": module_info[mac]["operation_hex"],
                "location": data["location"],
                "status": "active",
                "time": data["time"]
            }
            await send_to_api(payload)
            del tag_data_storage[mac]
        await asyncio.sleep(1)


# Xử lý kết nối và notify cho tag với semaphore
async def handle_tag(module: Dict):
    async with semaphore:
        mac = module["id"]
        name = module["name"]
        print(f"Đang kết nối tới tag {name} ({mac})...")
        try:
            client = BleakClient(mac)
            await client.connect()
            print(f"Đã kết nối tới tag {name}")

            # Đọc label và operation_mode sau khi kết nối
            label = await client.read_gatt_char(LABEL_CHAR_UUID)
            operation_mode = await client.read_gatt_char(OPERATION_MODE_CHAR_UUID)
            decoded_type = decode_operation_mode(operation_mode)
            operation_hex = bytes_to_hex(operation_mode)
            name = label.decode("utf-8", errors="ignore") if label else module["name"]

            # Lưu thông tin vào module_info
            module_info[mac] = {
                "name": name,
                "type": decoded_type,
                "operation_hex": operation_hex
            }

            await client.start_notify(LOCATION_DATA_CHAR_UUID, lambda sender, data: notify_callback(sender, data, mac))
            send_task = asyncio.create_task(send_tag_data_periodically(mac, name))
            while True:
                await asyncio.sleep(1)
                if not client.is_connected:
                    print(f"Kết nối với tag {name} đã bị ngắt")
                    break
            send_task.cancel()
        except BleakError as e:
            print(f"Lỗi BLE với tag {name}: {e}")
            module_info[mac] = {
                "name": module["name"],
                "type": "unknown",
                "operation_hex": "unknown"
            }
        except Exception as e:
            print(f"Lỗi không mong đợi với tag {name}: {e}")
        finally:
            await asyncio.sleep(0.5)  # Thêm độ trễ sau khi kết nối


# Xử lý module anchor (đọc dữ liệu một lần) với semaphore
async def handle_anchor(module: Dict):
    async with semaphore:  # Giả sử semaphore đã được định nghĩa ở ngoài
        mac = module["id"]
        name = module["name"]
        print(f"Đang kết nối tới anchor {name} ({mac})...")

        # Thiết lập số lần thử kết nối
        retry_count = 5
        client = None

        # Thử kết nối tối đa 3 lần
        while retry_count > 0:
            try:
                client = BleakClient(mac)
                await client.connect()
                print(f"Đã kết nối tới anchor {name} sau {3 - retry_count + 1} lần thử")
                break  # Thoát vòng lặp nếu kết nối thành công
            except BleakError as e:
                print(f"Lỗi kết nối tới anchor {name}: {e}")
                retry_count -= 1
                if retry_count > 0:
                    print(f"Thử lại sau 3 giây... ({retry_count} lần thử còn lại)")
                    await asyncio.sleep(3)
                else:
                    print(f"Không thể kết nối tới anchor {name} sau 3 lần thử")
                    # Gửi payload với status "disable" nếu hết lượt thử
                    tz = pytz.timezone('Asia/Ho_Chi_Minh')
                    current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                    payload = {
                        "name": name,
                        "id": mac,
                        "type": "unknown",
                        "operation": "unknown",
                        "location": "unknown",
                        "status": "disable",
                        "time": current_time
                    }
                    await send_to_api(payload)  # Giả sử hàm này đã được định nghĩa
                    return

        # Nếu kết nối thành công, đọc dữ liệu và xử lý
        if client and client.is_connected:
            try:
                label = await client.read_gatt_char(LABEL_CHAR_UUID)  # UUID giả định
                operation_mode = await client.read_gatt_char(OPERATION_MODE_CHAR_UUID)
                location_data = await client.read_gatt_char(LOCATION_DATA_CHAR_UUID)

                decoded_type = decode_operation_mode(operation_mode)  # Giả sử hàm này đã định nghĩa
                operation_hex = bytes_to_hex(operation_mode)  # Giả sử hàm này đã định nghĩa
                location_hex = process_location_data(location_data)  # Giả sử hàm này đã định nghĩa

                tz = pytz.timezone('Asia/Ho_Chi_Minh')
                current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                name = label.decode("utf-8", errors="ignore") if label else name

                # Tạo payload với status "active"
                payload = {
                    "name": name,
                    "id": mac,
                    "type": decoded_type,
                    "operation": operation_hex,
                    "location": location_hex,
                    "status": "active",
                    "time": current_time
                }
                await send_to_api(payload)

            except BleakError as e:
                print(f"Lỗi BLE khi đọc dữ liệu từ anchor {name}: {e}")
                # Gửi payload với status "disable" nếu đọc dữ liệu thất bại
                tz = pytz.timezone('Asia/Ho_Chi_Minh')
                current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
                payload = {
                    "name": name,
                    "id": mac,
                    "type": "unknown",
                    "operation": "unknown",
                    "location": "unknown",
                    "status": "disable",
                    "time": current_time
                }
                await send_to_api(payload)

            finally:
                # Ngắt kết nối sau khi hoàn tất
                await client.disconnect()
                await asyncio.sleep(3)

# Quét và kết nối tới các module
async def scan_and_connect():
    print("Đang quét các thiết bị BLE...")
    devices = await BleakScanner.discover(timeout=10.0)
    managed_modules = load_modules()
    tasks = []
    for module in managed_modules:
        if module["status"] == "disable":
            print(f"Bỏ qua module bị vô hiệu hóa: {module['name']} ({module['id']})")
            continue
        for device in devices:
            if device.address.lower() == module["id"].lower():
                if module["type"] == "tag":
                    tasks.append(handle_tag(module))
                elif module["type"] == "anchor":
                    tasks.append(handle_anchor(module))
                break
        else:
            print(f"Không tìm thấy module {module['name']} ({module['id']}) trong quá trình quét.")
    if tasks:
        await asyncio.gather(*tasks)
    else:
        print("Không có module active nào để kết nối.")


# Hàm chính
async def main():
    await scan_and_connect()


if __name__ == "__main__":
    asyncio.run(main())