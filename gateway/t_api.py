import requests
import time
from dotenv import load_dotenv
import os
load_dotenv()
sv_url = os.getenv("SV_URL") + ":" + os.getenv("PORT") + "/" + os.getenv("TOPIC")


def send_data_to_server(data):
    try:
        response = requests.post(sv_url, json=data)
        if response.status_code == 200:
            print("Dữ liệu đã được gửi thành công:", response.json())
        else:
            print(f"Lỗi khi gửi dữ liệu: {response.status_code}, {response.text}")
    except Exception as e:
        print("Lỗi khi kết nối tới server:", e)

# Giả lập dữ liệu từ module DWM1001
def get_uwb_data():
    # Dữ liệu giả lập (bạn thay bằng code nhận dữ liệu từ module DWM1001)
    return {
        "tag_id": "TAG12345",
        "distance": 2.35,  # Đơn vị: mét
        "timestamp": time.time()
    }

if __name__ == "__main__":
    while True:
        # Lấy dữ liệu từ module
        data = get_uwb_data()

        # Gửi dữ liệu lên server
        send_data_to_server(data)

        # Đợi 2 giây trước khi gửi dữ liệu tiếp theo
        time.sleep(2)