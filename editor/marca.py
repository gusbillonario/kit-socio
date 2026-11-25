"""Identidad visual del socio. Lee marca.json (junto a este archivo o en la ruta de la variable MARCA).
Todos los scripts del editor toman de aquí el color de acento y el @usuario."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
MDIR = "/usr/share/fonts/opentype/montserrat/"
DEFAULT = {"nombre": "Tu nombre", "handle": "@tu_usuario", "acento": "#FF5A1F", "fondo": "#0F0F0F",
           "fuente_fuerte": MDIR + "Montserrat-Black.otf",      # titulares y texto gigante
           "fuente_texto": MDIR + "Montserrat-Bold.otf",        # letras cinéticas normales
           "fuente_elegante": "/usr/share/fonts/truetype/extra/InstrumentSerif-Italic.ttf",  # palabra destacada
           "familia_web": "Montserrat"}                         # portadas y frases

def _load():
    for p in [os.environ.get("MARCA", ""), os.path.join(HERE, "marca.json"), os.path.join(os.path.dirname(HERE), "marca.json")]:
        if p and os.path.exists(p):
            d = dict(DEFAULT); d.update(json.load(open(p, encoding="utf-8"))); return d
    return dict(DEFAULT)

M = _load()
NOMBRE, HANDLE = M["nombre"], M["handle"]
HEX = M["acento"].lstrip("#").upper()
RGB = tuple(int(HEX[i:i + 2], 16) for i in (0, 2, 4))
FONDO = M["fondo"]
F_FUERTE, F_TEXTO, F_ELEGANTE, FAMILIA_WEB = M["fuente_fuerte"], M["fuente_texto"], M["fuente_elegante"], M["familia_web"]
ASS = f"&H00{HEX[4:6]}{HEX[2:4]}{HEX[0:2]}&"        # color en formato de subtítulos ASS (&H00BBGGRR&)
ASS_SHORT = f"&H{HEX[4:6]}{HEX[2:4]}{HEX[0:2]}&"     # versión corta para etiquetas \1c
FF = "0x" + HEX                                        # color para ffmpeg
CSS = "#" + HEX
NORM = tuple(round(c / 255, 3) for c in RGB)          # 0-1 para mezclas de luz

def rgba(a):
    return f"rgba({RGB[0]},{RGB[1]},{RGB[2]},{a})"

def resolve(col):
    """En los planes, "col": "acento" usa el color de la marca."""
    return RGB if col in (None, "acento") else tuple(col)
