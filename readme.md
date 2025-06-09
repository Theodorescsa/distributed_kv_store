# 🗂️ Distributed Key-Value Store

Một hệ thống lưu trữ dạng key-value phân tán sử dụng Python/Django, Redis, Docker nhằm đảm bảo:
- Khả năng **chịu lỗi node**
- Đồng bộ dữ liệu giữa các node
- Phục hồi trạng thái khi node khởi động lại
- Theo dõi tình trạng sống/chết của các node (`heartbeat`)
- Gửi email thông báo khi ghi dữ liệu (nếu cấu hình SMTP)

---

## 🛠️ Công nghệ sử dụng

| Thành phần       | Công cụ/Thư viện |
|------------------|------------------|
| Backend API      | Django + DRF     |
| Lưu trữ          | Redis            |
| Đồng bộ nền       | Celery (có thể tắt) |
| Môi trường       | Docker Compose   |
| HTTP client nội bộ| `requests`       |

---

## 🚀 Cách chạy hệ thống

1. **Clone dự án**

```bash
git clone https://github.com/your-username/distributed-kv-store.git
cd distributed-kv-store
Cấu hình biến môi trường (trong .env)

env
Sao chép
Chỉnh sửa
REDIS_HOST=redis1
REDIS_PORT=6379
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your@gmail.com
EMAIL_HOST_PASSWORD=yourpassword
Chạy hệ thống bằng Docker Compose

bash
Sao chép
Chỉnh sửa
docker-compose up --build
Hệ thống bao gồm:

3 Node: node1, node2, node3 (chạy trên các port 8001, 8002, 8003)

1 Redis dùng chung (redis1)

🧪 Kịch bản kiểm thử
✅ I. CRUD cơ bản
Ghi key

http
Sao chép
Chỉnh sửa
POST /kv/
{
  "key": "username123",
  "value": "mci_admin"
}
Đọc key

h
Sao chép
Chỉnh sửa
GET /kv/?key=username123
Xóa key

http
Sao chép
Chỉnh sửa
DELETE /kv/?key=username123
✅ II. Kịch bản sao lưu & nhất quán
Kiểm tra bản sao (replica)

Gửi POST key backup1 vào node1

Kiểm tra GET /snapshot/ ở node2 (hoặc replica kế tiếp)

Kiểm tra tính nhất quán

PUT key-x tại node A

GET key-x từ node B → Giá trị giống nhau

✅ III. Kịch bản chịu lỗi
Tạm dừng node chính

bash
Sao chép
Chỉnh sửa
docker-compose stop node2
PUT key="crash_test" từ node1 (hash về node2)

Hệ thống sẽ ghi vào node tiếp theo

Khởi động lại node bị lỗi

bash
Sao chép
Chỉnh sửa
docker-compose start node2
Node sẽ tự khôi phục từ node còn sống (nhờ try_restore)

✅ IV. Heartbeat & phát hiện lỗi
Gửi heartbeat 30s/lần

Tự động chạy sau khi app khởi động

Dữ liệu được ghi vào Redis:

bash
Sao chép
Chỉnh sửa
GET node_status:node1
=> "up"
✅ V. Định dạng & giao thức
Kiểm tra định dạng JSON

Tất cả API đều nhận/trả về JSON chuẩn

Test với Postman: PUT, GET, DELETE, /snapshot, /restore

✅ VI. Gửi email
Gửi email khi ghi key

Khi POST key="email_test" sẽ gửi email nếu SMTP được cấu hình

✅ VII. Kịch bản toàn diện (integration)
Chuỗi kiểm thử:

http
Sao chép
Chỉnh sửa
PUT key="test1" → node1
GET key="test1" → node2
DELETE key="test1" → node3
GET key="test1" → node1  → null
→ Dữ liệu luân chuyển đúng logic định tuyến, xóa đúng mọi node.

🔧 Cấu trúc thư mục chính
bash
Sao chép
Chỉnh sửa
distributed_kv_store/
│
├── docker-compose.yml
├── node1/  # Django project
├── node2/
├── node3/
├── .env
└── README.md
📬 Liên hệ
Nếu bạn gặp lỗi hoặc cần hỗ trợ, vui lòng mở issue hoặc liên hệ tại:
📧 Email: support@mci.edu.vn

yaml
Sao chép
Chỉnh sửa

--- 

Bạn có thể lưu nội dung trên thành file `README.md` và commit lên repo. Nếu cần tạo README riêng cho từng node 