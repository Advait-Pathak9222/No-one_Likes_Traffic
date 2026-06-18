#!/usr/bin/env python3
"""Cache a small CARTO/OpenStreetMap basemap tile set for the ParkPulse demo.

The dashboard still attributes OpenStreetMap/CARTO and can use live tiles, but a
local tile cache makes the judge-facing prototype reliable on conference Wi-Fi
or during offline screen recording.
"""

from __future__ import annotations

import math
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "public" / "data" / "tiles" / "carto_light"

# Bengaluru plus a small margin around the provided violation coordinates.
BBOX = {
    "min_lon": 77.25,
    "max_lon": 77.92,
    "min_lat": 12.74,
    "max_lat": 13.26,
}
ZOOMS = range(10, 14)
SUBDOMAINS = ["a", "b", "c", "d"]
USER_AGENT = "ParkPulseBengaluruHackathon/1.0 (local demo tile cache)"


def lonlat_to_tile(lon: float, lat: float, zoom: int) -> tuple[int, int]:
    lat_rad = math.radians(lat)
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def tile_ranges(zoom: int) -> tuple[range, range]:
    x_min, y_max = lonlat_to_tile(BBOX["min_lon"], BBOX["min_lat"], zoom)
    x_max, y_min = lonlat_to_tile(BBOX["max_lon"], BBOX["max_lat"], zoom)
    return range(min(x_min, x_max), max(x_min, x_max) + 1), range(min(y_min, y_max), max(y_min, y_max) + 1)


def download(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 100:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        dest.write_bytes(response.read())
    return True


def main() -> None:
    planned = []
    for zoom in ZOOMS:
        xs, ys = tile_ranges(zoom)
        for x in xs:
            for y in ys:
                planned.append((zoom, x, y))

    print(f"Preparing {len(planned)} CARTO light basemap tiles in {OUT_DIR}")
    created = 0
    for index, (zoom, x, y) in enumerate(planned, 1):
        subdomain = SUBDOMAINS[(x + y + zoom) % len(SUBDOMAINS)]
        url = f"https://{subdomain}.basemaps.cartocdn.com/light_all/{zoom}/{x}/{y}.png"
        dest = OUT_DIR / str(zoom) / str(x) / f"{y}.png"
        try:
            if download(url, dest):
                created += 1
                time.sleep(0.035)
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"Warning: failed {zoom}/{x}/{y}: {exc}")
        if index % 50 == 0 or index == len(planned):
            print(f"{index}/{len(planned)} checked, {created} downloaded")
    print(f"Done. {created} new tiles downloaded; existing tiles reused.")


if __name__ == "__main__":
    main()
