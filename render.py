import os, subprocess
from PIL import Image,ImageDraw,ImageFont
from weather import get_weather
from caption import make_caption, LINES

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

def main():
    w=get_weather(); t,cap=make_caption(w); src = "assetssunny.png" if t == "sunny" and os.path.exists("assetssunny.png") else f"assets/{t}.jpg"
    if os.path.exists(src):
        im=Image.open(src).convert("RGB"); scale=max(W/im.width,H/im.height); im=im.resize((int(im.width*scale),int(im.height*scale)))
        x=(im.width-W)//2; y=(im.height-H)//2; im=im.crop((x,y,x+W,y+H))
    else: im=fallback(t)
    # Designed theme artwork already contains the Meowcast branding.
    # Keep overlays minimal so the cat artwork remains the hero.
    d=ImageDraw.Draw(im)
    if not os.path.exists(src):
        overlay=Image.new("RGBA",(W,520),(0,0,0,125)); im.paste(overlay,(0,0),overlay)
        d.text((70,70),"TAIPEI MEOWCAST",font=font(66),fill="white"); d.text((70,165),f"{w['date']}   {w['low']}–{w['high']}°C",font=font(48),fill="white"); d.text((70,240),f"Rain {w['rain']}%",font=font(42),fill="white")
        en,zh=LINES[t]; d.text((70,330),en,font=font(40),fill="white"); d.text((70,395),zh,font=font(38),fill="white")
    os.makedirs("output",exist_ok=True); im.save("output/card.jpg",quality=94)
    subprocess.run(["ffmpeg","-y","-loop","1","-i","output/card.jpg","-vf","scale=1200:2134,zoompan=z='min(zoom+0.0005,1.08)':d=200:s=1080x1920:fps=25","-t","8","-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart","output/meowcast.mp4"],check=True)
    open("output/caption.txt","w",encoding="utf-8").write(cap)

if __name__=="__main__": main()
