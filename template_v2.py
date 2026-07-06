"""
LEGACY / DEPRECATED (2026-07-06) - sustituido por banner_engine/ (HTML/CSS +
Playwright). Ver README_BANNER_ENGINE.md. No usar para nuevos desarrollos;
se conserva sin modificar porque TemlateChollos.py todavia importa 4 helpers
de este archivo (format_price, trim_image_whitespace, contain_image,
fit_font_to_width). No se ha encontrado ningun otro archivo que dependa de
el; revisar en una futura limpieza si procede eliminarlo.

TEMPLATE_V2 - Plantilla de tarjeta de precio para BuenChollo Tech.

Version independiente de generar_post.py (v1), pensada para comparar ambas
antes de decidir cual pasa a produccion. No reutiliza codigo de v1 a
proposito: la especificacion pide una plantilla configurable desde cero,
con toda la geometria centralizada en CONFIG y funciones reutilizables
(fit de fuente, centrado vertical, tarjetas redondeadas, tachado real,
recorte de margenes, contain, sombra suave, carga de fuente con fallback,
formato de importes/porcentajes).

Diseno: tarjeta de comercio electronico premium - producto a la izquierda,
modulo de precios (Antes / Ahora / Ahorro) a la derecha, marca BuenChollo
abajo-izquierda y tienda abajo-derecha. Sin titulo, sin urgencia, sin
elementos promocionales: solo producto, precio y ahorro.

Uso:
    generar_post_v2(
        producto_img_path=...,
        precio_original=...,
        precio_oferta=...,
        output_path=...,
    )
"""

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

# ============================================================
# CONFIGURACION CENTRALIZADA - todo lo ajustable vive aqui.
# Todas las medidas estan en px del lienzo FINAL (1200x675); el
# renderizado interno a doble resolucion se aplica automaticamente
# mediante el factor SCALE al dibujar.
# ============================================================

CONFIG = {
    "canvas": {"w": 1200, "h": 675, "scale": 2},
    "bg": (248, 250, 252),  # #F8FAFC
    "margin": 42,

    "layout": {"left_pct": 0.55, "right_pct": 0.35},

    "fonts": {
        "family": "arial.ttf",
        "fallback": "arial.ttf",
        "fallback_semibold": "arial.ttf",
    },

    "product": {
        "max_w": 540,
        "max_h": 440,
        "circle_color": (234, 242, 255),  # #EAF2FF
        "shadow_opacity": 0.16,
        "shadow_blur": 14,
        "shadow_offset": (0, 12),
    },

    "price_module": {
        "width": 380,
        "gap": 14,
        "radius": 18,
        "padding_x": 24,
    },

    "antes": {
        "height": 85,
        "bg": (255, 255, 255),
        "border": (220, 229, 240),  # #DCE5F0
        "border_w": 1,
        "label_size": 18,
        "label_color": (37, 99, 235),  # #2563EB
        "price_size_min": 34,
        "price_size_max": 38,
        "price_color": (71, 85, 105),  # #475569
    },

    "ahora": {
        "height": 135,
        "bg": (37, 99, 235),  # #2563EB - plano, sin degradado
        "label_size": 18,
        "label_color": (219, 234, 254),  # #DBEAFE
        "price_size_min": 64,
        "price_size_max": 72,
        "price_size_floor": 52,  # nunca por debajo, ni en casos excepcionales
        "price_color": (255, 255, 255),
    },

    "ahorro": {
        "height": 64,
        "bg": (236, 253, 243),  # #ECFDF3
        "border": (187, 247, 208),  # #BBF7D0
        "border_w": 1,
        "pct_size_min": 30,
        "pct_size_max": 34,
        "pct_bg": (22, 163, 74),  # #16A34A
        "pct_color": (255, 255, 255),
        "ahorras_size": 21,
        "ahorras_color": (21, 128, 61),  # #15803D
    },

    "footer": {
        "logo_h": 44,
        "brand_size": 24,
        "brand_color": (37, 99, 235),  # #2563EB
        "store_label_size": 15,
        "store_label_color": (100, 116, 139),  # #64748B
        "margin": 34,
    },
}


# ============================================================
# FUNCIONES REUTILIZABLES
# ============================================================

def load_font(size, weight="Regular", cfg=CONFIG):
    """Carga la fuente variable con el peso pedido; si la fuente principal
    o el peso fallan por cualquier motivo, cae a Poppins (Bold para pesos
    fuertes, Medium para el resto) para que el pipeline nunca reviente por
    una fuente que falte."""
    try:
        f = ImageFont.truetype(cfg["fonts"]["family"], size)
        if hasattr(f, "set_variation_by_name"):
            f.set_variation_by_name(weight.encode())
        return f
    except Exception:
        fallback = (
            cfg["fonts"]["fallback"]
            if weight in ("Bold", "ExtraBold")
            else cfg["fonts"]["fallback_semibold"]
        )
        return ImageFont.truetype(fallback, size)


def fit_font_to_width(draw, text, weight, max_width, size_max, size_min, cfg=CONFIG):
    """Devuelve la fuente mas grande (dentro de [size_min, size_max]) cuyo
    ancho REAL (via textbbox) cabe en max_width. Reduce de 1 en 1 para
    precision. Si ni al minimo cabe, devuelve la de tamano minimo (el
    llamador decide si eso es un error segun el contexto)."""
    for size in range(size_max, size_min - 1, -1):
        f = load_font(size, weight, cfg)
        try:
            bbox = draw.textbbox((0, 0), text, font=f, features=["tnum"])
        except (KeyError, AttributeError):
            bbox = draw.textbbox((0, 0), text, font=f)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            return f, size
    return load_font(size_min, weight, cfg), size_min


def text_height(draw, text, font):
    """Alto real del texto renderizado (via textbbox), no una aproximacion
    por tamano de fuente."""
    bbox = draw.textbbox((0, 0), text, font=font, features=["tnum"])
    return bbox[3] - bbox[1], bbox[1]  # (alto, top_offset)


def draw_text_v_centered(draw, text, font, x, box_y0, box_y1, color, features=None):
    """Centra verticalmente un texto dentro de [box_y0, box_y1] usando sus
    metricas reales (textbbox), no un offset fijo a ojo."""
    bbox = draw.textbbox((0, 0), text, font=font, features=features or ["tnum"])
    h = bbox[3] - bbox[1]
    y = box_y0 + (box_y1 - box_y0 - h) // 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=color, features=features or ["tnum"])
    return bbox


def draw_rounded_card(draw, box, radius, fill=None, outline=None, outline_w=1):
    """Tarjeta redondeada generica - unico punto del codigo que dibuja
    rectangulos con esquinas, para que todos los bloques compartan
    exactamente el mismo radio y trazo."""
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=outline_w)


def draw_strikethrough(draw, text, font, x, y_top, color, width, features=None):
    """Linea de tachado calculada con las medidas REALES del texto (no
    coordenadas fijas): la centra en la altura x del texto, no en el medio
    geometrico de la caja, para que quede bien colocada a cualquier tamano
    de fuente."""
    bbox = draw.textbbox((x, y_top), text, font=font, features=features or ["tnum"])
    tw = bbox[2] - bbox[0]
    # centro vertical del propio texto renderizado
    strike_y = (bbox[1] + bbox[3]) / 2 + (bbox[3] - bbox[1]) * 0.02
    draw.line([(bbox[0], strike_y), (bbox[0] + tw, strike_y)], fill=color, width=width)


def trim_image_whitespace(im, tolerance=8):
    """Recorta margenes blancos o transparentes sobrantes del PNG/JPG de
    producto original, quedandose solo con el contenido real. Funciona
    tanto con imagenes con canal alfa real como con fondo blanco solido."""
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    alpha = im.split()[-1]
    if alpha.getextrema() != (255, 255):
        # Hay transparencia real: usarla tal cual para el recorte
        bbox = alpha.getbbox()
    else:
        # Sin canal alfa util: tratar el blanco casi puro como fondo
        rgb = im.convert("RGB")
        gray = rgb.convert("L")
        # todo lo que NO sea casi blanco cuenta como contenido
        mask = gray.point(lambda p: 0 if p >= (255 - tolerance) else 255)
        bbox = mask.getbbox()
    return im.crop(bbox) if bbox else im


def contain_image(im, max_w, max_h):
    """Redimensiona manteniendo proporcion, SIN deformar y sin recortar,
    dentro de max_w x max_h."""
    return ImageOps.contain(im, (int(max_w), int(max_h)), method=Image.LANCZOS)


def draw_soft_shadow(canvas_rgba, content_rgba, position, blur, opacity, offset, color=(15, 23, 42)):
    """Sombra suave a partir del canal alfa real de la imagen (si el
    producto tiene transparencia de verdad, la sombra sigue su silueta;
    si no, cae a la caja rectangular de la imagen - en ambos casos con
    poca opacidad y desenfoque generoso, nunca una sombra dura)."""
    alpha = content_rgba.split()[-1]
    shadow_alpha = alpha.point(lambda a: int(a * opacity))
    shadow = Image.new("RGBA", content_rgba.size, color + (0,))
    shadow.putalpha(shadow_alpha)
    layer = Image.new("RGBA", canvas_rgba.size, (0, 0, 0, 0))
    layer.paste(shadow, (position[0] + offset[0], position[1] + offset[1]), shadow)
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    canvas_rgba.alpha_composite(layer)


def format_price(value):
    """Formatea un importe al estilo espanol: miles con punto, decimales
    con coma, simbolo € SIEMPRE en la misma cadena/linea que el numero."""
    entero = int(value)
    decimales = round((value - entero) * 100)
    if decimales >= 100:
        entero += 1
        decimales -= 100
    entero_str = f"{entero:,}".replace(",", ".")
    return f"{entero_str},{decimales:02d} €"


def format_percent(value):
    """Formato '−19 %' (signo menos tipografico + espacio antes del %)."""
    return f"\u221216 %".replace("16", str(round(value)))


# ============================================================
# BLOQUES DE LA PLANTILLA
# ============================================================

def _s(v, scale):
    return round(v * scale)


def _draw_producto(draw, canvas, box, producto_img_path, scale, cfg=CONFIG):
    x0, y0, x1, y1 = box
    max_w = min(_s(cfg["product"]["max_w"], scale), x1 - x0)
    max_h = min(_s(cfg["product"]["max_h"], scale), y1 - y0)

    raw = Image.open(producto_img_path)
    trimmed = trim_image_whitespace(raw)
    fitted = contain_image(trimmed, max_w, max_h)

    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2

    # Elipse decorativa detras del producto - discreta, para separar
    # productos blancos del fondo claro
    circle_w = int(fitted.width * 1.28)
    circle_h = int(fitted.height * 1.22)
    circle_box = (
        cx - circle_w // 2, cy - circle_h // 2,
        cx + circle_w // 2, cy + circle_h // 2,
    )
    draw.ellipse(circle_box, fill=cfg["product"]["circle_color"])

    px, py = cx - fitted.width // 2, cy - fitted.height // 2

    draw_soft_shadow(
        canvas, fitted, (px, py),
        blur=_s(cfg["product"]["shadow_blur"], scale),
        opacity=cfg["product"]["shadow_opacity"],
        offset=(
            _s(cfg["product"]["shadow_offset"][0], scale),
            _s(cfg["product"]["shadow_offset"][1], scale),
        ),
    )
    canvas.paste(fitted, (px, py), fitted)


def _draw_bloque_antes(draw, box, precio_original, scale, cfg=CONFIG):
    c = cfg["antes"]
    draw_rounded_card(draw, box, radius=_s(cfg["price_module"]["radius"], scale),
                       fill=c["bg"], outline=c["border"], outline_w=max(1, _s(c["border_w"], scale)))
    x0, y0, x1, y1 = box
    pad = _s(cfg["price_module"]["padding_x"], scale)

    f_label = load_font(_s(c["label_size"], scale), "SemiBold", cfg)
    label_h, _ = text_height(draw, "Antes", f_label)
    f_precio, _ = fit_font_to_width(
        draw, format_price(precio_original), "SemiBold",
        (x1 - x0) - 2 * pad, _s(c["price_size_max"], scale), _s(c["price_size_min"], scale), cfg
    )

    gap = _s(6, scale)
    precio_txt = format_price(precio_original)
    precio_h, _ = text_height(draw, precio_txt, f_precio)
    total_h = label_h + gap + precio_h
    top = y0 + ((y1 - y0) - total_h) // 2

    draw.text((x0 + pad, top), "Antes", font=f_label, fill=c["label_color"])
    precio_y = top + label_h + gap
    draw.text((x0 + pad, precio_y), precio_txt, font=f_precio, fill=c["price_color"], features=["tnum"])
    draw_strikethrough(draw, precio_txt, f_precio, x0 + pad, precio_y, c["price_color"], max(2, _s(2, scale)))


def _draw_bloque_ahora(draw, box, precio_oferta, scale, cfg=CONFIG):
    c = cfg["ahora"]
    draw_rounded_card(draw, box, radius=_s(cfg["price_module"]["radius"], scale), fill=c["bg"])
    x0, y0, x1, y1 = box
    pad = _s(cfg["price_module"]["padding_x"], scale)
    content_w = (x1 - x0) - 2 * pad

    f_label = load_font(_s(c["label_size"], scale), "SemiBold", cfg)
    label_h, _ = text_height(draw, "Ahora", f_label)

    precio_txt = format_price(precio_oferta)
    # Rango normal primero; si no cabe, entra en el rango excepcional
    # hasta el suelo absoluto - nunca por debajo, nunca cortado.
    f_precio, size_used = fit_font_to_width(
        draw, precio_txt, "ExtraBold", content_w,
        _s(c["price_size_max"], scale), _s(c["price_size_min"], scale), cfg
    )
    if size_used == _s(c["price_size_min"], scale):
        bbox = draw.textbbox((0, 0), precio_txt, font=f_precio, features=["tnum"])
        if (bbox[2] - bbox[0]) > content_w:
            f_precio, size_used = fit_font_to_width(
                draw, precio_txt, "ExtraBold", content_w,
                _s(c["price_size_min"], scale) - 1, _s(c["price_size_floor"], scale), cfg
            )
            bbox = draw.textbbox((0, 0), precio_txt, font=f_precio, features=["tnum"])
            if (bbox[2] - bbox[0]) > content_w:
                raise ValueError(
                    f"El precio '{precio_txt}' no cabe ni al tamano minimo absoluto "
                    f"({c['price_size_floor']}px) del bloque Ahora. Revisa el ancho "
                    "del modulo de precios o el numero de digitos."
                )

    precio_h, _ = text_height(draw, precio_txt, f_precio)
    gap = _s(8, scale)
    total_h = label_h + gap + precio_h
    top = y0 + ((y1 - y0) - total_h) // 2

    draw.text((x0 + pad, top), "Ahora", font=f_label, fill=c["label_color"])
    draw.text((x0 + pad, top + label_h + gap), precio_txt, font=f_precio, fill=c["price_color"], features=["tnum"])


def _draw_bloque_ahorro(draw, box, descuento, ahorro, scale, cfg=CONFIG):
    c = cfg["ahorro"]
    draw_rounded_card(draw, box, radius=_s(cfg["price_module"]["radius"], scale),
                       fill=c["bg"], outline=c["border"], outline_w=max(1, _s(c["border_w"], scale)))
    x0, y0, x1, y1 = box
    pad = _s(cfg["price_module"]["padding_x"], scale)

    pct_txt = format_percent(descuento)
    f_pct, _ = fit_font_to_width(
        draw, pct_txt, "ExtraBold", (x1 - x0) - 2 * pad,
        _s(c["pct_size_max"], scale), _s(c["pct_size_min"], scale), cfg
    )
    bbox = draw.textbbox((0, 0), pct_txt, font=f_pct, features=["tnum"])
    pct_w, pct_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

    cap_pad_x = _s(16, scale)
    cap_h = y1 - y0 - _s(16, scale)
    cap_w = pct_w + 2 * cap_pad_x
    cap_y0 = y0 + (y1 - y0 - cap_h) // 2
    cap_box = (x0 + pad, cap_y0, x0 + pad + cap_w, cap_y0 + cap_h)
    draw_rounded_card(draw, cap_box, radius=_s(cfg["price_module"]["radius"] - 4, scale), fill=c["pct_bg"])
    draw_text_v_centered(draw, pct_txt, f_pct, x0 + pad + cap_pad_x - bbox[0], cap_y0, cap_y0 + cap_h, c["pct_color"])

    ahorras_txt = f"Ahorras {format_price(ahorro)}"
    f_ahorras = load_font(_s(c["ahorras_size"], scale), "SemiBold", cfg)
    ax = x0 + pad + cap_w + _s(16, scale)
    draw_text_v_centered(draw, ahorras_txt, f_ahorras, ax, y0, y1, c["ahorras_color"])


def _draw_footer(draw, canvas, canal_nombre, logo_path, tienda_nombre, tienda_logo_path, scale, cfg=CONFIG):
    c = cfg["footer"]
    W = canvas.size[0]
    H = canvas.size[1]
    margin = _s(c["margin"], scale)
    logo_h = _s(c["logo_h"], scale)
    row_y1 = H - margin
    row_y0 = row_y1 - logo_h

    if logo_path:
        logo = Image.open(logo_path).convert("RGBA")
        logo = ImageOps.fit(logo, (logo_h, logo_h), method=Image.LANCZOS)
        canvas.paste(logo, (margin, row_y0), logo)
        text_x = margin + logo_h + _s(14, scale)
    else:
        text_x = margin

    f_marca = load_font(_s(c["brand_size"], scale), "Bold", cfg)
    draw_text_v_centered(draw, canal_nombre, f_marca, text_x, row_y0, row_y1, c["brand_color"])

    x_right = W - margin
    if tienda_logo_path:
        tlogo = Image.open(tienda_logo_path).convert("RGBA")
        tlogo = ImageOps.contain(tlogo, (_s(210, scale), logo_h), method=Image.LANCZOS)
        canvas.paste(tlogo, (x_right - tlogo.width, row_y0 + (logo_h - tlogo.height) // 2), tlogo)
    else:
        f_label = load_font(_s(c["store_label_size"], scale), "Medium", cfg)
        f_tienda = load_font(_s(20, scale), "Bold", cfg)
        label_txt = "Disponible en"
        lbbox = draw.textbbox((0, 0), label_txt, font=f_label)
        tbbox = draw.textbbox((0, 0), tienda_nombre, font=f_tienda)
        lw, tw = lbbox[2] - lbbox[0], tbbox[2] - tbbox[0]
        draw.text((x_right - lw, row_y0), label_txt, font=f_label, fill=c["store_label_color"])
        draw.text((x_right - tw, row_y0 + _s(22, scale)), tienda_nombre, font=f_tienda, fill=(17, 17, 17))


# ============================================================
# ENTRADA PRINCIPAL
# ============================================================

def generar_post_v2(
    producto_img_path: str,
    precio_original: float,
    precio_oferta: float,
    output_path: str,
    canal_nombre: str = "BuenChollo Tech",
    logo_path: str = None,
    tienda_nombre: str = "Amazon",
    tienda_logo_path: str = None,
    cfg: dict = CONFIG,
):
    if precio_oferta >= precio_original:
        raise ValueError(
            f"precio_oferta ({precio_oferta}) debe ser menor que precio_original "
            f"({precio_original}); si no hay descuento real, esta plantilla no aplica."
        )

    scale = cfg["canvas"]["scale"]
    W, H = cfg["canvas"]["w"] * scale, cfg["canvas"]["h"] * scale
    margin = _s(cfg["margin"], scale)

    canvas = Image.new("RGBA", (W, H), cfg["bg"] + (255,))
    draw = ImageDraw.Draw(canvas)

    descuento = round((1 - precio_oferta / precio_original) * 100)
    ahorro = precio_original - precio_oferta

    content_w = W - 2 * margin
    price_w = _s(cfg["price_module"]["width"], scale)
    price_x1 = W - margin
    price_x0 = price_x1 - price_w
    left_x0 = margin
    left_x1 = price_x0 - _s(30, scale)

    row_y0 = margin
    row_h = _s(cfg["product"]["max_h"], scale)
    row_y1 = row_y0 + row_h

    _draw_producto(
        draw, canvas, (left_x0, row_y0, left_x1, row_y1),
        producto_img_path, scale, cfg
    )

    m = cfg["price_module"]
    a, ah, ao = cfg["antes"], cfg["ahora"], cfg["ahorro"]
    stack_h = _s(a["height"] + ah["height"] + ao["height"], scale) + 2 * _s(m["gap"], scale)
    stack_y0 = row_y0 + (row_h - stack_h) // 2

    y = stack_y0
    h_antes = _s(a["height"], scale)
    _draw_bloque_antes(draw, (price_x0, y, price_x1, y + h_antes), precio_original, scale, cfg)
    y += h_antes + _s(m["gap"], scale)
    h_ahora = _s(ah["height"], scale)
    _draw_bloque_ahora(draw, (price_x0, y, price_x1, y + h_ahora), precio_oferta, scale, cfg)
    y += h_ahora + _s(m["gap"], scale)
    h_ahorro = _s(ao["height"], scale)
    _draw_bloque_ahorro(draw, (price_x0, y, price_x1, y + h_ahorro), descuento, ahorro, scale, cfg)

    _draw_footer(draw, canvas, canal_nombre, logo_path, tienda_nombre, tienda_logo_path, scale, cfg)

    # Downscale final con LANCZOS para nitidez de texto y bordes
    final = canvas.convert("RGB").resize(
        (cfg["canvas"]["w"], cfg["canvas"]["h"]), resample=Image.LANCZOS
    )
    final.save(output_path)
    return output_path


if __name__ == "__main__":
    LOGO = "/mnt/user-data/uploads/logoTelegram.png"
    PRODUCTO = "/home/claude/producto_test.png"

    casos = [
        ("v2_caso_normal.png", 65.99, 53.29),
        ("v2_caso_precio_bajo.png", 3.99, 1.99),
        ("v2_caso_precio_alto.png", 1999.99, 999.99),
        ("v2_caso_descuento_alto.png", 49.99, 9.99),
    ]
    for filename, antes, ahora in casos:
        generar_post_v2(
            producto_img_path=PRODUCTO,
            precio_original=antes,
            precio_oferta=ahora,
            output_path=f"/home/claude/banner/{filename}",
            logo_path=LOGO,
        )
        print(f"generado: {filename}")
