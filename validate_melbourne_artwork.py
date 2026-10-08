"""Validate all Melbourne artwork and simulate every weather/period rotation."""
import hashlib
import io
import json
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from city_config import load_city_config
from render import _available_artwork_indices, asset_for, add_weather_overlay


def main():
    city = load_city_config('melbourne')
    manifest = json.loads(Path('asset/melbourne/artwork-manifest.json').read_text())
    for item in manifest['new_artwork']:
        path = Path(item['path'])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], path
        with Image.open(path) as image:
            image.verify()
    checks = 0
    output = Path('output/melbourne-artwork-validation')
    output.mkdir(parents=True, exist_ok=True)
    for period in ('morning', 'evening'):
        suffix = '_evening' if period == 'evening' else ''
        for theme in ('sunny', 'cloudy', 'rainy'):
            available = _available_artwork_indices(city['asset_prefix'], theme, suffix)
            assert available == list(range(1, 15)), (theme, period, available)
            for previous in available:
                cursors = {other: 14 for other in ('sunny', 'cloudy', 'rainy')}
                cursors[theme] = previous
                state = io.BytesIO(json.dumps(cursors).encode())
                with patch('render.urllib.request.urlopen', return_value=state) as read_state:
                    path, index = asset_for(theme, period=period, date_str='2026-10-08', city=city)
                slot = '1630' if period == 'evening' else '0700'
                assert read_state.call_args.args[0].endswith(f'/latest/melbourne/weather-rotation-{slot}.json')
                expected = previous + 1 if previous < 14 else 1
                assert index == expected, (theme, period, previous, index)
                assert path == f'asset/melbourne/{theme}{suffix}-{expected}.png', path
                checks += 1
                if index >= 8:
                    with Image.open(path) as source:
                        image = source.convert('RGB')
                    scale = max(1080 / image.width, 1920 / image.height)
                    image = image.resize((round(image.width * scale), round(image.height * scale)))
                    x, y = (image.width - 1080) // 2, (image.height - 1920) // 2
                    image = image.crop((x, y, x + 1080, y + 1920))
                    weather = {'date': '2026-10-08', 'high': 23, 'low': 12, 'rain': 5, 'period': period}
                    add_weather_overlay(image, weather, theme, city=city)
                    image.save(output / f'{theme}{suffix}-{index}.jpg', quality=90)
    result = {'decoded_artwork': 84, 'new_sha256_verified': 42, 'rotation_checks': checks,
              'preview_cards': len(list(output.glob('*.jpg'))), 'weather': 'synthetic preview',
              'state': 'mocked; production state unchanged', 'published': False}
    assert result['preview_cards'] == 42, result
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
