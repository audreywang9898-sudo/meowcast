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
    """Draw a compact, high-legibility weather card entirely in code."""
    d=ImageDraw.Draw(im,"RGBA")
    condition={"sunny":"Sunny","rainy":"Rainy","cloudy":"Cloudy","hot":"Hot","cold":"Cold"}[theme]

    # Fixed compact card below the branding area.
    x0,y0,x1,y1=145,685,935,1065
    d.rounded_rectangle((x0,y0,x1,y1),radius=54,
                        fill=(238,242,246,228),
                        outline=(255,255,255,220),width=3)

    ink=(24,30,39,255)
    muted=(83,94,108,255)
    line=(135,145,156,145)
    accent={"sunny":(226,169,47,255),"rainy":(92,145,185,255),
            "cloudy":(145,154,164,255),"hot":(218,126,62,255),
            "cold":(105,151,187,255)}[theme]

    def put(x,y,s,size,fill=ink,anchor="mm"):
        d.text((x,y),s,font=font(size),anchor=anchor,fill=fill)

    # Date: larger and visually connected to the weather block.
    date_label=datetime.strptime(w["date"],"%Y-%m-%d").strftime("%Y / %m / %d (%a)").upper()
    put(540,735,date_label,40)
    d.line((200,775,880,775),fill=line,width=2)

    # Compact main weather row: icon + high temperature + low temperature.
    cx,cy=255,850
    r=30
    if theme in ("sunny","hot"):
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

    put(485,845,f"{w['high']}°C",92)
    d.line((645,805,645,890),fill=line,width=2)
    put(735,812,"LOW",27,muted)
    put(735,865,f"{w['low']}°C",47)

    # Condition is prominent but visually tied to the temperature row.
    d.rounded_rectangle((310,915,770,975),radius=30,fill=(255,255,255,210))
    put(540,945,condition,42)

    # Rain probability as one compact sentence, not two scattered fields.
    put(540,1025,f"Rain chance  {w['rain']}%",36,(58,67,80,255))


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
