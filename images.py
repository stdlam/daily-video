"""Bước 3: Lấy ảnh minh họa từ Pexels (free, không giới hạn bản quyền)."""
import requests
from pathlib import Path
from config import PEXELS_API_KEY

PEXELS_URL = "https://api.pexels.com/v1/search"


def fetch_image(query: str, out_path: Path, orientation: str = "portrait") -> Path:
    """Tìm và tải 1 ảnh phù hợp với query. Trả về đường dẫn file ảnh."""
    if not PEXELS_API_KEY:
        raise RuntimeError("Thiếu PEXELS_API_KEY. Xem file .env.example")

    resp = requests.get(
        PEXELS_URL,
        headers={"Authorization": PEXELS_API_KEY},
        params={"query": query, "per_page": 5, "orientation": orientation},
        timeout=30,
    )
    resp.raise_for_status()
    results = resp.json().get("photos", [])
    if not results:
        # fallback: query chung chung hơn nếu không tìm thấy
        resp = requests.get(
            PEXELS_URL,
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": "background", "per_page": 5, "orientation": orientation},
            timeout=30,
        )
        resp.raise_for_status()
        results = resp.json().get("photos", [])

    img_url = results[0]["src"]["large2x"]
    img_data = requests.get(img_url, timeout=30).content
    out_path.write_bytes(img_data)
    return out_path


if __name__ == "__main__":
    from config import OUTPUT_DIR
    test_path = OUTPUT_DIR / "test_image.jpg"
    fetch_image("city sunset", test_path)
    print(f"Đã tải: {test_path}")
