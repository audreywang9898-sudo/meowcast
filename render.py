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
    icons={"sunny":"☀","rainy":"☂","cloudy":"☁","hot":"☀","cold":"❄"}
    tips={
        "sunny":"Sunshine is on duty. Enjoy the view!",
        "rainy":"Rain or shine, tomorrow is a brighter day!",
        "cloudy":"Soft skies can still hold a very good day.",
        "hot":"Stay cool, drink water, and find a little shade.",
        "cold":"Warm layers, warm drinks, warm thoughts.",
    }

    # Soft top gradient preserves the artwork while making the editorial text readable.
    shade=Image.new("RGBA",(W,820),(0,0,0,0))
    sd=ImageDraw.Draw(shade,"RGBA")
    for y in range(820):
        alpha=max(0,int(145*(1-y/820)))
        sd.rectangle((0,y,W,y+1),fill=(8,18,28,alpha))
    im.paste(shade,(0,0),shade)
    d=ImageDraw.Draw(im,"RGBA")

    # Brand / editorial header.
    title="TAIPEI\nMEOWCAST"
    d.multiline_text((W//2,70),title,font=font(72),anchor="ma",align="center",spacing=-8,fill="white")
    d.text((W//2,238),"Exploring Taipei with you, one little adventure at a time.",font=font(27),anchor="ma",fill=(255,255,255,235))

    # Dynamic date.
    date_label=datetime.strptime(w["date"],"%Y-%m-%d").strftime("%Y / %m / %d (%a)").upper()
    d.text((W//2,315),date_label,font=font(42),anchor="ma",fill="white")

    # Dynamic weather block, visually matching the designed poster.
    d.text((220,405),icons[theme],font=font(92),anchor="mm",fill=(220,235,255,255))
    d.text((525,410),f"{w['high']}°C",font=font(118),anchor="mm",fill="white")
    d.line((700,355,700,465),fill=(255,255,255,190),width=3)
    d.text((735,372),"LOW",font=font(35),fill=(235,240,248,245))
    d.text((735,415),f"{w['low']}°C",font=font(52),fill="white")
    d.text((W//2,515),condition,font=font(66),anchor="ma",fill="white")
    d.line((400,590,680,590),fill=(180,220,255,230),width=6)
    d.text((W//2,625),f"Rain chance {w['rain']}%  •  {tips[theme]}",font=font(29),anchor="ma",fill=(255,255,255,240))

    # Bottom editorial footer, kept dynamic-data-free so it never conflicts with weather facts.
    footer=Image.new("RGBA",(W,220),(8,15,22,115))
    im.paste(footer,(0,H-220),footer)
    d=ImageDraw.Draw(im,"RGBA")
    items=[("☕","Warm drink"),("⌂","A cozy day"),("♪","Good mood"),("♥","You got this")]
    xs=[150,410,675,930]
    for x,(ico,label) in zip(xs,items):
        d.text((x,H-165),ico,font=font(45),anchor="mm",fill="white")
        d.text((x,H-105),label,font=font(25),anchor="mm",fill="white")
    d.line((60,H-58,W-60,H-58),fill=(255,255,255,180),width=2)
    d.text((W//2,H-32),"GOOD WEATHER  ·  GOOD DAYS  ·  A HAPPIER YOU",font=font(23),anchor="mm",fill=(255,255,255,240))

def main():
    w=get_weather(); t,cap=make_caption(w); src=asset_for(t)
    if src:
        im=Image.open(src).convert("RGB"); scale=max(W/im.width,H/im.height); im=im.resize((int(im.width*scale),int(im.height*scale)))
        x=(im.width-W)//2; y=(im.height-H)//2; im=im.crop((x,y,x+W,y+H))
    else:
        im=fallback(t)
        d=ImageDraw.Draw(im)
        overlay=Image.new("RGBA",(W,430),(0,0,0,125)); im.paste(overlay,(0,0),overlay)
        d.text((70,125),"TAIPEI MEOWCAST",font=font(66),fill="white")
        d.text((70,220),f"{w['low']}–{w['high']}°C",font=font(48),fill="white")
        d.text((70,295),f"Rain {w['rain']}%",font=font(42),fill="white")
    add_weather_overlay(im,w,t)
    os.makedirs("output",exist_ok=True); im.save("output/card.jpg",quality=94)
    make_music("output/bgm.wav")
    subprocess.run(["ffmpeg","-y","-loop","1","-i","output/card.jpg","-i","output/bgm.wav","-vf","scale=1200:2134,zoompan=z='min(zoom+0.0005,1.08)':d=200:s=1080x1920:fps=25","-t","8","-c:v","libx264","-c:a","aac","-b:a","128k","-shortest","-pix_fmt","yuv420p","-movflags","+faststart","output/meowcast.mp4"],check=True)
    open("output/caption.txt","w",encoding="utf-8").write(cap)

if __name__=="__main__": main()
