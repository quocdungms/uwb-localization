import asyncio
from bleak import BleakClient, BleakScanner



from init import *
# UUID của characteristic chứa dữ liệu device info



async def decode_device_info(data):
    """
    Giải mã dữ liệu 29 bytes theo định dạng:
    - Node ID: 8 bytes
    - HW version: 4 bytes
    - FW1 version: 4 bytes
    - FW2 version: 4 bytes
    - FW1 checksum: 4 bytes
    - FW2 checksum: 4 bytes
    - RDonly Operation flags: 1 byte
    """
    if len(data) != 29:
        print(f"Độ dài dữ liệu không đúng: {len(data)} bytes (yêu cầu 29 bytes)")
        return None

    try:
        # Giải mã từng phần
        node_id = data[0:8].hex()
        hw_version = int.from_bytes(data[8:12], byteorder='little')
        fw1_version = int.from_bytes(data[12:16], byteorder='little')
        fw2_version = int.from_bytes(data[16:20], byteorder='little')
        fw1_checksum = int.from_bytes(data[20:24], byteorder='little')
        fw2_checksum = int.from_bytes(data[24:28], byteorder='little')
        operation_flags = data[28]

        # Trả về kết quả dưới dạng dictionary
        return {
            "Node ID": node_id,
            "Hardware Version": hw_version,
            "Firmware 1 Version": fw1_version,
            "Firmware 2 Version": fw2_version,
            "Firmware 1 Checksum": fw1_checksum,
            "Firmware 2 Checksum": fw2_checksum,
            "Operation Flags": operation_flags
        }
    except Exception as e:
        print(f"Lỗi khi giải mã: {e}")
        return None


async def scan_and_connect():
    print("Đang tìm kiếm thiết bị...")

    # Quét tìm thiết bị
    devices = await BleakScanner.discover()
    target_device = None

    for device in devices:
        # Thay bằng điều kiện để tìm thiết bị của bạn (tên hoặc địa chỉ)
        if device.name == "DWD29A":  # Thay bằng tên thiết bị thực tế
            target_device = device
            break

    if not target_device:
        print("Không tìm thấy thiết bị!")
        return

    print(f"Đã tìm thấy thiết bị: {target_device.name} ({target_device.address})")

    # Kết nối đến thiết bị
    async with BleakClient(target_device.address) as client:
        print("Đã kết nối đến thiết bị!")

        # Đọc dữ liệu từ characteristic
        try:
            device_info = await client.read_gatt_char(DEVICE_INFO)
            print("Dữ liệu thô:", device_info.hex())

            # Giải mã dữ liệu
            decoded_info = await decode_device_info(device_info)

            if decoded_info:
                print("\nThông tin thiết bị đã giải mã:")
                for key, value in decoded_info.items():
                    print(f"{key}: {value}")

        except Exception as e:
            print(f"Lỗi khi đọc dữ liệu: {e}")


def main():
    # Chạy asyncio event loop
    asyncio.run(scan_and_connect())


if __name__ == "__main__":
    main()