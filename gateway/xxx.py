import asyncio
from bleak import BleakClient, BleakScanner


async def explore_services(address):
    async with BleakClient(address) as client:
        print(f"Đã kết nối đến {address}")

        # Lấy danh sách tất cả services và characteristics
        services = await client.get_services()

        print("\nDanh sách Services và Characteristics:")
        for service in services:
            print(f"\nService UUID: {service.uuid}")
            for char in service.characteristics:
                print(f"  Characteristic UUID: {char.uuid}")
                print(f"  Properties: {char.properties}")

                # Thử đọc dữ liệu nếu characteristic hỗ trợ read
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char.uuid)
                        print(f"  Data: {value.hex()} (Length: {len(value)} bytes)")

                        # Kiểm tra xem có phải dữ liệu 29 byte không
                        if len(value) == 29:
                            print("  => Có thể đây là Device Info!")
                            decoded = await decode_device_info(value)
                            if decoded:
                                print("  Decoded Info:", decoded)
                    except Exception as e:
                        print(f"  Không thể đọc: {e}")


async def decode_device_info(data):
    if len(data) != 29:
        print(f"Độ dài dữ liệu không đúng: {len(data)} bytes (yêu cầu 29 bytes)")
        return None

    try:
        node_id = int.from_bytes(data[0:8], byteorder='little')
        hw_version = int.from_bytes(data[8:12], byteorder='little')
        fw1_version = int.from_bytes(data[12:16], byteorder='little')
        fw2_version = int.from_bytes(data[16:20], byteorder='little')
        fw1_checksum = int.from_bytes(data[20:24], byteorder='little')
        fw2_checksum = int.from_bytes(data[24:28], byteorder='little')
        operation_flags = data[28]

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

    devices = await BleakScanner.discover()
    target_device = None

    for device in devices:
        if device.name == "DWD29A":  # Tên thiết bị của bạn
            target_device = device
            break

    if not target_device:
        print("Không tìm thấy thiết bị!")
        return

    print(f"Đã tìm thấy thiết bị: {target_device.name} ({target_device.address})")
    await explore_services(target_device.address)


def main():
    asyncio.run(scan_and_connect())


if __name__ == "__main__":
    main()