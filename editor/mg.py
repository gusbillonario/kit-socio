"""Motion graphics en ASS (libass) · Kit Socio (color de acento desde marca.json).
Cada función devuelve (líneas_ass, eventos_sfx, ventanas_sin_subtítulos)."""
import os, sys
from PIL import ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import marca

FB = "/usr/share/fonts/opentype/montserrat/Montserrat-ExtraBold.otf"
FK = "/usr/share/fonts/opentype/montserrat/Montserrat-Black.otf"
OR, WH, GR, DK, BK = marca.ASS_SHORT, "&HFFFFFF&", "&HA0A0A0&", "&H141414&", "&H000000&"

def tw(text, size, black=False):
    return ImageFont.truetype(FK if black else FB, size).getlength(text) * 0.71 * 1.04  # tamaño ASS ≈ 0.71 em · ScaleX 104

def ts(t):
    t = max(0, t); return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"

def rrect(w, h, r=22):
    w, h = int(w), int(h)
    return (f"m {r} 0 l {w-r} 0 b {w} 0 {w} 0 {w} {r} l {w} {h-r} b {w} {h} {w} {h} {w-r} {h} "
            f"l {r} {h} b 0 {h} 0 {h} 0 {h-r} l 0 {r} b 0 0 0 0 {r} 0")

ICON = {  # dibujos en caja de 60x60
    "check": "m 4 32 l 22 50 l 56 12 l 48 4 l 22 34 l 12 24",
    "x": "m 8 0 l 30 22 l 52 0 l 60 8 l 38 30 l 60 52 l 52 60 l 30 38 l 8 60 l 0 52 l 22 30 l 0 8",
    "up": "m 0 52 l 18 30 l 30 40 l 48 16 l 40 10 l 60 2 l 58 22 l 52 16 l 30 46 l 18 36 l 6 60",
    "mic": "m 20 0 l 40 0 b 46 0 46 0 46 6 l 46 30 b 46 38 46 38 40 38 l 20 38 b 14 38 14 38 14 30 l 14 6 b 14 0 14 0 20 0 m 6 26 l 10 26 b 10 42 18 46 30 46 b 42 46 50 42 50 26 l 54 26 b 54 46 44 50 32 50 l 32 58 l 42 58 l 42 62 l 18 62 l 18 58 l 28 58 l 28 50 b 16 50 6 46 6 26",
    "star": "m 30 0 l 37 21 l 60 22 l 42 36 l 49 58 l 30 45 l 11 58 l 18 36 l 0 22 l 23 21",
}

def D(layer, t0, t1, tags, body):
    return f"Dialogue: {layer},{ts(t0)},{ts(t1)},G,,0,0,0,,{{{tags}}}{body}"

def card(t0, t1, text, icon="check", y=300, x=None, icon_color=OR, size=66):
    """Tarjeta oscura con acento de color, entra deslizando desde la izquierda."""
    if tw(text, size) + 150 > 1000: size = int(size * 850 / tw(text, size))
    w_text = tw(text, size); w = w_text + 150; h = 118
    x = int((1080 - w) / 2) if x is None else x
    sl = 220
    mv = lambda dx, dy: f"\\move({x+dx-260},{y+dy},{x+dx},{y+dy},0,{sl})"
    fade = "\\fad(90,160)"
    L = [
        D(10, t0, t1, f"\\an7{mv(-6,10)}\\bord0\\shad0\\1c{BK}\\1a&H50&\\blur20{fade}\\p1", rrect(w+12, h+12, 30)),
        D(11, t0, t1, f"\\an7{mv(0,0)}\\bord0\\shad0\\1c{DK}\\1a&H18&{fade}\\p1", rrect(w, h, 26)),
        D(12, t0, t1, f"\\an7{mv(0,0)}\\bord0\\shad0\\1c{OR}{fade}\\p1", rrect(12, h, 6)),
        D(13, t0 + 0.12, t1, f"\\an7{mv(40,29)}\\bord0\\shad0\\1c{icon_color}\\fscx0\\fscy0\\t(0,160,\\fscx100\\fscy100){fade}\\p1", ICON[icon]),
        D(13, t0, t1, f"\\an4{mv(124, h//2)}\\fn Montserrat ExtraBold\\fs{size}\\fscx104\\bord0\\shad0\\1c{WH}{fade}", text),
    ]
    return L, [("whoosh", t0 - 0.12, 0.4), ("pop", t0 + 0.14, 0.6)], [(t0, t0 + 1.0)]

def stack(rows, times, t_end, y0=1110, gap=128, size=62, icon="check"):
    """Lista que se va construyendo, fila por fila, en la zona de subtítulos."""
    L, S = [], []
    for i, (txt, t) in enumerate(zip(rows, times)):
        x0 = int((1080 - (max(tw(r, size) for r in rows) + 150)) / 2)
        l, s, _ = card(t, t_end, txt, icon, y=y0 + i * gap, x=x0, size=size, icon_color=(GR if icon == "x" else OR))
        L += l; S += [("pop", t + 0.12, 0.65)]
    return L, S, [(times[0] - 0.05, t_end)]

def versus(t1, t2, t_end, left, right, y=250, size=60):
    """Comparativo: izquierda tachada (gris), derecha confirmada (color de acento)."""
    L, S = [], []
    bw, bh = 470, 190
    for k, (t, txt, side, col, ic) in enumerate([(t1, left, 50, GR, "x"), (t2, right, 560, OR, "check")]):
        fade = "\\fad(80,160)"
        pop = "\\fscx70\\fscy70\\t(0,180,\\fscx104\\fscy104)\\t(180,260,\\fscx100\\fscy100)"
        L.append(D(10, t, t_end, f"\\an7\\pos({side-6},{y+10})\\bord0\\shad0\\1c{BK}\\1a&H50&\\blur20{fade}\\p1", rrect(bw+12, bh+12, 30)))
        L.append(D(11, t, t_end, f"\\an7\\pos({side},{y})\\bord0\\shad0\\1c{DK}\\1a&H18&{fade}\\p1", rrect(bw, bh, 26)))
        L.append(D(12, t, t_end, f"\\an7\\pos({side},{y+bh-12})\\bord0\\shad0\\1c{col}{fade}\\p1", rrect(bw, 12, 6)))
        L.append(D(13, t + 0.1, t_end, f"\\an5\\pos({side+bw//2},{y+62})\\bord0\\shad0\\1c{col}{pop}{fade}\\p1", ICON[ic]))
        st = "\\s1" if ic == "x" else ""
        L.append(D(13, t, t_end, f"\\an5\\pos({side+bw//2},{y+132})\\fn Montserrat Black\\fs{size}\\fscx104\\bord0\\shad0\\1c{WH if ic=='check' else GR}{st}{pop}{fade}", txt))
        S += [("whoosh", t - 0.12, 0.4), ("pop" if ic == "check" else "click", t + 0.12, 0.7)]
    L.append(D(14, t1 + 0.05, t_end, f"\\an5\\pos(540,{y+bh//2})\\fn Montserrat Black\\fs54\\bord0\\shad0\\1c{OR}\\fad(80,160)", "VS"))
    return L, S, []

def lower_third(t0, t1, name, role, x=60, y=860):
    w = max(tw(name, 70, True), tw(role, 42)) + 170; h = 178
    sl = "\\move({},{},{},{},0,240)"
    mv = lambda dx, dy: sl.format(x + dx - 300, y + dy, x + dx, y + dy)
    fade = "\\fad(100,180)"
    L = [
        D(10, t0, t1, f"\\an7{mv(-6,10)}\\bord0\\shad0\\1c{BK}\\1a&H50&\\blur20{fade}\\p1", rrect(w+12, h+12, 30)),
        D(11, t0, t1, f"\\an7{mv(0,0)}\\bord0\\shad0\\1c{DK}\\1a&H18&{fade}\\p1", rrect(w, h, 26)),
        D(12, t0, t1, f"\\an7{mv(0,0)}\\bord0\\shad0\\1c{OR}{fade}\\p1", rrect(12, h, 6)),
        D(13, t0 + 0.12, t1, f"\\an7{mv(38,52)}\\bord0\\shad0\\1c{OR}\\fscx110\\fscy110{fade}\\p1", ICON["mic"]),
        D(13, t0, t1, f"\\an7{mv(132,26)}\\fn Montserrat Black\\fs70\\fscx104\\bord0\\shad0\\1c{WH}{fade}", name),
        D(13, t0 + 0.1, t1, f"\\an7{mv(134,104)}\\fn Montserrat ExtraBold\\fs42\\bord0\\shad0\\1c{GR}{fade}", role),
    ]
    return L, [("whoosh", t0 - 0.1, 0.45)], []

def stamp(t0, t1, text, y=960, rot=-7):
    w = tw(text, 78, True) * 1.04 + 110; h = 124
    anim = f"\\frz{rot}\\fscx220\\fscy220\\t(0,140,\\fscx100\\fscy100)\\fad(0,180)"
    L = [
        D(19, t0, t1, f"\\an5\\pos(540,{y+h//2+8})\\bord0\\shad0\\1c{BK}\\1a&H60&\\blur18{anim}\\p1", rrect(w, h, 16)),
        D(20, t0, t1, f"\\an5\\pos(540,{y+h//2})\\bord6\\3c{OR}\\shad0\\1a&HFF&{anim}\\p1", rrect(w, h, 16)),
        D(21, t0, t1, f"\\an5\\pos(540,{y+h//2})\\fn Montserrat Black\\fs78\\bord0\\shad0\\1c{OR}{anim.replace('t(0,140,\\fscx100','t(0,140,\\fscx104')}", text),
    ]
    return L, [("impact", t0, 0.55)], []

def endcard(t0, t1, l1, l2, sub=None):
    L = [D(30, t0, t1, f"\\an7\\pos(0,0)\\bord0\\shad0\\1c{BK}\\1a&HFF&\\t(0,250,\\1a&H50&)\\p1", "m 0 0 l 1080 0 l 1080 1920 l 0 1920")]
    pop = "\\fscx160\\fscy160\\t(0,200,\\fscx98\\fscy98)\\t(200,280,\\fscx100\\fscy100)"
    fs = int(min(104, 104 * 940 / max(tw(l1, 104, True), tw(l2, 104, True))))
    L.append(D(31, t0, t1, f"\\an5\\pos(540,820)\\fn Montserrat Black\\fs{fs}\\fscx104\\bord0\\shad0\\1c{WH}{pop}", l1))
    L.append(D(31, t0 + 0.35, t1, f"\\an5\\pos(540,960)\\fn Montserrat Black\\fs{fs}\\fscx104\\bord0\\shad0\\1c{OR}{pop}", l2))
    w = tw(l2, fs, True)
    L.append(D(31, t0 + 0.5, t1, f"\\an7\\pos({int(540-w/2)},1030)\\bord0\\shad0\\1c{OR}\\fscx0\\t(0,300,\\fscx100)\\p1", rrect(w, 10, 5)))
    if sub:
        L.append(D(31, t0 + 0.8, t1, f"\\an5\\pos(540,1140)\\fn Montserrat ExtraBold\\fs44\\fscx104\\bord0\\shad0\\1c{GR}\\fad(200,0)", sub))
    return L, [("riser", t0 - 0.9, 0.5), ("impact", t0, 0.8)], [(t0, t1)]

def build(plan):
    L, S, W = [], [], []
    for m in plan.get("mg", []):
        k = m["type"]
        if k == "card": r = card(m["t"], m["t"] + m.get("d", 1.6), m["text"], m.get("icon", "check"), m.get("y", 300))
        elif k == "stack": r = stack(m["rows"], m["times"], m["end"], m.get("y", 1110), icon=m.get("icon", "check"))
        elif k == "versus": r = versus(m["t1"], m["t2"], m["end"], m["left"], m["right"], m.get("y", 250))
        elif k == "lower": r = lower_third(m["t"], m["t"] + m.get("d", 2.2), m["name"], m["role"])
        elif k == "stamp": r = stamp(m["t"], m["t"] + m.get("d", 1.2), m["text"], m.get("y", 960))
        elif k == "end": r = endcard(m["t"], m["end"], m["l1"], m["l2"], m.get("sub"))
        else: continue
        L += r[0]; S += r[1]; W += r[2]
    return L, S, W
