"""Proveedor DEMO: datos sintéticos deterministas, sin red. NO son datos reales."""
from __future__ import annotations

import zlib

import numpy as np
import pandas as pd

from .base import Proveedor, ahora_iso, info_bolsa, ErrorProveedor

# (rentabilidad anual, volatilidad anual) aproximadas, SOLO para el modo demo.
PARAMETROS = {
    "IWDA.AS": (0.09, 0.15), "EIMI.AS": (0.06, 0.18), "EUNH.DE": (0.02, 0.06),
    "XEON.DE": (0.01, 0.005), "4GLD.DE": (0.06, 0.14),
}


def serie_sintetica(ticker: str, anios: int = 15) -> pd.Series:
    """Paseo aleatorio mensual reproducible: la semilla es ``zlib.crc32(ticker)``."""
    meses = anios * 12
    fechas = pd.date_range(end=pd.Timestamp.today().normalize(), periods=meses, freq="ME")
    mu, sigma = PARAMETROS.get(ticker, (0.05, 0.15))
    rng = np.random.default_rng(zlib.crc32(ticker.encode()))
    r = rng.normal(mu / 12, sigma / np.sqrt(12), meses)
    return pd.Series(100 * np.cumprod(1 + r), index=fechas, name=ticker)


class ProveedorDemo(Proveedor):
    nombre = "demo"
    retraso_min = 0
    cachear_historico = False

    def __init__(self, anios: int = 15):
        self.anios = anios

    def historico_mensual(self, ticker: str) -> pd.Series:
        return serie_sintetica(ticker, self.anios)

    def cotizacion(self, ticker: str) -> dict:
        try:
            moneda = info_bolsa(ticker)[3]
        except ErrorProveedor:
            moneda = "EUR"
        ultimo = float(serie_sintetica(ticker, self.anios).iloc[-1])
        # pequeña variación intradía determinista (±0,5 %) para que parezca una cotización
        ajuste = (zlib.crc32((ticker + "cot").encode()) % 1001 - 500) / 100_000
        q = self._cotizacion(round(ultimo * (1 + ajuste), 4), moneda, ahora_iso())
        q["aviso"] = "Datos sintéticos (modo demo), no reales."
        return q
