import asyncio
from bleak import BleakClient
from init import *
# UUID của characteristic Operation Mode
OPERATION_MODE_UUID = "3f0afd88-7770-46b0-b5e7-9fc099598964"

def decode_operation_mode(operation_bytes):
    """
    Giải mã Operation Mode từ 2 byte nhận được từ characteristic UUID "3f0afd88-7770-46b0-b5e7-9fc099598964".

    Args:
        operation_bytes (bytes): 2 byte dữ liệu Operation Mode.

    Returns:
        dict: Dictionary chứa các thông tin cấu hình được giải mã.
    """
    # Kiểm tra độ dài dữ liệu đầu vào
    if len(operation_bytes) != 2:
        raise ValueError("Operation Mode phải là 2 byte.")

    byte1 = operation_bytes[0]  # Byte đầu tiên
    byte2 = operation_bytes[1]  # Byte thứ hai

    # Giải mã byte đầu tiên
    is_anchor = (byte1 & 0x80) != 0               # Bit 7: tag (0) hoặc anchor (1)
    uwb_mode = (byte1 & 0x60) >> 5                # Bit 6-5: UWB - off (0), passive (1), active (2)
    firmware_select = (byte1 & 0x10) != 0         # Bit 4: firmware 1 (0), firmware 2 (1)
    accelerometer_enable = (byte1 & 0x08) != 0    # Bit 3: accelerometer enable (0, 1)
    led_enable = (byte1 & 0x04) != 0              # Bit 2: LED indication enable (0, 1)
    firmware_update_enable = (byte1 & 0x02) != 0  # Bit 1: firmware update enable (0, 1)
    # Bit 0: reserved, không sử dụng

    # Giải mã byte thứ hai
    initiator_enable = (byte2 & 0x80) != 0        # Bit 7: initiator enable (anchor specific)
    low_power_mode = (byte2 & 0x40) != 0          # Bit 6: low power mode enable (tag specific)
    location_engine_enable = (byte2 & 0x20) != 0  # Bit 5: location engine enable (tag specific)
    # Bit 4-0: reserved, không sử dụng

    # Xác định loại nút
    node_type = "anchor" if is_anchor else "tag"

    # Xác định chế độ UWB
    uwb_mode_str = ["off", "passive", "active"][uwb_mode]

    # Tạo dictionary kết quả
    result = {
        "node_type": node_type,
        "uwb_mode": uwb_mode_str,
        "firmware_select": "firmware 2" if firmware_select else "firmware 1",
        "accelerometer_enable": accelerometer_enable,
        "led_enable": led_enable,
        "firmware_update_enable": firmware_update_enable,
    }

    # Thêm thông tin đặc biệt theo loại nút
    if is_anchor:
        result["initiator_enable"] = initiator_enable
    else:
        result["low_power_mode"] = low_power_mode
        result["location_engine_enable"] = location_engine_enable

    return result

async def read_and_decode_operation_mode(address):
    """
    Kết nối đến thiết bị BLE, đọc dữ liệu Operation Mode và giải mã.

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

            # Đọc dữ liệu từ characteristic Operation Mode
            operation_data = await client.read_gatt_char(OPERATION_MODE_UUID)
            print(f"Dữ liệu thô (hex): {operation_data.hex()}")

            # Giải mã dữ liệu
            decoded_data = decode_operation_mode(operation_data)
            print("Dữ liệu đã giải mã:", decoded_data)

    except Exception as e:
        print(f"Lỗi khi kết nối hoặc đọc dữ liệu: {e}")

# Hàm chạy chính
async def main():
    # Thay bằng địa chỉ MAC của thiết bị DWM1001 của bạn
    device_address = TAG_MAC  # Ví dụ, thay bằng địa chỉ thật
    await read_and_decode_operation_mode(device_address)

if __name__ == "__main__":
    asyncio.run(main())