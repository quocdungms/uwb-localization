import asyncio
import struct
from bleak import BleakClient
from location import *
from global_var import *


# Hàm xử lý dữ liệu nhận được từ notification
def notification_handler(sender, data):
    print(f"Nhận dữ liệu từ {sender}: {data.hex()}")
    decoded_data = decode_location_data(data)
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
            # await client.start_notify(LOCATION_DATA_UUID, notification_handler)
            # print(f"Đã đăng ký notification cho {LOCATION_DATA_UUID}")
            #
            # # Giữ kết nối trong 60 giây để nhận dữ liệu
            # await asyncio.sleep(6000)
            #
            # # Dừng notification (tùy chọn)
            # await client.stop_notify(LOCATION_DATA_UUID)
            # print("Đã dừng notification")
            data = await client.read_gatt_char(LOCATION_DATA_UUID)
            print(notification_handler("asd", data))

        except Exception as e:
            print(f"Lỗi: {e}")

# Hàm chính
async def main():

    # module_address = TAG_MAC
    module_address = "EB:C3:F1:BC:24:DD"
    await setup_notifications(module_address)

if __name__ == "__main__":
    asyncio.run(main())