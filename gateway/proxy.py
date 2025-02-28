import asyncio
from bleak import BleakClient, BleakScanner
import struct
from init import TAG_MAC
# Địa chỉ MAC của module DWM1001 (thay bằng địa chỉ thực tế của bạn)
DEVICE_ADDRESS =  TAG_MAC # Ví dụ: "00:11:22:33:44:55"

# UUID của service và characteristic
SERVICE_UUID = "680c21d9-c946-4c1f-9c11-baa1c21329e7"
PROXY_POSITIONS_UUID = "f4a67d7d-379d-4183-9c03-4b6ea5103291"

async def notification_handler(sender, data):
    """Xử lý thông báo từ Proxy Positions Characteristic"""
    try:
        # Đọc số lượng phần tử (1 byte đầu tiên)
        num_elements = data[0]
        print(f"Received notification with {num_elements} tag positions")

        # Mỗi tag position gồm: 2 bytes node ID + 13 bytes position data
        offset = 1
        for i in range(num_elements):
            if offset + 15 <= len(data):  # Kiểm tra đủ dữ liệu cho 1 tag position
                # Đọc node ID (2 bytes)
                node_id = struct.unpack("<H", data[offset:offset+2])[0]
                offset += 2

                # Đọc vị trí X, Y, Z (mỗi tọa độ 4 bytes, little-endian) và quality factor (1 byte)
                x = struct.unpack("<i", data[offset:offset+4])[0] / 1000.0  # mm -> m
                offset += 4
                y = struct.unpack("<i", data[offset:offset+4])[0] / 1000.0  # mm -> m
                offset += 4
                z = struct.unpack("<i", data[offset:offset+4])[0] / 1000.0  # mm -> m
                offset += 4
                quality = data[offset]
                offset += 1

                print(f"Tag {i+1}: Node ID = {node_id:04x}, Position = ({x:.3f}m, {y:.3f}m, {z:.3f}m), Quality = {quality}")
            else:
                print("Error: Incomplete data for a tag position")
                break
    except Exception as e:
        print(f"Error parsing notification data: {e}")

async def enable_proxy_notifications():
    try:
        # Tìm thiết bị (tùy chọn, để xác nhận địa chỉ MAC)
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

            # Tăng MTU (nếu được hỗ trợ bởi thiết bị)
            mtu = await client.request_mtu(128)
            print(f"MTU set to: {mtu} bytes")

            # Kiểm tra kết nối
            if not client.is_connected:
                print("Failed to connect")
                return

            # Bật notification cho Proxy Positions Characteristic
            await client.start_notify(PROXY_POSITIONS_UUID, notification_handler)
            print("Notifications enabled for Proxy Positions Characteristic")

            # Chờ thông báo trong 60 giây
            print("Waiting for notifications...")
            await asyncio.sleep(60)  # Chạy trong 60 giây

            # Tắt notification trước khi ngắt kết nối (tùy chọn)
            await client.stop_notify(PROXY_POSITIONS_UUID)

    except Exception as e:
        print(f"Error: {e}")

async def main():
    await enable_proxy_notifications()

if __name__ == "__main__":
    # Chạy vòng lặp sự kiện asyncio
    asyncio.run(main())