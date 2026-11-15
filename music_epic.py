"""Tự sinh nhạc nền "Rise Together" — phong cách epic / cinematic trailer, bằng numpy, không dính bản quyền.

Ý tưởng âm nhạc (mạnh mẽ, hùng tráng, vẫn chừa chỗ cho giọng đọc):
- Rê thứ, vòng hợp âm Dm - Bb - F - C (i - VI - III - VII)  -> kinh điển của nhạc trailer, hùng tráng
- 112 BPM, kick dồn từng phách + tom/taiko trầm + tiếng vỗ (clap) có reverb dài  -> nhịp hành quân mạnh
- Dàn dây ostinato nốt móc đơn, đồng ca "aah", kèn đồng chặn nhịp, bass có gằn  -> dày và đầy
- Có riser dâng lên, tiếng va chạm (impact) trầm và chũm chọe (crash) ở mỗi mốc chuyển đoạn
- Dải ~2kHz được khoét bớt và nhạc đứt nhẹ theo nhịp kick (sidechain) -> giọng đọc TTS vẫn rõ

Cấu trúc 40 ô nhịp (~85s), render dạng vòng tròn: đuôi riser/reverb cuộn về impact ở đầu bài, nên khi
video_builder lặp nhạc (-stream_loop -1) sẽ nối liền mạch.

  ô  0- 3  mở đầu: drone trầm + dây ngân, tim đập         ô 20-35  cao trào: đầy đủ, giai điệu lên cao
  ô  4- 7  dồn dập: ostinato dây + taiko, snare roll       ô 36-39  hạ xuống + riser kéo về đầu bài
  ô  8-15  đoạn chính: kick, clap, kèn, giai điệu A
  ô 16-19  lắng: đồng ca + piano, riser

Chạy:  python music_epic.py                       # ghi ra assets/music/rise_together.mp3
       python music_epic.py --out x.mp3 --seed 3  # đổi seed để ra biến thể (phase, độ lệch nhịp...)
"""
import argparse
import re
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 44100
BPM = 112
BEAT = 60 / BPM
BAR = 4 * BEAT
N_BARS = 40
LEN = int(round(N_BARS * BAR * SR))
TARGET_LUFS = -11.0  # to hơn bài Daily Discipline (-12.3) một chút cho cảm giác "strong"

# Hợp âm mỗi ô nhịp (vòng 4 ô): voicing đồng ca/dây (số MIDI) + nốt bass
CHORDS = [
    {"upper": [62, 65, 69], "bass": 38},  # Dm
    {"upper": [62, 65, 70], "bass": 34},  # Bb
    {"upper": [60, 65, 69], "bass": 41},  # F
    {"upper": [60, 64, 67], "bass": 36},  # C
]

# Giai điệu 4 ô nhịp: (ô nhịp, phách bắt đầu, nốt MIDI, độ dài tính bằng phách)
PHRASE_A = [(0, 0, 69, 2), (0, 2, 74, 2), (1, 0, 77, 2), (1, 2, 74, 2),
            (2, 0, 72, 2), (2, 2, 77, 2), (3, 0, 76, 2), (3, 2, 72, 1), (3, 3, 69, 1)]
PHRASE_B = [(0, 0, 81, 2), (0, 2, 77, 2), (1, 0, 82, 2), (1, 2, 79, 2),
            (2, 0, 81, 2), (2, 2, 84, 2), (3, 0, 79, 2), (3, 2, 76, 2)]


def midi_hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def _t(n: int) -> np.ndarray:
    return np.arange(n) / SR


def add(bus: np.ndarray, sig: np.ndarray, t0: float, pan: float = 0.0, gain: float = 1.0) -> None:
    """Cộng tín hiệu vào bus stereo tại t0 (giây), cuộn vòng về đầu bài nếu tràn cuối bài."""
    idx = (int(round(t0 * SR)) + np.arange(sig.shape[-1])) % LEN
    if sig.ndim == 1:
        a = (pan + 1) * np.pi / 4  # constant-power pan
        np.add.at(bus[0], idx, sig * np.cos(a) * gain)
        np.add.at(bus[1], idx, sig * np.sin(a) * gain)
    else:
        np.add.at(bus[0], idx, sig[0] * gain)
        np.add.at(bus[1], idx, sig[1] * gain)


# ----------------------------------------------------------------------------- nhạc cụ
_cache: dict = {}


def _cached(key, fn):
    if key not in _cache:
        _cache[key] = fn()
    return _cache[key]


def saw_ensemble(m: int, dur: float, rel: float = 0.25, attack: float = 0.02, bright: float = 0.12,
                 detune=(-14, 0, 14), vib: float = 0.0, seed: int = 0) -> np.ndarray:
    """Dàn dây/kèn: vài giọng sawtooth lệch cao độ (detune) -> stereo, dày. Trả về (2, n)."""
    def make():
        rng = np.random.default_rng(1000 + m + seed)
        f0 = midi_hz(m)
        n = int((dur + rel) * SR)
        t = _t(n)
        out = np.zeros((2, n))
        for i, cents in enumerate(detune):
            f = f0 * 2 ** (cents / 1200)
            ph = 2 * np.pi * np.cumsum(f * (1 + vib * np.sin(2 * np.pi * 5.2 * t) * np.minimum(1, t / 0.6))) / SR
            v = np.zeros(n)
            k = 1
            while k <= 40 and f * k < 9000:
                v += (1 / k) * np.exp(-k * bright) * np.sin(k * ph + rng.uniform(0, 2 * np.pi))
                k += 1
            pan = -0.8 + 1.6 * i / max(1, len(detune) - 1)
            a = (pan + 1) * np.pi / 4
            out[0] += v * np.cos(a)
            out[1] += v * np.sin(a)
        env = np.minimum(1, t / attack)
        tail = t > dur
        env[tail] *= np.exp(-(t[tail] - dur) / (rel / 4))
        return out * env / len(detune)
    return _cached(("saw", m, round(dur, 3), rel, attack, bright, detune, vib, seed), make)


def choir(m: int, dur: float, seed: int = 0) -> np.ndarray:
    """Đồng ca 'aah': hài âm nhấn quanh vùng formant ~800Hz và ~1200Hz, attack chậm, có vibrato."""
    def make():
        rng = np.random.default_rng(2000 + m + seed)
        f0 = midi_hz(m)
        rel = 1.2
        n = int((dur + rel) * SR)
        t = _t(n)
        out = np.zeros((2, n))
        for cents, pan in ((-9, -0.7), (0, 0.0), (9, 0.7)):
            f = f0 * 2 ** (cents / 1200)
            ph = 2 * np.pi * np.cumsum(f * (1 + 0.004 * np.sin(2 * np.pi * 5.0 * t))) / SR
            v = np.zeros(n)
            for k in range(1, 30):
                fk = f * k
                if fk > 6000:
                    break
                w = (np.exp(-((fk - 800) / 330) ** 2) + 0.6 * np.exp(-((fk - 1200) / 380) ** 2)
                     + 0.12 * np.exp(-k / 5)) / k ** 0.7
                v += w * np.sin(k * ph + rng.uniform(0, 2 * np.pi))
            a = (pan + 1) * np.pi / 4
            out[0] += v * np.cos(a)
            out[1] += v * np.sin(a)
        env = np.minimum(1, t / 0.7)
        tail = t > dur
        env[tail] *= np.exp(-(t[tail] - dur) * 3.5)
        return out * env / 3
    return _cached(("choir", m, round(dur, 3), seed), make)


def piano(m: int, vel: float, ring: float, rng) -> np.ndarray:
    f = midi_hz(m)
    n = int(ring * SR)
    t = _t(n)
    out = np.zeros(n)
    for k in range(1, 10):
        fk = f * k * np.sqrt(1 + 0.0004 * k * k)
        if fk > 9000:
            break
        out += (1 / k ** 1.4) * np.sin(2 * np.pi * fk * t + rng.uniform(0, 2 * np.pi)) * np.exp(-t * (1.0 + 0.8 * k))
    env = np.minimum(1, t / 0.004)
    env[-int(0.05 * SR):] *= np.linspace(1, 0, int(0.05 * SR))
    return out * env * vel


def bass(m: int, dur: float) -> np.ndarray:
    """Bass trầm có gằn: sine + hài âm, đẩy qua tanh để dày và nghe rõ cả trên loa nhỏ điện thoại."""
    def make():
        f = midi_hz(m)
        n = int((dur + 0.08) * SR)
        t = _t(n)
        sig = np.sin(2 * np.pi * f * t) + 0.45 * np.sin(4 * np.pi * f * t) + 0.25 * np.sin(6 * np.pi * f * t)
        sig = np.tanh(1.8 * sig) / 1.4
        env = np.minimum(1, t / 0.006) * (0.8 + 0.2 * np.exp(-t * 7))
        env[t > dur] *= np.exp(-(t[t > dur] - dur) * 55)
        return sig * env
    return _cached(("bass", m, round(dur, 3)), make)


def kick(vel: float = 1.0) -> np.ndarray:
    n = int(0.5 * SR)
    t = _t(n)
    freq = 44 + 95 * np.exp(-t * 34)
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 6.5)
    click = np.exp(-t * 450) * 0.3
    return (body + click) * np.minimum(1, t / 0.0015) * vel


def taiko(vel: float = 1.0, pitch: float = 62.0) -> np.ndarray:
    """Trống lớn kiểu taiko/tom trầm: cao độ rơi nhanh + ngân dài + chút tiếng da trống."""
    def make():
        n = int(1.1 * SR)
        t = _t(n)
        freq = pitch + 70 * np.exp(-t * 16)
        body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 4.2)
        rng = np.random.default_rng(5)
        skin = rng.standard_normal(n) * np.exp(-t * 55) * 0.35
        return (body * 1.0 + skin) * np.minimum(1, t / 0.002)
    return _cached(("taiko", pitch), make) * vel


def clap(rng, vel: float = 1.0) -> np.ndarray:
    """Snare/clap to: nhiều lớp nhiễu trễ nhau vài ms + thân trầm ~185Hz. Đưa vào bus có reverb."""
    n = int(0.45 * SR)
    t = _t(n)
    noise = np.diff(rng.standard_normal(n + 1))
    noise /= np.abs(noise).max()
    burst = np.zeros(n)
    for d in (0.0, 0.011, 0.023):
        i = int(d * SR)
        burst[i:] += noise[:n - i] * np.exp(-(t[:n - i]) * 30)
    body = np.sin(2 * np.pi * 185 * t) * np.exp(-t * 26) * 0.7
    return (burst * 0.55 + body) * vel


def hat(rng, vel: float = 1.0) -> np.ndarray:
    n = int(0.07 * SR)
    t = _t(n)
    noise = np.diff(rng.standard_normal(n + 2), 2)
    noise /= np.abs(noise).max()
    return noise * np.exp(-t * 80) * vel


def crash(rng, dur: float = 3.2) -> np.ndarray:
    n = int(dur * SR)
    t = _t(n)
    noise = np.diff(rng.standard_normal(n + 2), 2)
    noise /= np.abs(noise).max()
    return noise * np.exp(-t * 1.5) * np.minimum(1, t / 0.004)


def impact(rng, dur: float = 2.6) -> np.ndarray:
    """Cú 'boom' trầm ở mốc chuyển đoạn: sub-bass rơi tần số + nổ nhiễu ngắn."""
    n = int(dur * SR)
    t = _t(n)
    freq = 28 + 55 * np.exp(-t * 6)
    sub = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 1.5)
    boom = np.diff(rng.standard_normal(n + 1))
    boom = boom / np.abs(boom).max() * np.exp(-t * 9) * 0.5
    return (sub * 1.1 + boom) * np.minimum(1, t / 0.002)


def riser(rng, dur: float) -> np.ndarray:
    """Tiếng dâng: nhiễu to dần + một đường sine trượt từ trầm lên cao."""
    n = int(dur * SR)
    t = _t(n)
    x = t / dur
    noise = np.diff(rng.standard_normal(n + 1))
    noise /= np.abs(noise).max()
    sweep = np.sin(2 * np.pi * np.cumsum(180 + 2400 * x ** 2) / SR)
    sig = (noise * 0.6 + sweep * 0.5) * x ** 2.2
    sig[-int(0.02 * SR):] *= np.linspace(1, 0, int(0.02 * SR))
    return np.vstack([sig, np.roll(sig, 41)])


# ----------------------------------------------------------------------------- xử lý
def reverb(x: np.ndarray, rng, seconds: float, decay: float) -> np.ndarray:
    """Reverb bằng convolution vòng tròn (FFT) -> đuôi reverb cuối bài cuộn về đầu bài."""
    n = int(seconds * SR)
    t = _t(n)
    pre = int(0.02 * SR)
    freqs = np.fft.rfftfreq(LEN, 1 / SR)
    damp = 1 / (1 + (freqs / 6500) ** 2)
    out = np.empty_like(x)
    for ch in range(2):
        ir = np.zeros(LEN)
        ir[pre:pre + n] = rng.standard_normal(n) * np.exp(-t * decay)
        out[ch] = np.fft.irfft(np.fft.rfft(x[ch]) * np.fft.rfft(ir) * damp, n=LEN)
    peak = np.abs(out).max()
    return out / peak if peak > 0 else out


def master_eq(x: np.ndarray) -> np.ndarray:
    f = np.fft.rfftfreq(LEN, 1 / SR)
    f_safe = np.maximum(f, 1.0)
    db = -4.0 * np.exp(-(np.log2(f_safe / 2000) ** 2) / (2 * 0.9 ** 2))  # khoét dải giọng nói
    db += -4.0 / (1 + (12000 / f_safe) ** 4)                              # bớt chói trên 12k
    gain = 10 ** (db / 20) * np.minimum(1, (f / 30) ** 2)                 # cắt siêu trầm < 30Hz
    return np.fft.irfft(np.fft.rfft(x, axis=-1) * gain, n=LEN, axis=-1)


def measure_lufs(wav_path: Path) -> float:
    res = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(wav_path), "-af", "ebur128", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", res.stderr)[-1])


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
    music = np.zeros((2, LEN))   # dây, đồng ca, kèn, piano, giai điệu (có reverb, bị sidechain)
    low = np.zeros((2, LEN))     # bass + drone (bị sidechain)
    drums = np.zeros((2, LEN))   # kick, taiko, hat (khô)
    wetdrums = np.zeros((2, LEN))  # clap/snare/crash/impact (đưa qua reverb dài)
    fx = np.zeros((2, LEN))      # riser
    kick_times = []

    def beat_t(b, beat):  # thời điểm (giây) của phách `beat` trong ô nhịp b
        return b * BAR + beat * BEAT

    for b in range(N_BARS):
        ch = CHORDS[b % 4]
        root = ch["bass"]
        intro, build, main, calm = b < 4, 4 <= b < 8, 8 <= b < 16, 16 <= b < 20
        final, outro = 20 <= b < 36, b >= 36
        energy = 0.55 if intro else 0.8 if build else 1.0 if main else 0.6 if calm else 1.1 if final else 0.7

        # --- Nền ngân dài: dây trầm + drone ---
        for m in (root + 12, root + 19, root + 24):
            add(music, saw_ensemble(m, BAR * 0.98, rel=0.6, attack=0.35, bright=0.14), beat_t(b, 0),
                gain=0.10 * energy)
        add(low, bass(root, BAR * 0.99) * 0.55, beat_t(b, 0), gain=0.14 if (intro or calm or outro) else 0.07)

        # --- Đồng ca: đoạn lắng và cao trào ---
        if calm or final:
            for m in ch["upper"]:
                add(music, choir(m + 12, BAR * 0.98), beat_t(b, 0), gain=0.10 if final else 0.09)

        # --- Piano rải ở đoạn mở đầu, lắng và hạ xuống ---
        if intro or calm or outro:
            tones = ch["upper"] + [p + 12 for p in ch["upper"]]
            for i in range(8):
                v = (1.0 if i % 2 == 0 else 0.7) * (0.85 + 0.15 * rng.random())
                add(music, piano(tones[[0, 1, 2, 3, 4, 5, 4, 3][i]], v, 2.2, rng),
                    beat_t(b, i * 0.5) + rng.normal(0, 0.004), pan=-0.3 if i % 2 else 0.3, gain=0.12)

        # --- Ostinato dây nốt móc đơn: dồn dập, đẩy năng lượng ---
        if build or main or final:
            pat = [0, 12, 7, 12, 0, 12, 7, 12]
            for i, semi in enumerate(pat):
                acc = 1.0 if i % 2 == 0 else 0.7
                add(music, saw_ensemble(root + 24 + semi, BEAT * 0.5 * 0.7, rel=0.07, attack=0.006, bright=0.08,
                                        detune=(-9, 9)),
                    beat_t(b, i * 0.5), gain=(0.22 if final else 0.17) * acc)

        # --- Kèn đồng chặn nhịp: phách 1 dài và "và của 2" ngắn ---
        if main or final:
            for semi, g in ((0, 1.0), (7, 0.9), (12, 0.8)):
                add(music, saw_ensemble(root + 24 + semi, BEAT * 1.1, rel=0.2, attack=0.015, bright=0.05,
                                        detune=(-12, 0, 12)), beat_t(b, 0), gain=0.14 * g * energy)
            for semi in (0, 7, 12):
                add(music, saw_ensemble(root + 24 + semi, BEAT * 0.4, rel=0.12, attack=0.012, bright=0.05,
                                        detune=(-12, 0, 12)), beat_t(b, 1.5), gain=0.10)

        # --- Bass: nốt móc đơn dồn đoạn chính/cao trào, nốt dài ở đoạn build/outro ---
        if main or final:
            for i in range(8):
                add(low, bass(root, BEAT * 0.5 * 0.82), beat_t(b, i * 0.5),
                    gain=(0.17 if i % 2 == 0 else 0.12) * (1.1 if final else 1.0))
        elif build or outro:
            for beat in (0, 2):
                add(low, bass(root, BEAT * 1.9), beat_t(b, beat), gain=0.20)

        # --- Trống ---
        if build:
            for beat in (0, 2):
                kick_times.append(beat_t(b, beat))
                add(drums, kick(0.85), beat_t(b, beat), gain=0.38)
            add(drums, taiko(1.0), beat_t(b, 0), gain=0.40)
            add(drums, taiko(0.8, 58), beat_t(b, 3.5), gain=0.35)
            if b == 7:  # snare roll dồn vào đoạn chính, dày dần
                for i in range(8):
                    add(wetdrums, clap(rng, 0.35 + 0.65 * i / 7), beat_t(b, 2 + i * 0.25), gain=0.35)
        elif main or final:
            for beat in range(4):
                kick_times.append(beat_t(b, beat))
                add(drums, kick(1.0 if beat % 2 == 0 else 0.85), beat_t(b, beat), gain=0.42)
            add(drums, taiko(1.0), beat_t(b, 0), gain=0.38)
            for beat in (1, 3):
                add(wetdrums, clap(rng, 1.0), beat_t(b, beat), gain=0.65)
            add(drums, taiko(0.85, 56), beat_t(b, 2.5), gain=0.32)
            add(drums, taiko(0.8, 52), beat_t(b, 3.5), gain=0.32)
            if final and b % 2 == 1:  # nhồi thêm 2 tiếng tom nối để cao trào có sức đẩy
                add(drums, taiko(0.7, 66), beat_t(b, 3.75), gain=0.32)
            for i in range(8):
                add(drums, hat(rng, 0.9 if i % 2 else 0.45), beat_t(b, i * 0.5) + rng.normal(0, 0.003),
                    pan=0.3, gain=0.09)
            if b == 15 or b == 35:  # roll cuối đoạn
                for i in range(8):
                    add(wetdrums, clap(rng, 0.35 + 0.65 * i / 7), beat_t(b, 2 + i * 0.25), gain=0.35)
        elif calm:
            kick_times.append(beat_t(b, 0))
            add(drums, taiko(0.8, 58), beat_t(b, 0), gain=0.4)
        elif outro and b < 39:
            add(drums, taiko(0.8 - 0.1 * (b - 36), 58), beat_t(b, 0), gain=0.4)

        # --- Va chạm + chũm chọe ở mốc chuyển đoạn ---
        if b in (0, 8, 20, 28, 32):
            add(wetdrums, impact(rng), beat_t(b, 0), gain=0.5 if b in (0, 8, 20) else 0.35)
            add(wetdrums, crash(rng), beat_t(b, 0), gain=0.35)

    # --- Giai điệu (kèn + dây): A ở đoạn chính, B ở cao trào ---
    def melody(start_bar, phrase, octave_double=False, gain=0.17):
        for bar_off, beat, m, dur in phrase:
            t0 = beat_t(start_bar + bar_off, beat)
            add(music, saw_ensemble(m, dur * BEAT * 0.97, rel=0.3, attack=0.03, bright=0.06,
                                    detune=(-10, 0, 10), vib=0.004, seed=1), t0, pan=0.1, gain=gain)
            if octave_double:
                add(music, saw_ensemble(m - 12, dur * BEAT * 0.97, rel=0.3, attack=0.03, bright=0.09,
                                        detune=(-8, 8), vib=0.004, seed=2), t0, pan=-0.1, gain=gain * 0.7)

    melody(8, PHRASE_A)
    melody(12, PHRASE_A, octave_double=True)
    for s in (20, 24, 28, 32):
        melody(s, PHRASE_B, octave_double=True, gain=0.18)

    # --- Riser dâng vào các mốc chuyển đoạn (kể cả cuối bài kéo về impact ở đầu bài) ---
    for b_end, bars in ((4, 1.5), (8, 2), (20, 2), (N_BARS, 3)):
        dur = BAR * bars
        add(fx, riser(rng, dur), b_end * BAR - dur, gain=0.11)

    # --- Sidechain: nhạc + bass lùi một chút ở mỗi tiếng kick -> "thở" theo nhịp ---
    duck = np.ones(LEN)
    win = int(0.35 * SR)
    shape = 1 - 0.38 * np.exp(-_t(win) / 0.1)
    for kt in kick_times:
        idx = (int(round(kt * SR)) + np.arange(win)) % LEN
        duck[idx] = np.minimum(duck[idx], shape)

    wet_music = reverb(music, rng, seconds=2.8, decay=2.1)
    wet_drums = reverb(wetdrums, rng, seconds=2.2, decay=3.0)
    music_mix = (music + 0.38 * wet_music * np.abs(music).max()) * duck
    drums_mix = drums + wetdrums * 0.8 + 0.45 * wet_drums * max(np.abs(wetdrums).max(), 1e-9)
    mix = music_mix + low * duck + drums_mix + fx
    mix = master_eq(mix)
    return mix / np.abs(mix).max()


def render(out_path: Path, seed: int = 7) -> Path:
    mix = compose(seed)
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "mix.wav"
        ceiling = 0.89  # ~ -1 dBFS
        gain = 0.5
        for _ in range(4):  # lặp vài lần vì limiter làm lệch loudness một chút
            write_wav(wav, ceiling * np.tanh(mix * gain / ceiling))
            gain *= 10 ** ((TARGET_LUFS - measure_lufs(wav)) / 20)
        write_wav(wav, ceiling * np.tanh(mix * gain / ceiling))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav),
             "-codec:a", "libmp3lame", "-b:a", "192k", str(out_path)],
            check=True,
        )
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "assets" / "music" / "rise_together.mp3")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    path = render(args.out, args.seed)
    print(f"Đã tạo nhạc nền: {path} ({N_BARS} ô nhịp, {BPM} BPM, {LEN / SR:.1f}s, lặp liền mạch)")
