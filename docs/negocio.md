# Negocio y marco legal (España, nov. 2026)

> Resumen práctico, no es asesoramiento jurídico. Las cifras marcadas con **(est.)** son estimaciones o no están confirmadas en fuente oficial. Antes de lanzar, conviene una consulta de 1–2 h con un abogado de regulación financiera (≈300–600 € est.).

## 1. Línea regulatoria

**Qué es asesoramiento (LMV Ley 6/2023 + MiFID II):** una *recomendación personalizada* sobre un *instrumento concreto* (comprar, vender, mantener… incluso "no compres X") basada en las *circunstancias del usuario* o presentada como idónea para él. Lo genérico y no personalizado no es asesoramiento ([CNMV](https://www.cnmv.es/portal/Inversor/Asesoramiento), [ficha EAFI](https://cnmv.es/DocPortal/Publicaciones/Fichas/GR04_EAFI.PDF)).

| Puede (educativo) | No puede sin licencia |
|---|---|
| Backtest de carteras **que elige el usuario** | "Con tu perfil/edad/objetivo te conviene esta cartera" |
| Comparar métricas históricas (CAGR, volatilidad, drawdown, TER) | Cuestionario de riesgo → cartera recomendada con ISIN |
| Explicar con IA qué significa cada métrica | IA que responde "¿compro IWDA ahora?" con sí/no |
| Carteras modelo genéricas y públicas ("60/40 clásica"), igual para todos | Alertas "vende/compra" individualizadas |

- **IA:** el LLM es el mayor riesgo, porque puede personalizar sin que tú quieras. Pon un system prompt que se niegue a recomendar, filtra la salida y guarda registros. ESMA avisa de las alucinaciones y de que la responsabilidad no se delega en la IA ([ESMA 2024](https://www.esma.europa.eu/sites/default/files/2024-05/ESMA35-335435667-5924__Public_Statement_on_AI_and_investment_services.pdf)). El AI Act exige avisar al usuario de que habla con una IA (art. 50, aplicable desde ago. 2026).
- **Disclaimer** visible: "Información educativa, rentabilidades pasadas no garantizan futuras, no es asesoramiento". Ayuda, pero **no te protege si en la práctica personalizas**.

**Licencia propia o socio:**

| Vía | Requisitos | Coste/tiempo (est.) |
|---|---|---|
| EAF (sociedad) | Capital inicial 75.000 € (RD 813/2023), consejo idóneo, cumplimiento normativo, auditoría, informes a la CNMV ([BOE](https://www.boe.es/eli/es/rd/2023/11/08/813/con)) | 6–12 meses; 100–150 k€ el primer año |
| EAFN (nueva, solo nacional) | Persona jurídica: 50.000 € o seguro de RC; persona física: seguro de RC ([KPMG](https://assets.kpmg.com/content/dam/kpmg/es/pdf/2023/10/legal-alert-proyecto-real-decreto-regimen-juridico-esis.pdf)) | 6–9 meses; 15–40 k€/año |
| Agente o socio licenciado | Contrato con una ESI/EAF que asume la responsabilidad | 1–3 meses; reparto de ingresos |

Recomendación: **no pedir licencia ahora**. Valida primero como herramienta educativa y plantea una EAFN o un socio solo si hay demanda clara de recomendaciones personalizadas.

**Finfluencers/publicidad:** la CNMV revisó unos 100 perfiles (abril 2026), publicó una guía (mayo 2026) y exige etiquetar "Publicidad" ([guía](https://www.cnmv.es/DocPortal/Publicaciones/Guias/GuiaparaFinfluencers.pdf), [Cuatrecasas](https://www.cuatrecasas.com/es/global/propiedad-intelectual/art/cnmv-publica-guia-finfluencers)). Hay un punto clave para monetizar: **cobrar por cliente captado o por volumen indica "captación de clientes"**, lo que exige ser agente registrado. Una tarifa fija por pieza se considera publicidad ([Forbes](https://forbes.es/economia/846027/cnmv-define-cuando-la-publicidad-de-influencers-sobre-servicios-de-inversion-es-captacion-de-clientes/)).

**RGPD/LOPDGDD:** guardar carteras y perfiles financieros es tratamiento de datos personales. Necesitas base legal, política de privacidad, registro de actividades, contrato de encargado con el hosting y el proveedor de LLM (ojo con las transferencias fuera de la UE), cookies según LSSI y probablemente una EIPD si perfilas. Lo más simple es **no pedir datos personales** (cálculo en el navegador, cuentas opcionales).

## 2. Licencias de datos de mercado

| Fuente | ¿Mostrar a terceros o revender? | Precio aprox. |
|---|---|---|
| Yahoo Finance / yfinance | **No**. Solo uso personal; el uso comercial requiere permiso escrito ([yfinance](https://cdn.jsdelivr.net/gh/ranaroussi/yfinance@main/README.md), [ToS](https://legal.yahoo.com/xw/en/yahoo/terms/otos/index.html)) | n/a |
| EODHD | Mostrar a terceros = uso comercial; redistribuir requiere aprobación escrita ([términos](https://eodhd.com/financial-apis/commercial-vs-personal-license-use)) | Comercial desde ~399 $/mes, enterprise ~2.499 $/mes (est.) |
| Twelve Data | "Venture" incluye visualización externa (EEUU/UE); distribución en Enterprise; redistribuir requiere acuerdo aparte ([precios](https://twelvedata.com/pricing-business), [soporte](https://support.twelvedata.com/en/articles/5332349-commercial-and-personal-usage)) | Venture 149–499 $/mes; Enterprise ~1.099 $/mes |
| Financial Modeling Prep | Requiere un *Data Display and Licensing Agreement* ([FMP](https://site.financialmodelingprep.com/insights/platform/can-you-use-fmp-data-in-a-public-app-website-or-client-dashboard)) | Startup ~333 $/mes (est., no confirmado) |
| Xetra (Deutsche Börse) | Datos con retraso, en general gratis para mostrar; tiempo real y difusión con tarifa ([lista de precios 16.1](https://mds.deutsche-boerse.com/resource/blob/5353328/480628e5e12c9126a6a67030377d2a6e/data/MDDA_Price_List_16_1.pdf)) | Xetra Core redistribución ~3.642 €/mes (tiempo real) o ~1.820 € (retraso) |
| Euronext | Retraso de 15 min gratis por MiFID II; tarifas de no visualización por cliente; nuevo modelo desde 1 oct. 2026 ([políticas](https://www.euronext.com/en/data/market-data/market-data-pricing-policies)) | Bajo petición |

- **Vender los datos en bruto: mala idea.** No eres propietario de los precios, ningún plan barato lo permite y sería incumplimiento contractual. Lo que sí es tuyo son los cálculos derivados (métricas de backtest).
- **Índices MSCI:** mostrar niveles del índice requiere licencia de MSCI. Usa el precio del ETF, no el del índice.
- **Para el MVP basta un retraso de 15 min o el cierre del día.** El "tiempo real" no aporta nada a un inversor indexado y dispara los costes.

## 3. Monetización (de mejor a peor)

| # | Opción | Ingresos (est.) | Riesgo legal | Escala | Necesitas |
|---|---|---|---|---|---|
| 1 | **Freemium SaaS** (backtests largos, exportar PDF, comparar más de 3 carteras, informes con IA) | 0–2 k€/mes el primer año con 5–8 €/mes y 1–3 % de conversión | Bajo si es educativo | Alta | Stripe, licencia de visualización (~150–400 $/mes), RGPD |
| 2 | **Contenido/newsletter educativa** (Substack, curso) | 200–3 k€/mes | Bajo-medio (guía de finfluencers) | Media | Constancia; nunca recomendar a individuos |
| 3 | **B2B marca blanca para EAF/EAFN/gestoras** (backtester con su marca, informes para clientes) | 300–1.500 €/mes por cliente; 2–10 clientes | Bajo (el licenciado es el cliente) | Media | Ventas, contrato SaaS, licencia de redistribución |
| 4 | **Afiliación con brókeres** | Muy variable; 20–100 € por alta (est.) | **Medio-alto**: el pago por cliente se considera captación | Media | Ver nota |
| 5 | **Vender información agregada o anonimizada** | Incierto, bajo | **Alto** (RGPD + licencias + reputación) | Baja | Descartar |

**Afiliación, situación real:** Scalable tiene programa de partners con comisión pactada caso a caso (affiliates@scalable.capital) y un referido de 25 € ([términos](https://es.scalable.capital/terms-and-conditions-partner-program)). Trade Republic gestiona afiliados e influencers con foco en España, pero no publica condiciones y ha penalizado la difusión pública del enlace de invitación ([Finect](https://www.finect.com/usuario/davidcarmona/articulos/cuidado-si-haces-esto-al-compartir-el-enlace-de-invitacion-de-trade-republic)). MyInvestor e Indexa solo tienen "Plan Amigo" entre clientes, sin pago a webs (no he encontrado programa público) ([MyInvestor](https://myinvestor.es/ayuda/preguntas-frecuentes/plan-amigo/), [Rankia](https://www.rankia.com/blog/etf/5953217-promociones-indexa-invitacion-plan-amigo-comisiones-gratis)). Si lo usas, que sea con banners pagados como **tarifa fija**, etiquetados como publicidad y separados del backtester. Nunca dentro de una frase de la IA ("esta cartera, en el bróker X").

**Ventaja a largo plazo:** el valor duradero está en la **marca educativa en español + la comunidad + el motor de backtest con costes y fiscalidad españoles** (traspasos, IRPF del ahorro, comisiones reales). Los datos no son una ventaja, porque cualquiera los compra.

## 4. Plan de 90 días

| Días | Acciones |
|---|---|
| 0–30 | Revisar textos e IA para quitar toda personalización (prompt que se niegue, filtros, disclaimers, aviso de IA). Quitar Yahoo de producción y contratar Twelve Data Venture o similar con retraso o cierre del día. Usar precios de ETF, no de MSCI. Política de privacidad y cookies; cálculo sin cuenta. Consulta con abogado (1 h). |
| 31–60 | Lanzar el MVP gratis. Publicar 2 artículos/vídeos por semana (educativos y etiquetados). Lista de correo. Medir activación y retención. Contactar con 10 EAF/EAFN para validar el B2B. |
| 61–90 | Activar premium (5–8 €/mes) si hay más de 500 usuarios activos al mes. Piloto B2B con 1–2 EAF. Probar patrocinio con tarifa fija si un bróker acepta. Decidir: seguir B2C, girar a B2B o explorar una EAFN o un socio licenciado. |

**Lo que no debes hacer:** usar yfinance en producción comercial, revender precios, dejar que la IA diga "te conviene", cobrar por cliente captado sin estar registrado como agente y vender datos de usuarios.
