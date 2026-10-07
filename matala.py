"""Prepare the 42 Matala assets or render a non-publishing local edition."""
import argparse
import io
import os
from pathlib import Path
import zipfile

from PIL import Image

ASSET_DIR = Path("asset/matala")
CONDITIONS = ("sunny", "cloudy", "rainy", "sunny_evening", "cloudy_evening", "rainy_evening")
EXPECTED = tuple(f"{condition}-{index}.png" for index in range(1, 8) for condition in CONDITIONS)


def validate_image(data, name):
    with Image.open(io.BytesIO(data)) as image:
        if image.format != "PNG" or image.width < 720 or image.height <= image.width:
            raise ValueError(f"Invalid portrait PNG: {name}")
        image.verify()


def validate_artwork():
    missing = [name for name in EXPECTED if not (ASSET_DIR / name).is_file()]
    if missing:
        raise ValueError("Missing Matala artwork: " + ", ".join(missing))
    for name in EXPECTED:
        validate_image((ASSET_DIR / name).read_bytes(), name)
    print("Matala artwork ready: 7 sets x 6 conditions = 42 PNGs")


def import_artwork(archive):
    # Inspect the complete archive before writing; never extract arbitrary paths.
    images = {}
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            name = Path(entry.filename).name
            if entry.is_dir() or name not in EXPECTED:
                continue
            if name in images or entry.file_size > 20 * 1024 * 1024:
                raise ValueError(f"Duplicate or oversized asset: {name}")
            data = bundle.read(entry)
            validate_image(data, name)
            images[name] = data
    missing = set(EXPECTED) - images.keys()
    if missing:
        raise ValueError("Incomplete artwork bundle: " + ", ".join(sorted(missing)))
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for name in EXPECTED:
        (ASSET_DIR / name).write_bytes(images[name])
    validate_artwork()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--import-assets", type=Path, help="Import Matala-Meowcast-42-images.zip")
    parser.add_argument("--check-assets", action="store_true")
    parser.add_argument("--period", choices=("morning", "evening"))
    args = parser.parse_args()
    if args.import_assets:
        import_artwork(args.import_assets)
    if args.check_assets or args.period:
        validate_artwork()
    if args.period:
        os.environ["CITY"] = "matala"
        from render import main as render_edition
        render_edition(args.period)
    if not (args.import_assets or args.check_assets or args.period):
        parser.print_help()


if __name__ == "__main__":
    main()
