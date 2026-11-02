"""Agente 2 · CREADOR: convierte un producto en guiones de vídeo listos para grabar."""
from pydantic import BaseModel, Field

from .comun import EXTRA, MODELO, cliente, comprobar

SISTEMA = """Eres el Creador de vídeos de una microagencia de afiliados de TikTok Shop en España.
Escribes guiones de 15-30 s para vídeo orgánico, en español de España, tono natural (nada de
'¡increíble!' ni frases de teletienda). Se graban con móvil y sin mostrar la cara.
Reglas: el gancho de los 2 primeros segundos es lo más importante; muestra el problema antes
que el producto; nada de afirmaciones falsas, médicas o de resultados garantizados;
una llamada a la acción suave hacia el carrito naranja."""


class Escena(BaseModel):
    segundos: str = Field(description="p.ej. 0-2")
    plano: str = Field(description="Qué se graba exactamente")
    texto_pantalla: str
    voz_en_off: str


class Guion(BaseModel):
    titulo_interno: str
    gancho: str
    escenas: list[Escena]
    descripcion_post: str
    hashtags: list[str]
    sonido_sugerido: str


class Paquete(BaseModel):
    producto: str
    guiones: list[Guion]


def crear(producto: dict, variantes: int = 3) -> Paquete:
    r = cliente().beta.messages.parse(
        model=MODELO,
        max_tokens=16000,
        system=SISTEMA,
        output_config={"effort": "medium"},
        output_format=Paquete,
        messages=[{
            "role": "user",
            "content": f"Producto:\n{producto}\n\nCrea {variantes} guiones con ganchos "
                       "distintos (problema, curiosidad, antes/después).",
        }],
        **EXTRA,
    )
    comprobar(r)
    return r.parsed_output
