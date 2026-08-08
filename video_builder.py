"""Bước 4: Ghép ảnh + giọng đọc + phụ đề + nhạc nền thành video bằng FFmpeg."""
import shutil
import subprocess
import json
from pathlib import Path
from typing import Optional, List
from PIL import Image
from config import VIDEO_WIDTH, VIDEO_HEIGHT, FPS, MUSIC_DIR
from caption import wrap_words, draw_caption_at

_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",  # macOS
    "/System/Library/Fonts/Supplemental/Arial.ttf",  # macOS
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux (GitHub Actions runner)
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux (GitHub Actions runner)
]

def _find_font():
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            return path
    # Không có font nào trong danh sách -> caption.draw_caption_at sẽ âm thầm rơi về
    # ImageFont.load_default() của PIL, vốn render cỡ chữ CỐ ĐỊNH ~8px bất kể font_size truyền
    # vào -> chữ phụ đề nhỏ tí không đọc được. Cảnh báo ngay để không mất công debug lại lần nữa.
    print(
        "[video_builder] CẢNH BÁO: không tìm thấy font nào trong _FONT_CANDIDATES — phụ đề sẽ "
        "render bằng font mặc định rất nhỏ của PIL. Cài thêm font TTF và thêm đường dẫn vào "
        "_FONT_CANDIDATES."
    )
    return None

_FONT_PATH = _find_font()


def get_audio_duration(audio_path: Path) -> float:
    """Lấy độ dài (giây) của file audio bằng ffprobe."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "json", str(audio_path),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def build_scene_clip(image_path: Path, audio_path: Path, word_timings: List[dict], out_path: Path):
    """
    Tạo 1 clip: ảnh có hiệu ứng Ken Burns (zoom nhẹ) + giọng đọc + phụ đề burn-in, từ đang được đọc
    tô nổi bật đồng bộ theo giọng đọc (`word_timings` từ tts.generate_voice).
    """
    duration = get_audio_duration(audio_path)
    frames = max(int(duration * FPS), 1)
    # Zoom chậm, tăng đều từ 1.0 -> target_zoom trong suốt cả cảnh, không bao giờ reset giữa chừng
    # (bug cũ: zoom giảm dần rồi bị reset đột ngột về 1.15 mỗi ~6s -> giật hình)
    target_zoom = 1.12
    zoom_increment = (target_zoom - 1.0) / frames
    zoom_expr = f"min(zoom+{zoom_increment:.8f},{target_zoom})"

    # Phụ đề đổi theo từng frame (từ đang đọc tô nổi bật) nên được vẽ sẵn thành 1 chuỗi ảnh PNG
    # trong suốt rồi overlay lên video bằng ffmpeg (không dùng drawtext filter vì nhiều bản ffmpeg,
    # vd. Homebrew, không build kèm libfreetype/libass nên thiếu filter này -> ffmpeg thoát sớm
    # ngay khi parse -vf).
    wrapped_lines = wrap_words(word_timings)
    caption_dir = out_path.with_name(f"{out_path.stem}_captions")
    caption_dir.mkdir(exist_ok=True)
    try:
        for frame_idx in range(frames):
            img = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
            draw_caption_at(img, wrapped_lines, frame_idx / FPS, _FONT_PATH)
            img.save(caption_dir / f"cap_{frame_idx:05d}.png")

        # Ken Burns: scale ảnh lớn hơn khung hình rồi zoompan để tạo chuyển động nhẹ, sau đó
        # overlay chuỗi ảnh phụ đề (đổi theo từng frame) lên trên
        filter_complex = (
            f"[0:v]scale=8000:-1,"
            f"zoompan=z='{zoom_expr}':d={frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={FPS}[bg];"
            f"[bg][2:v]overlay=0:0[v]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(image_path),
            "-i", str(audio_path),
            "-framerate", str(FPS), "-i", str(caption_dir / "cap_%05d.png"),
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "1:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-r", str(FPS),
            str(out_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    finally:
        shutil.rmtree(caption_dir, ignore_errors=True)
    return out_path


def build_scene_clip_physics(audio_path: Path, word_timings: List[dict], out_path: Path, seed: Optional[int] = None):
    """
    Tạo 1 clip: nền mô phỏng vật lý (bóng nảy, tự sinh bằng code) + giọng đọc + phụ đề burn-in, từ
    đang được đọc tô nổi bật đồng bộ theo giọng đọc. Không dùng ảnh/footage có bản quyền — thay
    thế build_scene_clip khi dùng style 'physics'.
    """
    from physics_bg import frame_generator  # import cục bộ để tránh phụ thuộc vòng

    duration = get_audio_duration(audio_path)
    wrapped_lines = wrap_words(word_timings)

    # Phụ đề được vẽ trực tiếp lên từng frame bằng PIL trong frame_generator (không dùng ffmpeg
    # drawtext filter) vì một số bản ffmpeg (vd. Homebrew) không build kèm libfreetype/libass,
    # khiến drawtext không tồn tại -> ffmpeg thoát sớm -> BrokenPipeError khi ghi frame vào stdin.
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{VIDEO_WIDTH}x{VIDEO_HEIGHT}", "-r", str(FPS),
        "-i", "pipe:0",              # video frames đọc từ stdin
        "-i", str(audio_path),       # audio input
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(out_path),
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for frame in frame_generator(
            VIDEO_WIDTH, VIDEO_HEIGHT, FPS, duration, seed=seed,
            wrapped_lines=wrapped_lines, font_path=_FONT_PATH,
        ):
            proc.stdin.write(frame.tobytes())
    except BrokenPipeError:
        # ffmpeg đã thoát sớm (lỗi) trước khi đọc hết frame — bỏ qua để đọc stderr thật bên dưới
        pass
    try:
        proc.stdin.close()
    except BrokenPipeError:
        pass
    stderr = proc.stderr.read()
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg lỗi khi build physics clip: {stderr.decode(errors='ignore')[-1500:]}")

    return out_path


def concat_clips(clip_paths: List[Path], out_path: Path, music_path: Optional[Path] = None):
    """Nối các scene clip lại, mix thêm nhạc nền (âm lượng thấp) nếu có."""
    list_file = out_path.parent / "concat_list.txt"
    list_file.write_text("\n".join(f"file '{p.resolve()}'" for p in clip_paths))

    if music_path and music_path.exists():
        # Nối clip trước, sau đó mix nhạc nền đè lên toàn bộ
        tmp_concat = out_path.parent / "_tmp_concat.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
             "-c", "copy", str(tmp_concat)],
            check=True, capture_output=True,
        )
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(tmp_concat),
                "-stream_loop", "-1", "-i", str(music_path),
                "-filter_complex",
                "[1:a]volume=0.15[music];[0:a][music]amix=inputs=2:duration=first[aout]",
                "-map", "0:v", "-map", "[aout]",
                "-c:v", "copy", "-shortest",
                str(out_path),
            ],
            check=True, capture_output=True,
        )
        tmp_concat.unlink(missing_ok=True)
    else:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
             "-c", "copy", str(out_path)],
            check=True, capture_output=True,
        )

    list_file.unlink(missing_ok=True)
    return out_path
