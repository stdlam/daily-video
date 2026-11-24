# Nhạc nền

Bỏ file .mp3 nhạc nền (free-copyright) vào thư mục này. Script sẽ tự random chọn 1 bài mỗi lần chạy.

Nguồn nhạc free để tải:
- YouTube Audio Library: https://studio.youtube.com/ (mục Audio Library, lọc "Free to use")
- Pixabay Music: https://pixabay.com/music/
- Chosic (free download, ghi nguồn theo yêu cầu từng bài): https://www.chosic.com/free-music/all/

## Nhạc nền hiện tại: `in_flight_alegend.mp3`

**"In Flight" — Alegend**, nguồn Free To Use (freetouse.com). Đã chuẩn hoá về ~-11 LUFS, đỉnh -1 dBTP
(bản gốc -10.6 LUFS, đỉnh +0.3 dBFS dễ vỡ tiếng) để khớp mức mix `volume=0.2` trong `video_builder.py`.
Dài 2:56, phần mở đầu 0-8s nhỏ hơn rồi đều từ giây 8; video 20-40s không chạm đoạn fade-out cuối bài.

Ghi nguồn: nội dung file `in_flight_alegend.credit.txt` được pipeline tự nối vào CUỐI caption mỗi video
(cơ chế chung: đặt `<tên-bài>.credit.txt` cạnh file mp3; bài nào không có file thì không thêm gì).

Nhạc tự soạn trước đây (`rise_together.mp3`, tạo lại bằng [`music_epic.py`](../../music_epic.py); và
`daily_discipline.mp3` bằng [`music_gen.py`](../../music_gen.py)) đã được thay thế, vẫn lấy lại được từ git.

Nếu thư mục này trống, video vẫn tạo được bình thường, chỉ là không có nhạc nền.
