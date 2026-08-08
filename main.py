"""
Pipeline auto tạo video TikTok - chạy toàn bộ từ đầu đến cuối.

Cách dùng:
    python main.py "chủ đề video" [--background physics|slideshow] [--voice <edge-tts voice>]
                                   [--lang vi|en|...] [--rate +20%]

    Không truyền --background/--voice/--lang/--rate thì dùng mặc định trong config.py.

Yêu cầu: đã cài dependencies (pip install -r requirements.txt),
đã set biến môi trường GROQ_API_KEY và PEXELS_API_KEY (xem .env.example).
"""
import argparse
import re
import shutil
import random
from pathlib import Path
from datetime import datetime
from typing import Optional

from config import OUTPUT_DIR, MUSIC_DIR, NUM_IMAGES, VIDEO_STYLE, DEFAULT_LANG, DEFAULT_VOICES, TTS_VOICE, TTS_RATE
from script_gen import generate_script
from tts import generate_voice
from images import fetch_image
from video_builder import build_scene_clip, build_scene_clip_physics, concat_clips
from deliver import send_to_telegram
from tiktok_poster import post_video_draft


def _sanitize_filename(name: str) -> str:
    """Loại bỏ ký tự không hợp lệ trong tên file (vd. '/' bị hiểu thành thư mục con), vì tiêu đề
    do LLM sinh ra có thể chứa các ký tự này (vd. ngày tháng viết kiểu "2/9")."""
    cleaned = re.sub(r'[\\/:*?"<>|]+', '_', name).strip('_ ')
    return cleaned or "video"


def run_pipeline(
    topic: str,
    background: str = VIDEO_STYLE,
    voice: Optional[str] = None,
    lang: str = DEFAULT_LANG,
    rate: str = TTS_RATE,
) -> Path:
    resolved_voice = voice or DEFAULT_VOICES.get(lang, TTS_VOICE)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = OUTPUT_DIR / run_id
    work_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"[1/4] Đang tạo script cho chủ đề: {topic} (ngôn ngữ: {lang}, nền: {background}, "
        f"giọng: {resolved_voice}, tốc độ: {rate})"
    )
    script = generate_script(topic, num_scenes=NUM_IMAGES, lang=lang)
    title = script["title"]
    scenes = script["scenes"]
    print(f"  → Tiêu đề: {title} ({len(scenes)} cảnh)")

    clip_paths = []
    for i, scene in enumerate(scenes):
        narration = scene["narration"]
        print(f"[2/4] Cảnh {i+1}/{len(scenes)}: {narration[:50]}...")

        audio_path = work_dir / f"voice_{i}.mp3"
        clip_path = work_dir / f"clip_{i}.mp4"
        word_timings = generate_voice(narration, audio_path, voice=resolved_voice, rate=rate)

        if background == "physics":
            # Nền bóng nảy tự sinh bằng code — không cần ảnh, không dính bản quyền
            build_scene_clip_physics(audio_path, word_timings, clip_path, seed=i)
        else:
            image_query = scene["image_query"]
            image_path = work_dir / f"image_{i}.jpg"
            fetch_image(image_query, image_path)
            build_scene_clip(image_path, audio_path, word_timings, clip_path)

        clip_paths.append(clip_path)

    print("[3/4] Đang ghép các cảnh lại + thêm nhạc nền...")
    music_files = list(MUSIC_DIR.glob("*.mp3"))
    music_path = random.choice(music_files) if music_files else None
    if not music_path:
        print("  (Không tìm thấy nhạc nền trong assets/music/ — video sẽ không có nhạc)")

    safe_title = _sanitize_filename(title)[:30].replace(' ', '_').strip('_')
    final_path = OUTPUT_DIR / f"{run_id}_{safe_title}.mp4"
    concat_clips(clip_paths, final_path, music_path)

    # dọn file tạm của từng scene, giữ lại video final
    shutil.rmtree(work_dir, ignore_errors=True)

    print(f"[4/4] Hoàn tất: {final_path}")

    print("Đang đăng video lên TikTok (chế độ riêng tư, nếu đã cấu hình)...")
    try:
        tiktok_result = post_video_draft(final_path, caption=title)
        if tiktok_result:
            print(
                "  → Đã đăng lên TikTok (riêng tư). Muốn video này public: mở app TikTok, "
                "tắt Private account CHO TÀI KHOẢN, rồi vào chính video này đổi privacy riêng "
                "thành \"Everyone\" (cần cả 2 bước, đã test thực tế)."
            )
    except Exception as e:
        print(f"  (Đăng TikTok thất bại, video vẫn được lưu tại {final_path}: {e})")

    print("Đang gửi video qua Telegram (nếu đã cấu hình)...")
    send_to_telegram(final_path, caption=title)

    return final_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pipeline auto tạo video TikTok")
    parser.add_argument(
        "topic", nargs="?", default="3 mẹo tiết kiệm tiền mỗi tháng",
        help="Chủ đề video (mặc định: %(default)r)",
    )
    parser.add_argument(
        "--background", "-b", choices=["physics", "slideshow"], default=VIDEO_STYLE,
        help=f"Kiểu nền video: 'physics' (bóng nảy tự sinh) hoặc 'slideshow' (ảnh + Ken Burns). Mặc định: {VIDEO_STYLE}",
    )
    parser.add_argument(
        "--voice", "-v", default=None,
        help="Giọng đọc edge-tts (vd: vi-VN-HoaiMyNeural). Không truyền → tự chọn theo --lang",
    )
    parser.add_argument(
        "--lang", "-l", default=DEFAULT_LANG,
        help=f"Ngôn ngữ kịch bản/giọng đọc: {', '.join(DEFAULT_VOICES)}. Mặc định: {DEFAULT_LANG}",
    )
    parser.add_argument(
        "--rate", "-r", default=TTS_RATE,
        # argparse tự chạy help-text qua % nội bộ, nên mọi ký tự % (kể cả từ TTS_RATE nội suy
        # vào, vd. "+20%") đều phải escape thành %% để không lỗi "incomplete format"
        help=f"Tốc độ đọc, vd: +20%%, +0%%, -10%% (video sẽ theo tốc độ này). Mặc định: {TTS_RATE.replace('%', '%%')}",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_pipeline(args.topic, background=args.background, voice=args.voice, lang=args.lang, rate=args.rate)
