"""Render additional synthetic package fixtures (PNG) with adjacent truth files.

    python scripts/make_fixtures.py

Every product, strength, lot and date is fictional and labelled as such on the image. The point is
breadth for the reader-accuracy suite: three different layouts and products, not one lucky image.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WEB = Path(__file__).resolve().parent.parent / "web"
FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

PRODUCTS = [
    {
        "slug": "liraglutide",
        "name": "LIRAGLUTIDE-DEMO INJECTION",
        "strength": "18 mg/3 mL (6 mg/mL)",
        "form": "3 mL prefilled pen",
        "lot": "DEMO-5117",
        "opened_on": "2026-08-14",
        "palette": ((236, 244, 255), (23, 61, 110)),
    },
    {
        "slug": "adalimumab",
        "name": "ADALIMUMAB-DEMO INJECTION",
        "strength": "40 mg/0.4 mL",
        "form": "single-dose prefilled syringe",
        "lot": "DEMO-7730",
        "opened_on": "2026-08-18",
        "palette": ((246, 240, 232), (92, 46, 20)),
    },
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for name in (("arialbd.ttf" if bold else "arial.ttf"), "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def render(product: dict) -> Path:
    bg, ink = product["palette"]
    image = Image.new("RGB", (900, 560), bg)
    draw = ImageDraw.Draw(image)
    draw.rectangle((24, 24, 875, 535), outline=ink, width=4)
    draw.text((48, 44), "SYNTHETIC DEMONSTRATION PACKAGE - NOT FOR HUMAN USE", fill=ink, font=font(24, True))
    draw.text((48, 110), product["name"], fill=ink, font=font(44, True))
    draw.text((48, 190), product["strength"], fill=ink, font=font(34))
    draw.text((48, 245), product["form"], fill=ink, font=font(30))
    draw.text((48, 320), f"Rx only    Lot {product['lot']}", fill=ink, font=font(30))
    draw.text((48, 372), f"Opened {product['opened_on']}", fill=ink, font=font(30))
    draw.text((48, 450), "Fictional package; no real patient, prescription, lot, or product.", fill=ink, font=font(22))
    draw.text((48, 484), "Store refrigerated 2-8 C (36-46 F). Do not freeze.", fill=ink, font=font(22))
    path = WEB / f"package-fixture-{product['slug']}.png"
    image.save(path, optimize=True)
    truth = {"synthetic": True, "name": product["name"], "strength": product["strength"], "form": product["form"], "lot": product["lot"], "opened_on": product["opened_on"]}
    (FIXTURES / f"package-{product['slug']}.truth.json").write_text(json.dumps(truth, indent=2), encoding="utf-8")
    return path


def main() -> int:
    for product in PRODUCTS:
        print("wrote", render(product))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
