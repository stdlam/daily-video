"""Tự sinh nhạc nền "Daily Discipline" bằng numpy — không dính bản quyền, chạy lại được bất cứ lúc nào.

Ý tưởng âm nhạc (bám theo thông điệp kênh "kỷ luật mỗi ngày > cảm xúc nhất thời"):
- Nhịp kick đều như nhịp tim / tiếng đồng hồ tích tắc  -> sự đều đặn mỗi ngày
- Vòng hợp âm Am - F - C - G (i - VI - III - VII)        -> quyết tâm nhưng có hy vọng
- Lớp nhạc cụ thêm dần, giai điệu đi lên cao dần          -> tiến bộ nhờ kiên trì
- Dải ~2kHz được khoét bớt                                -> chừa chỗ cho giọng đọc TTS rõ ràng

Bài dài đúng 32 ô nhịp và được render dạng vòng tròn (đuôi reverb/nốt ngân cuộn về đầu bài), nên
khi video_builder lặp nhạc (-stream_loop -1) sẽ nối liền mạch, không bị khựng.

Chạy:  python music_gen.py                      # ghi ra assets/music/daily_discipline.mp3
       python music_gen.py --out x.mp3 --seed 3 # đổi seed để ra biến thể khác (tiếng trống/pad)
"""
import argparse
import re
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 44100
BPM = 96
BEAT = 60 / BPM
BAR = 4 * BEAT
N_BARS = 32
LEN = int(round(N_BARS * BAR * SR))
TARGET_LUFS = -12.0  # ngang bài nhạc có sẵn trong assets/music -> mức volume=0.15 khi mix vẫn cân

# Hợp âm mỗi ô nhịp (lặp vòng 4 ô): voicing pad/arp + nốt bass (số MIDI)
CHORDS = [
    {"pad": [57, 60, 64], "bass": 45},  # Am
    {"pad": [57, 60, 65], "bass": 41},  # F
    {"pad": [55, 60, 64], "bass": 48},  # C
    {"pad": [55, 59, 62], "bass": 43},  # G
]

# Giai điệu: mỗi phrase dài 4 ô nhịp, (ô nhịp, phách bắt đầu, nốt MIDI, độ dài tính bằng phách)
PHRASE_A = [(0, 0, 76, 3), (0, 3, 74, 1), (1, 0, 72, 4), (2, 0, 67, 2), (2, 2, 72, 2), (3, 0, 71, 3), (3, 3, 74, 1)]
PHRASE_B = [(0, 0, 76, 2), (0, 2, 79, 2), (1, 0, 77, 3), (1, 3, 76, 1), (2, 0, 76, 2), (2, 2, 72, 2), (3, 0, 74, 4)]
PHRASE_C = PHRASE_B[:-1] + [(3, 0, 79, 4)]  # kết lên G5 thay vì D5


def midi_hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def _t(n: int) -> np.ndarray:
    return np.arange(n) / SR


def add(bus: np.ndarray, sig: np.ndarray, t0: float, pan: float = 0.0, gain: float = 1.0) -> None:
    """Cộng tín hiệu vào bus stereo tại thời điểm t0 (giây), cuộn vòng về đầu nếu tràn cuối bài."""
    idx = (int(round(t0 * SR)) + np.arange(sig.shape[-1])) % LEN
    if sig.ndim == 1:
        a = (pan + 1) * np.pi / 4  # constant-power pan
        bus[0, idx] += sig * np.cos(a) * gain
        bus[1, idx] += sig * np.sin(a) * gain
    else:
        bus[:, idx] += sig * gain


# ----------------------------------------------------------------------------- nhạc cụ
def piano(m: int, vel: float, ring: float = 2.0, rng=None) -> np.ndarray:
    f = midi_hz(m)
    n = int(ring * SR)
    t = _t(n)
    out = np.zeros(n)
    for k in range(1, 11):
        fk = f * k * np.sqrt(1 + 0.0004 * k * k)  # hơi inharmonic như dây đàn thật
        if fk > 11000:
            break
        out += (1 / k ** 1.5) * np.sin(2 * np.pi * fk * t + rng.uniform(0, 2 * np.pi)) * np.exp(-t * (1.1 + 0.9 * k))
    env = np.minimum(1, t / 0.004)
    env[-int(0.05 * SR):] *= np.linspace(1, 0, int(0.05 * SR))
    return out * env * vel


def pad(m: int, dur: float, rng) -> np.ndarray:
    """Pad ấm: 3 lớp detune trái/giữa/phải, ít bồi âm cao, attack chậm."""
    f = midi_hz(m)
    rel = 1.4
    n = int((dur + rel) * SR)
    t = _t(n)
    out = np.zeros((2, n))
    for cents, pan in ((-8, -0.7), (0, 0.0), (8, 0.7)):
        fv = f * 2 ** (cents / 1200)
        v = np.zeros(n)
        for k in range(1, 13):
            v += (1 / k) * np.exp(-k / 3.0) * np.sin(2 * np.pi * fv * k * t + rng.uniform(0, 2 * np.pi))
        a = (pan + 1) * np.pi / 4
        out[0] += v * np.cos(a)
        out[1] += v * np.sin(a)
    env = np.minimum(1, t / 0.9)
    tail = t > dur
    env[tail] *= np.exp(-(t[tail] - dur) * 4)
    return out * env * (1 + 0.04 * np.sin(2 * np.pi * 0.3 * t))  # thở nhẹ


def bass(m: int, dur: float) -> np.ndarray:
    f = midi_hz(m)
    n = int((dur + 0.08) * SR)
    t = _t(n)
    sig = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) + 0.08 * np.sin(6 * np.pi * f * t)
    env = np.minimum(1, t / 0.008) * (0.75 + 0.25 * np.exp(-t * 6))
    env[t > dur] *= np.exp(-(t[t > dur] - dur) * 60)
    return sig * env


def kick(vel: float = 1.0) -> np.ndarray:
    n = int(0.45 * SR)
    t = _t(n)
    freq = 46 + 85 * np.exp(-t * 32)
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 7.5)
    click = np.exp(-t * 400) * 0.25
    return (body + click) * np.minimum(1, t / 0.0015) * vel


def hat(rng, vel: float = 1.0, open_: bool = False) -> np.ndarray:
    n = int((0.28 if open_ else 0.07) * SR)
    t = _t(n)
    noise = np.diff(rng.standard_normal(n + 2), 2)  # high-pass thô
    noise /= np.abs(noise).max()
    return noise * np.exp(-t * (16 if open_ else 75)) * vel


def bell(m: int, dur: float) -> np.ndarray:
    """Giai điệu: tiếng chuông/pluck mềm, có vibrato nhẹ khi ngân."""
    f = midi_hz(m)
    n = int((dur + 1.2) * SR)
    t = _t(n)
    vib = 1 + 0.003 * np.sin(2 * np.pi * 5 * t) * np.minimum(1, t / 0.5)
    ph = 2 * np.pi * f * np.cumsum(vib) / SR
    sig = np.sin(ph) + 0.22 * np.sin(2 * ph) + 0.06 * np.sin(3.01 * ph)
    env = np.minimum(1, t / 0.02) * np.exp(-t * 0.9)
    env[t > dur] *= np.exp(-(t[t > dur] - dur) * 5)
    return sig * env


def swell(rng, dur: float) -> np.ndarray:
    """Tiếng gió dâng lên trước khi vào đoạn mới."""
    n = int(dur * SR)
    t = _t(n)
    noise = np.diff(rng.standard_normal(n + 1))
    noise /= np.abs(noise).max()
    return noise * (t / dur) ** 3


# ----------------------------------------------------------------------------- xử lý
def circular_fft_filter(x: np.ndarray, gain: np.ndarray) -> np.ndarray:
    return np.fft.irfft(np.fft.rfft(x, axis=-1) * gain, n=x.shape[-1], axis=-1)


def reverb(x: np.ndarray, rng, seconds: float = 2.6, decay: float = 2.4) -> np.ndarray:
    """Reverb bằng convolution vòng tròn (FFT không pad) -> đuôi reverb cuối bài cuộn về đầu bài."""
    n = int(seconds * SR)
    t = _t(n)
    pre = int(0.018 * SR)
    out = np.empty_like(x)
    freqs = np.fft.rfftfreq(LEN, 1 / SR)
    damp = 1 / (1 + (freqs / 5000) ** 2)  # reverb tối, không chói
    for ch in range(2):
        ir = np.zeros(LEN)
        ir[pre:pre + n] = rng.standard_normal(n) * np.exp(-t * decay)
        out[ch] = np.fft.irfft(np.fft.rfft(x[ch]) * np.fft.rfft(ir) * damp, n=LEN)
    return out / np.abs(out).max()


def master_eq(x: np.ndarray) -> np.ndarray:
    f = np.fft.rfftfreq(LEN, 1 / SR)
    f_safe = np.maximum(f, 1.0)
    db = -5.0 * np.exp(-(np.log2(f_safe / 2000) ** 2) / (2 * 0.9 ** 2))  # khoét dải giọng nói
    db += -4.0 / (1 + (11000 / f_safe) ** 4)                              # bớt chói trên 11k
    gain = 10 ** (db / 20) * np.minimum(1, (f / 32) ** 2)                 # cắt siêu trầm < 32Hz
    return circular_fft_filter(x, gain)


def measure_lufs(wav_path: Path) -> float:
    res = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(wav_path), "-af", "ebur128", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    vals = re.findall(r"I:\s+(-?[\d.]+) LUFS", res.stderr)
    return float(vals[-1])


def write_wav(path: Path, x: np.ndarray) -> None:
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").T.copy()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ----------------------------------------------------------------------------- phối khí
def compose(seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    music = np.zeros((2, LEN))  # pad + piano + giai điệu (có reverb, bị sidechain)
    low = np.zeros((2, LEN))    # bass (bị sidechain)
    drums = np.zeros((2, LEN))
    kick_times = []

    for b in range(N_BARS):
        t_bar = b * BAR
        ch = CHORDS[b % 4]
        intro, heartbeat, main, lift = b < 4, 4 <= b < 8, 8 <= b < 24, 24 <= b < 28
        outro = b >= 28
        energy = 0.7 if intro else 0.75 if heartbeat else 1.0 if (main or lift) else 0.7

        # Pad
        for m in ch["pad"]:
            add(music, pad(m, BAR, rng), t_bar, gain=0.085 * energy)

        # Piano arpeggio (nốt hợp âm + quãng tám): intro chơi phách đen, sau đó móc đơn
        tones = ch["pad"] + [p + 12 for p in ch["pad"]][:2]
        pattern = [0, 1, 2, 3, 4, 3, 2, 1]
        step, n_steps = (BEAT, 4) if intro else (BEAT / 2, 8)
        for i in range(n_steps):
            vel = (1.0 if i % (2 if step < BEAT else 1) == 0 else 0.72) * (0.85 + 0.15 * rng.random())
            note = tones[pattern[(i * (2 if intro else 1)) % 8]]
            add(music, piano(note, vel, rng=rng), t_bar + i * step + rng.normal(0, 0.004),
                pan=0.25 if i % 2 else -0.25, gain=0.16)

        # Bass: nốt tròn ở đoạn heartbeat, móc đơn đều đặn ở đoạn chính
        if heartbeat or outro:
            add(low, bass(ch["bass"], BAR * 0.95), t_bar, gain=0.30)
        elif main or lift:
            for i in range(8):
                add(low, bass(ch["bass"], BEAT / 2 * 0.8), t_bar + i * BEAT / 2, gain=0.30 if i % 2 == 0 else 0.22)

        # Trống
        if heartbeat:  # "thình-thịch" như nhịp tim ở phách 1 và 3
            for beat in (0, 2):
                kick_times.append(t_bar + beat * BEAT)
                add(drums, kick(0.85), t_bar + beat * BEAT, gain=0.55)
                add(drums, kick(0.5), t_bar + (beat + 0.33) * BEAT, gain=0.55)
        elif main or lift or (outro and b < 30):
            for beat in range(4):
                kick_times.append(t_bar + beat * BEAT)
                add(drums, kick(1.0 if beat % 2 == 0 else 0.85), t_bar + beat * BEAT, gain=0.55)
            for i in range(8):  # tích - tắc: hat đều mỗi móc đơn, nhấn ở nhịp nghịch
                off = i % 2 == 1
                add(drums, hat(rng, 0.9 if off else 0.45, open_=lift and off),
                    t_bar + i * BEAT / 2 + rng.normal(0, 0.003), pan=0.3, gain=0.07)

        # Giai điệu: ô 12-27, phrase A-B-A-C (C = B nhưng kết lên nốt cao hơn -> đi lên = tiến bộ)
        if 12 <= b < 28 and (b - 12) % 4 == 0:
            k = (b - 12) // 4
            phrase = [PHRASE_A, PHRASE_B, PHRASE_A, PHRASE_C][k]
            for bar_off, beat, m, dur in phrase:
                add(music, bell(m, dur * BEAT), (b + bar_off) * BAR + beat * BEAT, pan=0.1, gain=0.11)

    # Tiếng gió dâng trước đoạn chính và đoạn cao trào
    for b in (8, 24):
        sw = swell(rng, BAR)
        add(drums, np.vstack([sw, np.roll(sw, 37)]), (b - 1) * BAR, gain=0.03)

    # Sidechain: nhạc + bass nhường chỗ cho tiếng kick -> cảm giác "thở" theo nhịp
    duck = np.ones(LEN)
    win = int(0.4 * SR)
    shape = 1 - 0.35 * np.exp(-_t(win) / 0.11)
    for kt in kick_times:
        idx = (int(round(kt * SR)) + np.arange(win)) % LEN
        duck[idx] = np.minimum(duck[idx], shape)

    wet = reverb(music, rng)
    music_mix = (music + 0.35 * wet * np.abs(music).max()) * duck
    mix = music_mix + low * duck + drums
    mix = master_eq(mix)
    return mix / np.abs(mix).max()


def render(out_path: Path, seed: int = 7) -> Path:
    mix = compose(seed)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "mix.wav"
        ceiling = 0.89  # ~ -1 dBFS
        gain = 0.5
        for _ in range(3):  # lặp vài lần vì limiter làm lệch loudness một chút
            final = ceiling * np.tanh(mix * gain / ceiling)  # limiter mềm, đỉnh không vượt ceiling
            write_wav(wav, final)
            gain *= 10 ** ((TARGET_LUFS - measure_lufs(wav)) / 20)
        final = ceiling * np.tanh(mix * gain / ceiling)
        write_wav(wav, final)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav),
             "-codec:a", "libmp3lame", "-b:a", "192k", str(out_path)],
            check=True,
        )
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "assets" / "music" / "daily_discipline.mp3")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    path = render(args.out, args.seed)
    print(f"Đã tạo nhạc nền: {path} ({N_BARS} ô nhịp, {BPM} BPM, {LEN / SR:.1f}s, lặp liền mạch)")
