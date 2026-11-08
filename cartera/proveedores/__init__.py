"""Proveedores de datos de mercado intercambiables.

Selección: ``obtener_proveedor("eodhd")`` o variable de entorno ``CARTERA_PROVEEDOR``
(``yahoo`` por defecto; también ``eodhd``, ``twelvedata``, ``demo``).
"""
from __future__ import annotations

import os

from .base import ErrorProveedor, Proveedor

DISPONIBLES = ("yahoo", "eodhd", "twelvedata", "demo")


def obtener_proveedor(nombre: str | None = None) -> Proveedor:
    nombre = (nombre or os.environ.get("CARTERA_PROVEEDOR") or "yahoo").strip().lower()
    if nombre == "yahoo":
        from .yahoo import ProveedorYahoo
        return ProveedorYahoo()
    if nombre == "eodhd":
        from .eodhd import ProveedorEODHD
        return ProveedorEODHD()
    if nombre in ("twelvedata", "twelve_data", "12data"):
        from .twelvedata import ProveedorTwelveData
        return ProveedorTwelveData()
    if nombre == "demo":
        from .demo import ProveedorDemo
        return ProveedorDemo()
    raise ErrorProveedor(f"Proveedor '{nombre}' desconocido. Opciones: {', '.join(DISPONIBLES)}.")


__all__ = ["DISPONIBLES", "ErrorProveedor", "Proveedor", "obtener_proveedor"]
