"""Genera efectos de sonido y pistas de fondo por intención, 100% sintetizados (sin derechos de autor).
Uso: python3 sfx.py OUTDIR
"""
import sys, os, numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile

SR = 48000
rng = np.random.default_rng(7)

def env(n, a=0.005, r=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(r, 1e-4))

def bp(x, lo, hi, order=2): return sosfilt(butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x)
def lp(x, f, order=2): return sosfilt(butter(order, f, "lowpass", fs=SR, output="sos"), x)
def hp(x, f, order=2): return sosfilt(butter(order, f, "highpass", fs=SR, output="sos"), x)

def norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1
    return x / m * peak

def save(path, x):
    x = np.clip(x, -1, 1)
    st = np.stack([x, x], 1) if x.ndim == 1 else x
    wavfile.write(path, SR, (st * 32767).astype(np.int16))

def whoosh(d=0.45):
    n = int(SR * d); t = np.arange(n) / SR
    noise = rng.standard_normal(n); out = np.zeros(n); blocks = 24
    for i in range(blocks):
        s, e = i * n // blocks, (i + 1) * n // blocks
        f = 300 + (4500 - 300) * np.sin(np.pi * (i / blocks)) ** 2
        out[s:e] = bp(noise, max(80, f * 0.6), min(20000, f * 1.6))[s:e]
    return norm(out * np.sin(np.pi * t / d) ** 2, 0.7)

def pop():
    n = int(SR * 0.12); t = np.arange(n) / SR
    f = 1100 * np.exp(-t * 28) + 250
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.035), 0.8)

def impact():
    n = int(SR * 1.1); t = np.arange(n) / SR
    f = 120 * np.exp(-t * 6) + 42
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.35)
    crack = hp(rng.standard_normal(n), 1500) * env(n, 0.001, 0.05) * 0.5
    body = lp(rng.standard_normal(n), 400) * env(n, 0.002, 0.18) * 0.6
    return norm(sub + crack + body, 0.95)

def riser(d=0.9):
    n = int(SR * d); t = np.arange(n) / SR
    noise = hp(rng.standard_normal(n), 2000) * (t / d) ** 2
    f = 200 + 1400 * (t / d) ** 2
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / d) ** 2 * 0.4
    return norm(noise * 0.6 + tone, 0.6)

def ding():
    n = int(SR * 1.0); t = np.arange(n) / SR
    x = sum(a * np.sin(2 * np.pi * f * t) for f, a in [(1318.5, 1), (2637, .4), (3955, .15)])
    return norm(x * env(n, 0.002, 0.28), 0.6)

def click():
    n = int(SR * 0.03)
    return norm(hp(rng.standard_normal(n), 3000) * env(n, 0.0005, 0.006), 0.6)

def glitch():
    n = int(SR * 0.25); x = np.zeros(n)
    for k in range(6):
        s = int(k * n / 6); m = int(n / 9)
        f = rng.uniform(300, 2400); t = np.arange(m) / SR
        x[s:s + m] += np.sign(np.sin(2 * np.pi * f * t)) * 0.4 + hp(rng.standard_normal(m), 2000) * 0.5
    return norm(x * env(n, 0.001, 0.15), 0.6)

NOTE = lambda m: 440 * 2 ** ((m - 69) / 12)

def kick(n):
    t = np.arange(n) / SR
    f = 110 * np.exp(-t * 30) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.12)

def hat(n): return hp(rng.standard_normal(n), 7000) * env(n, 0.0005, 0.025) * 0.25

def pad(freqs, n):
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * 0.3 * t)) + 0.5 * np.sin(2 * np.pi * f * 2.003 * t) for f in freqs)
    a = np.minimum(1, t / 0.4) * np.minimum(1, (t[-1] - t + 1e-3) / 0.4)
    return lp(x, 2200) * a / len(freqs)

def pluck(f, n):
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * 2 * f * t)) * env(n, 0.002, 0.18)

def track(mood, seconds=70):
    cfg = {
        "motivacional": dict(bpm=100, prog=[[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]], drums=True, arp=False, bass=True),
        "tech":         dict(bpm=112, prog=[[50, 53, 57], [46, 50, 53], [43, 46, 50], [45, 48, 52]], drums=True, arp=True, bass=True),
        "reflexivo":    dict(bpm=72,  prog=[[52, 55, 59], [48, 52, 55], [45, 48, 52], [47, 50, 54]], drums=False, arp=True, bass=False),
        "energia":      dict(bpm=124, prog=[[57, 60, 64], [55, 59, 62], [53, 57, 60], [55, 59, 62]], drums=True, arp=True, bass=True),
    }[mood]
    beat = 60 / cfg["bpm"]; bar = 4 * beat
    total = int(SR * seconds); out = np.zeros(total)
    for b in range(int(seconds / bar) + 1):
        s = int(b * bar * SR); chord = cfg["prog"][b % 4]
        seg = pad([NOTE(m) for m in chord], int(bar * SR))
        e = min(total, s + len(seg)); out[s:e] += 0.35 * seg[: e - s]
        if cfg["bass"]:
            for q in range(4):
                bs = s + int(q * beat * SR); bn = int(beat * SR * 0.9)
                if bs + bn < total: out[bs:bs + bn] += 0.35 * pluck(NOTE(chord[0] - 12), bn)
        if cfg["arp"]:
            for q in range(8):
                ps = s + int(q * beat / 2 * SR); pn = int(beat * SR)
                if ps + pn < total: out[ps:ps + pn] += 0.16 * pluck(NOTE(chord[q % 3] + 12), pn)
        if cfg["drums"]:
            for q in range(4):
                ks = s + int(q * beat * SR); kn = int(0.3 * SR)
                if ks + kn < total: out[ks:ks + kn] += 0.6 * kick(kn)
            for q in range(8):
                hs = s + int((q + 0.5) * beat / 2 * SR); hn = int(0.06 * SR)
                if hs + hn < total: out[hs:hs + hn] += hat(hn)
    return norm(lp(out, 9000), 0.8)

if __name__ == "__main__":
    d = sys.argv[1]; os.makedirs(d, exist_ok=True)
    for name, fn in [("whoosh", whoosh), ("pop", pop), ("impact", impact), ("riser", riser), ("ding", ding), ("click", click), ("glitch", glitch)]:
        save(os.path.join(d, name + ".wav"), fn())
    for m in ["motivacional", "tech", "reflexivo", "energia"]:
        save(os.path.join(d, f"musica_{m}.wav"), track(m))
    print("ok")
