import os

DEFAULT_TRACK = "music/daily_gentle.mp3"

def music_for_event(event=None):
    """Choose an approved real audio file from music/. Never synthesize BGM."""
    candidates = []
    if event:
        key = event.get("music")
        if key:
            candidates.extend([
                f"music/{key}.mp3",
                f"music/{key}.wav",
                f"music/{key}.m4a",
            ])
    candidates.append(DEFAULT_TRACK)

    for path in candidates:
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            print("BGM:", path)
            return path

    raise FileNotFoundError(
        f"No approved real BGM found. Expected {DEFAULT_TRACK} or an event-specific file in music/."
    )

if __name__ == "__main__":
    print(music_for_event())
