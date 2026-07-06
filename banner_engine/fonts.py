"""Carga y cachea las fuentes locales (Segoe UI) como base64 para @font-face.

Las fuentes viven en static/fonts/ (copiadas una vez desde el sistema,
ver README.md). Nunca se descargan en tiempo de ejecución.
"""
from __future__ import annotations

import base64
import functools
import os

FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "fonts")

FONT_FILES = {
    "regular": "segoeui.ttf",
    "bold": "segoeuib.ttf",
    "black": "segoeuiz.ttf",
}


@functools.lru_cache(maxsize=None)
def _font_data_uri(filename: str) -> str:
    path = os.path.join(FONTS_DIR, filename)
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"No se encuentra la fuente local '{filename}' en {FONTS_DIR}. "
            "Copia los .ttf de Segoe UI (o su sustituto) antes de renderizar."
        )
    with open(path, "rb") as fh:
        encoded = base64.b64encode(fh.read()).decode("ascii")
    return f"data:font/ttf;base64,{encoded}"


def font_face_css() -> str:
    """Genera el bloque @font-face con las 3 variantes embebidas en base64."""
    weights = {"regular": 400, "bold": 700, "black": 800}
    styles = []
    for variant, filename in FONT_FILES.items():
        data_uri = _font_data_uri(filename)
        styles.append(
            "@font-face {\n"
            "  font-family: 'Segoe UI Local';\n"
            f"  src: url('{data_uri}') format('truetype');\n"
            f"  font-weight: {weights[variant]};\n"
            "  font-style: normal;\n"
            "  font-display: block;\n"
            "}"
        )
    return "\n".join(styles)
