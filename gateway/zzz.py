import asyncio
from bleak import BleakClient
from init import *
# Định nghĩa UUID của các Anchor-specific Characteristics
CHARACTERISTICS = {
    "Operation Mode": "3f0afd88-7770-46b0-b5e7-9fc099598964",
    "Device Info": "1e63b1eb-d4ed-444e-af54-c1e965192501",
    "Persisted Position": "fof26c9b-2c8c-49ac-ab60-fe03def1b40c",
    "MAC Stats": "28d01d60-89de-4bfa-b6e9-651ba596232c",
    "Cluster Info": "17b1613e-98f2-4436-bcde-23af17a10c72",
    "Anchor List": "5b10c428-af2f-486f-aee1-9dbd79b6bccb"
}

def decode_operation_mode(data: bytes) -> dict:
    """Giải mã Operation Mode (2 bytes)."""
    if len(data) != 2:
        raise ValueError("Operation Mode phải là 2 byte.")
    byte1 = data[0]
    byte2 = data[1]
    initiator_enable = (byte2 & 0x80) != 0
    return {
        "initiator_enable": initiator_enable,
        "raw_hex": data.hex()
    }

def decode_device_info(data: bytes) -> dict:
    """Giải mã Device Info (29 bytes)."""
    if len(data) != 29:
        raise ValueError("Device Info phải là 29 byte.")
    operation_flags = data[28]
    is_bridge = (operation_flags & 0x80) != 0
    return {
        "node_id": data[0:8].hex(),
        "hw_version": int.from_bytes(data[8:12], "little"),
        "fw1_version": int.from_bytes(data[12:16], "little"),
        "fw2_version": int.from_bytes(data[16:20], "little"),
        "fw1_checksum": int.from_bytes(data[20:24], "little"),
        "fw2_checksum": int.from_bytes(data[24:28], "little"),
        "is_bridge": is_bridge,
        "raw_hex": data.hex()
    }

def decode_persisted_position(data: bytes) -> dict:
    """Giải mã Persisted Position (13 bytes)."""
    if len(data) != 13:
        raise ValueError("Persisted Position phải là 13 byte.")
    return {
        "x": int.from_bytes(data[0:4], "little", signed=True),  # mm
        "y": int.from_bytes(data[4:8], "little", signed=True),  # mm
        "z": int.from_bytes(data[8:12], "little", signed=True), # mm
        "quality_factor": data[12],                             # 1-100
        "raw_hex": data.hex()
    }

def decode_mac_stats(data: bytes) -> dict:
    """Giải mã MAC Stats (4 bytes)."""
    if len(data) != 4:
        raise ValueError("MAC Stats phải là 4 byte.")
    return {
        "mac_stats": int.from_bytes(data, "little"),
        "raw_hex": data.hex()
    }

def decode_cluster_info(data: bytes) -> dict:
    """Giải mã Cluster Info (5 bytes)."""
    if len(data) != 5:
        raise ValueError("Cluster Info phải là 5 byte.")
    return {
        "seat_number": data[0],
        "cluster_map": int.from_bytes(data[1:3], "little"),
        "cluster_neighbor_map": int.from_bytes(data[3:5], "little"),
        "raw_hex": data.hex()
    }

def decode_anchor_list(data: bytes) -> dict:
    """Giải mã Anchor List (33 bytes)."""
    if len(data) != 33:
        raise ValueError("Anchor List phải là 33 byte.")
    count = data[0]
    anchor_ids = [data[i:i+2].hex() for i in range(1, min(count * 2 + 1, len(data)), 2)]
    return {
        "count": count,
        "anchor_ids": anchor_ids,
        "raw_hex": data.hex()
    }

DECODERS = {
    "3f0afd88-7770-46b0-b5e7-9fc099598964": decode_operation_mode,
    "1e63b1eb-d4ed-444e-af54-c1e965192501": decode_device_info,
    "fof26c9b-2c8c-49ac-ab60-fe03def1b40c": decode_persisted_position,
    "28d01d60-89de-4bfa-b6e9-651ba596232c": decode_mac_stats,
    "17b1613e-98f2-4436-bcde-23af17a10c72": decode_cluster_info,
    "5b10c428-af2f-486f-aee1-9dbd79b6bccb": decode_anchor_list
}

async def read_and_decode_anchor_data(address: str):
    """Đọc và giải mã dữ liệu từ tất cả Anchor-specific Characteristics."""
    try:
        async with BleakClient(address) as client:
            if not client.is_connected:
                print(f"Không thể kết nối đến thiết bị {address}")
                return

            print(f"Đã kết nối đến thiết bị {address}")

            for name, uuid in CHARACTERISTICS.items():
                try:
                    # Đọc dữ liệu từ characteristic
                    data = await client.read_gatt_char(uuid)
                    print(f"\n{name} ({uuid}):")
                    print(f"Dữ liệu thô (hex): {data.hex()}")

                    # Giải mã dữ liệu
                    decoder = DECODERS.get(uuid)
                    if decoder:
                        decoded = decoder(data)
                        print(f"Dữ liệu giải mã: {decoded}")
                    else:
                        print("Không có hàm giải mã cho UUID này.")

                except Exception as e:
                    print(f"Lỗi khi đọc {name} ({uuid}): {e}")

    except Exception as e:
        print(f"Lỗi khi kết nối đến thiết bị {address}: {e}")

async def main():
    # Thay bằng địa chỉ MAC của anchor DWM1001 của bạn
    device_address = "EB:C3:F1:BC:24:DD"  # Ví dụ, thay bằng địa chỉ thật
    await read_and_decode_anchor_data(device_address)

if __name__ == "__main__":
    asyncio.run(main())