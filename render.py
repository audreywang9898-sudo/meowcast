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
    accent={"sunny":(255,210,105,245),"rainy":(145,205,255,245),"cloudy":(205,215,225,245),"hot":(255,175,95,245),"cold":(180,220,255,245)}[theme]
    tips={
        "sunny":"Sunshine is on duty. Enjoy the view!",
        "rainy":"Rain or shine, tomorrow is a brighter day!",
        "cloudy":"Soft skies can still hold a very good day.",
        "hot":"Stay cool, drink water, and find a little shade.",
        "cold":"Warm layers, warm drinks, warm thoughts.",
    }

    # Strong localized contrast instead of washing out the whole photo.
    top=Image.new("RGBA",(W,900),(0,0,0,0))
    td=ImageDraw.Draw(top,"RGBA")
    for y in range(900):
        alpha=int(150*(1-y/900))
        td.rectangle((0,y,W,y+1),fill=(7,18,28,max(0,alpha)))
    im.paste(top,(0,0),top)
    d=ImageDraw.Draw(im,"RGBA")

    # Branded headline: large, centered, balanced like the approved poster.
    d.text((W//2,72),"🐾",font=font(48),anchor="ma",fill="white")
    d.text((W//2,132),"TAIPEI",font=font(82),anchor="ma",fill="white")
    d.text((W//2,222),"MEOWCAST",font=font(86),anchor="ma",fill=accent)
    d.line((300,318,780,318),fill=accent,width=5)
    d.text((W//2,338),"Exploring Taipei with you,",font=font(30),anchor="ma",fill="white")
    d.text((W//2,380),"one little adventure at a time. ♡",font=font(30),anchor="ma",fill="white")

    date_label=datetime.strptime(w["date"],"%Y-%m-%d").strftime("%Y / %m / %d (%a)").upper()
    d.text((W//2,458),date_label,font=font(43),anchor="ma",fill="white")

    # Main weather information.
    icon={"sunny":"☀","rainy":"☂","cloudy":"☁","hot":"☀","cold":"❄"}[theme]
    d.text((205,585),icon,font=font(100),anchor="mm",fill=accent)
    d.text((500,580),f"{w['high']}°C",font=font(128),anchor="mm",fill="white")
    d.line((690,515,690,645),fill=(255,255,255,220),width=3)
    d.text((730,530),"LOW",font=font(35),fill=(245,248,252,255))
    d.text((730,575),f"{w['low']}°C",font=font(55),fill="white")

    # Accent label ensures Sunny/Rainy remains readable on every photograph.
    label_box=(315,690,765,785)
    d.rounded_rectangle(label_box,radius=45,fill=accent)
    text_fill=(30,30,35,255) if theme in ("sunny","hot","cloudy") else (255,255,255,255)
    d.text((W//2,716),condition,font=font(58),anchor="ma",fill=text_fill)
    d.text((W//2,812),f"Rain chance {w['rain']}%",font=font(35),anchor="ma",fill="white")
    d.line((410,862,670,862),fill=accent,width=5)

    # Daily line gets its own dark translucent card: no low-contrast white-on-sky.
    d.rounded_rectangle((105,900,975,1025),radius=30,fill=(8,16,24,145))
    d.text((W//2,928),tips[theme],font=font(31),anchor="ma",fill="white")

    # Footer uses a strong dark band so labels remain readable over any base image.
    footer_y=1645
    d.rounded_rectangle((35,footer_y,1045,1880),radius=34,fill=(7,13,18,175))
    items=[("☕","Warm drink"),("⌂","A cozy day"),("♪","Good mood"),("♥","You got this")]
    xs=[155,410,670,925]
    for x,(ico,label) in zip(xs,items):
        d.text((x,1700),ico,font=font(48),anchor="mm",fill="white")
        d.text((x,1760),label,font=font(26),anchor="mm",fill="white")
    d.line((90,1810,990,1810),fill=(255,255,255,190),width=2)
    d.text((W//2,1842),"GOOD WEATHER  ·  GOOD DAYS  ·  A HAPPIER YOU",font=font(23),anchor="mm",fill="white")

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
