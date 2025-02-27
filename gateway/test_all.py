import asyncio
import json
import time
from bleak import BleakScanner, BleakClient
import requests
from typing import Dict, Optional

from dotenv import load_dotenv
import os


load_dotenv()
SV_URL = os.getenv("SV_URL") + ":" + os.getenv("PORT") + "/" + os.getenv("TOPIC")
# Định nghĩa UUID của các characteristic
NETWORK_NODE_SERVICE_UUID = "680c21d9-c946-4c1f-9c11-baa1c21329e7"
LABEL_UUID = "00002a00-0000-1000-8000-00805f9b34fb"  # Device Name (GAP)
OPERATION_MODE_UUID = "3f0afd88-7770-46b0-b5e7-9fc099598964"
LOCATION_DATA_MODE_UUID = "a02b947e-df97-4516-996a-1882521e0ead"
LOCATION_DATA_UUID = "003bbdf2-c634-4b3d-ab56-7ec889b89a37"

# Đọc danh sách module từ file module.json
def load_modules() -> Dict:
    try:
        with open('module.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Ghi danh sách module vào file module.json
def save_modules(modules: Dict):
    with open('module.json', 'w') as f:
        json.dump(modules, f, indent=4)

# Gửi dữ liệu lên server qua RESTful API
def send_to_server(data: Dict) -> int:
    url = SV_URL  # Thay bằng URL thực tế
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, json=data, headers=headers, timeout=5)
        return response.status_code
    except requests.RequestException as e:
        print(f"Error sending to server: {e}")
        return 500

# Giải mã operation mode để xác định type (tag/anchor)
def decode_operation_mode(op_mode: bytes) -> str:
    # Giả sử bit cao nhất của byte đầu tiên xác định tag/anchor
    return 'tag' if (op_mode[0] & 0x80) == 0 else 'anchor'

# Mã hóa operation mode sang byte array
def encode_operation_mode(tag_or_anchor: str) -> bytes:
    return bytes([0x00, 0x00]) if tag_or_anchor == 'tag' else bytes([0x80, 0x00])

# Xử lý dữ liệu location
def process_location_data(location_data: bytes) -> Dict:
    mode = location_data[0]
    if mode == 0:  # Position only (14 bytes)
        x = int.from_bytes(location_data[1:5], 'little')
        y = int.from_bytes(location_data[5:9], 'little')
        z = int.from_bytes(location_data[9:13], 'little')
        qf = location_data[13]
        return {'mode': mode, 'position': {'x': x, 'y': y, 'z': z, 'qf': qf}}
    # Xử lý mode khác nếu cần (ví dụ mode 2)
    return {'mode': mode, 'position': None}

# Quét và kết nối ban đầu với các module
async def scan_and_connect():
    modules = load_modules()
    devices = await BleakScanner.discover(timeout=10.0)
    tasks = []
    for device in devices:
        mac = device.address
        if mac in modules and modules[mac]['status'] == 'active':
            tasks.append(connect_and_collect_data(mac, modules[mac]))
    if tasks:
        await asyncio.gather(*tasks)

# Kết nối và thu thập dữ liệu từ module
async def connect_and_collect_data(mac: str, module: Dict):
    try:
        async with BleakClient(mac, timeout=20.0) as client:
            # Đọc thông tin từ module
            label = await client.read_gatt_char(LABEL_UUID)
            label = label.decode('utf-8')
            op_mode = await client.read_gatt_char(OPERATION_MODE_UUID)
            tag_or_anchor = decode_operation_mode(op_mode)
            location_data_mode = await client.read_gatt_char(LOCATION_DATA_MODE_UUID)
            location_data = await client.read_gatt_char(LOCATION_DATA_UUID)
            location_info = process_location_data(location_data)
            timestamp = time.time()

            # Đóng gói dữ liệu
            data = {
                'name': module['name'],
                'id': mac,
                'operation': op_mode.hex(),
                'location': location_info,
                'status': 'active',
                'time': timestamp
            }
            send_to_server(data)

            # Cập nhật type vào module.json
            module['type'] = tag_or_anchor
            save_modules(load_modules())

            # Nếu là tag, thiết lập notify
            if tag_or_anchor == 'tag':
                await setup_tag_notify(client, mac)
    except Exception as e:
        print(f"Error with module {mac}: {e}")
        module['status'] = 'disable'
        save_modules(load_modules())
        send_to_server({'id': mac, 'status': 'disable', 'time': time.time()})

# Thiết lập notify cho tag
async def setup_tag_notify(client: BleakClient, mac: str):
    last_position = None
    last_send_time = 0
    notify_interval_stationary = 10  # Giây, có thể tùy chỉnh
    notify_interval_moving = 1  # Giây, có thể tùy chỉnh
    movement_threshold = 100  # mm, ngưỡng để xác định chuyển động

    async def handle_notify(sender: int, data: bytes):
        nonlocal last_position, last_send_time
        location_info = process_location_data(data)
        timestamp = time.time()
        position = location_info['position']

        # Xác định tag đứng yên hay di chuyển
        is_moving = False
        if last_position and position:
            dx = abs(position['x'] - last_position['x'])
            dy = abs(position['y'] - last_position['y'])
            dz = abs(position['z'] - last_position['z'])
            is_moving = (dx > movement_threshold or dy > movement_threshold or dz > movement_threshold)
        last_position = position

        # Xác định khoảng thời gian gửi dữ liệu
        interval = notify_interval_moving if is_moving else notify_interval_stationary
        if timestamp - last_send_time >= interval:
            data = {
                'id': mac,
                'location': location_info,
                'status': 'active',
                'time': timestamp
            }
            send_to_server(data)
            last_send_time = timestamp

    await client.start_notify(LOCATION_DATA_UUID, handle_notify)

# Kiểm tra trạng thái anchor mỗi 30 giây
async def check_anchor_status():
    while True:
        modules = load_modules()
        tasks = []
        for mac, module in modules.items():
            if module.get('type') == 'anchor' and module['status'] == 'active':
                tasks.append(check_single_anchor(mac, module))
        if tasks:
            await asyncio.gather(*tasks)
        await asyncio.sleep(30)

async def check_single_anchor(mac: str, module: Dict):
    try:
        async with BleakClient(mac, timeout=10.0) as client:
            await client.read_gatt_char(OPERATION_MODE_UUID)
            module['status'] = 'active'
    except Exception:
        module['status'] = 'disable'
        send_to_server({'id': mac, 'status': 'disable', 'time': time.time()})
    save_modules(load_modules())

# Thêm module
async def add_module(mac: str, operation_mode: str):
    modules = load_modules()
    if mac not in modules:
        op_mode_bytes = bytes.fromhex(operation_mode)
        modules[mac] = {
            'name': f"Module_{mac[-6:]}",
            'id': mac,
            'type': decode_operation_mode(op_mode_bytes),
            'status': 'active'
        }
        save_modules(modules)
        # Ghi operation mode vào module
        try:
            async with BleakClient(mac) as client:
                await client.write_gatt_char(OPERATION_MODE_UUID, op_mode_bytes)
        except Exception as e:
            print(f"Error adding module {mac}: {e}")

# Sửa module
async def update_module(mac: str, operation_mode: Optional[str] = None, location_data_mode: Optional[str] = None):
    modules = load_modules()
    if mac in modules:
        try:
            async with BleakClient(mac) as client:
                if operation_mode:
                    op_mode_bytes = bytes.fromhex(operation_mode)
                    await client.write_gatt_char(OPERATION_MODE_UUID, op_mode_bytes)
                    modules[mac]['type'] = decode_operation_mode(op_mode_bytes)
                if location_data_mode:
                    mode_bytes = bytes.fromhex(location_data_mode)
                    await client.write_gatt_char(LOCATION_DATA_MODE_UUID, mode_bytes)
            save_modules(modules)
        except Exception as e:
            print(f"Error updating module {mac}: {e}")

# Xóa module
def delete_module(mac: str):
    modules = load_modules()
    if mac in modules:
        del modules[mac]
        save_modules(modules)

# Hàm chính
async def main():
    tasks = [
        asyncio.create_task(scan_and_connect()),
        asyncio.create_task(check_anchor_status())
    ]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())