import asyncio
from bleak import BleakClient
from init import *

# Địa chỉ MAC hoặc UUID của thiết bị BLE
DEVICE_ADDRESS = TAG_MAC  # Thay bằng địa chỉ thiết bị BLE của bạn
BATTERY_CHARACTERISTIC_UUID = "00002a00-0000-1000-8000-00805f9b34fb"

async def get_battery_level(address):
    async with BleakClient(address) as client:
        if await client.is_connected():
            battery_level = await client.read_gatt_char(BATTERY_CHARACTERISTIC_UUID)
            print(f"Battery Level: {int.from_bytes(battery_level, 'little')}%")
        else:
            print("Không thể kết nối với thiết bị")

asyncio.run(get_battery_level(DEVICE_ADDRESS))
