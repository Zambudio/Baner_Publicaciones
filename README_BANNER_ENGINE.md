# Motor de banners BuenChollo Tech (HTML/CSS + Playwright)

## Qué hace este código, en corto

Genera la imagen cuadrada de oferta (1200x1200, la que se publica en Amazon/Telegram)
a partir de unos datos (precio actual, precio anterior, descuento, ahorro, foto del
producto...). En vez de dibujar rectángulos a mano con Python (como hacía el sistema
viejo), monta una página web (HTML + CSS) con el diseño, le hace una "foto" con un
navegador Chrome invisible (Chromium, controlado por Playwright) y guarda esa foto
como el PNG final. Es determinista: mismos datos de entrada → siempre el mismo PNG.

Sustituye al motor Pillow de `TemlateChollos.py` (formato cuadrado 1200x1200).
`TemlateChollos.py` y `template_v2.py` quedan como **legacy / deprecated**
(ver cabeceras de esos archivos): no se han modificado ni borrado, pero no
deben usarse para nuevos desarrollos.

## Cómo está organizado el código

| Carpeta/archivo | Para qué sirve |
|---|---|
| `banner_engine/data.py` | Recibe los datos (JSON o diccionario) y los valida: que no falte ningún precio, que la imagen del producto exista, etc. Si algo está mal, avisa con un mensaje claro en vez de romperse en silencio. |
| `banner_engine/image_processor.py` | Recorta los márgenes en blanco de la foto del producto y la ajusta de tamaño con Pillow. |
| `banner_engine/fonts.py` | Carga las fuentes (Segoe UI) desde `static/fonts/` para que el diseño no dependa de fuentes de Windows. |
| `banner_engine/render.py` | El "director de orquesta": junta datos + plantilla, abre Chromium sin ventana, hace la captura y guarda el PNG. |
| `banner_engine/cli.py` | El programa que ejecutas tú desde la terminal. |
| `templates/offer.html` | La estructura del banner (qué bloques hay y en qué orden). |
| `static/css/offer.css` | Todo el diseño visual: colores, gradientes, sombras, tamaños de letra. Si quieres cambiar el aspecto del banner, casi siempre es aquí. |
| `examples/*.json` | Datos de ejemplo para probar (precio normal, precio largo, descuento del 50%). |
| `output/` | Aquí se guardan los PNG que generas. |

Arquitectura completa:

```
datos (JSON / diccionario) -> banner_engine.data (validación + cálculo)
   -> banner_engine.image_processor (recorte/encaje de la foto de producto)
   -> templates/offer.html + static/css/offer.css (Jinja2 rellena las plantillas)
   -> Chromium headless vía Playwright (hace la captura)
   -> Pillow (ajusta la resolución final)
   -> PNG en output/ listo para Telegram sendPhoto
```

Preparado por presets (`banner_engine/presets.py`): hoy solo está implementado
`square_1200x1200`. `horizontal_1200x675` y `vertical_1080x1350` están
reservados para el futuro (mismo motor, sin duplicar código).

## Instalación (una sola vez)

**Importante en Windows si tienes varias versiones de Python instaladas:**
ejecuta `py -0` en PowerShell para ver cuáles tienes. Si aparece más de una,
usa siempre la misma versión para instalar y para ejecutar — si no, `pip`
instala las librerías en una versión y `python` intenta ejecutar con otra,
y da error de "no module named...". En esta máquina la que funciona es la
**3.11**, así que todos los comandos de abajo usan `py -3.11`. Si en tu
equipo solo tienes una versión de Python, puedes usar simplemente `python`.

```powershell
py -3.11 -m pip install -r requirements.txt
py -3.11 -m playwright install chromium
```

`playwright install chromium` descarga el navegador Chromium (unos 150 MB).
Se hace una sola vez; necesita internet solo en este paso, nunca cuando
generas una imagen.

## Generar un banner

```powershell
py -3.11 -m banner_engine.cli examples/offer_data.json output/offer_banner.png
```

- El primer argumento es el archivo JSON con los datos de la oferta.
- El segundo argumento es dónde se guarda el PNG resultante.
- El tercer argumento (opcional) es el preset; hoy solo existe `square_1200x1200`, que es el que se usa por defecto si no lo indicas.

Ejemplos ya incluidos para probar casos límite:

```powershell
py -3.11 -m banner_engine.cli examples/offer_data_long_price.json output/prueba_precio_largo.png
py -3.11 -m banner_engine.cli examples/offer_data_discount50.json output/prueba_descuento_50.png
```

### Datos de entrada

Copia `examples/offer_data.json`, cámbialo con tu producto y apunta el comando
a tu copia. Campos soportados:

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

Obligatorios: `product_image`, `current_price`, `previous_price`.
`discount_percentage` y `saving_amount` son opcionales: si se omiten se
calculan solos a partir de los dos precios.

## Docker (para cuando esté listo y lo subas al NAS Synology DS224+)

```bash
docker build -t buenchollo-banner .
docker run --rm \
  -v "$(pwd)/examples:/app/examples" \
  -v "$(pwd)/output:/app/output" \
  buenchollo-banner examples/offer_data.json output/offer_banner.png
```

## Si algo falla, el error te dice exactamente qué pasa

- Falta la imagen de producto → mensaje con la ruta que no existe.
- Falta un dato obligatorio (`product_image`, `current_price`, `previous_price`) → mensaje con el nombre del campo que falta.
- Un precio no se puede interpretar → mensaje indicándolo.
- Chromium no está instalado → mensaje diciendo que ejecutes `playwright install chromium`.
- No se puede guardar el PNG (carpeta sin permisos, etc.) → mensaje con la ruta.

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
- Falta conectar el PNG generado con el envío real por Telegram (`sendPhoto`);
  este proyecto solo genera la imagen, no la envía.
