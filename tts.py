"""Bước 2: Tạo giọng đọc bằng edge-tts (free, không cần API key)."""
import asyncio
import time
from pathlib import Path
from typing import List, Tuple
import edge_tts
from config import TTS_VOICE, TTS_RATE

MAX_RETRIES = 3
# Tỷ lệ tối thiểu số ký tự đã thực sự được đọc (theo WordBoundary edge-tts trả về) so với text
# gốc. Dùng coverage theo ký tự thay vì ngưỡng "giây/ký tự" cố định vì tốc độ đọc thực tế thay đổi
# khá nhiều tùy câu chữ (dấu câu, độ dài từ...) nên không có ngưỡng thời lượng cố định nào đáng tin
# cậy — coverage theo WordBoundary phản ánh đúng việc audio có bị cắt cụt giữa chừng hay không
# (vd. do WebSocket tới dịch vụ của Microsoft bị ngắt kết nối).
MIN_COVERAGE_RATIO = 0.7


async def _generate(text: str, out_path: Path, voice: str = TTS_VOICE, rate: str = TTS_RATE) -> Tuple[float, List[dict]]:
    """Stream audio + word-boundary metadata từ edge-tts, ghi audio ra file, trả về (coverage,
    words) — coverage là tỷ lệ ký tự đã đọc được so với text gốc, words là timing từng từ
    ({"text","start","end"} tính bằng giây) để đồng bộ highlight phụ đề theo giọng đọc. `rate` áp
    dụng ngay tại nguồn (edge-tts) nên timing trả về đã khớp sẵn với audio nhanh/chậm hơn."""
    communicate = edge_tts.Communicate(text, voice, boundary="WordBoundary", rate=rate)
    audio_bytes = bytearray()
    words: List[dict] = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            words.append({
                "text": chunk["text"],
                "start": chunk["offset"] / 10_000_000,
                "end": (chunk["offset"] + chunk["duration"]) / 10_000_000,
            })
    out_path.write_bytes(audio_bytes)
    spoken_chars = sum(len(w["text"]) for w in words)
    coverage = spoken_chars / len(text) if text else 1.0
    return coverage, words


def generate_voice(text: str, out_path: Path, voice: str = TTS_VOICE, rate: str = TTS_RATE) -> List[dict]:
    """Tạo file mp3 giọng đọc từ text, trả về timing từng từ ({"text","start","end"} tính bằng
    giây) để video_builder đồng bộ highlight phụ đề theo giọng đọc. Tự retry nếu edge-tts đọc
    thiếu nội dung (audio bị cắt cụt giữa chừng do WebSocket tới dịch vụ của Microsoft bị ngắt)."""
    last_err = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            coverage, words = asyncio.run(_generate(text, out_path, voice, rate))
            if coverage >= MIN_COVERAGE_RATIO:
                return words
            last_err = RuntimeError(f"audio bị cắt cụt (chỉ đọc được ~{coverage:.0%} nội dung)")
        except Exception as e:
            last_err = e

        if attempt < MAX_RETRIES:
            print(f"  [tts] Lỗi tạo giọng đọc (lần {attempt}/{MAX_RETRIES}): {last_err} — thử lại...")
            time.sleep(1.5 * attempt)

    raise RuntimeError(f"Không tạo được giọng đọc hợp lệ sau {MAX_RETRIES} lần thử: {last_err}")


if __name__ == "__main__":
    from config import OUTPUT_DIR
    test_path = OUTPUT_DIR / "test_voice.mp3"
    words = generate_voice("Xin chào, đây là giọng đọc thử nghiệm.", test_path)
    print(f"Đã tạo: {test_path}")
    print(f"Số từ: {len(words)}")
