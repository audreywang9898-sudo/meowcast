import math, wave, struct
from datetime import datetime
from zoneinfo import ZoneInfo
SR=22050; DUR=8
TRACKS=[(104,[60,64,67,72,67,64,62,67],"Fresh Start"),(112,[64,67,69,71,69,67,64,62],"Sunny Steps"),(92,[57,60,64,67,64,60,59,64],"Cozy City"),(108,[62,66,69,74,69,66,64,69],"Little Adventure"),(118,[60,64,67,69,72,69,67,64],"Happy Paws"),(84,[55,59,62,67,62,59,57,62],"Slow Morning"),(78,[60,64,67,71,67,64,62,60],"Soft Sunshine")]
def hz(n): return 440*2**((n-69)/12)
def make_music(path="output/bgm.wav"):
    bpm,notes,title=TRACKS[datetime.now(ZoneInfo("Asia/Taipei")).weekday()]
    n=int(SR*DUR); audio=[0.0]*n; beat=60/bpm
    for k in range(int(DUR/beat)+1):
        st=k*beat; f=hz(notes[k%len(notes)])
        for i in range(int(st*SR),min(n,int((st+.5)*SR))):
            t=i/SR-st; env=(1-math.exp(-30*t))*math.exp(-5*t)
            audio[i]+=.18*env*(math.sin(2*math.pi*f*t)+.25*math.sin(4*math.pi*f*t))
    for i in range(n): audio[i]+=.035*math.sin(2*math.pi*hz(notes[0]-12)*(i/SR))
    peak=max(map(abs,audio)) or 1
    with wave.open(path,"w") as w:
        w.setparams((1,2,SR,n,"NONE","not compressed"))
        w.writeframes(b"".join(struct.pack("<h",int(max(-1,min(1,x/peak*.8))*32767)) for x in audio))
    print("BGM:",title)
