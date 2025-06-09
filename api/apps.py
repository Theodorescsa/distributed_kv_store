# api/apps.py
import os
import threading
import time
from django.apps import AppConfig
from django.conf import settings
import redis, requests

class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    # ----- cấu hình cụm -----
    NODES = {
        "node1": "http://node1:8000",
        "node2": "http://node2:8000",
        "node3": "http://node3:8000",
    }

    # -------------------------------------------------
    #             HÀM CHẠY KHI APP KHỞI ĐỘNG
    # -------------------------------------------------
    def ready(self):
        print("[AppConfig] ready() được gọi")
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()
        print("[AppConfig] heartbeat_loop đã khởi động")
        # Bảo đảm chỉ chạy 1 lần trong process chính (django autoreload)
        if os.getenv("RUN_MAIN") != "true":
            return

        # 1) khôi phục dữ liệu nếu cần
        self.try_restore()

        # 2) khởi động vòng lặp heartbeat 30 s
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()

    # -------------------------------------------------
    #                 KHÔI PHỤC DỮ LIỆU
    # -------------------------------------------------
    def try_restore(self):
        cur_node = os.getenv("NODE_ID")
        r = redis.Redis(host=os.getenv("REDIS_HOST"), port=settings.REDIS_PORT)
        # Chọn node khác bất kỳ còn sống để lấy snapshot
        for node_id, url in self.NODES.items():
            if node_id == cur_node:
                continue
            try:
                snap = requests.get(f"{url}/snapshot/", timeout=3).json()
                # Nạp các key kiểu string
                for k, v in snap.items():
                    if not v.startswith("<non-string"):
                        r.set(k, v)
                print(f"[Restore] {cur_node} nạp {len(snap)} khóa từ {node_id}")
                break
            except Exception as e:
                print(f"[Restore] Không thể lấy snapshot từ {node_id}: {e}")

    # -------------------------------------------------
    #                 HÀM HEARTBEAT
    # -------------------------------------------------
    def heartbeat_once(self):
        r = redis.Redis(host=os.getenv("REDIS_HOST"), port=settings.REDIS_PORT)
        for node_id, url in self.NODES.items():
            try:
                resp = requests.get(f"{url}/health/", timeout=3)
                status = "up" if resp.status_code == 200 else "down"
                print(f"[Heartbeat] node {node_id}: {status}")
            except requests.exceptions.RequestException:
                status = "down"
            r.set(f"node_status:{node_id}", status)
        # (Tuỳ chọn) log nhỏ
        print("[Heartbeat] cập nhật trạng thái node_status:*")

    def heartbeat_loop(self):
        while True:
            try:
                self.heartbeat_once()
            except Exception as e:
                print("[Heartbeat error]", e)
            time.sleep(30)      # 30 giây/lần
