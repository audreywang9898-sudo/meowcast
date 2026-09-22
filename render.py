import os, subprocess
from PIL import Image,ImageDraw,ImageFont
from weather import get_weather
from caption import theme,make_caption

W,H=1080,1920

def font(size):
    for p in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if os.path.exists(p): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def main():
    w=get_weather(); t,cap=make_caption(w); src=f"assets/{t}.jpg"
    if not os.path.exists(src): src="assets/placeholder.jpg"
    im=Image.open(src).convert("RGB"); scale=max(W/im.width,H/im.height); im=im.resize((int(im.width*scale),int(im.height*scale)))
    x=(im.width-W)//2; y=(im.height-H)//2; im=im.crop((x,y,x+W,y+H))
    d=ImageDraw.Draw(im); overlay=Image.new("RGBA",(W,520),(0,0,0,125)); im.paste(overlay,(0,0),overlay); d=ImageDraw.Draw(im)
    d.text((70,70),"TAIPEI MEOWCAST",font=font(66),fill="white"); d.text((70,165),f"{w['date']}   {w['low']}–{w['high']}°C",font=font(48),fill="white"); d.text((70,240),f"Rain {w['rain']}%",font=font(42),fill="white")
    en,zh={k:v for k,v in __import__("caption").LINES.items()}[t]; d.text((70,330),en,font=font(40),fill="white"); d.text((70,395),zh,font=font(38),fill="white")
    os.makedirs("output",exist_ok=True); im.save("output/card.jpg",quality=94)
    subprocess.run(["ffmpeg","-y","-loop","1","-i","output/card.jpg","-vf","scale=1200:2134,zoompan=z='min(zoom+0.0005,1.08)':d=200:s=1080x1920:fps=25","-t","8","-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart","output/meowcast.mp4"],check=True)
    open("output/caption.txt","w").write(cap)

if __name__=="__main__": main()
