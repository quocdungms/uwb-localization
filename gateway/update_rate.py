import asyncio
import struct
from bleak import BleakClient

from init import UPDATE_RATE_UUID

# Hàm đọc và giải mã Update Rate
async def read_update_rate(address):
    """Kết nối tới module và đọc giá trị Update Rate của tag."""
    try:
        async with BleakClient(address) as client:
            # Kiểm tra kết nối
            if not await client.is_connected():
                print(f"Không thể kết nối tới {address}")
                return

            print(f"Đã kết nối tới {address}")

            # Đọc giá trị Update Rate
            update_rate_data = await client.read_gatt_char(UPDATE_RATE_UUID)

            # Giải mã dữ liệu (8 byte: U1 - 4 byte, U2 - 4 byte, little-endian)
            u1, u2 = struct.unpack("<II", update_rate_data)

            # Hiển thị kết quả
            print(f"Update Rate:")
            print(f"  U1 (khi di chuyển): {u1} ms ({u1 / 1000:.2f} giây)")
            print(f"  U2 (khi đứng yên): {u2} ms ({u2 / 1000:.2f} giây)")

    except Exception as e:
        print(f"Lỗi khi đọc Update Rate từ {address}: {e}")


# Hàm chính
async def main():
    # Thay bằng địa chỉ BLE của module DWM1001 của bạn
    module_address = "EB:52:53:F5:D5:90"  # Ví dụ
    await read_update_rate(module_address)


if __name__ == "__main__":
    asyncio.run(main())