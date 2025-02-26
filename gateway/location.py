import asyncio
import struct
from bleak import BleakScanner, BleakClient

from utils import print_result

# UUIDs từ tài liệu
NAME_UUID = "00002a00-0000-1000-8000-00805f9b34fb"  # Label (GAP service)
LOC_DATA_MODE_UUID = "a02b947e-df97-4516-996a-1882521e0ead"  # Location Data Mode
LOC_DATA_UUID = "003bbdf2-c634-4b3d-ab56-7ec889b89a37"  # Location Data



# Hàm chuyển dữ liệu thô thành chuỗi bit
def raw_to_bits(data):
    bit_string = ""
    for byte in data:
        bits = bin(byte)[2:].zfill(8)
        bit_string += bits + " "
    return bit_string.strip()


def decode_location_mode_0(data):
    result = {}
    location_mode = data[0]
    result["Mode:"] = location_mode
    x, y, z, quality_position = struct.unpack("<iiiB", data[1:14])
    result["Position"] = {
        "X": x / 1000,  # Chuyển từ mm sang m
        "Y": y / 1000,
        "Z": z / 1000,
        "Quality Factor": quality_position
    }
    return result

def decode_location_mode_1(data):
    result = {}
    distances = []
    distance_count = data[0]

    result["Distances count:"] = distance_count

    for i in range(distance_count):
        offset = 1 + i * 7
        node_id, distance, quality = struct.unpack("<H i B", data[offset:offset + 7])
        distances.append({
            "Node ID": node_id,
            "Distance": distance / 1000,  # Chuyển từ mm sang m
            "Quality Factor": quality
        })
    result["Distances"] = distances


    return result



# Hàm giải mã Location Data Mode 2 (Position + Distances)
def decode_location_mode_2(data):
    result = {}
    mode_0 = decode_location_mode_0(data[:14])
    mode_1 = decode_location_mode_1(data[14:])
    result.update(mode_0)
    result.update(mode_1)
    return result

# data = bytearray(b'\x02\xc3\x02\x00\x00\x1e\x02\x00\x00i\x04\x00\x008\x04\x0f')
# data_1 =  bytearray(b'\x02\xc3\x02\x00\x00\x1e\x02\x00\x00i\x04\x00\x008\x04\x0f\xd4\x0e\t\x00\x00d\x9a\xd2y\x06\x00\x00d\x11\xc5-\x08\x00\x00d\x0e\xc6\xed\x08\x00\x00d')
#
# print_result(decode_location_mode_1(data_1[14:]))