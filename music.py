import os
import shutil

DEFAULT_TRACK = "music/the_window_seat_reel.mp3"


def make_music(path="output/bgm.mp3", event=None, date_text=None, dt=None):
    """Use the approved Taipei Meowcast background track.

    Calendar/event arguments are kept for API compatibility so different
    approved tracks can be mapped later without changing render.py.
    """
    if not os.path.exists(DEFAULT_TRACK):
        raise FileNotFoundError(f"Approved BGM not found: {DEFAULT_TRACK}")

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    shutil.copyfile(DEFAULT_TRACK, path)
    print("BGM: The Window Seat (approved Reel edit)")
    return path


if __name__ == "__main__":
    make_music()
