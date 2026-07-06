"""Punto de entrada: python -m banner_engine.cli examples/offer_data.json [output.png]"""
from __future__ import annotations

import sys

from .data import OfferData, OfferDataError
from .render import RenderError, render_png


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print("Uso: python -m banner_engine.cli <datos.json> [salida.png] [preset]", file=sys.stderr)
        return 2

    json_path = argv[0]
    output_path = argv[1] if len(argv) > 1 else "output/offer_banner.png"
    preset_name = argv[2] if len(argv) > 2 else "square_1200x1200"

    try:
        offer = OfferData.from_json(json_path)
        result_path = render_png(offer, output_path, preset_name)
    except (OfferDataError, RenderError, NotImplementedError, ValueError) as exc:
        print(f"Error generando el banner: {exc}", file=sys.stderr)
        return 1

    print(f"Banner generado en: {result_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
