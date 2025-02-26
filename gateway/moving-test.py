import asyncio
import struct
import math
from collections import deque
from bleak import BleakClient

# Định nghĩa UUID
LOCATION_DATA_UUID = "003bbdf2-c634-4b3d-ab56-7ec889b89a37"
LOCATION_DATA_MODE_UUID = "a02b947e-df97-4516-996a-1882521e0ead"

# Lớp lưu trữ dữ liệu mẫu
class PositionSample:
    def __init__(self, x, y, z, timestamp):
        self.x = x  # m
        self.y = y  # m
        self.z = z  # m
        self.timestamp = timestamp  # giây

# Hàm giải mã dữ liệu vị trí từ notification
def decode_location_data(data, mode=2):
    """Giải mã dữ liệu vị trí từ notification (giả định Mode 2)."""
    if mode == 2:  # Position + Distances
        if len(data) < 13:
            return None
        x, y, z, quality = struct.unpack("<iiiB", data[1:14])
        position = {"x": x / 1000.0, "y": y / 1000.0, "z": z / 1000.0, "quality": quality}
        return position  # Chỉ lấy position để đơn giản
    return None

# Hàm tính khoảng cách Euclidean giữa hai vị trí
def calculate_distance(pos1, pos2):
    """Tính khoảng cách giữa hai vị trí (m)."""
    dx = pos2.x - pos1.x
    dy = pos2.y - pos1.y
    dz = pos2.z - pos1.z
    return math.sqrt(dx**2 + dy**2 + dz**2)

# Hàm tính tốc độ từ hai mẫu
def calculate_velocity(sample1, sample2):
    """Tính tốc độ (m/s) từ hai mẫu liên tiếp."""
    distance = calculate_distance(sample1, sample2)
    delta_t = sample2.timestamp - sample1.timestamp
    print("time1: ", sample1.timestamp)
    print("time2: ", sample2.timestamp)
    if delta_t <= 0:  # Tránh chia cho 0
        return 0
    return distance / delta_t

# Hàm xác định trạng thái tag
def determine_tag_state(buffer, velocity_threshold=0.5):
    """Xác định tag di chuyển hay đứng yên dựa trên tốc độ trung bình."""
    if len(buffer) < 2:  # Cần ít nhất 2 mẫu để tính tốc độ
        return "unknown"

    velocities = []
    for i in range(len(buffer) - 1):
        v = calculate_velocity(buffer[i], buffer[i + 1])
        velocities.append(v)

    avg_velocity = sum(velocities) / len(velocities)
    print(f"Tốc độ trung bình: {avg_velocity:.2f} m/s")

    if avg_velocity > velocity_threshold:
        return "moving"
    return "stationary"

# Hàm xử lý notification
async def notification_handler(sender, data, buffer, loop):
    """Xử lý dữ liệu nhận từ notification và cập nhật buffer."""
    timestamp = loop.time()  # Thời gian nhận dữ liệu
    position = decode_location_data(data)
    if position:
        sample = PositionSample(position["x"], position["y"], position["z"], timestamp)
        buffer.append(sample)
        print(f"Nhận vị trí: X={position['x']:.3f}, Y={position['y']:.3f}, Z={position['z']:.3f}, t={timestamp:.2f}s")

        # Giới hạn buffer ở 5 mẫu
        if len(buffer) > 5:
            buffer.popleft()

        # Xác định trạng thái
        state = determine_tag_state(buffer)
        print(f"Trạng thái tag: {state}")

# Hàm thiết lập notification
async def setup_notifications(address):
    """Kết nối và nhận notification từ module."""
    buffer = deque(maxlen=5)  # Buffer lưu tối đa 5 mẫu
    loop = asyncio.get_event_loop()

    async with BleakClient(address, timeout=20.0) as client:
        if not await client.is_connected():
            print(f"Không thể kết nối tới {address}")
            return

        print(f"Đã kết nối tới {address}")

        # Đọc mode để xác nhận (giả định Mode 2)
        loc_mode_data = await client.read_gatt_char(LOCATION_DATA_MODE_UUID)
        loc_mode = int(loc_mode_data[0])
        print(f"Location Data Mode: {loc_mode}")

        # Đăng ký notification
        await client.start_notify(LOCATION_DATA_UUID, lambda sender, data: asyncio.ensure_future(notification_handler(sender, data, buffer, loop)))
        print(f"Đã đăng ký notification cho {LOCATION_DATA_UUID}")

        # Chờ vô hạn để nhận notification
        try:
            await asyncio.Event().wait()  # Chờ mãi mãi, dừng bằng Ctrl+C
        except KeyboardInterrupt:
            print("Dừng bởi người dùng")
        finally:
            await client.stop_notify(LOCATION_DATA_UUID)
            print("Đã dừng notification")

# Hàm chính
async def main():
    module_address = "EB:52:53:F5:D5:90"  # Thay bằng địa chỉ module
    await setup_notifications(module_address)

if __name__ == "__main__":
    asyncio.run(main())