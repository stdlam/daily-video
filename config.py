"""Cấu hình chung cho pipeline auto video."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")  # đọc file .env và nạp vào biến môi trường
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"
MUSIC_DIR = ASSETS_DIR / "music"

OUTPUT_DIR.mkdir(exist_ok=True)
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

# --- API keys (đọc từ biến môi trường / .env) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# TikTok Content Posting API - đăng video tự động ở chế độ riêng tư (SELF_ONLY).
# Thiết lập lần đầu: xem hướng dẫn trong tiktok_auth.py
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TIKTOK_REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", "https://httpbingo.org/get")
TIKTOK_REFRESH_TOKEN = os.getenv("TIKTOK_REFRESH_TOKEN", "")

# --- Video settings (TikTok chuẩn 9:16) ---
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30

# --- Voice settings (edge-tts) ---
TTS_VOICE = "vi-VN-HoaiMyNeural"  # giọng mặc định khi không truyền --voice / --lang không xác định
# Tốc độ đọc — tăng để video có nhịp độ nhanh hơn. Đây là tốc độ NGAY TỪ edge-tts (không phải
# tăng tốc video sau khi render), nên timing WordBoundary trả về đã khớp sẵn với audio nhanh hơn
# -> karaoke highlight tự động đồng bộ đúng, không cần tính lại.
TTS_RATE = "+20%"

# --- Ngôn ngữ mặc định của kịch bản + giọng đọc tương ứng cho từng ngôn ngữ ---
DEFAULT_LANG = "vi"
DEFAULT_VOICES = {
    "vi": "vi-VN-HoaiMyNeural",
    "en": "en-US-AriaNeural",
    "ja": "ja-JP-NanamiNeural",
    "ko": "ko-KR-SunHiNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "fr": "fr-FR-DeniseNeural",
    "es": "es-ES-ElviraNeural",
}

# --- LLM model (Groq free tier) ---
GROQ_MODEL = "openai/gpt-oss-120b"

# --- Số cảnh mặc định trên mỗi video ---
NUM_IMAGES = 5

# --- Style video: "physics" (bóng nảy tự sinh, an toàn bản quyền) hoặc "slideshow" (ảnh + Ken Burns) ---
VIDEO_STYLE = "physics"
