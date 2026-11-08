"""Tests del backtest con valores calculados a mano (datos sintéticos, sin red)."""
import math

import numpy as np
import pandas as pd
import pytest

from cartera.backtest import Resultado, simular

A = pytest.approx


def precios_desde(rentabilidades: dict[str, list[float]], inicio="2019-12-31", base=100.0):
    """Construye precios mensuales (freq='ME') a partir de rentabilidades mensuales."""
    n = len(next(iter(rentabilidades.values())))
    idx = pd.date_range(inicio, periods=n + 1, freq="ME")
    return pd.DataFrame({t: base * np.cumprod([1.0] + [1 + x for x in rs])
                         for t, rs in rentabilidades.items()}, index=idx)


def serie_precios(valores, inicio="2019-12-31", ticker="X"):
    return pd.DataFrame({ticker: valores}, index=pd.date_range(inicio, periods=len(valores), freq="ME"))


# --- Rentabilidad, volatilidad, Sharpe, Sortino -------------------------------------------

def test_cagr_rentabilidad_constante():
    px = precios_desde({"X": [0.01] * 24})
    res, _ = simular("x", {"X": 1}, px, inicial=1000)
    assert res.rentabilidad_anual_pct == A((1.01 ** 12 - 1) * 100, abs=0.01)  # 12.68 %
    assert res.volatilidad_pct == 0
    assert res.max_caida_pct == 0
    assert res.meses_recuperar_max_caida == 0
    assert res.meses_positivos_pct == 100
    assert res.sharpe is None  # volatilidad 0 -> Sharpe no definido
    assert res.desde == "2020-01" and res.hasta == "2021-12"


def test_cagr_21_por_ciento_en_dos_anios_es_10_anual():
    px = serie_precios([100 * 1.21 ** (i / 24) for i in range(25)])
    res, _ = simular("x", {"X": 1}, px)
    assert res.rentabilidad_anual_pct == A(10.0, abs=0.01)


def test_volatilidad_y_sharpe():
    # r = [2 %, 0, 2 %, 0]: media 1 %, sd muestral 0,011547 -> anual 0,04 exacto.
    px = precios_desde({"X": [0.02, 0.0, 0.02, 0.0]})
    res, _ = simular("x", {"X": 1}, px)
    assert res.volatilidad_pct == A(4.0, abs=0.01)
    assert res.sharpe == A(3.0, abs=0.01)  # 0,12 / 0,04
    assert res.sortino is None  # ningún mes por debajo de 0
    assert res.meses_positivos_pct == 50  # los meses a 0 no cuentan como positivos


def test_sortino_y_meses_positivos():
    # r = [3 %, -1 %, 3 %, -1 %]: media anual 0,12; sd anual 0,08; desviación bajista
    # sqrt((0,01² + 0,01²) / 4) * sqrt(12) = 0,0244949
    px = precios_desde({"X": [0.03, -0.01, 0.03, -0.01]})
    res, _ = simular("x", {"X": 1}, px)
    assert res.sharpe == A(1.5, abs=0.01)
    assert res.sortino == A(0.12 / (math.sqrt(5e-5) * math.sqrt(12)), abs=0.01)  # 4.90
    assert res.meses_positivos_pct == 50


def test_sharpe_con_tasa_libre_riesgo():
    px = precios_desde({"X": [0.03, -0.01, 0.03, -0.01]})
    rf = 1.005 ** 12 - 1  # 0,5 % mensual
    res, _ = simular("x", {"X": 1}, px, tasa_libre_riesgo=rf)
    assert res.sharpe == A(0.75, abs=0.01)  # (0,01 - 0,005)·12 / 0,08
    assert res.tasa_libre_riesgo_pct == A(rf * 100, abs=1e-3)


# --- Máxima caída y recuperación --------------------------------------------------------

def test_max_caida_y_recuperacion():
    # pico 110, fondo 88 (-20 %), recupera (115 >= 110) 2 meses después del fondo
    res, _ = simular("x", {"X": 1}, serie_precios([100, 110, 88, 99, 115]))
    assert res.max_caida_pct == A(-20.0, abs=0.01)
    assert res.meses_recuperar_max_caida == 2


def test_max_caida_sin_recuperar():
    res, _ = simular("x", {"X": 1}, serie_precios([100, 110, 88, 99]))
    assert res.max_caida_pct == A(-20.0, abs=0.01)
    assert res.meses_recuperar_max_caida is None


def test_max_caida_cuenta_desde_el_punto_de_partida():
    # Cae el primer mes: la caída se mide desde el valor inicial (100), no desde 90.
    res, _ = simular("x", {"X": 1}, serie_precios([100, 90, 95, 100.5]))
    assert res.max_caida_pct == A(-10.0, abs=0.01)
    assert res.meses_recuperar_max_caida == 2


# --- Años naturales ---------------------------------------------------------------------

def test_peor_y_mejor_anio_solo_anios_completos():
    # 2020 completo a +1 %/mes; 2021 solo ene-jun a -5 %/mes (parcial, se excluye)
    px = precios_desde({"X": [0.01] * 12 + [-0.05] * 6})
    res, _ = simular("x", {"X": 1}, px)
    esperado = (1.01 ** 12 - 1) * 100
    assert res.peor_anio_pct == A(esperado, abs=0.01)
    assert res.mejor_anio_pct == A(esperado, abs=0.01)
    assert res.anios_completos == 1


def test_peor_y_mejor_anio_dos_anios_completos():
    px = precios_desde({"X": [0.01] * 12 + [-0.01] * 12})
    res, _ = simular("x", {"X": 1}, px)
    assert res.peor_anio_pct == A((0.99 ** 12 - 1) * 100, abs=0.01)  # -11.36
    assert res.mejor_anio_pct == A((1.01 ** 12 - 1) * 100, abs=0.01)  # 12.68
    assert res.anios_completos == 2


def test_primer_anio_empieza_en_enero_si_hay_precio_de_diciembre():
    # Precios desde ene-2020: rentabilidades feb-dic 2020 (11) -> 2020 NO es completo.
    px = precios_desde({"X": [0.01] * 11 + [-0.01] * 12}, inicio="2020-01-31")
    res, _ = simular("x", {"X": 1}, px)
    assert res.anios_completos == 1
    assert res.peor_anio_pct == res.mejor_anio_pct == A((0.99 ** 12 - 1) * 100, abs=0.01)


def test_peor_anio_sin_anios_completos_usa_parciales():
    # oct-dic 2020 a +1 %, ene-mar 2021 a -1 %
    px = precios_desde({"X": [0.01] * 3 + [-0.01] * 3}, inicio="2020-09-30")
    res, _ = simular("x", {"X": 1}, px)
    assert res.anios_completos == 0
    assert res.peor_anio_pct == A((0.99 ** 3 - 1) * 100, abs=0.01)  # -2.97
    assert res.mejor_anio_pct == A((1.01 ** 3 - 1) * 100, abs=0.01)  # 3.03


# --- Aportaciones y rebalanceo ----------------------------------------------------------

def test_aportaciones_periodicas():
    px = precios_desde({"X": [0.10, -0.10, 0.05]})
    res, serie = simular("x", {"X": 1}, px, inicial=1000, mensual=100)
    # 1000·1,1+100 = 1200; 1200·0,9+100 = 1180; 1180·1,05+100 = 1339
    assert list(serie.round(6)) == [1200, 1180, 1339]
    assert res.valor_final_eur == A(1339)
    assert res.aportado_eur == A(1300)
    assert serie.name == "x" and len(serie) == 3


def test_rebalanceo_mensual():
    # A +10 %/mes, B 0 %: con rebalanceo la cartera gana 5 % cada mes -> 1,05² = 1,1025
    # (sin rebalanceo serían (1,21 + 1)/2 = 1,105)
    px = precios_desde({"A": [0.10, 0.10], "B": [0.0, 0.0]})
    res, _ = simular("ab", {"A": 0.5, "B": 0.5}, px, inicial=1000)
    assert res.valor_final_eur == A(1102.50)


def test_pesos_se_normalizan():
    px = precios_desde({"A": [0.10, 0.10], "B": [0.0, 0.0]})
    r1, s1 = simular("ab", {"A": 3, "B": 2}, px, inicial=1000)
    r2, s2 = simular("ab", {"A": 0.6, "B": 0.4}, px, inicial=1000)
    assert r1.valor_final_eur == r2.valor_final_eur == A(1000 * 1.06 ** 2)
    pd.testing.assert_series_equal(s1, s2)


def test_columnas_extra_no_afectan():
    px = precios_desde({"A": [0.01, 0.02], "Z": [0.5, -0.5]})
    res, _ = simular("a", {"A": 1}, px, inicial=100)
    assert res.valor_final_eur == A(100 * 1.01 * 1.02)


# --- Costes (TER) -----------------------------------------------------------------------

def test_ter_resta_un_doceavo_al_mes():
    px = precios_desde({"X": [0.01] * 12})
    res, _ = simular("x", {"X": 1}, px, inicial=1000, ter_anual={"X": 0.012})
    assert res.valor_final_eur == A(1000 * 1.009 ** 12, abs=0.01)
    assert res.coste_ter_anual_pct == A(1.2)


def test_ter_ponderado_y_tickers_sin_ter():
    px = precios_desde({"A": [0.0, 0.0], "B": [0.0, 0.0]})
    res, _ = simular("ab", {"A": 1, "B": 1}, px, inicial=1000, ter_anual={"A": 0.012})
    # drag = 0,5·0,012/12 = 0,0005 al mes
    assert res.coste_ter_anual_pct == A(0.6)
    assert res.valor_final_eur == A(1000 * 0.9995 ** 2, abs=0.01)


def test_sin_ter_igual_que_antes():
    px = precios_desde({"X": [0.01, 0.02, -0.01]})
    r1, _ = simular("x", {"X": 1}, px, 1000)
    r2, _ = simular("x", {"X": 1}, px, 1000, ter_anual=None)
    assert r1 == r2 and r1.coste_ter_anual_pct == 0


# --- Compatibilidad y errores -----------------------------------------------------------

def test_compatibilidad_firma_y_campos():
    px = precios_desde({"X": [0.01, 0.02, -0.01]})
    res, serie = simular("x", {"X": 1}, px, 1000, 50)  # posicional, como en cartera.py
    assert isinstance(res, Resultado) and isinstance(serie, pd.Series)
    campos = {"nombre", "desde", "hasta", "rentabilidad_anual_pct", "volatilidad_pct",
              "max_caida_pct", "peor_anio_pct", "meses_recuperar_max_caida",
              "aportado_eur", "valor_final_eur"}
    assert campos <= set(res.dict())


def test_ticker_sin_precios_da_error_claro():
    px = precios_desde({"A": [0.01, 0.02]})
    with pytest.raises(ValueError, match="Faltan precios para: B"):
        simular("x", {"A": 1, "B": 1}, px)


@pytest.mark.parametrize("pesos, mensaje", [
    ({"A": 0, "B": 0}, "sumar más de 0"),
    ({"A": 1, "B": -0.5}, "negativo"),
    ({}, "vacía"),
    ({"A": float("nan")}, "no válido"),
])
def test_pesos_invalidos(pesos, mensaje):
    px = precios_desde({"A": [0.01, 0.02], "B": [0.0, 0.0]})
    with pytest.raises(ValueError, match=mensaje):
        simular("x", pesos, px)


@pytest.mark.parametrize("n_precios", [0, 1, 2])
def test_pocos_datos(n_precios):
    px = serie_precios([100.0, 101.0, 102.0][:n_precios])
    with pytest.raises(ValueError, match="al menos 3 meses"):
        simular("x", {"X": 1}, px)


def test_aportaciones_negativas():
    px = precios_desde({"X": [0.01, 0.02]})
    with pytest.raises(ValueError, match="negativas"):
        simular("x", {"X": 1}, px, inicial=-1)
