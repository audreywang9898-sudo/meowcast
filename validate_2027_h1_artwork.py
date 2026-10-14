"""Offline validation of the 2027 H1 Taipei holiday artwork routing.

Runs without weather API, Instagram, or Facebook access.
"""
import json
from pathlib import Path
from PIL import Image
import render
from calendar_events import event_for_date
from city_config import load_city_config
from caption import theme

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "asset/taipei"
MANIFEST = BASE / "2027-h1/artwork-manifest.json"
OUT = ROOT / "dry-run/2027-h1"


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = manifest["images"]
    assert len(records) == 31, f"Expected 31 images, found {len(records)}"
    city = load_city_config("taipei")
    assert city["holiday_mode"] is True
    assert city["asset_prefix"] == "asset/taipei"
    seen = set()
    OUT.mkdir(parents=True, exist_ok=True)
    for entry in records:
        day, asset, key = entry["date"], entry["asset"], entry["key"]
        assert asset not in seen, f"Duplicate asset: {asset}"
        seen.add(asset)
        candidate = BASE / asset
        assert candidate.is_file(), f"Missing: {candidate}"
        with Image.open(candidate) as im:
            im.verify()
        ev = event_for_date(day)
        assert ev is not None, f"Calendar missing {day}"
        is_primary = ev.get("asset") == asset
        if is_primary:
            period, selected = "morning", ev
        else:
            secondary = next((x for x in ev.get("also", []) if x.get("asset") == asset), None)
            assert secondary, f"Calendar has no secondary {asset}"
            period, selected = "evening", {**secondary, "_use_evening_artwork": True}
        assert selected.get("key") == key, f"Key mismatch: {day}"
        weather = {"date": day, "code": 2, "high": 26, "low": 20, "rain": 30,
                   "temperature": 24, "period": period}
        t = theme(weather)
        resolved, _ = render.asset_for(t, selected, period=period, date_str=day, city=city)
        expected = str(candidate)
        assert Path(resolved).resolve() == candidate.resolve(), (
            f"Wrong artwork on {day}/{period}: {resolved} != {expected}"
        )
        # Match the production crop/overlay composition, without publishing.
        with Image.open(resolved) as im:
            im = im.convert("RGB")
            scale = max(render.W / im.width, render.H / im.height)
            im = im.resize((int(im.width * scale), int(im.height * scale)))
            x, y = (im.width - render.W) // 2, (im.height - render.H) // 2
            im = im.crop((x, y, x + render.W, y + render.H))
            render.add_weather_overlay(im, weather, t, selected, city=city)
            dest = OUT / f"{day}_{period}_{key}.jpg"
            im.save(dest, quality=88)
        print(f"PASS {day} {period}: {asset}")
    assert len(list(OUT.glob("*.jpg"))) == 31
    print("PASS: 31 artwork paths, 31 decoded PNGs, 31 selections, 31 rendered previews")


if __name__ == "__main__":
    main()
