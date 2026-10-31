"""Bước 1: Sinh script video bằng Groq API (free tier, rất nhanh)."""
import json
import random
import requests
from config import GROQ_API_KEY, GROQ_MODEL, DEFAULT_LANG

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Thông điệp cốt lõi của kênh — dùng chung cho bước nghĩ chủ đề và bước viết script. Mục tiêu dài
# hạn: kéo người xem vào tư duy "build habit" để làm nền cho việc giới thiệu app sau này (hiện
# chưa nhắc app trong video — khi cần, thêm CTA ở cảnh cuối của generate_script).
CHANNEL_THEME = """THÔNG ĐIỆP CỐT LÕI CỦA KÊNH: kỷ luật mỗi ngày quan trọng hơn cảm xúc nhất thời.
Người thành công không chờ có hứng/có động lực mới làm — họ làm theo hệ thống và thói quen, kể cả
khi không muốn. Động lực đến sau hành động chứ không đến trước. Thói quen nhỏ lặp lại đều đặn
thắng nỗ lực lớn nhưng thất thường. Kênh giúp người xem thay đổi TƯ DUY về việc xây dựng thói quen."""

# Các góc tiếp cận khác nhau của cùng một thông điệp — chọn ngẫu nhiên mỗi lần để chủ đề đa dạng,
# không bị lặp một ý.
HABIT_ANGLES = [
    "động lực/cảm hứng là cái bẫy: vì sao chờ 'có hứng' khiến bạn mãi không bắt đầu",
    "hành động đi trước, động lực đi sau: cách bắt đầu khi không muốn làm gì",
    "thói quen nhỏ lặp lại mỗi ngày (quy tắc 2 phút, atomic habits, 1% mỗi ngày) thắng nỗ lực lớn thất thường",
    "hệ thống thắng mục tiêu: vì sao đặt mục tiêu mà không có hệ thống thì thất bại",
    "khoa học về hình thành thói quen: vòng lặp tín hiệu - hành vi - phần thưởng, thời gian thực sự để thành thói quen",
    "vì sao bỏ cuộc sau vài ngày đầu và cách không đứt chuỗi (không bỏ lỡ 2 ngày liên tiếp)",
    "thiết kế môi trường và gắn thói quen mới vào thói quen cũ để không phụ thuộc ý chí",
    "bản sắc: trở thành 'người làm việc đó' thay vì chỉ muốn đạt kết quả",
    "kỷ luật là sự tự do: giữ lời hứa với chính mình xây dựng lòng tự tin ra sao",
    "cảm xúc đến rồi đi, nhưng kỷ luật ở lại: cách hành động bất chấp tâm trạng mệt mỏi, chán nản, trì hoãn",
    "sai lầm phổ biến khi xây thói quen (đặt quá cao, đổi quá nhiều thứ cùng lúc, bắt đầu bằng 'thứ Hai tuần sau')",
    "người bình thường kiên trì đều đặn vs người tài năng làm theo hứng: ai đi xa hơn và vì sao",
]

_LANG_NAMES = {
    "vi": "tiếng Việt",
    "en": "tiếng Anh (English)",
    "ja": "tiếng Nhật (Japanese)",
    "ko": "tiếng Hàn (Korean)",
    "zh": "tiếng Trung (Chinese)",
    "fr": "tiếng Pháp (French)",
    "es": "tiếng Tây Ban Nha (Spanish)",
}


def generate_script(topic: str, num_scenes: int = 5, lang: str = DEFAULT_LANG) -> dict:
    """
    Trả về dict dạng:
    {
        "title": "...",
        "hashtags": ["#...", "#...", ...],
        "scenes": [
            {"narration": "...", "image_query": "..."},
            ...
        ]
    }
    - narration: câu thoại sẽ đọc (TTS)
    - image_query: từ khóa tiếng Anh để search ảnh minh họa (Pexels cần query tiếng Anh)
    - hashtags: dùng làm caption khi đăng TikTok (xem tiktok_poster.post_video_draft)
    """
    if not GROQ_API_KEY:
        raise RuntimeError("Thiếu GROQ_API_KEY. Xem file .env.example")

    lang_name = _LANG_NAMES.get(lang, lang)
    system_prompt = (
        f"Bạn là chuyên gia về xây dựng thói quen và kỷ luật bản thân, đồng thời là copywriter "
        f"viết kịch bản video ngắn TikTok bằng {lang_name}. Phong cách cuốn hút, câu ngắn, dễ đọc to, "
        "thẳng thắn, hơi 'tát nước vào mặt' nhưng thấu hiểu người xem, không giáo điều. "
        "Nội dung phải có chiều sâu và giá trị thực tế như một người thực sự hiểu chuyên môn "
        "đang chia sẻ, không phải lời khuyên chung chung ai cũng nói được. "
        "Luôn trả lời CHỈ bằng JSON hợp lệ, không thêm text nào khác, không markdown."
    )
    user_prompt = f"""
Viết kịch bản video TikTok về chủ đề: "{topic}"

{CHANNEL_THEME}
Hãy để video làm nổi bật thông điệp này một cách tự nhiên qua góc nhìn của chủ đề (không cần nhắc
lại nguyên văn). Người xem xem xong phải thấy "kỷ luật đều đặn > cảm xúc/động lực nhất thời" và biết
MỘT hành động nhỏ có thể bắt đầu ngay hôm nay. KHÔNG nhắc tới bất kỳ app/sản phẩm/dịch vụ nào.

NGÔN NGỮ (bắt buộc, áp dụng cho TẤT CẢ nội dung trả về): title, hashtags, và narration của mọi
cảnh PHẢI viết bằng {lang_name} — kể cả khi ví dụ/mô tả field bên dưới đây đang viết bằng tiếng
Việt (đó chỉ là hướng dẫn cho bạn, không phải ngôn ngữ cần trả về). Không lẫn ngôn ngữ khác vào
bất kỳ field nào dù chỉ một phần.

YÊU CẦU VỀ CHIỀU SÂU NỘI DUNG (quan trọng nhất):
- Mỗi cảnh nội dung (trừ cảnh hook mở đầu và cảnh CTA kết thúc) PHẢI chứa ít nhất MỘT trong các yếu tố sau:
  ví dụ/tình huống đời thường cụ thể mà người xem nhận ra chính mình, cơ chế hoặc lý do "tại sao nó xảy ra"
  (tâm lý, não bộ, hành vi...), hoặc một bước hành động cụ thể người xem có thể làm ngay. Con số KHÔNG bắt
  buộc — tối đa 1 con số cho cả video, và chỉ lấy từ DANH SÁCH SỐ LIỆU ĐƯỢC PHÉP bên dưới.
- TUYỆT ĐỐI KHÔNG viết câu chung chung, sáo rỗng, hiển nhiên ai cũng biết mà không giải thích (vd: "hãy tiết
  kiệm tiền", "sức khỏe là quan trọng nhất", "hãy cố gắng mỗi ngày") — nếu nêu lời khuyên thì phải kèm THEO
  CÁCH LÀM hoặc LÝ DO cụ thể ngay trong câu đó.
- Ưu tiên insight ít người biết, thông tin gây bất ngờ, hoặc góc nhìn khác với những gì đã bị nói đi nói lại,
  hơn là lời khuyên hiển nhiên.
- Mỗi cảnh nên nói về MỘT ý cụ thể riêng biệt, không lặp lại ý của cảnh khác, không dùng 2 cảnh để nói cùng
  một điều theo cách diễn đạt khác nhau.
- CẤM BỊA SỐ LIỆU: không dùng bất kỳ thống kê dạng "X% người...", "nghiên cứu cho thấy...", "sau X phút
  não bộ...", "chỉ X người trong 100..." NẰM NGOÀI danh sách dưới đây — kể cả các con số lan truyền trên
  mạng (vd: "92% người bỏ quyết tâm năm mới" là con số KHÔNG được dùng). Không nêu tên nghiên cứu/tác giả
  nào ngoài danh sách. DANH SÁCH SỐ LIỆU ĐƯỢC PHÉP (dùng đúng như ghi, không phóng đại):
    * Nghiên cứu của Phillippa Lally (2009): trung bình ~66 ngày để một hành vi thành tự động, dao động
      18-254 ngày; bỏ lỡ 1 ngày không làm hỏng quá trình hình thành thói quen.
    * Tốt hơn 1% mỗi ngày: 1.01^365 ≈ 37.8 lần sau 1 năm (đây là phép toán minh họa, không phải nghiên cứu).
    * Quy tắc 2 phút: bắt đầu thói quen mới bằng phiên bản chỉ mất 2 phút (nguyên tắc, không phải thống kê).
  Thay vì số liệu, hãy thuyết phục bằng tình huống đời thường, nghịch lý, và cơ chế dễ hiểu.
- Narration PHẢI viết bằng {lang_name} thuần túy, không chèn xen từ/ký tự của ngôn ngữ khác vào giữa câu
  (trừ tên riêng hoặc thuật ngữ không có bản dịch tự nhiên).

CẤU TRÚC:
- Đúng {num_scenes} cảnh (scenes)
- Cảnh 1: hook trong 2 giây đầu — một nghịch lý hoặc một câu nói thẳng chạm đúng suy nghĩ/nỗi đau của người
  xem (vd: "Bạn không lười. Bạn chỉ đang chờ có hứng.", "Động lực là thứ tệ nhất để dựa vào."). KHÔNG mở đầu
  bằng con số/thống kê, KHÔNG hook mơ hồ kiểu "bạn có biết...", "điều gì xảy ra nếu tôi nói với bạn..."
- Các cảnh giữa: mỗi cảnh 1 insight/mẹo/sự thật cụ thể, đúng yêu cầu chiều sâu ở trên
- Cảnh cuối: chốt lại giá trị cốt lõi bằng 1 câu cụ thể + lời kêu gọi tương tác (follow để xem thêm
  mỗi ngày, hoặc comment cho biết thói quen bạn đang xây — ưu tiên câu hỏi dễ trả lời)

FORMAT MỖI CẢNH:
- "narration": lời thoại ngắn 1-2 câu bằng {lang_name}, giọng tự nhiên như đang kể chuyện, nhưng phải chứa
  thông tin cụ thể theo đúng yêu cầu chiều sâu ở trên
- "image_query": từ khóa TIẾNG ANH mô tả hình ảnh minh họa phù hợp (để search stock photo), luôn viết bằng
  tiếng Anh bất kể narration dùng ngôn ngữ gì

HASHTAGS (dùng làm caption khi đăng TikTok, giúp tăng khả năng viral):
- "hashtags": mảng 6-10 hashtag bằng {lang_name}, mỗi hashtag là 1 chuỗi bắt đầu bằng "#", KHÔNG
  chứa dấu cách bên trong (viết liền không dấu cách)
- Kết hợp 2-3 hashtag phổ biến tăng viral bằng {lang_name} (vd: #fyp #foryoupage #viral nếu tiếng
  Anh, #fyp #xuhuong nếu tiếng Việt — chọn dạng đúng ngôn ngữ đang yêu cầu) với các hashtag cụ thể
  bằng {lang_name} bám sát chủ đề và nội dung video, ưu tiên nhóm thói quen/kỷ luật/phát triển bản
  thân (vd: #habits #discipline #selfimprovement #motivation nếu tiếng Anh; #thoiquen #kyluat
  #phattrienbanthan nếu tiếng Việt — dùng đúng ngôn ngữ đang yêu cầu), không hashtag vô nghĩa

Trả về đúng format JSON sau, không thêm gì khác (title/hashtags/narration bằng {lang_name} như đã
yêu cầu ở trên):
{{
  "title": "<video title in {lang_name}>",
  "hashtags": ["#...", "#..."],
  "scenes": [
    {{"narration": "...", "image_query": "..."}}
  ]
}}
"""

    resp = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.8,
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def generate_topic(lang: str = DEFAULT_LANG, recent_topics: list | None = None) -> str:
    """Nhờ LLM nghĩ ra 1 chủ đề video TikTok mới, dùng khi chạy tự động (vd. GitHub Actions theo
    lịch) không có ai truyền sẵn chủ đề. `recent_topics` là các chủ đề đã dùng gần đây để tránh
    lặp lại/na ná."""
    if not GROQ_API_KEY:
        raise RuntimeError("Thiếu GROQ_API_KEY. Xem file .env.example")

    lang_name = _LANG_NAMES.get(lang, lang)
    avoid = ""
    if recent_topics:
        joined = "; ".join(recent_topics[-15:])
        avoid = f"\nTRÁNH các chủ đề đã dùng gần đây (không lặp lại, không na ná): {joined}"

    angle = random.choice(HABIT_ANGLES)

    system_prompt = (
        f"Bạn là chuyên gia sáng tạo nội dung TikTok cho một kênh về XÂY DỰNG THÓI QUEN và KỶ LUẬT "
        f"BẢN THÂN, giỏi nghĩ ra chủ đề video ngắn hấp dẫn bằng {lang_name}. "
        "Luôn trả lời CHỈ bằng JSON hợp lệ, không thêm text nào khác, không markdown."
    )
    user_prompt = f"""
{CHANNEL_THEME}

Nghĩ ra 1 chủ đề video TikTok MỚI, ngắn gọn (dưới 12 từ), nằm trong thông điệp cốt lõi trên.
Góc tiếp cận cho lần này: {angle}

Chủ đề phải cụ thể, gây tò mò, đánh vào nỗi đau/suy nghĩ có thật của người xem (vd: "tôi chỉ
làm khi có hứng", "bỏ giữa chừng sau vài ngày", "đợi đủ động lực mới bắt đầu"), không chung chung,
không sáo rỗng kiểu "hãy cố gắng mỗi ngày". KHÔNG đề cập tới bất kỳ app/sản phẩm nào.

NGÔN NGỮ (bắt buộc): "topic" PHẢI viết bằng {lang_name}, không lẫn ngôn ngữ khác dù chỉ một phần.
{avoid}

Trả về đúng format JSON sau, không thêm gì khác:
{{"topic": "<topic in {lang_name}>"}}
"""
    resp = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 1.1,
            "response_format": {"type": "json_object"},
        },
        timeout=60,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return json.loads(content)["topic"]


if __name__ == "__main__":
    import sys
    topic = sys.argv[1] if len(sys.argv) > 1 else "3 mẹo tiết kiệm tiền mỗi tháng"
    data = generate_script(topic)
    print(json.dumps(data, ensure_ascii=False, indent=2))
