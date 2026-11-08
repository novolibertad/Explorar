"""Backtest con rebalanceo mensual y aportaciones periódicas."""
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd


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

    def dict(self):
        return asdict(self)


def simular(nombre: str, pesos: dict[str, float], precios: pd.DataFrame,
            inicial: float = 0, mensual: float = 0) -> tuple[Resultado, pd.Series]:
    rent = precios[list(pesos)].pct_change().dropna()
    w = np.array([pesos[t] for t in rent.columns])
    r = rent.to_numpy() @ w  # rebalanceo mensual a pesos objetivo
    r = pd.Series(r, index=rent.index)

    indice = (1 + r).cumprod()
    anios = len(r) / 12
    cagr = indice.iloc[-1] ** (1 / anios) - 1
    vol = r.std() * np.sqrt(12)

    maximo = indice.cummax()
    caidas = indice / maximo - 1
    fondo = caidas.idxmin()
    tras = indice[fondo:]
    rec = tras[tras >= maximo[fondo]]
    meses_rec = None if rec.empty else int((rec.index[0].to_period("M") - fondo.to_period("M")).n)

    anual = (1 + r).groupby(r.index.year).prod() - 1
    anual = anual[r.groupby(r.index.year).size() == 12]  # solo años completos
    peor = anual.min() if len(anual) else caidas.min()

    valor, aportado = inicial, inicial
    serie_valor = []
    for x in r:
        valor = valor * (1 + x) + mensual
        aportado += mensual
        serie_valor.append(valor)

    res = Resultado(
        nombre=nombre,
        desde=r.index[0].strftime("%Y-%m"),
        hasta=r.index[-1].strftime("%Y-%m"),
        rentabilidad_anual_pct=round(cagr * 100, 2),
        volatilidad_pct=round(vol * 100, 2),
        max_caida_pct=round(caidas.min() * 100, 2),
        peor_anio_pct=round(peor * 100, 2),
        meses_recuperar_max_caida=meses_rec,
        aportado_eur=round(aportado, 2),
        valor_final_eur=round(valor, 2),
    )
    return res, pd.Series(serie_valor, index=r.index, name=nombre)
