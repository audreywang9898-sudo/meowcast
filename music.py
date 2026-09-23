import math, os, wave, struct
from datetime import datetime
from zoneinfo import ZoneInfo
from calendar_events import event_for_date

SR=22050
DUR=8

# Music dates/events come ONLY from calendar.json.
# This file contains sound recipes, never holiday/date rules.
TRACKS=[
    (104,[60,64,67,72,67,64,62,67],"Fresh Start"),
    (112,[64,67,69,71,69,67,64,62],"Sunny Steps"),
    (92,[57,60,64,67,64,60,59,64],"Cozy City"),
    (108,[62,66,69,74,69,66,64,69],"Little Adventure"),
    (118,[60,64,67,69,72,69,67,64],"Happy Paws"),
    (84,[55,59,62,67,62,59,57,62],"Slow Morning"),
    (78,[60,64,67,71,67,64,62,60],"Soft Sunshine"),
]

MUSIC_RECIPES={
    "new_year":(118,[60,64,67,72,76,72,69,67],"New Year Cat"),
    "valentine":(72,[60,64,67,71,69,67,64,60],"Love Cat"),
    "peaceful":(68,[60,64,67,69,67,64,62,60],"Peaceful Paws"),
    "lunar_new_year":(104,[60,64,67,72,76,72,69,67],"Lunar New Year Cat"),
    "lantern_festival":(96,[64,67,72,76,72,69,67,64],"Lantern Festival Cat"),
    "gentle":(82,[60,64,67,71,69,67,64,62],"Gentle Paws"),
    "playful":(112,[60,64,67,72,74,69,67,64],"Playful Paws"),
    "childrens_day":(116,[60,64,67,72,74,72,69,67],"Children's Day Cat"),
    "nature":(84,[57,60,64,67,64,60,59,64],"Nature Paws"),
    "may_day":(104,[60,64,67,69,72,69,67,64],"May Day Cat"),
    "warm_family":(82,[60,64,67,71,69,67,64,60],"Warm Family Cat"),
    "dragon_boat":(112,[62,67,69,74,71,69,67,62],"Dragon Boat Cat"),
    "calm_night":(72,[57,60,64,67,64,62,60,57],"Calm Night Cat"),
    "mid_autumn":(82,[57,60,64,69,67,64,60,57],"Mid-Autumn Moon Cat"),
    "teacher_appreciation":(88,[60,64,67,71,69,67,64,62],"Teacher Appreciation Cat"),
    "celebration":(112,[60,67,72,76,72,69,67,64],"Celebration Cat"),
    "commemoration":(90,[57,60,64,67,69,67,64,60],"Commemoration Cat"),
    "halloween":(96,[57,60,63,66,63,60,58,57],"Halloween Cat"),
    "christmas":(94,[67,71,74,79,74,71,69,67],"Christmas Cat"),
    "lichun":(92,[60,64,67,72,69,67,64,67],"Beginning of Spring"),
    "yushui":(82,[62,65,69,67,65,62,60,65],"Rain Water"),
    "jingzhe":(108,[60,67,69,72,67,74,72,69],"Awakening of Insects"),
    "chunfen":(98,[64,67,71,72,71,67,64,69],"Spring Equinox"),
    "qingming":(76,[57,60,64,62,60,57,55,60],"Pure Brightness"),
    "guyu":(86,[60,62,65,69,67,65,62,60],"Grain Rain"),
    "lixia":(112,[64,69,71,76,71,69,67,71],"Beginning of Summer"),
    "xiaoman":(106,[62,66,69,74,71,69,66,64],"Grain Buds"),
    "mangzhong":(116,[60,64,69,72,76,72,69,67],"Grain in Ear"),
    "xiazhi":(120,[67,71,74,79,76,74,71,72],"Summer Solstice"),
    "xiaoshu":(110,[64,67,72,76,74,72,69,67],"Minor Heat"),
    "dashu":(118,[62,69,74,78,74,71,69,66],"Major Heat"),
    "liqiu":(94,[60,64,67,71,69,67,64,62],"Beginning of Autumn"),
    "chushu":(88,[62,65,69,72,69,67,65,60],"End of Heat"),
    "bailu":(80,[67,71,74,71,69,67,64,62],"White Dew"),
    "qiufen":(84,[60,64,67,71,67,64,62,60],"Autumn Equinox"),
    "hanlu":(74,[57,60,64,67,64,62,60,55],"Cold Dew"),
    "shuangjiang":(70,[55,59,62,67,64,62,59,57],"Frost's Descent"),
    "lidong":(76,[60,63,67,70,67,63,58,60],"Beginning of Winter"),
    "xiaoxue":(72,[64,67,71,76,71,69,67,64],"Minor Snow"),
    "daxue":(68,[57,60,64,69,64,62,60,57],"Major Snow"),
    "dongzhi":(66,[60,64,67,72,67,64,59,60],"Winter Solstice"),
    "xiaohan":(70,[62,65,69,65,62,60,57,60],"Minor Cold"),
    "dahan":(64,[55,60,63,67,63,60,58,55],"Major Cold"),
}

def hz(n):
    return 440*2**((n-69)/12)

def _render(path,bpm,notes,title,duration=DUR):
    os.makedirs(os.path.dirname(path) or ".",exist_ok=True)
    n=int(SR*duration)
    audio=[0.0]*n
    beat=60/bpm
    for k in range(int(duration/beat)+1):
        st=k*beat
        f=hz(notes[k%len(notes)])
        for i in range(int(st*SR),min(n,int((st+.5)*SR))):
            t=i/SR-st
            env=(1-math.exp(-12*t))*math.exp(-4.2*t)
            audio[i]+=.13*env*(math.sin(2*math.pi*f*t)+.10*math.sin(4*math.pi*f*t))
    root=hz(notes[0]-12)
    for i in range(n):
        t=i/SR
        audio[i]+=.018*math.sin(2*math.pi*root*t)
    peak=max(map(abs,audio)) or 1
    with wave.open(path,"w") as w:
        w.setparams((1,2,SR,n,"NONE","not compressed"))
        w.writeframes(b"".join(
            struct.pack("<h",int(max(-1,min(1,x/peak*.62))*32767)) for x in audio
        ))
    print("BGM:",title)
    return path

def make_music(path="output/bgm.wav", event=None, date_text=None, dt=None):
    # Calendar is the only source that decides whether today is special.
    if event is None:
        if date_text is None:
            now=dt or datetime.now(ZoneInfo("Asia/Taipei"))
            date_text=now.strftime("%Y-%m-%d")
        event=event_for_date(date_text)

    if event:
        music_key=event.get("music")
        if music_key:
            recipe=MUSIC_RECIPES.get(music_key)
            if recipe:
                bpm,notes,title=recipe
                return _render(path,bpm,notes,title)
            print(f"Calendar music recipe missing: {music_key}; using everyday track.")

    now=dt
    if now is None:
        if date_text:
            now=datetime.strptime(date_text,"%Y-%m-%d").replace(tzinfo=ZoneInfo("Asia/Taipei"))
        else:
            now=datetime.now(ZoneInfo("Asia/Taipei"))
    bpm,notes,title=TRACKS[now.weekday()]
    return _render(path,bpm,notes,title)

if __name__=="__main__":
    make_music()
