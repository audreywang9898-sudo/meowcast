#!/bin/bash
cd "$(dirname "$0")/.."
export CITY=taipei MEOWCAST_PERIOD=evening
command -v python3 >/dev/null || { echo "Install Python 3 first"; read -r; exit 1; }
command -v ffmpeg >/dev/null || { echo "Install ffmpeg first: brew install ffmpeg"; read -r; exit 1; }
python3 -c 'import PIL, requests, lunar_python' 2>/dev/null || python3 -m pip install -r requirements.txt
python3 render.py || { echo "Generation failed"; read -r; exit 1; }
open output
echo "READY: output/meowcast.mp4 and output/caption.txt"
read -r -p "Press Enter to close"
