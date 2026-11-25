#!/usr/bin/env python3
"""Editor de reels · estilo "CINE" (v4) · versión Kit Socio (color y @usuario desde marca.json)

bg_mode "real": se conserva el fondo real (sin oscurecer ni desenfocar); el texto grande va DETRÁS
de la persona gracias a la máscara. Sin bg_mode: fondo oscurecido con luz del color de la marca.
Uso (después de prep.py y cutmask.py):
  python3 cine.py CRUDO plan.json SALIDA.mp4 [--frames t1,t2,...]
En los planes, "col": "acento" usa el color de la marca.
"""
import json, math, os, subprocess, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import marca

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
W, H, FPS = 1080, 1920, 30
OR = marca.RGB; WH = (246, 244, 241); GR = (150, 150, 150); DK = (17, 17, 17)
ACC = np.float32(marca.NORM)
MDIR = "/usr/share/fonts/opentype/montserrat/"
MB = marca.F_TEXTO
MK = marca.F_FUERTE
MS = MDIR + "Montserrat-SemiBold.otf"
SI = marca.F_ELEGANTE
EMO = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

STY = {
    "s": dict(f=MB, size=64, col=WH, lh=82),
    "S": dict(f=MK, size=112, col=WH, lh=120),
    "i": dict(f=SI, size=150, col=OR, lh=128),
    "g": dict(f=MB, size=64, col=GR, lh=82, strike=True),
    "p": dict(f=MK, size=62, col=DK, lh=100, pill=OR),
    "P": dict(f=MK, size=96, col=DK, lh=150, pill=OR),
}

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_out(p): return 1 - (1 - p) ** 3
def back_out(p, k=1.7):
    p -= 1; return 1 + p * p * ((k + 1) * p + k)

class Sprite:
    def __init__(self, rgba, ax, ay):
        a = rgba[..., 3:4].astype(np.float32) / 255
        self.rgb = rgba[..., :3].astype(np.float32) / 255 * a
        self.a = a; self.ax, self.ay = ax, ay
        self.h, self.w = a.shape[:2]

    def transformed(self, scale=1.0, rot=0.0):
        if abs(scale - 1) < 1e-3 and abs(rot) < 1e-3: return self.rgb, self.a, self.ax, self.ay
        M = cv2.getRotationMatrix2D((self.ax, self.ay), rot, scale)
        corners = np.array([[0, 0, 1], [self.w, 0, 1], [0, self.h, 1], [self.w, self.h, 1]], np.float32) @ M.T
        x0, y0 = corners.min(0); x1, y1 = corners.max(0)
        M[0, 2] -= x0; M[1, 2] -= y0
        ow, oh = int(math.ceil(x1 - x0)) + 1, int(math.ceil(y1 - y0)) + 1
        rgb = cv2.warpAffine(self.rgb, M, (ow, oh), flags=cv2.INTER_LINEAR, borderValue=0)
        a = cv2.warpAffine(self.a, M, (ow, oh), flags=cv2.INTER_LINEAR, borderValue=0)[..., None]
        return rgb, a, self.ax - x0, self.ay - y0

def blit(img, spr, x, y, alpha=1.0, scale=1.0, rot=0.0):
    if alpha <= 0.002: return
    rgb, a, ax, ay = spr.transformed(scale, rot)
    x0, y0 = int(round(x - ax)), int(round(y - ay))
    h, w = a.shape[:2]
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0 = max(0, x0), max(0, y0)
    dx1, dy1 = min(W, x0 + w), min(H, y0 + h)
    if dx1 <= dx0 or dy1 <= dy0: return
    sx1, sy1 = sx0 + (dx1 - dx0), sy0 + (dy1 - dy0)
    reg = img[dy0:dy1, dx0:dx1]
    aa = a[sy0:sy1, sx0:sx1] * alpha
    reg *= (1 - aa); reg += rgb[sy0:sy1, sx0:sx1] * alpha

def _shadow(im, radius=14, opacity=0.6, off=(0, 6)):
    a = im.split()[3]
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sa = a.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: int(v * opacity))
    sh.putalpha(sa); sh = sh.transform(im.size, Image.AFFINE, (1, 0, -off[0], 0, 1, -off[1]))
    sh.alpha_composite(im); return sh

def text_sprite(text, font, size, col, strike=False, pill=None, shadow=True, stroke=0, stroke_col=None):
    f = ImageFont.truetype(font, size)
    x0, y0, x1, y1 = f.getbbox(text, anchor="ls")
    pad = 60 if shadow else 20
    px, py = (int(size * 0.36), int(size * 0.24)) if pill else (0, 0)
    w, h = x1 - x0 + 2 * pad + 2 * px, y1 - y0 + 2 * pad + 2 * py
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ox, oy = pad + px - x0, pad + py - y0
    if pill:
        d.rounded_rectangle([pad, pad, w - pad, h - pad], radius=int(size * 0.28), fill=pill + (255,))
    d.text((ox, oy), text, font=f, fill=col + (255,), anchor="ls", stroke_width=stroke, stroke_fill=(stroke_col or col) + (255,))
    if strike:
        ys = oy - int(size * 0.32); t = max(5, int(size * 0.09))
        d.rectangle([ox - 6, ys - t // 2, ox + (x1) + 6, ys + t // 2], fill=OR + (255,))
    if shadow: im = _shadow(im, radius=max(10, size // 7), opacity=0.9)
    return Sprite(np.array(im), ox, oy), f.getlength(text)

def emoji_sprite(ch, size=180, outline=10):
    f = ImageFont.truetype(EMO, 109)
    im = Image.new("RGBA", (220, 220), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((20, 20), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox()); k = size / max(im.size)
    im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    pad = outline + 40
    canvas = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    canvas.alpha_composite(im, (pad, pad))
    a = np.array(canvas.split()[3])
    dil = cv2.dilate((a > 40).astype(np.uint8) * 255, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * outline + 1, 2 * outline + 1)))
    dil = cv2.GaussianBlur(dil, (0, 0), 1.2)
    white = Image.new("RGBA", canvas.size, (255, 255, 255, 0)); white.putalpha(Image.fromarray(dil))
    white.alpha_composite(canvas); out = _shadow(white, radius=16, opacity=0.55, off=(0, 10))
    return Sprite(np.array(out), out.width / 2, out.height / 2)

def stamp_sprite(text, size=92):
    f = ImageFont.truetype(MK, size)
    x0, y0, x1, y1 = f.getbbox(text, anchor="ls")
    px, py, pad = 46, 30, 50
    w, h = x1 - x0 + 2 * (px + pad), y1 - y0 + 2 * (py + pad)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([pad, pad, w - pad, h - pad], radius=20, fill=(14, 14, 14, 190), outline=OR + (255,), width=8)
    d.text((pad + px - x0, pad + py - y0), text, font=f, fill=OR + (255,), anchor="ls")
    im = _shadow(im, 18, 0.6, (0, 10))
    return Sprite(np.array(im), w / 2, h / 2)

def chip_sprite(text):
    f = ImageFont.truetype(MB, 36)
    x0, y0, x1, y1 = f.getbbox(text, anchor="ls")
    pad, px, py = 30, 26, 16
    w, h = x1 - x0 + 2 * (px + pad) + 30, y1 - y0 + 2 * (py + pad)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([pad, pad, w - pad, h - pad], radius=(h - 2 * pad) // 2, fill=(14, 14, 14, 170), outline=(255, 255, 255, 60), width=2)
    cy = h // 2; d.ellipse([pad + px - 4, cy - 8, pad + px + 12, cy + 8], fill=OR + (255,))
    d.text((pad + px + 30 - x0, pad + py - y0), text, font=f, fill=WH + (255,), anchor="ls")
    return Sprite(np.array(_shadow(im, 12, 0.4)), pad, pad)

class Scene:
    def __init__(self, plan, total):
        self.plan, self.total = plan, total
        self.items_back, self.items_front, self.sfx = [], [], []
        X0 = plan.get("kx", 80); Y0 = plan.get("ky", 1110)
        for b in plan.get("kinetic", []):
            y = b.get("y", Y0); x_base = b.get("x", X0); center = b.get("center", False)
            for line in b["lines"]:
                lh = max(STY[s]["lh"] for _, s, _ in line)
                segs = []
                for txt, st, ta in line:
                    c = STY[st]
                    spr, adv = text_sprite(txt, c["f"], c["size"], c["col"], c.get("strike", False), c.get("pill"))
                    segs.append([spr, adv, ta, st])
                gap = 20
                width = sum(s[1] for s in segs) + gap * (len(segs) - 1) + sum(STY[s[3]]["size"] * 0.72 for s in segs if STY[s[3]].get("pill"))
                k = 1.0
                if width > 920:
                    k = 920 / width; segs = []
                    for txt, st, ta in line:
                        c = STY[st]; spr, adv = text_sprite(txt, c["f"], int(c["size"] * k), c["col"], c.get("strike", False), c.get("pill"))
                        segs.append([spr, adv, ta, st])
                    width = sum(s[1] for s in segs) + gap * (len(segs) - 1); lh = int(lh * k)
                base = y + int(lh * 0.80)
                x = (W - width) / 2 if center else x_base
                for spr, adv, ta, st in segs:
                    pl = STY[st]["size"] * 0.36 * k if STY[st].get("pill") else 0
                    x += pl
                    self.items_front.append(dict(kind="kin", spr=spr, x=x, y=base, t0=ta, t1=b["end"]))
                    if st in ("i", "S", "p", "P"): self.sfx.append(("pop", ta + 0.02, 0.45))
                    else: self.sfx.append(("click", ta, 0.25))
                    x += adv + gap + pl
                y += lh
        for bt in plan.get("behind", []):
            fnt = {"MK": MK, "SI": SI, "MB": MB}[bt.get("font", "MK")]
            col = marca.resolve(bt["col"]) if "col" in bt else WH
            size = bt["size"]
            fw = ImageFont.truetype(fnt, size).getlength(bt["text"])
            if fw > bt.get("maxw", 1010): size = int(size * bt.get("maxw", 1010) / fw); bt["size"] = size
            spr, adv = text_sprite(bt["text"], fnt, size, col, shadow=bt.get("shadow", False))
            spr.ax += adv / 2; spr.ay -= bt["size"] * 0.36
            self.items_back.append(dict(kind="back", spr=spr, x=bt["x"], y=bt["y"], t0=bt["t0"], t1=bt["t1"], alpha=bt.get("alpha", 0.95)))
            self.sfx.append(("impact" if bt.get("impact", True) else "whoosh", bt["t0"], 0.45))
        for st in plan.get("stickers", []):
            spr = emoji_sprite(st["e"], st.get("size", 180))
            self.items_front.append(dict(kind="stk", spr=spr, x=st["x"], y=st["y"], t0=st["t0"], t1=st["t1"], rot=st.get("rot", -8)))
            self.sfx.append(("pop", st["t0"], 0.7))
        for sp in plan.get("stamps", []):
            self.items_front.append(dict(kind="stamp", spr=stamp_sprite(sp["text"]), x=540, y=sp.get("y", 960), t0=sp["t0"], t1=sp["t1"], rot=sp.get("rot", -6)))
            self.sfx += [("impact", sp["t0"], 0.6), ("glitch", sp["t0"], 0.5)]
        for ch in plan.get("chips", []):
            self.items_front.append(dict(kind="chip", spr=chip_sprite(ch["text"]), x=60, y=170, t0=ch["t0"], t1=ch["t1"]))
        self.dim = plan.get("dim", [])
        for g in plan.get("grid", []): self.sfx += [("whoosh", g - 0.15, 0.6), ("glitch", g, 0.35)]
        for p in plan.get("punches", []): self.sfx.append(("click", p, 0.35))
        self.sfx.append(("impact", 0.0, 0.9))
        if self.dim: self.sfx += [("riser", self.dim[0][0] - 0.9, 0.45), ("ding", self.dim[0][0] + 1.6, 0.5)]

    def draw(self, img, t, items):
        for it in items:
            if not (it["t0"] <= t < it["t1"]): continue
            d = t - it["t0"]; r = it["t1"] - t
            k = it["kind"]
            out = clamp(r / 0.16)
            if k == "kin":
                p = clamp(d / 0.26); a = clamp(d / 0.08) * out
                blit(img, it["spr"], it["x"], it["y"] + (1 - ease_out(p)) * 26 - (1 - out) * 14, a, 0.6 + 0.4 * back_out(p) if p < 1 else 1.0)
            elif k == "back":
                p = clamp(d / 0.45); a = clamp(d / 0.12) * clamp(r / 0.2) * it["alpha"]
                sc = (1.25 - 0.25 * ease_out(p)) * (1 + 0.012 * d)
                blit(img, it["spr"], it["x"], it["y"], a, sc)
            elif k == "stk":
                p = clamp(d / 0.3); a = clamp(d / 0.06) * out
                sc = back_out(p, 2.4) if p < 1 else 1.0
                blit(img, it["spr"], it["x"], it["y"] + 8 * math.sin(d * 3.2), a, max(0.05, sc), it["rot"] + 4 * math.sin(d * 2.1))
            elif k == "stamp":
                p = clamp(d / 0.14); a = clamp(d / 0.04) * out
                blit(img, it["spr"], it["x"], it["y"], a, 2.2 - 1.2 * ease_out(p), it["rot"])
            elif k == "chip":
                p = clamp(d / 0.3); a = clamp(d / 0.15) * out
                blit(img, it["spr"], it["x"] - (1 - ease_out(p)) * 260, it["y"], a)

def make_lut(strength=1.0):
    x = np.arange(256) / 255.0
    s = 1 / (1 + np.exp(-(x - 0.5) * 6.2)); s = (s - s.min()) / (s.max() - s.min())
    s = 0.62 * s + 0.38 * x
    s = 0.03 + s * 0.94
    sh = np.clip(1 - x * 2.2, 0, 1); hi = np.clip((x - 0.45) * 1.8, 0, 1)
    r = s + 0.040 * hi - 0.012 * sh
    g = s + 0.010 * hi + 0.010 * sh
    b = s - 0.045 * hi + 0.040 * sh
    lut = np.stack([r, g, b], -1)
    lut = x[:, None] * (1 - strength) + lut * strength
    return (np.clip(lut, 0, 1) * 255).astype(np.uint8).reshape(256, 1, 3)

def radial(cx, cy, rx, ry):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    return np.clip(1 - d, 0, 1) ** 2

def render(src, plan, out, frames=None):
    work = os.path.splitext(src)[0] + "_work"
    cut = os.path.join(work, "cut.mov")
    masks = np.load(os.path.join(work, "mask.npy")).astype(np.float32)
    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", cut], capture_output=True, text=True).stdout)
    total = plan.get("total", total)
    sc = Scene(plan, total)
    real = plan.get("bg_mode") == "real"
    lut = make_lut(plan.get("lut", 0.6 if real else 1.0))
    glow_c = np.array(plan.get("glow_col", list(ACC)), np.float32)
    gx, gy = plan.get("glow_xy", [760, 560])
    glow = radial(gx, gy, 720, 820)[..., None] * glow_c * plan.get("glow", 0.42)
    cool = radial(120, 1700, 900, 900)[..., None] * np.array([0.10, 0.30, 0.36], np.float32) * 0.18
    bg_floor = glow + cool + np.array([0.020, 0.024, 0.030], np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    vd = np.sqrt(((xx - 540) / 760) ** 2 + ((yy - 900) / 1150) ** 2)
    vstr = plan.get("vignette", 0.30 if real else 0.55)
    vig = np.clip(1 - vstr * np.clip(vd - 0.45, 0, 1) ** 1.6, 0.35, 1)[..., None].astype(np.float32)
    key = (0.86 + 0.20 * (xx / W))[..., None].astype(np.float32)
    rim = (np.clip((xx - 600) / 480, 0, 1) ** 2)[..., None] * ACC * 0.10
    bg_k = plan.get("bg", 0.26)
    band = (1 - plan.get("band", 0.0 if real else 0.5) * np.clip((yy - 950) / 380, 0, 1) ** 1.2)[..., None].astype(np.float32)
    grids = plan.get("grid", []); punches = plan.get("punches", [])
    leaks = plan.get("leaks", []) + grids
    LEAK = radial(1020, 260, 900, 1300)[..., None] * (ACC * 0.7 + 0.3)

    def zoom_at(t):
        z = 1.0 + 0.14 * clamp(1 - t / 0.45) ** 2
        z += 0.035 * ((t % 7.0) / 7.0)
        for p in punches:
            if p <= t < p + 0.9: z += 0.07 * (1 - ease_out(clamp((t - p) / 0.9)))
        return z

    rd = subprocess.Popen(["ffmpeg", "-v", "error", "-i", cut, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = None
    if not frames:
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                                "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", out + ".video.mp4"], stdin=subprocess.PIPE)
    want = None if not frames else sorted(set(int(round(t * FPS)) for t in frames))
    n = 0; shots = []
    while True:
        b = rd.stdout.read(W * H * 3)
        if len(b) < W * H * 3: break
        fi = n; n += 1; t = fi / FPS
        if t >= total: break
        if want is not None and fi not in want:
            if fi > want[-1]: break
            continue
        f = np.frombuffer(b, np.uint8).reshape(H, W, 3).astype(np.float32) / 255
        k = min(t * 10, len(masks) - 1.001); i0 = int(k); fr = k - i0
        m = masks[i0] * (1 - fr) + masks[min(i0 + 1, len(masks) - 1)] * fr
        m = np.clip((m - 0.30) / 0.40, 0, 1); m = cv2.GaussianBlur(m, (0, 0), 1.6)
        m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
        if plan.get("sharpen", 0.35) > 0:
            bl = cv2.GaussianBlur(f, (0, 0), 1.2); f = np.clip(f + (f - bl) * plan.get("sharpen", 0.35), 0, 1)
        if real:
            bg = f.copy()
            sc.draw(bg, t, sc.items_back)
            img = bg * (1 - m) + f * m
        else:
            small = cv2.resize(f, (270, 480), interpolation=cv2.INTER_AREA)
            small = cv2.GaussianBlur(small, (0, 0), 3.0)
            bg = cv2.resize(small, (W, H), interpolation=cv2.INTER_LINEAR) * bg_k + bg_floor
            sc.draw(bg, t, sc.items_back)
            fg = f * key + rim * m
            img = bg * (1 - m) + fg * m
        z = zoom_at(t)
        if z > 1.0005:
            M = np.float32([[z, 0, (1 - z) * 540], [0, z, (1 - z) * 820]])
            img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        lum = img @ np.float32([0.2126, 0.7152, 0.0722])
        img = lum[..., None] + (img - lum[..., None]) * plan.get("sat", 0.95 if real else 0.88)
        img = np.clip(img * vig * band, 0, 1)
        u8 = cv2.LUT((img * 255).astype(np.uint8), lut)
        img = u8.astype(np.float32) / 255
        for g in grids:
            d = t - g
            if 0 <= d < 0.55:
                src_img = img.copy(); img[:] = 0.04
                tw, th = W // 3, H // 4
                for r in range(4):
                    for c in range(3):
                        p = ease_out(clamp((d - (r + c) * 0.035) / 0.30))
                        dx = int((1 - p) * 1150 * (1 if r % 2 else -1)); gap = int(8 * (1 - p))
                        x0, y0 = c * tw + gap, r * th + gap; x1, y1 = (c + 1) * tw - gap, (r + 1) * th - gap
                        X0, X1 = x0 + dx, x1 + dx
                        cx0, cx1 = max(0, X0), min(W, X1)
                        if cx1 > cx0: img[y0:y1, cx0:cx1] = src_img[y0:y1, cx0 - dx:cx1 - dx]
        for lk in leaks:
            d = t - lk
            if -0.05 <= d < 0.45:
                s = math.exp(-max(0, d) / 0.14) * 0.55
                img += LEAK * s
        if plan.get("scrim"):
            for blk in plan.get("kinetic", []):
                t0b = min(seg[2] for ln in blk["lines"] for seg in ln); y0b = blk.get("y", plan.get("ky", 1110))
                hb = sum(max(STY[s_]["lh"] for _, s_, _ in ln) for ln in blk["lines"])
                if t0b - 0.1 <= t < blk["end"]:
                    a_ = clamp((t - t0b + 0.1) / 0.2) * clamp((blk["end"] - t) / 0.15) * plan["scrim"]
                    prof = np.clip(1 - np.abs((yy[:, :1] - (y0b + hb / 2)) / (hb / 2 + 140)), 0, 1) ** 0.8
                    img *= (1 - a_ * prof[..., None])
        for a, b2 in sc.dim:
            if a <= t < b2: img *= 1 - 0.55 * clamp((t - a) / 0.25)
        sc.draw(img, t, sc.items_front)
        if not plan.get("no_bar"):
            img[H - 12:, :] *= 0.55
            img[H - 12:, : int(W * t / total)] = ACC
        o = (np.clip(img, 0, 1) * 255).astype(np.uint8)
        if frames: shots.append((t, o))
        else: enc.stdin.write(o.tobytes())
        if fi % 90 == 0: print(f"  {t:5.1f}s / {total:.1f}s", flush=True)
    rd.kill()
    if frames:
        for t, o in shots: cv2.imwrite(f"{out}_{t:05.2f}.jpg", cv2.cvtColor(o, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 85])
        return sc
    enc.stdin.close(); enc.wait()
    return sc

def mix_audio(src, plan, sc, out, total):
    work = os.path.splitext(src)[0] + "_work"; cut = os.path.join(work, "cut.mov")
    inputs = ["-i", out + ".video.mp4", "-i", cut]; fc = []; mix = ["[voice]"]; idx = 2
    fc.append("[1:a]highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=10:release=200,loudnorm=I=-14:TP=-1.5:LRA=9,aresample=48000,asplit=2[voice][key];")
    mood = plan.get("mood")
    if mood:
        inputs += ["-stream_loop", "-1", "-i", os.path.join(ASSETS, f"musica_{mood}.wav")]
        fc.append(f"[{idx}:a]atrim=0:{total:.3f},volume={plan.get('music_vol', 0.2)},afade=t=in:d=0.8,afade=t=out:st={max(0,total-1.5):.3f}:d=1.5[mraw];"
                  "[mraw][key]sidechaincompress=threshold=0.03:ratio=6:attack=30:release=350[mus];")
        mix.append("[mus]"); idx += 1
    else: fc.append("[key]anullsink;")
    for name, t, v in sc.sfx + [tuple(x) for x in plan.get("extra_sfx", [])]:
        inputs += ["-i", os.path.join(ASSETS, name + ".wav")]; ms = int(max(0, t) * 1000)
        fc.append(f"[{idx}:a]adelay={ms}|{ms},volume={v}[s{idx}];"); mix.append(f"[s{idx}]"); idx += 1
    fc.append("".join(mix) + f"amix=inputs={len(mix)}:duration=longest:normalize=0,alimiter=limit=0.95,atrim=0:{total:.3f},apad=whole_dur={total:.3f}[ao]")
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", "".join(fc), "-map", "0:v", "-map", "[ao]", "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{total:.3f}", out], capture_output=True, text=True)
    if r.returncode: print(r.stderr[-2000:]); raise SystemExit("falló el audio")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("plan"); ap.add_argument("out")
    ap.add_argument("--frames")
    a = ap.parse_args(); plan = json.load(open(a.plan))
    if a.frames:
        render(a.src, plan, a.out, frames=[float(x) for x in a.frames.split(",")])
    else:
        sc = render(a.src, plan, a.out)
        total = plan.get("total") or float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                 os.path.join(os.path.splitext(a.src)[0] + "_work", "cut.mov")], capture_output=True, text=True).stdout)
        mix_audio(a.src, plan, sc, a.out, total); os.remove(a.out + ".video.mp4"); print("Listo:", a.out)
