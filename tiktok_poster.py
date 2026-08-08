"""Bước 5 (tùy chọn): Tự động đăng video lên TikTok ở chế độ riêng tư (SELF_ONLY) bằng
TikTok Content Posting API. Cần chạy `python tiktok_auth.py` một lần trước để lấy
TIKTOK_REFRESH_TOKEN (xem hướng dẫn trong tiktok_auth.py).

App chưa qua audit CHỈ được phép đăng lên account đang để Private (TikTok trả lỗi 403
"unaudited_client_can_only_post_to_private_accounts" nếu account đang Public).

Muốn một video cụ thể thành public sau khi đã đăng riêng tư (đã test thực tế, cần đủ cả 2 bước):
1. Tắt "Private account" cho toàn bộ tài khoản (Cài đặt và quyền riêng tư -> Quyền riêng tư)
2. Vào chính video đó, đổi privacy riêng của nó từ "Only me" thành "Everyone"
   (privacy của từng video độc lập với privacy tài khoản — tắt account Private thôi KHÔNG đủ
   để video cũ tự public, phải đổi cả hai)
"""
import time
from pathlib import Path
from typing import Optional

import requests

from config import TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REFRESH_TOKEN
from env_utils import update_env_var

TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

POLL_INTERVAL_SEC = 3
POLL_TIMEOUT_SEC = 120


def _raise_with_body(resp: requests.Response) -> None:
    """resp.raise_for_status() bỏ mất nội dung response — mà lỗi TikTok trả về (code/message cụ
    thể) luôn nằm trong body JSON, nên bọc lại để không mất thông tin debug quan trọng nhất."""
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise requests.HTTPError(f"{e} | response body: {resp.text[:1000]}", response=resp) from None


def _refresh_access_token() -> str:
    resp = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": TIKTOK_CLIENT_KEY,
            "client_secret": TIKTOK_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": TIKTOK_REFRESH_TOKEN,
        },
        timeout=30,
    )
    _raise_with_body(resp)
    data = resp.json()
    # TikTok có thể trả về refresh_token mới (rotate) — lưu lại để lần sau không bị hết hạn
    new_refresh_token = data.get("refresh_token")
    if new_refresh_token and new_refresh_token != TIKTOK_REFRESH_TOKEN:
        update_env_var("TIKTOK_REFRESH_TOKEN", new_refresh_token)
    return data["access_token"]


def post_video_draft(video_path: Path, caption: str) -> Optional[dict]:
    """Đăng video lên TikTok ở chế độ riêng tư (chỉ tài khoản của bạn xem được).
    Trả về status dict cuối cùng từ TikTok, hoặc None nếu chưa cấu hình TikTok (bỏ qua êm)."""
    if not TIKTOK_CLIENT_KEY or not TIKTOK_CLIENT_SECRET or not TIKTOK_REFRESH_TOKEN:
        print("[tiktok] Chưa cấu hình TikTok, bỏ qua bước đăng. Chạy `python tiktok_auth.py` để thiết lập.")
        return None

    access_token = _refresh_access_token()
    video_size = video_path.stat().st_size

    init_resp = requests.post(
        INIT_URL,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        json={
            "post_info": {
                "title": caption[:2200],
                "privacy_level": "SELF_ONLY",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": video_size,
                "total_chunk_count": 1,
            },
        },
        timeout=30,
    )
    _raise_with_body(init_resp)
    init_data = init_resp.json()
    error = init_data.get("error", {})
    if error.get("code") not in (None, "ok"):
        raise RuntimeError(f"TikTok từ chối khởi tạo bài đăng: {error}")

    publish_id = init_data["data"]["publish_id"]
    upload_url = init_data["data"]["upload_url"]

    upload_resp = requests.put(
        upload_url,
        headers={
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{video_size - 1}/{video_size}",
        },
        data=video_path.read_bytes(),
        timeout=120,
    )
    _raise_with_body(upload_resp)

    deadline = time.monotonic() + POLL_TIMEOUT_SEC
    while time.monotonic() < deadline:
        status_resp = requests.post(
            STATUS_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={"publish_id": publish_id},
            timeout=30,
        )
        _raise_with_body(status_resp)
        status_data = status_resp.json()["data"]
        status = status_data.get("status")
        if status == "PUBLISH_COMPLETE":
            return status_data
        if status == "FAILED":
            raise RuntimeError(f"TikTok báo đăng thất bại: {status_data}")
        time.sleep(POLL_INTERVAL_SEC)

    raise RuntimeError(f"Hết thời gian chờ TikTok xử lý video (publish_id={publish_id})")


if __name__ == "__main__":
    import sys
    video_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not video_arg or not video_arg.exists():
        print("Cách dùng: python tiktok_poster.py <đường_dẫn_video.mp4>")
        sys.exit(1)
    result = post_video_draft(video_arg, caption="Video test")
    print("Kết quả:", result)
