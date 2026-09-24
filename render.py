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
    """Draw the complete weather UI in code. Background artwork stays independent."""
    d=ImageDraw.Draw(im,"RGBA")
    condition={"sunny":"Sunny","rainy":"Rainy","cloudy":"Cloudy","hot":"Hot","cold":"Cold"}[theme]

    # One fixed panel for every background. No weather_UI image asset is used.
    x0,y0,x1,y1=155,500,925,960
    radius=52
    d.rounded_rectangle((x0,y0,x1,y1),radius=radius,
                        fill=(238,242,246,224),
                        outline=(255,255,255,205),width=3)

    ink=(25,31,40,255)
    muted=(91,102,116,255)
    line=(135,145,156,150)
    accent={"sunny":(226,169,47,255),"rainy":(92,145,185,255),
            "cloudy":(145,154,164,255),"hot":(218,126,62,255),
            "cold":(105,151,187,255)}[theme]

    def put(x,y,s,size,fill=ink,anchor="mm"):
        d.text((x,y),s,font=font(size),anchor=anchor,fill=fill)

    date_label=datetime.strptime(w["date"],"%Y-%m-%d").strftime("%Y / %m / %d (%a)").upper()
    put(540,565,date_label,34)
    d.line((205,615,875,615),fill=line,width=2)

    # Weather icon
    cx,cy=270,720
    r=28
    if theme in ("sunny","hot"):
        d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=accent)
        for dx,dy in [(0,-60),(0,60),(-60,0),(60,0),(-43,-43),(43,-43),(-43,43),(43,43)]:
            d.line((cx+dx*.68,cy+dy*.68,cx+dx,cy+dy),fill=accent,width=5)
    elif theme in ("rainy","cloudy"):
        d.ellipse((cx-48,cy-12,cx+8,cy+38),fill=accent)
        d.ellipse((cx-12,cy-38,cx+50,cy+38),fill=accent)
        d.rectangle((cx-48,cy,cx+50,cy+38),fill=accent)
        if theme=="rainy":
            for off in (-25,10,42):
                d.line((cx+off,cy+55,cx+off-8,cy+75),fill=accent,width=5)
    else:
        d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=accent)

    put(485,705,f"{w['high']}°C",76)
    d.line((630,660,630,755),fill=line,width=2)
    put(705,680,"LOW",21,muted)
    put(705,725,f"{w['low']}°C",34)

    # Condition pill
    d.rounded_rectangle((285,785,795,855),radius=35,fill=(255,255,255,205))
    put(540,820,condition,36)

    d.line((205,885,875,885),fill=line,width=2)
    put(430,925,"Rain chance",25,muted)
    put(700,925,f"{w['rain']}%",38)


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
