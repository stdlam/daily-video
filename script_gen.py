"""Bước 1: Sinh script video bằng Groq API (free tier, rất nhanh)."""
import json
import random
import requests
from config import GROQ_API_KEY, GROQ_MODEL, DEFAULT_LANG, DEFAULT_NICHE
from niches import Niche, get_niche

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

_LANG_NAMES = {
    "vi": "tiếng Việt",
    "en": "tiếng Anh (English)",
    "ja": "tiếng Nhật (Japanese)",
    "ko": "tiếng Hàn (Korean)",
    "zh": "tiếng Trung (Chinese)",
    "fr": "tiếng Pháp (French)",
    "es": "tiếng Tây Ban Nha (Spanish)",
}


def generate_script(topic: str, num_scenes: int = 5, lang: str = DEFAULT_LANG,
                    niche: "str | Niche" = DEFAULT_NICHE, fmt: str = "classic") -> dict:
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
    `niche`: tên preset hoặc mô tả tự do (xem niches.py) — quyết định vai chuyên gia, thông điệp,
    quy tắc số liệu, hook, CTA và hashtag.
    `fmt`: "classic" (như cũ) hoặc "hook" (video ngắn 15-25s + thêm field "hook_text" là chữ mở đầu cỡ
    lớn hiện trên màn hình 3 giây đầu, xem caption.draw_hook_at). Prompt "classic" giữ nguyên để A/B.
    """
    if not GROQ_API_KEY:
        raise RuntimeError("Thiếu GROQ_API_KEY. Xem file .env.example")

    n = niche if isinstance(niche, Niche) else get_niche(niche)
    lang_name = _LANG_NAMES.get(lang, lang)
    system_prompt = (
        f"{n.script_role} Kịch bản viết bằng {lang_name}. "
        "Nội dung phải có chiều sâu và giá trị thực tế như một người thực sự hiểu chuyên môn "
        "đang chia sẻ, không phải lời khuyên chung chung ai cũng nói được. "
        "Luôn trả lời CHỈ bằng JSON hợp lệ, không thêm text nào khác, không markdown."
    )
    theme_block = f"\n{n.theme}\n" if n.theme else ""
    hashtag_hint = f", {n.hashtag_hint}" if n.hashtag_hint else ""
    format_block, hook_json = "", ""
    if fmt == "hook":
        format_block = f"""ĐỊNH DẠNG VIDEO NGẮN (quan trọng, áp dụng ĐÈ lên độ dài ở trên):
- Tổng thời lượng đọc 15-25 giây: cả video tối đa ~60 từ. Cảnh 1 tối đa 10 từ, mỗi cảnh còn lại 1 câu
  ngắn tối đa 14 từ. Cắt hết từ đệm, đi thẳng vào ý.
- "hook_text": chữ mở đầu cỡ lớn hiện trên màn hình trong 3 giây đầu (nhiều người lướt TikTok TẮT TIẾNG,
  nên chữ này phải tự đứng được và khiến họ dừng lướt). Viết bằng {lang_name}, TỐI ĐA 7 từ, không hashtag,
  không emoji, không dấu ngoặc kép. Là một nghịch lý / câu nói thẳng chạm đúng người xem, cùng ý với cảnh 1
  nhưng có thể ngắn và gắt hơn (vd tiếng Anh: "You're not lazy. You're alone.", "Your friends are your
  habits."). KHÔNG mở đầu bằng "Did you know" / "Bạn có biết".

"""
        hook_json = f'  "hook_text": "<on-screen hook in {lang_name}, max 7 words>",\n'
    user_prompt = f"""
Viết kịch bản video TikTok về chủ đề: "{topic}"
{theme_block}
NGÔN NGỮ (bắt buộc, áp dụng cho TẤT CẢ nội dung trả về): title, hashtags, và narration của mọi
cảnh PHẢI viết bằng {lang_name} — kể cả khi ví dụ/mô tả field bên dưới đây đang viết bằng tiếng
Việt (đó chỉ là hướng dẫn cho bạn, không phải ngôn ngữ cần trả về). Không lẫn ngôn ngữ khác vào
bất kỳ field nào dù chỉ một phần.

YÊU CẦU VỀ CHIỀU SÂU NỘI DUNG (quan trọng nhất):
- Mỗi cảnh nội dung (trừ cảnh hook mở đầu và cảnh CTA kết thúc) PHẢI chứa ít nhất MỘT trong các yếu tố sau:
  {n.evidence}
- TUYỆT ĐỐI KHÔNG viết câu chung chung, sáo rỗng, hiển nhiên ai cũng biết mà không giải thích (vd: "hãy tiết
  kiệm tiền", "sức khỏe là quan trọng nhất", "hãy cố gắng mỗi ngày") — nếu nêu lời khuyên thì phải kèm THEO
  CÁCH LÀM hoặc LÝ DO cụ thể ngay trong câu đó.
- Ưu tiên insight ít người biết, thông tin gây bất ngờ, hoặc góc nhìn khác với những gì đã bị nói đi nói lại,
  hơn là lời khuyên hiển nhiên.
- Mỗi cảnh nên nói về MỘT ý cụ thể riêng biệt, không lặp lại ý của cảnh khác, không dùng 2 cảnh để nói cùng
  một điều theo cách diễn đạt khác nhau.
{n.facts_policy}
- Narration PHẢI viết bằng {lang_name} thuần túy, không chèn xen từ/ký tự của ngôn ngữ khác vào giữa câu
  (trừ tên riêng hoặc thuật ngữ không có bản dịch tự nhiên).

CẤU TRÚC:
- Đúng {num_scenes} cảnh (scenes)
- Cảnh 1: {n.hook}
- Các cảnh giữa: mỗi cảnh 1 insight/mẹo/sự thật cụ thể, đúng yêu cầu chiều sâu ở trên
- Cảnh cuối: {n.cta}

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
  bằng {lang_name} bám sát chủ đề và nội dung video{hashtag_hint}, không hashtag vô nghĩa

{format_block}Trả về đúng format JSON sau, không thêm gì khác (title/hashtags/narration bằng {lang_name} như đã
yêu cầu ở trên):
{{
  "title": "<video title in {lang_name}>",
{hook_json}  "hashtags": ["#...", "#..."],
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


def generate_topic(lang: str = DEFAULT_LANG, recent_topics: list | None = None,
                   niche: "str | Niche" = DEFAULT_NICHE) -> str:
    """Nhờ LLM nghĩ ra 1 chủ đề video TikTok mới, dùng khi chạy tự động (vd. GitHub Actions theo
    lịch) không có ai truyền sẵn chủ đề. `recent_topics` là các chủ đề đã dùng gần đây để tránh
    lặp lại/na ná. `niche` quyết định phạm vi chủ đề (xem niches.py)."""
    if not GROQ_API_KEY:
        raise RuntimeError("Thiếu GROQ_API_KEY. Xem file .env.example")

    lang_name = _LANG_NAMES.get(lang, lang)
    avoid = ""
    if recent_topics:
        joined = "; ".join(recent_topics[-15:])
        avoid = f"\nTRÁNH các chủ đề đã dùng gần đây (không lặp lại, không na ná): {joined}"

    n = niche if isinstance(niche, Niche) else get_niche(niche)
    angle = f"\nGóc tiếp cận cho lần này: {random.choice(n.angles)}\n" if n.angles else ""

    system_prompt = (
        f"{n.topic_role} bằng {lang_name}. "
        "Luôn trả lời CHỈ bằng JSON hợp lệ, không thêm text nào khác, không markdown."
    )
    user_prompt = f"""
{n.topic_instructions}
{angle}
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
