"""
Sinh clip nền dạng mô phỏng vật lý (bóng nảy) — thay cho ảnh tĩnh.
Không dùng footage game có bản quyền, 100% tự sinh bằng code, chạy bất cứ đâu không cần internet.
"""
import random
import numpy as np
from PIL import Image, ImageDraw
from caption import draw_caption_at

BG_COLOR = (18, 18, 28)
PALETTE = [
    (255, 99, 132), (54, 162, 235), (255, 206, 86),
    (75, 192, 192), (153, 102, 255), (255, 159, 64),
    (0, 230, 150), (255, 87, 187),
]


class Ball:
    def __init__(self, x, y, vx, vy, r, color):
        self.x, self.y, self.vx, self.vy, self.r, self.color = x, y, vx, vy, r, color


def _make_balls(width, height, num_balls, rng):
    balls = []
    for i in range(num_balls):
        r = rng.randint(int(width * 0.045), int(width * 0.075))
        balls.append(Ball(
            x=rng.uniform(r, width - r),
            y=rng.uniform(r, height * 0.4),
            vx=rng.uniform(-9, 9),
            vy=rng.uniform(-3, 3),
            r=r,
            color=PALETTE[i % len(PALETTE)],
        ))
    return balls


def _step_and_draw(balls, width, height, gravity=0.55, damping=0.86):
    img = Image.new("RGB", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # va chạm bóng-bóng đơn giản (đẩy nhau ra khi chồng lấn)
    for i in range(len(balls)):
        for j in range(i + 1, len(balls)):
            a, b = balls[i], balls[j]
            dx, dy = b.x - a.x, b.y - a.y
            dist = (dx ** 2 + dy ** 2) ** 0.5 or 1e-6
            min_dist = a.r + b.r
            if dist < min_dist:
                overlap = (min_dist - dist) / 2
                nx, ny = dx / dist, dy / dist
                a.x -= nx * overlap
                a.y -= ny * overlap
                b.x += nx * overlap
                b.y += ny * overlap
                a.vx, b.vx = b.vx * 0.9, a.vx * 0.9
                a.vy, b.vy = b.vy * 0.9, a.vy * 0.9

    for b in balls:
        b.vy += gravity
        b.x += b.vx
        b.y += b.vy

        if b.x - b.r < 0:
            b.x = b.r
            b.vx *= -damping
        elif b.x + b.r > width:
            b.x = width - b.r
            b.vx *= -damping

        if b.y - b.r < 0:
            b.y = b.r
            b.vy *= -damping
        elif b.y + b.r > height:
            b.y = height - b.r
            b.vy *= -damping
            b.vx *= 0.99  # ma sát nhẹ khi chạm sàn

        # bóng đổ nhẹ tạo chiều sâu
        draw.ellipse(
            [b.x - b.r + 6, b.y - b.r + 10, b.x + b.r + 6, b.y + b.r + 10],
            fill=(0, 0, 0),
        )
        draw.ellipse([b.x - b.r, b.y - b.r, b.x + b.r, b.y + b.r], fill=b.color)
        # điểm sáng nhỏ tạo hiệu ứng bóng 3D
        hl_r = b.r * 0.28
        draw.ellipse(
            [b.x - b.r * 0.35 - hl_r, b.y - b.r * 0.35 - hl_r,
             b.x - b.r * 0.35 + hl_r, b.y - b.r * 0.35 + hl_r],
            fill=(255, 255, 255),
        )

    return img


def frame_generator(width, height, fps, duration, num_balls=6, seed=None,
                     wrapped_lines=None, font_path=None):
    """Generator trả về từng frame (numpy array RGB) cho toàn bộ thời lượng. `wrapped_lines` (từ
    caption.wrap_words) quyết định từ nào đang được đọc tại thời điểm mỗi frame để tô nổi bật."""
    rng = random.Random(seed)
    balls = _make_balls(width, height, num_balls, rng)
    total_frames = max(1, int(duration * fps))
    for frame_idx in range(total_frames):
        img = _step_and_draw(balls, width, height)
        draw_caption_at(img, wrapped_lines, frame_idx / fps, font_path)
        yield np.asarray(img)
