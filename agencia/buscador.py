"""Agente 1 · BUSCADOR: investiga en la web y propone productos para TikTok Shop."""
from pydantic import BaseModel, Field

from .comun import EXTRA, MODELO, cliente, comprobar

SISTEMA = """Eres el Buscador de una microagencia de afiliados de TikTok Shop en España.
Objetivo: encontrar productos con demanda real y poca saturación, vendibles con vídeo orgánico
(sin anuncios de pago). Investiga con la búsqueda web: tendencias actuales, TikTok Shop España,
reseñas, Amazon más vendidos. Descarta productos saturados, frágiles, de marca registrada,
con riesgo sanitario o que requieran certificaciones. Sé escéptico: puntúa bajo si dudas.
Precio ideal 15-60 €. Prioriza productos que se entienden en 3 segundos de vídeo."""


class Producto(BaseModel):
    nombre: str
    precio_estimado_eur: float
    por_que_vende: str = Field(description="Problema que resuelve y prueba de demanda")
    angulo_video: str = Field(description="Idea visual concreta para el vídeo")
    saturacion: str = Field(description="baja | media | alta, con motivo")
    riesgos: str
    puntuacion: int = Field(description="0-100, potencial real de venta orgánica")
    fuentes: list[str]


class Informe(BaseModel):
    productos: list[Producto]


def buscar(nicho: str, cantidad: int = 5) -> Informe:
    r = cliente().beta.messages.parse(
        model=MODELO,
        max_tokens=16000,
        system=SISTEMA,
        output_config={"effort": "medium"},
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 8}],
        output_format=Informe,
        messages=[{
            "role": "user",
            "content": f"Nicho: {nicho}. Dame los {cantidad} mejores productos, "
                       "ordenados de mayor a menor puntuación.",
        }],
        **EXTRA,
    )
    comprobar(r)
    return r.parsed_output
