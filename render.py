import os, subprocess, json, urllib.request, re
from datetime import datetime
from PIL import Image,ImageDraw,ImageFont
from weather import get_weather, get_evening_weather
from caption import make_caption, temperature_label
from music import music_for_event
from calendar_events import event_for_date
from city_config import load_city_config

W,H=1080,1920

def font(size):
    for p in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if os.path.exists(p): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def fallback(theme):
    tones={"sunny":(235,196,104),"rainy":(91,119,145),"cloudy":(164,174,181)}
    im=Image.new("RGB",(W,H),tones[theme]); d=ImageDraw.Draw(im)
    d.ellipse((290,570,790,1070),fill=(238,238,232)); d.ellipse((335,480,500,680),fill=(238,238,232)); d.ellipse((580,480,745,680),fill=(238,238,232))
    d.ellipse((390,690,455,755),fill=(35,35,35)); d.ellipse((625,690,690,755),fill=(35,35,35)); d.polygon([(520,790),(560,790),(540,825)],fill=(215,130,140))
    d.text((330,1120),"MEOW",font=font(100),fill="white")
    return im

def _valid_artwork_file(path):
    """Return True only for a non-trivial image Pillow can actually decode."""
    try:
        if not os.path.isfile(path) or os.path.getsize(path)<=1024:
            return False
        with Image.open(path) as im:
            im.verify()
        return True
    except Exception as exc:
        print(f"Skipping invalid artwork {path}: {exc}")
        return False


def _available_artwork_indices(asset_prefix, theme, suffix=""):
    """Return sorted decodable artwork indices that actually exist on disk."""
    directory=asset_prefix or "."
    if not os.path.isdir(directory):
        return []
    pattern=re.compile(rf"^{re.escape(theme+suffix)}-(\d+)\.(?:png|jpg)$",re.IGNORECASE)
    indices=set()
    for name in os.listdir(directory):
        match=pattern.match(name)
        if not match:
            continue
        path=os.path.join(directory,name)
        if _valid_artwork_file(path):
            indices.add(int(match.group(1)))
    return sorted(indices)

def _rotation_state(theme, date_str, period, city=None, available_indices=None):
    """Return the next artwork index from the files that actually exist.

    Morning/evening and sunny/cloudy/rainy each keep their own cursor. The
    cursor advances only after a successful Instagram publish.
    """
    city=city or load_city_config()
    available_indices=sorted(set(available_indices or [1]))
    slot="1630" if period=="evening" else "0700"
    prefix=city.get("media_state_prefix",f"latest/{city['id']}").strip("/")
    url=f"https://raw.githubusercontent.com/audreywang9898-sudo/meowcast-media/main/{prefix}/weather-rotation-{slot}.json"
    try:
        with urllib.request.urlopen(url,timeout=8) as r:
            state=json.load(r)
        prev_idx=int(state.get(theme,0))
        if prev_idx in available_indices:
            pos=available_indices.index(prev_idx)
            return available_indices[(pos+1)%len(available_indices)]
        for idx in available_indices:
            if idx>prev_idx:
                return idx
        return available_indices[0]
    except Exception as e:
        print(f"Weather rotation state unavailable; starting at {available_indices[0]}:",e)
        return available_indices[0]

def asset_for(theme,event=None,period="morning",date_str=None,city=None):
    city=city or load_city_config()
    asset_prefix=city.get("asset_prefix","asset").rstrip("/")
    # A secondary same-day calendar event may explicitly supply evening artwork.
    # Other evening editions continue rotating weather artwork as before.
    if event and (period != "evening" or event.get("_use_evening_artwork")):
        configured=event.get("asset")
        key=event.get("key")
        special=[]
        if configured: special.append(f"{asset_prefix}/{configured}")
        if key: special.extend([f"{asset_prefix}/{key}.png", f"{asset_prefix}/{key}.jpg"])
        for p in special:
            if _valid_artwork_file(p): return p, None

    suffix="_evening" if period=="evening" else ""
    available=_available_artwork_indices(asset_prefix,theme,suffix)
    if available:
        idx=_rotation_state(
            theme,date_str,period,city=city,available_indices=available
        ) if date_str else available[0]
        print(f"Available artwork indices: theme={theme}{suffix} indices={available}")
        for ext in ("png","jpg"):
            p=f"{asset_prefix}/{theme}{suffix}-{idx}.{ext}"
            if _valid_artwork_file(p):
                print(f"Weather artwork rotation: theme={theme} index={idx} asset={p}")
                return p, idx

        # Extremely defensive: if the selected file disappears between scan
        # and open, stay inside the same theme and period.
        for fallback_idx in available:
            for ext in ("png","jpg"):
                p=f"{asset_prefix}/{theme}{suffix}-{fallback_idx}.{ext}"
                if _valid_artwork_file(p):
                    print(f"Selected artwork vanished; SAME-THEME FALLBACK={p}")
                    return p, fallback_idx
    else:
        idx=1
        print(f"No valid artwork found for theme={theme}{suffix}")

    # Global fail-safe prefers sunny artwork from the same period.
    sunny_available=_available_artwork_indices(asset_prefix,"sunny",suffix)
    for fallback_idx in sunny_available:
        for ext in ("png","jpg"):
            p=f"{asset_prefix}/sunny{suffix}-{fallback_idx}.{ext}"
            if _valid_artwork_file(p):
                print(f"Requested artwork {theme}{suffix}-{idx} unavailable; GLOBAL FALLBACK={p}")
                return p, fallback_idx

    # Last-resort compatibility: if an evening set is entirely absent, allow a
    # valid daytime sunny asset rather than failing the production render.
    if suffix:
        for fallback_idx in _available_artwork_indices(asset_prefix,"sunny",""):
            for ext in ("png","jpg"):
                p=f"{asset_prefix}/sunny-{fallback_idx}.{ext}"
                if _valid_artwork_file(p):
                    print(f"Evening artwork unavailable; DAYTIME SUNNY FALLBACK={p}")
                    return p, fallback_idx

    # Temporary compatibility until sunny-1 itself has been added.
    legacy=[f"{asset_prefix}/sunny.png",f"{asset_prefix}/sunny.jpg"]
    for p in legacy:
        if _valid_artwork_file(p):
            print(f"WARNING: sunny-1 missing; temporary legacy fallback={p}")
            return p, 1
    return None, 1

def add_weather_overlay(im,w,theme,event=None,city=None):
    """Draw a compact, high-legibility weather card entirely in code."""
    city=city or load_city_config()
    english_only=city.get("language")=="english"
    d=ImageDraw.Draw(im,"RGBA")
    condition={"sunny":"Sunny","rainy":"Rainy","cloudy":"Cloudy"}[theme]
    temp_label=temperature_label(w)
    # Avoid emoji glyphs in the rendered card: the CI font stack can render them as tofu/boxes.
    condition_zh={"Sunny":"晴朗","Rainy":"雨天","Cloudy":"陰天"}[condition]
    temp_zh={"Hot":"炎熱","Cold":"寒冷"}.get(temp_label, "")
    temp_badge={"Hot":"Hot","Cold":"Cold"}.get(temp_label, "")
    condition_text=condition if english_only else f"{condition} {condition_zh}"
    if temp_badge:
        condition_text += f" · {temp_badge}" if english_only else f" · {temp_badge} {temp_zh}"

    # Fixed compact card below the branding area.
    x0,y0,x1,y1=145,685,935,1065
    d.rounded_rectangle((x0,y0,x1,y1),radius=54,
                        fill=(238,242,246,160),
                        outline=(255,255,255,190),width=3)

    ink=(24,30,39,255)
    muted=(83,94,108,255)
    line=(135,145,156,145)
    accent={"sunny":(226,169,47,255),"rainy":(92,145,185,255),
            "cloudy":(145,154,164,255)}[theme]

    def put(x,y,s,size,fill=ink,anchor="mm"):
        d.text((x,y),s,font=font(size),anchor=anchor,fill=fill)

    # Date: larger and visually connected to the weather block.
    date_label=datetime.strptime(w["date"],"%Y-%m-%d").strftime("%Y / %m / %d (%a)").upper()
    put(540,735,date_label,40)
    d.line((200,775,880,775),fill=line,width=2)

    # Compact main weather row: icon + high temperature + low temperature.
    cx,cy=255,850
    r=30
    if theme=="sunny":
        d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=accent)
        for dx,dy in [(0,-64),(0,64),(-64,0),(64,0),(-45,-45),(45,-45),(-45,45),(45,45)]:
            d.line((cx+dx*.68,cy+dy*.68,cx+dx,cy+dy),fill=accent,width=5)
    elif theme in ("rainy","cloudy"):
        d.ellipse((cx-52,cy-2,cx+4,cy+42),fill=accent)
        d.ellipse((cx-30,cy-34,cx+34,cy+42),fill=accent)
        d.ellipse((cx+5,cy-15,cx+58,cy+42),fill=accent)
        d.rounded_rectangle((cx-52,cy+8,cx+58,cy+43),radius=17,fill=accent)
        if theme=="rainy":
            for off in (-25,10,42):
                d.line((cx+off,cy+58,cx+off-8,cy+80),fill=accent,width=5)
    else:
        d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=accent)

    main_temp=w.get("temperature",w["high"])
    # Bilingual high/low labels above each temperature.
    put(485,795,"HIGH" if english_only else "最高溫  HIGH",25,muted)
    put(485,855,f"{main_temp}°C",82)
    d.line((645,805,645,890),fill=line,width=2)
    if english_only:
        low_label="TONIGHT LOW" if w.get("period")=="evening" else "LOW"
    else:
        low_label="今晚最低溫  TONIGHT LOW" if w.get("period")=="evening" else "最低溫  LOW"
    put(760,805,low_label,22 if w.get("period")=="evening" else 25,muted)
    put(760,860,f"{w['low']}°C",45)

    # Condition is prominent but visually tied to the temperature row.
    d.rounded_rectangle((310,915,770,975),radius=30,fill=(255,255,255,210))
    # English is primary; Chinese translations are intentionally smaller.
    parts=[(condition,42)] if english_only else [(condition_zh,28),(condition,42)]
    if temp_badge:
        parts += [(" · "+temp_badge,42)] if english_only else [(" · "+temp_zh,28),(temp_badge,42)]
    fonts=[font(sz) for _,sz in parts]
    widths=[d.textlength(txt,font=ft) for (txt,_),ft in zip(parts,fonts)]
    total=sum(widths)+14*(len(parts)-1)
    x=540-total/2
    for (txt,_),ft,wid in zip(parts,fonts,widths):
        d.text((x,945),txt,font=ft,anchor="lm",fill=ink)
        x += wid+14

    # Evening card must explicitly read as a tonight forecast.
    rain_en="Tonight rain chance" if w.get("period")=="evening" else "Rain chance"
    rain_zh="今晚降雨機率" if w.get("period")=="evening" else "降雨機率"
    zh_ft=font(23)
    pct_ft=font(34)
    en_ft=font(30 if w.get("period")=="evening" else 32)
    zh_w=0 if english_only else d.textlength(rain_zh,font=zh_ft)
    pct_text=f"{w['rain']}%"
    pct_w=d.textlength(pct_text,font=pct_ft)
    en_w=d.textlength(rain_en,font=en_ft)
    gap=16
    drop_w=28
    total=(drop_w+gap+pct_w+gap+en_w
           if english_only
           else drop_w+gap+zh_w+gap+pct_w+gap+en_w)
    x=540-total/2
    # Draw a real blue raindrop so CI does not depend on emoji glyph support.
    drop_cx=x+drop_w/2
    drop_cy=1025
    blue=(30,144,255,255)
    d.polygon([(drop_cx,drop_cy-22),(drop_cx-15,drop_cy+5),(drop_cx+15,drop_cy+5)],fill=blue)
    d.ellipse((drop_cx-15,drop_cy-7,drop_cx+15,drop_cy+20),fill=blue)
    x += drop_w+gap
    if not english_only:
        d.text((x,1025),rain_zh,font=zh_ft,anchor="lm",fill=(58,67,80,255))
        x += zh_w+gap
    d.text((x,1025),pct_text,font=pct_ft,anchor="lm",fill=(58,67,80,255))
    x += pct_w+gap
    d.text((x,1025),rain_en,font=en_ft,anchor="lm",fill=(58,67,80,255))


def main(period=None):
    city=load_city_config()
    print(f"City config: {city['id']} timezone={city['timezone']} language={city['language']}")
    period=(period or os.environ.get("MEOWCAST_PERIOD","morning")).lower()
    if period not in ("morning","evening"):
        raise ValueError(f"Unsupported MEOWCAST_PERIOD: {period}")
    w=get_evening_weather(city) if period=="evening" else get_weather(city)
    print("Weather input:", w)
    event=event_for_date(w["date"]) if city.get("holiday_mode",False) else None
    if period=="evening":
        # Where two independently illustrated observances share one date,
        # publish the primary artwork in the morning and secondary in the evening.
        # This preserves the existing two daily publication slots.
        secondary=next((item for item in (event or {}).get("also", [])
                        if isinstance(item,dict) and item.get("asset")
                        and _valid_artwork_file(f"{city.get('asset_prefix', 'asset').rstrip('/')}/{item['asset']}")),None)
        event={**secondary,"_use_evening_artwork":True} if secondary else None
    t,cap=make_caption(w,event=event,city=city)
    src,rotation_index=asset_for(t,event,period=period,date_str=w["date"],city=city)
    if src:
        im=Image.open(src).convert("RGB"); scale=max(W/im.width,H/im.height); im=im.resize((int(im.width*scale),int(im.height*scale)))
        x=(im.width-W)//2; y=(im.height-H)//2; im=im.crop((x,y,x+W,y+H))
    else:
        im=fallback(t)
    add_weather_overlay(im,w,t,event,city=city)
    os.makedirs("output",exist_ok=True); im.save("output/card.jpg",quality=94)
    # Candidate state is committed by the workflow only after Instagram publish succeeds.
    with open("output/weather-state.json","w",encoding="utf-8") as sf:
        json.dump({"date":w["date"],"city":city["id"],"theme":t,"index":rotation_index or 1,"period":period},sf,ensure_ascii=False)
    # Evening uses the normal/default BGM; no holiday-specific music.
    bgm=music_for_event(None if period=="evening" else event)
    subprocess.run(["ffmpeg","-y","-loop","1","-i","output/card.jpg","-i",bgm,"-vf","scale=1200:2134,zoompan=z='min(zoom+0.0005,1.08)':d=200:s=1080x1920:fps=25","-t","8","-c:v","libx264","-c:a","aac","-b:a","128k","-shortest","-pix_fmt","yuv420p","-movflags","+faststart","output/meowcast.mp4"],check=True)
    open("output/caption.txt","w",encoding="utf-8").write(cap)

if __name__=="__main__": main()
