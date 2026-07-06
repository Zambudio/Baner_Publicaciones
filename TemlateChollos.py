"""
LEGACY / DEPRECATED (2026-07-06) - sustituido por banner_engine/ (HTML/CSS +
Playwright + Jinja2), que reemplaza el bloque de precios por un diseno con
gradientes/sombras/brillos reales en vez de dibujo manual con Pillow. Ver
README.md para instalacion y uso del nuevo motor. Este archivo
se conserva sin modificar (no se ha encontrado nada mas que lo importe) por
si algo externo depende todavia de generar_post_v3/generar_banner_chollo.

Nota de auditoria: generar_post_v3 tiene un KeyError latente porque
cfg["precios"]["spacing"]["between_current_previous"] se lee (usos mas abajo
en el archivo) pero nunca se define en CONFIG["precios"]["spacing"]. No se
corrige aqui a proposito (codigo legacy, no se modifica su comportamiento).

TEMPLATE_V3 - Variante "energetica" de la tarjeta de oferta BuenChollo Tech.

Inspirada en dos referencias que trajo Pedro:
- Una imagen generada por IA (fondo oscuro, brillos, insignias cromadas) que
  le gustaba en espiritu pero le parecia "demasiado fantastica" - y que,
  critico importante, no es reproducible con datos exactos (es arte
  generativo, no una plantilla: no vale para automatizar precios reales).
- chollosDeluxe.com como referencia de composicion mas comedida: fondo
  oscuro con estrellas sutiles, precio grande en texto de color, precio
  anterior tachado debajo, marca abajo.

Esta version SI es codigo determinista (como V1 y V2): mismo input,
mismo resultado exacto, siempre. Reutiliza helpers de template_v2 donde
tiene sentido (formato de precios, ajuste de fuente, recorte de imagen)
en vez de duplicar logica.
"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageChops

from template_v2 import (
    format_price,
    trim_image_whitespace,
    contain_image,
    fit_font_to_width,
)

import math

FONT_FAMILY = "Segoe UI"
FONT_FALLBACK = "Arial"

CONFIG = {
    # Formato cuadrado por defecto (como la imagen original 1254x1254)
    "canvas": {"w": 1200, "h": 1200, "scale": 2},
    "bg": (255, 255, 255),
    "margin": 48,

    "product": {
        "max_w": 520, "max_h": 720,
        "circle_color": (235, 243, 255),
    },

    "colors": {
        "azul_marca": (8, 99, 235),
        "azul_texto_tenue": (100, 116, 139),
        "magenta": (197, 32, 160),
        "negro": (17, 24, 39),
        "gris": (100, 116, 139),
        "gris_borde": (220, 229, 240),
    },

    "titulo": {"cat_size": 30, "sub_size": 22},
    
    "precios": {
        "precio_ahora": {
            "size_max": 130, "size_min": 85,
            # Degradado azul metálico premium (luminoso a marino profundo)
            "color_top": (20, 140, 255),      # Azul luminoso superior
            "color_mid": (0, 60, 200),        # Azul medio intenso
            "color_bottom": (0, 20, 120),     # Azul marino profundo inferior
            "border_color": (255, 255, 255),  # Sin borde por defecto
            "radius": 38,
            "padding": 28,
            "height": 220,
            "shadow_offset": (0, 6),
            "shadow_blur": 12,
            "shine_opacity": 0.45,
        },
        "precio_antes": {
            "size_max": 54, "size_min": 36,
            # Degradado naranja intenso
            "color_top": (255, 130, 0),       # Naranja claro
            "color_bottom": (220, 50, 0),     # Naranja oscuro
            "border_color": (255, 160, 50),
            "radius": 28,
            "padding": 24,
            "height": 80,
            "shadow_blur": 8,
            "shine_opacity": 0.25,
            "strike_color": (0, 0, 0),        # Línea negra diagonal
        },
        "descuento": {
            "diameter": 130,                  # Más grande
            "color_top": (255, 225, 0),      # Amarillo
            "color_bottom": (255, 140, 0),   # Naranja amarillo
            "border_color": (255, 110, 0),   # Borde naranja
            "font_size": 44,
            "font_color": (15, 23, 42),       # Negro / azul marino oscuro
            "shadow_blur": 8,
            "overlap_percent": 0.28,          # Más superpuesto
        },
        "ahorro": {
            "color_bg": (15, 23, 42),        # Azul marino muy oscuro
            "color_accent": (30, 41, 59),    # Azul grisáceo
            "label_color": (255, 255, 255),
            "value_color": (255, 215, 0),     # Amarillo del importe ahorrado
            "radius": 28,
            "padding": 22,
            "shadow_blur": 8,
            "shine_opacity": 0.15,
        },
        "amazon_card": {
            "bg_color": (255, 255, 255),
            "border_color": (220, 229, 240),
            "text_label_color": (100, 116, 139),
            "text_name_color": (8, 77, 219),
            "radius": 14,
            "padding": 16,
            "shadow_blur": 6,
        },
        "spacing": {
            "overlap_naranja": 26,            # Solape Y de tarjeta naranja sobre tarjeta azul
            "between_previous_discount": 16,  # Separación corta entre naranja y ahorro
        },
    },

    "footer": {
        "logo_h": 84, "brand_size": 38,
        "pill_h": 46, "pill_font_size": 18,
        "store_font_size": 28,
    },
}


def _s(v, scale):
    return round(v * scale)


def load_font(size, style="Regular"):
    """
    Carga fuentes TrueType del sistema de forma robusta.
    Soporta estilos: Regular, Bold, Italic, BoldItalic.
    """
    fonts_map = {
        "Regular": ["segoeui.ttf", "arial.ttf"],
        "Bold": ["segoeuib.ttf", "arialbd.ttf"],
        "Italic": ["segoeuii.ttf", "ariali.ttf"],
        "BoldItalic": ["segoeuiz.ttf", "arialbi.ttf"]
    }
    
    candidates = fonts_map.get(style, fonts_map["Regular"])
    
    for font_name in candidates:
        try:
            sys_font_path = f"C:\\Windows\\Fonts\\{font_name}"
            return ImageFont.truetype(sys_font_path, size)
        except Exception:
            continue
            
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def _draw_background_decorations(canvas, scale):
    """
    Dibuja ondas celestes concéntricas muy suaves en el fondo
    para emular el fondo de luz de la imagen de referencia.
    """
    W, H = canvas.size
    decor_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(decor_layer)
    
    # 1. Arcos en la esquina superior izquierda (enmarcando el canvas)
    cx, cy = -_s(80, scale), -_s(80, scale)
    for r in [_s(300, scale), _s(500, scale), _s(700, scale), _s(900, scale)]:
        draw.arc([cx - r, cy - r, cx + r, cy + r], start=0, end=90, fill=(37, 99, 235, 18), width=_s(4, scale))
        
    # 2. Círculos concéntricos detrás de la zona del producto (centro-izquierda)
    px, py = int(W * 0.28), int(H * 0.45)
    for r in [_s(300, scale), _s(450, scale), _s(600, scale)]:
        draw.ellipse([px - r, py - r, px + r, py + r], outline=(37, 99, 235, 12), width=_s(2, scale))
        
    # Aplicar un ligero filtro de desenfoque para que las líneas sean suaves y etéreas
    decor_layer = decor_layer.filter(ImageFilter.GaussianBlur(_s(2, scale)))
    canvas.alpha_composite(decor_layer)


def _draw_sparkles_around_circle(draw, cx, cy, radius, scale):
    """
    Dibuja chispas decorativas de color naranja alrededor del círculo de descuento
    tal como se muestra en la imagen de referencia (abajo-izquierda y arriba-derecha).
    """
    color = (255, 110, 0, 240)
    # Ángulos de las chispas en grados (3 abajo-izquierda, 2 arriba-derecha)
    angles = [205, 225, 245, 25, 45]
    for angle in angles:
        rad = math.radians(angle)
        start_dist = radius + _s(12, scale)
        length = _s(14, scale)
        
        x0 = cx + start_dist * math.cos(rad)
        y0 = cy + start_dist * math.sin(rad)
        x1 = cx + (start_dist + length) * math.cos(rad)
        y1 = cy + (start_dist + length) * math.sin(rad)
        
        draw.line([(x0, y0), (x1, y1)], fill=color, width=_s(4, scale))



def _draw_producto(canvas, box, producto_img_path, cfg, scale):
    x0, y0, x1, y1 = box
    max_w = min(_s(cfg["product"]["max_w"], scale), x1 - x0)
    max_h = min(_s(cfg["product"]["max_h"], scale), y1 - y0)

    raw = Image.open(producto_img_path)
    trimmed = trim_image_whitespace(raw)
    fitted = contain_image(trimmed, max_w, max_h)

    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    px, py = cx - fitted.width // 2, cy - fitted.height // 2
    canvas.paste(fitted, (px, py), fitted)


def _draw_titulo(draw, x, y0, categoria, subtitulo, cfg, scale):
    c = cfg["colors"]
    f_cat = load_font(_s(cfg["titulo"]["cat_size"], scale), "ExtraBold")
    draw.text((x, y0), categoria.upper(), font=f_cat, fill=c["azul_marca"])
    cat_bbox = draw.textbbox((x, y0), categoria.upper(), font=f_cat)

    f_sub = load_font(_s(cfg["titulo"]["sub_size"], scale), "SemiBold")
    sub_y = cat_bbox[3] + _s(10, scale)
    draw.text((x, sub_y), subtitulo, font=f_sub, fill=c["gris"])
    sub_bbox = draw.textbbox((x, sub_y), subtitulo, font=f_sub)
    return sub_bbox[3]


def _add_shine(canvas, box, scale, radius=0, shape="rect", opacity=0.22):
    """Brillo diagonal suave, recortado a la forma exacta de la caja (rect
    redondeado o elipse) - el toque 'glossy' que le falta a un color plano."""
    x0, y0, x1, y1 = box
    w, h = max(1, int(x1 - x0)), max(1, int(y1 - y0))

    clip = Image.new("L", (w, h), 0)
    cd = ImageDraw.Draw(clip)
    if shape == "ellipse":
        cd.ellipse([0, 0, w - 1, h - 1], fill=255)
    else:
        cd.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)

    shine = Image.new("L", (w, h), 0)
    sd = ImageDraw.Draw(shine)
    sd.ellipse([-w * 0.2, -h * 0.8, w * 0.7, h * 0.6], fill=int(255 * opacity))
    shine = shine.filter(ImageFilter.GaussianBlur(_s(12, scale)))

    final_mask = ImageChops.multiply(shine, clip)
    white_layer = Image.new("RGB", (w, h), (255, 255, 255))
    canvas.paste(white_layer, (int(x0), int(y0)), final_mask)


def _gradient_shape(canvas, box, color_top, color_bottom, radius=None, shape="rect"):
    """Rellena una caja (rectangulo redondeado o elipse) con un degradado
    vertical. shape='rect' usa 'radius'; shape='ellipse' ignora radius."""
    x0, y0, x1, y1 = box
    w, h = max(1, int(x1 - x0)), max(1, int(y1 - y0))
    grad = Image.new("RGB", (w, h))
    gd = ImageDraw.Draw(grad)
    for i in range(h):
        t = i / max(h - 1, 1)
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * t)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * t)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * t)
        gd.line([(0, i), (w, i)], fill=(r, g, b))
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    if shape == "ellipse":
        md.ellipse([0, 0, w - 1, h - 1], fill=255)
    else:
        md.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius or 0, fill=255)
    canvas.paste(grad, (int(x0), int(y0)), mask)


def _draw_sparkle(draw, cx, cy, r, color):
    """Destello de 4 puntas (decorativo, junto a la caja Ahorras, como en
    la referencia)."""
    pts = [(cx, cy - r), (cx + r * 0.28, cy - r * 0.28), (cx + r, cy),
           (cx + r * 0.28, cy + r * 0.28), (cx, cy + r), (cx - r * 0.28, cy + r * 0.28),
           (cx - r, cy), (cx - r * 0.28, cy - r * 0.28)]
    draw.polygon(pts, fill=color)


def _draw_star(draw, cx, cy, r_outer, color):
    """Estrella de 5 puntas dibujada como poligono - evita depender de que
    la fuente tenga el glifo Unicode ★ (Manrope no lo trae, sale como tofu)."""
    import math
    points = []
    for i in range(10):
        angle = math.pi / 2 + i * math.pi / 5
        r = r_outer if i % 2 == 0 else r_outer * 0.42
        points.append((cx + r * math.cos(angle), cy - r * math.sin(angle)))
    draw.polygon(points, fill=color)


def _draw_tilted(canvas, draw_content_fn, box, angle_deg):
    """Dibuja contenido (via draw_content_fn) sobre una capa del tamano de
    'box', la gira 'angle_deg' grados y la pega centrada en la posicion
    original. Asi conseguimos el efecto 'sello' de la caja Antes en la
    referencia: ligeramente inclinada, no un rectangulo recto."""
    x0, y0, x1, y1 = box
    w, h = int(x1 - x0), int(y1 - y0)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    draw_content_fn(layer, ld, w, h)
    rotated = layer.rotate(angle_deg, expand=True, resample=Image.BICUBIC)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    paste_x = int(cx - rotated.width / 2)
    paste_y = int(cy - rotated.height / 2)
    canvas.paste(rotated, (paste_x, paste_y), rotated)


def _v_center_text(draw, text, font, box_y0, box_y1, features=None):
    try:
        bbox = draw.textbbox((0, 0), text, font=font, features=features or ["tnum"])
    except (KeyError, AttributeError):
        bbox = draw.textbbox((0, 0), text, font=font)
    h = bbox[3] - bbox[1]
    return box_y0 + (box_y1 - box_y0 - h) // 2 - bbox[1]


def _create_shadow(w, h, blur_radius, offset_x=0, offset_y=0, opacity=0.3):
    """Crea una capa de sombra suave."""
    shadow = Image.new("RGBA", (w + abs(offset_x) * 2, h + abs(offset_y) * 2), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow)
    alpha = int(255 * opacity)
    s_draw.rectangle([abs(offset_x), abs(offset_y), abs(offset_x) + w, abs(offset_y) + h], fill=(0, 0, 0, alpha))
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur_radius))
    return shadow


def _draw_card_with_shadow(canvas, box, radius, color_top, color_mid, color_bottom, border_color, 
                           shadow_offset_x, shadow_offset_y, shadow_blur, shine_opacity=0.3, border_width=1):
    """Dibuja una tarjeta con degradado de 3 puntos, borde, sombra y brillo."""
    x0, y0, x1, y1 = box
    w, h = int(x1 - x0), int(y1 - y0)
    
    # Crear capa con la tarjeta
    card_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card_layer)
    
    # Degradado de 3 puntos (superior, medio, inferior)
    grad = Image.new("RGB", (w, h))
    grad_draw = ImageDraw.Draw(grad)
    for i in range(h):
        t = i / max(h - 1, 1)
        if t < 0.5:
            # Primera mitad: color_top a color_mid
            t1 = t * 2
            r = int(color_top[0] + (color_mid[0] - color_top[0]) * t1)
            g = int(color_top[1] + (color_mid[1] - color_top[1]) * t1)
            b = int(color_top[2] + (color_mid[2] - color_top[2]) * t1)
        else:
            # Segunda mitad: color_mid a color_bottom
            t1 = (t - 0.5) * 2
            r = int(color_mid[0] + (color_bottom[0] - color_mid[0]) * t1)
            g = int(color_mid[1] + (color_bottom[1] - color_mid[1]) * t1)
            b = int(color_mid[2] + (color_bottom[2] - color_mid[2]) * t1)
        grad_draw.line([(0, i), (w, i)], fill=(r, g, b))
    
    # Crear máscara con forma redondeada
    mask = Image.new("L", (w, h), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    
    # Aplicar máscara al gradado
    card_layer.paste(grad, (0, 0), mask)
    
    # Añadir borde
    if border_width > 0:
        border_draw = ImageDraw.Draw(card_layer)
        border_draw.rounded_rectangle([0, 0, w - 1, h - 1], outline=border_color, width=border_width)
    
    # Añadir reflejos internos
    shine_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shine_draw = ImageDraw.Draw(shine_layer)
    alpha_top = int(255 * shine_opacity * 0.6)
    shine_draw.ellipse([int(-w * 0.3), int(-h * 0.6), int(w * 0.8), int(h * 0.5)], 
                       fill=(255, 255, 255, alpha_top))
    shine_layer = shine_layer.filter(ImageFilter.GaussianBlur(8))
    card_layer = Image.alpha_composite(card_layer, shine_layer)
    
    # Reflejo inferior sutil
    shine_bottom = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shine_draw_b = ImageDraw.Draw(shine_bottom)
    alpha_bottom = int(255 * shine_opacity * 0.3)
    shine_draw_b.rectangle([0, int(h * 0.85), w, h], fill=(255, 255, 255, alpha_bottom))
    shine_bottom = shine_bottom.filter(ImageFilter.GaussianBlur(4))
    card_layer = Image.alpha_composite(card_layer, shine_bottom)
    
    # Pegar en el canvas
    canvas.paste(card_layer, (int(x0), int(y0)), card_layer)


def _draw_diagonal_strikethrough(draw, bbox, color, width, angle_deg=-15):
    """Dibuja un tachado diagonal basado en el bounding box real del texto."""
    x0, y0, x1, y1 = bbox
    cy = (y0 + y1) / 2
    
    import math
    angle_rad = math.radians(angle_deg)
    
    # Calcular puntos de la línea diagonal
    dx = (x1 - x0) * 0.5
    dy = dx * math.tan(angle_rad)
    
    x_start = x0 - dx * 0.1
    y_start = cy - dy * 0.6
    x_end = x1 + dx * 0.1
    y_end = cy + dy * 0.6
    
    draw.line([(x_start, y_start), (x_end, y_end)], fill=color, width=width)


def _draw_halo(canvas, box, color, blur_radius, opacity=0.15):
    """Dibuja un halo exterior discreto alrededor de una forma."""
    x0, y0, x1, y1 = box
    w, h = int(x1 - x0), int(y1 - y0)
    
    halo = Image.new("RGBA", (w + blur_radius * 4, h + blur_radius * 4), (0, 0, 0, 0))
    halo_draw = ImageDraw.Draw(halo)
    offset = blur_radius * 2
    
    halo_draw.ellipse([offset - blur_radius, offset - blur_radius, 
                       offset + w + blur_radius, offset + h + blur_radius],
                      fill=color + (int(255 * opacity),))
    halo = halo.filter(ImageFilter.GaussianBlur(blur_radius))
    
    canvas.paste(halo, (int(x0 - blur_radius * 2), int(y0 - blur_radius * 2)), halo)


def _draw_precios(draw, canvas, x, y0, x_right, precio_original, precio_oferta, descuento, ahorro, cfg, scale):
    """Dibuja el módulo de precios completo con tarjetas comerciales elaboradas y efectos de la imagen."""
    pc = cfg["precios"]
    box_w = x_right - x
    
    # ========== 1. TARJETA DEL PRECIO ACTUAL (AZUL) ==========
    ahora_h = _s(pc["precio_ahora"]["height"], scale)
    ahora_radius = _s(pc["precio_ahora"]["radius"], scale)
    ahora_padding = _s(pc["precio_ahora"]["padding"], scale)
    
    # Dibujar tarjeta con degradado de 3 puntos, borde y efectos
    _draw_card_with_shadow(
        canvas, 
        (x, y0, x_right, y0 + ahora_h),
        ahora_radius,
        pc["precio_ahora"]["color_top"],
        pc["precio_ahora"]["color_mid"],
        pc["precio_ahora"]["color_bottom"],
        pc["precio_ahora"]["border_color"],
        _s(pc["precio_ahora"]["shadow_offset"][0], scale), 
        _s(pc["precio_ahora"]["shadow_offset"][1], scale),
        _s(pc["precio_ahora"]["shadow_blur"], scale),
        shine_opacity=pc["precio_ahora"]["shine_opacity"],
        border_width=_s(2.5, scale)
    )
    
    # Insignia "PRECIO TOP ★"
    w_insignia = _s(180, scale)
    h_insignia = _s(38, scale)
    insignia_x0 = x + (box_w - w_insignia) // 2
    insignia_y0 = y0 + _s(24, scale)
    
    # Dibujar píldora celeste brillante de la insignia
    draw.rounded_rectangle(
        [insignia_x0, insignia_y0, insignia_x0 + w_insignia, insignia_y0 + h_insignia],
        radius=h_insignia // 2,
        fill=(8, 140, 255) # Azul celeste brillante
    )
    
    f_insignia = load_font(_s(15, scale), "Bold")
    ins_txt = "PRECIO TOP"
    ins_bbox = draw.textbbox((0, 0), ins_txt, font=f_insignia)
    ins_tw = ins_bbox[2] - ins_bbox[0]
    ins_th = ins_bbox[3] - ins_bbox[1]
    
    # Dibujar estrella con polígono a la derecha del texto
    star_r = _s(7.5, scale)
    gap_star = _s(8, scale)
    total_ins_w = ins_tw + gap_star + star_r * 2
    
    start_ins_x = insignia_x0 + (w_insignia - total_ins_w) // 2
    text_ins_y = insignia_y0 + (h_insignia - ins_th) // 2 - ins_bbox[1]
    draw.text((start_ins_x, text_ins_y), ins_txt, font=f_insignia, fill=(255, 255, 255))
    
    star_cx = start_ins_x + ins_tw + gap_star + star_r
    star_cy = insignia_y0 + h_insignia // 2
    _draw_star(draw, star_cx, star_cy, star_r, (255, 255, 255))
    
    # Precio actual (centrado horizontalmente)
    ahora_txt = format_price(precio_oferta)
    f_ahora, _ = fit_font_to_width(
        draw, ahora_txt, "Bold", 
        box_w - 2 * ahora_padding,
        _s(pc["precio_ahora"]["size_max"], scale), 
        _s(pc["precio_ahora"]["size_min"], scale)
    )
    
    abbox = draw.textbbox((0, 0), ahora_txt, font=f_ahora)
    price_w = abbox[2] - abbox[0]
    price_height = abbox[3] - abbox[1]
    price_x = x + (box_w - price_w) // 2 - abbox[0]
    price_y = y0 + h_insignia + _s(42, scale) - abbox[1]
    draw.text((price_x, price_y), ahora_txt, font=f_ahora, fill=(255, 255, 255))
    
    # ========== 2. TARJETA DEL PRECIO ANTERIOR (NARANJA) ==========
    y1 = y0 + ahora_h + _s(pc["spacing"]["between_current_previous"], scale)
    antes_h = _s(pc["precio_antes"]["height"], scale)
    antes_radius = _s(pc["precio_antes"]["radius"], scale)
    antes_padding = _s(pc["precio_antes"]["padding"], scale)
    
    antes_txt = format_price(precio_original)
    f_antes, _ = fit_font_to_width(
        draw, antes_txt, "Bold",
        box_w - 2 * antes_padding,
        _s(pc["precio_antes"]["size_max"], scale),
        _s(pc["precio_antes"]["size_min"], scale)
    )
    
    # Calcular ancho de la tarjeta naranja y centrarla
    antes_tbbox = draw.textbbox((0, 0), antes_txt, font=f_antes)
    antes_tw = antes_tbbox[2] - antes_tbbox[0]
    antes_w = min(box_w * 0.75, antes_tw + 2 * antes_padding)
    antes_x0 = x + (box_w - antes_w) // 2
    
    _draw_card_with_shadow(
        canvas,
        (antes_x0, y1, antes_x0 + antes_w, y1 + antes_h),
        antes_radius,
        pc["precio_antes"]["color_top"],
        pc["precio_antes"]["color_top"],  # Naranja brillante degradado a rojo anaranjado
        pc["precio_antes"]["color_bottom"],
        pc["precio_antes"]["border_color"],
        0,
        _s(2, scale),
        _s(pc["precio_antes"]["shadow_blur"], scale),
        shine_opacity=pc["precio_antes"]["shine_opacity"],
        border_width=_s(1.5, scale)
    )
    
    # Precio anterior centrado en su tarjeta naranja
    antes_x_pos = antes_x0 + (antes_w - antes_tw) // 2 - antes_tbbox[0]
    antes_y = y1 + (antes_h - (antes_tbbox[3] - antes_tbbox[1])) // 2 - antes_tbbox[1]
    draw.text((antes_x_pos, antes_y), antes_txt, font=f_antes, fill=(255, 255, 255))
    
    # Tachado diagonal (azul marino oscuro, cruzando el precio)
    strike_bbox = draw.textbbox((antes_x_pos, antes_y), antes_txt, font=f_antes)
    strike_width = max(2, _s(3.5, scale))
    _draw_diagonal_strikethrough(draw, strike_bbox, pc["precio_antes"]["strike_color"], strike_width, angle_deg=-12)
    
    # ========== 3. BLOQUE DE DESCUENTO Y AHORRO ==========
    y2 = y1 + antes_h + _s(pc["spacing"]["between_previous_discount"], scale)
    
    # Círculo de descuento a la izquierda
    d = _s(pc["descuento"]["diameter"], scale)
    x_circle = x + _s(10, scale)
    
    # Rectángulo de ahorro oscuro a la derecha
    overlap = int(d * pc["descuento"]["overlap_percent"])
    ahorro_x0 = x_circle + d - overlap
    ahorro_x1 = x_right
    ahorro_h = d
    
    ahorro_radius = _s(pc["ahorro"]["radius"], scale)
    
    # Dibujar tarjeta de ahorro oscura
    _draw_card_with_shadow(
        canvas,
        (ahorro_x0, y2, ahorro_x1, y2 + ahorro_h),
        ahorro_radius,
        pc["ahorro"]["color_bg"],
        pc["ahorro"]["color_bg"],
        pc["ahorro"]["color_accent"],
        pc["ahorro"]["color_accent"],
        0,
        _s(2, scale),
        _s(pc["ahorro"]["shadow_blur"], scale),
        shine_opacity=pc["ahorro"]["shine_opacity"],
        border_width=_s(1.5, scale)
    )
    
    # Texto de Ahorro alineado a la derecha del solape
    ahorro_padding = _s(pc["ahorro"]["padding"], scale)
    f_ahorro_label = load_font(_s(15, scale), "Regular")
    f_ahorro_val = load_font(_s(26, scale), "Bold")
    
    ahorro_val_txt = format_price(ahorro)
    ahorro_label_txt = "Ahorras"
    
    label_bbox = draw.textbbox((0, 0), ahorro_label_txt, font=f_ahorro_label)
    val_bbox = draw.textbbox((0, 0), ahorro_val_txt, font=f_ahorro_val)
    
    label_h = label_bbox[3] - label_bbox[1]
    val_h = val_bbox[3] - val_bbox[1]
    
    text_gap = _s(4, scale)
    total_text_h = label_h + text_gap + val_h
    
    # Posicionar textos dentro de la tarjeta de ahorro
    start_text_y = y2 + (ahorro_h - total_text_h) // 2
    label_y = start_text_y - label_bbox[1]
    val_y = start_text_y + label_h + text_gap - val_bbox[1]
    
    # Alinear textos a la izquierda en la zona no solapada
    text_x_pos = ahorro_x0 + overlap + _s(16, scale)
    draw.text((text_x_pos, label_y), ahorro_label_txt, font=f_ahorro_label, fill=pc["ahorro"]["label_color"])
    draw.text((text_x_pos, val_y), ahorro_val_txt, font=f_ahorro_val, fill=pc["ahorro"]["value_color"])
    
    # Dibujar Círculo de descuento
    circle_layer = Image.new("RGBA", (d + _s(4, scale), d + _s(4, scale)), (0, 0, 0, 0))
    circle_draw = ImageDraw.Draw(circle_layer)
    
    circle_grad = Image.new("RGB", (d, d))
    circle_grad_draw = ImageDraw.Draw(circle_grad)
    
    center = d // 2
    for i in range(center, 0, -1):
        t = 1 - (i / center)
        r = int(pc["descuento"]["color_top"][0] + (pc["descuento"]["color_bottom"][0] - pc["descuento"]["color_top"][0]) * t)
        g = int(pc["descuento"]["color_top"][1] + (pc["descuento"]["color_bottom"][1] - pc["descuento"]["color_top"][1]) * t)
        b = int(pc["descuento"]["color_top"][2] + (pc["descuento"]["color_bottom"][2] - pc["descuento"]["color_top"][2]) * t)
        circle_grad_draw.ellipse([center - i, center - i, center + i, center + i], fill=(r, g, b))
    
    circle_mask = Image.new("L", (d, d), 0)
    circle_mask_draw = ImageDraw.Draw(circle_mask)
    circle_mask_draw.ellipse([0, 0, d - 1, d - 1], fill=255)
    circle_layer.paste(circle_grad, (2, 2), circle_mask)
    
    circle_draw.ellipse([2, 2, d + 1, d + 1], outline=pc["descuento"]["border_color"], width=_s(2.5, scale))
    
    circle_shadow = _create_shadow(d, d, _s(pc["descuento"]["shadow_blur"], scale), 0, 3, opacity=0.3)
    canvas.paste(circle_shadow, (int(x_circle - 2), int(y2 - 2)), circle_shadow)
    canvas.paste(circle_layer, (int(x_circle), int(y2)), circle_layer)
    
    # Dibujar anillo discontinuo exterior de color naranja alrededor del círculo amarillo
    anillo_r = (d // 2) + _s(8, scale)
    anillo_cx, anillo_cy = x_circle + d // 2, y2 + d // 2
    for angle in range(0, 360, 15):
        draw.arc(
            [anillo_cx - anillo_r, anillo_cy - anillo_r, anillo_cx + anillo_r, anillo_cy + anillo_r],
            start=angle, end=angle + 8,
            fill=(255, 110, 0, 200),
            width=_s(1.8, scale)
        )
    
    # Dibujar chispas de color naranja alrededor del círculo
    _draw_sparkles_around_circle(draw, anillo_cx, anillo_cy, d // 2, scale)
    
    # Texto del descuento en el círculo (-19%)
    pct_txt = f"-{descuento}%"
    f_pct = load_font(_s(pc["descuento"]["font_size"], scale), "Bold")
    pct_bbox = draw.textbbox((0, 0), pct_txt, font=f_pct)
    pw, ph = pct_bbox[2] - pct_bbox[0], pct_bbox[3] - pct_bbox[1]
    pct_x = x_circle + (d - pw) // 2 - pct_bbox[0]
    pct_y = y2 + (d - ph) // 2 - pct_bbox[1]
    draw.text((pct_x, pct_y), pct_txt, font=f_pct, fill=pc["descuento"]["font_color"])
    
    # Retornar la altura total del módulo
    return y2 + ahorro_h



def _draw_footer(draw, canvas, canal_nombre, logo_path, tienda_nombre, tienda_logo_path, footer_box, cfg, scale):
    c = cfg["colors"]
    x0, y0, x1, y1 = footer_box
    fh = cfg["footer"]

def _draw_footer(draw, canvas, canal_nombre, logo_path, tienda_nombre, tienda_logo_path, footer_box, cfg, scale):
    c = cfg["colors"]
    x0, y0, x1, y1 = footer_box
    fh = cfg["footer"]

    logo_h = _s(fh["logo_h"], scale)
    x = x0
    
    # 1. Logo circular del canal (BC Tech)
    if logo_path and os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        logo = ImageOps.fit(logo, (logo_h, logo_h), method=Image.LANCZOS)
        canvas.paste(logo, (x, y0), logo)
        x += logo_h + _s(20, scale)
    else:
        # Si no hay logo, dejamos un margen por defecto
        x += _s(10, scale)

    # Coordenada x de alineación para la marca y la píldora
    x_start = x

    # 2. Nombre de marca: "BuenChollo" (negro) + "Tech" (azul) en BoldItalic
    f_marca = load_font(_s(fh["brand_size"], scale), "BoldItalic")
    parte1, parte2 = "BuenChollo", "Tech"
    
    # Calcular alturas de texto para posicionamiento vertical preciso
    bbox1 = draw.textbbox((0, 0), parte1 + " ", font=f_marca)
    brand_h = bbox1[3] - bbox1[1]
    
    # El texto de marca va arriba en la columna de la derecha del logo
    marca_y = y0 + _s(4, scale) - bbox1[1]
    draw.text((x_start, marca_y), parte1 + " ", font=f_marca, fill=(15, 23, 42))
    w1 = draw.textlength(parte1 + " ", font=f_marca)
    draw.text((x_start + w1, marca_y), parte2, font=f_marca, fill=c["azul_marca"])

    # 3. Píldora de Telegram, debajo de la marca y alineada con ella
    pill_y = y0 + brand_h + _s(20, scale)
    pill_h = _s(fh["pill_h"], scale)
    pill_txt = "TU CANAL DE CHOLLOS TECH"
    f_pill = load_font(_s(fh["pill_font_size"], scale), "Bold")
    pbbox = draw.textbbox((0, 0), pill_txt, font=f_pill)
    
    plane_r = _s(10, scale)
    pill_w = (plane_r * 2) + _s(10, scale) + (pbbox[2] - pbbox[0]) + _s(44, scale)
    
    # Dibujar fondo redondeado de la píldora azul
    draw.rounded_rectangle(
        (x_start, pill_y, x_start + pill_w, pill_y + pill_h),
        radius=pill_h // 2,
        fill=c["azul_marca"]
    )
    
    # Dibujar icono del avión de papel en la píldora
    pcx, pcy = x_start + _s(22, scale), pill_y + pill_h // 2
    draw.polygon([
        (pcx - plane_r, pcy - plane_r * 0.6), (pcx + plane_r, pcy),
        (pcx - plane_r, pcy + plane_r * 0.6), (pcx - plane_r * 0.4, pcy),
    ], fill=(255, 255, 255))
    
    # Dibujar el texto de la píldora
    draw.text(
        (x_start + _s(40, scale), pill_y + (pill_h - (pbbox[3] - pbbox[1])) // 2 - pbbox[1]),
        pill_txt,
        font=f_pill,
        fill=(255, 255, 255)
    )

    # 4. Tarjeta de Amazon (a la derecha)
    x_right = x1
    
    # Primero intentamos pegar la tarjeta pre-renderizada de Amazon para fidelidad del 100%
    amazon_extracted_path = "tienda_amazon.png"
    if tienda_nombre == "Amazon" and os.path.exists(amazon_extracted_path):
        amazon_card_img = Image.open(amazon_extracted_path).convert("RGBA")
        # Mantener proporciones pero ajustar el alto del footer si es necesario
        target_h = _s(100, scale)
        target_w = int(amazon_card_img.width * (target_h / amazon_card_img.height))
        amazon_card_resized = amazon_card_img.resize((target_w, target_h), resample=Image.LANCZOS)
        
        # Posicionar en la esquina inferior derecha
        paste_x = x_right - target_w
        paste_y = y1 - target_h
        canvas.paste(amazon_card_resized, (paste_x, paste_y), amazon_card_resized)
    else:
        # Fallback de dibujo dinámico para otras tiendas o si no existe la imagen
        f_label = load_font(_s(15, scale), "Regular")
        f_tienda = load_font(_s(24, scale), "Bold")
        
        label_txt = "Disponible en"
        lbbox = draw.textbbox((0, 0), label_txt, font=f_label)
        tbbox = draw.textbbox((0, 0), tienda_nombre, font=f_tienda)
        
        lw = lbbox[2] - lbbox[0]
        tw = tbbox[2] - tbbox[0]
        lh = lbbox[3] - lbbox[1]
        th = tbbox[3] - tbbox[1]
        
        # Tarjeta blanca redondeada
        card_w = max(lw, tw) + _s(48, scale)
        card_h = lh + th + _s(24, scale)
        
        card_x0 = x_right - card_w
        card_y0 = y1 - card_h
        
        # Sombra
        shadow = _create_shadow(card_w, card_h, _s(6, scale), 0, 3, opacity=0.15)
        canvas.paste(shadow, (card_x0 - _s(2, scale), card_y0 - _s(2, scale)), shadow)
        
        # Fondo y borde
        draw.rounded_rectangle(
            [card_x0, card_y0, x_right, y1],
            radius=_s(14, scale),
            fill=(255, 255, 255),
            outline=(220, 229, 240),
            width=_s(1.5, scale)
        )
        # Textos de la tarjeta
        draw.text((card_x0 + (card_w - lw) // 2, card_y0 + _s(10, scale) - lbbox[1]),
                  label_txt, font=f_label, fill=(100, 116, 139))
        draw.text((card_x0 + (card_w - tw) // 2, card_y0 + _s(10, scale) + lh + _s(4, scale) - tbbox[1]),
                  tienda_nombre, font=f_tienda, fill=(8, 77, 219) if tienda_nombre == "Amazon" else (17, 24, 39))


def generar_post_v3(
    producto_img_path: str,
    precio_original: float,
    precio_oferta: float,
    output_path: str,
    categoria: str = "",
    subtitulo: str = "",
    canal_nombre: str = "BuenChollo Tech",
    logo_path: str = "logo_telegram.png",
    tienda_nombre: str = "Amazon",
    tienda_logo_path: str = "tienda_amazon.png",
    cfg: dict = CONFIG,
):
    if precio_oferta >= precio_original:
        raise ValueError("precio_oferta debe ser menor que precio_original.")

    scale = cfg["canvas"]["scale"]
    W, H = cfg["canvas"]["w"] * scale, cfg["canvas"]["h"] * scale
    margin = _s(cfg["margin"], scale)

    descuento = round((1 - precio_oferta / precio_original) * 100)
    ahorro = precio_original - precio_oferta

    # 1. Crear canvas con fondo blanco
    canvas = Image.new("RGBA", (W, H), cfg["bg"] + (255,))
    draw = ImageDraw.Draw(canvas)

    # 2. Dibujar ondas celestes concéntricas de fondo (glow premium)
    _draw_background_decorations(canvas, scale)

    # 3. Calcular caja del footer y del producto
    footer_h = _s(cfg["footer"]["logo_h"] + 12 + cfg["footer"]["pill_h"], scale)
    footer_box = (margin, H - margin - footer_h, W - margin, H - margin)

    # El producto ocupa la mitad izquierda del banner
    left_w = int(W * 0.45)
    producto_box = (margin, margin, margin + left_w, footer_box[1] - _s(20, scale))
    _draw_producto(canvas, producto_box, producto_img_path, cfg, scale)

    # 4. Dibujar precios (a la derecha) centrándolos en vertical
    text_x0 = margin + left_w + _s(48, scale)
    
    if categoria and subtitulo:
        y_after_titulo = _draw_titulo(draw, text_x0, margin + _s(10, scale), categoria, subtitulo, cfg, scale)
        y_start_precios = y_after_titulo + _s(30, scale)
    else:
        # Centrar verticalmente en el espacio disponible a la derecha
        stack_h = _s(cfg["precios"]["precio_ahora"]["height"] + 
                     cfg["precios"]["precio_antes"]["height"] + 
                     cfg["precios"]["descuento"]["diameter"] + 
                     cfg["precios"]["spacing"]["between_current_previous"] + 
                     cfg["precios"]["spacing"]["between_previous_discount"], scale)
        y_start_precios = margin + ((footer_box[1] - margin) - stack_h) // 2

    _draw_precios(
        draw, canvas, text_x0, y_start_precios, W - margin,
        precio_original, precio_oferta, descuento, ahorro, cfg, scale
    )

    # 5. Dibujar el footer con marca, píldora y tarjeta de tienda
    _draw_footer(draw, canvas, canal_nombre, logo_path, tienda_nombre, tienda_logo_path, footer_box, cfg, scale)

    # 6. Guardar la imagen en el tamaño deseado con redimensionado LANCZOS de alta calidad
    final = canvas.convert("RGB").resize((cfg["canvas"]["w"], cfg["canvas"]["h"]), resample=Image.LANCZOS)
    final.save(output_path)
    return output_path


def generar_banner_chollo(
    producto_path: str,
    precio_antes: float,
    precio_ahora: float,
    output_path: str = "banner_final.png",
    categoria: str = None,
    subtitulo: str = None
):
    """
    Función de plantilla de alto nivel y fácil uso para generar banners de ofertas.
    Usa por defecto el logo de BC Tech y la tarjeta de Amazon extraídos.
    """
    return generar_post_v3(
        producto_img_path=producto_path,
        precio_original=precio_antes,
        precio_oferta=precio_ahora,
        output_path=output_path,
        categoria=categoria or "",
        subtitulo=subtitulo or "",
        logo_path="logo_telegram.png",
        tienda_nombre="Amazon",
        tienda_logo_path="tienda_amazon.png"
    )


if __name__ == "__main__":
    # ============================================================
    # PLANTILLA INTERACTIVA - CAMBIA ESTOS TEXTOS Y VALORES
    # ============================================================
    PRODUCTO_IMG = "producto_test.png"      # Imagen del producto
    PRECIO_ANTES = 65.99                    # Precio original antes de la oferta
    PRECIO_AHORA = 53.29                    # Precio actual de la oferta
    OUTPUT_FILE  = "v3_normal.png"          # Nombre del archivo de salida
    
    # Textos opcionales (dejar en None o "" para que se vea igual a la imagen)
    CATEGORIA    = None                     # Ej: "Gaming"
    SUBTITULO    = None                     # Ej: "Mando inalámbrico RGB"

    # Generar el banner con la plantilla premium
    print("Generando banner con diseño premium...")
    generar_banner_chollo(
        producto_path=PRODUCTO_IMG,
        precio_antes=PRECIO_ANTES,
        precio_ahora=PRECIO_AHORA,
        output_path=OUTPUT_FILE,
        categoria=CATEGORIA,
        subtitulo=SUBTITULO
    )
    print(f"¡Banner premium generado con éxito en: {OUTPUT_FILE}!")