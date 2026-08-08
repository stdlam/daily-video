"""Bước 5 (tùy chọn): Gửi video hoàn chỉnh qua Telegram bot để Lam tải về đăng tay."""
import requests
from pathlib import Path
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_to_telegram(video_path: Path, caption: str = ""):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[deliver] Chưa cấu hình Telegram, bỏ qua bước gửi. Video nằm ở:", video_path)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    with open(video_path, "rb") as f:
        resp = requests.post(
            url,
            data={"chat_id": TELEGRAM_CHAT_ID, "caption": caption[:1024]},
            files={"video": f},
            timeout=120,
        )
    resp.raise_for_status()
    print("[deliver] Đã gửi video qua Telegram.")
