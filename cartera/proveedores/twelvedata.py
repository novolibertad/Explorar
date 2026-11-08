"""Proveedor Twelve Data (twelvedata.com), API REST.

Endpoints usados:
* Histórico: ``GET https://api.twelvedata.com/time_series?symbol=IWDA&mic_code=XAMS
  &interval=1month&outputsize=5000&adjust=all`` -> ``{meta:{currency,..},
  values:[{datetime, close, ...}], status:"ok"}`` (por defecto, más reciente primero).
* Cotización: ``GET https://api.twelvedata.com/quote?symbol=IWDA&mic_code=XAMS``
  -> ``{symbol, currency, datetime, timestamp, close, is_market_open, ...}``.
* Errores: HTTP 200 con ``{"status": "error", "code": 4xx, "message": ...}``.

Formato de ticker: símbolo sin sufijo + ``mic_code`` ISO 10383 (XAMS = Ámsterdam,
XETR = Xetra). La clave (``TWELVEDATA_API_KEY``) va en la cabecera
``Authorization: apikey ...`` (recomendado por la documentación), no en la URL.
Bolsas europeas: requieren plan de pago; en planes Basic/Grow el uso es solo personal.
"""
from __future__ import annotations

import os

import pandas as pd

from .base import ErrorProveedor, Proveedor, a_fin_de_mes, info_bolsa, iso_desde_unix, pedir_json

URL = "https://api.twelvedata.com"


def params_twelvedata(ticker: str) -> dict:
    """``EUNH.DE`` -> ``{'symbol': 'EUNH', 'mic_code': 'XETR'}``; ``SPY`` -> ``{'symbol': 'SPY'}``."""
    simbolo, _eod, mic, _moneda = info_bolsa(ticker)
    return {"symbol": simbolo, **({"mic_code": mic} if mic else {})}


class ProveedorTwelveData(Proveedor):
    nombre = "twelvedata"

    def __init__(self, api_key: str | None = None, sesion=None):
        self._clave = api_key or os.environ.get("TWELVEDATA_API_KEY", "")
        if not self._clave:
            raise ErrorProveedor("Twelve Data: falta la clave API. Define la variable de entorno "
                                 "TWELVEDATA_API_KEY (consíguela en twelvedata.com).")
        # Tiempo real en planes de pago; ajustable si tu plan entrega datos diferidos.
        self.retraso_min = int(os.environ.get("TWELVEDATA_RETRASO_MIN", "0"))
        self._sesion = sesion

    def _pedir(self, ruta: str, ticker: str, **params):
        d = pedir_json(f"{URL}/{ruta}", params={**params_twelvedata(ticker), **params},
                       headers={"Authorization": f"apikey {self._clave}"},
                       fuente="Twelve Data", secretos=[self._clave], sesion=self._sesion)
        if not isinstance(d, dict):
            raise ErrorProveedor(f"Twelve Data: respuesta inesperada para {ticker}.")
        if d.get("status") == "error":
            codigo = d.get("code")
            if codigo in (401, 403):
                raise ErrorProveedor("Twelve Data: clave API no válida o tu plan no incluye "
                                     f"{ticker} (código {codigo}).")
            if codigo == 429:
                raise ErrorProveedor("Twelve Data: límite de peticiones alcanzado; espera un minuto.")
            if codigo == 404:
                raise ErrorProveedor(f"Twelve Data no encuentra {ticker}. Revisa el ticker.")
            raise ErrorProveedor(f"Twelve Data: error {codigo} para {ticker}.")
        return d

    def historico_mensual(self, ticker: str) -> pd.Series:
        d = self._pedir("time_series", ticker, interval="1month", outputsize=5000, adjust="all")
        valores = d.get("values") or []
        if not valores:
            raise ErrorProveedor(f"Twelve Data no devuelve datos para {ticker}. Revisa el ticker.")
        df = pd.DataFrame(valores)
        serie = pd.to_numeric(df["close"], errors="coerce")
        serie.index = pd.to_datetime(df["datetime"])
        return a_fin_de_mes(serie).rename(ticker)

    def cotizacion(self, ticker: str) -> dict:
        d = self._pedir("quote", ticker)
        if d.get("close") is None:
            raise ErrorProveedor(f"Twelve Data no devuelve cotización para {ticker}.")
        hora = iso_desde_unix(d["timestamp"]) if d.get("timestamp") else None
        q = self._cotizacion(d["close"], d.get("currency"), hora)
        if "is_market_open" in d:
            q["mercado_abierto"] = bool(d["is_market_open"])
        return q
