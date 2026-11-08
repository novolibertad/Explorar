"""Universo de ETFs UCITS, carteras modelo por perfil y cuestionario.

La asignación es por REGLAS, no por IA: resultados reproducibles y auditables.
Tickers de Yahoo Finance (verifica en justetf.com antes de invertir).
"""
import math

UNIVERSO = {
    "IWDA.AS": "iShares Core MSCI World (acciones países desarrollados)",
    "EIMI.AS": "iShares Core MSCI EM IMI (acciones emergentes)",
    "EUNH.DE": "iShares Core Euro Government Bond (bonos de gobiernos euro)",
    "XEON.DE": "Xtrackers EUR Overnight Rate Swap (monetario, casi sin riesgo)",
    "4GLD.DE": "Xetra-Gold (oro físico)",
}

PERFILES = {
    "conservador": {"IWDA.AS": 25, "EUNH.DE": 45, "XEON.DE": 25, "4GLD.DE": 5},
    "moderado": {"IWDA.AS": 45, "EIMI.AS": 5, "EUNH.DE": 40, "4GLD.DE": 10},
    "dinamico": {"IWDA.AS": 65, "EIMI.AS": 10, "EUNH.DE": 15, "4GLD.DE": 10},
    "agresivo": {"IWDA.AS": 80, "EIMI.AS": 20},
}

# TER (gastos corrientes anuales) APROXIMADOS, en fracción (0.002 = 0,20 %).
# Valores orientativos tomados de las fichas públicas de los emisores; pueden
# cambiar: compruébalos en justetf.com o en el KID del ETF antes de invertir.
TER = {
    "IWDA.AS": 0.0020,  # iShares Core MSCI World: ~0,20 %
    "EIMI.AS": 0.0018,  # iShares Core MSCI EM IMI: ~0,18 %
    "EUNH.DE": 0.0007,  # iShares Core Euro Government Bond: ~0,07 %
    "XEON.DE": 0.0010,  # Xtrackers EUR Overnight Rate Swap: ~0,10 %
    "4GLD.DE": 0.0000,  # Xetra-Gold: sin TER (ETC; puede haber otros costes de custodia)
}

ORDEN = list(PERFILES)

PUNTOS_MAX = 8

PREGUNTAS = [
    ("¿Cuándo vas a necesitar este dinero?",
     [("Menos de 3 años", 0), ("3-7 años", 1), ("7-15 años", 2), ("Más de 15 años", 3)]),
    ("Tu cartera cae un 25 % en 3 meses. ¿Qué haces?",
     [("Vendo todo", 0), ("Vendo una parte", 1), ("No toco nada", 2), ("Compro más", 3)]),
    ("¿Experiencia invirtiendo?",
     [("Ninguna", 0), ("Algo (fondos/ETFs)", 1), ("Bastante, he vivido caídas", 2)]),
]


def perfil_por_puntos(puntos: int, colchon: bool) -> str:
    """0-8 puntos -> perfil. Sin colchón de emergencia, nunca más que conservador.

    Tramos: 0-2 conservador, 3-4 moderado, 5-6 dinámico, 7-8 agresivo.
    """
    if isinstance(puntos, bool) or not isinstance(puntos, int) or not 0 <= puntos <= PUNTOS_MAX:
        raise ValueError(f"Los puntos deben ser un entero entre 0 y {PUNTOS_MAX} (recibido: {puntos!r}).")
    if not colchon:
        return "conservador"
    if puntos <= 2:
        return "conservador"
    if puntos <= 4:
        return "moderado"
    if puntos <= 6:
        return "dinamico"
    return "agresivo"


def cuestionario() -> str:
    puntos = 0
    for texto, opciones in PREGUNTAS:
        print(f"\n{texto}")
        for i, (op, _) in enumerate(opciones, 1):
            print(f"  {i}. {op}")
        while True:
            r = input("> ").strip()
            if r.isdigit() and 1 <= int(r) <= len(opciones):
                puntos += opciones[int(r) - 1][1]
                break
            print("Elige un número de la lista.")
    colchon = input("\n¿Tienes 3-6 meses de gastos ahorrados aparte? (s/n) > ").strip().lower().startswith("s")
    return perfil_por_puntos(puntos, colchon)


def parsear_cartera(texto: str) -> dict[str, float]:
    """'IWDA.AS:60,EUNH.DE:40' -> {'IWDA.AS': 60.0, 'EUNH.DE': 40.0}

    Tolera espacios, minúsculas, un '%' tras el peso y una coma final.
    Lanza ValueError (en español) si el formato no es válido.
    """
    formato = 'Formato esperado: "TICKER:peso,TICKER:peso" (ej. "IWDA.AS:60,EUNH.DE:40").'
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError(f"Cartera vacía. {formato}")
    pesos: dict[str, float] = {}
    for parte in texto.split(","):
        parte = parte.strip()
        if not parte:
            continue
        if parte.count(":") != 1:
            raise ValueError(f"Fragmento no válido: '{parte}'. {formato}")
        ticker, peso = (x.strip() for x in parte.split(":"))
        ticker = ticker.upper()
        if not ticker:
            raise ValueError(f"Falta el ticker en '{parte}'. {formato}")
        try:
            valor = float(peso.rstrip("%").strip())
        except ValueError:
            raise ValueError(f"Peso no numérico para {ticker}: '{peso}'. {formato}") from None
        if not math.isfinite(valor) or valor < 0:
            raise ValueError(f"Peso no válido para {ticker}: '{peso}' (debe ser un número ≥ 0).")
        if ticker in pesos:
            raise ValueError(f"Ticker repetido: {ticker}.")
        pesos[ticker] = valor
    if not pesos:
        raise ValueError(f"Cartera vacía. {formato}")
    if sum(pesos.values()) <= 0:
        raise ValueError("Los pesos deben sumar más de 0.")
    return pesos


def normalizar(pesos: dict[str, float]) -> dict[str, float]:
    """Escala los pesos para que sumen 1. Sin pesos negativos ni suma 0."""
    if not pesos:
        raise ValueError("La cartera está vacía.")
    for t, p in pesos.items():
        if not math.isfinite(p) or p < 0:
            raise ValueError(f"Peso no válido para {t}: {p} (debe ser un número ≥ 0).")
    total = sum(pesos.values())
    if total <= 0:
        raise ValueError("Los pesos deben sumar más de 0.")
    return {t: p / total for t, p in pesos.items()}
