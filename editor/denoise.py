"""Limpia ruido de fondo: perfil tomado de las pausas reales (no del silencio digital)."""
import sys, numpy as np, noisereduce as nr
from scipy.io import wavfile
sr, x = wavfile.read(sys.argv[1]); x = x.astype(np.float32) / 32768
w = int(sr * 0.25)
segs = [(i, np.sqrt(np.mean(x[i:i+w]**2)) + 1e-12) for i in range(0, len(x) - w, w)]
segs = [(i, r) for i, r in segs if 20 * np.log10(r) > -85]           # fuera silencio digital
segs.sort(key=lambda s: s[1])
quiet = np.concatenate([x[i:i+w] for i, _ in segs[:max(4, len(segs) // 12)]])  # ~8% más silencioso
y = nr.reduce_noise(y=x, sr=sr, y_noise=quiet, stationary=True, prop_decrease=0.92, n_fft=2048)
wavfile.write(sys.argv[2], sr, (np.clip(y, -1, 1) * 32767).astype(np.int16))
nf = 20 * np.log10(np.sqrt(np.mean(quiet**2)))
print(f"perfil de ruido: {len(quiet)/sr:.1f}s a {nf:.1f} dB")
