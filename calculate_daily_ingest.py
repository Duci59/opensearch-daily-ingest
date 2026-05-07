import argparse
import requests
import json
import os
import yaml
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def setup_logger(log_file, keep_days):
    logger = logging.getLogger("OS_Ingest")
    logger.setLevel(logging.INFO)

    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=keep_days)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)
        logger.addHandler(console)

    return logger

def load_config(config_path, logger):
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Lỗi khi đọc file config tại {config_path}: {e}")
        exit(1)

def get_current_index_sizes(conf, logger):
    os_conf = conf['opensearch']
    set_conf = conf['settings']
    url = f"{os_conf['url']}/_cat/indices?format=json&bytes=b"
    try:
        response = requests.get(
            url, auth=(os_conf['username'], os_conf['password']), verify=os_conf['verify_ssl']
        )
        response.raise_for_status()
        indices = response.json()

        include = set_conf.get('include_prefixes', ['logs-', 'metrics-'])
        return {
            item['index']: int(item.get('pri.store.size', 0) or 0)
            for item in indices
            if any(item['index'].startswith(pre) for pre in include)
        }

    except Exception as e:
        logger.error(f"Lỗi khi gọi API OpenSearch: {e}")
        return {}

def send_to_opensearch(conf, logs, logger):
    if not logs:
        logger.info("Không có dữ liệu nào để gửi.")
        return

    os_conf = conf['opensearch']
    dest_index = conf['settings']['dest_index']
    url = f"{os_conf['url']}/{dest_index}/_bulk"
    headers = {'Content-Type': 'application/x-ndjson'}
    bulk_data = ""
    for log in logs:
        bulk_data += json.dumps({"index": {"_index": dest_index}}) + "\n"
        bulk_data += json.dumps(log) + "\n"
    try:
        response = requests.post(
            url, auth=(os_conf['username'], os_conf['password']),
            headers=headers, data=bulk_data, verify=os_conf['verify_ssl']
        )
        response.raise_for_status()
        logger.info(f"Đã gửi thành công {len(logs)} bản ghi log ingest vào {dest_index}.")
    except Exception as e:
        logger.error(f"Lỗi khi gửi dữ liệu vào OpenSearch: {e}")

def main():
    parser = argparse.ArgumentParser(description="Tool tính toán dung lượng Ingest hàng ngày của OpenSearch.")
    parser.add_argument('-c', '--config', type=str, default='/etc/calculate_dailyingest/config.yml',
                        help='Đường dẫn tới file cấu hình config.yml')
    parser.add_argument('-l', '--log-file', type=str, default='/var/log/os_daily_ingest.log',
                        help='Đường dẫn lưu file log hoạt động của tool')
    parser.add_argument('-k', '--keep-log-days', type=int, default=7,
                        help='Số ngày giữ lại file log hoạt động')
    parser.add_argument('--clear-state', action='store_true',
                        help='Force xóa file state cũ trước khi chạy (Reset base line về 0)')

    args = parser.parse_args()
    logger = setup_logger(args.log_file, args.keep_log_days)
    logger.info("=== Bắt đầu tiến trình thu thập dung lượng Ingest ===")

    config = load_config(args.config, logger)
    set_conf = config['settings']
    state_file = set_conf['state_file']

    if args.clear_state and os.path.exists(state_file):
        os.remove(state_file)
        logger.info(f"Đã xóa file state cũ tại {state_file} do có cờ --clear-state")

    current_sizes = get_current_index_sizes(config, logger)
    if not current_sizes:
        logger.warning("Không lấy được danh sách index hiện tại hoặc không có index nào match điều kiện. Kết thúc.")
        return

    previous_sizes = {}
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            previous_sizes = json.load(f)

    logs_to_send = []
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')

    for index_name, current_size in current_sizes.items():
        prev_size = previous_sizes.get(index_name, 0)
        daily_growth_bytes = current_size - prev_size
        if daily_growth_bytes < 0:
            daily_growth_bytes = current_size

        logs_to_send.append({
            "@timestamp": timestamp,
            "target_index_name": index_name,
            "daily_growth_bytes": daily_growth_bytes,
            "daily_growth_mb": round(daily_growth_bytes / (1024**2), 2),
            "daily_growth_gb": round(daily_growth_bytes / (1024**3), 4)
        })

    send_to_opensearch(config, logs_to_send, logger)
    with open(state_file, 'w') as f:
        json.dump(current_sizes, f)

    logger.info("=== Tiến trình hoàn tất ===")

if __name__ == "__main__":
    main()
