import asyncio
import json
from datetime import datetime
import pytz
from bleak import BleakScanner, BleakClient
import requests
from typing import Dict, Optional
from dotenv import load_dotenv
import os
load_dotenv()
sv_url = os.getenv("SV_URL") + ":" + os.getenv("PORT") + "/" + os.getenv("TOPIC")
# UUID của các characteristic
OPERATION_MODE_UUID = "3f0afd88-7770-46b0-b5e7-9fc099598964"
LOCATION_DATA_MODE_UUID = "a02b947e-df97-4516-996a-1882521e0ead"
LOCATION_DATA_UUID = "003bbdf2-c634-4b3d-ab56-7ec889b89a37"
LABEL_UUID = "00002a00-0000-1000-8000-00805f9b34fb"

# Đọc và ghi file module.json
def load_modules() -> Dict:
    try:
        with open('module.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_modules(modules: Dict):
    with open('module.json', 'w') as f:
        json.dump(modules, f, indent=4)

# Hàm định dạng thời gian GMT+7
def get_gmt7_time() -> str:
    tz = pytz.timezone('Asia/Bangkok')  # GMT+7
    return datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')

# Gửi dữ liệu lên server
def send_to_server(data: Dict) -> int:
    url = sv_url
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, json=data, headers=headers, timeout=5)
        print(f"Phản hồi từ server: {response.text}")
        return response.status_code
    except requests.RequestException as e:
        print(f"Error sending to server: {e}")
        return 500

# Giải mã Operation Mode
def decode_operation_mode(op_mode: bytes) -> str:
    return 'tag' if (op_mode[0] & 0x80) == 0 else 'anchor'

# Xử lý dữ liệu Location
def process_location_data(location_data: bytes) -> Dict:
    mode = location_data[0]
    if mode == 0 and len(location_data) >= 14:
        x = int.from_bytes(location_data[1:5], 'little', signed=True)
        y = int.from_bytes(location_data[5:9], 'little', signed=True)
        z = int.from_bytes(location_data[9:13], 'little', signed=True)
        qf = location_data[13]
        return {'mode': mode, 'position': {'x': x, 'y': y, 'z': z, 'qf': qf}}
    return {'mode': mode, 'position': None}

# Quét và kết nối với giới hạn đồng thời
async def scan_and_connect(semaphore: asyncio.Semaphore):
    modules = load_modules()
    devices = await BleakScanner.discover(timeout=10.0)
    tasks = []
    for device in devices:
        mac = device.address
        if mac in modules and modules[mac]['status'] == 'active':
            tasks.append(connect_and_collect_data(mac, modules[mac], semaphore))
    if tasks:
        await asyncio.gather(*tasks)

async def connect_and_collect_data(mac: str, module: Dict, semaphore: asyncio.Semaphore):
    async with semaphore:
        retries = 3
        for attempt in range(retries):
            try:
                async with BleakClient(mac, timeout=20.0) as client:
                    label = await client.read_gatt_char(LABEL_UUID)
                    label = label.decode('utf-8')
                    op_mode = await client.read_gatt_char(OPERATION_MODE_UUID)
                    tag_or_anchor = decode_operation_mode(op_mode)
                    location_data_mode = await client.read_gatt_char(LOCATION_DATA_MODE_UUID)
                    location_data = await client.read_gatt_char(LOCATION_DATA_UUID)
                    location_info = process_location_data(location_data)
                    timestamp = get_gmt7_time()

                    data = {
                        'name': module['name'],
                        'id': mac,
                        'operation': op_mode.hex(),
                        'location': location_info,
                        'status': 'active',
                        'time': timestamp
                    }
                    send_to_server(data)

                    module['type'] = tag_or_anchor
                    save_modules(load_modules())

                    if tag_or_anchor == 'tag':
                        await setup_tag_notify(client, mac)
                    break
            except Exception as e:
                print(f"Error with module {mac} (lần thử {attempt + 1}/{retries}): {e}")
                if "InProgress" in str(e):
                    await asyncio.sleep(2)
                elif attempt < retries - 1:
                    await asyncio.sleep(1)
                else:
                    module['status'] = 'disable'
                    save_modules(load_modules())
                    send_to_server({'id': mac, 'status': 'disable', 'time': get_gmt7_time()})
        await asyncio.sleep(1)

async def setup_tag_notify(client: BleakClient, mac: str):
    last_position = None
    last_send_time = 0
    notify_interval_stationary = 10
    notify_interval_moving = 1
    movement_threshold = 100

    async def handle_notify(sender: int, data: bytes):
        nonlocal last_position, last_send_time
        location_info = process_location_data(data)
        timestamp = datetime.now(pytz.timezone('Asia/Bangkok')).timestamp()
        position = location_info['position']

        is_moving = False
        if last_position and position:
            dx = abs(position['x'] - last_position['x'])
            dy = abs(position['y'] - last_position['y'])
            dz = abs(position['z'] - last_position['z'])
            is_moving = (dx > movement_threshold or dy > movement_threshold or dz > movement_threshold)
        last_position = position

        interval = notify_interval_moving if is_moving else notify_interval_stationary
        if timestamp - last_send_time >= interval:
            data = {'id': mac, 'location': location_info, 'status': 'active', 'time': get_gmt7_time()}
            send_to_server(data)
            last_send_time = timestamp

    await client.start_notify(LOCATION_DATA_UUID, handle_notify)

async def check_anchor_status(semaphore: asyncio.Semaphore):
    while True:
        modules = load_modules()
        tasks = []
        for mac, module in modules.items():
            if module.get('type') == 'anchor' and module['status'] == 'active':
                tasks.append(check_single_anchor(mac, module, semaphore))
        if tasks:
            await asyncio.gather(*tasks)
        await asyncio.sleep(30)

async def check_single_anchor(mac: str, module: Dict, semaphore: asyncio.Semaphore):
    async with semaphore:
        retries = 3
        connected = False
        for attempt in range(retries):
            try:
                async with BleakClient(mac, timeout=10.0) as client:
                    await client.read_gatt_char(OPERATION_MODE_UUID)
                    module['status'] = 'active'
                    connected = True
                    break
            except Exception as e:
                print(f"Error with anchor {mac} (lần thử {attempt + 1}/{retries}): {e}")
                if "InProgress" in str(e):
                    await asyncio.sleep(2)
                elif attempt < retries - 1:
                    await asyncio.sleep(1)
        if not connected:
            module['status'] = 'disable'
            send_to_server({'id': mac, 'status': 'disable', 'time': get_gmt7_time()})
        save_modules(load_modules())
        await asyncio.sleep(1)

async def main():
    semaphore = asyncio.Semaphore(2)
    tasks = [
        asyncio.create_task(scan_and_connect(semaphore)),
        asyncio.create_task(check_anchor_status(semaphore))
    ]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())