"""Montador de vídeo: convierte un guion del Creador en un MP4 vertical 1080x1920 listo para TikTok.

Para cada escena busca en la carpeta de medios un archivo escenaN.(mp4|mov|jpg|jpeg|png).
- Si existe, lo usa de fondo (recortado a 9:16).
- Si no existe, genera una tarjeta con el plano que debes grabar (el vídeo sirve de storyboard).
Encima pone el texto en pantalla. Sin audio: el sonido en tendencia se añade dentro de TikTok.
"""
import re
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FUENTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FUENTE_NORMAL = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
EXT_VIDEO = (".mp4", ".mov", ".m4v", ".webm")
EXT_IMG = (".jpg", ".jpeg", ".png", ".webp")


def _duracion(segundos: str) -> float:
    nums = [float(n) for n in re.findall(r"\d+(?:[.,]\d+)?", segundos.replace(",", "."))]
    if len(nums) >= 2 and nums[1] > nums[0]:
        return nums[1] - nums[0]
    return nums[0] if nums else 3.0


def _fuente(ruta: str, tam: int):
    try:
        return ImageFont.truetype(ruta, tam)
    except OSError:
        return ImageFont.load_default()


def _caja_texto(draw, texto, y, tam, ancho_chars, fondo=(0, 0, 0, 170)):
    f = _fuente(FUENTE, tam)
    lineas = textwrap.wrap(texto, ancho_chars) or [""]
    alto_linea = int(tam * 1.25)
    alto = alto_linea * len(lineas) + 50
    draw.rounded_rectangle([60, y, W - 60, y + alto], radius=36, fill=fondo)
    for i, linea in enumerate(lineas):
        draw.text((W // 2, y + 25 + i * alto_linea + alto_linea // 2), linea,
                  font=f, fill="white", anchor="mm")


def _limpiar(texto: str) -> str:
    """Quita emojis: la fuente no los dibuja (añádelos en el texto del post en TikTok)."""
    return re.sub(r"[\U00010000-\U0010FFFF\u2600-\u27BF\uFE0F]", "", texto).strip()


def _overlay(texto: str, ruta: Path):
    texto = _limpiar(texto)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if texto.strip():
        _caja_texto(ImageDraw.Draw(img), texto, 330, 68, 22)
    img.save(ruta)


def _tarjeta(plano: str, n: int, ruta: Path):
    """Fondo de storyboard cuando aún no hay material grabado."""
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):  # degradado oscuro
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(20 + 30 * t), int(18 + 10 * t), int(45 + 40 * t)))
    d.text((W // 2, 1150), f"ESCENA {n} · GRABA ESTO", font=_fuente(FUENTE, 44),
           fill=(255, 190, 80), anchor="mm")
    f = _fuente(FUENTE_NORMAL, 46)
    for i, linea in enumerate(textwrap.wrap(plano, 30)):
        d.text((W // 2, 1250 + i * 62), linea, font=f, fill=(230, 230, 240), anchor="mm")
    img.save(ruta)


def _medio(carpeta: Path | None, n: int) -> Path | None:
    if not carpeta:
        return None
    for ext in EXT_VIDEO + EXT_IMG:
        p = carpeta / f"escena{n}{ext}"
        if p.exists():
            return p
    return None


ESCALA = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"


def _segmento(fondo: Path, overlay: Path, dur: float, salida: Path):
    es_video = fondo.suffix.lower() in EXT_VIDEO
    entrada = ["-stream_loop", "-1", "-i", str(fondo)] if es_video else ["-loop", "1", "-i", str(fondo)]
    # Zoom lento en imágenes fijas para que no parezca una diapositiva.
    mov = "" if es_video else f",zoompan=z='min(zoom+0.0008,1.08)':d={int(dur * 30)}:s={W}x{H}:fps=30"
    filtro = f"[0:v]{ESCALA}{mov},fps=30[bg];[bg][1:v]overlay=0:0,format=yuv420p[v]"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", *entrada, "-i", str(overlay),
         "-filter_complex", filtro, "-map", "[v]", "-t", f"{dur:.2f}", "-an",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(salida)],
        check=True,
    )


def montar(guion: dict, salida: Path, carpeta_medios: Path | None = None) -> Path:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("Necesitas ffmpeg instalado (https://ffmpeg.org).")
    salida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        partes = []
        for n, e in enumerate(guion["escenas"], 1):
            fondo = _medio(carpeta_medios, n)
            if fondo is None:
                fondo = tmp / f"tarjeta{n}.png"
                _tarjeta(e["plano"], n, fondo)
            ov = tmp / f"ov{n}.png"
            _overlay(e.get("texto_pantalla", ""), ov)
            parte = tmp / f"p{n}.mp4"
            _segmento(fondo, ov, _duracion(e["segundos"]), parte)
            partes.append(parte)
        lista = tmp / "lista.txt"
        lista.write_text("".join(f"file '{p}'\n" for p in partes))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", str(lista), "-c", "copy", "-movflags", "+faststart", str(salida)],
                       check=True)
    return salida
