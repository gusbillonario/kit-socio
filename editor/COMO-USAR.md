# Editor del Kit Socio · guía técnica para Claude

(Este archivo es para Claude, no para el socio. El socio solo sube su video y escribe "edítalo".)

## Archivos
- marca.json → nombre, @usuario, color de acento y fondo del socio. TODOS los scripts toman de aquí el color. Si no existe, pídele al socio su color y su @ y créalo junto a los scripts.
- prep.py → normaliza (HDR del iPhone → SDR, 1080x1920, 30 fps), limpia ruido (denoise.py), transcribe y corta silencios > 0.4 s.
- edit_reel3.py + mg.py → estilos NATIVO y PRODUCIDO.
- cutmask.py + cine.py → estilo CINE (premium: letras cinéticas, texto gigante detrás de la persona).
- sfx.py → efectos y música sintetizados (sin derechos de autor).
- portada.py → portada de carrusel con foto real · frase.py → frase con foto real (1080x1350).
- plan_*_ejemplo.json → ejemplos de cada estilo.

## Preparar el entorno (una vez por sesión, ~3-5 min; hazlo tú sin pedirle nada al socio)
1. Copia todos los archivos de editor/ a /home/claude/reels y pon ahí el marca.json del socio (el de su proyecto o memoria, no el de ejemplo).
2. `pip install faster-whisper noisereduce onnxruntime opencv-python-headless scipy playwright --break-system-packages`
3. `apt-get install -y fonts-montserrat fonts-noto-color-emoji` (si falla: `apt-get update` primero).
4. Instrument Serif: `mkdir -p /usr/share/fonts/truetype/extra && curl -sSfL -o /usr/share/fonts/truetype/extra/InstrumentSerif-Italic.ttf https://raw.githubusercontent.com/google/fonts/main/ofl/instrumentserif/InstrumentSerif-Italic.ttf`
5. Modelo Whisper small en /home/claude/whisper-small (Hugging Face suele estar bloqueado): bajar de npm SIN ejecutar scripts los tarballs `@skillninja/shortmovie-telop-model-p0`, `-p1`, `-p2`, `-p3` versión 1.0.0 (`npm pack --ignore-scripts`), copiar config.json, preprocessor_config.json, tokenizer.json y vocabulary.json de p0 y unir `cat model.bin.part0 part1 part2 part3 > /home/claude/whisper-small/model.bin`. SHA256 esperado: ca732cb1379efc49417d028465f543d83a39de2c61f3027678de103dc404ce73
6. Solo para CINE: `mkdir -p /home/claude/models && curl -sSfL -o /home/claude/models/u2net_human_seg.onnx https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx`
7. `cd /home/claude/reels && python3 sfx.py assets`
8. Si playwright no encuentra navegador: `python3 -m playwright install chromium`.

## Flujo NATIVO / PRODUCIDO (rápido, 2-4 min)
1. `python3 edit_reel3.py CRUDO --prep` → imprime cada palabra con su tiempo final.
2. Escribe plan.json:
   - NATIVO (lo-fi, para videos en el carro, caminando, cocina): `"style": "nativo", "title": "LÍNEA 1|LÍNEA 2"`. Sin emojis en el título (no se ven).
   - PRODUCIDO: `hook` (2 líneas, la segunda sale con el color de la marca), `mood` (motivacional/tech/reflexivo/energia), `punches` (zooms en palabras clave), `mg`: card, stack (lista), versus, stamp (sello), lower (nombre + rol), end (cierre).
   - Siempre: `remove` [[a,b]] para quitar tropiezos; `fix` para corregir la transcripción ("palabra@2" corrige solo la 2.ª aparición; "" la borra).
3. `python3 edit_reel3.py CRUDO --plan plan.json --out FINAL.mp4`

## Flujo CINE (premium, 8-15 min)
1. `python3 prep.py CRUDO` → timeline.
2. `nohup python3 cutmask.py CRUDO plan.json > mask.log 2>&1 &` (~1 s por cada 0.1 s de video). Revisa mask.log hasta "mask listo". Sin prisa por la máscara: `NOMASK=1` la salta (el texto gigante queda delante de la persona).
3. Plan (ver plan_cine_ejemplo.json): `bg_mode: "real"` (fondo real, recomendado), `kinetic` (bloques de letras: s normal, S grande, i cursiva en color, g gris tachado, p/P pastilla de color), `behind` (texto gigante detrás; `"col": "acento"` = color de la marca), `stickers` (emoji), `stamps`, `chips` ("LECCIÓN 1/3"), `grid` (transición), `punches`, `dim` (cierre oscurecido), `mood`.
4. Prueba cuadros: `python3 cine.py CRUDO plan.json chk --frames 0.5,8,20` y míralos.
5. Render: `nohup python3 cine.py CRUDO plan.json FINAL.mp4 > r.log 2>&1 &` y revisa r.log hasta "Listo". No esperes con bucles largos: el shell corta comandos largos.

## Revisar antes de entregar
- Mira 3-4 cuadros del final y confirma con ffprobe que audio y video duran lo mismo.
- Si pesa > 30 MB: `ffmpeg -i FINAL.mp4 -c:v libx264 -crf 21 -maxrate 6M -bufsize 12M -c:a copy FINAL_ig.mp4`.
- Entrega con el archivo + caption listo para copiar.

## Fuentes del socio
- marca.json define `fuente_fuerte` (titulares y texto gigante), `fuente_texto` (letras cinéticas), `fuente_elegante` (palabra destacada) como rutas a archivos .ttf/.otf, y `familia_web` (portadas y frases).
- Para usar otra fuente de Google Fonts: `curl -sSfL -o /usr/share/fonts/truetype/extra/NOMBRE.ttf "https://raw.githubusercontent.com/google/fonts/main/ofl/<carpeta>/<archivo>.ttf"` (los corchetes del nombre van como %5B y %5D), `fc-cache -f`, y pon la ruta en marca.json. Las fuentes se pierden al cerrar la sesión: vuelve a bajarlas en cada sesión.
- Los estilos NATIVO y PRODUCIDO usan Montserrat siempre; CINE, portadas y frases usan las fuentes del socio.

## Crear un estilo propio del socio
El editor es una base, no un límite. Si las referencias de edición del socio piden algo que no existe (otro tipo de subtítulo, íconos flotantes, captura de pantalla flotante, título fijo con lista que se va llenando, etc.):
1. Escribe un script nuevo `estilo_<nombre>.py` (o amplía cine.py en una copia) usando marca.py para color y fuentes.
2. Prueba cuadros con un video real del socio y enséñaselos antes de renderizar completo.
3. Cuando lo apruebe, guarda el script como documento del proyecto y anótalo en MI-MARCA.md ("Estilos aprobados") con su descripción y un plan de ejemplo.
4. Nunca copies el look de Gustavo tal cual (naranja, mismas combinaciones): la base técnica se comparte, la identidad es del socio.

## Reglas visuales
- Solo fotos y videos reales del socio. Nunca generar su cara con IA. Nunca fotos de personas famosas (si se menciona a alguien, usar `lower` con nombre y rol).
- Sin dinero en stickers ni textos (nada de 💰 ni cifras de ingresos).
- Variedad: no repetir el mismo estilo dos reels seguidos.
