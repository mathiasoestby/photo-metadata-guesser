import json
from datetime import datetime


# JSON PARSING


def parse_json(input_file):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    points_by_date: dict[str, list[dict]] = {}

    # Extract data points
    for segment in data.get("semanticSegments", []):
        for path_point in segment.get("timelinePath", []):
            try:
                # Extract and parse data
                raw_coords = path_point["point"].replace("°", "").strip()
                coords = raw_coords.split(", ")
                lat, lon = float(coords[0]), float(coords[1])
                time = path_point["time"]

                # Extract date for grouping
                date = datetime.fromisoformat(time).date().isoformat()

                # Group by date
                if date not in points_by_date:
                    points_by_date[date] = []
                points_by_date[date].append({
                    "lat": lat, "lon": lon, "time": time})
            except (KeyError, ValueError):
                continue  # Skip invalid points

    return points_by_date
