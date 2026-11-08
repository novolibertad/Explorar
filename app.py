"""Comparador de carteras indexadas — interfaz web (Streamlit).

Herramienta EDUCATIVA, no asesoramiento financiero personalizado.

Ejecuta:  streamlit run app.py
"""
from __future__ import annotations

import os
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from cartera import backtest, datos
from cartera.perfiles import (ORDEN, PERFILES, PREGUNTAS, UNIVERSO, normalizar,
                              perfil_por_puntos)

from cartera import perfiles as _perfiles

TER: dict = getattr(_perfiles, "TER", {}) or {}

AVISO = ("**Herramienta educativa.** No constituye asesoramiento financiero personalizado "
         "en el sentido de la normativa de la CNMV (MiFID II). Rentabilidades pasadas no "
         "garantizan rentabilidades futuras. Antes de invertir, consulta el folleto y el KID "
         "de cada ETF y, si lo necesitas, a un asesor registrado en la CNMV.")

NOMBRES = {"conservador": "Conservador", "moderado": "Moderado", "dinamico": "Dinámico",
           "agresivo": "Agresivo", "mi_cartera": "Mi cartera"}
COLORES = {"conservador": "#2a9d8f", "moderado": "#457b9d", "dinamico": "#e9c46a",
           "agresivo": "#e76f51", "mi_cartera": "#6a4c93"}

st.set_page_config(page_title="Comparador de carteras indexadas", page_icon="📊",
                   layout="wide", initial_sidebar_state="auto")

st.markdown("""
<style>
.block-container {padding-top: 2rem; padding-bottom: 6rem; max-width: 1200px;}
.aviso-pie {position: fixed; left: 0; right: 0; bottom: 0; z-index: 1000002;
  background: var(--background-color, #fff); border-top: 1px solid rgba(128,128,128,.3);
  padding: .45rem 1rem; font-size: .78rem; line-height: 1.3; text-align: center;
  opacity: .97;}
@media (max-width: 640px) {
  .block-container {padding-left: 1rem; padding-right: 1rem;}
  .aviso-pie {font-size: .7rem; padding: .35rem .6rem;}
  .aviso-largo {display: none;}
}
@media (min-width: 641px) {.aviso-corto {display: none;}}
</style>
""", unsafe_allow_html=True)


def nombre_bonito(n: str) -> str:
    return NOMBRES.get(n, n)


# --------------------------------------------------------------------------- datos
@st.cache_data(ttl=3600, show_spinner="Descargando precios…")
def cargar_precios(tickers: tuple[str, ...], demo: bool) -> pd.DataFrame:
    return datos.precios(list(tickers), demo=demo)


@st.cache_data(ttl=3600, show_spinner=False)
def red_disponible() -> bool:
    """Comprueba una vez si se pueden descargar datos reales."""
    try:
        cargar_precios(tuple(sorted(UNIVERSO)), False)
        return True
    except Exception:  # noqa: BLE001 — sin red, sin yfinance, ticker caído...
        return False


@st.cache_data(ttl=60, show_spinner="Consultando cotizaciones…")
def cargar_cotizaciones(tickers: tuple[str, ...], demo: bool) -> dict:
    return datos.cotizaciones(list(tickers), proveedor="demo" if demo else None)


def caidas(pesos: dict[str, float], precios: pd.DataFrame) -> pd.Series:
    """Caída desde máximos de la cartera (sin efecto de las aportaciones)."""
    rent = precios[list(pesos)].pct_change().dropna()
    r = rent.to_numpy() @ np.array([pesos[t] for t in rent.columns])
    indice = pd.Series((1 + r).cumprod(), index=rent.index)
    return (indice / indice.cummax() - 1) * 100


def eur(x: float) -> str:
    return f"{x:,.0f} €".replace(",", ".")


# --------------------------------------------------------------------------- barra lateral
with st.sidebar:
    st.header("⚙️ Parámetros")
    inicial = st.number_input("Inversión inicial (€)", min_value=0.0, value=10000.0,
                              step=500.0, format="%.0f")
    mensual = st.number_input("Aportación mensual (€)", min_value=0.0, value=0.0,
                              step=50.0, format="%.0f")

    if "demo" not in st.session_state:
        st.session_state.demo = not red_disponible()
    demo = st.toggle("Usar datos de demostración", key="demo",
                     help="Datos sintéticos generados al azar, sin conexión. "
                          "Útiles para probar la herramienta, NO reflejan el mercado real.")

    st.divider()
    st.subheader("🧩 Mi cartera (opcional)")
    usar_propia = st.checkbox("Añadir una cartera propia a la comparación")
    propia: dict[str, float] = {}
    if usar_propia:
        elegidos = st.multiselect("ETFs", list(UNIVERSO), default=["IWDA.AS", "EUNH.DE"],
                                  format_func=lambda t: f"{t} — {UNIVERSO[t].split(' (')[0]}")
        for t in elegidos:
            propia[t] = st.slider(f"{t} (%)", 0, 100, round(100 / len(elegidos)), key=f"w_{t}")
        total = sum(propia.values())
        if elegidos:
            if total == 0:
                st.error("Los pesos deben sumar más de 0 %.")
            elif total != 100:
                st.caption(f"Suma: {total} %. Se reescalará al 100 %.")
            else:
                st.caption("Suma: 100 % ✓")
        propia = {t: p for t, p in propia.items() if p > 0}

# --------------------------------------------------------------------------- carga
carteras = {n: normalizar(p) for n, p in PERFILES.items()}
if propia:
    carteras["mi_cartera"] = normalizar(propia)
tickers = tuple(sorted({t for p in carteras.values() for t in p}))

st.title("📊 Comparador de carteras indexadas")
st.caption("Compara carteras modelo de ETFs UCITS por perfil de riesgo con un backtest histórico "
           "con rebalanceo mensual.")

try:
    precios = cargar_precios(tickers, demo)
except Exception as e:  # noqa: BLE001
    st.error(f"No se han podido descargar datos reales ({e}). Se usan datos de demostración.")
    demo = True
    precios = cargar_precios(tickers, True)

if demo:
    st.warning("⚠️ **MODO DEMO:** estás viendo datos **sintéticos**, no precios reales de mercado. "
               "Las cifras sirven solo para entender la herramienta.")

resultados, series = [], {}
for n, p in carteras.items():
    r, s = backtest.simular(n, p, precios, inicial, mensual, ter_anual=TER)
    resultados.append(r)
    series[n] = s

perfil_usuario = st.session_state.get("perfil")

tab_perfil, tab_comp, tab_cot = st.tabs(["🧭 Mi perfil", "📈 Comparar", "💹 Cotizaciones"])

# --------------------------------------------------------------------------- Mi perfil
with tab_perfil:
    st.subheader("Cuestionario de perfil")
    st.write("Responde con sinceridad. La asignación se hace por **reglas fijas**, no por IA, "
             "para que sea reproducible.")
    col_q, col_r = st.columns([3, 2], gap="large")
    with col_q:
        puntos = 0
        for i, (texto, opciones) in enumerate(PREGUNTAS):
            etiquetas = [o for o, _ in opciones]
            elegida = st.radio(f"**{i + 1}. {texto}**", etiquetas, key=f"p{i}", index=None)
            if elegida is not None:
                puntos += dict(opciones)[elegida]
        colchon_r = st.radio(f"**{len(PREGUNTAS) + 1}. ¿Tienes 3-6 meses de gastos ahorrados aparte "
                             "(colchón de emergencia)?**", ["Sí", "No"], key="colchon", index=None)
        completo = all(st.session_state.get(f"p{i}") is not None for i in range(len(PREGUNTAS))) \
            and colchon_r is not None

    with col_r:
        if not completo:
            st.info("Contesta todas las preguntas para ver tu perfil.")
        else:
            perfil = perfil_por_puntos(puntos, colchon_r == "Sí")
            st.session_state.perfil = perfil_usuario = perfil
            st.metric("Tu perfil", nombre_bonito(perfil), help=f"{puntos} puntos")
            if colchon_r == "No":
                st.caption("Sin colchón de emergencia el perfil se limita a conservador: "
                           "primero conviene tener ese ahorro aparte.")
            pesos = PERFILES[perfil]
            df = pd.DataFrame({"ETF": list(pesos), "Peso": list(pesos.values())})
            df["Descripción"] = df["ETF"].map(UNIVERSO)
            fig = px.pie(df, names="ETF", values="Peso", hole=0.55,
                         hover_data=["Descripción"],
                         color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_traces(textinfo="percent", textposition="inside")
            fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.05), margin=dict(t=10, b=10, l=10, r=10), height=360,
                              annotations=[dict(text=nombre_bonito(perfil), showarrow=False,
                                                font_size=16)])
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            tabla_p = df[["ETF", "Peso", "Descripción"]].assign(Peso=df["Peso"].map(lambda x: f"{x} %"))
            if TER:
                tabla_p["TER"] = tabla_p["ETF"].map(lambda t: f"{TER[t] * 100:.2f} %" if t in TER else "—")
            st.dataframe(tabla_p, hide_index=True, width="stretch")

# --------------------------------------------------------------------------- Comparar
with tab_comp:
    r0 = resultados[0]
    st.subheader("Resultados del backtest")
    st.caption(f"Periodo: {r0.desde} → {r0.hasta} · Inicial {eur(inicial)} · "
               f"Mensual {eur(mensual)} · Aportado en total {eur(r0.aportado_eur)}")

    filas = []
    for r in resultados:
        filas.append({
            "Cartera": ("⭐ " if r.nombre == perfil_usuario else "") + nombre_bonito(r.nombre),
            "Rent./año": r.rentabilidad_anual_pct,
            "Volatilidad": r.volatilidad_pct,
            "Máx. caída": r.max_caida_pct,
            "Peor año": r.peor_anio_pct,
            "Recuperación": (f"{r.meses_recuperar_max_caida} meses"
                             if r.meses_recuperar_max_caida is not None else "Sin recuperar"),
            "Valor final": r.valor_final_eur,
        })
    st.dataframe(
        pd.DataFrame(filas), hide_index=True, width="stretch",
        column_config={
            "Rent./año": st.column_config.NumberColumn(format="%.1f %%"),
            "Volatilidad": st.column_config.NumberColumn(format="%.1f %%"),
            "Máx. caída": st.column_config.NumberColumn(format="%.1f %%"),
            "Peor año": st.column_config.NumberColumn(format="%.1f %%"),
            "Recuperación": st.column_config.TextColumn(
                help="Meses hasta recuperar la máxima caída"),
            "Valor final": st.column_config.NumberColumn(format="%.0f €"),
        })
    if perfil_usuario:
        st.caption("⭐ = tu perfil según el cuestionario.")

    valores = pd.DataFrame(series)
    fig_v = go.Figure()
    for n in valores:
        fig_v.add_scatter(x=valores.index, y=valores[n], name=nombre_bonito(n), mode="lines",
                          line=dict(color=COLORES.get(n), width=3 if n == perfil_usuario else 2),
                          hovertemplate="%{x|%b %Y}: %{y:,.0f} €<extra>" + nombre_bonito(n) + "</extra>")
    if mensual or inicial:
        aport = pd.Series(inicial + mensual * np.arange(1, len(valores) + 1), index=valores.index)
        fig_v.add_scatter(x=aport.index, y=aport, name="Aportado", mode="lines",
                          line=dict(color="gray", dash="dot"), hovertemplate="%{y:,.0f} €")
    fig_v.update_layout(title="Valor de la cartera", yaxis_title="€", height=420,
                        hovermode="x unified", margin=dict(t=50, b=10, l=10, r=10),
                        legend=dict(orientation="h", y=-0.15), separators=",.")
    st.plotly_chart(fig_v, width="stretch")

    fig_d = go.Figure()
    for n, p in carteras.items():
        dd = caidas(p, precios)
        fig_d.add_scatter(x=dd.index, y=dd, name=nombre_bonito(n), mode="lines",
                          line=dict(color=COLORES.get(n)), fill="tozeroy" if n == perfil_usuario else None,
                          hovertemplate="%{x|%b %Y}: %{y:.1f} %<extra>" + nombre_bonito(n) + "</extra>")
    fig_d.update_layout(title="Caída desde máximos (drawdown)", yaxis_title="%", height=340,
                        hovermode="x unified", margin=dict(t=50, b=10, l=10, r=10),
                        legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig_d, width="stretch")

    with st.expander("¿Qué significa cada métrica?"):
        st.markdown(
            "- **Rent./año**: crecimiento anual compuesto de la cartera (sin contar aportaciones).\n"
            "- **Volatilidad**: cuánto oscila al año; más alta = más sustos.\n"
            "- **Máx. caída**: la peor bajada desde un máximo. Piensa en euros: "
            f"con {eur(inicial)} invertidos, un −30 % son {eur(inicial * 0.3)} menos.\n"
            "- **Peor año**: el peor año natural completo.\n"
            "- **Recuperación**: meses que tardó en volver al máximo previo.\n"
            "- Incluye el TER aproximado de cada ETF; no incluye comisiones del bróker ni impuestos.")

    st.divider()
    st.subheader("🤖 Explicación en lenguaje claro")
    if st.button("Explícamelo con IA", type="primary"):
        clave = os.environ.get("ANTHROPIC_API_KEY")
        if not clave:
            try:
                clave = st.secrets.get("ANTHROPIC_API_KEY")
            except Exception:  # noqa: BLE001 — sin secrets.toml
                clave = None
            if clave:
                os.environ["ANTHROPIC_API_KEY"] = clave
        if not clave:
            st.info("Para usar la explicación con IA configura la variable de entorno "
                    "`ANTHROPIC_API_KEY` (o en `.streamlit/secrets.toml`) y reinicia la app.")
        else:
            try:
                from cartera.asesor import explicar
                with st.spinner("Pensando…"):
                    e = explicar([r.dict() for r in resultados], perfil_usuario)
                st.session_state.explicacion = e.model_dump()
            except ImportError:
                st.error("Falta el paquete `anthropic`. Instálalo con `pip install -r requirements.txt`.")
            except Exception as err:  # noqa: BLE001
                st.error(f"No se pudo generar la explicación: {err}")
    e = st.session_state.get("explicacion")
    if e:
        st.write(e["resumen"])
        st.markdown(f"**La caída en tu caso:** {e['que_significa_la_caida']}")
        c1, c2, c3 = st.columns(3)
        for col, titulo, clave in [(c1, "✅ Puntos fuertes", "puntos_fuertes"),
                                   (c2, "⚠️ Riesgos", "riesgos"),
                                   (c3, "❓ Pregúntate", "preguntas_para_hacerte")]:
            col.markdown(f"**{titulo}**\n" + "\n".join(f"- {i}" for i in e[clave]))
        st.caption("Texto generado por IA con fines educativos; puede contener errores.")

# --------------------------------------------------------------------------- Cotizaciones
with tab_cot:
    st.subheader("Cotizaciones")
    if not hasattr(datos, "cotizaciones"):
        st.info("Las cotizaciones en directo no están disponibles en esta versión.")
    else:
        auto = st.toggle("Auto-actualizar cada 60 s", value=False)

        @st.fragment(run_every=60 if auto else None)
        def panel_cotizaciones():
            if st.button("🔄 Actualizar ahora") or auto:
                cargar_cotizaciones.clear()
            try:
                cot = cargar_cotizaciones(tuple(sorted(UNIVERSO)), demo)
            except Exception as err:  # noqa: BLE001
                st.warning(f"No se pudieron obtener cotizaciones: {err}")
                return
            filas = []
            for t, q in cot.items():
                q = q or {}
                retraso = q.get("retraso_min")
                filas.append({
                    "ETF": t,
                    "Nombre": UNIVERSO.get(t, "").split(" (")[0],
                    "Precio": q.get("precio"),
                    "Moneda": q.get("moneda", ""),
                    "Hora": str(q.get("hora", "") or ""),
                    "Retraso": "—" if retraso is None else
                               ("Tiempo real" if retraso == 0 else f"~{retraso} min"),
                    "Fuente": q.get("fuente", ""),
                })
            st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch",
                         column_config={"Precio": st.column_config.NumberColumn(format="%.2f")})
            st.caption(f"Consultado: {datetime.now():%d/%m/%Y %H:%M:%S}. Las cotizaciones pueden "
                       "tener retraso según la fuente; no las uses para operar.")

        panel_cotizaciones()

AVISO_CORTO = ("Herramienta educativa, no es asesoramiento personalizado (CNMV). "
               "Rentabilidades pasadas no garantizan futuras.")
st.markdown(f'<div class="aviso-pie">⚖️ <span class="aviso-largo">{AVISO.replace("**", "")}</span>'
            f'<span class="aviso-corto">{AVISO_CORTO}</span></div>', unsafe_allow_html=True)
