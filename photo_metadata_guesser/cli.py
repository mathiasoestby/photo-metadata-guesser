import argparse
import os
import sys
from datetime import datetime, timedelta
from tkinter import filedialog

from main import (
    parse_json, read_pictures, find_points_from_locations,
    print_results, write_picture_dates_to_file
)

# from .timeline_parser import parse_json
# from .exif_reader import read_pictures
# from .mapper import find_points_from_locations
# from .output import print_results, write_picture_dates_to_file


def open_filedialog():
    filetypes = [
        ("Bilder", "*.jpg *.jpeg *.png")
    ]
    initial_dir = os.path.join(os.getcwd(), "test_pictures")
    if not os.path.isdir(initial_dir):
        # Fallback to script directory if test_pictures doesn't exist
        initial_dir = os.path.dirname(os.path.abspath(__file__))
    picture_files = filedialog.askopenfilename(
        title="Choose picture files",
        filetypes=filetypes,
        multiple=True,  # type: ignore
        initialdir=initial_dir,
    )
    return picture_files


def parse_date(date_str: str) -> str:
    """ Parse date string and validate format. """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD."
        )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="photo-metadata-guesser",
        description=(
            "Guess photo metadata based on timeline JSON "
            "data from Google Maps"
        ),
    )
    parser.add_argument(
        "-i", "--input",
        default="timeline.json",
        help="Path to timeline JSON file (default: timeline.json)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--files", nargs="*", metavar="IMG",
        help="One or more image files to process",
    )
    group.add_argument(
        "--filedialog", action="store_true",
        help="Open a file dialog to select images",
    )
    parser.add_argument(
        "--save", action="store_true",
        help="Save results to picture_dates.txt",
    )
    parser.add_argument(
        "--max-distance", type=int, default=100,
        help="Max distance in meters for matching points (default: 100)",
    )
    time_now = datetime.now()
    time_one_year_ago = time_now - timedelta(days=365)
    parser.add_argument(
        "--start",
        default=time_one_year_ago.date().isoformat(),
        type=parse_date,
        metavar="DATE",
        help="Start date (YYYY-MM-DD) for matching window",
    )
    parser.add_argument(
        "--end",
        default=time_now.date().isoformat(),
        type=parse_date,
        metavar="DATE",
        help="End date (YYYY-MM-DD) for matching window",
    )
    parser.add_argument(
        "-n", "--num", type=int, default=5,
        help="Number of closest points to report per image (default: 5)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    args = build_arg_parser().parse_args(argv)

    # Resolve images
    if args.filedialog:
        picture_files = open_filedialog()
    elif args.files:
        picture_files = tuple(args.files)
    else:
        # Fallback to testbilder directory if present
        print("No images provided")
        print("Trying 'test_pictures' directory...", end=" ")
        test_dir = os.path.join(os.getcwd(), "test_pfictures")
        if os.path.isdir(test_dir):
            picture_files = tuple(
                os.path.join(test_dir, f) for f in os.listdir(test_dir)
                if f.lower().endswith((".jpg", ".jpeg", ".png"))
            )
            print(f" {len(picture_files)} images found!")
        else:
            print("No images found. \n\nUse --files or --filedialog to "
                  "provide images.")
            return 1

    try:
        points_by_date = parse_json(args.input)
    except FileNotFoundError:
        print(f"Timeline file not found: {args.input!r}")
        return 1

    picture_locations = read_pictures(picture_files=picture_files)

    picture_dates = find_points_from_locations(
        points_by_date=points_by_date,
        picture_locations=picture_locations,
        min_date=args.start,
        max_date=args.end,
        max_distance=args.max_distance,
        n=args.num,
    )

    print_results(picture_dates)

    if args.save:
        write_picture_dates_to_file(picture_dates)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
