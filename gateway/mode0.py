import asyncio
from bleak import BleakClient
from init import *
# UUID của characteristic Location Data Mode
LOCATION_DATA_MODE_UUID = "a02b947e-df97-4516-996a-1882521e0ead"

async def set_location_data_mode_to_zero(address):
    """
    Chuyển Location Data Mode của thiết bị sang mode 0 (Position only).

    Args:
        address (str): Địa chỉ MAC của thiết bị BLE (ví dụ: "AA:BB:CC:DD:EE:FF").
    """
    try:
        async with BleakClient(address) as client:
            # Kiểm tra kết nối
            if not client.is_connected:
                print(f"Không thể kết nối đến thiết bị {address}")
                return

            print(f"Đã kết nối đến thiết bị {address}")

            # Giá trị mode 0 dưới dạng bytes (1 byte)
            mode_zero = bytes([0x00])

            # Ghi giá trị mode 0 vào characteristic
            await client.write_gatt_char(LOCATION_DATA_MODE_UUID, mode_zero)
            print(f"Đã chuyển Location Data Mode sang mode 0 (Position only)")

            # Đọc lại để xác nhận (tùy chọn)
            current_mode = await client.read_gatt_char(LOCATION_DATA_MODE_UUID)
            print(f"Giá trị hiện tại của Location Data Mode (hex): {current_mode.hex()}")

    except Exception as e:
        print(f"Lỗi khi kết nối hoặc ghi dữ liệu: {e}")

# Hàm chạy chính
async def main():
    # Thay bằng địa chỉ MAC của thiết bị DWM1001 của bạn
    device_address = TAG_MAC  # Ví dụ, thay bằng địa chỉ thật
    await set_location_data_mode_to_zero(device_address)

if __name__ == "__main__":
    asyncio.run(main())