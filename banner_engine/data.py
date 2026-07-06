"""Datos de la oferta: validación y normalización.

Única fuente de verdad para los datos de entrada del banner. Acepta
diccionario Python, JSON o instancia de OfferData directamente.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields
from typing import Optional


class OfferDataError(ValueError):
    """Error de validación de los datos de la oferta (mensaje siempre explícito)."""


def parse_price(value) -> float:
    """Convierte '1.299,99 €', '53,29', 53.29 o 53 a float. Lanza OfferDataError si no es parseable."""
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("€", "").replace("EUR", "").strip()
    if not text:
        raise OfferDataError(f"Precio vacío o con formato no válido: {value!r}")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError as exc:
        raise OfferDataError(f"Precio con formato no válido: {value!r}") from exc


def format_price(value: float) -> str:
    """Formatea un float como precio en español: 1234.5 -> '1.234,50 €'."""
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted} €"


def parse_percent(value) -> int:
    """Convierte '-19%', '19%', 19, -19 a un entero de descuento positivo (19)."""
    if isinstance(value, (int, float)):
        return abs(round(value))
    text = str(value).strip().replace("%", "").replace("-", "").strip()
    try:
        return abs(round(float(text)))
    except ValueError as exc:
        raise OfferDataError(f"Porcentaje de descuento con formato no válido: {value!r}") from exc


REQUIRED_FIELDS = ("product_image", "current_price", "previous_price")


@dataclass
class OfferData:
    # Fase 5: campos obligatorios de negocio
    product_name: str = ""
    product_image: str = ""
    current_price: str = ""
    previous_price: str = ""
    discount_percentage: Optional[str] = None
    saving_amount: Optional[str] = None
    affiliate_url: str = ""
    category: str = ""
    subcategory: str = ""

    # Extras de composición (footer / marca) con valores por defecto sensatos
    brand_name: str = "BuenChollo Tech"
    brand_logo: str = "static/images/logo_telegram.png"
    store_name: str = "Amazon"
    store_logo: str = "static/images/tienda_amazon.png"

    @classmethod
    def from_dict(cls, data: dict) -> "OfferData":
        known = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    @classmethod
    def from_json(cls, path: str) -> "OfferData":
        if not os.path.isfile(path):
            raise OfferDataError(f"No existe el archivo JSON de datos: {path}")
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    def validate(self) -> None:
        missing = [name for name in REQUIRED_FIELDS if not getattr(self, name)]
        if missing:
            raise OfferDataError(f"Faltan variables obligatorias: {', '.join(missing)}")
        if not os.path.isfile(self.product_image):
            raise OfferDataError(f"No existe la imagen de producto: {self.product_image}")
        # Fuerza el parseo de precios ahora para fallar con un mensaje claro, no más tarde.
        parse_price(self.current_price)
        parse_price(self.previous_price)
        for logo_attr in ("brand_logo", "store_logo"):
            logo_path = getattr(self, logo_attr)
            if logo_path and not os.path.isfile(logo_path):
                raise OfferDataError(f"No existe el recurso '{logo_attr}': {logo_path}")


def _price_size_class(display: str) -> str:
    length = len(display)
    if length <= 6:
        return "price-xl"
    if length <= 8:
        return "price-lg"
    if length <= 10:
        return "price-md"
    return "price-sm"


@dataclass
class ResolvedOffer:
    """Valores ya calculados y listos para pasar directamente a la plantilla Jinja2."""

    product_name: str
    affiliate_url: str
    category: str
    subcategory: str
    brand_name: str
    store_name: str

    current_price_display: str
    current_price_class: str
    previous_price_display: str
    previous_price_class: str
    discount_display: str
    discount_class: str
    saving_display: str


def resolve(offer: OfferData) -> ResolvedOffer:
    """Valida y calcula todos los valores derivados (descuento, ahorro, clases CSS)."""
    offer.validate()

    current_value = parse_price(offer.current_price)
    previous_value = parse_price(offer.previous_price)
    if current_value >= previous_value:
        raise OfferDataError(
            f"El precio actual ({current_value}) debe ser menor que el precio anterior ({previous_value})"
        )

    current_display = format_price(current_value)
    previous_display = format_price(previous_value)

    if offer.discount_percentage is not None:
        discount_value = parse_percent(offer.discount_percentage)
    else:
        discount_value = round((1 - current_value / previous_value) * 100)
    discount_display = f"-{discount_value}%"

    if offer.saving_amount is not None:
        saving_display = format_price(parse_price(offer.saving_amount))
    else:
        saving_display = format_price(previous_value - current_value)

    return ResolvedOffer(
        product_name=offer.product_name,
        affiliate_url=offer.affiliate_url,
        category=offer.category,
        subcategory=offer.subcategory,
        brand_name=offer.brand_name,
        store_name=offer.store_name,
        current_price_display=current_display,
        current_price_class=_price_size_class(current_display),
        previous_price_display=previous_display,
        previous_price_class=_price_size_class(previous_display),
        discount_display=discount_display,
        discount_class=_price_size_class(discount_display),
        saving_display=saving_display,
    )
