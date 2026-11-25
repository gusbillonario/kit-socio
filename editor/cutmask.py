"""Paso 2 · corta silencios (select) y calcula la máscara de la persona.
Uso: python3 cutmask.py CRUDO [plan.json]  → CRUDO_work/cut.mov, mask.npy (10 fps, 270x480)
NOMASK=1 salta la máscara (más rápido; el texto "behind" queda delante de la persona)."""
import json, os, subprocess, sys, numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prep

U2NET = os.environ.get("U2NET", "/home/claude/models/u2net_human_seg.onnx")

def apply_remove(rngs, removes):
    for a, b in sorted(removes, reverse=True):
        out, acc = [], 0.0
        for s, e in rngs:
            ls, le = acc, acc + (e - s)
            if le <= a or ls >= b: out.append((s, e))
            else:
                if ls < a: out.append((s, s + (a - ls)))
                if le > b: out.append((s + (b - ls), e))
            acc = le
        rngs = out
    return rngs

src = sys.argv[1]; plan = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}
clean, words, rngs = prep.prepare(src)
rngs = apply_remove(rngs, plan.get("remove", []))
work = os.path.splitext(src)[0] + "_work"
json.dump(rngs, open(os.path.join(work, "rngs.json"), "w"))
cut = os.path.join(work, "cut.mov")
sel = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in rngs)
prep.run(["ffmpeg", "-y", "-i", clean, "-vf", f"select='{sel}',setpts=N/30/TB", "-af", f"aselect='{sel}',asetpts=N/SR/TB",
          "-c:v", "libx264", "-crf", "14", "-preset", "veryfast", "-c:a", "pcm_s16le", cut])
print("cut listo", flush=True)

MAXT = float(os.environ.get("MAXT", "1e9"))
if os.environ.get("NOMASK"):
    n = int(float(prep.dur_of(cut)) * 10) + 2
    np.save(os.path.join(work, "mask.npy"), np.zeros((n, 480, 270), np.float16)); print("mask listo (vacía)", n); sys.exit(0)
import onnxruntime as ort
sess = ort.InferenceSession(U2NET, providers=["CPUExecutionProvider"])
inp = sess.get_inputs()[0].name
p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", cut, "-vf", f"fps=10,scale=320:320,trim=0:{MAXT}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
masks = []
while True:
    b = p.stdout.read(320 * 320 * 3)
    if len(b) < 320 * 320 * 3: break
    x = np.frombuffer(b, np.uint8).reshape(320, 320, 3).astype(np.float32) / 255
    x = ((x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]).transpose(2, 0, 1)[None].astype(np.float32)
    m = sess.run(None, {inp: x})[0][0, 0]
    m = (m - m.min()) / (m.max() - m.min() + 1e-6)
    masks.append(cv2.resize(m, (270, 480), interpolation=cv2.INTER_LINEAR).astype(np.float16))
    if len(masks) % 30 == 0: print("máscaras:", len(masks), flush=True)
np.save(os.path.join(work, "mask.npy"), np.stack(masks))
print("mask listo", len(masks), flush=True)
