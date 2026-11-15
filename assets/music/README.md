# Nhạc nền

Bỏ file .mp3 nhạc nền (free-copyright) vào thư mục này. Script sẽ tự random chọn 1 bài mỗi lần chạy.

Nguồn nhạc free để tải:
- YouTube Audio Library: https://studio.youtube.com/ (mục Audio Library, lọc "Free to use")
- Pixabay Music: https://pixabay.com/music/
- Chosic (free download, ghi nguồn theo yêu cầu từng bài): https://www.chosic.com/free-music/all/

## Nhạc nền hiện tại: `rise_together.mp3`

Bài epic orchestral (Rê thứ, 108 BPM, 89s, lặp liền mạch, -11 LUFS) được soạn và render bằng
[`music_epic.py`](../../music_epic.py): soạn MIDI rồi chơi bằng nhạc cụ lấy mẫu thật (kèn horn, dàn dây,
đồng ca, timpani, piano, trống) qua FluidSynth + SoundFont FluidR3_GM. Dải ~2kHz được khoét bớt cho giọng đọc.

Tạo lại / tạo biến thể (cần `apt-get install fluidsynth fluid-soundfont-gm`, `pip install mido`):
`python music_epic.py --seed 3 --out assets/music/rise_together_v2.mp3`

Bài cũ `daily_discipline.mp3` (synth numpy, tạo bằng [`music_gen.py`](../../music_gen.py)) đã được thay thế.

Nếu thư mục này trống, video vẫn tạo được bình thường, chỉ là không có nhạc nền.
