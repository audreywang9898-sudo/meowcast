import io
import json
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from matala_caption import make_caption
from city_config import load_city_config
from matala_render import _rotation_state
from weather import get_evening_weather, get_weather


class MatalaTests(unittest.TestCase):
    def setUp(self):
        self.city = load_city_config("matala")
        self.hourly = {
            "time": [f"2026-10-07T{h:02}:00" for h in range(24)],
            "temperature_2m": [20 + h / 10 for h in range(24)],
            "precipitation_probability": [90 if h == 15 else 10 for h in range(24)],
            "weather_code": [61 if h == 15 else 2 for h in range(24)],
        }

    def test_daytime_rain_probability_does_not_change_cloudy_artwork(self):
        with patch("weather._open_meteo_hourly", return_value=self.hourly), patch("weather.datetime") as clock:
            clock.fromisoformat.side_effect = datetime.fromisoformat
            clock.now.return_value = datetime(2026, 10, 7, 7, 7, tzinfo=ZoneInfo("Europe/Athens"))
            forecast = get_weather(self.city)
        theme, caption = make_caption(forecast, city=self.city)
        self.assertEqual(theme, "cloudy")
        self.assertEqual(forecast["rain"], 90)
        self.assertIn("Matala", caption)
        self.assertNotIn("Melbourne", caption)
        self.assertEqual(forecast["date"], "2026-10-07")

    def test_evening_window(self):
        with patch("weather._open_meteo_hourly", return_value=self.hourly):
            forecast = get_evening_weather(self.city)
        self.assertEqual(forecast["period"], "evening")
        self.assertEqual(forecast["window"], "17:00-23:00")
        self.assertEqual(forecast["rain"], 10)

    def test_rotation_wrap_and_matala_state_isolation(self):
        with patch("matala_render.urllib.request.urlopen", return_value=io.BytesIO(json.dumps({"sunny": 7}).encode())) as fetch:
            index = _rotation_state("sunny", "2026-10-07", "evening", self.city, range(1, 8))
        self.assertEqual(index, 1)
        self.assertIn("latest/matala/weather-rotation-1630.json", fetch.call_args.args[0])

    def test_all_fourteen_captions_use_english_without_ai_calls(self):
        with patch("matala_caption.make_ai_caption") as ai:
            for day in range(5, 12):
                for period in ("morning", "evening"):
                    _, caption = make_caption({"date": f"2026-10-{day:02}", "code": 0, "high": 24, "low": 19, "temperature": 22, "rain": 10, "period": period, "window": "17:00-23:00" if period == "evening" else "07:00-17:00"}, city=self.city)
                    self.assertIn("Matala", caption)
                    self.assertFalse(any("\u4e00" <= c <= "\u9fff" for c in caption))
            ai.assert_not_called()

    def test_greek_summer_winter_offsets(self):
        tz = ZoneInfo(self.city["timezone"])
        self.assertEqual(datetime(2026, 7, 1, tzinfo=tz).utcoffset().total_seconds(), 10800)
        self.assertEqual(datetime(2026, 12, 1, tzinfo=tz).utcoffset().total_seconds(), 7200)


if __name__ == "__main__":
    unittest.main()
