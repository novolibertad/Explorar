"""Comparador de carteras indexadas con IA (herramienta EDUCATIVA, no asesoramiento).

Uso:
  python cartera.py perfil                              # cuestionario -> tu perfil y su cartera
  python cartera.py comparar                            # los 4 perfiles, mismo periodo
  python cartera.py comparar --cartera "IWDA.AS:70,EUNH.DE:30"   # añade una cartera tuya
  python cartera.py comparar --inicial 5000 --mensual 200 --explicar --perfil moderado

Opciones: --inicial EUR  --mensual EUR  --explicar (IA)  --demo (datos sintéticos, sin red)
"""
import argparse
import sys

from cartera import backtest, datos
from cartera.perfiles import ORDEN, PERFILES, TER, UNIVERSO, cuestionario, normalizar, parsear_cartera

AVISO = ("Aviso: herramienta educativa. Rentabilidades pasadas no garantizan futuras. "
         "No es asesoramiento financiero personalizado.")


def mostrar_cartera(nombre: str, pesos: dict[str, float]):
    print(f"\nCartera '{nombre}':")
    for t, p in pesos.items():
        print(f"  {p * 100:5.1f} %  {t:8}  {UNIVERSO.get(t, '')}")


def tabla(resultados: list[backtest.Resultado]):
    r0 = resultados[0]
    print(f"\nPeriodo: {r0.desde} → {r0.hasta}")
    cab = f"{'Cartera':<14}{'Rent/año':>9}{'Volat.':>8}{'Máx caída':>10}{'Peor año':>9}{'Recup.':>8}{'Sharpe':>7}{'Valor final':>13}"
    print(cab + "\n" + "-" * len(cab))
    for r in resultados:
        sharpe = f"{r.sharpe:.2f}" if r.sharpe is not None else "—"
        rec = f"{r.meses_recuperar_max_caida}m" if r.meses_recuperar_max_caida is not None else "—"
        print(f"{r.nombre:<14}{r.rentabilidad_anual_pct:>8.1f}%{r.volatilidad_pct:>7.1f}%"
              f"{r.max_caida_pct:>9.1f}%{r.peor_anio_pct:>8.1f}%{rec:>8}{sharpe:>7}{r.valor_final_eur:>12,.0f}€")
    print("Resultados netos de TER aproximado de cada ETF.")
    print("Recup. = meses hasta recuperar la máxima caída (— = aún sin recuperar)")
    if r0.aportado_eur:
        print(f"Aportado en total: {r0.aportado_eur:,.0f} €")


def ejecutar(carteras: dict[str, dict[str, float]], args, perfil: str | None):
    tickers = sorted({t for p in carteras.values() for t in p})
    px = datos.precios(tickers, demo=args.demo)
    if args.demo:
        print("⚠️  MODO DEMO: datos sintéticos, no reales.")
    resultados = [backtest.simular(n, p, px, args.inicial, args.mensual, ter_anual=TER)[0] for n, p in carteras.items()]
    tabla(resultados)
    salida = {"perfil": perfil, "resultados": [r.dict() for r in resultados], "carteras": carteras}
    if args.explicar:
        from cartera.asesor import explicar  # importa anthropic solo si se usa

        e = explicar(salida["resultados"], perfil)
        print(f"\n{e.resumen}\n\nLa caída en tu caso: {e.que_significa_la_caida}")
        for titulo, items in [("✅ Fuertes", e.puntos_fuertes), ("⚠️ Riesgos", e.riesgos),
                              ("❓ Pregúntate", e.preguntas_para_hacerte)]:
            print(f"\n{titulo}:\n" + "\n".join(f"  - {i}" for i in items))
        salida["explicacion"] = e.model_dump()
    print(f"\n{AVISO}\nGuardado en {datos.guardar('cartera', salida)}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("comando", choices=["perfil", "comparar"])
    ap.add_argument("--cartera", help='Cartera propia: "TICKER:peso,TICKER:peso"')
    ap.add_argument("--perfil", choices=ORDEN)
    ap.add_argument("--inicial", type=float, default=10000)
    ap.add_argument("--mensual", type=float, default=0)
    ap.add_argument("--explicar", action="store_true")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args(argv)

    if args.comando == "perfil":
        perfil = cuestionario()
        print(f"\nTu perfil: {perfil.upper()}")
        carteras = {perfil: normalizar(PERFILES[perfil])}
        mostrar_cartera(perfil, carteras[perfil])
    else:
        perfil = args.perfil
        carteras = {n: normalizar(p) for n, p in PERFILES.items()}
        if args.cartera:
            carteras["mi_cartera"] = normalizar(parsear_cartera(args.cartera))
            mostrar_cartera("mi_cartera", carteras["mi_cartera"])
    ejecutar(carteras, args, perfil)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as e:
        sys.exit(f"Error: {e}")
