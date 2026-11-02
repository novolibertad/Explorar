# Explorar · Microagencia IA para TikTok Shop

Tres agentes (Claude API) para vender como **afiliado de TikTok Shop** con vídeo orgánico, sin gastar en anuncios.

| Agente | Qué hace | Comando |
|---|---|---|
| 🔎 Buscador | Busca en la web productos con demanda y poca saturación | `buscar "nicho"` |
| 🎬 Creador | 3 guiones de 15–30 s por producto (gancho, planos, texto, hashtags) | `crear <json> <n>` |
| 🧠 Jesús (jefe) | Lee tus métricas reales y decide ESCALAR / ITERAR / MATAR | `decidir datos/metricas.csv` |

## Arranque (5 min)
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...      # console.anthropic.com, carga 5 €
python agencia.py dia "hogar y cocina"   # productos + guiones del mejor
```

## Rutina diaria (~45 min)
1. `python agencia.py dia "<nicho>"` → elige guion.
2. Graba con el móvil (sin cara) y publica 1–3 vídeos con el producto enlazado.
3. A las 48 h apunta los datos en `datos/metricas.csv`.
4. `python agencia.py decidir datos/metricas.csv` → haz lo que diga.

Regla de oro: **no pagar anuncios hasta tener 5 ventas orgánicas** de un producto.

Coste API aproximado: 0,10–0,40 € por ejecución de `dia`.
