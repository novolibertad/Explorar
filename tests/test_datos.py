"""Tests de la capa de datos y proveedores. Sin red: HTTP simulado y proveedor demo."""
import logging
import sys
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cartera import datos  # noqa: E402
from cartera.proveedores import ErrorProveedor, Proveedor, base, obtener_proveedor  # noqa: E402
from cartera.proveedores.demo import ProveedorDemo  # noqa: E402
from cartera.proveedores.eodhd import ProveedorEODHD, ticker_eodhd  # noqa: E402
from cartera.proveedores.twelvedata import ProveedorTwelveData, params_twelvedata  # noqa: E402

CLAVE = "CLAVE-SECRETA-123"


class Resp:
    def __init__(self, status=200, json_data=None):
        self.status_code = status
        self._json = json_data

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


class Sesion:
    """Sesión HTTP falsa: devuelve respuestas en orden y registra las llamadas."""

    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.llamadas.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        r = self.respuestas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


@pytest.fixture(autouse=True)
def entorno(monkeypatch, tmp_path):
    monkeypatch.setattr(base, "_dormir", lambda s: None)
    monkeypatch.setattr(datos, "CACHE", tmp_path / "precios")
    monkeypatch.setattr(datos, "SALIDAS", tmp_path)
    monkeypatch.delenv("CARTERA_PROVEEDOR", raising=False)
    datos.limpiar_cache_cotizaciones()
    # Red bloqueada: cualquier petición real hace fallar el test.
    monkeypatch.setattr(requests, "get", mock.Mock(side_effect=AssertionError("red real")))
    yield


# ---------- mapeo de tickers ----------

@pytest.mark.parametrize("yahoo, eod, td", [
    ("IWDA.AS", "IWDA.AS", {"symbol": "IWDA", "mic_code": "XAMS"}),
    ("EUNH.DE", "EUNH.XETRA", {"symbol": "EUNH", "mic_code": "XETR"}),
    ("4GLD.DE", "4GLD.XETRA", {"symbol": "4GLD", "mic_code": "XETR"}),
    ("SPY", "SPY.US", {"symbol": "SPY"}),
    ("vwrl.l", "VWRL.LSE", {"symbol": "VWRL", "mic_code": "XLON"}),
])
def test_mapeo_tickers(yahoo, eod, td):
    assert ticker_eodhd(yahoo) == eod
    assert params_twelvedata(yahoo) == td


def test_sufijo_desconocido():
    with pytest.raises(ErrorProveedor, match="no reconocida"):
        ticker_eodhd("ABC.XX")


# ---------- selección de proveedor ----------

def test_obtener_proveedor(monkeypatch):
    assert obtener_proveedor().nombre == "yahoo"
    monkeypatch.setenv("CARTERA_PROVEEDOR", "demo")
    assert obtener_proveedor().nombre == "demo"
    monkeypatch.setenv("TWELVEDATA_API_KEY", CLAVE)
    assert obtener_proveedor("TwelveData").nombre == "twelvedata"
    with pytest.raises(ErrorProveedor, match="desconocido"):
        obtener_proveedor("bloomberg")


def test_falta_clave(monkeypatch):
    monkeypatch.delenv("EODHD_API_KEY", raising=False)
    monkeypatch.delenv("TWELVEDATA_API_KEY", raising=False)
    with pytest.raises(ErrorProveedor, match="EODHD_API_KEY"):
        obtener_proveedor("eodhd")
    with pytest.raises(ErrorProveedor, match="TWELVEDATA_API_KEY"):
        obtener_proveedor("twelvedata")


# ---------- demo ----------

def test_demo_determinista_y_compatible():
    a = datos.precios(["IWDA.AS", "EUNH.DE"], demo=True)
    b = datos.precios(["IWDA.AS", "EUNH.DE"], demo=True)
    pd.testing.assert_frame_equal(a, b)
    assert list(a.columns) == ["IWDA.AS", "EUNH.DE"] and len(a) == 180
    assert (a.index == a.index.to_period("M").to_timestamp("M")).all()
    # mismo resultado usando el proveedor demo por nombre
    c = datos.precios(["IWDA.AS", "EUNH.DE"], proveedor="demo")
    pd.testing.assert_frame_equal(a, c, check_freq=False)


def test_demo_cotizaciones():
    q = datos.cotizaciones(["IWDA.AS", "SPY"], proveedor="demo")
    assert set(q["IWDA.AS"]) >= {"precio", "moneda", "hora", "retraso_min", "fuente"}
    assert q["IWDA.AS"]["moneda"] == "EUR" and q["SPY"]["moneda"] == "USD"
    assert q["IWDA.AS"]["fuente"] == "demo"
    assert q == datos.cotizaciones(["IWDA.AS", "SPY"], proveedor="demo")


# ---------- EODHD ----------

def _eod_mensual(n=30, desde="2022-01-01"):
    fechas = pd.date_range(desde, periods=n, freq="MS")
    return [{"date": f.strftime("%Y-%m-%d"), "close": 100 + i, "adjusted_close": 90 + i}
            for i, f in enumerate(fechas)]


def test_eodhd_historico():
    s = Sesion(Resp(200, _eod_mensual()))
    p = ProveedorEODHD(api_key=CLAVE, sesion=s)
    serie = p.historico_mensual("EUNH.DE")
    assert s.llamadas[0]["url"] == "https://eodhd.com/api/eod/EUNH.XETRA"
    assert s.llamadas[0]["params"]["period"] == "m"
    assert s.llamadas[0]["timeout"] == base.TIMEOUT_S
    assert serie.iloc[0] == 90  # usa adjusted_close
    assert serie.index[0] == pd.Timestamp("2022-01-31")


def test_eodhd_cotizacion():
    s = Sesion(Resp(200, {"code": "IWDA.AS", "timestamp": 1_700_000_000, "close": 85.5}))
    q = ProveedorEODHD(api_key=CLAVE, sesion=s).cotizacion("IWDA.AS")
    assert s.llamadas[0]["url"] == "https://eodhd.com/api/real-time/IWDA.AS"
    assert q == {"precio": 85.5, "moneda": "EUR", "hora": "2023-11-14T22:13:20+00:00",
                 "retraso_min": 15, "fuente": "eodhd"}


def test_eodhd_cotizacion_na():
    s = Sesion(Resp(200, {"code": "X.AS", "timestamp": "NA", "close": "NA"}))
    with pytest.raises(ErrorProveedor, match="no devuelve cotización"):
        ProveedorEODHD(api_key=CLAVE, sesion=s).cotizacion("X.AS")


def test_reintentos_con_backoff(monkeypatch):
    esperas = []
    monkeypatch.setattr(base, "_dormir", esperas.append)
    s = Sesion(requests.ConnectionError("caída"), Resp(503), Resp(200, _eod_mensual()))
    serie = ProveedorEODHD(api_key=CLAVE, sesion=s).historico_mensual("IWDA.AS")
    assert len(serie) == 30 and len(s.llamadas) == 3
    assert esperas == [0.5, 1.0]


def test_reintentos_agotados_no_filtran_clave(caplog):
    url_con_clave = f"https://eodhd.com/api/eod/IWDA.AS?api_token={CLAVE}"
    s = Sesion(*[requests.Timeout(url_con_clave)] * 3)
    with caplog.at_level(logging.DEBUG), pytest.raises(ErrorProveedor) as e:
        ProveedorEODHD(api_key=CLAVE, sesion=s).historico_mensual("IWDA.AS")
    assert "3 intentos" in str(e.value)
    assert CLAVE not in str(e.value) and CLAVE not in caplog.text


def test_acceso_denegado_mensaje_claro():
    s = Sesion(Resp(403))
    with pytest.raises(ErrorProveedor, match="acceso denegado") as e:
        ProveedorEODHD(api_key=CLAVE, sesion=s).historico_mensual("IWDA.AS")
    assert CLAVE not in str(e.value) and len(s.llamadas) == 1  # 403 no se reintenta


# ---------- Twelve Data ----------

def _td_mensual(n=30):
    fechas = pd.date_range("2022-01-01", periods=n, freq="MS")[::-1]  # más reciente primero
    return {"meta": {"symbol": "IWDA", "currency": "EUR"}, "status": "ok",
            "values": [{"datetime": f.strftime("%Y-%m-%d"), "close": str(200 + i)}
                       for i, f in enumerate(fechas)]}


def test_twelvedata_historico_clave_en_cabecera():
    s = Sesion(Resp(200, _td_mensual()))
    serie = ProveedorTwelveData(api_key=CLAVE, sesion=s).historico_mensual("IWDA.AS")
    llamada = s.llamadas[0]
    assert llamada["url"] == "https://api.twelvedata.com/time_series"
    assert llamada["params"]["symbol"] == "IWDA" and llamada["params"]["mic_code"] == "XAMS"
    assert llamada["params"]["interval"] == "1month"
    assert CLAVE not in str(llamada["params"]) and llamada["headers"]["Authorization"].endswith(CLAVE)
    assert serie.index.is_monotonic_increasing and serie.iloc[-1] == 200


def test_twelvedata_cotizacion():
    s = Sesion(Resp(200, {"symbol": "EUNH", "currency": "EUR", "close": "4.95",
                          "timestamp": 1_700_000_000, "is_market_open": False}))
    q = ProveedorTwelveData(api_key=CLAVE, sesion=s).cotizacion("EUNH.DE")
    assert s.llamadas[0]["params"] == {"symbol": "EUNH", "mic_code": "XETR"}
    assert q["precio"] == 4.95 and q["moneda"] == "EUR" and q["fuente"] == "twelvedata"
    assert q["mercado_abierto"] is False


@pytest.mark.parametrize("codigo, patron", [(401, "clave API"), (429, "límite"), (404, "no encuentra")])
def test_twelvedata_errores(codigo, patron):
    s = Sesion(Resp(200, {"status": "error", "code": codigo, "message": f"x {CLAVE}"}))
    with pytest.raises(ErrorProveedor, match=patron) as e:
        ProveedorTwelveData(api_key=CLAVE, sesion=s).cotizacion("IWDA.AS")
    assert CLAVE not in str(e.value)


# ---------- datos.precios / cotizaciones con caché ----------

class Contador(Proveedor):
    nombre = "contador"
    retraso_min = 5

    def __init__(self, meses=30):
        self.meses, self.hist, self.cot = meses, 0, 0

    def historico_mensual(self, ticker):
        self.hist += 1
        idx = pd.date_range("2020-01-31", periods=self.meses, freq="ME")
        return pd.Series(range(1, self.meses + 1), index=idx, dtype=float, name=ticker)

    def cotizacion(self, ticker):
        self.cot += 1
        if ticker == "MAL":
            raise ErrorProveedor("ticker malo")
        return self._cotizacion(10, "EUR", None)


def test_precios_cache_disco():
    p = Contador()
    a = datos.precios(["A.AS", "B.DE"], proveedor=p)
    b = datos.precios(["A.AS", "B.DE"], proveedor=p)
    assert p.hist == 2  # la segunda vez sale de la caché CSV
    pd.testing.assert_frame_equal(a, b, check_freq=False)
    assert (datos.CACHE / "contador_A.AS.csv").exists()


def test_precios_historia_corta():
    with pytest.raises(ValueError, match="2 años"):
        datos.precios(["A.AS"], proveedor=Contador(meses=12))


def test_cotizaciones_cache_60s(monkeypatch):
    p, t = Contador(), [1000.0]
    monkeypatch.setattr(datos.time, "monotonic", lambda: t[0])
    q = datos.cotizaciones(["A.AS", "MAL"], proveedor=p)
    assert q["A.AS"]["precio"] == 10 and q["A.AS"]["retraso_min"] == 5
    assert "error" in q["MAL"]
    datos.cotizaciones(["A.AS"], proveedor=p)
    assert p.cot == 2  # A.AS en caché
    t[0] += 61
    datos.cotizaciones(["A.AS"], proveedor=p)
    assert p.cot == 3


def test_yahoo_seleccion_por_entorno_sin_red(monkeypatch):
    """Con CARTERA_PROVEEDOR=yahoo se usa yfinance; aquí se simula para no tocar la red."""
    falso = mock.Mock()
    idx = pd.date_range("2020-01-01", periods=30, freq="MS")
    falso.download.return_value = pd.DataFrame({"Close": range(1, 31)}, index=idx, dtype=float)
    monkeypatch.setitem(sys.modules, "yfinance", falso)
    monkeypatch.setenv("CARTERA_PROVEEDOR", "yahoo")
    df = datos.precios(["IWDA.AS"])
    assert len(df) == 30 and (datos.CACHE / "IWDA.AS.csv").exists()


def test_guardar():
    ruta = datos.guardar("prueba", {"a": "ñ"})
    assert ruta.exists() and "ñ" in ruta.read_text(encoding="utf-8")
