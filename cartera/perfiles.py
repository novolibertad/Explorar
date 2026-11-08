"""Universo de ETFs UCITS, carteras modelo por perfil y cuestionario.

La asignación es por REGLAS, no por IA: resultados reproducibles y auditables.
Tickers de Yahoo Finance (verifica en justetf.com antes de invertir).
"""

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

ORDEN = list(PERFILES)

PREGUNTAS = [
    ("¿Cuándo vas a necesitar este dinero?",
     [("Menos de 3 años", 0), ("3-7 años", 1), ("7-15 años", 2), ("Más de 15 años", 3)]),
    ("Tu cartera cae un 25 % en 3 meses. ¿Qué haces?",
     [("Vendo todo", 0), ("Vendo una parte", 1), ("No toco nada", 2), ("Compro más", 3)]),
    ("¿Experiencia invirtiendo?",
     [("Ninguna", 0), ("Algo (fondos/ETFs)", 1), ("Bastante, he vivido caídas", 2)]),
]


def perfil_por_puntos(puntos: int, colchon: bool) -> str:
    """0-8 puntos -> perfil. Sin colchón de emergencia, nunca más que conservador."""
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
    """'IWDA.AS:60,EUNH.DE:40' -> {'IWDA.AS': 60, 'EUNH.DE': 40}"""
    pesos = {}
    for parte in texto.split(","):
        ticker, peso = parte.split(":")
        pesos[ticker.strip().upper()] = float(peso)
    return pesos


def normalizar(pesos: dict[str, float]) -> dict[str, float]:
    total = sum(pesos.values())
    if total <= 0:
        raise ValueError("Los pesos deben sumar más de 0.")
    return {t: p / total for t, p in pesos.items()}
