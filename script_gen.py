"""Bước 1: Sinh script video bằng Groq API (free tier, rất nhanh)."""
import json
import requests
from config import GROQ_API_KEY, GROQ_MODEL, DEFAULT_LANG

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


def generate_script(topic: str, num_scenes: int = 5, lang: str = DEFAULT_LANG) -> dict:
    """
    Trả về dict dạng:
    {
        "title": "...",
        "scenes": [
            {"narration": "...", "image_query": "..."},
            ...
        ]
    }
    - narration: câu thoại sẽ đọc (TTS)
    - image_query: từ khóa tiếng Anh để search ảnh minh họa (Pexels cần query tiếng Anh)
    """
    if not GROQ_API_KEY:
        raise RuntimeError("Thiếu GROQ_API_KEY. Xem file .env.example")

    lang_name = _LANG_NAMES.get(lang, lang)
    system_prompt = (
        f"Bạn là chuyên gia trong lĩnh vực liên quan đến chủ đề được giao, đồng thời là copywriter "
        f"viết kịch bản video ngắn TikTok bằng {lang_name}. Phong cách cuốn hút, câu ngắn, dễ đọc to, "
        "nhưng nội dung phải có chiều sâu và giá trị thực tế như một người thực sự hiểu chuyên môn "
        "đang chia sẻ, không phải lời khuyên chung chung ai cũng nói được. "
        "Luôn trả lời CHỈ bằng JSON hợp lệ, không thêm text nào khác, không markdown."
    )
    user_prompt = f"""
Viết kịch bản video TikTok về chủ đề: "{topic}"

YÊU CẦU VỀ CHIỀU SÂU NỘI DUNG (quan trọng nhất):
- Mỗi cảnh nội dung (trừ cảnh hook mở đầu và cảnh CTA kết thúc) PHẢI chứa ít nhất MỘT trong các yếu tố sau:
  con số/tỷ lệ % cụ thể, ví dụ/tình huống thực tế, cơ chế hoặc lý do "tại sao nó xảy ra" (tâm lý, sinh học,
  tài chính...), hoặc một bước hành động cụ thể người xem có thể làm ngay.
- TUYỆT ĐỐI KHÔNG viết câu chung chung, sáo rỗng, hiển nhiên ai cũng biết mà không giải thích (vd: "hãy tiết
  kiệm tiền", "sức khỏe là quan trọng nhất", "hãy cố gắng mỗi ngày") — nếu nêu lời khuyên thì phải kèm THEO
  CÁCH LÀM hoặc LÝ DO cụ thể ngay trong câu đó.
- Ưu tiên insight ít người biết, thông tin gây bất ngờ, hoặc góc nhìn khác với những gì đã bị nói đi nói lại,
  hơn là lời khuyên hiển nhiên.
- Mỗi cảnh nên nói về MỘT ý cụ thể riêng biệt, không lặp lại ý của cảnh khác, không dùng 2 cảnh để nói cùng
  một điều theo cách diễn đạt khác nhau.
- Narration PHẢI viết bằng {lang_name} thuần túy, không chèn xen từ/ký tự của ngôn ngữ khác vào giữa câu
  (trừ tên riêng hoặc thuật ngữ không có bản dịch tự nhiên).

CẤU TRÚC:
- Đúng {num_scenes} cảnh (scenes)
- Cảnh 1: hook gây tò mò cụ thể trong 2 giây đầu — một câu hỏi bất ngờ, một con số gây sốc, hoặc một nghịch lý,
  KHÔNG hook mơ hồ kiểu "bạn có biết..."
- Các cảnh giữa: mỗi cảnh 1 insight/mẹo/sự thật cụ thể, đúng yêu cầu chiều sâu ở trên
- Cảnh cuối: chốt lại giá trị cốt lõi bằng 1 câu cụ thể + lời kêu gọi tương tác (like/follow/comment)

FORMAT MỖI CẢNH:
- "narration": lời thoại ngắn 1-2 câu bằng {lang_name}, giọng tự nhiên như đang kể chuyện, nhưng phải chứa
  thông tin cụ thể theo đúng yêu cầu chiều sâu ở trên
- "image_query": từ khóa TIẾNG ANH mô tả hình ảnh minh họa phù hợp (để search stock photo), luôn viết bằng
  tiếng Anh bất kể narration dùng ngôn ngữ gì

Trả về đúng format JSON sau, không thêm gì khác:
{{
  "title": "tiêu đề ngắn cho video",
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

    system_prompt = (
        f"Bạn là chuyên gia sáng tạo nội dung TikTok, giỏi nghĩ ra chủ đề video ngắn hấp dẫn bằng "
        f"{lang_name}. Luôn trả lời CHỈ bằng JSON hợp lệ, không thêm text nào khác, không markdown."
    )
    user_prompt = f"""
Nghĩ ra 1 chủ đề video TikTok MỚI, ngắn gọn (dưới 12 từ), thuộc một lĩnh vực bất kỳ trong: tài
chính cá nhân, sức khỏe, tâm lý học, năng suất làm việc, sự thật thú vị, mẹo vặt cuộc sống, phát
triển bản thân, khoa học đời thường, các mối quan hệ. Chủ đề phải cụ thể, gây tò mò, không chung
chung, không phải chủ đề đã quá phổ biến/nhàm.
{avoid}

Trả về đúng format JSON sau, không thêm gì khác:
{{"topic": "..."}}
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
