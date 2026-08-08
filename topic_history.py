"""Lưu lịch sử chủ đề đã dùng để tránh lặp lại khi để LLM tự nghĩ chủ đề (chạy tự động, không
truyền topic). File topic_history.txt được commit lại vào repo sau mỗi lần chạy trên GitHub
Actions (xem .github/workflows/daily-video.yml) để lịch sử không mất giữa các lần chạy CI."""
from pathlib import Path

HISTORY_PATH = Path(__file__).parent / "topic_history.txt"
MAX_HISTORY = 50


def load_recent_topics() -> list:
    if not HISTORY_PATH.exists():
        return []
    return [line.strip() for line in HISTORY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_topic(topic: str) -> None:
    topics = load_recent_topics()
    topics.append(topic)
    topics = topics[-MAX_HISTORY:]
    HISTORY_PATH.write_text("\n".join(topics) + "\n", encoding="utf-8")
