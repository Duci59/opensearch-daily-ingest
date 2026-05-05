# OpenSearch Daily Ingest Calculator

Công cụ tự động tính toán và thống kê dung lượng ghi log (Ingest Size) hàng ngày của hệ thống OpenSearch. Tool được thiết kế tối ưu cho môi trường NOC/SOC, giúp theo dõi sức khỏe lưu trữ, phát hiện bất thường và dự báo dung lượng hệ thống.

## 🌟 Tính năng nổi bật

- **Theo dõi chính xác:** So sánh chênh lệch dung lượng index giữa 2 ngày để tính ra lượng data thực tế được ghi vào (Bytes, MB, GB).
- **Cơ chế Allowlist an toàn:** Chỉ thống kê các index hợp lệ (VD: `logs-*`, `metrics-*`), tự động bỏ qua các index hệ thống hoặc index rác.
- **Xử lý Rollover thông minh:** Tự động nhận diện và tính toán đúng dung lượng kể cả khi hệ thống chạy ISM (Index State Management) rollover sang index mới.
- **Ghi log chuyên nghiệp:** Tích hợp sẵn Log Rotation, tự động dọn dẹp log xoay vòng sau N ngày để tránh rác ổ cứng server.
- **Tách biệt cấu hình:** Thông tin kết nối (nhạy cảm) được lưu trong file `config.yml` riêng biệt.

---

## 🛠 Yêu cầu hệ thống

- Hệ điều hành: Linux (Ubuntu/CentOS/RedHat,...)
- Python: 3.x
- Thư viện Python: `requests`, `PyYAML`
- Quyền truy cập: Tài khoản OpenSearch có quyền đọc list indices (`cluster:monitor/state`) và quyền ghi (`write`) vào index đích.

### Cài đặt thư viện:
```bash
pip3 install requests pyyaml
```
# ⚙️ Hướng dẫn cài đặt & Cấu hình

## 1. Khởi tạo thư mục và phân quyền

```bash
sudo mkdir -p /etc/calculate_dailyingest/
sudo chown root:root /etc/calculate_dailyingest/
```

---

## 2. Tạo file cấu hình `config.yml`

Tạo file tại:

```
/etc/calculate_dailyingest/config.yml
```

Với nội dung mẫu:

```yaml
# Thông tin kết nối OpenSearch
opensearch:
  url: "https://<OPENSEARCH_IP>:9200"
  username: "admin"
  password: "your_password"
  verify_ssl: false

# Cấu hình lưu trữ và index
settings:
  state_file: "/tmp/opensearch_index_state.json"
  dest_index: "logs-ism-opensearch-pop-write" # Index lưu kết quả thống kê
  include_prefixes: 
    - "logs-"
    - "metrics-"
```

**Lưu ý:**  

```bash
chmod 600 /etc/calculate_dailyingest/config.yml
```

---

## 3. Đặt file script

```bash
sudo chmod +x /opt/calculate_daily_ingest.py
```

---

# 🚀 Hướng dẫn sử dụng (CLI)

```bash
python3 /opt/calculate_daily_ingest.py [OPTIONS]
```

## Các tham số

- `-c, --config`: /etc/calculate_dailyingest/config.yml  
- `-l, --log-file`: /var/log/os_daily_ingest.log  
- `-k, --keep-log-days`: mặc định 7  
- `--clear-state`: reset baseline  

---

## Ví dụ

```bash
sudo python3 /opt/calculate_daily_ingest.py -k 14
sudo python3 /opt/calculate_daily_ingest.py --clear-state
```

---

# ⏰ Cronjob

```bash
sudo crontab -e
```

```bash
59 23 * * * /usr/bin/python3 /opt/calculate_daily_ingest.py -c /etc/calculate_dailyingest/config.yml -l /var/log/os_daily_ingest.log -k 14
```

---

# 📊 Output JSON

```json
{
  "@timestamp": "2026-05-05T23:59:00.000Z",
  "target_index_name": "logs-app-000001",
  "daily_growth_bytes": 1073741824,
  "daily_growth_mb": 1024.0,
  "daily_growth_gb": 1.0
}
```
