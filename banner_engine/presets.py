"""Registro de presets de tamaño/layout del banner.

Solo 'square_1200x1200' está implementado por ahora (petición explícita:
migrar únicamente la plantilla cuadrada v3). Los demás quedan
registrados como referencia para el futuro, sin implementación, para
que añadir un formato nuevo no requiera otro motor de render distinto.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Preset:
    name: str
    width: int
    height: int
    device_scale_factor: int
    template: str
    product_max_w: int
    product_max_h: int


PRESETS = {
    "square_1200x1200": Preset(
        name="square_1200x1200",
        width=1200,
        height=1200,
        device_scale_factor=2,
        template="offer.html",
        product_max_w=520,
        product_max_h=720,
    ),
}

NOT_IMPLEMENTED_PRESETS = ("horizontal_1200x675", "vertical_1080x1350")


def get_preset(name: str) -> Preset:
    if name in NOT_IMPLEMENTED_PRESETS:
        raise NotImplementedError(
            f"El preset '{name}' está reservado para el futuro pero aún no implementado."
        )
    if name not in PRESETS:
        raise ValueError(f"Preset desconocido: {name!r}. Disponibles: {list(PRESETS)}")
    return PRESETS[name]
