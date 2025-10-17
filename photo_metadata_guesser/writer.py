from __future__ import annotations

from typing import Dict, List


def print_picture_dates_to_console(
    picture_dates: Dict[str, List[dict]]
) -> None:
    """Format and print picture dates to the console.

    The function sorts points by their "time" key, replaces the 'T' with a
    space and groups timestamps on the same date on one line. If no points are
    present for a picture it prints "No date found".
    """
    for name, point in picture_dates.items():
        if point:
            times: list[str] = []
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
            print(f"Picture: ...{name[-18:]:<30} -> Dates: {"".join(times)}")
        else:
            print(f"Picture: ...{name[-18:]:<30} -> No date found")


def write_picture_dates_to_file(picture_dates: Dict[str, List[dict]]) -> None:
    """Write the formatted picture dates to `picture_dates.txt`.

    Each picture is written on its own line; multi-date entries use the same
    alignment as the console output.
    """
    with open("picture_dates.txt", "w", encoding="utf-8") as f:
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
                f.write(f"Picture: ...{name[-18:]:<30} -> Dates: {"".join(times)}\n")
            else:
                f.write(f"Picture: ...{name[-18:]:<30} -> No date found\n")
