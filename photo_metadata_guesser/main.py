import sys
from tkinter import filedialog
import os
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import heapq
from geopy.distance import great_circle

from .parser import parse_json
from .writer import print_picture_dates_to_console, write_picture_dates_to_file
from .mapper import find_points_from_locations

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
              f"{picture_file[-18:]:<30} -> Latitude: {lat:.6f}, Longitude: {lon:.6f}",
              end="\r", flush=True)
        picture_coordinates[picture_file] = {"lat": lat, "lon": lon}

    return picture_coordinates

# TESTING


def test(points_by_date) -> None:
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
        found_dates[name] = found_point[0]["time"] if found_point else None

    print("test_results")
    for name, found_date in found_dates.items():
        if not found_date:
            print("name: ", name, "-> date: not found")
        print("name: ", name, "-> date: ", found_date)

# MAIN
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

    print_picture_dates_to_console(picture_dates)

    save_to_file = input("Save to file? (y/n) ").lower() == "y"
    if save_to_file:
        write_picture_dates_to_file(picture_dates)


if __name__ == "__main__":
    main()
