"""Soạn + render nhạc nền "Rise Together" — epic orchestral, chơi bằng NHẠC CỤ LẤY MẪU THẬT.

Khác bản synth numpy trước (nghe rè, "rẻ tiền"): bài này được soạn thành MIDI (giai điệu chủ đề +
bản phối dàn nhạc) rồi render bằng FluidSynth với SoundFont FluidR3_GM (mẫu âm thanh của kèn French
horn, dàn dây, đồng ca, timpani, piano, bass, trống...). Sau đó mix/master bằng ffmpeg.

Cần cài (chỉ khi muốn tạo lại bài, workflow hằng ngày chỉ dùng file .mp3 đã render):
    apt-get install -y fluidsynth fluid-soundfont-gm ffmpeg ; pip install mido numpy

Âm nhạc:
- Rê thứ, 108 BPM. Đoạn chính: Dm - Bb - F - C. Cao trào: Dm - Bb - Gm - A (A trưởng kéo về Dm)
- Chủ đề (motif) 4 ô nhịp rõ ràng, nhắc lại và nâng dần: kèn horn -> kèn + dây -> kèn + dây + đồng ca
- Ostinato cello/viola nốt móc đơn dồn nhịp, timpani + kick + snare, brass stabs, snare/timpani roll
- Khoét dải ~2kHz (cho giọng đọc TTS), loudness -11 LUFS
- 40 ô nhịp (~89s), đuôi reverb/ngân cuộn về đầu bài -> lặp (-stream_loop -1) liền mạch

  ô  0- 3  mở đầu: piano + dây ngân, timpani roll         ô 20-35  cao trào: chủ đề B, đồng ca, trumpet
  ô  4- 7  dồn dập: ostinato, timpani, snare roll         ô 36-39  hạ xuống, kết ở A để quay về Dm
  ô  8-15  đoạn chính: chủ đề A bằng kèn horn
  ô 16-19  lắng: đồng ca + harp, dâng lên

Chạy:  python music_epic.py                       # ghi ra assets/music/rise_together.mp3
       python music_epic.py --out x.mp3 --seed 3  # seed đổi độ lệch nhịp/độ mạnh nhẹ ("người chơi")
"""
import argparse
import re
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import mido
import numpy as np

SR = 44100
BPM = 108
BEAT = 60 / BPM
BAR = 4 * BEAT
N_BARS = 40
TAIL_BARS = 2  # render dư để bắt đuôi reverb rồi cuộn về đầu bài
TPB = 480
SOUNDFONT = Path("/usr/share/sounds/sf2/FluidR3_GM.sf2")
TARGET_LUFS = -11.0

# kênh MIDI -> (chương trình GM, âm lượng CC7, pan CC10)
PIANO, STR, CELLO, VIOLA, HORN, BRASS, CHOIR, BASS, TIMP, DRUM, HARP, TRUMPET = range(12)
INSTR = {
    PIANO: (0, 95, 64), STR: (48, 82, 64), CELLO: (42, 105, 50), VIOLA: (41, 85, 78),
    HORN: (60, 118, 60), BRASS: (61, 110, 64), CHOIR: (52, 78, 64), BASS: (43, 127, 64),
    TIMP: (47, 127, 64), HARP: (46, 95, 80), TRUMPET: (56, 105, 70),
}

# Hợp âm: bass, âm lót (đồng ca/dây, quãng 4), voicing thấp cho piano
CH = {
    "Dm": {"bass": 38, "up": [62, 65, 69], "low": [50, 57, 62, 65]},
    "Bb": {"bass": 34, "up": [62, 65, 70], "low": [46, 53, 58, 62]},
    "F": {"bass": 41, "up": [60, 65, 69], "low": [53, 57, 60, 65]},
    "C": {"bass": 36, "up": [60, 64, 67], "low": [48, 55, 60, 64]},
    "Gm": {"bass": 31, "up": [62, 67, 70], "low": [43, 50, 55, 58]},
    "A": {"bass": 33, "up": [61, 64, 69], "low": [45, 52, 57, 61]},
}
PROG_A = ["Dm", "Bb", "F", "C"]
PROG_B = ["Dm", "Bb", "Gm", "A"]

# Chủ đề: (phách trong 4 ô nhịp, độ dài phách, nốt MIDI)
THEME_A = [(0, 1, 69), (1, 1, 74), (2, 1.5, 77), (3.5, .5, 76), (4, 3, 74), (7, .5, 72), (7.5, .5, 74),
           (8, 1, 72), (9, 1, 77), (10, 1.5, 81), (11.5, .5, 79), (12, 2, 76), (14, 1, 74), (15, 1, 72)]
THEME_B = [(0, 1, 74), (1, 1, 81), (2, 1.5, 81), (3.5, .5, 79), (4, 2, 77), (6, 1, 79), (7, 1, 81),
           (8, 1.5, 82), (9.5, .5, 81), (10, 1, 79), (11, 1, 77), (12, 1, 76), (13, 1, 79), (14, 1, 76),
           (15, 1, 73)]


def prog_for(bar: int) -> str:
    if 20 <= bar < 28 or 32 <= bar < 40:
        return PROG_B[bar % 4]
    return PROG_A[bar % 4]


class Song:
    def __init__(self, seed: int):
        self.ev = []  # (tick, order, msg)
        self.rng = np.random.default_rng(seed)

    @staticmethod
    def _tick(beat: float) -> int:
        return int(round(beat * TPB))

    def note(self, ch, pitch, beat, dur, vel, human=True):
        if human and ch != DRUM:
            beat += self.rng.normal(0, 0.008)
            vel += self.rng.normal(0, 3)
        beat = max(0.0, beat)
        vel = int(np.clip(vel, 1, 127))
        t0 = self._tick(beat)
        t1 = max(t0 + 1, self._tick(beat + dur))
        self.ev.append((t0, 1, mido.Message("note_on", channel=ch, note=int(pitch), velocity=vel)))
        self.ev.append((t1, 0, mido.Message("note_off", channel=ch, note=int(pitch), velocity=0)))

    def cc(self, ch, ctl, beat, val):
        self.ev.append((self._tick(beat), -1, mido.Message("control_change", channel=ch, control=ctl,
                                                            value=int(np.clip(val, 0, 127)))))

    def expression(self, ch, beat0, beat1, v0, v1, steps=8):
        """Dâng/hạ dần CC11 (expression) -> crescendo/diminuendo tự nhiên của dàn dây, đồng ca..."""
        for i in range(steps + 1):
            self.cc(ch, 11, beat0 + (beat1 - beat0) * i / steps, v0 + (v1 - v0) * i / steps)

    def save(self, path: Path):
        mid = mido.MidiFile(ticks_per_beat=TPB)
        tr = mido.MidiTrack()
        mid.tracks.append(tr)
        tr.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(BPM), time=0))
        for ch, (prog, vol, pan) in INSTR.items():
            if ch != DRUM:
                tr.append(mido.Message("program_change", channel=ch, program=prog, time=0))
            tr.append(mido.Message("control_change", channel=ch, control=7, value=vol, time=0))
            tr.append(mido.Message("control_change", channel=ch, control=10, value=pan, time=0))
            tr.append(mido.Message("control_change", channel=ch, control=11, value=127, time=0))
        tr.append(mido.Message("control_change", channel=DRUM, control=7, value=127, time=0))
        last = 0
        for tick, _, msg in sorted(self.ev, key=lambda e: (e[0], e[1])):
            tr.append(msg.copy(time=tick - last))
            last = tick
        end = (N_BARS + TAIL_BARS) * 4 * TPB
        tr.append(mido.MetaMessage("end_of_track", time=max(0, end - last)))
        mid.save(str(path))


# ----------------------------------------------------------------------------- bản phối
def arrange(seed: int) -> Song:
    s = Song(seed)
    K, SN, HH, CR, T1, T2, T3 = 36, 38, 42, 49, 41, 43, 45  # kick, snare, hat, crash, toms

    def roll(beat0, beat1, v0, v1, ch=DRUM, pitch=SN, step=0.25):
        n = int(round((beat1 - beat0) / step))
        for i in range(n):
            s.note(ch, pitch, beat0 + i * step, step * 0.9, v0 + (v1 - v0) * i / max(1, n - 1))

    for b in range(N_BARS):
        name = prog_for(b)
        c = CH[name]
        b0 = b * 4  # phách bắt đầu ô nhịp
        intro, build, main, calm = b < 4, 4 <= b < 8, 8 <= b < 16, 16 <= b < 20
        final, outro = 20 <= b < 36, b >= 36
        v = 62 if intro else 78 if build else 92 if main else 70 if calm else 104 if final else 66

        # --- Dàn dây ngân (nền) + bass ---
        for p in c["low"][1:] + [x + 12 for x in c["up"]][:2]:
            s.note(STR, p, b0, 3.95, v - 8, human=False)
        s.note(BASS, c["bass"], b0, 3.9, 84 if not (intro or calm) else 70, human=False)
        if main or final:
            s.note(BASS, c["bass"] + 12, b0, 3.9, 60, human=False)

        # --- Piano rải hợp âm: mở đầu, lắng, hạ xuống ---
        if intro or calm or outro:
            tones = c["low"][1:] + [x + 12 for x in c["up"]]
            order = [0, 1, 2, 3, 4, 5, 4, 3]
            for i in range(8):
                s.note(PIANO, tones[order[i] % len(tones)], b0 + i * 0.5, 1.6, 60 + (8 if i % 2 == 0 else 0))

        # --- Harp lướt ở đoạn lắng và cao trào ---
        if calm or (final and b % 2 == 0):
            for i, p in enumerate(c["up"] + [c["up"][0] + 12, c["up"][1] + 12]):
                s.note(HARP, p, b0 + i * 0.25, 1.5, 62)

        # --- Ostinato cello + viola nốt móc đơn: dồn nhịp ---
        if build or main or final:
            pat = [0, 7, 12, 7, 0, 7, 12, 7]
            for i, semi in enumerate(pat):
                acc = 10 if i % 2 == 0 else 0
                s.note(CELLO, c["bass"] + 12 + semi, b0 + i * 0.5, 0.42, v - 6 + acc)
                if main or final:
                    s.note(VIOLA, c["bass"] + 12 + semi + 12, b0 + i * 0.5, 0.42, v - 12 + acc)

        # --- Brass stabs chặn nhịp: phách 1 và "và của 2" ---
        if main or final:
            for p in (c["bass"] + 24, c["bass"] + 31, c["bass"] + 36):
                s.note(BRASS, p, b0, 1.0, v + 12)
                s.note(BRASS, p, b0 + 1.5, 0.4, v + 4)

        # --- Đồng ca: đoạn lắng (mềm) và cao trào (dày) ---
        if calm or final:
            for p in c["up"]:
                s.note(CHOIR, p + 12, b0, 3.95, 78 if calm else 92, human=False)

        # --- Timpani ---
        if intro:
            if b % 2 == 0:
                s.note(TIMP, 38, b0, 2.0, 70)
        elif build or calm or outro:
            s.note(TIMP, c["bass"] + 12, b0, 1.5, 88 if build else 72)
            if build:
                s.note(TIMP, c["bass"] + 12, b0 + 2.5, 1.0, 80)
        else:
            s.note(TIMP, c["bass"] + 12, b0, 1.0, 110)
            s.note(TIMP, c["bass"] + 12, b0 + 2.5, 0.8, 95)
            s.note(TIMP, c["bass"] + 7, b0 + 3.5, 0.8, 95)

        # --- Trống ---
        if build:
            for beat in (0, 2):
                s.note(DRUM, K, b0 + beat, 0.3, 90)
            if b % 2 == 1:
                s.note(DRUM, T3, b0 + 3.5, 0.3, 90)
        elif main or final:
            for beat in range(4):
                s.note(DRUM, K, b0 + beat, 0.3, 112 if beat % 2 == 0 else 98)
            for beat in (1, 3):
                s.note(DRUM, SN, b0 + beat, 0.3, 112)
            for i in range(8):
                s.note(DRUM, HH, b0 + i * 0.5, 0.2, 78 if i % 2 else 52)
            s.note(DRUM, T2, b0 + 2.5, 0.3, 96)
            s.note(DRUM, T1, b0 + 3.5, 0.3, 100)
            if final and b % 2 == 1:
                s.note(DRUM, T3, b0 + 3.75, 0.3, 100)
        elif b == 19:
            roll(b0 + 2, b0 + 4, 40, 118)

        # --- Mốc chuyển đoạn: crash + hit; roll dồn vào mốc ---
        if b in (0, 8, 20, 28, 32):
            s.note(DRUM, CR, b0, 3.0, 118 if b in (0, 8, 20) else 100)
            s.note(DRUM, K, b0, 0.4, 125)
            s.note(TIMP, c["bass"] + 12, b0, 2.0, 125)
        if b in (7, 15, 27, 31, 35):
            roll(b0 + 2, b0 + 4, 45, 124)
            roll(b0 + 2, b0 + 4, 60, 120, ch=TIMP, pitch=c["bass"] + 12)
        if b == 3:
            roll(b0 + 1.5, b0 + 4, 40, 112, ch=TIMP, pitch=38)
        if b == 39:  # kéo về hit ở ô 0 khi lặp
            roll(b0 + 2, b0 + 4, 30, 110)
            roll(b0 + 1, b0 + 4, 40, 120, ch=TIMP, pitch=45)

    # --- Expression: dâng/hạ dàn dây theo từng đoạn (phách) ---
    for ch in (STR, CHOIR, CELLO, VIOLA):
        s.expression(ch, 0, 64, 70, 105)       # mở đầu -> đoạn chính: dâng dần
        s.expression(ch, 64, 80, 105, 78)      # lắng
        s.expression(ch, 80, 144, 90, 127)     # cao trào: dâng liên tục
        s.expression(ch, 144, 160, 122, 85)    # hạ xuống

    # --- Chủ đề: (nhạc cụ, dịch quãng tám, chênh velocity) ---
    def theme(start_bar, notes, instr, vel=100, dur_scale=0.96):
        for beat, dur, p in notes:
            for ch, shift, dv in instr:
                s.note(ch, p + shift, start_bar * 4 + beat, dur * dur_scale, vel + dv)

    theme(8, THEME_A, [(HORN, 0, 0)], vel=96)
    theme(12, THEME_A, [(HORN, 0, 8), (STR, 0, -6), (TRUMPET, 0, -16)], vel=100)
    theme(20, THEME_B, [(HORN, 0, 8), (STR, 0, 0), (TRUMPET, 0, -6), (CHOIR, 0, -8)], vel=104)
    theme(24, THEME_B, [(HORN, 0, 8), (STR, 12, -2), (TRUMPET, 0, -4), (CHOIR, 0, -6)], vel=108)
    theme(28, THEME_A, [(HORN, 12, 6), (HORN, 0, 0), (STR, 12, 0), (TRUMPET, 12, -4), (CHOIR, 12, -10)], vel=108)
    theme(32, THEME_B, [(HORN, 0, 12), (STR, 12, 4), (TRUMPET, 12, 0), (CHOIR, 12, -4), (BRASS, -12, -10)], vel=112)
    theme(36, THEME_A, [(PIANO, 12, -30)], vel=70)  # hạ xuống: giai điệu mềm bằng piano
    return s


# ----------------------------------------------------------------------------- render + master
def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        assert w.getnchannels() == 2 and w.getsampwidth() == 2
        raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, "<i2").astype(np.float64).reshape(-1, 2).T / 32768


def write_wav(path: Path, x: np.ndarray) -> None:
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").T.copy()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def measure_lufs(wav_path: Path) -> float:
    res = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(wav_path), "-af", "ebur128",
                          "-f", "null", "-"], capture_output=True, text=True)
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", res.stderr)[-1])


def render(out_path: Path, seed: int = 7) -> Path:
    if not SOUNDFONT.exists() or not shutil.which("fluidsynth"):
        raise SystemExit("Thiếu fluidsynth hoặc SoundFont: apt-get install -y fluidsynth fluid-soundfont-gm")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        mid, raw, folded, leveled = tmp / "song.mid", tmp / "raw.wav", tmp / "folded.wav", tmp / "leveled.wav"
        arrange(seed).save(mid)
        subprocess.run(
            ["fluidsynth", "-ni", "-q", "-F", str(raw), "-r", str(SR), "-g", "0.9",
             "-o", "synth.reverb.active=1", "-o", "synth.reverb.room-size=0.85", "-o", "synth.reverb.damp=0.25",
             "-o", "synth.reverb.width=0.9", "-o", "synth.reverb.level=0.55",
             "-o", "synth.chorus.active=1", "-o", "synth.chorus.level=1.2",
             str(SOUNDFONT), str(mid)],
            check=True, capture_output=True)
        x = read_wav(raw)
        length = int(round(N_BARS * BAR * SR))
        body, tail = x[:, :length].copy(), x[:, length:]
        n = min(tail.shape[1], length)
        body[:, :n] += tail[:, :n]  # cuộn đuôi về đầu bài -> lặp liền mạch
        write_wav(folded, body)
        # master: khoét dải giọng nói, nén nhẹ cho dày, rồi chuẩn loudness
        chain = ("highpass=f=32,bass=g=4:f=90,equalizer=f=900:t=q:w=0.8:g=-3.5,equalizer=f=2200:t=q:w=0.9:g=-3,"
                 "treble=g=3:f=7000,"
                 "acompressor=threshold=-20dB:ratio=2.5:attack=20:release=250:makeup=2,alimiter=limit=0.8")
        gain_db = TARGET_LUFS - measure_lufs(folded)
        for _ in range(3):
            subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(folded),
                            "-af", f"volume={gain_db}dB,{chain}", str(leveled)], check=True)
            gain_db += TARGET_LUFS - measure_lufs(leveled)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(leveled),
                        "-codec:a", "libmp3lame", "-b:a", "192k", str(out_path)], check=True)
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "assets" / "music" / "rise_together.mp3")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    path = render(args.out, args.seed)
    print(f"Đã tạo nhạc nền: {path} ({N_BARS} ô nhịp, {BPM} BPM, {N_BARS * BAR:.1f}s, lặp liền mạch)")
