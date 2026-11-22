# Explorar · Microagencia IA para TikTok Shop

Tres agentes (Claude API) para vender como **afiliado de TikTok Shop** con vídeo orgánico, sin gastar en anuncios.

| Agente | Qué hace | Comando |
|---|---|---|
| 🔎 Buscador | Busca en la web productos con demanda y poca saturación | `buscar "nicho"` |
| 🎬 Creador | 3 guiones de 15–30 s por producto (gancho, planos, texto, hashtags) | `crear <json> <n>` |
| 🎞️ Montador | Convierte un guion en MP4 vertical 1080×1920 con textos | `video <json> <n> [medios/]` |
| 🧠 Jesús (jefe) | Lee tus métricas reales y decide ESCALAR / ITERAR / MATAR | `decidir datos/metricas.csv` |

## Arranque (5 min)
```bash
pip install -r requirements.txt     # y ffmpeg para el montador
export ANTHROPIC_API_KEY=sk-ant-...      # console.anthropic.com, carga 5 €
python agencia.py dia "hogar y cocina"   # productos + guiones del mejor
```

## Rutina diaria (~45 min)
1. `python agencia.py dia "<nicho>"` → elige guion.
2. `python agencia.py video salidas/<fecha>_guiones.json 1` → storyboard con lo que hay que grabar.
3. Graba cada plano con el móvil (sin cara) y guárdalo como `medios/escena1.mp4`, `escena2.mp4`…
   (también vale `.jpg`). Repite el comando con `medios/` al final → vídeo final con textos.
4. Súbelo a TikTok, añade el sonido en tendencia y enlaza el producto.
5. A las 48 h apunta los datos en `datos/metricas.csv`.
6. `python agencia.py decidir datos/metricas.csv` → haz lo que diga.

Regla de oro: **no pagar anuncios hasta tener 5 ventas orgánicas** de un producto.

Coste API aproximado: 0,10–0,40 € por ejecución de `dia`.
