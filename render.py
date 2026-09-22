import os, subprocess
from datetime import datetime
from PIL import Image,ImageDraw,ImageFont
from weather import get_weather
from caption import make_caption
from music import make_music

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

def asset_for(theme):
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

def add_weather_overlay(im,w,theme):
    d=ImageDraw.Draw(im,"RGBA")
    condition={"sunny":"Sunny","rainy":"Rainy","cloudy":"Cloudy","hot":"Hot","cold":"Cold"}[theme]
    accent={"sunny":(255,205,88,255),"rainy":(125,195,245,255),"cloudy":(205,215,225,255),"hot":(255,160,78,255),"cold":(170,215,250,255)}[theme]
    dark=(30,30,35,255)
    tips={
        "sunny":"Sunshine is on duty. Enjoy the view!",
        "rainy":"Rain or shine, tomorrow is a brighter day!",
        "cloudy":"Soft skies can still hold a very good day.",
        "hot":"Stay cool, drink water, and find a little shade.",
        "cold":"Warm layers, warm drinks, warm thoughts.",
    }

    # Subtle shadow helper: poster-like lettering without UI boxes.
    def txt(pos,text,fnt,fill="white",anchor="ma",shadow=True):
        x,y=pos
        if shadow:
            d.text((x+3,y+4),text,font=fnt,anchor=anchor,fill=(0,0,0,105))
        d.text((x,y),text,font=fnt,anchor=anchor,fill=fill)

    # Local top vignette only; preserve the bright photograph and the cat.
    grad=Image.new("RGBA",(W,930),(0,0,0,0)); gd=ImageDraw.Draw(grad,"RGBA")
    for y in range(930):
        alpha=int(90*max(0,1-y/930))
        gd.rectangle((0,y,W,y+1),fill=(5,15,25,alpha))
    im.paste(grad,(0,0),grad); d=ImageDraw.Draw(im,"RGBA")

    # Match the approved poster hierarchy.
    txt((W//2,76),"TAIPEI",font(78),"white")
    txt((W//2,162),"MEOWCAST",font(88),accent)
    d.line((305,263,775,263),fill=accent,width=6)
    txt((W//2,288),"Exploring Taipei with you,",font(29),"white")
    txt((W//2,328),"one little adventure at a time.",font(29),"white")

    date_label=datetime.strptime(w["date"],"%Y-%m-%d").strftime("%Y / %m / %d (%a)").upper()
    txt((W//2,405),date_label,font(42),"white")

    # Main temperature block.
    if theme in ("sunny","hot"):
        d.ellipse((150,505,220,575),fill=accent)
        for dx,dy in [(0,-55),(0,55),(-55,0),(55,0),(-40,-40),(40,-40),(-40,40),(40,40)]:
            d.line((185+dx*.65,540+dy*.65,185+dx,540+dy),fill=accent,width=6)
    elif theme in ("rainy","cloudy"):
        d.ellipse((135,520,195,570),fill=accent); d.ellipse((170,500,235,570),fill=accent); d.rectangle((135,540,235,570),fill=accent)
        if theme=="rainy":
            for x in (150,185,220): d.line((x,585,x-10,610),fill=accent,width=5)
    else:
        d.line((145,540,225,540),fill=accent,width=7); d.line((185,500,185,580),fill=accent,width=7)
        d.line((155,510,215,570),fill=accent,width=7); d.line((215,510,155,570),fill=accent,width=7)

    txt((505,535),f"{w['high']}°C",font(126),"white",anchor="mm")
    d.line((700,480,700,600),fill=(255,255,255,220),width=3)
    txt((740,495),"LOW",font(34),(245,248,252,255),anchor="la")
    txt((740,540),f"{w['low']}°C",font(54),"white",anchor="la")

    # Painted weather label like the design reference, not a UI button.
    d.rounded_rectangle((335,650,745,738),radius=40,fill=accent)
    label_fill=dark if theme in ("sunny","hot","cloudy") else (255,255,255,255)
    txt((W//2,671),condition,font(54),label_fill,shadow=False)
    txt((W//2,765),f"Rain chance {w['rain']}%",font(34),"white")
    d.line((430,817,650,817),fill=accent,width=5)

    # Handwritten-note feel: no black rectangle.
    txt((125,855),tips[theme],font(29),"white",anchor="la")

    # Minimal footer inspired by the poster; placed above Reel UI safe area.
    footer_y=1660
    d.line((90,footer_y,990,footer_y),fill=(255,255,255,190),width=2)
    labels=["Warm drink","A cozy day","Good mood","You got this"]
    xs=[155,410,670,925]
    for x,label in zip(xs,labels):
        d.ellipse((x-7,footer_y+45,x+7,footer_y+59),fill=accent)
        txt((x,footer_y+78),label,font(24),"white",anchor="ma")
    d.line((90,footer_y+125,990,footer_y+125),fill=(255,255,255,150),width=2)
    txt((W//2,footer_y+148),"GOOD WEATHER  ·  GOOD DAYS  ·  A HAPPIER YOU",font(22),"white")

def main():
    w=get_weather(); t,cap=make_caption(w); src=asset_for(t)
    if src:
        im=Image.open(src).convert("RGB"); scale=max(W/im.width,H/im.height); im=im.resize((int(im.width*scale),int(im.height*scale)))
        x=(im.width-W)//2; y=(im.height-H)//2; im=im.crop((x,y,x+W,y+H))
    else:
        im=fallback(t)
    add_weather_overlay(im,w,t)
    os.makedirs("output",exist_ok=True); im.save("output/card.jpg",quality=94)
    make_music("output/bgm.wav")
    subprocess.run(["ffmpeg","-y","-loop","1","-i","output/card.jpg","-i","output/bgm.wav","-vf","scale=1200:2134,zoompan=z='min(zoom+0.0005,1.08)':d=200:s=1080x1920:fps=25","-t","8","-c:v","libx264","-c:a","aac","-b:a","128k","-shortest","-pix_fmt","yuv420p","-movflags","+faststart","output/meowcast.mp4"],check=True)
    open("output/caption.txt","w",encoding="utf-8").write(cap)

if __name__=="__main__": main()
