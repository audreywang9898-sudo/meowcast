import os, subprocess
from datetime import datetime
from PIL import Image,ImageDraw,ImageFont
from weather import get_weather
from caption import make_caption
from music import make_music
from calendar_events import event_for_date

W,H=1080,1920

def font(size):
    for p in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if os.path.exists(p): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def fallback(theme):
    tones={"sunny":(235,196,104),"rainy":(91,119,145),"cloudy":(164,174,181),"hot":(221,145,98),"cold":(136,163,186)}
    im=Image.new("RGB",(W,H),tones[theme]); d=ImageDraw.Draw(im)
    d.ellipse((290,570,790,1070),fill=(238,238,232)); d.ellipse((335,480,500,680),fill=(238,238,232)); d.ellipse((580,480,745,680),fill=(238,238,232))
    d.ellipse((390,690,455,755),fill=(35,35,35)); d.ellipse((625,690,690,755),fill=(35,35,35)); d.polygon([(520,790),(560,790),(540,825)],fill=(215,130,140))
    d.text((330,1120),"MEOW",font=font(100),fill="white")
    return im

def asset_for(theme,event=None):
    # Calendar artwork wins over normal weather artwork when provided.
    if event:
        configured=event.get("asset")
        key=event.get("key")
        special=[]
        if configured: special.append(f"asset/{configured}")
        if key: special.extend([f"asset/{key}.png", f"asset/{key}.jpg"])
        for p in special:
            if os.path.exists(p): return p
    candidates={
        "sunny":["asset/sunny.png","asset/sunny.jpg"],
        "rainy":["asset/rainy.png","asset/rainy.jpg"],
        "cloudy":["asset/cloudy.png","asset/cloudy.jpg"],
        "hot":["asset/hot.png","asset/hot.jpg"],
        "cold":["asset/cold.png","asset/cold.jpg"],
    }
    for p in candidates[theme]:
        if os.path.exists(p): return p
    return None

def add_weather_overlay(im,w,theme,event=None):
    d=ImageDraw.Draw(im,"RGBA")
    condition={"sunny":"Sunny","rainy":"Rainy","cloudy":"Cloudy","hot":"Hot","cold":"Cold"}[theme]
    event_key=event.get("key") if event else None
    is_equinox=(event_key=="autumn_equinox")
    accent={"sunny":(255,205,88,255),"rainy":(155,205,245,255),"cloudy":(215,220,225,255),"hot":(255,165,80,255),"cold":(185,220,250,255)}[theme]
    ink=(28,30,34,255)
    tips={"sunny":"Sunshine is on duty.\nEnjoy the view!",
          "rainy":"Rain or shine,\ntomorrow is a brighter day!",
          "cloudy":"Soft skies can still hold\na very good day.",
          "hot":"Stay cool, drink water,\nand find a little shade.",
          "cold":"Warm layers, warm drinks,\nwarm thoughts."}

    def text(x,y,s,size,fill=(255,255,255,255),anchor="ma",stroke=0):
        d.text((x,y),s,font=font(size),anchor=anchor,fill=fill,
               stroke_width=stroke,stroke_fill=(0,0,0,95))

    # Original-poster composition: large airy header, centered weather, cat area left untouched.
    # Only a very light top vignette for legibility.
    vignette=Image.new("RGBA",(W,1050),(0,0,0,0)); vd=ImageDraw.Draw(vignette,"RGBA")
    for yy in range(1050):
        alpha=int(68*(1-yy/1050))
        vd.rectangle((0,yy,W,yy+1),fill=(5,18,30,max(alpha,0)))
    im.paste(vignette,(0,0),vignette); d=ImageDraw.Draw(im,"RGBA")

    # Branding/title/subtitle are part of the base artwork.
    # Do not draw TAIPEI / MEOWCAST / tagline dynamically.

    date_label=datetime.strptime(w["date"],"%Y-%m-%d").strftime("%Y / %m / %d (%a)").upper()
    text(W//2,452,date_label,43)
    if is_equinox:
        # Seasonal badge: weather remains live; only the art direction/message changes.
        d.rounded_rectangle((92,705,300,785),radius=34,fill=(245,181,74,235))
        text(196,722,"AUTUMNAL",25,ink,stroke=0)
        text(196,752,"EQUINOX",25,ink,stroke=0)

    # Weather icon + temperature + low, same proportions as the approved reference.
    cx,cy=210,590
    if theme in ("sunny","hot"):
        d.ellipse((cx-38,cy-38,cx+38,cy+38),fill=accent)
        for dx,dy in [(0,-68),(0,68),(-68,0),(68,0),(-48,-48),(48,-48),(-48,48),(48,48)]:
            d.line((cx+int(dx*.68),cy+int(dy*.68),cx+dx,cy+dy),fill=accent,width=7)
    elif theme in ("rainy","cloudy"):
        d.ellipse((150,565,215,620),fill=accent); d.ellipse((190,545,260,620),fill=accent)
        d.rectangle((150,590,260,620),fill=accent)
        if theme=="rainy":
            for xx in (165,205,245): d.line((xx,640,xx-12,670),fill=accent,width=6)
    else:
        for ang in [(210,530,210,650),(150,590,270,590),(168,548,252,632),(252,548,168,632)]:
            d.line(ang,fill=accent,width=7)

    text(510,575,f"{w['high']}°C",132,anchor="mm")
    d.line((710,515,710,650),fill=(255,255,255,225),width=3)
    text(750,530,"LOW",35,anchor="la")
    text(750,577,f"{w['low']}°C",56,anchor="la")

    # Hand-painted condition swash.
    d.rounded_rectangle((335,700,745,795),radius=46,fill=accent)
    # Center the weather condition both horizontally and vertically in the pill.
    # Slightly larger type improves Reel readability.
    text(W//2,748,condition,68,ink if theme in ("sunny","hot","cloudy") else (255,255,255,255),anchor="mm",stroke=0)
    text(W//2,825,f"Rain chance {w['rain']}%",35)
    d.line((430,880,650,880),fill=accent,width=5)

    # Small handwritten-style note at left, no dark UI card.
    note = "Day and night in balance.\nA gentler season begins." if is_equinox else tips[theme]
    d.multiline_text((125,920),note,font=font(31),fill=(255,255,255,255),
                     spacing=7,stroke_width=2,stroke_fill=(0,0,0,95))

    # No bottom toolbar: preserve the cat and scenery. One subtle brand line only.
    text(W//2,1815,"GOOD WEATHER  ·  GOOD DAYS  ·  A HAPPIER YOU",23,stroke=2)

def main():
    w=get_weather(); event=event_for_date(w["date"]); t,cap=make_caption(w,event=event); src=asset_for(t,event)
    if src:
        im=Image.open(src).convert("RGB"); scale=max(W/im.width,H/im.height); im=im.resize((int(im.width*scale),int(im.height*scale)))
        x=(im.width-W)//2; y=(im.height-H)//2; im=im.crop((x,y,x+W,y+H))
    else:
        im=fallback(t)
    add_weather_overlay(im,w,t,event)
    os.makedirs("output",exist_ok=True); im.save("output/card.jpg",quality=94)
    make_music("output/bgm.wav")
    subprocess.run(["ffmpeg","-y","-loop","1","-i","output/card.jpg","-i","output/bgm.wav","-vf","scale=1200:2134,zoompan=z='min(zoom+0.0005,1.08)':d=200:s=1080x1920:fps=25","-t","8","-c:v","libx264","-c:a","aac","-b:a","128k","-shortest","-pix_fmt","yuv420p","-movflags","+faststart","output/meowcast.mp4"],check=True)
    open("output/caption.txt","w",encoding="utf-8").write(cap)

if __name__=="__main__": main()
