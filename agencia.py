"""Microagencia IA: 3 agentes para vender como afiliado en TikTok Shop sin pagar anuncios.

Uso:
  python agencia.py buscar "hogar y cocina"        # Agente 1: productos
  python agencia.py crear salidas/<fecha>_productos.json 1   # Agente 2: guiones del producto nº1
  python agencia.py decidir datos/metricas.csv     # Agente 3: qué escalar o matar
  python agencia.py dia "hogar y cocina"           # Buscar + guiones del mejor producto
  python agencia.py video salidas/<fecha>_guiones.json 1 medios/   # Monta el guion nº1 en MP4
"""
import json
import sys
from pathlib import Path

from agencia import buscador, creador, jefe, video
from agencia.comun import guardar


def cmd_buscar(nicho: str):
    informe = buscador.buscar(nicho)
    ruta = guardar("productos", informe.model_dump())
    for i, p in enumerate(informe.productos, 1):
        print(f"{i}. [{p.puntuacion}] {p.nombre} · {p.precio_estimado_eur} € · saturación {p.saturacion}")
        print(f"   {p.por_que_vende}")
    print(f"\nGuardado en {ruta}")
    return informe


def cmd_crear(ruta: str, n: str = "1"):
    productos = json.loads(Path(ruta).read_text(encoding="utf-8"))["productos"]
    producto = productos[int(n) - 1]
    paquete = creador.crear(producto)
    salida = guardar("guiones", paquete.model_dump())
    for g in paquete.guiones:
        print(f"\n=== {g.titulo_interno} ===\nGancho: {g.gancho}")
        for e in g.escenas:
            print(f"  [{e.segundos}] {e.plano} | texto: {e.texto_pantalla} | voz: {e.voz_en_off}")
        print(f"  Post: {g.descripcion_post} {' '.join(g.hashtags)}")
    print(f"\nGuardado en {salida}")


def cmd_decidir(ruta: str):
    parte = jefe.decidir(Path(ruta))
    salida = guardar("decision", parte.model_dump())
    print(parte.resumen)
    for d in parte.decisiones:
        print(f"- {d.decision}: {d.producto} → {d.motivo}\n  Haz: {d.siguiente_accion}")
    print(f"\nMañana: {parte.prioridad_de_manana}\nGuardado en {salida}")


def cmd_dia(nicho: str):
    informe = cmd_buscar(nicho)
    mejor = max(informe.productos, key=lambda p: p.puntuacion)
    ruta = guardar("mejor_producto", {"productos": [mejor.model_dump()]})
    cmd_crear(str(ruta), "1")


def cmd_video(ruta: str, n: str = "1", medios: str = ""):
    paquete = json.loads(Path(ruta).read_text(encoding="utf-8"))
    guion = paquete["guiones"][int(n) - 1]
    nombre = Path(ruta).stem.replace("_guiones", "") + f"_video{n}.mp4"
    salida = video.montar(guion, Path("salidas") / nombre, Path(medios) if medios else None)
    print(f"Vídeo listo: {salida}")
    if not medios:
        print("Sin carpeta de medios: escenas en modo storyboard. Graba escena1.mp4, escena2.mp4… y repite.")


if __name__ == "__main__":
    comandos = {"buscar": cmd_buscar, "crear": cmd_crear, "decidir": cmd_decidir, "dia": cmd_dia, "video": cmd_video}
    if len(sys.argv) < 3 or sys.argv[1] not in comandos:
        print(__doc__)
        sys.exit(1)
    comandos[sys.argv[1]](*sys.argv[2:])
