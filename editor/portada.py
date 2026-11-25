"""Portada de carrusel con la foto real del socio · 1080x1350 · color y @usuario desde marca.json
Uso: python3 portada.py "LÍNEA 1|LÍNEA 2 EN COLOR|LÍNEA 3" "kicker" salida.png foto.jpg"""
import sys, base64, asyncio, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import marca
from playwright.async_api import async_playwright
lines, kicker, out, foto = sys.argv[1].split("|"), sys.argv[2], sys.argv[3], sys.argv[4]
mime = "jpeg" if foto.lower().endswith(("jpg", "jpeg")) else "png"
b64 = base64.b64encode(open(foto, "rb").read()).decode()
A, BG = marca.CSS, marca.FONDO
h = "".join(f'<div class="l {"o" if i == 1 else ""}">{t}</div>' for i, t in enumerate(lines))
html = f"""<html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1080px;height:1350px;background:{BG};font-family:'{marca.FAMILIA_WEB}',Montserrat,sans-serif;overflow:hidden;position:relative}}
.ph{{position:absolute;right:-170px;bottom:-40px;height:1420px;filter:brightness(.92) contrast(1.06) saturate(.9)}}
.fade{{position:absolute;inset:0;background:linear-gradient(90deg,{BG} 30%,rgba(15,15,15,.75) 50%,rgba(15,15,15,0) 72%),
 linear-gradient(0deg,{BG} 0%,rgba(15,15,15,0) 30%),linear-gradient(180deg,{BG} 0%,rgba(15,15,15,0) 22%),radial-gradient(circle at 75% 35%,{marca.rgba(.10)},rgba(0,0,0,0) 45%)}}
.bar{{position:absolute;left:0;top:0;width:100%;height:12px;background:{A}}}
.txt{{position:absolute;left:72px;top:250px;width:600px}}
.k{{font-size:28px;letter-spacing:.18em;font-weight:700;color:{A};margin-bottom:34px;text-transform:uppercase}}
.l{{font-size:76px;line-height:1.02;font-weight:900;color:#F4F4F4;letter-spacing:-.01em;text-shadow:0 8px 30px rgba(0,0,0,.6)}}
.l.o{{color:{A}}}
.sw{{position:absolute;left:72px;bottom:120px;display:flex;gap:18px;align-items:center;font-size:30px;font-weight:700;color:#F4F4F4}}
.sw span{{background:{A};color:#111;border-radius:40px;padding:14px 30px}}
.h{{position:absolute;left:72px;bottom:60px;font-size:24px;font-weight:600;color:#8A847F}}
</style></head><body>
<img class="ph" src="data:image/{mime};base64,{b64}"><div class="fade"></div><div class="bar"></div>
<div class="txt"><div class="k">{kicker}</div>{h}</div>
<div class="sw"><span>Desliza →</span></div><div class="h">{marca.HANDLE}</div>
</body></html>"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 1080, "height": 1350})
        await pg.set_content(html); await pg.wait_for_timeout(300); await pg.screenshot(path=out); await b.close()
asyncio.run(main()); print("ok", out)
