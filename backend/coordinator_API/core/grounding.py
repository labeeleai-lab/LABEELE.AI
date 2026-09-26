"""
core/grounding.py - deterministic date/time/weather answers.

The local Duke Brain (see ml/duke_brain.py) has no clock, no location
sense, and no live internet access. Left to itself it hallucinates a
plausible-looking wrong answer, and live testing surfaced two real bugs:

1. A combined "what's the date, time, and weather in Lavon, TX" question
   only ever got a date/time answer - the weather part was silently
   dropped, because the old check in duke_brain.py returned immediately
   on any date/time match without looking at the rest of the question.
2. The date/time answer used the server's raw UTC clock with no timezone
   conversion, so it was hours off from the asked-about location's actual
   local time (and formatted as "2026-09-26 (Saturday), current time
   14:12" rather than something a person would actually say).

This module answers both together when asked together, converts to the
named location's real timezone when one is given (falling back to
LABEELE.AI's home timezone, Central Time, otherwise), and fetches real
current weather from Open-Meteo (free, no API key) instead of guessing.
"""
import re
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import httpx

from coordinator_API.core.config import logger

DEFAULT_TZ = ZoneInfo("America/Chicago")
DEFAULT_TZ_LABEL = "Central Time"

DATE_TIME_PATTERN = re.compile(
    r"\b(what'?s?\s+(is\s+)?(the\s+)?(current\s+|today'?s\s+)?(date|day|time)\b|"
    r"what\s+(day|date|time)\s+is\s+it|current\s+date|current\s+time)",
    re.IGNORECASE,
)

_WEATHER_LOCATION = re.compile(
    r"weather\s+(?:in|for|at)\s+([A-Za-z][A-Za-z ,.'-]*?)"
    r"(?:\s*[!?.]|\s*,?\s*(?:and|thank|right\s+now|today|currently|please)\b|$)",
    re.IGNORECASE,
)

_WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "freezing fog",
    51: "light drizzle", 53: "drizzle", 55: "dense drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow",
    80: "light showers", 81: "showers", 82: "heavy showers",
    95: "a thunderstorm", 96: "a thunderstorm with hail", 99: "a severe thunderstorm with hail",
}


def _geocode(location: str) -> Optional[dict]:
    try:
        resp = httpx.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": location, "count": 1},
            timeout=8.0,
        )
        resp.raise_for_status()
        results = resp.json().get("results")
        return results[0] if results else None
    except Exception as e:
        logger.warning(f"⚠️ Geocoding failed for '{location}': {e}")
        return None


def _fetch_weather(lat: float, lon: float) -> Optional[dict]:
    try:
        resp = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "timezone": "auto",
            },
            timeout=8.0,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"⚠️ Weather fetch failed: {e}")
        return None


def _format_time(dt: datetime) -> str:
    hour12 = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{hour12}:{dt.minute:02d} {ampm}"


def try_ground(question: str) -> Optional[str]:
    """Returns a deterministic, factual answer for date/time and/or weather
    questions asked together or separately, or None if the question needs
    neither. Returns None (rather than a partial answer) if weather was
    asked for but couldn't actually be fetched, so the caller can fall
    back to the model saying so honestly instead of this silently
    omitting it."""
    wants_date_time = bool(DATE_TIME_PATTERN.search(question))
    location_match = _WEATHER_LOCATION.search(question)
    wants_weather = location_match is not None

    if not wants_date_time and not wants_weather:
        return None

    tz = DEFAULT_TZ
    tz_label = DEFAULT_TZ_LABEL
    place_label = None
    weather_sentence = None

    if wants_weather:
        location = location_match.group(1).strip().rstrip(",")
        geo = _geocode(location)
        if not geo:
            return f"I couldn't find a location matching \"{location}\" to check the weather."

        weather = _fetch_weather(geo["latitude"], geo["longitude"])
        if not weather or "current_weather" not in weather:
            return f"I couldn't reach live weather data for {location} right now - please try again in a moment."

        place_label = ", ".join(filter(None, [geo.get("name"), geo.get("admin1")]))
        cw = weather["current_weather"]
        condition = _WEATHER_CODES.get(cw.get("weathercode"), "changing conditions")
        weather_sentence = (
            f"The weather in {place_label} is currently {condition}, "
            f"{round(cw['temperature'])}°F with wind around {round(cw['windspeed'])} mph."
        )

        # Localize date/time to the actual place asked about (Open-Meteo
        # returns the real IANA timezone for these coordinates), not just
        # LABEELE.AI's Texas default.
        place_tz = weather.get("timezone")
        if place_tz:
            try:
                tz = ZoneInfo(place_tz)
                # Open-Meteo's own "timezone_abbreviation" is sometimes just
                # a raw offset ("GMT-5") - %Z on a real zoneinfo-aware
                # datetime gives the actual abbreviation ("CDT") instead.
                tz_label = datetime.now(tz).strftime("%Z") or weather.get("timezone_abbreviation") or place_tz
            except Exception:
                pass

    sentences = []
    if wants_date_time:
        now = datetime.now(tz)
        where = f" in {place_label}" if place_label else ""
        sentences.append(
            f"Today is {now.strftime('%A, %B')} {now.day}, {now.year}, and the current "
            f"time{where} is {_format_time(now)} {tz_label}."
        )
    if weather_sentence:
        sentences.append(weather_sentence)

    return " ".join(sentences)
