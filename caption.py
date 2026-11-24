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


# ----------------------------------------------------------------------------- chữ mở đầu (hook)
HOOK_SECONDS = 3.0   # chữ mở đầu hiện trong ~3 giây đầu của video
HOOK_FADE = 0.4      # mờ dần trong 0.4s cuối


def _wrap_text(draw, text, font, max_width):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and draw.textlength(trial, font=font) > max_width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def draw_hook_at(img, text, current_time, font_path, center_y_ratio=0.30, max_width=900,
                 max_font=96, min_font=60, max_lines=3):
    """Vẽ chữ mở đầu cỡ lớn (đọc được cả khi người xem TẮT TIẾNG) lên `img` (PIL Image RGB hoặc RGBA,
    sửa tại chỗ) trong HOOK_SECONDS giây đầu: chữ trắng đậm, viền đen, trên khối nền tối bán trong suốt,
    đặt ở ~1/3 trên khung hình (tránh cột nút bấm bên phải và vùng caption ở đáy của TikTok).
    Cỡ chữ tự giảm cho tới khi vừa `max_lines` dòng."""
    if not text or current_time >= HOOK_SECONDS:
        return
    from PIL import Image  # import cục bộ, module này vốn chỉ cần ImageDraw/ImageFont

    opacity = min(1.0, (HOOK_SECONDS - current_time) / HOOK_FADE)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    size = max_font
    while True:
        font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
        lines = _wrap_text(draw, text, font, max_width)
        if len(lines) <= max_lines or size <= min_font:
            break
        size -= 6

    stroke = max(3, size // 16)
    spacing = size // 5
    heights = [draw.textbbox((0, 0), ln, font=font, stroke_width=stroke)[3]
               - draw.textbbox((0, 0), ln, font=font, stroke_width=stroke)[1] for ln in lines]
    widths = [draw.textlength(ln, font=font) for ln in lines]
    block_h = sum(heights) + spacing * (len(lines) - 1)
    pad_x, pad_y = 44, 36
    top = int(img.height * center_y_ratio - block_h / 2)
    box_w = max(widths) + 2 * pad_x
    left = int((img.width - box_w) / 2)
    draw.rounded_rectangle([left, top - pad_y, left + box_w, top + block_h + pad_y], radius=32,
                           fill=(0, 0, 0, 165))
    y = top
    for ln, w, h in zip(lines, widths, heights):
        x = (img.width - w) / 2
        bbox = draw.textbbox((0, 0), ln, font=font, stroke_width=stroke)
        draw.text((x, y - bbox[1]), ln, font=font, fill="white", stroke_width=stroke, stroke_fill="black")
        y += h + spacing

    if opacity < 1.0:
        alpha = layer.getchannel("A").point(lambda a: int(a * opacity))
        layer.putalpha(alpha)
    img.paste(layer, (0, 0), layer)
