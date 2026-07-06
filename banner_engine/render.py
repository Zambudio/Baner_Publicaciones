"""Orquesta: datos -> HTML (Jinja2) -> Chromium headless (Playwright) -> PNG (Pillow)."""
from __future__ import annotations

import os

from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image

from . import fonts as fonts_mod
from . import image_processor
from .data import OfferData, resolve
from .presets import Preset, get_preset

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")
CSS_PATH = os.path.join(PROJECT_ROOT, "static", "css", "offer.css")

_jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
)


class RenderError(RuntimeError):
    """Error explícito durante el renderizado (Chromium, escritura de archivo, etc.)."""


def _read_css() -> str:
    with open(CSS_PATH, "r", encoding="utf-8") as fh:
        return fh.read()


def build_html(offer: OfferData, preset: Preset) -> str:
    """Valida los datos, prepara imágenes/fuentes y renderiza la plantilla Jinja2 a un string HTML."""
    resolved = resolve(offer)

    product_image_uri = image_processor.prepare_product_image(
        offer.product_image, preset.product_max_w, preset.product_max_h
    )
    brand_logo_uri = image_processor.file_to_data_uri(offer.brand_logo)
    store_logo_uri = image_processor.file_to_data_uri(offer.store_logo)

    template = _jinja_env.get_template(preset.template)
    return template.render(
        font_face_css=fonts_mod.font_face_css(),
        offer_css=_read_css(),
        product_image_uri=product_image_uri,
        brand_logo_uri=brand_logo_uri,
        store_logo_uri=store_logo_uri,
        brand_name=resolved.brand_name,
        store_name=resolved.store_name,
        current_price_display=resolved.current_price_display,
        current_price_class=resolved.current_price_class,
        previous_price_display=resolved.previous_price_display,
        previous_price_class=resolved.previous_price_class,
        discount_display=resolved.discount_display,
        discount_class=resolved.discount_class,
        saving_display=resolved.saving_display,
    )


def render_png(offer: OfferData, output_path: str, preset_name: str = "square_1200x1200") -> str:
    """Genera el PNG final. Lanza RenderError con un mensaje claro si algo falla."""
    preset = get_preset(preset_name)
    html = build_html(offer, preset)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RenderError(
            "Playwright no está instalado. Ejecuta: pip install playwright && playwright install chromium"
        ) from exc

    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
            except Exception as exc:
                raise RenderError(
                    "No se pudo lanzar Chromium. ¿Está instalado? Ejecuta: playwright install chromium"
                ) from exc
            try:
                page = browser.new_page(
                    viewport={"width": preset.width, "height": preset.height},
                    device_scale_factor=preset.device_scale_factor,
                )
                page.set_content(html, wait_until="load")
                page.evaluate("document.fonts.ready")
                element = page.locator(".banner")
                screenshot_bytes = element.screenshot()
            finally:
                browser.close()
    except RenderError:
        raise
    except Exception as exc:
        raise RenderError(f"Fallo durante el renderizado con Chromium: {exc}") from exc

    try:
        import io

        with Image.open(io.BytesIO(screenshot_bytes)) as captured:
            final = captured.convert("RGB").resize((preset.width, preset.height), resample=Image.LANCZOS)
            os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
            final.save(output_path)
    except OSError as exc:
        raise RenderError(f"No se pudo escribir el archivo de salida '{output_path}': {exc}") from exc

    return output_path
