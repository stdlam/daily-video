# Auto Video TikTok — Free Pipeline

Tự động tạo video TikTok (ảnh hoặc nền physics + giọng đọc + phụ đề karaoke đồng bộ theo giọng đọc + nhạc nền) từ 1 chủ đề, chạy free hoàn toàn qua GitHub Actions. Không cần mở máy, không tốn tiền server.

## Pipeline

```
Chủ đề → Groq API (free) → script (title + lời thoại từng cảnh)
       → edge-tts (free) → giọng đọc từng cảnh (kèm timing từng từ)
       → physics_bg.py hoặc Pexels → nền bóng nảy tự sinh / ảnh Ken Burns
       → FFmpeg → phụ đề karaoke (từ đang đọc tô nổi bật) + ghép + nhạc nền
       → TikTok Content Posting API (tùy chọn) → tự đăng riêng tư (SELF_ONLY)
       → Telegram bot (tùy chọn) → gửi video về điện thoại/máy tính
```

Output: file `.mp4` chuẩn TikTok (1080x1920, 9:16). Mặc định nền là clip bóng nảy vật lý tự sinh (kiểu "satisfying background" đang viral, không dính bản quyền như footage Minecraft/Subway Surfers), phụ đề tô nổi bật từng từ đúng lúc giọng đọc tới đó.

**Auto-đăng TikTok:** pipeline có thể tự đăng video lên TikKok ở chế độ riêng tư (chỉ tài khoản của bạn xem được — do TikTok giới hạn app chưa qua audit chỉ đăng được lên account private). Xem hướng dẫn setup trong [`tiktok_auth.py`](tiktok_auth.py). Muốn video public: xem phần "Giới hạn cần biết" bên dưới.

**Đổi style nền / giọng / ngôn ngữ / tốc độ** không cần sửa code — dùng flag khi chạy, xem `python main.py --help`.

## Setup lần đầu (10-15 phút)

### 1. Lấy API key (đều free)

- **Groq**: https://console.groq.com/keys → tạo key
- **Pexels** (chỉ cần nếu dùng `VIDEO_STYLE = "slideshow"`): https://www.pexels.com/api/

### 2. Test local trước (khuyến nghị)

```bash
git clone <repo-url-của-lam>
cd auto-video-tiktok
pip install -r requirements.txt
brew install ffmpeg   # nếu máy Mac chưa có ffmpeg

cp .env.example .env
# mở .env, điền GROQ_API_KEY và PEXELS_API_KEY vào

python main.py "3 mẹo tiết kiệm tiền mỗi tháng"
```

Video xuất ra ở `output/<timestamp>_<tiêu-đề>.mp4`.

### 3. (Tùy chọn) Cấu hình Telegram để nhận video tự động

1. Chat với `@BotFather` trên Telegram → `/newbot` → lấy `TELEGRAM_BOT_TOKEN`
2. Chat với `@userinfobot` → lấy `TELEGRAM_CHAT_ID`
3. Điền 2 giá trị này vào `.env`

### 4. (Tùy chọn) Cấu hình auto-đăng TikTok (chế độ riêng tư)

Làm theo hướng dẫn chi tiết ở đầu file [`tiktok_auth.py`](tiktok_auth.py) (tạo app trên TikTok for
Developers, thêm target user, chạy `python tiktok_auth.py` một lần để lấy `TIKTOK_REFRESH_TOKEN`).

### 5. Đẩy lên GitHub + bật chạy tự động

```bash
git init
git add .
git commit -m "init auto video pipeline"
git remote add origin <repo-url-của-bạn>
git push -u origin main
```

Vào repo trên GitHub → **Settings → Secrets and variables → Actions** → thêm các secret:
- `GROQ_API_KEY`
- `PEXELS_API_KEY` (nếu dùng `--background slideshow`)
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` (nếu dùng)
- `TIKTOK_CLIENT_KEY` / `TIKTOK_CLIENT_SECRET` / `TIKTOK_REFRESH_TOKEN` (nếu dùng auto-đăng TikTok)

Workflow `.github/workflows/daily-video.yml` sẽ tự chạy **mỗi ngày lúc 9h sáng giờ VN**. Có thể đổi lịch bằng cách sửa dòng `cron` trong file đó.

Muốn chạy tay ngay lập tức: vào tab **Actions** trên GitHub → chọn workflow "Auto Tạo Video TikTok" → **Run workflow** → có thể tùy chỉnh chủ đề, nền, giọng, ngôn ngữ, tốc độ đọc.

## Chỉnh sửa theo ý muốn

| Muốn đổi | Sửa ở đâu |
|---|---|
| Giọng đọc | Flag `--voice` (vd: `--voice vi-VN-NamMinhNeural`), xem danh sách: `edge-tts --list-voices \| grep vi-VN` |
| Ngôn ngữ kịch bản/giọng đọc | Flag `--lang` (vi, en, ja, ko, zh, fr, es), xem `config.py` → `DEFAULT_VOICES` |
| Tốc độ đọc (nhịp độ video) | Flag `--rate` (vd: `+20%`), mặc định `config.py` → `TTS_RATE` |
| Style nền (physics/slideshow) | Flag `--background`, mặc định `config.py` → `VIDEO_STYLE` |
| Màu chữ highlight karaoke | `caption.py` → `HIGHLIGHT_COLOR` |
| Số cảnh/video | `config.py` → `NUM_IMAGES` |
| Số bóng, màu sắc, độ nảy | `physics_bg.py` → `PALETTE`, `num_balls`, `gravity`/`damping` trong `_step_and_draw` |
| Chủ đề cố định hoặc random theo list | `main.py`, hoặc sửa `workflow_dispatch.inputs.topic` trong yml |
| Nhạc nền | Bỏ file `.mp3` vào `assets/music/` |
| Lịch chạy | `.github/workflows/daily-video.yml` → dòng `cron` |

## Giới hạn cần biết

- **Groq free tier**: có rate limit (đủ dùng vài chục video/ngày, xem chi tiết tại console.groq.com)
- **Pexels free tier**: 200 request/giờ — dư dùng cho vài video/ngày
- **GitHub Actions free tier**: 2000 phút/tháng cho repo private — mỗi lần chạy pipeline này tốn ~3-5 phút, dư sức chạy 1-2 video/ngày
- **TikTok auto-đăng chỉ ở chế độ riêng tư**: app chưa qua audit của TikTok chỉ được đăng lên account đang để Private. Muốn video cụ thể public: tắt Private account CHO TÀI KHOẢN, rồi vào chính video đó đổi privacy riêng thành "Everyone" (cần cả 2 bước) — hoặc nộp app cho TikTok audit để đăng public thẳng qua API.
