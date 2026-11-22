---
name: guiones-tiktok-shop
description: Escribe guiones de vídeo orgánico de 15-30 s para vender como afiliado de TikTok Shop en España (móvil, sin cara). Úsala cuando Oscar pida guiones, ganchos, ideas de vídeo o textos de post para un producto de TikTok Shop, o al iterar un vídeo que falló según datos/metricas.csv.
---

# Guiones TikTok Shop

Misma línea que el agente Creador (`agencia/creador.py`), pero usable directamente en el chat.

## Antes de escribir
1. Identifica el producto, el precio y el problema que resuelve. Si falta el problema, pregúntalo (una sola pregunta).
2. Si existe `datos/metricas.csv` con filas, léelo y aplica lo aprendido:
   - <500 vistas a las 48 h → falló el gancho: cambia el tipo de gancho.
   - Buenas vistas y 0 clics al carrito → falló la oferta: muestra más el uso y el precio.
   - ≥1 venta → repite el gancho ganador con otra escena.

## Reglas
- Español de España, tono natural. Prohibido: "¡increíble!", "no te lo vas a creer", estilo teletienda.
- Los 2 primeros segundos deciden el vídeo: el gancho tiene que ser visual y entenderse sin sonido.
- El problema va antes que el producto.
- Nada de afirmaciones médicas, falsas ni resultados garantizados.
- Grabable con un móvil, sin cara, en casa y en menos de 15 minutos.
- CTA suave hacia el carrito naranja, nunca agresiva.

## Salida
Tres guiones con ganchos distintos: **problema**, **curiosidad** y **antes/después**. Para cada uno:

```
### <título interno> · gancho: <tipo>
Gancho (0-2 s): <texto en pantalla + qué se ve>
| Seg | Plano | Texto en pantalla | Voz en off |
|-----|-------|-------------------|------------|
Post: <descripción ≤150 caracteres>
Hashtags: 4-6, mezcla de nicho + #tiktokshop
Sonido: <tipo de audio en tendencia, sin inventar nombres de canciones>
```

Termina con una línea: **Graba primero:** <el guion con más potencial> y por qué.
