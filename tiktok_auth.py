"""
Script chạy MỘT LẦN DUY NHẤT để lấy TikTok refresh_token, phục vụ việc tự động đăng video
(chế độ riêng tư - SELF_ONLY) trong main.py.

CHUẨN BỊ TRƯỚC (làm trên trang TikTok for Developers, không thể tự động hoá bước này):
1. Tạo app tại https://developers.tiktok.com/apps -> "Manage apps" -> "Create an app"
2. Trong app, thêm product "Content Posting API"
3. Ở phần Scopes, bật "video.publish" (và "user.info.basic" nếu có)
4. Ở phần "Sandbox" của app, thêm chính tài khoản TikTok của bạn vào "Target users" — bước này
   cho phép app ĐĂNG ĐƯỢC lên tài khoản của bạn ngay cả khi app chưa qua audit, miễn là chỉ đăng
   ở chế độ riêng tư (SELF_ONLY, đúng như pipeline này dùng)
4b. QUAN TRỌNG: mở app TikTok trên điện thoại -> Hồ sơ -> "Cài đặt và quyền riêng tư" ->
    "Quyền riêng tư" -> bật "Tài khoản riêng tư" (Private account) cho chính tài khoản TikTok đó.
    App CHƯA qua audit chỉ được phép đăng lên tài khoản đã ở chế độ riêng tư — nếu bỏ qua bước
    này, TikTok trả lỗi 403 "unaudited_client_can_only_post_to_private_accounts" khi gọi API.
5. Trong app settings, thêm Redirect URI: https://httpbingo.org/get
   (TikTok bắt buộc redirect URI phải là HTTPS thật, không chấp nhận localhost — dùng httpbingo.org
   vì nó chỉ echo lại query string, không cần bạn tự dựng server hay sở hữu domain nào cả.
   Nếu httpbingo.org cũng lỗi, đổi sang URI echo khác (vd. httpbin.org/get) và cập nhật
   TIKTOK_REDIRECT_URI trong .env cho khớp)
6. Copy "Client key" và "Client secret" của app vào file .env:
   TIKTOK_CLIENT_KEY=...
   TIKTOK_CLIENT_SECRET=...

CHẠY:
    python tiktok_auth.py

Trình duyệt sẽ mở ra để bạn đăng nhập TikTok và bấm "Cho phép" (chỉ bạn thao tác, script không
bao giờ thấy mật khẩu của bạn). Sau khi cấp quyền, TikTok sẽ chuyển bạn tới httpbingo.org — trang đó
hiển thị JSON chứa "code" trong "args". Copy toàn bộ URL trên thanh địa chỉ (hoặc chỉ giá trị code)
rồi dán lại vào terminal khi script hỏi. refresh_token sẽ được tự động lưu vào .env, từ đó pipeline
(main.py) có thể tự đăng video mà không cần chạy lại script này.
"""
import urllib.parse

import requests

from config import TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REDIRECT_URI
from env_utils import update_env_var

AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
SCOPES = "user.info.basic,video.publish"


def _extract_code(pasted: str) -> str:
    """Chấp nhận cả URL đầy đủ (vd. https://httpbingo.org/get?code=XXX&state=...) lẫn chỉ giá trị
    code người dùng tự copy ra."""
    pasted = pasted.strip()
    if "code=" in pasted:
        query = urllib.parse.urlparse(pasted).query or pasted.split("?", 1)[-1]
        params = urllib.parse.parse_qs(query)
        code = params.get("code", [None])[0]
        if code:
            return code
    return pasted


def main():
    if not TIKTOK_CLIENT_KEY or not TIKTOK_CLIENT_SECRET:
        raise RuntimeError(
            "Thiếu TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET trong .env — xem hướng dẫn ở đầu file "
            "tiktok_auth.py để tạo app trên TikTok for Developers trước."
        )

    query = urllib.parse.urlencode({
        "client_key": TIKTOK_CLIENT_KEY,
        "scope": SCOPES,
        "response_type": "code",
        "redirect_uri": TIKTOK_REDIRECT_URI,
        "state": "tiktok_auth_local",
    })
    auth_url = f"{AUTHORIZE_URL}?{query}"

    print("Mở URL này trong trình duyệt, đăng nhập TikTok và bấm \"Cho phép\":")
    print(f"\n{auth_url}\n")
    print(f"Sau khi cấp quyền, bạn sẽ được chuyển tới {TIKTOK_REDIRECT_URI} với JSON hiện ra.")
    pasted = input("Dán URL đầy đủ trên thanh địa chỉ (hoặc chỉ giá trị \"code\" trong JSON) rồi Enter: ")
    code = _extract_code(pasted)
    if not code:
        raise RuntimeError("Không đọc được authorization code từ nội dung đã dán.")

    resp = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": TIKTOK_CLIENT_KEY,
            "client_secret": TIKTOK_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": TIKTOK_REDIRECT_URI,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "refresh_token" not in data:
        raise RuntimeError(f"TikTok không trả về refresh_token: {data}")

    update_env_var("TIKTOK_REFRESH_TOKEN", data["refresh_token"])
    print("\nĐã lưu TIKTOK_REFRESH_TOKEN vào .env.")
    print("Từ giờ chạy main.py, pipeline sẽ tự đăng video lên TikTok (chế độ riêng tư).")


if __name__ == "__main__":
    main()
