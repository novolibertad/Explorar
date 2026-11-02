"""Configuración compartida por los 3 agentes."""
import json
import os
from datetime import date
from pathlib import Path

import anthropic

MODELO = os.environ.get("AGENCIA_MODELO", "claude-opus-5-5")
SALIDAS = Path(__file__).resolve().parent.parent / "salidas"

# Si el modelo rechaza una petición, la API la reintenta con otro modelo.
EXTRA = {
    "betas": ["server-side-fallback-2026-07-01"],
    "fallbacks": "default",
}

_client = None


def cliente() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # usa ANTHROPIC_API_KEY
    return _client


def comprobar(respuesta) -> None:
    if respuesta.stop_reason == "refusal":
        raise RuntimeError("El modelo rechazó la petición. Reformula el nicho.")
    if respuesta.stop_reason == "max_tokens":
        raise RuntimeError("Respuesta cortada por longitud. Pide menos productos.")


def guardar(nombre: str, datos) -> Path:
    SALIDAS.mkdir(exist_ok=True)
    ruta = SALIDAS / f"{date.today().isoformat()}_{nombre}.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta
