"""Frase con foto real · 1080x1350 · color y @usuario desde marca.json
Uso: python3 frase.py "Texto con *palabra en color*" foto.jpg salida.png [pos_y% de la foto] [margen_sup_px]"""
import sys, base64, asyncio, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import marca
from playwright.async_api import async_playwright
txt, foto, out = sys.argv[1], sys.argv[2], sys.argv[3]
py = sys.argv[4] if len(sys.argv) > 4 else "30%"; top = sys.argv[5] if len(sys.argv) > 5 else "0"
mime = "jpeg" if foto.lower().endswith(("jpg", "jpeg")) else "png"
b64 = base64.b64encode(open(foto, "rb").read()).decode()
txt = re.sub(r"\*(.+?)\*", r'<span class="o">\1</span>', txt).replace("\n", "<br>")
A = marca.CSS
html = f"""<html><head><meta charset="utf-8"><style>*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1080px;height:1350px;font-family:'{marca.FAMILIA_WEB}',Montserrat,sans-serif;overflow:hidden;position:relative;background:{marca.FONDO}}}
.ph{{position:absolute;left:0;right:0;bottom:0;top:{top}px;background:url(data:image/{mime};base64,{b64}) center {py}/cover no-repeat;filter:brightness(.95) saturate(.92)}}
.fade{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(10,10,10,1) 0%,rgba(10,10,10,.95) 22%,rgba(10,10,10,.2) 42%,rgba(10,10,10,0) 60%,rgba(10,10,10,.55) 100%)}}
.bar{{position:absolute;top:0;left:0;right:0;height:12px;background:{A}}}
.t{{position:absolute;left:80px;right:80px;top:110px;font-size:64px;line-height:1.16;font-weight:800;color:#F4F4F4;letter-spacing:-.01em;text-shadow:0 6px 28px rgba(0,0,0,.55)}}
.o{{color:{A}}}
.h{{position:absolute;left:80px;bottom:60px;font-size:28px;font-weight:700;color:#F4F4F4;text-shadow:0 2px 12px rgba(0,0,0,.7)}}
</style></head><body><div class="ph"></div><div class="fade"></div><div class="bar"></div><div class="t">{txt}</div><div class="h">{marca.HANDLE}</div></body></html>"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 1080, "height": 1350})
        await pg.set_content(html); await pg.wait_for_timeout(300); await pg.screenshot(path=out); await b.close()
asyncio.run(main()); print("ok", out)
