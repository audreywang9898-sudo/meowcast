"""Render Sunday weekly pawcasts. Publishing is handled by weekly_publish.py.

Example: python weekly.py --city taipei --issue-date 2026-10-04 --dry-run
Daily data uses the city's local timezone. Missing days abort the preview.
"""
import argparse
import json
import math
import os
import time
from urllib.error import URLError
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont, ImageOps
from city_config import load_city_config

W, H = 1080, 1350
INK, MUTED, GOLD = '#243644', '#657787', '#dc9b36'
ZH_DAYS = ['週一', '週二', '週三', '週四', '週五', '週六', '週日']
EN_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
DAILY_KEYS = ['weather_code', 'temperature_2m_max', 'temperature_2m_min', 'precipitation_probability_max']


def week_dates(issue_date):
    if issue_date.weekday() != 6:
        raise ValueError('Weekly issue date must be a Sunday')
    start = issue_date + timedelta(days=1)
    return [start + timedelta(days=i) for i in range(7)]


def condition(code):
    if code == 0: return '晴朗', 'Clear'
    if code in (1, 2): return '晴時多雲', 'Partly cloudy'
    if code == 3: return '陰天', 'Overcast'
    if code in (45, 48): return '有霧', 'Fog'
    if code in (51, 53, 55): return '毛毛雨', 'Drizzle'
    if code in (56, 57, 66, 67): return '凍雨', 'Freezing rain'
    if code in (61, 63, 65): return '有雨', 'Rain'
    if code in (80, 81, 82): return '陣雨', 'Showers'
    if code in (71, 73, 75, 77, 85, 86): return '降雪', 'Snow'
    if code in (95, 96, 99): return '雷雨', 'Thunderstorms'
    raise ValueError(f'Unknown WMO weather code: {code}')


def fetch_forecast(city):
    params = {'latitude': city['latitude'], 'longitude': city['longitude'],
              'timezone': city['timezone'], 'daily': ','.join(DAILY_KEYS), 'forecast_days': 16}
    url = 'https://api.open-meteo.com/v1/forecast?' + urlencode(params)
    for attempt in range(3):
        try:
            with urlopen(url, timeout=45) as r:
                data = json.load(r)
            data['_retrieved_at'] = datetime.now(ZoneInfo(city['timezone'])).isoformat(timespec='minutes')
            return data
        except (URLError, TimeoutError, ValueError):
            if attempt == 2: raise
            time.sleep(2 * (attempt + 1))


def select_week(data, dates, city):
    if data.get('timezone') != city['timezone']:
        raise ValueError('Weather response timezone does not match city')
    daily = data['daily']
    times = daily['time']
    if len(set(times)) != len(times):
        raise ValueError('Duplicate forecast dates')
    if any(len(daily[k]) != len(times) for k in DAILY_KEYS):
        raise ValueError('Forecast arrays have different lengths')
    rows = []
    for day in dates:
        if day.isoformat() not in times:
            raise ValueError(f'Missing forecast date {day}; refusing to invent data')
        i = times.index(day.isoformat())
        values = [daily[k][i] for k in DAILY_KEYS]
        if any(v is None or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
            raise ValueError(f'Invalid forecast values for {day}')
        code, high, low, rain = values
        if low > high or not 0 <= rain <= 100 or int(code) != code:
            raise ValueError(f'Invalid forecast range for {day}')
        condition(int(code))
        rows.append({'date': day.isoformat(), 'code': int(code), 'high': round(high),
                     'low': round(low), 'rain': round(rain)})
    return rows


def highlights(rows, zh):
    wet = [EN_DAYS[i] for i, r in enumerate(rows) if r['rain'] >= 50]
    wet_zh = [ZH_DAYS[i] for i, r in enumerate(rows) if r['rain'] >= 50]
    best = min(rows, key=lambda r: r['rain'])
    best_i = rows.index(best)
    hottest = max(rows, key=lambda r: r['high'])
    coldest = min(rows, key=lambda r: r['low'])
    if zh:
        return [
            ('雨傘值班表', ('、'.join(wet_zh) + '降雨機率達 50% 以上，記得帶傘。') if wet else '各天最高降雨機率均低於 50%；仍不保證無雨。'),
            ('出遊候選日', f"{ZH_DAYS[best_i]}降雨機率相對最低（{best['rain']}%）。先列候選，出門前再確認。"),
            ('衣櫃備忘錄', f"全週最高 {hottest['high']}°C、最低 {coldest['low']}°C。穿搭看每日預報；貓的毛外套不外借。")]
    return [
        ('Brolly roster', (', '.join(wet) + ': rain chance reaches 50% or more. Pack a brolly.') if wet else 'Daily peak rain chances stay below 50%. That is not a dry-weather guarantee.'),
        ('Outdoor shortlist', f"{EN_DAYS[best_i]} has the lowest rain chance ({best['rain']}%). A candidate, not a promise; check again before heading out."),
        ('Wardrobe memo', f"Weekly high {hottest['high']}°C; weekly low {coldest['low']}°C. Check each day's forecast. My fur coat is not available to borrow.")]


def caption(rows, city, fetched):
    span = rows[0]['date'] + ' – ' + rows[-1]['date']
    en_lines = '\n'.join(f"{EN_DAYS[i]} {r['date'][5:]}: {condition(r['code'])[1]}, high {r['high']}°C / low {r['low']}°C, peak rain chance {r['rain']}%." for i, r in enumerate(rows))
    en = (f"{city['brand']} | Next-week pawcast\n{span}\n"
          "Your week has plans. Mine has seven naps. Let's check the sky first. 🐱\n\n" + en_lines + '\n\n' +
          '\n'.join(title + ': ' + body for title, body in highlights(rows, False)) +
          '\n\nLater dates may change more. Check the daily pawcast before heading out.\n'
          'Enjoy the pawcast? Tap the heart ❤️ and follow for weather with cat attitude every morning and evening. 🐾')
    if city['id'] == 'taipei':
        zh_lines = '\n'.join(f"{ZH_DAYS[i]} {r['date'][5:]}：{condition(r['code'])[0]}，最高 {r['high']}°C／最低 {r['low']}°C，每日最高降雨機率 {r['rain']}%。" for i, r in enumerate(rows))
        zh = ('台北天氣貓｜下週七天喵報\n' + span + '\n'
              '你排下週行程，我排七天午睡。先看看天空有沒有別的安排。🐱\n\n' + zh_lines + '\n\n' +
              '\n'.join(title + '：' + body for title, body in highlights(rows, True)) +
              '\n\n越後面的日期變動可能越大，出門前請看每日喵報。\n'
              '喜歡這隻愛碎念的天氣貓，就幫我點個愛心 ❤️、追蹤台北天氣貓！每天早晚一起看天氣，先問貓再出門。🐾\n'
              f'資料：Open-Meteo｜取得時間 {fetched}\n\n— English pawcast —\n')
        en = zh + en
    return en + f'\n\nSource: Open-Meteo | Retrieved: {fetched}\n' + ' '.join(city['hashtags']) + ' #WeeklyWeather'


def font_path(explicit, zh):
    candidates = [explicit, os.environ.get('WEEKLY_FONT'), 'NotoSansCJKtc-Regular.otf',
                  '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
    if not zh: candidates.append('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    for p in candidates:
        if p and Path(p).is_file(): return p
    raise RuntimeError('Install a CJK font or pass --font for Taipei rendering')


def weather_style(code):
    if code == 0: return 'sunny', '#fff1c9', '#e4a321'
    if code in (1, 2): return 'partly', '#e6f5d9', '#70a65a'
    if code == 3: return 'cloudy', '#e9eef9', '#8e9ecd'
    if code in (45, 48): return 'fog', '#eaf1ef', '#819b99'
    if code in (51, 53, 55): return 'drizzle', '#dff5f5', '#52a6b0'
    if code in (71, 73, 75, 77, 85, 86): return 'snow', '#f0e7fb', '#a58aca'
    if code in (95, 96, 99): return 'storm', '#e8e5f8', '#8e7abb'
    return 'rain', '#e1efff', '#639bda'


def weather_icon(code, size=76):
    """Draw weather-code-specific illustrations without emoji/font dependency."""
    family, _, accent = weather_style(code)
    icon = Image.new('RGBA', (160, 160))
    d = ImageDraw.Draw(icon)
    if code == -1:
        d.polygon([(28, 49), (57, 28), (68, 38), (92, 38), (103, 28), (132, 49),
                   (114, 80), (104, 73), (104, 137), (56, 137), (56, 73), (46, 80)],
                  fill='#b7a0db', outline='#8a6bb9', width=4)
        d.arc((66, 25, 94, 49), 0, 180, fill='#725295', width=4)
        d.line((65, 119, 95, 119), fill='#dcd1ee', width=5)
        return icon.resize((size, size), Image.Resampling.LANCZOS)
    if family in ('sunny', 'partly'):
        cx, cy = (80, 78) if family == 'sunny' else (55, 48)
        for n in range(8):
            angle = n * math.pi / 4
            d.line((cx + 40 * math.cos(angle), cy + 40 * math.sin(angle),
                    cx + 53 * math.cos(angle), cy + 53 * math.sin(angle)), fill='#f0b134', width=7)
        d.ellipse((cx-29, cy-29, cx+29, cy+29), fill='#ffd25a', outline='#e9a62c', width=3)
    if family != 'sunny':
        cloud = '#bfd3e6' if family in ('rain', 'storm') else '#f9fcff'
        edge = '#7d9eb7'
        d.ellipse((25, 61, 81, 109), fill=cloud, outline=edge, width=3)
        d.ellipse((53, 36, 114, 105), fill=cloud, outline=edge, width=3)
        d.ellipse((91, 58, 141, 109), fill=cloud, outline=edge, width=3)
        d.rounded_rectangle((30, 80, 136, 111), radius=15, fill=cloud)
        d.line((41, 109, 125, 109), fill=edge, width=3)
    if family == 'drizzle':
        for x in (43, 68, 93, 118):
            d.line((x, 122, x-3, 128), fill='#5aafb9', width=4)
            d.line((x-7, 140, x-10, 146), fill='#5aafb9', width=4)
    elif family in ('rain', 'storm'):
        for x in (46, 81, 119):
            d.polygon([(x, 119), (x-8, 135), (x+6, 135)], fill='#4c99df')
            d.ellipse((x-8, 128, x+6, 143), fill='#4c99df')
        if family == 'storm': d.polygon([(87, 80), (67, 113), (82, 111), (74, 139), (107, 99), (91, 100)], fill='#ffd157')
    elif family == 'snow':
        for x in (48, 82, 117):
            for angle in (0, math.pi/3, 2*math.pi/3):
                d.line((x-9*math.cos(angle), 134-9*math.sin(angle), x+9*math.cos(angle), 134+9*math.sin(angle)), fill=accent, width=3)
    elif family == 'fog':
        for y in (119, 133, 147): d.rounded_rectangle((30, y, 134, y+4), radius=2, fill=accent)
    return icon.resize((size, size), Image.Resampling.LANCZOS)


def render(rows, city, fetched, art_path, font_file, out, preview=True):
    zh = city['id'] == 'taipei'
    def ft(size): return ImageFont.truetype(font_file, size)
    def put(d, xy, text, size, fill=INK, bold=False):
        if d.textlength(text, font=ft(size)) > W - xy[0] - 56:
            raise ValueError(f'Text too wide: {text}')
        d.text(xy, text, font=ft(size), fill=fill, stroke_width=1 if bold else 0, stroke_fill=fill)
    def wrapped(d, text, x, y, size, width):
        line = ''
        # Word wrapping for English; character wrapping for Chinese.
        units = list(text) if zh else [w + ' ' for w in text.split()]
        for unit in units:
            if line and d.textlength(line + unit, font=ft(size)) > width:
                d.text((x, y), line.strip(), font=ft(size), fill=MUTED)
                y += size + 15
                line = unit
            else: line += unit
        if line: d.text((x, y), line.strip(), font=ft(size), fill=MUTED)
        return y + size + 15

    art = None
    if art_path:
        with Image.open(art_path) as a:
            a.load()
            art = a.convert('RGB')
    paths = []
    for page in [1, 2]:
        im = Image.new('RGB', (W, H), '#fff9f0')
        d = ImageDraw.Draw(im)
        d.ellipse((850, -125, 1230, 260), fill='#ffe8bc')
        d.ellipse((-140, 1060, 220, 1480), fill='#e0f2ef')
        for i, color in enumerate(['#f6c44e', '#91c7b0', '#87b9e7', '#be9bd7']):
            d.rectangle((i*270, 0, (i+1)*270, 12), fill=color)
        for code, x, y in [(0, 775, 100), (2, 880, 170), (53, 965, 65)]:
            icon = weather_icon(code, 86)
            im.paste(icon, (x, y), icon)
        put(d, (58, 34), 'DRY RUN / PREVIEW' if preview else ('週日週報 SUNDAY EDITION' if zh else 'SUNDAY EDITION'), 23, MUTED)
        put(d, (58, 82), '台北天氣貓' if zh else city['brand'], 46)
        put(d, (58, 147), ('下週七天喵報' if page == 1 else '貓咪幫你畫重點') if zh else ('Next-week pawcast' if page == 1 else "The cat's weekly verdict"), 37)
        put(d, (58, 205), f"{rows[0]['date']} — {rows[-1]['date']}  |  {page}/2", 29, MUTED)
        if zh: put(d, (58, 253), 'Taipei Meowcast | Weekly forecast', 23, MUTED)
        if page == 1:
            put(d, (58, 305), '日期 DAY' if zh else 'DAY / DATE', 26, MUTED)
            put(d, (352, 305), '天氣 WEATHER' if zh else 'WEATHER', 26, MUTED)
            put(d, (616, 305), '最高 HIGH' if zh else 'HIGH', 26, '#be4b26', bold=True)
            put(d, (755, 305), '最低 LOW' if zh else 'LOW', 25, MUTED)
            put(d, (904, 305), '雨 RAIN' if zh else 'RAIN', 25, MUTED)
            for i, r in enumerate(rows):
                y = 350 + i * 89
                _, tint, accent = weather_style(r['code'])
                d.rounded_rectangle((48, y, 1032, y + 80), radius=20, fill=tint)
                d.rounded_rectangle((48, y+12, 54, y+68), radius=3, fill=accent)
                put(d, (68, y + 17), (ZH_DAYS[i] if zh else EN_DAYS[i]) + ' ' + r['date'][5:].replace('-', '/'), 31)
                icon = weather_icon(r['code'], 76)
                im.paste(icon, (260, y+2), icon)
                a, b = condition(r['code'])
                put(d, (352, y + 5 if zh else y+18), a if zh else b, 31 if zh else 28)
                if zh: put(d, (352, y + 43), b, 21, MUTED)
                put(d, (616, y - 2), f"{r['high']}°", 50, '#be4b26', bold=True)
                put(d, (755, y + 13), f"{r['low']}°C", 35, '#367fae')
                put(d, (912, y + 13), f"{r['rain']}%", 35, '#287ba1')
            put(d, (58, 997), '雨＝每日最高降雨機率' if zh else 'Rain = daily maximum precipitation probability', 24, MUTED)
        else:
            y = 335
            for index, (title, body) in enumerate(highlights(rows, zh)):
                tint, accent, code = [('#e0f3ff', '#619bd0', 61), ('#fff0ce', '#d69b2e', 0), ('#ede7fb', '#a48bc9', -1)][index]
                d.rounded_rectangle((48, y - 10, 1032, y + 205), radius=28, fill=tint)
                icon = weather_icon(code, 76)
                im.paste(icon, (70, y-1), icon)
                put(d, (162, y + 6), title, 40)
                wrapped(d, body, 78, y + 65, 34, 925)
                y += 225
        # A separate portrait strip keeps cats clear of the forecast table.
        if art:
            box = (int(art.width * .25), int(art.height * .40), art.width, int(art.height * .87))
            portrait = ImageOps.fit(art.crop(box), (240, 280))
            im.paste(portrait, (840, 1070))
        put(d, (58, 1080), '天空負責變天，貓負責碎念。' if zh else 'Forecast first. Nap later.', 34)
        wrapped(d, '喜歡請按愛心、追蹤，每天早晚收看！' if zh else 'Like + follow for daily morning & evening pawcasts.', 58, 1130, 26, 760)
        put(d, (58, 1210), '越後面的日期變動可能越大。' if zh else 'Later dates may change more.', 24, MUTED)
        put(d, (58, 1250), '出門前請看每日喵報。' if zh else 'Check the daily pawcast before heading out.', 24, MUTED)
        put(d, (58, 1300), 'Open-Meteo | ' + fetched, 17, MUTED)
        path = out / f'{city["id"]}-weekly-{page}.png'
        im.save(path)
        if not preview:
            im.save(path.with_suffix('.jpg'), quality=95, subsampling=0)
        paths.append(path)
    return paths


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--city', choices=['taipei', 'melbourne'], required=True)
    p.add_argument('--issue-date', help='Sunday date; defaults to today in Asia/Taipei')
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--production', action='store_true', help='Render JPEG carousel slides; does not publish')
    p.add_argument('--forecast-json', help='Replay a saved real API response')
    p.add_argument('--artwork')
    p.add_argument('--font')
    p.add_argument('--output', default='dry-run/weekly')
    args = p.parse_args()
    city = load_city_config(args.city)
    issue = date.fromisoformat(args.issue_date) if args.issue_date else datetime.now(ZoneInfo('Asia/Taipei')).date()
    dates = week_dates(issue)
    data = json.loads(Path(args.forecast_json).read_text()) if args.forecast_json else fetch_forecast(city)
    fetched = data.get('_retrieved_at', 'Replay: time unknown')
    rows = select_week(data, dates, city)
    out = Path(args.output) / city['id']
    out.mkdir(parents=True, exist_ok=True)
    (out / 'forecast-source.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    (out / 'forecast.json').write_text(json.dumps({'city': city['id'], 'issue_date': issue.isoformat(),
        'timezone': city['timezone'], 'retrieved_at': fetched, 'source': 'Open-Meteo', 'days': rows,
        'mode': 'dry_run' if args.dry_run else 'production', 'published': False}, ensure_ascii=False, indent=2), encoding='utf-8')
    text = caption(rows, city, fetched)
    if len(text) > 2200: raise ValueError('Caption exceeds Instagram limit')
    (out / 'caption.txt').write_text(text, encoding='utf-8')
    default_art = Path(city['asset_prefix']) / 'sunny-2.png'
    art = args.artwork or (str(default_art) if default_art.is_file() else None)
    if args.production and not art: raise RuntimeError('Production weekly artwork is missing')
    images = render(rows, city, fetched, art, font_path(args.font, city['id'] == 'taipei'), out, preview=args.dry_run)
    print(json.dumps({'city': city['id'], 'dates': [r['date'] for r in rows],
        'images': [str(x) for x in images], 'caption': str(out / 'caption.txt'), 'published': False}))


if __name__ == '__main__':
    main()
