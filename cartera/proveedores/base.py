"""Base común de los proveedores de datos: interfaz, errores, HTTP robusto y tickers.

Todos los proveedores reciben tickers en formato Yahoo (``IWDA.AS``, ``EUNH.DE``)
porque es el formato que usa el resto del proyecto; cada uno lo traduce al suyo.
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import pandas as pd

log = logging.getLogger("cartera.proveedores")

TIMEOUT_S = 10          # timeout por petición HTTP
REINTENTOS = 3          # intentos totales (1 + 2 reintentos)
ESPERA_BASE_S = 0.5     # backoff exponencial: 0.5 s, 1 s, 2 s...
_dormir = time.sleep    # sustituible en tests


class ErrorProveedor(ValueError):
    """Error de un proveedor de datos con mensaje claro en español (sin claves API)."""


# Sufijo Yahoo -> (código de bolsa EODHD, MIC ISO 10383 para Twelve Data, moneda habitual)
BOLSAS: dict[str, tuple[str, str, str]] = {
    "AS": ("AS", "XAMS", "EUR"),       # Euronext Ámsterdam
    "DE": ("XETRA", "XETR", "EUR"),    # Xetra (Deutsche Börse)
    "F": ("F", "XFRA", "EUR"),         # Fráncfort
    "PA": ("PA", "XPAR", "EUR"),       # Euronext París
    "MI": ("MI", "XMIL", "EUR"),       # Borsa Italiana
    "MC": ("MC", "XMAD", "EUR"),       # Bolsa de Madrid
    "BR": ("BR", "XBRU", "EUR"),       # Euronext Bruselas
    "L": ("LSE", "XLON", "GBX"),       # Londres (muchos ETF cotizan en peniques o USD)
    "SW": ("SW", "XSWX", "CHF"),       # SIX Suiza
}


def separar_ticker(ticker: str) -> tuple[str, str | None]:
    """``'IWDA.AS'`` -> ``('IWDA', 'AS')``; ``'SPY'`` -> ``('SPY', None)``."""
    simbolo, _, sufijo = ticker.strip().upper().rpartition(".")
    if not simbolo:  # no había punto
        return sufijo, None
    return simbolo, sufijo


def info_bolsa(ticker: str) -> tuple[str, str, str, str]:
    """Devuelve (símbolo, código EODHD, MIC, moneda) para un ticker estilo Yahoo."""
    simbolo, sufijo = separar_ticker(ticker)
    if sufijo is None:
        return simbolo, "US", "", "USD"
    if sufijo not in BOLSAS:
        raise ErrorProveedor(
            f"Bolsa '.{sufijo}' del ticker {ticker} no reconocida. "
            f"Sufijos admitidos: {', '.join('.' + s for s in BOLSAS)} o sin sufijo (EE. UU.).")
    return (simbolo, *BOLSAS[sufijo])


def a_fin_de_mes(serie: pd.Series) -> pd.Series:
    """Normaliza el índice a fin de mes, ordena y quita duplicados (se queda con el último)."""
    serie = serie.dropna().astype(float)
    serie.index = pd.to_datetime(serie.index).to_period("M").to_timestamp("M")
    serie = serie.sort_index()
    return serie[~serie.index.duplicated(keep="last")]


def ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def iso_desde_unix(ts) -> str:
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat(timespec="seconds")


def _ocultar(texto: str, secretos: list[str]) -> str:
    for s in secretos:
        if s:
            texto = texto.replace(s, "***")
    return texto


def pedir_json(url: str, *, params: dict | None = None, headers: dict | None = None,
               fuente: str, secretos: list[str] | None = None, sesion=None):
    """GET con timeout, reintentos con backoff exponencial y errores en español.

    Reintenta ante fallos de red, 429 y 5xx. Nunca incluye en mensajes ni logs los
    valores de ``secretos`` (claves API), aunque aparezcan en la URL o la excepción.
    """
    import requests

    secretos = secretos or []
    http = sesion or requests
    ultimo = "sin respuesta"
    for intento in range(1, REINTENTOS + 1):
        try:
            r = http.get(url, params=params, headers=headers, timeout=TIMEOUT_S)
        except (requests.ConnectionError, requests.Timeout) as e:
            ultimo = f"error de red ({type(e).__name__})"
        else:
            if r.status_code in (401, 403):
                raise ErrorProveedor(
                    f"{fuente}: acceso denegado (HTTP {r.status_code}). Revisa que la clave API "
                    "sea correcta y que tu plan incluya esta bolsa o este tipo de dato.")
            if r.status_code == 404:
                raise ErrorProveedor(f"{fuente}: recurso no encontrado (HTTP 404). Revisa el ticker.")
            if r.status_code == 429 or r.status_code >= 500:
                ultimo = f"HTTP {r.status_code}"
            elif r.status_code >= 400:
                raise ErrorProveedor(f"{fuente}: petición rechazada (HTTP {r.status_code}).")
            else:
                try:
                    return r.json()
                except ValueError:
                    raise ErrorProveedor(f"{fuente}: la respuesta no es JSON válido.") from None
        log.warning("%s: intento %d/%d fallido: %s", fuente, intento, REINTENTOS,
                    _ocultar(ultimo, secretos))
        if intento < REINTENTOS:
            _dormir(ESPERA_BASE_S * 2 ** (intento - 1))
    raise ErrorProveedor(_ocultar(
        f"{fuente}: no se pudo obtener respuesta tras {REINTENTOS} intentos ({ultimo}). "
        "Comprueba tu conexión o inténtalo más tarde.", secretos))


class Proveedor(ABC):
    """Interfaz de un proveedor de precios.

    * ``historico_mensual(ticker)``: serie de cierres mensuales (ajustados por
      dividendos/splits cuando el proveedor lo permite), índice a fin de mes.
    * ``cotizacion(ticker)``: dict con ``precio``, ``moneda``, ``hora`` (ISO 8601,
      hora del último precio), ``retraso_min`` (retraso típico del dato según el
      proveedor/plan) y ``fuente``.
    """

    nombre: str = "base"
    retraso_min: int = 0
    # True si el histórico es de pago por petición y conviene cachearlo en disco
    cachear_historico: bool = True

    @abstractmethod
    def historico_mensual(self, ticker: str) -> pd.Series: ...

    @abstractmethod
    def cotizacion(self, ticker: str) -> dict: ...

    def _cotizacion(self, precio, moneda, hora: str | None) -> dict:
        return {"precio": float(precio), "moneda": moneda, "hora": hora or ahora_iso(),
                "retraso_min": self.retraso_min, "fuente": self.nombre}

    def __repr__(self) -> str:
        return f"<Proveedor {self.nombre}>"
