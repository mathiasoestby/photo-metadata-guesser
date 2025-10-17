# Photo Metadata Guesser

Map image EXIF GPS coordinates to timeline points (e.g., exported JSON) and creates a list of the closest matching timestamps.

## Features
- Read GPS coordinates from image EXIF data (JPG/JPEG/PNG)
- Parse timeline JSON and group points by date
- Find up to N closest points per image within a max distance and date range
- Simple CLI and text output file option

## Requirements
- Python 3.10+
- Dependencies: Pillow, geopy, tkinter (ships with Python on Windows)

Install requirements:

```
pip install -r requirements.txt
```

## Usage
From the project root:

```
python -m gps_image_mapper.cli --input timeline.json --files testbilder\R1-02783-001A.JPG --save
```

Or open a file dialog to select images:

```
python -m gps_image_mapper.cli --input Tidslinje.json --filedialog --save
```

Options:
- `--input` / `-i`: Path to the timeline JSON (default: `Tidslinje.json`)
- `--files`: One or more image files to process
- `--filedialog`: Open a file dialog to select images
- `--save`: Save results to `picture_dates.txt`
- `--max-distance`: Max distance in meters for matching points (default 100)
- `--start` / `--end`: Date window in `YYYY-MM-DD` (default: 2013-01-01 to today)
- `-n` / `--num`: Number of closest points per image (default 5)

## Project Structure
- `gps_image_mapper/` package with:
  - `cli.py` – command-line interface
  - `timeline_parser.py` – JSON parsing utilities
  - `exif_reader.py` – EXIF coordinate extraction
  - `mapper.py` – matching logic
  - `output.py` – printing and file output helpers
- `main.py` – thin wrapper calling the CLI (for convenience)
- `testbilder/` – sample images (not required)

## Notes
- `.gitignore` excludes personal data exports and caches.
- The original Norwegian file name `Tidslinje.json` is still supported as default input; feel free to rename your export when sharing.

## License
MIT (you can change this if you prefer).