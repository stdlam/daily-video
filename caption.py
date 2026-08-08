"""Vẽ phụ đề (caption) lên ảnh bằng PIL — dùng chung cho mọi style video.
Không dùng ffmpeg drawtext filter vì nhiều bản ffmpeg (vd. Homebrew) không build kèm
libfreetype/libass nên thiếu filter này, khiến ffmpeg thoát sớm khi gặp -vf drawtext.

Phụ đề đồng bộ theo từng từ (karaoke-style): mỗi từ trong `words` kèm "start"/"end" (giây) lấy từ
WordBoundary của edge-tts — tại thời điểm current_time nằm trong [start, end) của từ nào thì từ đó
được tô màu nổi bật, các từ khác giữ màu trắng viền đen như bình thường.
"""
from PIL import ImageDraw, ImageFont

HIGHLIGHT_COLOR = (255, 214, 0)  # vàng nổi bật, dễ đọc trên nền tối lẫn nền sáng


def wrap_words(words, max_chars=22):
    """Gom list các từ (mỗi từ là dict {"text","start","end"}) thành các dòng, không vượt quá
    `max_chars` ký tự/dòng, vẫn giữ nguyên start/end của từng từ để đồng bộ highlight."""
    lines, cur, cur_len = [], [], 0
    for w in words:
        wlen = len(w["text"])
        if cur and cur_len + wlen + 1 > max_chars:
            lines.append(cur)
            cur, cur_len = [], 0
        cur.append(w)
        cur_len += wlen + 1
    if cur:
        lines.append(cur)
    return lines


def draw_caption_at(img, wrapped_lines, current_time, font_path, font_size=54, bottom_margin=220,
                     line_spacing=12):
    """Vẽ phụ đề lên `img` (PIL Image, sửa tại chỗ) tại thời điểm `current_time` (giây) — từ đang
    được đọc tô màu vàng nổi bật, các từ khác trắng viền đen. Căn giữa theo chiều ngang, đáy khối
    chữ cách đáy ảnh `bottom_margin` px."""
    if not wrapped_lines:
        return
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()

    line_texts = [" ".join(w["text"] for w in line) for line in wrapped_lines]
    line_heights = []
    for text in line_texts:
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=3)
        line_heights.append(bbox[3] - bbox[1])
    total_height = sum(line_heights) + line_spacing * (len(wrapped_lines) - 1)

    space_w = draw.textlength(" ", font=font)
    y = img.height - bottom_margin - total_height
    for line, text, lh in zip(wrapped_lines, line_texts, line_heights):
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=3)
        x = (img.width - (bbox[2] - bbox[0])) / 2 - bbox[0]
        for w in line:
            is_active = w["start"] <= current_time < w["end"]
            color = HIGHLIGHT_COLOR if is_active else "white"
            draw.text((x, y), w["text"], font=font, fill=color, stroke_width=3, stroke_fill="black")
            x += draw.textlength(w["text"], font=font) + space_w
        y += lh + line_spacing
