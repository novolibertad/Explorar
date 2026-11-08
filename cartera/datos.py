"""Precios mensuales: Yahoo Finance (con caché local) o datos sintéticos de demo."""
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

SALIDAS = Path(__file__).resolve().parent.parent / "salidas"
CACHE = SALIDAS / "precios"

# (rentabilidad anual, volatilidad anual) aproximadas, SOLO para el modo demo.
_DEMO = {
    "IWDA.AS": (0.09, 0.15), "EIMI.AS": (0.06, 0.18), "EUNH.DE": (0.02, 0.06),
    "XEON.DE": (0.01, 0.005), "4GLD.DE": (0.06, 0.14),
}


def _demo(tickers: list[str], anios: int = 15) -> pd.DataFrame:
    meses = anios * 12
    fechas = pd.date_range(end=pd.Timestamp.today().normalize(), periods=meses, freq="ME")
    datos = {}
    for t in tickers:
        mu, sigma = _DEMO.get(t, (0.05, 0.15))
        rng = np.random.default_rng(zlib.crc32(t.encode()))
        r = rng.normal(mu / 12, sigma / np.sqrt(12), meses)
        datos[t] = 100 * np.cumprod(1 + r)
    return pd.DataFrame(datos, index=fechas)


def _yahoo(ticker: str) -> pd.Series:
    CACHE.mkdir(parents=True, exist_ok=True)
    ruta = CACHE / f"{ticker}.csv"
    if ruta.exists() and (pd.Timestamp.now() - pd.Timestamp(ruta.stat().st_mtime, unit="s")).days < 7:
        return pd.read_csv(ruta, index_col=0, parse_dates=True).iloc[:, 0]
    import yfinance as yf

    df = yf.download(ticker, period="max", interval="1mo", auto_adjust=True, progress=False)
    if df.empty:
        raise ValueError(f"Yahoo no devuelve datos para {ticker}. Revisa el ticker.")
    serie = df["Close"].squeeze().dropna()
    serie.index = pd.to_datetime(serie.index).to_period("M").to_timestamp("M")
    serie = serie[~serie.index.duplicated(keep="last")]
    serie.rename(ticker).to_csv(ruta)
    return serie


def precios(tickers: list[str], demo: bool = False) -> pd.DataFrame:
    """Precios mensuales alineados al periodo común (desde el ETF más reciente)."""
    if demo:
        return _demo(tickers)
    df = pd.concat({t: _yahoo(t) for t in tickers}, axis=1).dropna()
    if len(df) < 24:
        raise ValueError("Menos de 2 años de historia común: el backtest no sería fiable.")
    return df


def guardar(nombre: str, datos) -> Path:
    import json
    from datetime import date

    SALIDAS.mkdir(exist_ok=True)
    ruta = SALIDAS / f"{date.today().isoformat()}_{nombre}.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta
