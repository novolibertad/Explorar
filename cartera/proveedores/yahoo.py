"""Proveedor Yahoo Finance vía ``yfinance`` (API no oficial, gratuita).

Las cotizaciones de bolsas europeas en Yahoo suelen ir con ~15 min de retraso.
Uso personal/educativo: las condiciones de Yahoo no permiten redistribuir los datos.
"""
from __future__ import annotations

import pandas as pd

from .base import ErrorProveedor, Proveedor, a_fin_de_mes, ahora_iso


class ProveedorYahoo(Proveedor):
    nombre = "yahoo"
    retraso_min = 15  # retraso típico de Yahoo para Euronext/Xetra (no es tiempo real)

    @staticmethod
    def _yf():
        try:
            import yfinance as yf
        except ImportError:
            raise ErrorProveedor("Falta la librería yfinance: pip install yfinance") from None
        return yf

    def historico_mensual(self, ticker: str) -> pd.Series:
        yf = self._yf()
        try:
            df = yf.download(ticker, period="max", interval="1mo", auto_adjust=True,
                             progress=False, timeout=10)
        except Exception as e:  # yfinance lanza tipos muy variados
            raise ErrorProveedor(f"Yahoo: error descargando {ticker} ({type(e).__name__}).") from None
        if df is None or df.empty:
            raise ErrorProveedor(f"Yahoo no devuelve datos para {ticker}. Revisa el ticker.")
        return a_fin_de_mes(df["Close"].squeeze()).rename(ticker)

    def cotizacion(self, ticker: str) -> dict:
        yf = self._yf()
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="5d", interval="1m")
            moneda = None
            try:
                moneda = t.fast_info.get("currency")
            except Exception:
                pass
        except Exception as e:
            raise ErrorProveedor(f"Yahoo: error pidiendo la cotización de {ticker} "
                                 f"({type(e).__name__}).") from None
        if hist is None or hist.empty:
            raise ErrorProveedor(f"Yahoo no devuelve cotización para {ticker}. Revisa el ticker.")
        ult = hist["Close"].dropna()
        if ult.empty:
            raise ErrorProveedor(f"Yahoo no devuelve cotización para {ticker}.")
        hora = pd.Timestamp(ult.index[-1])
        hora_iso = (hora.tz_convert("UTC") if hora.tzinfo else hora.tz_localize("UTC")).isoformat()
        return self._cotizacion(ult.iloc[-1], moneda, hora_iso or ahora_iso())
