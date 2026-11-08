"""Explica en lenguaje claro los resultados del backtest (educativo, no asesoramiento)."""
from pydantic import BaseModel

from agencia.comun import EXTRA, MODELO, cliente, comprobar

SISTEMA = """Eres un divulgador financiero para un inversor particular español.
Recibes resultados históricos de carteras indexadas (ETFs UCITS) y los explicas en
lenguaje llano, sin jerga. Reglas:
- Es contenido EDUCATIVO: no digas "debes comprar" ni recomiendes productos concretos.
- Explica qué significa la caída máxima en euros reales para su inversión.
- Recuerda que rentabilidades pasadas no garantizan futuras.
- Menciona costes (TER, comisiones del bróker) y fiscalidad española de ETFs
  (no hay traspaso sin peaje fiscal, a diferencia de los fondos) cuando sea relevante.
- Sé concreto y breve."""


class Explicacion(BaseModel):
    resumen: str
    que_significa_la_caida: str
    puntos_fuertes: list[str]
    riesgos: list[str]
    preguntas_para_hacerte: list[str]


def explicar(resultados: list[dict], perfil: str | None) -> Explicacion:
    contexto = f"Perfil del usuario: {perfil}.\n" if perfil else ""
    r = cliente().beta.messages.parse(
        model=MODELO,
        max_tokens=8000,
        system=SISTEMA,
        output_config={"effort": "medium"},
        output_format=Explicacion,
        messages=[{"role": "user", "content": f"{contexto}Resultados:\n{resultados}"}],
        **EXTRA,
    )
    comprobar(r)
    return r.parsed_output
