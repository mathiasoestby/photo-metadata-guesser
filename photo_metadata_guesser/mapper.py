from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from geopy.distance import great_circle
import heapq

import numpy as np


def _process_date_great_circle(
        date, date_points, lat, lon, min_date, max_date, max_distance
) -> list[dict]:
    """ Process a date's points using geopys great circle."""
    if not (min_date <= date <= max_date):
        return []

    local_points = []
    for point in date_points:
        distance = great_circle(
            (point["lat"], point["lon"]), (lat, lon)
        ).meters
        if distance <= max_distance:
            local_points.append({**point, "distance": distance})

    return local_points


def find_closest_points_multithreaded(
        points_by_date, lat, lon, min_date, max_date,
        max_distance, n) -> list[dict]:
    """Find closest points by location using Geopy and multithreading."""

    closest_points = []
    index = 0
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(
                _process_date_great_circle,
                date,
                date_points,
                lat,
                lon,
                min_date,
                max_date,
                max_distance,
            ): date
            for date, date_points in points_by_date.items()
        }

        for future in as_completed(futures):
            try:
                local_points = future.result()

                for point in local_points:
                    if len(closest_points) < n:
                        heapq.heappush(
                            closest_points, (-point["distance"], index, point))
                    else:
                        heapq.heappushpop(
                            closest_points, (-point["distance"], index, point))
                    index += 1
            except Exception as e:
                print(f"Error processing date {futures[future]}: {e}")

    return [point for _, _, point in sorted(closest_points, reverse=True)]


def find_closest_points_vectorized(
        points_by_date, lat, lon, min_date, max_date, max_distance, n
) -> list[dict]:
    """Find closest points by location using vectorized Haversine formula."""
    def haversine(lat1, lon1, lat2, lon2):
        """Calculate the great-circle distance between two points on the Earth."""
        R = 6371000
        phi1, phi2 = np.radians(lat1), np.radians(lat2)
        dphi = np.radians(lat2 - lat1)
        dlambda = np.radians(lon2 - lon1)
        a = (np.sin(dphi / 2)**2 + np.cos(phi1)
             * np.cos(phi2) * np.sin(dlambda / 2)**2)
        return 2 * R * np.arcsin(np.sqrt(a))

    results = []
    for date, pts in points_by_date.items():
        if not (min_date <= date <= max_date):
            continue
        lat_points = np.array([p["lat"] for p in pts])
        lon_points = np.array([p["lon"] for p in pts])
        distances = haversine(lat_points, lon_points, lat, lon)
        mask = distances <= max_distance
        for p, d, keep in zip(pts, distances, mask):
            if keep:
                results.append({**p, "distance": float(d)})
    return results


def find_closest_points_by_location(
        points_by_date: dict[str, list[dict]],
        lat: float,
        lon: float,
        min_date: str,
        max_date: str,
        max_distance: int,
        n: int
) -> list[dict]:
    """Find closest points by location using multithreading."""

    args = (points_by_date, lat, lon, min_date, max_date, max_distance, n)

    return find_closest_points_vectorized(*args)


def find_points_from_locations(
        points_by_date: dict[str, list[dict]],
        picture_locations: dict[str, dict[str, float]],
        min_date: str,
        max_date: str,
        max_distance: int,
        n: int
) -> dict[str, list[dict]]:
    """Find points from a list of locations."""
    mapped_picture_points: dict[str, list[dict]] = {}
    for name, location in picture_locations.items():
        print(f"Finding dates for {name[-18:]:<30}...", end='\r', flush=True)
        lat, lon = location["lat"], location["lon"]
        closest_image_points = find_closest_points_by_location(
            points_by_date, lat, lon, min_date, max_date, max_distance, n)
        mapped_picture_points[name] = closest_image_points
    # Clear terminal line after processing
    print(" " * 100, end='\r', flush=True)

    return mapped_picture_points


def find_point_from_date(
        points_by_date: dict[str, list[dict]],
        time: str):
    """Find point from a specific date and time."""
    date = datetime.fromisoformat(time).date().isoformat()

    if date not in points_by_date:
        return None

    points = points_by_date[date]

    # Find closest point
    closest_point = None
    closest_distance = float("inf")
    for point in points:
        distance = abs(datetime.fromisoformat(point["time"])
                       - datetime.fromisoformat(time)).total_seconds()
        if distance < closest_distance:
            closest_distance = distance
            closest_point = point

    return closest_point
