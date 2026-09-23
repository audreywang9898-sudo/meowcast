import math, os, wave, struct
from datetime import datetime
from zoneinfo import ZoneInfo
from calendar_events import event_for_date

SR=44100
DUR=8

# Taipei Cat sound identity:
# gentle chamber-light-music feel, slow tempo, bowed-string-like pads,
# soft pizzicato accents, no harsh electronic lead tones.
DAILY=[
    (72,[60,64,67,71],"Morning Strings"),
    (76,[62,65,69,72],"Little Taipei Walk"),
    (70,[57,60,64,67],"Soft City Light"),
    (74,[60,65,69,72],"Gentle Paws"),
    (78,[60,64,67,72],"Friday Breeze"),
    (68,[55,59,62,67],"Slow Weekend"),
    (66,[60,64,67,71],"Sunday Window"),
]

MOODS={
    "new_year":"bright","new_years_eve":"bright","celebration":"bright",
    "lunar_new_year":"warm","lantern_festival":"warm","childrens_day":"bright",
    "playful":"bright","may_day":"gentle","nature":"gentle",
    "valentine":"romantic","white_day":"romantic","qixi":"romantic",
    "warm_family":"warm","fathers_day":"warm","thanksgiving":"warm",
    "peaceful":"calm","commemoration":"calm","calm_night":"night",
    "ghost_festival":"night","halloween":"night",
    "mid_autumn":"moon","teacher_appreciation":"gentle",
    "christmas":"winter","christmas_eve":"winter",
    "lichun":"spring","yushui":"spring","jingzhe":"spring","chunfen":"spring",
    "qingming":"calm","guyu":"spring",
    "lixia":"summer","xiaoman":"summer","mangzhong":"summer",
    "xiazhi":"summer","xiaoshu":"summer","dashu":"summer",
    "liqiu":"autumn","chushu":"autumn","bailu":"autumn","qiufen":"autumn",
    "hanlu":"autumn","shuangjiang":"autumn",
    "lidong":"winter","xiaoxue":"winter","daxue":"winter",
    "dongzhi":"winter","xiaohan":"winter","dahan":"winter",
}

MOOD_MUSIC={
    "gentle":(72,[60,64,67,71]),
    "bright":(82,[60,64,67,72]),
    "warm":(70,[57,60,64,67]),
    "romantic":(66,[60,64,69,71]),
    "calm":(64,[57,60,64,67]),
    "night":(62,[57,60,63,67]),
    "moon":(64,[57,62,64,69]),
    "spring":(72,[60,64,67,72]),
    "summer":(76,[62,66,69,74]),
    "autumn":(66,[57,60,64,69]),
    "winter":(62,[55,60,63,67]),
}

def hz(n):
    return 440*2**((n-69)/12)

def _bowed(freq,t):
    # Additive spectrum + slow vibrato approximates a soft string ensemble
    # without the buzzy sine-lead character of the old generator.
    vib=1+.0022*math.sin(2*math.pi*5.0*t)
    f=freq*vib
    return (
        .72*math.sin(2*math.pi*f*t)
        +.20*math.sin(2*math.pi*2*f*t)
        +.07*math.sin(2*math.pi*3*f*t)
        +.025*math.sin(2*math.pi*4*f*t)
    )

def _fade(t,start,end,attack=.65,release=.9):
    a=min(1,max(0,(t-start)/attack))
    r=min(1,max(0,(end-t)/release))
    return a*r

def _render(path,bpm,chord,title,duration=DUR):
    os.makedirs(os.path.dirname(path) or ".",exist_ok=True)
    n=int(SR*duration)
    audio=[0.0]*n
    beat=60/bpm

    # Warm cello + viola/violin pad. Chords change slowly, like light background music.
    progression=[
        chord,
        [chord[1],chord[2],chord[3],chord[0]+12],
        [chord[2],chord[0]+12,chord[1]+12,chord[3]+12],
        chord,
    ]
    section=duration/len(progression)
    for sec,notes in enumerate(progression):
        start=sec*section
        end=min(duration,start+section+.35)
        for midi in notes:
            f=hz(midi)
            for i in range(int(start*SR),min(n,int(end*SR))):
                t=i/SR
                local=t-start
                audio[i]+=.032*_fade(t,start,end)*_bowed(f,local)

        # Quiet cello root one octave below.
        f=hz(notes[0]-12)
        for i in range(int(start*SR),min(n,int(end*SR))):
            t=i/SR
            audio[i]+=.025*_fade(t,start,end,.8,1.0)*_bowed(f,t-start)

    # Sparse pizzicato: soft accents, not a lead melody.
    pizz=[chord[0]+12,chord[2]+12,chord[1]+12,chord[3]+12]
    for k in range(int(duration/(beat*2))+1):
        start=k*beat*2
        f=hz(pizz[k%len(pizz)])
        stop=min(duration,start+.7)
        for i in range(int(start*SR),min(n,int(stop*SR))):
            t=i/SR-start
            env=(1-math.exp(-18*t))*math.exp(-5.5*t)
            tone=.65*math.sin(2*math.pi*f*t)+.20*math.sin(4*math.pi*f*t)
            audio[i]+=.022*env*tone

    # Gentle room-like echo for a less synthetic, more spacious result.
    delay=int(.18*SR)
    wet=audio[:]
    for i in range(delay,n):
        wet[i]+=.13*audio[i-delay]
    delay2=int(.31*SR)
    for i in range(delay2,n):
        wet[i]+=.07*audio[i-delay2]

    # Fade entire clip in/out.
    for i in range(n):
        t=i/SR
        master=min(1,t/.45,(duration-t)/.65)
        wet[i]*=max(0,master)

    peak=max(map(abs,wet)) or 1
    with wave.open(path,"w") as w:
        w.setparams((1,2,SR,n,"NONE","not compressed"))
        w.writeframes(b"".join(
            struct.pack("<h",int(max(-1,min(1,x/peak*.55))*32767)) for x in wet
        ))
    print("BGM:",title)
    return path

def make_music(path="output/bgm.wav",event=None,date_text=None,dt=None):
    if event is None:
        if date_text is None:
            now=dt or datetime.now(ZoneInfo("Asia/Taipei"))
            date_text=now.strftime("%Y-%m-%d")
        event=event_for_date(date_text)

    if event and event.get("music"):
        key=event["music"]
        mood=MOODS.get(key,"gentle")
        bpm,chord=MOOD_MUSIC[mood]
        title=f"Taipei Cat Strings · {event.get('name_en',key)}"
        return _render(path,bpm,chord,title)

    now=dt
    if now is None:
        if date_text:
            now=datetime.strptime(date_text,"%Y-%m-%d").replace(tzinfo=ZoneInfo("Asia/Taipei"))
        else:
            now=datetime.now(ZoneInfo("Asia/Taipei"))
    bpm,chord,title=DAILY[now.weekday()]
    return _render(path,bpm,chord,f"Taipei Cat Strings · {title}")

if __name__=="__main__":
    make_music()
