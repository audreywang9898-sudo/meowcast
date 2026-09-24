import os, subprocess
from datetime import datetime
from PIL import Image,ImageDraw,ImageFont
from weather import get_weather
from caption import make_caption
from music import music_for_event
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
    """Composite the fixed weather UI layer, then draw live data inside its panel."""
    ui_path="asset/weather_UI.png"
    if not os.path.exists(ui_path):
        raise FileNotFoundError(f"Missing fixed weather UI: {ui_path}")

    ui=Image.open(ui_path).convert("RGBA").resize((W,H),Image.Resampling.LANCZOS)
    # weather_UI is a full-canvas transparent PNG. Its non-transparent bbox defines
    # the panel, so text placement follows the UI itself instead of any background.
    alpha=ui.getchannel("A")
    bbox=alpha.getbbox()
    if not bbox:
        raise ValueError("weather_UI.png has no visible pixels")
    im_rgba=im.convert("RGBA")
    im_rgba.alpha_composite(ui)
    im.paste(im_rgba.convert("RGB"))

    d=ImageDraw.Draw(im,"RGBA")
    x0,y0,x1,y1=bbox
    pw,ph=x1-x0,y1-y0
    condition={"sunny":"Sunny","rainy":"Rainy","cloudy":"Cloudy","hot":"Hot","cold":"Cold"}[theme]
    ink=(28,30,34,255)
    muted=(95,105,118,255)
    accent={"sunny":(226,169,47,255),"rainy":(92,145,185,255),"cloudy":(145,154,164,255),"hot":(218,126,62,255),"cold":(105,151,187,255)}[theme]

    def put(rx,ry,s,size,fill=ink,anchor="mm"):
        d.text((x0+pw*rx,y0+ph*ry),s,font=font(size),anchor=anchor,fill=fill)

    date_label=datetime.strptime(w["date"],"%Y-%m-%d").strftime("%Y / %m / %d (%a)").upper()
    put(.50,.13,date_label,40)

    # Weather icon at left of the temperature row.
    cx=x0+pw*.20; cy=y0+ph*.43
    r=max(18,int(min(pw,ph)*.045))
    if theme in ("sunny","hot"):
        d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=accent)
        for dx,dy in [(0,-2*r),(0,2*r),(-2*r,0),(2*r,0)]:
            d.line((cx+dx*.65,cy+dy*.65,cx+dx,cy+dy),fill=accent,width=max(3,r//5))
    elif theme in ("rainy","cloudy"):
        d.ellipse((cx-r*1.2,cy-r*.25,cx+r*.15,cy+r*.85),fill=accent)
        d.ellipse((cx-r*.35,cy-r*.8,cx+r*1.15,cy+r*.85),fill=accent)
        d.rectangle((cx-r*1.2,cy,cx+r*1.15,cy+r*.85),fill=accent)
        if theme=="rainy":
            for off in (-r*.7,0,r*.7):
                d.line((cx+off,cy+r*1.2,cx+off-r*.2,cy+r*1.65),fill=accent,width=max(3,r//6))
    else:
        for dx,dy in [(0,-2*r),(0,2*r),(-2*r,0),(2*r,0),(-1.4*r,-1.4*r),(1.4*r,-1.4*r)]:
            d.line((cx+dx*.65,cy+dy*.65,cx+dx,cy+dy),fill=accent,width=max(3,r//5))
        d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=accent)

    put(.46,.43,f"{w['high']}°C",82)
    put(.70,.36,"LOW",25,muted)
    put(.70,.46,f"{w['low']}°C",39)
    put(.50,.64,condition,43)
    put(.39,.86,"Rain chance",28,muted)
    put(.72,.86,f"{w['rain']}%",42)


def main():
    w=get_weather(); event=event_for_date(w["date"]); t,cap=make_caption(w,event=event); src=asset_for(t,event)
    if src:
        im=Image.open(src).convert("RGB"); scale=max(W/im.width,H/im.height); im=im.resize((int(im.width*scale),int(im.height*scale)))
        x=(im.width-W)//2; y=(im.height-H)//2; im=im.crop((x,y,x+W,y+H))
    else:
        im=fallback(t)
    add_weather_overlay(im,w,t,event)
    os.makedirs("output",exist_ok=True); im.save("output/card.jpg",quality=94)
    bgm=music_for_event(event)
    subprocess.run(["ffmpeg","-y","-loop","1","-i","output/card.jpg","-i",bgm,"-vf","scale=1200:2134,zoompan=z='min(zoom+0.0005,1.08)':d=200:s=1080x1920:fps=25","-t","8","-c:v","libx264","-c:a","aac","-b:a","128k","-shortest","-pix_fmt","yuv420p","-movflags","+faststart","output/meowcast.mp4"],check=True)
    open("output/caption.txt","w",encoding="utf-8").write(cap)

if __name__=="__main__": main()
