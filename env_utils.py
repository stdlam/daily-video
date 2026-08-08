"""Helper cập nhật/thêm biến vào file .env (dùng khi cần lưu token mới, vd. TikTok refresh_token)."""
import re
from pathlib import Path

ENV_PATH = Path(__file__).parent / ".env"


def update_env_var(key: str, value: str) -> None:
    """Cập nhật giá trị của `key` trong .env nếu đã tồn tại, ngược lại thêm dòng mới."""
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    pattern = re.compile(rf"^{re.escape(key)}=")
    for i, line in enumerate(lines):
        if pattern.match(line):
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
