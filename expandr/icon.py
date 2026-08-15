from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw


def make_icon(size: int = 64) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = max(2, size // 16)
    draw.rounded_rectangle(
        (margin, margin, size - margin - 1, size - margin - 1),
        radius=size // 5,
        fill=(37, 99, 235, 255),
    )
    bar_w = size // 5
    x0 = size // 2 - bar_w // 2
    draw.rectangle((x0, size // 4, x0 + bar_w, size - size // 4), fill=(255, 255, 255, 255))
    draw.polygon(
        [
            (size // 2, size - size // 6),
            (size // 3, size // 2 + size // 10),
            (size - size // 3, size // 2 + size // 10),
        ],
        fill=(255, 255, 255, 255),
    )
    return image


def icon_bytes() -> bytes:
    buffer = BytesIO()
    make_icon(256).save(buffer, format="PNG")
    return buffer.getvalue()
