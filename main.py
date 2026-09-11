"""
ETS Bus Times - Flet version.

Same logic as the desktop/Kivy versions, wrapped in a Flet UI (modern,
Flutter-based look). Stop IDs are baked in below - no input needed.
"""

import os
import re
import time
import threading
import zipfile
import io
from datetime import datetime, timedelta

import urllib.request
import urllib.error

import flet as ft

GTFS_URL = "https://gtfs.edmonton.ca/TMGTFSRealTimeWebService/GTFS/gtfs.zip"
REALTIME_URL = "https://gtfs.edmonton.ca/TMGTFSRealTimeWebService/TripUpdate/TripUpdates.pb"
BROWSER_HEADERS = {"User-Agent": "Mozilla/5.0 (Android)"}

# Your stops - baked in so nothing needs to be entered
STOP_IDS = ["4084", "4062"]


def cache_dir():
    # Flet guarantees this env var points to a writable, app-private,
    # persistent directory on every platform (mobile, desktop, etc).
    d = os.getenv("FLET_APP_STORAGE_DATA") or os.getcwd()
    os.makedirs(d, exist_ok=True)
    return d


def download_gtfs():
    req = urllib.request.Request(GTFS_URL, headers=BROWSER_HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()

    cd = cache_dir()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name, dest in [
            ("stop_times.txt", "stop_times.csv"),
            ("trips.txt", "trips.csv"),
            ("routes.txt", "routes.csv"),
        ]:
            with z.open(name) as f_in, open(os.path.join(cd, dest), "wb") as f_out:
                f_out.write(f_in.read())


def is_cached():
    return os.path.exists(os.path.join(cache_dir(), "stop_times.csv"))


def load_csv_dict(name):
    import csv
    path = os.path.join(cache_dir(), name)
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def iter_matching_stop_times(stop_id_set):
    import csv
    path = os.path.join(cache_dir(), "stop_times.csv")
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["stop_id"] in stop_id_set:
                yield row


def parse_gtfs_time(t):
    h, m, s = (int(x) for x in t.split(":"))
    return timedelta(hours=h, minutes=m, seconds=s)


def fetch_realtime_feed():
    try:
        from google.transit import gtfs_realtime_pb2
    except ImportError:
        return None
    try:
        req = urllib.request.Request(REALTIME_URL, headers=BROWSER_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(raw)
        return feed
    except Exception:
        return None


def get_delay_seconds(feed, trip_id, stop_id):
    if feed is None:
        return 0
    for entity in feed.entity:
        if not entity.HasField("trip_update"):
            continue
        tu = entity.trip_update
        if tu.trip.trip_id != trip_id:
            continue
        for stu in tu.stop_time_update:
            if stu.stop_id != str(stop_id):
                continue
            if stu.HasField("departure") and stu.departure.HasField("delay"):
                return stu.departure.delay
            if stu.HasField("arrival") and stu.arrival.HasField("delay"):
                return stu.arrival.delay
        if tu.HasField("delay"):
            return tu.delay
    return 0


def next_departures(stop_ids, limit=8, window_minutes=180):
    trips = {t["trip_id"]: t for t in load_csv_dict("trips.csv")}
    routes = {r["route_id"]: r for r in load_csv_dict("routes.csv")}

    feed = fetch_realtime_feed()

    now = datetime.now()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    now_td = timedelta(hours=now.hour, minutes=now.minute, seconds=now.second)
    stop_id_set = {str(s) for s in stop_ids}

    results = []
    for row in iter_matching_stop_times(stop_id_set):
        dep_td = parse_gtfs_time(row["departure_time"])
        delta_min = (dep_td - now_td).total_seconds() / 60
        if delta_min < -2 or delta_min > window_minutes:
            continue

        trip_id = row["trip_id"]
        trip = trips.get(trip_id, {})
        route = routes.get(trip.get("route_id"), {})
        route_short = route.get("route_short_name", "?")
        headsign = trip.get("trip_headsign", "")
        headsign = re.sub(rf"^\s*{re.escape(route_short)}\s*[-:]?\s*", "", headsign)

        scheduled_dt = midnight + dep_td
        delay_seconds = get_delay_seconds(feed, trip_id, row["stop_id"])
        expected_dt = scheduled_dt + timedelta(seconds=delay_seconds)
        expected_delta_min = (expected_dt - now).total_seconds() / 60

        results.append({
            "stop_id": row["stop_id"],
            "route": route_short,
            "headsign": headsign,
            "scheduled_dt": scheduled_dt,
            "scheduled_time": scheduled_dt.strftime("%I:%M %p").lstrip("0"),
            "expected_time": expected_dt.strftime("%I:%M %p").lstrip("0"),
            "delay_minutes": round(delay_seconds / 60),
            "minutes_away": max(0, round(expected_delta_min)),
        })

    results.sort(key=lambda r: r["scheduled_dt"])
    deduped, seen = [], set()
    for r in results:
        key = (r["stop_id"], r["route"], r["headsign"], r["scheduled_time"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    return deduped[:limit]


def main(page: ft.Page):
    page.title = "ETS Bus Times"
    page.padding = 15
    page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH

    status_text = ft.Text("Loading...", size=13, color="#888888")
    results_column = ft.Column(spacing=10, expand=True, scroll=ft.ScrollMode.AUTO)

    def build_result_card(d):
        delay_note = ""
        if d["delay_minutes"] > 0:
            delay_note = f"  (+{d['delay_minutes']}m)"
        elif d["delay_minutes"] < 0:
            delay_note = f"  ({d['delay_minutes']}m)"
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        f"[{d['stop_id']}] Route {d['route']} \u2014 {d['headsign']}",
                        weight=ft.FontWeight.BOLD, size=15,
                    ),
                    ft.Text(
                        f"Sched {d['scheduled_time']}    Live {d['expected_time']}    "
                        f"{d['minutes_away']} min{delay_note}",
                        size=13, color="#555555",
                    ),
                ],
                spacing=2,
            ),
            padding=10,
            border=ft.Border.all(1, "#dddddd"),
            border_radius=8,
        )

    def refresh(force_download=True):
        status_text.value = "Loading..."
        page.update()
        threading.Thread(target=worker, args=(force_download,), daemon=True).start()

    def worker(force_download):
        try:
            if force_download or not is_cached():
                download_gtfs()
            deps = next_departures(STOP_IDS, limit=6)

            results_column.controls.clear()
            if not deps:
                results_column.controls.append(
                    ft.Text("No upcoming departures found in the next 3 hours.")
                )
            for d in deps:
                results_column.controls.append(build_result_card(d))

            status_text.value = (
                f"Current Time: {datetime.now().strftime('%I:%M %p').lstrip('0')}"
            )
        except Exception as e:
            status_text.value = f"Error: {e}"
        page.update()

    refresh_btn = ft.ElevatedButton(
        "Refresh",
        on_click=lambda e: refresh(True),
        width=200,
        height=55,
        style=ft.ButtonStyle(text_style=ft.TextStyle(size=18)),
    )

    page.add(
        ft.SafeArea(
            content=ft.Column(
                [
                    ft.Row([refresh_btn], alignment=ft.MainAxisAlignment.CENTER),
                    status_text,
                    ft.Divider(height=1),
                    results_column,
                ],
                expand=True,
                spacing=10,
            ),
            expand=True,
        )
    )

    page.update()

    # Load immediately on open - no tap required
    refresh(force_download=False)

    # Auto-refresh every hour in the background
    def auto_loop():
        while True:
            time.sleep(3600)
            refresh(force_download=False)

    threading.Thread(target=auto_loop, daemon=True).start()


if __name__ == "__main__":
    ft.run(main)
