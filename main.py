"""
ETS Bus Times - Kivy mobile app version.

Wraps the same logic as the desktop ets_next_departures.py script in a
simple touch UI: enter one or more stop IDs, tap Refresh, see a list of
upcoming departures. Static schedule is cached daily; realtime delay
lookup is attempted on every refresh and silently skipped if unavailable.
"""

import csv
import io
import os
import re
import threading
import zipfile
from datetime import datetime, timedelta

import urllib.request
import urllib.error

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

GTFS_URL = "https://gtfs.edmonton.ca/TMGTFSRealTimeWebService/GTFS/gtfs.zip"
REALTIME_URL = "https://gtfs.edmonton.ca/TMGTFSRealTimeWebService/TripUpdate/TripUpdates.pb"
BROWSER_HEADERS = {"User-Agent": "Mozilla/5.0 (Android)"}


def cache_dir():
    # App.user_data_dir resolves to proper app-private storage on Android
    return App.get_running_app().user_data_dir


def download_gtfs():
    cd = cache_dir()
    os.makedirs(cd, exist_ok=True)
    zip_path = os.path.join(cd, "gtfs.zip")
    req = urllib.request.Request(GTFS_URL, headers=BROWSER_HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    with open(zip_path, "wb") as f:
        f.write(data)

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
    path = os.path.join(cache_dir(), name)
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


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


def iter_matching_stop_times(stop_id_set):
    path = os.path.join(cache_dir(), "stop_times.csv")
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["stop_id"] in stop_id_set:
                yield row


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


# Your stops - baked in so nothing needs to be entered
STOP_IDS = ["4084", "4062"]


class ETSApp(App):
    def build(self):
        self.title = "ETS Bus Times"
        root = BoxLayout(orientation="vertical", padding=10, spacing=10)

        btn_row = BoxLayout(size_hint=(1, None), height=48, spacing=10)
        self.refresh_btn = Button(text="Refresh Now")
        self.refresh_btn.bind(on_press=lambda *_: self.refresh(force_download=False))
        self.resync_btn = Button(text="Re-sync Schedule")
        self.resync_btn.bind(on_press=lambda *_: self.refresh(force_download=True))
        btn_row.add_widget(self.refresh_btn)
        btn_row.add_widget(self.resync_btn)
        root.add_widget(btn_row)

        self.status_label = Label(text="", size_hint=(1, None), height=30)
        root.add_widget(self.status_label)

        scroll = ScrollView()
        self.results_label = Label(
            text="Loading...",
            size_hint=(1, None), halign="left", valign="top",
        )
        self.results_label.bind(texture_size=self._update_label_height)
        scroll.add_widget(self.results_label)
        root.add_widget(scroll)

        # Auto-refresh every hour
        Clock.schedule_interval(lambda *_: self.refresh(force_download=False), 3600)
        # Load immediately on open - no tap required
        Clock.schedule_once(lambda *_: self.refresh(force_download=False), 0)

        return root

    def _update_label_height(self, instance, size):
        instance.height = size[1]
        instance.text_size = (instance.width, None)

    def set_status(self, text):
        self.status_label.text = text

    def refresh(self, force_download=False):
        self.set_status("Loading...")
        threading.Thread(target=self._refresh_worker, args=(force_download,), daemon=True).start()

    def _refresh_worker(self, force_download):
        try:
            stop_ids = STOP_IDS
            if force_download or not is_cached():
                download_gtfs()
            deps = next_departures(stop_ids)
            lines = [f"Current Time: {datetime.now().strftime('%I:%M %p').lstrip('0')}", ""]
            for d in deps:
                delay = f"  (+{d['delay_minutes']}m)" if d["delay_minutes"] > 0 else (
                    f"  ({d['delay_minutes']}m)" if d["delay_minutes"] < 0 else "")
                lines.append(
                    f"[{d['stop_id']}] Route {d['route']} - {d['headsign']}\n"
                    f"   Sched {d['scheduled_time']}   Live {d['expected_time']}   "
                    f"{d['minutes_away']} min{delay}"
                )
            if not deps:
                lines.append("No upcoming departures found in the next 3 hours.")
            text = "\n\n".join(lines)
            Clock.schedule_once(lambda *_: self._show_results(text, "Updated."))
        except Exception as e:
            Clock.schedule_once(lambda *_: self.set_status(f"Error: {e}"))

    def _show_results(self, text, status):
        self.results_label.text = text
        self.set_status(status)


if __name__ == "__main__":
    ETSApp().run()
