"""Backtest con rebalanceo mensual y aportaciones periódicas.

Convenciones (documentadas para que los resultados sean auditables):

* ``precios``: DataFrame de precios de cierre MENSUALES (una fila por mes), una
  columna por ticker. Las rentabilidades se calculan con ``pct_change``.
* Rebalanceo mensual: cada mes la cartera rinde ``sum(peso_i * r_i)``.
* Los pesos se normalizan para que sumen 1; no se admiten pesos negativos.
* Aportaciones: ``inicial`` se invierte al principio; ``mensual`` se aporta al
  final de cada mes (después de aplicar la rentabilidad de ese mes).
* Costes (TER): si se pasa ``ter_anual`` (fracciones, 0.002 = 0,20 %), cada mes
  se resta ``sum(peso_i * ter_i) / 12`` a la rentabilidad de la cartera.
* Máxima caída: incluye el punto de partida (valor 1 antes del primer mes), de
  modo que una caída en el primer mes también cuenta.
* Meses para recuperar: meses desde el FONDO de la máxima caída hasta volver al
  máximo previo; ``None`` si aún no se ha recuperado.
* Peor / mejor año: solo años naturales completos (12 rentabilidades mensuales).
  Si no hay ninguno completo, se usan los años parciales disponibles y
  ``anios_completos`` vale 0.
"""
import math
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

_EPS = 1e-12


@dataclass
class Resultado:
    nombre: str
    desde: str
    hasta: str
    rentabilidad_anual_pct: float
    volatilidad_pct: float
    max_caida_pct: float
    peor_anio_pct: float
    meses_recuperar_max_caida: int | None
    aportado_eur: float
    valor_final_eur: float
    # Métricas añadidas (con valor por defecto para no romper código existente)
    mejor_anio_pct: float | None = None
    anios_completos: int = 0
    sharpe: float | None = None
    sortino: float | None = None
    meses_positivos_pct: float | None = None
    tasa_libre_riesgo_pct: float = 0.0
    coste_ter_anual_pct: float = 0.0

    def dict(self):
        return asdict(self)


def _validar_pesos(pesos: dict[str, float], precios: pd.DataFrame) -> dict[str, float]:
    if not pesos:
        raise ValueError("La cartera está vacía: indica al menos un ticker con su peso.")
    for t, p in pesos.items():
        if not isinstance(p, (int, float, np.number)) or not math.isfinite(p):
            raise ValueError(f"Peso no válido para {t}: {p!r}.")
        if p < 0:
            raise ValueError(f"Peso negativo para {t} ({p}): no se admiten posiciones cortas.")
    total = sum(pesos.values())
    if total <= 0:
        raise ValueError("Los pesos deben sumar más de 0.")
    faltan = [t for t in pesos if t not in precios.columns]
    if faltan:
        raise ValueError(f"Faltan precios para: {', '.join(faltan)}. "
                         f"Disponibles: {', '.join(map(str, precios.columns))}.")
    return {t: p / total for t, p in pesos.items()}


def _redondear(x: float | None, nd: int = 2) -> float | None:
    if x is None or not math.isfinite(x):
        return None
    return round(float(x), nd)


def simular(nombre: str, pesos: dict[str, float], precios: pd.DataFrame,
            inicial: float = 0, mensual: float = 0, *,
            tasa_libre_riesgo: float = 0.0,
            ter_anual: dict[str, float] | None = None) -> tuple[Resultado, pd.Series]:
    """Simula la cartera. Devuelve (Resultado, serie del valor en euros por mes).

    ``tasa_libre_riesgo``: anual, en fracción (0.02 = 2 %), para Sharpe y Sortino.
    ``ter_anual``: {ticker: TER anual en fracción}; los tickers ausentes cuentan 0.
    """
    if inicial < 0 or mensual < 0:
        raise ValueError("Las aportaciones inicial y mensual no pueden ser negativas.")
    w_dict = _validar_pesos(pesos, precios)
    tickers = list(w_dict)

    rent = precios[tickers].pct_change().iloc[1:]
    if rent.isna().any().any():
        rent = rent.dropna()
    if len(rent) < 2:
        raise ValueError("Se necesitan al menos 3 meses de precios comunes para simular.")

    w = np.array([w_dict[t] for t in tickers])
    ter = sum(w_dict[t] * (ter_anual or {}).get(t, 0.0) for t in tickers)
    r = pd.Series(rent.to_numpy() @ w - ter / 12, index=rent.index)  # rebalanceo mensual

    indice = (1 + r).cumprod()
    anios = len(r) / 12
    cagr = indice.iloc[-1] ** (1 / anios) - 1 if indice.iloc[-1] > 0 else -1.0
    vol = r.std() * np.sqrt(12)

    # Máxima caída, contando el punto de partida (valor 1) como máximo inicial.
    maximo = indice.cummax().clip(lower=1.0)
    caidas = indice / maximo - 1
    max_caida = min(caidas.min(), 0.0)
    if max_caida < 0:
        fondo = caidas.idxmin()
        tras = indice[fondo:]
        rec = tras[tras >= maximo[fondo]]
        meses_rec = None if rec.empty else int((rec.index[0].to_period("M") - fondo.to_period("M")).n)
    else:
        meses_rec = 0

    por_anio = r.groupby(r.index.year)
    anual = (1 + r).groupby(r.index.year).prod() - 1
    completos = anual[por_anio.size() == 12]
    base = completos if len(completos) else anual
    peor, mejor = base.min(), base.max()

    # Sharpe y Sortino anualizados (media de excesos mensuales × 12).
    rf_m = (1 + tasa_libre_riesgo) ** (1 / 12) - 1
    exceso = r - rf_m
    media_anual = exceso.mean() * 12
    sd = exceso.std() * np.sqrt(12)
    sharpe = media_anual / sd if sd > _EPS else None  # evita ruido numérico
    abajo = np.sqrt((np.minimum(exceso, 0) ** 2).mean()) * np.sqrt(12)
    sortino = media_anual / abajo if abajo > _EPS else None

    valor, aportado = float(inicial), float(inicial)
    serie_valor = []
    for x in r:
        valor = valor * (1 + x) + mensual
        aportado += mensual
        serie_valor.append(valor)

    res = Resultado(
        nombre=nombre,
        desde=r.index[0].strftime("%Y-%m"),
        hasta=r.index[-1].strftime("%Y-%m"),
        rentabilidad_anual_pct=round(float(cagr * 100), 2),
        volatilidad_pct=round(float(vol * 100), 2),
        max_caida_pct=round(float(max_caida * 100), 2),
        peor_anio_pct=round(float(peor * 100), 2),
        meses_recuperar_max_caida=meses_rec,
        aportado_eur=round(aportado, 2),
        valor_final_eur=round(valor, 2),
        mejor_anio_pct=round(float(mejor * 100), 2),
        anios_completos=int(len(completos)),
        sharpe=_redondear(sharpe),
        sortino=_redondear(sortino),
        meses_positivos_pct=round(float((r > 0).mean()) * 100, 2),
        tasa_libre_riesgo_pct=round(tasa_libre_riesgo * 100, 4),
        coste_ter_anual_pct=round(ter * 100, 4),
    )
    return res, pd.Series(serie_valor, index=r.index, name=nombre)
