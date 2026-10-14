"""Update the 21 remaining 2027 H1 festival artworks with a legible brand banner.

Only entries marked original_pending_update in artwork-manifest.json are changed.
The modified images are kept at their original calendar-selected filenames.
"""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

BASE = Path("asset/taipei/2027-h1")
MANIFEST = BASE / "artwork-manifest.json"
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def font_for(size):
    for candidate in FONT_CANDIDATES:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    raise RuntimeError("No bold font installed for branding")


def apply_banner(path):
    with Image.open(path) as original:
        image = original.convert("RGB")
    width, height = image.size
    if width < 500 or height < 850:
        raise ValueError(f"Unexpected artwork dimensions: {path}: {image.size}")

    # Place the brand within the frame, not clipped at the very top.
    # This opaque header masks any old, partially offscreen masthead.
    top = round(height * .035)
    bottom = round(height * .155)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    # Hide previous clipped-at-top logo before drawing the new, lower masthead.
    draw.rectangle((0, 0, width, bottom), fill=(34, 48, 65, 245))
    margin = round(width * .06)
    radius = round(width * .035)
    draw.rounded_rectangle(
        (margin, top, width - margin, bottom),
        radius=radius,
        fill=(34, 48, 65, 238),
        outline=(238, 194, 102, 255),
        width=max(3, round(width * .005)),
    )
    message = "Taipei Meowcast"
    font = font_for(round(width * .075))
    bbox = draw.textbbox((0, 0), message, font=font)
    while bbox[2] - bbox[0] > width * .8:
        font = font_for(font.size - 2)
        bbox = draw.textbbox((0, 0), message, font=font)
    draw.text(
        (width / 2, (top + bottom) / 2),
        message,
        font=font,
        fill=(255, 250, 234, 255),
        anchor="mm",
        stroke_width=max(1, round(width * .0015)),
        stroke_fill=(85, 58, 29, 255),
    )
    result = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    result.save(path, format="PNG", optimize=True)


def main():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pending = [item for item in data["images"] if item.get("brand_status") == "original_pending_update"]
    if len(pending) not in (0, 21):
        raise RuntimeError(f"Unexpected pending artwork count: {len(pending)}")
    for item in pending:
        path = BASE / item["filename"]
        if not path.is_file():
            raise FileNotFoundError(path)
        apply_banner(path)
        with Image.open(path) as image:
            image.verify()
        item["brand_status"] = "updated"
        item["brand_update_method"] = "brand_banner_with_safe_top_margin"
        print("UPDATED", path)
    data["branding"] = {"banner": "Taipei Meowcast", "placement": "upper inset safe area", "pending": 0}
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Processed {len(pending)} images; pending after: 0")


if __name__ == "__main__":
    main()
