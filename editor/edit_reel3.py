#!/usr/bin/env python3
"""Editor de reels · estilos NATIVO y PRODUCIDO-v3 · Kit Socio (color de acento desde marca.json)

Paso 1 (preparar):  python3 edit_reel3.py CRUDO.MOV --prep
   -> convierte HDR, limpia ruido, transcribe, corta silencios y escribe CRUDO.timeline.txt
Paso 2 (render):    python3 edit_reel3.py CRUDO.MOV --plan plan.json --out FINAL.mp4

plan.json (ver plan_nativo_ejemplo.json y plan_producido_ejemplo.json):
  "style": "nativo" + "title": "LÍNEA 1|LÍNEA 2"  → caja blanca fija arriba, subtítulos sencillos (lo-fi)
  sin "style" → producido: "hook", "mood", "punches", "mg" (card, stack, versus, lower, stamp, end), "cta"
  "remove": [[a, b]] tramos a quitar (tiempo final) · "fix": {"palabra": "corrección", "palabra@2": "..."}
"""
import argparse, json, os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import marca
from prep import prepare, cut_points, remap

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
W, H = 1080, 1920
OR = marca.ASS; WH = "&H00FFFFFF&"; BK = "&H00000000&"
ORS = OR.rstrip("&")   # para las líneas Style
CAP_Y = 1180          # zona más vista y libre de la interfaz de Instagram
TOP_Y = 300           # hook y tarjetas

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write("\n".join(l for l in r.stderr.replace("\r", "\n").splitlines() if not l.startswith("frame="))[-3000:]); raise SystemExit("Falló: " + " ".join(cmd[:4]))
    return r.stdout

def ts(t):
    t = max(0, t); return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"

CHECK = r"{\p1}m 0 22 l 14 36 l 44 4 l 52 12 l 14 52 l -8 30{\p0}"

def build_ass(words, rngs, plan, total):
    kw = {k.lower() for k in plan.get("keywords", [])}
    fix = {k.lower(): v for k, v in plan.get("fix", {}).items()}
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Montserrat Black,94,&H00F4F4F4,&H00F4F4F4,&H00000000,&H00000000,0,0,0,0,104,100,1,0,1,2.5,0,5,90,90,0,1
Style: CapSh,Montserrat Black,94,&HFF000000,&HFF000000,&H50000000,&H00000000,0,0,0,0,104,100,1,0,1,16,0,5,90,90,0,1
Style: Nat,Montserrat SemiBold,60,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,0,0,0,0,100,100,0,0,1,0,3,5,90,90,0,1
Style: Title,Montserrat Bold,58,&H00111111,&H00111111,&H00FFFFFF,&H00FFFFFF,0,0,0,0,100,100,0,0,3,22,0,5,110,110,0,1
Style: G,Montserrat ExtraBold,60,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Hook,Montserrat Black,108,&H00F4F4F4,&H00F4F4F4,&H00000000,&H00000000,0,0,0,0,104,100,1,0,1,2.5,0,5,60,60,0,1
Style: HookSh,Montserrat Black,108,&HFF000000,&HFF000000,&H48000000,&H00000000,0,0,0,0,104,100,1,0,1,18,0,5,60,60,0,1
Style: HookBox,Montserrat Black,108,{ORS},{ORS},&H00141414,&H00141414,0,0,0,0,104,100,1,0,3,24,0,5,60,60,0,1
Style: Card,Montserrat Black,86,&H00111111,&H00111111,{ORS},{ORS},0,0,0,0,104,100,1,0,3,24,0,5,60,60,0,1
Style: Icon,Montserrat Black,10,&H00111111,&H00111111,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    hook = plan.get("hook")
    if plan.get("style") == "nativo":
        if plan.get("title"):
            tl = plan["title"].replace("|", "\\N")
            ev.append(f"Dialogue: 5,{ts(0)},{ts(total)},Title,,0,0,0,,{{\\pos(540,{TOP_Y})\\fad(150,0)}}{tl}")
        hook = None
    hold = (hook or {}).get("hold", 2.8)
    if hook:
        lines = hook["lines"]
        y0 = TOP_Y - 70 * (len(lines) - 1)
        for i, ln in enumerate(lines):
            style = "HookBox" if i == len(lines) - 1 else "Hook"
            st = i * 0.12
            anim = f"\\pos(540,{y0 + i*150})\\fscx150\\fscy150\\t(0,180,\\fscx98\\fscy98)\\t(180,260,\\fscx104\\fscy100)\\fad(0,180)"
            if style == "Hook": ev.append(f"Dialogue: 4,{ts(st)},{ts(hold)},HookSh,,0,0,0,,{{{anim}\\blur14}}{ln}")
            ev.append(f"Dialogue: 5,{ts(st)},{ts(hold)},{style},,0,0,0,,{{{anim}}}{ln}")
    # subtítulos
    nw = []; seen = {}
    for w in words:
        clean = re.sub(r"[^\wáéíóúñü]", "", w["w"].lower())
        seen[clean] = seen.get(clean, 0) + 1
        txt = fix.get(f"{clean}@{seen[clean]}", fix.get(clean, w["w"]))
        if txt == "": continue
        nw.append({"w": txt, "k": clean, "s": remap(w["s"], rngs), "e": remap(w["e"], rngs)})
    groups, cur = [], []
    for w in nw:
        cur.append(w)
        if len(cur) >= 3 or len(" ".join(x["w"] for x in cur)) >= 14 or re.search(r"[.,!?¿¡:;]$", w["w"]):
            groups.append(cur); cur = []
    if cur: groups.append(cur)
    import mg
    mgL, mgS, mgW = mg.build(plan)
    plan["_mgS"] = mgS
    card_win = [(c["t"], c["t"] + c.get("d", 1.6)) for c in plan.get("cards", [])] + mgW
    for gi, g in enumerate(groups):
        gend = groups[gi + 1][0]["s"] if gi + 1 < len(groups) else g[-1]["e"] + 0.35
        for i, w in enumerate(g):
            s = w["s"]; e = g[i + 1]["s"] if i + 1 < len(g) else gend
            if e <= s: e = s + 0.05
            if any(a - 0.05 <= s and e <= b + 0.6 for a, b in card_win):
                continue  # la tarjeta ya muestra esas palabras
            if plan.get("style") == "nativo":
                if i: continue  # un evento por grupo, sin palabra activa
                txt = " ".join(re.sub(r"[.,;:]$", "", x["w"]) for x in g)
                txt = txt[0].upper() + txt[1:]
                ev.append(f"Dialogue: 1,{ts(g[0]['s'])},{ts(gend)},Nat,,0,0,0,,{{\\pos(540,{CAP_Y+90})}}{txt}")
                continue
            parts = []
            for j, x in enumerate(g):
                word = re.sub(r"[.,;:]$", "", x["w"]).upper()
                if j == i:
                    parts.append(f"{{\\c{OR}\\fscx108\\fscy108\\t(0,90,\\fscx104\\fscy100)}}{word}{{\\c&H00F4F4F4&\\fscx104\\fscy100}}")
                else:
                    parts.append(word)
            intro = "\\fscx80\\fscy80\\t(0,80,\\fscx104\\fscy100)" if i == 0 else ""
            plain = " ".join(re.sub(r"[.,;:]$", "", x["w"]).upper() for x in g)
            ev.append(f"Dialogue: 0,{ts(s)},{ts(e)},CapSh,,0,0,0,,{{\\pos(540,{CAP_Y+6}){intro}\\blur18}}{plain}")
            ev.append(f"Dialogue: 1,{ts(s)},{ts(e)},Cap,,0,0,0,,{{\\pos(540,{CAP_Y}){intro}}}{' '.join(parts)}")
    for c in plan.get("cards", []):
        t0, t1 = c["t"], c["t"] + c.get("d", 1.6)
        ev.append(f"Dialogue: 4,{ts(t0)},{ts(t1)},Card,,0,0,0,,{{\\move(-200,{TOP_Y},540,{TOP_Y},0,200)\\fad(0,150)\\t(200,280,\\fscx110\\fscy110)\\t(280,360,\\fscx104\\fscy100)}}{c['text']}")
        if c.get("icon") == "check":
            ev.append(f"Dialogue: 6,{ts(t0+0.15)},{ts(t1)},Icon,,0,0,0,,{{\\an5\\pos(540,{TOP_Y-120})\\c{WH}\\3c{BK}\\bord4\\shad0\\fscx0\\fscy0\\t(0,160,\\fscx260\\fscy260)\\t(160,240,\\fscx220\\fscy220)\\fad(0,150)}}{CHECK}")
    cta = plan.get("cta")
    if cta:
        d = cta.get("d", 2.5); t0 = max(0, total - d)
        ev.append(f"Dialogue: 4,{ts(t0)},{ts(total)},Card,,0,0,0,,{{\\pos(540,{TOP_Y})\\fscx60\\fscy60\\t(0,200,\\fscx106\\fscy106)\\t(200,280,\\fscx100\\fscy100)}}{cta['text']}")
    return hdr + "\n".join(ev + mgL) + "\n"

def zoom_expr(plan, hold):
    if plan.get("style") == "nativo": return "1+" + plan.get("_alt", "0").replace("0.06*", "0.04*")
    terms = ["0.14*max(0,1-it/0.45)", plan.get("_alt", "0")]
    for p in plan.get("punches", []):
        terms.append(f"0.09*between(it,{p:.2f},{p+0.7:.2f})*(1-(it-{p:.2f})/0.7)")
    return "1+" + "+".join(terms)

def apply_remove(rngs, removes):
    """Quita tramos indicados en tiempo final (timeline) y devuelve nuevos rangos de la fuente."""
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

def render(src_std, words, rngs, plan, out):
    rngs = apply_remove(rngs, plan.get("remove", []))
    words = [w for w in words if any(a - 0.05 <= (w["s"] + w["e"]) / 2 <= b + 0.05 for a, b in rngs)]
    global TOP_Y
    TOP_Y = plan.get("top_y", TOP_Y)
    total = sum(b - a for a, b in rngs)
    hold = (plan.get("hook") or {}).get("hold", 2.8)
    tmp = tempfile.mkdtemp()
    ass = os.path.join(tmp, "s.ass"); open(ass, "w").write(build_ass(words, rngs, plan, total))
    cuts = cut_points(rngs)
    sel = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in rngs)
    cut = os.path.join(tmp, "cut.mov")
    run(["ffmpeg", "-y", "-i", src_std, "-vf", f"select='{sel}',setpts=N/30/TB", "-af", f"aselect='{sel}',asetpts=N/SR/TB",
         "-c:v", "libx264", "-crf", "14", "-preset", "veryfast", "-c:a", "pcm_s16le", cut])
    fc = ["[0:v]setsar=1[cv];[0:a]anull[ca];"]
    bounds = [0.0] + cuts + [total]
    alt = "+".join(f"0.06*between(it,{bounds[i]:.3f},{bounds[i+1]:.3f})" for i in range(1, len(bounds) - 1, 2)) or "0"
    plan["_alt"] = alt
    z = zoom_expr(plan, hold)
    shake = "0" if plan.get("style") == "nativo" else "if(lt(it,0.35),10*sin(it*90),0)"
    fc.append(f"[cv]zoompan=z='{z}':x='iw/2-(iw/zoom/2)+{shake}':y='ih*0.42-(ih/zoom*0.42)':d=1:s=1080x1920:fps=30,"
              f"eq=brightness=0.03:contrast=1.05:saturation=1.10,")
    flashes = "".join(f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.55:t=fill:enable='between(t,{c:.2f},{c+0.07:.2f})'," for c in cuts)
    flashes += "drawbox=x=0:y=0:w=iw:h=ih:color=white@0.7:t=fill:enable='between(t,0,0.06)',"
    if plan.get("style") == "nativo": flashes = ""
    ass_esc = ass.replace(":", "\\:")
    fc.append(flashes + f"ass='{ass_esc}',drawbox=x=0:y=ih-14:w=iw:h=14:color=black@0.35:t=fill,"
              f"drawbox=x=0:y=ih-14:w='iw*t/{total:.3f}':h=14:color={marca.FF}:t=fill[vo];")
    fc.append("[ca]highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=10:release=200,loudnorm=I=-14:TP=-1.5:LRA=9,aresample=48000,asplit=2[voice][key];")
    inputs = ["-i", cut]; idx = 1; mix = ["[voice]"]
    mood = plan.get("mood")
    if mood:
        inputs += ["-stream_loop", "-1", "-i", os.path.join(ASSETS, f"musica_{mood}.wav")]
        vol = plan.get("music_vol", 0.22)
        fc.append(f"[{idx}:a]atrim=0:{total:.3f},volume={vol},afade=t=in:d=0.8,afade=t=out:st={max(0,total-1.5):.3f}:d=1.5[mraw];"
                  f"[mraw][key]sidechaincompress=threshold=0.03:ratio=6:attack=30:release=350[mus];")
        mix.append("[mus]"); idx += 1
    else:
        fc.append("[key]anullsink;")
    events = []
    if plan.get("hook") and plan.get("style") != "nativo": events += [("impact", 0.0, 0.9), ("whoosh", hold - 0.2, 0.5)]
    for c in plan.get("cards", []): events += [("whoosh", c["t"] - 0.15, 0.45), ("pop", c["t"] + 0.2, 0.7)]
    for p in plan.get("punches", []): events += [("click", p, 0.5)]
    events += plan.get("_mgS", [])
    if plan.get("style") != "nativo":
        for c in cuts: events += [("whoosh", c - 0.2, 0.35)]
    if plan.get("cta"): events += [("ding", max(0, total - plan["cta"].get("d", 2.5)), 0.6)]
    for name, t, v in events:
        inputs += ["-i", os.path.join(ASSETS, name + ".wav")]
        ms = int(max(0, t) * 1000)
        fc.append(f"[{idx}:a]adelay={ms}|{ms},volume={v}[s{idx}];"); mix.append(f"[s{idx}]"); idx += 1
    fc.append("".join(mix) + f"amix=inputs={len(mix)}:duration=longest:normalize=0,alimiter=limit=0.95,atrim=0:{total:.3f},apad=whole_dur={total:.3f}[ao]")
    run(["ffmpeg", "-y", *inputs, "-filter_complex", "".join(fc), "-map", "[vo]", "-map", "[ao]",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{total:.3f}", out])
    print("Listo:", out)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("--prep", action="store_true")
    ap.add_argument("--plan"); ap.add_argument("--out")
    a = ap.parse_args()
    std, words, rngs = prepare(a.src)
    if a.prep:
        print(open(os.path.splitext(a.src)[0] + ".timeline.txt").read())
    else:
        render(std, words, rngs, json.load(open(a.plan)), a.out)
