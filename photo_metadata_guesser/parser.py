from __future__ import annotations

import json
from datetime import datetime

# JSON PARSING


def parse_json(input_file: str) -> dict[str, list[dict]]:
    """Parse Google Maps-timeline JSON file and group dates.

    The expected file structure contains a top-level key "semanticSegments"
    with nested "timelinePath" arrays, where each item has "point" as
    "lat, lon" and a timestamp "time".
    """
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    points_by_date: dict[str, list[dict]] = {}

    for segment in data.get("semanticSegments", []):
        for path_point in segment.get("timelinePath", []):
            try:
                raw_coords = path_point["point"].replace("°", "").strip()
                coords = raw_coords.split(", ")
                lat, lon = float(coords[0]), float(coords[1])
                time = path_point["time"]

                # Extract YYYY-MM-DD from time
                date = datetime.fromisoformat(time).date().isoformat()

                # Group by date
                points_by_date.setdefault(date, []).append(
                    {"lat": lat, "lon": lon, "time": time}
                )
            except (KeyError, ValueError):
                continue  # Skip invalid points

    return points_by_date
