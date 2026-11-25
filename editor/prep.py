"""Paso 1 · prepara un crudo: HDR→SDR 1080x1920 30fps, limpia ruido, transcribe, corta silencios.
Uso: python3 prep.py CRUDO  → escribe CRUDO_work/ y CRUDO.timeline.txt"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
WHISPER = os.environ.get("WHISPER", "/home/claude/whisper-small")

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-3000:]); raise SystemExit("Falló: " + " ".join(cmd[:4]))
    return r.stdout

def dur_of(p): return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]).strip())

def keep_ranges(words, dur, gap=0.40, pad=0.10):
    if not words: return [(0, dur)]
    out = []; cs, ce = max(0, words[0]["s"] - pad), words[0]["e"]
    for w in words[1:]:
        if w["s"] - ce > gap: out.append((cs, min(dur, ce + pad))); cs = max(0, w["s"] - pad)
        ce = w["e"]
    out.append((cs, min(dur, ce + pad)))
    m = []
    for a, b in out:
        if m and a <= m[-1][1]: m[-1] = (m[-1][0], b)
        else: m.append((a, b))
    return m

def remap(t, rngs):
    acc = 0.0
    for a, b in rngs:
        if t < a: return acc
        if t <= b: return acc + (t - a)
        acc += b - a
    return acc

def cut_points(rngs):
    acc, pts = 0, []
    for a, b in rngs[:-1]: acc += b - a; pts.append(acc)
    return pts

def prepare(src):
    base = os.path.splitext(src)[0]; work = base + "_work"; os.makedirs(work, exist_ok=True)
    std = os.path.join(work, "std.mp4")
    if not os.path.exists(std):
        ct = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer", "-of", "csv=p=0", src]).strip()
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30"
        if ct in ("arib-std-b67", "smpte2084"):
            vf = "zscale=t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p," + vf
        print("Normalizando video…", flush=True)
        run(["ffmpeg", "-y", "-i", src, "-vf", vf, "-c:v", "libx264", "-crf", "15", "-preset", "veryfast", "-c:a", "aac", "-b:a", "256k", std])
    clean = os.path.join(work, "std_clean.mov")
    if not os.path.exists(clean):
        print("Limpiando ruido…", flush=True)
        raw = os.path.join(work, "raw.wav"); cw = os.path.join(work, "clean.wav")
        run(["ffmpeg", "-y", "-i", std, "-vn", "-ac", "1", "-ar", "48000", raw])
        run([sys.executable, os.path.join(HERE, "denoise.py"), raw, cw])
        run(["ffmpeg", "-y", "-i", std, "-i", cw, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "pcm_s16le", clean])
    wj = os.path.join(work, "words.json")
    if not os.path.exists(wj):
        print("Transcribiendo…", flush=True)
        import numpy as np
        from faster_whisper import WhisperModel
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", clean, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
        m = WhisperModel(WHISPER, device="cpu", compute_type="int8")
        segs, _ = m.transcribe(np.frombuffer(raw, dtype=np.float32), language="es", word_timestamps=True, vad_filter=True,
                               vad_parameters=dict(min_silence_duration_ms=300))
        words = [{"w": w.word.strip(), "s": w.start, "e": w.end} for s in segs for w in (s.words or []) if w.word.strip()]
        json.dump(words, open(wj, "w"), ensure_ascii=False)
    words = json.load(open(wj))
    rngs = keep_ranges(words, dur_of(clean))
    with open(base + ".timeline.txt", "w") as f:
        f.write(f"Duración final: {sum(b-a for a,b in rngs):.2f}s · cortes en: {', '.join(f'{x:.2f}' for x in cut_points(rngs))}\n")
        for w in words: f.write(f"{remap(w['s'], rngs):6.2f}  {w['w']}\n")
    return clean, words, rngs

if __name__ == "__main__":
    prepare(sys.argv[1]); print(open(os.path.splitext(sys.argv[1])[0] + ".timeline.txt").read())
