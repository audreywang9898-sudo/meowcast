# Taipei Meowcast Auto-Reel

Free-first automated Taipei weather Reel generator.

## v1
Every day at 07:30 Asia/Taipei, GitHub Actions fetches Taipei weather from Open-Meteo, selects a weather theme, renders a 1080x1920 card and creates an 8-second MP4 with FFmpeg.

## Assets
Add these portrait images under assets/: sunny.jpg, rainy.jpg, cloudy.jpg, hot.jpg, cold.jpg. Until then add any image as assets/placeholder.jpg for testing.

## Current status
Generation is automated. Instagram publishing is the next stage and requires Meta/Instagram publishing credentials plus a publicly reachable video URL.

You can also run the workflow manually from GitHub Actions using **Run workflow**.
