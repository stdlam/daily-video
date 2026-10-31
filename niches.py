"""Ngách nội dung (niche) của kênh — quyết định AI nghĩ chủ đề gì và viết script theo hướng nào.

Chọn niche (ưu tiên từ trên xuống):
  1. Flag khi chạy:            python main.py --niche general
  2. Biến môi trường / .env:   CONTENT_NICHE=general
  3. Mặc định trong config.py: DEFAULT_NICHE

Giá trị hợp lệ:
  - Tên 1 preset trong NICHES bên dưới ("habits", "general", ...)
  - HOẶC 1 câu mô tả tự do, vd: --niche "quản lý tài chính cho sinh viên" → dùng template chung,
    AI tự bám theo mô tả đó. Tiện để thử ngách mới trước khi viết thành preset riêng.

Thêm preset mới: copy 1 Niche trong NICHES, đổi key + nội dung từng field.
"""
from dataclasses import dataclass, field

# Quy tắc chống bịa số liệu dùng cho mọi niche không có danh sách số liệu riêng.
_GENERIC_FACTS_POLICY = (
    "- KHÔNG bịa số liệu, nghiên cứu hay tên tác giả. Chỉ dùng con số/nghiên cứu bạn CHẮC CHẮN là có thật\n"
    "  và nổi tiếng; nếu không chắc, dùng ví dụ/tình huống/cơ chế thay vì con số. Không dùng các thống kê\n"
    "  lan truyền trên mạng không rõ nguồn."
)


@dataclass
class Niche:
    key: str
    label: str  # mô tả ngắn, hiện trong --help và log
    # --- bước nghĩ chủ đề (generate_topic) ---
    topic_role: str            # "Bạn là chuyên gia sáng tạo nội dung TikTok cho ..."
    topic_instructions: str    # phạm vi + yêu cầu cho chủ đề
    angles: list = field(default_factory=list)  # góc tiếp cận, chọn ngẫu nhiên 1 mỗi lần (có thể rỗng)
    # --- bước viết script (generate_script) ---
    script_role: str = ""      # vai chuyên gia + giọng văn
    theme: str = ""            # thông điệp cốt lõi chèn vào prompt script (rỗng = không có)
    evidence: str = ""         # mỗi cảnh nội dung phải chứa ít nhất 1 trong các yếu tố này
    facts_policy: str = _GENERIC_FACTS_POLICY
    hook: str = ""             # hướng dẫn cảnh 1
    cta: str = ""              # hướng dẫn cảnh cuối
    hashtag_hint: str = ""     # gợi ý nhóm hashtag riêng của niche


_HABITS_THEME = """THÔNG ĐIỆP CỐT LÕI CỦA KÊNH: kỷ luật mỗi ngày quan trọng hơn cảm xúc nhất thời.
Người thành công không chờ có hứng/có động lực mới làm — họ làm theo hệ thống và thói quen, kể cả
khi không muốn. Động lực đến sau hành động chứ không đến trước. Thói quen nhỏ lặp lại đều đặn
thắng nỗ lực lớn nhưng thất thường. Kênh giúp người xem thay đổi TƯ DUY về việc xây dựng thói quen."""

NICHES = {
    # Build habit — kỷ luật > cảm xúc. Làm nền để sau này giới thiệu app (hiện CHƯA nhắc app; khi
    # cần, sửa field `cta` bên dưới).
    "habits": Niche(
        key="habits",
        label="Build habit: kỷ luật mỗi ngày > cảm xúc nhất thời",
        topic_role="Bạn là chuyên gia sáng tạo nội dung TikTok cho một kênh về XÂY DỰNG THÓI QUEN và KỶ "
                   "LUẬT BẢN THÂN, giỏi nghĩ ra chủ đề video ngắn hấp dẫn",
        topic_instructions=f"""{_HABITS_THEME}

Nghĩ ra 1 chủ đề video TikTok MỚI, ngắn gọn (dưới 12 từ), nằm trong thông điệp cốt lõi trên.

Chủ đề phải cụ thể, gây tò mò, đánh vào nỗi đau/suy nghĩ có thật của người xem (vd: "tôi chỉ
làm khi có hứng", "bỏ giữa chừng sau vài ngày", "đợi đủ động lực mới bắt đầu"), không chung chung,
không sáo rỗng kiểu "hãy cố gắng mỗi ngày". KHÔNG đề cập tới bất kỳ app/sản phẩm nào.""",
        angles=[
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
        ],
        script_role="Bạn là chuyên gia về xây dựng thói quen và kỷ luật bản thân, đồng thời là copywriter "
                    "viết kịch bản video ngắn TikTok. Phong cách cuốn hút, câu ngắn, dễ đọc to, thẳng thắn, "
                    "hơi 'tát nước vào mặt' nhưng thấu hiểu người xem, không giáo điều.",
        theme=f"""{_HABITS_THEME}
Hãy để video làm nổi bật thông điệp này một cách tự nhiên qua góc nhìn của chủ đề (không cần nhắc
lại nguyên văn). Người xem xem xong phải thấy "kỷ luật đều đặn > cảm xúc/động lực nhất thời" và biết
MỘT hành động nhỏ có thể bắt đầu ngay hôm nay. KHÔNG nhắc tới bất kỳ app/sản phẩm/dịch vụ nào.""",
        evidence="""ví dụ/tình huống đời thường cụ thể mà người xem nhận ra chính mình, cơ chế hoặc lý do "tại sao nó xảy ra"
  (tâm lý, não bộ, hành vi...), hoặc một bước hành động cụ thể người xem có thể làm ngay. Con số KHÔNG bắt
  buộc — tối đa 1 con số cho cả video, và chỉ lấy từ DANH SÁCH SỐ LIỆU ĐƯỢC PHÉP bên dưới.""",
        facts_policy="""- CẤM BỊA SỐ LIỆU: không dùng bất kỳ thống kê dạng "X% người...", "nghiên cứu cho thấy...", "sau X phút
  não bộ...", "chỉ X người trong 100..." NẰM NGOÀI danh sách dưới đây — kể cả các con số lan truyền trên
  mạng (vd: "92% người bỏ quyết tâm năm mới" là con số KHÔNG được dùng). Không nêu tên nghiên cứu/tác giả
  nào ngoài danh sách. DANH SÁCH SỐ LIỆU ĐƯỢC PHÉP (dùng đúng như ghi, không phóng đại):
    * Nghiên cứu của Phillippa Lally (2009): trung bình ~66 ngày để một hành vi thành tự động, dao động
      18-254 ngày; bỏ lỡ 1 ngày không làm hỏng quá trình hình thành thói quen.
    * Tốt hơn 1% mỗi ngày: 1.01^365 ≈ 37.8 lần sau 1 năm (đây là phép toán minh họa, không phải nghiên cứu).
    * Quy tắc 2 phút: bắt đầu thói quen mới bằng phiên bản chỉ mất 2 phút (nguyên tắc, không phải thống kê).
  Thay vì số liệu, hãy thuyết phục bằng tình huống đời thường, nghịch lý, và cơ chế dễ hiểu.""",
        hook="""hook trong 2 giây đầu — một nghịch lý hoặc một câu nói thẳng chạm đúng suy nghĩ/nỗi đau của người
  xem (vd: "Bạn không lười. Bạn chỉ đang chờ có hứng.", "Động lực là thứ tệ nhất để dựa vào."). KHÔNG mở đầu
  bằng con số/thống kê, KHÔNG hook mơ hồ kiểu "bạn có biết...", "điều gì xảy ra nếu tôi nói với bạn..." """.rstrip(),
        cta="""chốt lại giá trị cốt lõi bằng 1 câu cụ thể + lời kêu gọi tương tác (follow để xem thêm
  mỗi ngày, hoặc comment cho biết thói quen bạn đang xây — ưu tiên câu hỏi dễ trả lời)""",
        hashtag_hint="""ưu tiên nhóm thói quen/kỷ luật/phát triển bản
  thân (vd: #habits #discipline #selfimprovement #motivation nếu tiếng Anh; #thoiquen #kyluat
  #phattrienbanthan nếu tiếng Việt — dùng đúng ngôn ngữ đang yêu cầu)""",
    ),

    # Chủ đề chung chung như phiên bản đầu của kênh (thêm quy tắc chống bịa số liệu).
    "general": Niche(
        key="general",
        label="Chung: tài chính, sức khỏe, tâm lý, năng suất, mẹo vặt, khoa học đời thường...",
        topic_role="Bạn là chuyên gia sáng tạo nội dung TikTok, giỏi nghĩ ra chủ đề video ngắn hấp dẫn",
        topic_instructions="""Nghĩ ra 1 chủ đề video TikTok MỚI, ngắn gọn (dưới 12 từ), thuộc một lĩnh vực bất kỳ trong: tài
chính cá nhân, sức khỏe, tâm lý học, năng suất làm việc, sự thật thú vị, mẹo vặt cuộc sống, phát
triển bản thân, khoa học đời thường, các mối quan hệ. Chủ đề phải cụ thể, gây tò mò, không chung
chung, không phải chủ đề đã quá phổ biến/nhàm.""",
        script_role="Bạn là chuyên gia trong lĩnh vực liên quan đến chủ đề được giao, đồng thời là copywriter "
                    "viết kịch bản video ngắn TikTok. Phong cách cuốn hút, câu ngắn, dễ đọc to.",
        evidence="""con số/tỷ lệ % cụ thể, ví dụ/tình huống thực tế, cơ chế hoặc lý do "tại sao nó xảy ra" (tâm lý, sinh học,
  tài chính...), hoặc một bước hành động cụ thể người xem có thể làm ngay.""",
        hook="""hook gây tò mò cụ thể trong 2 giây đầu — một câu hỏi bất ngờ, một sự thật gây bất ngờ, hoặc một
  nghịch lý, KHÔNG hook mơ hồ kiểu "bạn có biết..." """.rstrip(),
        cta="chốt lại giá trị cốt lõi bằng 1 câu cụ thể + lời kêu gọi tương tác (like/follow/comment)",
    ),
}


def _custom_niche(description: str) -> Niche:
    """Niche tự do từ 1 câu mô tả — dùng template chung, AI tự bám theo mô tả."""
    return Niche(
        key="custom",
        label=description,
        topic_role=f"Bạn là chuyên gia sáng tạo nội dung TikTok cho một kênh về: {description}. Bạn giỏi "
                   "nghĩ ra chủ đề video ngắn hấp dẫn",
        topic_instructions=f"""KÊNH CHỈ LÀM NỘI DUNG VỀ: {description}

Nghĩ ra 1 chủ đề video TikTok MỚI, ngắn gọn (dưới 12 từ), nằm TRONG phạm vi kênh ở trên. Chủ đề phải
cụ thể, gây tò mò, đánh vào vấn đề/suy nghĩ có thật của người xem, không chung chung, không phải chủ
đề đã quá phổ biến/nhàm.""",
        script_role=f"Bạn là chuyên gia về {description}, đồng thời là copywriter viết kịch bản video ngắn "
                    "TikTok. Phong cách cuốn hút, câu ngắn, dễ đọc to.",
        theme=f"KÊNH CHỈ LÀM NỘI DUNG VỀ: {description}. Giữ nội dung video bám sát phạm vi này.",
        evidence="""ví dụ/tình huống thực tế, cơ chế hoặc lý do "tại sao nó xảy ra", hoặc một bước hành động cụ thể
  người xem có thể làm ngay (con số chỉ dùng khi chắc chắn có thật).""",
        hook="""hook gây tò mò cụ thể trong 2 giây đầu — một câu hỏi bất ngờ, một nghịch lý, hoặc một câu nói
  thẳng chạm đúng vấn đề của người xem, KHÔNG hook mơ hồ kiểu "bạn có biết..." """.rstrip(),
        cta="chốt lại giá trị cốt lõi bằng 1 câu cụ thể + lời kêu gọi tương tác (like/follow/comment)",
        hashtag_hint=f"ưu tiên hashtag thuộc lĩnh vực: {description}",
    )


def get_niche(name: str) -> Niche:
    """Trả về preset nếu `name` là key trong NICHES, ngược lại coi `name` là mô tả niche tự do."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Niche rỗng — truyền tên preset (" + ", ".join(NICHES) + ") hoặc 1 câu mô tả")
    return NICHES.get(name.lower()) or _custom_niche(name)
