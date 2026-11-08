"""Proveedor EODHD (eodhd.com), API REST de pago con plan gratuito limitado.

Endpoints usados (documentación oficial):
* Histórico: ``GET https://eodhd.com/api/eod/{SIMBOLO}.{BOLSA}?api_token=..&fmt=json&period=m``
  -> lista de ``{date, open, high, low, close, adjusted_close, volume}``; con
  ``period=m`` la fecha es el primer día de negociación del mes.
* Cotización: ``GET https://eodhd.com/api/real-time/{SIMBOLO}.{BOLSA}?api_token=..&fmt=json``
  ("Live (delayed)": ~15-20 min de retraso) -> ``{code, timestamp, close, previousClose, ...}``.

Formato de ticker: ``SIMBOLO.BOLSA`` con códigos propios de EODHD: ``IWDA.AS``
(Euronext Ámsterdam), ``EUNH.XETRA`` (Xetra), ``SPY.US``...
Clave: variable de entorno ``EODHD_API_KEY``. Va en la query (la API lo exige),
por eso nunca se registra la URL completa.
"""
from __future__ import annotations

import os

import pandas as pd

from .base import ErrorProveedor, Proveedor, a_fin_de_mes, info_bolsa, iso_desde_unix, pedir_json

URL = "https://eodhd.com/api"


def ticker_eodhd(ticker: str) -> str:
    """``IWDA.AS`` -> ``IWDA.AS``; ``EUNH.DE`` -> ``EUNH.XETRA``; ``SPY`` -> ``SPY.US``."""
    simbolo, bolsa, _mic, _moneda = info_bolsa(ticker)
    return f"{simbolo}.{bolsa}"


class ProveedorEODHD(Proveedor):
    nombre = "eodhd"
    retraso_min = 15  # "Live (delayed)" API: 15-20 min según la bolsa

    def __init__(self, api_key: str | None = None, sesion=None):
        self._clave = api_key or os.environ.get("EODHD_API_KEY", "")
        if not self._clave:
            raise ErrorProveedor("EODHD: falta la clave API. Define la variable de entorno "
                                 "EODHD_API_KEY (consíguela en eodhd.com).")
        self._sesion = sesion

    def _pedir(self, ruta: str, **params):
        params = {"api_token": self._clave, "fmt": "json", **params}
        return pedir_json(f"{URL}/{ruta}", params=params, fuente="EODHD",
                          secretos=[self._clave], sesion=self._sesion)

    def historico_mensual(self, ticker: str) -> pd.Series:
        sym = ticker_eodhd(ticker)
        datos = self._pedir(f"eod/{sym}", period="m")
        if isinstance(datos, dict):  # errores vienen como {"message": ...} o similar
            raise ErrorProveedor(f"EODHD: respuesta inesperada para {ticker} ({sym}).")
        if not datos:
            raise ErrorProveedor(f"EODHD no devuelve datos para {ticker} ({sym}). Revisa el ticker.")
        df = pd.DataFrame(datos)
        col = "adjusted_close" if "adjusted_close" in df else "close"
        serie = pd.to_numeric(df[col], errors="coerce")
        serie.index = pd.to_datetime(df["date"])
        return a_fin_de_mes(serie).rename(ticker)

    def cotizacion(self, ticker: str) -> dict:
        sym = ticker_eodhd(ticker)
        moneda = info_bolsa(ticker)[3]  # la respuesta no trae moneda: se deduce de la bolsa
        d = self._pedir(f"real-time/{sym}")
        precio, ts = (d or {}).get("close"), (d or {}).get("timestamp")
        if precio in (None, "NA") or ts in (None, "NA"):
            raise ErrorProveedor(f"EODHD no devuelve cotización para {ticker} ({sym}).")
        return self._cotizacion(precio, moneda, iso_desde_unix(ts))
