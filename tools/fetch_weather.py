#!/usr/bin/env python3
"""Fetch live weather (Open-Meteo, no key) and pollen (Pollen.com, unofficial)
into the JSON that gen_weather.py renders.

    python tools/fetch_weather.py weather.json            # Eden Prairie, MN
    python tools/fetch_weather.py weather.json --lat 44.85 --lon -93.47 --zip 55344 --place "EDEN PRAIRIE, MN"
    python tools/gen_weather.py weather.json && python ezsign_write.py examples/weather_400x300.png --reader PICC

Pollen.com returns one 0-12 index plus the top "trigger" plants; per-type bars
are derived from that (index scaled to 0-5, applied to the plant types named
as triggers). Mold is not reported there and is shown as "no data".
"""
import argparse, datetime as dt, json, sys, urllib.request

WMO = {0: ("sun", "Clear"), 1: ("sun", "Mostly sun"), 2: ("partly", "Pt cloudy"), 3: ("cloud", "Cloudy"),
       45: ("fog", "Fog"), 48: ("fog", "Rime fog"), 51: ("rain", "Drizzle"), 53: ("rain", "Drizzle"),
       55: ("rain", "Drizzle"), 56: ("rain", "Frz drizzle"), 57: ("rain", "Frz drizzle"),
       61: ("rain", "Lt rain"), 63: ("rain", "Rain"), 65: ("rain", "Hvy rain"), 66: ("rain", "Frz rain"),
       67: ("rain", "Frz rain"), 71: ("snow", "Lt snow"), 73: ("snow", "Snow"), 75: ("snow", "Hvy snow"),
       77: ("snow", "Snow grains"), 80: ("rain", "Showers"), 81: ("rain", "Showers"), 82: ("rain", "Hvy showers"),
       85: ("snow", "Snow shwr"), 86: ("snow", "Snow shwr"), 95: ("storm", "T-storm"),
       96: ("storm", "T-storm hail"), 99: ("storm", "T-storm hail")}
DIRS = "N NE E SE S SW W NW".split()


def get(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh) ezsign-nfc", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def weather(lat, lon, tz):
    url = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           "&current=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,wind_direction_10m,weather_code"
           "&hourly=precipitation_probability"
           "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset"
           "&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone={tz}&forecast_days=8").format(lat=lat, lon=lon, tz=tz)
    return get(url)


def pollen(zip_code):
    url = f"https://www.pollen.com/api/forecast/current/pollen/{zip_code}"
    j = None
    for attempt in range(2):                    # unofficial endpoint, sometimes slow; degrade gracefully
        try:
            j = get(url, {"Referer": url, "Accept": "application/json"}, timeout=30); break
        except Exception as e:
            print(f"pollen fetch failed (try {attempt + 1}/2):", e, file=sys.stderr)
    if j is None:
        return {"index": 0.0, "level": "N/A", "tree": None, "grass": None, "weed": None, "mold": None, "top": "no data"}
    today = next(p for p in j["Location"]["periods"] if p["Type"] == "Today")
    idx = float(today["Index"])
    level = ("LOW" if idx < 2.5 else "LOW-MED" if idx < 4.9 else "MED" if idx < 7.3 else "MED-HIGH" if idx < 9.7 else "HIGH")
    seg = max(1, round(idx / 12 * 5)) if idx > 0 else 0
    types = {t["PlantType"].lower() for t in today.get("Triggers", [])}
    return {"index": idx, "level": level,
            "tree": seg if "tree" in types else 0, "grass": seg if "grass" in types else 0,
            "weed": seg if "weed" in types or "ragweed" in types else 0, "mold": None,
            "top": ", ".join(t["Name"] for t in today.get("Triggers", [])[:3]) or "none"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--lat", type=float, default=44.8547); ap.add_argument("--lon", type=float, default=-93.4708)
    ap.add_argument("--zip", default="55344"); ap.add_argument("--place", default="EDEN PRAIRIE, MN")
    ap.add_argument("--tz", default="America/Chicago"); ap.add_argument("--alert", default=None, help="text for the red alert bar")
    a = ap.parse_args()

    w = weather(a.lat, a.lon, a.tz)
    now = dt.datetime.fromisoformat(w["current"]["time"])
    cur, dly, hr = w["current"], w["daily"], w["hourly"]
    icon, cond = WMO.get(cur["weather_code"], ("cloud", "Cloudy"))
    hours = []
    for i, ts in enumerate(hr["time"]):
        t = dt.datetime.fromisoformat(ts)
        if t >= now and (t.hour % 3 == 0) and len(hours) < 6:
            lab = "12a" if t.hour == 0 else "12p" if t.hour == 12 else f"{t.hour % 12}{'a' if t.hour < 12 else 'p'}"
            hours.append([lab, int(hr["precipitation_probability"][i] or 0)])
    week = []
    for i in range(1, 8):
        d = dt.date.fromisoformat(dly["time"][i])
        ic, cd = WMO.get(dly["weather_code"][i], ("cloud", "Cloudy"))
        week.append({"day": d.strftime("%a").upper(), "icon": ic, "cond": cd,
                     "hi": round(dly["temperature_2m_max"][i]), "lo": round(dly["temperature_2m_min"][i]),
                     "rain": int(dly["precipitation_probability_max"][i] or 0)})
    fmt_t = lambda s: dt.datetime.fromisoformat(s).strftime("%-I:%M")
    lo_tonight = round(dly["temperature_2m_min"][1])
    data = {
        "place": a.place, "date": now.strftime("%a %b %-d").upper(), "updated": now.strftime("%-I:%M %p"),
        "today": {"temp": round(cur["temperature_2m"]), "feels": round(cur["apparent_temperature"]),
                  "hi": round(dly["temperature_2m_max"][0]), "lo": round(dly["temperature_2m_min"][0]),
                  "cond": cond, "icon": icon,
                  "wind": f"{DIRS[int((cur['wind_direction_10m'] + 22.5) // 45) % 8]} {round(cur['wind_speed_10m'])} mph",
                  "hum": cur["relative_humidity_2m"], "sunrise": fmt_t(dly["sunrise"][0]), "sunset": fmt_t(dly["sunset"][0]),
                  "rain": int(dly["precipitation_probability_max"][0] or 0)},
        "alert": a.alert or ("Freeze tonight" if lo_tonight <= 32 else None),
        "tonight": f"{WMO.get(dly['weather_code'][1], ('', 'Cloudy'))[1]}, low {lo_tonight}°",
        "rain_hours": hours,
        "pollen": pollen(a.zip),
        "week": week,
    }
    json.dump(data, open(a.out, "w"), indent=1)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
