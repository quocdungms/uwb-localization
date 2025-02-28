import asyncio
from bleak import BleakClient, BleakScanner
import struct
from init import *
# Địa chỉ MAC của module DWM1001 (tag) - thay bằng địa chỉ thực tế
DEVICE_ADDRESS = TAG_MAC  # Ví dụ: "00:11:22:33:44:55"

# UUID của service và characteristic
SERVICE_UUID = "680c21d9-c946-4c1f-9c11-baa1c21329e7"
UPDATE_RATE_UUID = "7bd47f30-5602-4389-b069-8305731308b6"

async def set_update_rate(u1_ms, u2_ms):
    """
    Đặt giá trị Update Rate cho tag.
    u1_ms: Thời gian cập nhật khi di chuyển (ms)
    u2_ms: Thời gian cập nhật khi đứng yên (ms)
    """
    try:
        # Tìm thiết bị (tùy chọn)
        print("Scanning for devices...")
        devices = await BleakScanner.discover()
        for device in devices:
            if device.address.upper() == DEVICE_ADDRESS.upper():
                print(f"Found device: {device.address} - {device.name}")
                break
        else:
            print(f"Device {DEVICE_ADDRESS} not found")
            return

        # Kết nối đến module
        async with BleakClient(DEVICE_ADDRESS) as client:
            print(f"Connected to {DEVICE_ADDRESS}")

            # # Đảm bảo MTU đủ lớn (tùy chọn)
            # mtu = await client.request_mtu(128)
            # print(f"MTU set to: {mtu} bytes")

            # Chuyển giá trị U1 và U2 thành bytes (little-endian)
            u1_bytes = struct.pack("<I", u1_ms)  # 4 bytes cho U1
            u2_bytes = struct.pack("<I", u2_ms)  # 4 bytes cho U2
            update_rate_value = u1_bytes + u2_bytes  # Tổng 8 bytes
            print(f"Setting Update Rate: U1 = {u1_ms}ms, U2 = {u2_ms}ms")
            print(f"Raw data: {update_rate_value.hex()}")

            # Ghi giá trị vào Update Rate Characteristic
            await client.write_gatt_char(UPDATE_RATE_UUID, update_rate_value, response=True)
            print("Update Rate successfully written")

            # (Tùy chọn) Đọc lại để xác nhận
            read_value = await client.read_gatt_char(UPDATE_RATE_UUID)
            u1_read, u2_read = struct.unpack("<II", read_value)
            print(f"Confirmed Update Rate: U1 = {u1_read}ms, U2 = {u2_read}ms")

    except Exception as e:
        print(f"Error: {e}")

async def main():
    # Ví dụ: Đặt U1 = 100ms (khi di chuyển), U2 = 1000ms (khi đứng yên)
    await set_update_rate(100, 1000)

if __name__ == "__main__":
    asyncio.run(main())