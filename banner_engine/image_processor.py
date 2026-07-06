"""Preprocesado de imágenes con Pillow: recorte de márgenes, encaje
proporcional y codificación a base64 para embeber en el HTML (sin
depender de rutas file:// ni de red durante el renderizado).

Reimplementado de forma independiente a template_v2.py (no se importa,
ver plan de migración: el nuevo motor no depende del legacy).
"""
from __future__ import annotations

import base64
import io

from PIL import Image, ImageOps


def trim_whitespace(im: Image.Image, tolerance: int = 8) -> Image.Image:
    """Recorta márgenes blancos o transparentes sobrantes de la imagen de producto."""
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    alpha = im.split()[-1]
    if alpha.getextrema() != (255, 255):
        bbox = alpha.getbbox()
    else:
        gray = im.convert("RGB").convert("L")
        mask = gray.point(lambda p: 0 if p >= (255 - tolerance) else 255)
        bbox = mask.getbbox()
    return im.crop(bbox) if bbox else im


def contain(im: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Redimensiona manteniendo proporción, sin deformar ni recortar."""
    return ImageOps.contain(im, (int(max_w), int(max_h)), method=Image.LANCZOS)


def image_to_data_uri(im: Image.Image, fmt: str = "PNG") -> str:
    buffer = io.BytesIO()
    im.save(buffer, format=fmt)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    mime = "image/png" if fmt.upper() == "PNG" else f"image/{fmt.lower()}"
    return f"data:{mime};base64,{encoded}"


def file_to_data_uri(path: str) -> str:
    with open(path, "rb") as fh:
        encoded = base64.b64encode(fh.read()).decode("ascii")
    mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    return f"data:{mime};base64,{encoded}"


def prepare_product_image(path: str, max_w: int, max_h: int) -> str:
    """Abre, recorta márgenes y encaja la imagen de producto; devuelve un data URI PNG."""
    with Image.open(path) as raw:
        trimmed = trim_whitespace(raw.copy())
    fitted = contain(trimmed, max_w, max_h)
    return image_to_data_uri(fitted, fmt="PNG")
