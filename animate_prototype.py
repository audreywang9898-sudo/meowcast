import math, os, subprocess
from PIL import Image, ImageEnhance, ImageDraw, ImageFilter

W,H=1080,1920
FPS=25
SECONDS=8
N=FPS*SECONDS
SRC="asset/sunny.png"
TMP="output/prototype_frames"
OUT="output/sunny-animation-prototype.mp4"
os.makedirs(TMP,exist_ok=True)

src=Image.open(SRC).convert("RGB")
scale=max((W+90)/src.width,(H+160)/src.height)
src=src.resize((round(src.width*scale),round(src.height*scale)),Image.Resampling.LANCZOS)

for i in range(N):
    t=i/(N-1)
    loop=math.sin(2*math.pi*t)
    # Slow cinematic drift, intentionally gentler than production zoompan.
    zoom=1.015 + 0.012*(0.5-0.5*math.cos(2*math.pi*t))
    fw,fh=round(src.width*zoom),round(src.height*zoom)
    frame=src.resize((fw,fh),Image.Resampling.LANCZOS)
    cx=(fw-W)//2 + round(10*loop)
    cy=(fh-H)//2 + round(5*math.sin(2*math.pi*t+0.8))
    frame=frame.crop((cx,cy,cx+W,cy+H)).convert("RGBA")

    # Soft breathing sunlight: a blurred warm glow pulses in the upper sky.
    glow=Image.new("RGBA",(W,H),(0,0,0,0))
    gd=ImageDraw.Draw(glow)
    pulse=0.5+0.5*math.sin(2*math.pi*t-math.pi/2)
    alpha=18+round(24*pulse)
    gx=230+round(30*math.sin(2*math.pi*t))
    gy=310+round(12*math.cos(2*math.pi*t))
    gd.ellipse((gx-230,gy-230,gx+230,gy+230),fill=(255,226,150,alpha))
    glow=glow.filter(ImageFilter.GaussianBlur(80))
    frame=Image.alpha_composite(frame,glow)

    # Very subtle brightness pulse gives the scene a living/breathing feel.
    frame=ImageEnhance.Brightness(frame.convert("RGB")).enhance(1.0+0.012*math.sin(2*math.pi*t))
    frame.save(f"{TMP}/frame_{i:04d}.jpg",quality=90)

subprocess.run([
    "ffmpeg","-y","-framerate",str(FPS),"-i",f"{TMP}/frame_%04d.jpg",
    "-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p",
    "-movflags","+faststart","-t",str(SECONDS),OUT
],check=True)
print(OUT)
