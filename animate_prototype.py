import math, os, subprocess, random
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
scale=max((W+180)/src.width,(H+260)/src.height)
src=src.resize((round(src.width*scale),round(src.height*scale)),Image.Resampling.LANCZOS)

# Fixed dreamy light particles: deterministic positions, animated opacity/drift.
random.seed(42)
particles=[(random.randint(60,W-60),random.randint(120,1450),random.randint(3,8),random.random()*2*math.pi) for _ in range(28)]

for i in range(N):
    t=i/N
    phase=2*math.pi*t
    # Clearly visible but calm Ken-Burns movement; returns smoothly to start.
    zoom=1.025 + 0.045*(0.5-0.5*math.cos(phase))
    fw,fh=round(src.width*zoom),round(src.height*zoom)
    frame=src.resize((fw,fh),Image.Resampling.LANCZOS)
    cx=(fw-W)//2 + round(28*math.sin(phase))
    cy=(fh-H)//2 + round(16*math.sin(phase+0.7))
    frame=frame.crop((cx,cy,cx+W,cy+H)).convert("RGBA")

    # Large warm sun glow that visibly breathes and glides across the sky.
    glow=Image.new("RGBA",(W,H),(0,0,0,0))
    gd=ImageDraw.Draw(glow)
    pulse=0.5+0.5*math.sin(phase-math.pi/2)
    gx=180+round(100*(0.5+0.5*math.sin(phase)))
    gy=300+round(35*math.cos(phase))
    radius=300+round(45*pulse)
    gd.ellipse((gx-radius,gy-radius,gx+radius,gy+radius),fill=(255,218,120,55+round(55*pulse)))
    glow=glow.filter(ImageFilter.GaussianBlur(95))
    frame=Image.alpha_composite(frame,glow)

    # Diagonal soft sunbeams: intentionally visible, still low-contrast.
    beams=Image.new("RGBA",(W,H),(0,0,0,0))
    bd=ImageDraw.Draw(beams)
    beam_alpha=20+round(24*pulse)
    drift=round(45*math.sin(phase))
    bd.polygon([(0+drift,100),(150+drift,70),(760+drift,1250),(570+drift,1320)],fill=(255,244,200,beam_alpha))
    bd.polygon([(220+drift,0),(310+drift,0),(900+drift,1000),(760+drift,1080)],fill=(255,247,218,max(10,beam_alpha-7)))
    beams=beams.filter(ImageFilter.GaussianBlur(35))
    frame=Image.alpha_composite(frame,beams)

    # Floating golden bokeh/dust adds an obvious but soothing living layer.
    dust=Image.new("RGBA",(W,H),(0,0,0,0))
    dd=ImageDraw.Draw(dust)
    for x,y,r,p in particles:
        yy=(y + 34*math.sin(phase+p)) % 1500
        xx=x + 18*math.sin(phase*0.7+p)
        a=int(18+42*(0.5+0.5*math.sin(phase+p)))
        dd.ellipse((xx-r,yy-r,xx+r,yy+r),fill=(255,232,164,a))
    dust=dust.filter(ImageFilter.GaussianBlur(2.5))
    frame=Image.alpha_composite(frame,dust)

    # Warm cinematic breathing: more noticeable than v1 without flashing.
    rgb=frame.convert("RGB")
    rgb=ImageEnhance.Brightness(rgb).enhance(1.015+0.035*math.sin(phase))
    rgb=ImageEnhance.Color(rgb).enhance(1.04+0.025*math.sin(phase-0.4))
    rgb.save(f"{TMP}/frame_{i:04d}.jpg",quality=91)

subprocess.run([
    "ffmpeg","-y","-framerate",str(FPS),"-i",f"{TMP}/frame_%04d.jpg",
    "-c:v","libx264","-preset","medium","-crf","19","-pix_fmt","yuv420p",
    "-movflags","+faststart","-t",str(SECONDS),OUT
],check=True)
print(OUT)
