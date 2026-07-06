# Motor de banners BuenChollo Tech (HTML/CSS + Playwright)

Sustituye al motor Pillow de `TemlateChollos.py` (formato cuadrado 1200x1200).
`TemlateChollos.py` y `template_v2.py` quedan como **legacy / deprecated**
(ver cabeceras de esos archivos): no se han modificado ni borrado, pero no
deben usarse para nuevos desarrollos.

## Arquitectura

```
datos (dict / JSON / OfferData) -> banner_engine.data (validación + cálculo)
   -> banner_engine.image_processor (Pillow: recorte/encaje de la imagen de producto -> base64)
   -> templates/offer.html + static/css/offer.css (Jinja2)
   -> Chromium headless vía Playwright (captura solo el contenedor .banner, @2x)
   -> Pillow (downscale LANCZOS a la resolución final)
   -> PNG en output/ listo para Telegram sendPhoto
```

Preparado por presets (`banner_engine/presets.py`): hoy solo está implementado
`square_1200x1200`. `horizontal_1200x675` y `vertical_1080x1350` están
reservados para el futuro (mismo motor, sin duplicar código).

## Instalación

```bash
pip install -r requirements.txt
playwright install chromium   # una sola vez; requiere red solo en este paso
```

## Generar un banner

```bash
python -m banner_engine.cli examples/offer_data.json output/offer_banner.png
```

Datos de entrada (JSON o dict), campos soportados:

```json
{
  "product_name": "...",
  "product_image": "ruta/producto.png",
  "current_price": "53,29 €",
  "previous_price": "65,99 €",
  "discount_percentage": "-19%",
  "saving_amount": "12,70 €",
  "affiliate_url": "...",
  "category": "...",
  "subcategory": "..."
}
```

`discount_percentage` y `saving_amount` son opcionales: si se omiten se
calculan automáticamente a partir de `current_price`/`previous_price`.

## Docker (Synology DS224+ / Container Manager, linux/amd64)

```bash
docker build -t buenchollo-banner .
docker run --rm \
  -v "$(pwd)/examples:/app/examples" \
  -v "$(pwd)/output:/app/output" \
  buenchollo-banner examples/offer_data.json output/offer_banner.png
```

## Errores esperados (mensajes explícitos, no genéricos)

- Falta la imagen de producto → `FileNotFoundError`/`OfferDataError` con la ruta.
- Falta una variable obligatoria (`product_image`, `current_price`, `previous_price`) → `OfferDataError` con el nombre del campo.
- Precio con formato no parseable → `OfferDataError`.
- Chromium no instalado → `RenderError` indicando `playwright install chromium`.
- No se puede escribir el PNG de salida → `RenderError` con la ruta.

## Pendiente de decisión manual

- **Fuentes**: se han copiado `segoeui.ttf` / `segoeuib.ttf` / `segoeuiz.ttf`
  desde `C:\Windows\Fonts` a `static/fonts/` para que el render sea 100%
  local y portable a Linux. Segoe UI no es libremente redistribuible fuera
  de Windows; esto es aceptable para uso interno en tu propio NAS, pero si
  se quiere evitar cualquier duda de licencia, la alternativa es sustituir
  esos 3 archivos por la fuente **Inter** (OFL, geometría muy similar) sin
  tocar el resto del código.
- `template_v2.py` solo lo usa `TemlateChollos.py` (4 helpers) y no se ha
  encontrado ningún otro archivo que dependa de él; se deja para una futura
  limpieza, no se ha eliminado en esta migración.
