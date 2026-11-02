"""Agente 3 · JESÚS (jefe): lee las métricas reales y decide qué escalar o matar."""
import csv
from pathlib import Path

from pydantic import BaseModel, Field

from .comun import EXTRA, MODELO, cliente, comprobar

SISTEMA = """Eres Jesús, el jefe de una microagencia de afiliados de TikTok Shop sin anuncios
de pago. Recibes métricas reales de vídeos publicados y decides con frialdad.
Criterios orientativos: menos de 500 vistas tras 48 h -> el gancho falla; buen alcance pero
0 clics al carrito -> falla el producto o la oferta; ventas >= 1 -> producto validado.
Decisiones posibles: ESCALAR (hacer más vídeos de ese producto/gancho), ITERAR (mismo producto,
nuevo gancho), MATAR (abandonar). Nunca recomiendes pagar anuncios salvo con al menos
5 ventas orgánicas, y entonces con tope diario de 10 €. Si los datos son insuficientes, dilo."""


class Decision(BaseModel):
    producto: str
    decision: str = Field(description="ESCALAR | ITERAR | MATAR")
    motivo: str
    siguiente_accion: str


class Parte(BaseModel):
    resumen: str
    decisiones: list[Decision]
    prioridad_de_manana: str


def decidir(ruta_csv: Path) -> Parte:
    with open(ruta_csv, encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    if not filas:
        raise ValueError(f"{ruta_csv} no tiene métricas todavía.")
    r = cliente().beta.messages.parse(
        model=MODELO,
        max_tokens=16000,
        system=SISTEMA,
        output_config={"effort": "high"},
        output_format=Parte,
        messages=[{"role": "user", "content": f"Métricas de los vídeos:\n{filas}"}],
        **EXTRA,
    )
    comprobar(r)
    return r.parsed_output
