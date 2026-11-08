"""Capa de datos: precios mensuales y cotizaciones con proveedores intercambiables.

* ``precios(tickers, demo=False, proveedor=None)``: DataFrame mensual alineado al
  periodo común. Histórico cacheado en CSV 7 días (``salidas/precios``).
* ``cotizaciones(tickers, proveedor=None)``: último precio de cada ticker, con
  caché en memoria de 60 s. Cada cotización indica ``retraso_min`` y ``fuente``.
* ``guardar(nombre, datos)``: guarda un JSON con fecha en ``salidas/``.

Proveedor: argumento ``proveedor`` (nombre o instancia) o variable de entorno
``CARTERA_PROVEEDOR`` (``yahoo`` por defecto; ``eodhd``, ``twelvedata``, ``demo``).
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd

from cartera.proveedores import ErrorProveedor, Proveedor, obtener_proveedor
from cartera.proveedores.demo import PARAMETROS as _DEMO  # noqa: F401  (compatibilidad)
from cartera.proveedores.demo import ProveedorDemo

log = logging.getLogger("cartera.datos")

SALIDAS = Path(__file__).resolve().parent.parent / "salidas"
CACHE = SALIDAS / "precios"
CADUCIDAD_HISTORICO_DIAS = 7
CADUCIDAD_COTIZACION_S = 60
MIN_MESES_COMUNES = 24

_cache_cotizaciones: dict[tuple[str, str], tuple[float, dict]] = {}


def _resolver(proveedor: str | Proveedor | None) -> Proveedor:
    return proveedor if isinstance(proveedor, Proveedor) else obtener_proveedor(proveedor)


def _demo(tickers: list[str], anios: int = 15) -> pd.DataFrame:
    """Compatibilidad: DataFrame sintético del modo demo."""
    p = ProveedorDemo(anios)
    return pd.DataFrame({t: p.historico_mensual(t) for t in tickers})


def _ruta_cache(prov: Proveedor, ticker: str) -> Path:
    # Yahoo conserva el nombre de fichero histórico para reutilizar cachés existentes.
    nombre = ticker if prov.nombre == "yahoo" else f"{prov.nombre}_{ticker}"
    return CACHE / f"{nombre.replace('/', '_')}.csv"


def _historico(prov: Proveedor, ticker: str) -> pd.Series:
    if not prov.cachear_historico:
        return prov.historico_mensual(ticker)
    ruta = _ruta_cache(prov, ticker)
    if ruta.exists():
        edad = pd.Timestamp.now() - pd.Timestamp(ruta.stat().st_mtime, unit="s")
        if edad.days < CADUCIDAD_HISTORICO_DIAS:
            return pd.read_csv(ruta, index_col=0, parse_dates=True).iloc[:, 0].rename(ticker)
    serie = prov.historico_mensual(ticker)
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        serie.rename(ticker).to_csv(ruta)
    except OSError as e:  # la caché es una optimización: no debe romper el cálculo
        log.warning("No se pudo escribir la caché %s: %s", ruta, e)
    return serie


def precios(tickers: list[str], demo: bool = False,
            proveedor: str | Proveedor | None = None) -> pd.DataFrame:
    """Precios mensuales alineados al periodo común (desde el ETF más reciente)."""
    if demo:
        return _demo(tickers)
    prov = _resolver(proveedor)
    series = {}
    for t in tickers:
        try:
            series[t] = _historico(prov, t)
        except ErrorProveedor:
            raise
        except Exception as e:
            raise ErrorProveedor(f"{prov.nombre}: error inesperado obteniendo {t} "
                                 f"({type(e).__name__}).") from e
    df = pd.concat(series, axis=1).dropna()
    if len(df) < MIN_MESES_COMUNES:
        raise ValueError("Menos de 2 años de historia común: el backtest no sería fiable.")
    return df


def cotizaciones(tickers: list[str], proveedor: str | Proveedor | None = None) -> dict[str, dict]:
    """Última cotización por ticker: ``{ticker: {precio, moneda, hora, retraso_min, fuente}}``.

    Si un ticker falla, su entrada es ``{"error": "<mensaje>", "fuente": ...}`` y
    el resto se devuelve igualmente.
    """
    prov = _resolver(proveedor)
    ahora = time.monotonic()
    salida: dict[str, dict] = {}
    for t in tickers:
        clave = (prov.nombre, t)
        guardado = _cache_cotizaciones.get(clave)
        if guardado and ahora - guardado[0] < CADUCIDAD_COTIZACION_S:
            salida[t] = dict(guardado[1])
            continue
        try:
            q = prov.cotizacion(t)
        except ErrorProveedor as e:
            salida[t] = {"error": str(e), "fuente": prov.nombre}
            continue
        except Exception as e:
            salida[t] = {"error": f"{prov.nombre}: error inesperado ({type(e).__name__}).",
                         "fuente": prov.nombre}
            continue
        _cache_cotizaciones[clave] = (ahora, q)
        salida[t] = dict(q)
    return salida


def limpiar_cache_cotizaciones() -> None:
    _cache_cotizaciones.clear()


def guardar(nombre: str, datos) -> Path:
    import json
    from datetime import date

    SALIDAS.mkdir(exist_ok=True)
    ruta = SALIDAS / f"{date.today().isoformat()}_{nombre}.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta
