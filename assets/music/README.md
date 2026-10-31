# Nhạc nền

Bỏ file .mp3 nhạc nền (free-copyright) vào thư mục này. Script sẽ tự random chọn 1 bài mỗi lần chạy.

Nguồn nhạc free để tải:
- YouTube Audio Library: https://studio.youtube.com/ (mục Audio Library, lọc "Free to use")
- Pixabay Music: https://pixabay.com/music/
- Chosic (free download, ghi nguồn theo yêu cầu từng bài): https://www.chosic.com/free-music/all/

## Nhạc tự sinh: `daily_discipline.mp3`

Bài này được tạo bằng [`music_gen.py`](../../music_gen.py) (numpy thuần, không dính bản quyền), viết riêng
cho thông điệp kênh "kỷ luật mỗi ngày > cảm xúc nhất thời": 96 BPM, Am–F–C–G, nhịp kick đều như nhịp
tim / đồng hồ, giai điệu đi lên dần, khoét dải ~2kHz chừa chỗ cho giọng đọc. Dài 80s, lặp liền mạch.

Tạo lại / tạo biến thể: `python music_gen.py --seed 3 --out assets/music/daily_discipline_v2.mp3`

Nếu thư mục này trống, video vẫn tạo được bình thường, chỉ là không có nhạc nền.
