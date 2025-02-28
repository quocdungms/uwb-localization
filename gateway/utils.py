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


def decode_operation_mode(op_mode: bytes) -> str:
    return 'tag' if (op_mode[0] & 0x80) == 0 else 'anchor'


