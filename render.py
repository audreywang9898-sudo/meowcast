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
    # Dynamic data panel: all values come from today's weather API response.
    panel=(54,54,1026,500)
    d.rounded_rectangle(panel,radius=42,fill=(10,18,28,150),outline=(255,255,255,80),width=2)

    date_label=datetime.strptime(w["date"],"%Y-%m-%d").strftime("%Y/%m/%d (%a)").upper()
    condition={"sunny":"SUNNY","rainy":"RAINY","cloudy":"CLOUDY","hot":"HOT","cold":"COLD"}[theme]

    d.text((92,82),"TAIPEI MEOWCAST",font=font(58),fill=(255,255,255,255))
    d.text((92,160),date_label,font=font(48),fill=(255,255,255,245))
    d.text((92,245),f"{w['high']}°C",font=font(112),fill=(255,255,255,255))
    d.text((430,274),f"LOW  {w['low']}°C",font=font(45),fill=(255,255,255,245))
    d.text((92,382),condition,font=font(52),fill=(255,255,255,255))
    rain_text=f"RAIN  {w['rain']}%"
    rb=d.textbbox((0,0),rain_text,font=font(46))
    d.text((986-(rb[2]-rb[0]),388),rain_text,font=font(46),fill=(255,255,255,245))

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
