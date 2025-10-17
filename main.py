import sys
from tkinter import filedialog
import os
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import heapq
from geopy.distance import great_circle

from parser import parse_json


# LOCATIONS AND DATES

def _process_date(date, date_points, lat, lon, min_date, max_date,
                  max_distance):
    """ Process a single date's points in parallel. """
    if not (min_date <= date <= max_date):
        return []

    local_points = []
    for point in date_points:
        distance = great_circle(
            (point["lat"], point["lon"]), (lat, lon)).meters
        if distance <= max_distance:
            local_points.append({**point, "distance": distance})

    return local_points


def find_closest_points_by_location(
        points_by_date: dict[str, list[dict]], lat: float, lon: float,
        min_date: str, max_date: str,
        max_distance: int = 100, n: int = 5) -> list[dict]:
    # Find all points within the date range
    closest_points = []
    index = 0

    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(
                _process_date,
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

    # index = 0  # to ensure unique keys and stop dict comparison
    # for date, date_points in points_by_date.items():
    #     if date < min_date or date > max_date:
    #         continue

    #     for point in date_points:
    #         distance = geodesic(
    #             (point["lat"], point["lon"]), (lat, lon)).meters

    #         if distance <= max_distance:
    #             point_with_distance = {**point, "distance": distance}
    #             heapq.heappush(closest_points, (distance,
    #                            index, point_with_distance))
    #         index += 1

    # # Get 'n' smallest distances
    # if not closest_points:
    #     return None
    # return [point for _, _, point in heapq.nsmallest(n, closest_points,
    #                                                   y=lambda p: p[0])]


def find_point_from_date(
        points_by_date: dict[str, list[dict]],
        time: str):
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


def find_points_from_locations(
        points_by_date: dict[str, list[dict]],
        picture_locations: dict[str, dict[str, float]]
        ) -> dict[str, list[dict]]:
    """Finner punkter fra en liste med lokasjoner."""

    def resolve_duplicate_time_entry(min_date, found_point):  
        if not found_point:
            return min_date, None
        if min_date == found_point["time"]:
            found_point["time"] = \
                (datetime.fromisoformat(found_point["time"])
                 + timedelta(minutes=1)).isoformat()
        else:
            min_date = found_point["time"]
        return min_date, found_point

    min_date = "2024-09-01"  # input("Enter start date (YYYY-MM-DD): ")
    max_date = None  # input("Enter end date (YYYY-MM-DD): ")

    if not min_date:
        min_date = "2013-01-01"
    if not max_date:
        max_date = datetime.now().date().isoformat()

    mapped_picture_points: dict[str, list[dict]] = {}

    for name, location in picture_locations.items():
        print(f"Finding dates for {name}...", end='\r')

        lat, lon = location["lat"], location["lon"]
        closest_image_points = find_closest_points_by_location(
            points_by_date, lat, lon, min_date, max_date)

        # Add one minute to the time if
        # it is the same as the previous picture
        # _, closest_image_points = resolve_duplicate_time_entry(min_date,
        #                                               closest_image_points)
        # min_date
        mapped_picture_points[name] = closest_image_points

    return mapped_picture_points


# PICTURES

def read_picture(picture_file: str):
    def get_exif_data(image_path):
        """Henter EXIF-data fra et bilde."""
        image = Image.open(image_path)
        exif_data = image._getexif()  # type: ignore
        if not exif_data:
            return None

        # Konverter EXIF-tags til menneskeleselige navn
        exif = {}
        for tag, value in exif_data.items():
            tag_name = TAGS.get(tag, tag)
            exif[tag_name] = value
        return exif

    def get_gps_data(exif_data):
        """Henter GPS-data fra EXIF."""
        if 'GPSInfo' not in exif_data:
            return None

        gps_info = {}
        for key in exif_data['GPSInfo'].keys():
            name = GPSTAGS.get(key, key)
            gps_info[name] = exif_data['GPSInfo'][key]
        return gps_info

    def convert_to_decimal(coords, ref):
        """Konverterer GPS-koordinater til desimalformat."""
        degrees = float(coords[0])
        minutes = float(coords[1])
        seconds = float(coords[2])
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)

        # Hvis referansen er sør eller vest, gjør tallet negativt
        if ref in ['S', 'W']:
            decimal = -decimal
        return decimal

    def get_lat_lon(image_path):
        """Henter breddegrad og lengdegrad fra et bilde."""
        exif_data = get_exif_data(image_path)
        if not exif_data:
            return None, None

        gps_data = get_gps_data(exif_data)
        if not gps_data:
            return None, None

        latitude = gps_data.get('GPSLatitude')
        latitude_ref = gps_data.get('GPSLatitudeRef')
        longitude = gps_data.get('GPSLongitude')
        longitude_ref = gps_data.get('GPSLongitudeRef')

        if latitude and latitude_ref and longitude and longitude_ref:
            lat = convert_to_decimal(latitude, latitude_ref)
            lon = convert_to_decimal(longitude, longitude_ref)
            return lat, lon

        return None, None

    return get_lat_lon(picture_file)


def read_pictures(
            picture_files: tuple[str, ...],
        ) -> dict[str, dict[str, float]]:
    """Leser GPS-koordinater fra bilder."""
    picture_coordinates = {}
    if not picture_files:
        print("No pictures selected > Exiting...")
        sys.exit(1)

    for picture_file in picture_files:
        # Read the latidude and longitude from the picture
        lat, lon = read_picture(picture_file)
        print("Picture:" +
              f"{picture_file} -> Latitude: {lat:.6f}, Longitude: {lon:.6f}")
        picture_coordinates[picture_file] = {"lat": lat, "lon": lon}

    return picture_coordinates

# TESTING


def test(points_by_date):
    test_locations = {
        "Helsinki cathedral": "60.170418, 24.952174",
        "Tallin city gates": "59.43658520202904, 24.75032650543977"
    }

    found_dates = {}

    for name, location in test_locations.items():
        lat, lon = location.split(", ")
        min_date = "2024-09-01"
        max_date = "2024-09-31"
        found_point = find_closest_points_by_location(
            points_by_date, float(lat), float(lon), min_date, max_date)
        found_dates[name] = found_point["time"] if found_point else None

    print("test_results")
    for name, found_date in found_dates.items():
        if not found_date:
            print("name: ", name, "-> date: not found")
        print("name: ", name, "-> date: ", found_date)

# MAIN


def print_results(picture_dates):
    """Skriver resultatene til konsollen."""
    for name, point in picture_dates.items():
        if point:
            times = []
            previous_date = None
            point = sorted(point, key=lambda p: p["time"])
            times.append(point[0]["time"].replace("T", " "))
            for p in point[1:]:
                current_date = p["time"].split("T")[0]
                time_part = p["time"].split("T")[1]
                if current_date != previous_date:
                    times.append("\n" + " " * 53)
                    times.append(current_date + " " + time_part)
                    previous_date = current_date
                else:
                    times.append(", " + time_part)
            times = "".join(times)
            print(f"Picture: ...{name[18:]:<30} -> Dates: {times}")
        else:
            print(f"Picture: ...{name[18:]:<30} -> No date found")


def write_picture_dates_to_file(picture_dates):
    """Skriver resultatene til en fil."""
    with open("picture_dates.txt", "w") as f:
        for name, point in picture_dates.items():
            if point:
                times = []
                previous_date = None
                point = sorted(point, key=lambda p: p["time"])
                times.append(point[0]["time"].replace("T", " "))
                for p in point[1:]:
                    current_date = p["time"].split("T")[0]
                    time_part = p["time"].split("T")[1]
                    if current_date != previous_date:
                        times.append("\n" + " " * 53)
                        times.append(current_date + " " + time_part)
                        previous_date = current_date
                    else:
                        times.append(", " + time_part)
                times = "".join(times)
                f.write(f"Picture: ...{name[18:]:<30} -> Dates: {times}\n")
            else:
                f.write(f"Picture: ...{name[18:]:<30} -> No date found\n")


def open_filedialog():
    filetypes = [
        ("Bilder", "*.jpg *.jpeg *.png")
    ]
    initial_dir = os.path.dirname(os.path.abspath(__file__))
    picture_files = filedialog.askopenfilename(
        title="Velg bilder",
        filetypes=filetypes,
        multiple=True,  # type: ignore
        initialdir=initial_dir,
    )
    return picture_files


def main():
    input_path = "timeline.json"
    if "-i" in sys.argv:
        try:
            input_path = sys.argv[sys.argv.index("-i") + 1]
        except IndexError:
            print("Usage: python parser.py -i <input_file>")
            sys.exit(1)

    picture_files: tuple[str, ...] = ()
    if "-fd" in sys.argv:
        picture_files = open_filedialog()
    elif "-i" in sys.argv:
        picture_files = tuple(sys.argv[sys.argv.index("-i") + 1:])
    else:
        # picture_files = sys.argv[1:]
        picture_files = tuple(
            os.path.join("testbilder", f) for f in os.listdir("testbilder")
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        )

    try:
        points_by_date = parse_json(input_path)
    except FileNotFoundError:
        print(f"File not found: {input_path} > Exiting...")
        sys.exit(1)

    if not picture_files:
        print("No pictures selected > Exiting...")
        sys.exit(1)

    picture_locations = read_pictures(picture_files=picture_files)

    picture_dates = find_points_from_locations(
        points_by_date=points_by_date,
        picture_locations=picture_locations)

    print_results(picture_dates)

    save_to_file = input("Save to file? (y/n) ").lower() == "y"
    if save_to_file:
        write_picture_dates_to_file(picture_dates)

    # test(points_by_date=points_by_date)


if __name__ == "__main__":
    main()
