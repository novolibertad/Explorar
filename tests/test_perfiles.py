"""Tests de perfiles: parseo de carteras, normalización, cuestionario y TER."""
import pytest

from cartera.perfiles import (PERFILES, PUNTOS_MAX, TER, UNIVERSO, normalizar,
                              parsear_cartera, perfil_por_puntos)


def test_parsear_basico():
    assert parsear_cartera("IWDA.AS:60,EUNH.DE:40") == {"IWDA.AS": 60.0, "EUNH.DE": 40.0}


def test_parsear_espacios_minusculas_porcentaje_y_coma_final():
    assert parsear_cartera("  iwda.as : 60 ,  eunh.de:40%, ") == {"IWDA.AS": 60.0, "EUNH.DE": 40.0}


def test_parsear_decimales():
    assert parsear_cartera("A:33.5,B:66.5") == {"A": 33.5, "B": 66.5}


@pytest.mark.parametrize("texto, mensaje", [
    ("", "vacía"),
    ("   ", "vacía"),
    (",", "vacía"),
    ("IWDA.AS", "Formato esperado"),
    ("IWDA.AS:60:40", "Formato esperado"),
    ("IWDA.AS:abc", "no numérico"),
    ("IWDA.AS:", "no numérico"),
    (":50", "Falta el ticker"),
    ("IWDA.AS:-10", "≥ 0"),
    ("IWDA.AS:nan", "≥ 0"),
    ("A:1,a:2", "repetido"),
    ("A:0,B:0", "sumar más de 0"),
])
def test_parsear_errores(texto, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        parsear_cartera(texto)


def test_normalizar():
    assert normalizar({"A": 60, "B": 40}) == pytest.approx({"A": 0.6, "B": 0.4})
    assert sum(normalizar({"A": 1, "B": 1, "C": 1}).values()) == pytest.approx(1)


@pytest.mark.parametrize("pesos", [{}, {"A": 0}, {"A": -1, "B": 2}, {"A": float("inf")}])
def test_normalizar_errores(pesos):
    with pytest.raises(ValueError):
        normalizar(pesos)


@pytest.mark.parametrize("puntos, perfil", [
    (0, "conservador"), (2, "conservador"),
    (3, "moderado"), (4, "moderado"),
    (5, "dinamico"), (6, "dinamico"),
    (7, "agresivo"), (8, "agresivo"),
])
def test_perfil_por_puntos_limites(puntos, perfil):
    assert perfil_por_puntos(puntos, colchon=True) == perfil


@pytest.mark.parametrize("puntos", range(PUNTOS_MAX + 1))
def test_sin_colchon_siempre_conservador(puntos):
    assert perfil_por_puntos(puntos, colchon=False) == "conservador"


@pytest.mark.parametrize("puntos", [-1, 9, 2.5, True, "3"])
def test_perfil_por_puntos_fuera_de_rango(puntos):
    with pytest.raises(ValueError, match="entre 0 y 8"):
        perfil_por_puntos(puntos, colchon=True)


def test_puntos_max_coincide_con_preguntas():
    from cartera.perfiles import PREGUNTAS
    assert PUNTOS_MAX == sum(max(p for _, p in ops) for _, ops in PREGUNTAS)


def test_perfiles_suman_100_y_usan_universo():
    for nombre, pesos in PERFILES.items():
        assert sum(pesos.values()) == 100, nombre
        assert set(pesos) <= set(UNIVERSO), nombre


def test_ter_cubre_universo_y_es_razonable():
    assert set(TER) == set(UNIVERSO)
    assert all(0 <= t < 0.01 for t in TER.values())  # fracciones, no porcentajes
