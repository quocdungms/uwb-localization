import asyncio
import struct
from bleak import BleakClient




from location import *
# Định nghĩa UUID
SERVICE_UUID = "680c21d9-c946-4c1f-9c11-baa1c21329e7"
LOCATION_DATA_UUID = "003bbdf2-c634-4b3d-ab56-7ec889b89a37"
LOCATION_DATA_MODE_UUID = "a02b947e-df97-4516-996a-1882521e0ead"

# Hàm giải mã Location Data
def decode_location_data(mode, data):
    """Giải mã dữ liệu vị trí dựa trên mode (0, 1, hoặc 2)."""
    if mode == 0:  # Position only
        return decode_location_mode_0(data)
    elif mode == 1:  # Distances
        return decode_location_mode_1(data)
    elif mode == 2:  # Position + Distances
        return decode_location_mode_2(data)
    else:
        return None

# Hàm xử lý dữ liệu nhận được từ notification
def notification_handler(sender, data):
    """Xử lý dữ liệu nhận được từ notification."""
    print(f"Nhận dữ liệu từ {sender}: {data.hex()}")
    # Đọc mode để giải mã dữ liệu (giả định mode đã biết, hoặc cần đọc trước)
    # Ở đây tôi giả định mode 2 dựa trên dữ liệu thực tế bạn cung cấp trước đó
    decoded_data = decode_location_data(2, data)
    print(f"Dữ liệu giải mã: {decoded_data}")

# Hàm kết nối và đăng ký notification
async def setup_notifications(address):
    """Kết nối tới module và đăng ký nhận notification từ LOCATION_DATA_UUID."""
    async with BleakClient(address) as client:
        try:
            # Kiểm tra kết nối
            if not await client.is_connected():
                print(f"Không thể kết nối tới {address}")
                return

            print(f"Đã kết nối tới {address}")

            # Đọc Location Data Mode để biết mode hiện tại
            loc_mode_data = await client.read_gatt_char(LOCATION_DATA_MODE_UUID)
            loc_mode = int(loc_mode_data[0])
            print(f"Location Data Mode: {loc_mode}")

            # Đăng ký nhận notification từ LOCATION_DATA_UUID
            await client.start_notify(LOCATION_DATA_UUID, notification_handler)
            print(f"Đã đăng ký notification cho {LOCATION_DATA_UUID}")

            # Giữ kết nối trong 60 giây để nhận dữ liệu
            await asyncio.sleep(60)

            # Dừng notification (tùy chọn)
            await client.stop_notify(LOCATION_DATA_UUID)
            print("Đã dừng notification")

        except Exception as e:
            print(f"Lỗi: {e}")

# Hàm chính
async def main():
    # Thay bằng địa chỉ BLE của module DWM1001 của bạn
    module_address = "EB:52:53:F5:D5:90"  # Ví dụ
    await setup_notifications(module_address)

if __name__ == "__main__":
    asyncio.run(main())