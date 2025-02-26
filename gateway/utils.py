import json

def print_result(data):
    print(json.dumps(data, indent=4))

# Hàm chuyển dữ liệu thô thành chuỗi bit
def raw_to_bits(data):
    bit_string = ""
    for byte in data:
        bits = bin(byte)[2:].zfill(8)
        bit_string += bits + " "
    return bit_string.strip()


