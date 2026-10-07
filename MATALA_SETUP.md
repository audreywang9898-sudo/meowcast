# Matala Meowcast setup

Matala is a third, independent English-language weather cat. It uses Europe/Athens for forecast dates, weekdays and schedules, with daylight-saving transitions handled by the timezone. Its state lives under latest/matala; its videos under matala/reels.

## Current status

City config, 14 weekday captions, Instagram workflow and an opt-in external watchdog are prepared. Production remains disabled. The 42 images have been generated; import the bundle below. Dedicated credentials and live publication checks are still required. Facebook is not connected: the existing Facebook publisher is Taipei-specific and must not be pointed at Matala.

## Artwork

Import all seven sets (42 images) with:

```bash
python matala.py --import-assets /path/to/Matala-Meowcast-42-images.zip
python matala.py --check-assets
CITY=matala python matala.py --period morning
CITY=matala python matala.py --period evening
```

This produces previews only. Commit `asset/matala/*.png` to this branch before using GitHub previews. Required naming:
- sunny-1.png, cloudy-1.png, rainy-1.png
- sunny_evening-1.png, cloudy_evening-1.png, rainy_evening-1.png

Further numbered sets use the same rotation engine. Use Matala Meowcast branding, a realistic orange cat below the weather card, and Matala's beach and cliff caves. The Matala weather card occupies x=145–935, y=465–845 in a 1080×1920 image; keep the cat below y=845. Do not bake weather numbers or dates into the artwork. The workflow validates all 42 images before rendering. Matala uses deterministic English captions (no AI call) and the existing approved daily music.

## Dedicated Instagram account

Use the Matala professional Instagram account and authorize it through Instagram Login for the existing `graph.instagram.com` publisher. A Facebook Page is not required for this route. Do not supply Facebook Login tokens to this publisher. Put the following secrets in this repository:
- MATALA_IG_USER_ID
- MATALA_IG_ACCESS_TOKEN

Reuse MEDIA_REPO_TOKEN only for the existing media repository. Never paste tokens in chat or source files.

## Preview and launch

1. Merge this preparation only after code review.
2. Import and commit all 42 images and run Matala Meowcast manually with publish=false, once for morning and once for evening.
3. Inspect both preview artifacts, local dates, weather, captions and cat placement.
4. Add the dedicated credentials and set repository variable MATALA_PRODUCTION_ENABLED=true.
5. Run a single controlled publish=true test. Verify the Reel on the correct account and its latest/matala receipt.
6. Repeat the same slot with republish=false and verify it is skipped.
7. Set MATALA_PRODUCTION_ENABLED=true on the Render watchdog environment only after GitHub production is ready.

The first scheduled morning trigger is 07:07 local time, matching the existing Melbourne recovery pattern; evening starts at 16:30. Extra cron triggers recover the same slot. GitHub scheduling and processing can delay actual publication. Slot 0700 is the internal morning identifier, not an exact publish-time promise. If the schedule is disabled, manual previews remain available but publication is blocked.

The Matala workflow has a separate publisher concurrency group. Keep republish=false for routine recovery. Do not enable native IG-to-FB sharing and API Facebook publication simultaneously without choosing one route.

