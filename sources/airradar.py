"""Air Radar.

Mostra le informazioni degli aerei che transitano entro un raggio dato da
una coordinata GPS. Si appoggia alle API pubbliche ADS-B della comunita',
gratuite e senza chiave di accesso:

  adsb.fi    https://opendata.adsb.fi/api/v3/lat/{lat}/lon/{lon}/dist/{nm}
  adsb.one   https://api.adsb.one/v2/point/{lat}/{lon}/{nm}
  adsb.lol   https://api.adsb.lol/v2/point/{lat}/{lon}/{nm}

Sono tutte compatibili con il formato ADSBexchange v2, quindi i campi
restituiti sono gli stessi e i servizi si possono usare uno come riserva
dell'altro. FlightRadar24 non ha un'API libera per questo scopo.

Il raggio si esprime in chilometri e viene convertito in miglia nautiche
per l'interrogazione; la distanza reale di ogni aereo viene poi ricalcolata
con la formula dell'emisenoverso, perche' il raggio dell'API e' grossolano.

Non essendoci un'antenna locale, la copertura dipende dai riceventi
volontari della rete: la maggior parte del traffico commerciale compare,
ma non e' garantito che ci sia proprio tutto.
"""

import csv
import json
import math
import os
import threading
import time
import urllib.error
import urllib.request

from PIL import Image, ImageDraw

from .base import Source
from .clock import _load_font, parse_color

KM_PER_NM = 1.852
USER_AGENT = "zedmd-pi AirRadar"

PROVIDERS = {
    "adsb.fi": "https://opendata.adsb.fi/api/v3/lat/%(lat).5f/lon/%(lon).5f/dist/%(nm).1f",
    "adsb.one": "https://api.adsb.one/v2/point/%(lat).5f/%(lon).5f/%(nm).1f",
    "adsb.lol": "https://api.adsb.lol/v2/point/%(lat).5f/%(lon).5f/%(nm).1f",
}

PROVIDER_LIST = [("adsb.fi", "adsb.fi"), ("adsb.one", "adsb.one / airplanes.live"),
                 ("adsb.lol", "adsb.lol")]

# Campi selezionabili per la riga di dettaglio, nell'ordine in cui compaiono.
FIELD_LIST = [
    ("route", "Rotta (origine → destinazione)"),
    ("type", "Modello di aeromobile"),
    ("reg", "Immatricolazione"),
    ("altitude", "Quota"),
    ("speed", "Velocità al suolo"),
    ("track", "Direzione"),
    ("squawk", "Codice transponder"),
    ("distance", "Distanza"),
    ("hex", "Codice Mode S"),
]

CSV_COLUMNS = ["timestamp", "hex", "callsign", "registration", "type",
               "altitude_ft", "speed_kt", "track_deg", "squawk",
               "distance_km", "latitude", "longitude", "route"]


def haversine_km(lat1, lon1, lat2, lon2):
    """Distanza in chilometri fra due coordinate."""
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def fetch_json(url, timeout=12):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


def post_json(url, payload, timeout=12):
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", "replace"))


ROUTESET_URL = "https://api.adsb.lol/api/0/routeset"


class AirRadarSource(Source):
    name = "air_radar"
    label = "Air Radar"
    priority = 60  # sopra il Media Player, sotto ZeDMD: il passaggio e' un evento

    def __init__(self, cfg, width, height):
        super().__init__(cfg, width, height)
        self._running = False
        self._thread = None
        self._wake = threading.Event()

        self._lock = threading.Lock()
        self._image = None
        self._dirty = False

        self._showing = False
        self._recent = {}       # hex -> istante dell'ultima visualizzazione
        self._status = ("status.radar.waiting", {})
        self._last_poll = 0.0
        self._seen = 0

        self._logged = {}       # hex -> istante dell'ultima riga scritta
        self._font_big = _load_font(max(14, int(height * 0.40)))
        self._font_small = _load_font(max(8, int(height * 0.20)))
        self._route_cache = {}
        self._routes_found = 0
        self._routes_missing = 0

    # ------------------------------------------------------------------ ciclo di vita

    def start(self):
        if self._running:
            return
        self._running = True
        self._wake.clear()
        self._thread = threading.Thread(target=self._loop, name="airradar", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._showing = False
        self._wake.set()

    def poll_now(self):
        self._wake.set()

    # ------------------------------------------------------------------ arbitro

    def active(self):
        return self._running and self._showing

    def frame(self):
        with self._lock:
            if not self._dirty or self._image is None:
                return None
            self._dirty = False
            return self._image

    def status(self, lang=None):
        if not self._running:
            return self.t("status.disabled", lang)
        key, values = self._status
        text = self.t(key, lang, **values)
        if self._routes_found or self._routes_missing:
            text += " | " + self.t("status.radar.routes", lang,
                                   found=self._routes_found,
                                   missing=self._routes_missing)
        return text

    # ------------------------------------------------------------------ ciclo principale

    def _loop(self):
        while self._running:
            cfg = self.cfg["air_radar"]
            try:
                aircraft = self._poll(cfg)
                self._show_all(aircraft, cfg)
            except Exception as exc:
                self._status = ("status.radar.error", {"error": str(exc)})
                print("[airradar] %s" % exc)

            interval = max(15, int(cfg["poll_interval"]))
            self._wake.wait(interval)
            self._wake.clear()

    def _poll(self, cfg):
        """Interroga il provider scelto, con gli altri come riserva."""
        lat = float(cfg["latitude"])
        lon = float(cfg["longitude"])

        # Coordinate non impostate: nessuna interrogazione, nessun dato inviato.
        if abs(lat) < 0.0001 and abs(lon) < 0.0001:
            self._status = ("status.radar.nocoords", {})
            return []
        radius_km = max(0.5, float(cfg["radius_km"]))
        params = {"lat": lat, "lon": lon, "nm": max(1.0, radius_km / KM_PER_NM)}

        order = [cfg["provider"]] + [p for p in PROVIDERS if p != cfg["provider"]]
        payload = None
        used = None
        last_error = None
        for name in order:
            try:
                payload = fetch_json(PROVIDERS[name] % params)
                used = name
                break
            except (urllib.error.URLError, ValueError, OSError) as exc:
                last_error = exc
        if payload is None:
            raise RuntimeError("nessun provider raggiungibile (%s)" % last_error)

        self._last_poll = time.time()
        rows = payload.get("ac") or payload.get("aircraft") or []

        found = []
        for row in rows:
            try:
                plane_lat = float(row.get("lat"))
                plane_lon = float(row.get("lon"))
            except (TypeError, ValueError):
                continue
            distance = haversine_km(lat, lon, plane_lat, plane_lon)
            if distance > radius_km:
                continue

            altitude = row.get("alt_baro")
            if altitude == "ground":
                altitude = 0
            try:
                altitude = int(altitude)
            except (TypeError, ValueError):
                altitude = None

            ceiling = int(cfg.get("max_altitude_ft", 0) or 0)
            if ceiling and altitude is not None and altitude > ceiling:
                continue

            found.append({
                "hex": (row.get("hex") or "").strip().upper(),
                "flight": (row.get("flight") or "").strip(),
                "type": (row.get("t") or "").strip(),
                "reg": (row.get("r") or "").strip(),
                "altitude": altitude,
                "speed": row.get("gs"),
                "track": row.get("track"),
                "squawk": (row.get("squawk") or "").strip(),
                "distance": distance,
                "lat": plane_lat,
                "lon": plane_lon,
            })

        found.sort(key=lambda a: a["distance"])
        self._seen = len(found)

        # Le rotte servono se il campo e' a schermo oppure se le vuole il registro.
        if found and ("route" in (cfg.get("fields") or []) or cfg.get("log_route", True)):
            self.resolve_routes(found)
            for plane in found:
                plane["route"] = self._route_cache.get(plane["flight"], "")

        self._log_flights(found, cfg)
        # Lo stato si conserva come chiave e valori, non come frase gia'
        # composta: la lingua la decide chi lo legge, non chi lo scrive.
        self._status = ("status.radar.found",
                        {"provider": used, "count": len(found), "radius": radius_km})
        return found

    # ------------------------------------------------------------------ registro CSV

    def log_path(self):
        return self.cfg["air_radar"].get("log_path", "/var/lib/dmd/flights.csv")

    def log_info(self):
        """Numero di voli registrati e dimensione del file."""
        path = self.log_path()
        if not os.path.exists(path):
            return {"exists": False, "rows": 0, "size": "0 kB", "path": path}
        try:
            size = os.path.getsize(path)
            with open(path, newline="") as handle:
                rows = max(0, sum(1 for _ in handle) - 1)
        except OSError:
            return {"exists": False, "rows": 0, "size": "0 kB", "path": path}
        return {
            "exists": True,
            "rows": rows,
            "size": "%.1f MB" % (size / 1048576) if size >= 1048576 else "%d kB" % max(1, size // 1024),
            "path": path,
        }

    def clear_log(self):
        try:
            os.remove(self.log_path())
            return True
        except OSError:
            return False

    def _log_flights(self, aircraft, cfg):
        """Scrive una riga per ogni volo, una sola volta per passaggio."""
        if not cfg.get("log_enabled", True) or not aircraft:
            return

        window = max(30, int(cfg["cooldown"]))
        now = time.time()
        self._logged = {k: t for k, t in self._logged.items() if now - t < window}

        fresh = [p for p in aircraft
                 if (p["hex"] or p["flight"]) and (p["hex"] or p["flight"]) not in self._logged]
        if not fresh:
            return

        path = self.log_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            is_new = not os.path.exists(path) or os.path.getsize(path) == 0
            with open(path, "a", newline="") as handle:
                writer = csv.writer(handle)
                if is_new:
                    writer.writerow(CSV_COLUMNS)
                for plane in fresh:
                    key = plane["hex"] or plane["flight"]
                    self._logged[key] = now
                    route = plane.get("route") or ""
                    if not route and cfg.get("log_route", True) and plane["flight"]:
                        route = self._lookup_route(plane["flight"])
                        plane["route"] = route
                    writer.writerow([
                        time.strftime("%Y-%m-%dT%H:%M:%S"),
                        plane["hex"], plane["flight"], plane["reg"], plane["type"],
                        plane["altitude"] if plane["altitude"] is not None else "",
                        plane.get("speed") or "", plane.get("track") or "",
                        plane.get("squawk") or "",
                        "%.2f" % plane["distance"],
                        "%.5f" % plane.get("lat", 0.0), "%.5f" % plane.get("lon", 0.0),
                        route,
                    ])
        except OSError as exc:
            print("[airradar] registro non scrivibile: %s" % exc)

    def _show_all(self, aircraft, cfg):
        cooldown = max(30, int(cfg["cooldown"]))
        duration = max(2, int(cfg["display_seconds"]))
        now = time.time()

        # Non ripresentare lo stesso aereo finche' non e' passato il tempo di riposo.
        self._recent = {k: t for k, t in self._recent.items() if now - t < cooldown}

        for plane in aircraft:
            if not self._running:
                return
            key = plane["hex"] or plane["flight"]
            if not key or key in self._recent:
                continue
            self._recent[key] = time.time()

            if "route" in (cfg.get("fields") or []) and plane["flight"]:
                plane["route"] = self._lookup_route(plane["flight"])

            with self._lock:
                self._image = self._render(plane, cfg)
                self._dirty = True
            self._showing = True

            deadline = time.time() + duration
            while self._running and time.time() < deadline:
                time.sleep(0.1)

        self._showing = False

    # ------------------------------------------------------------------ rotta

    def resolve_routes(self, planes):
        """Chiede in un colpo solo le rotte di tutti i voli non ancora noti.

        Usa il servizio routeset di adsb.lol, che accetta fino a 100 voli per
        richiesta e restituisce sia i codici ICAO sia quelli IATA, piu' un
        indicatore di attendibilita'. Molto meglio di una richiesta per volo.
        """
        pending = [p for p in planes
                   if p.get("flight") and p["flight"] not in self._route_cache]
        if not pending:
            return

        payload = {"planes": [{"callsign": p["flight"],
                               "lat": float(p.get("lat") or 0.0),
                               "lng": float(p.get("lon") or 0.0)}
                              for p in pending[:100]]}
        try:
            rows = post_json(ROUTESET_URL, payload, timeout=12)
        except Exception as exc:
            print("[airradar] servizio rotte non raggiungibile: %s" % exc)
            return

        if not isinstance(rows, list):
            return

        for row in rows:
            if not isinstance(row, dict):
                continue
            callsign = (row.get("callsign") or "").strip()
            if not callsign:
                continue
            # I codici IATA sono piu' corti e leggibili su un pannello stretto.
            codes = row.get("_airport_codes_iata") or ""
            if not codes or codes == "unknown":
                codes = row.get("airport_codes") or ""
            if not codes or codes == "unknown" or "-" not in codes:
                self._route_cache[callsign] = ""
                self._routes_missing += 1
                continue
            route = "→".join(part.strip() for part in codes.split("-") if part.strip())
            self._route_cache[callsign] = route
            self._routes_found += 1

    def _lookup_route(self, callsign):
        """Origine e destinazione da hexdb.io.

        Due tentativi: prima l'API JSON, poi l'endpoint in testo semplice.
        L'esito viene messo in cache anche quando e' negativo, per non
        tempestare il servizio con lo stesso volo sconosciuto.
        """
        callsign = callsign.strip().upper()
        if not callsign:
            return ""
        if callsign in self._route_cache:
            return self._route_cache[callsign]

        route = ""
        for url, as_json in (
                ("https://hexdb.io/api/v1/route/icao/%s" % callsign, True),
                ("https://hexdb.io/callsign-route-iata?callsign=%s" % callsign, False)):
            try:
                if as_json:
                    data = fetch_json(url, timeout=6)
                    text = data.get("route", "") if isinstance(data, dict) else str(data)
                else:
                    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(request, timeout=6) as response:
                        text = response.read().decode("utf-8", "replace").strip()
                text = (text or "").strip().strip('"')
                # Formato atteso: "LIMC-EGLL". Scali multipli restano tali.
                if "-" in text and len(text) <= 40 and "unknown" not in text.lower():
                    route = "→".join(part.strip() for part in text.split("-") if part.strip())
                    break
            except Exception:
                continue

        self._route_cache[callsign] = route
        if not route:
            self._routes_missing += 1
        else:
            self._routes_found += 1
        return route

    # ------------------------------------------------------------------ disegno

    @staticmethod
    def _format_field(key, plane):
        try:
            if key == "route":
                return plane.get("route") or ""
            if key == "type":
                return plane.get("type") or ""
            if key == "reg":
                return plane.get("reg") or ""
            if key == "hex":
                return plane.get("hex") or ""
            if key == "squawk":
                return plane.get("squawk") or ""
            if key == "altitude":
                return "%dft" % plane["altitude"] if plane.get("altitude") is not None else ""
            if key == "speed":
                return "%dkt" % int(plane["speed"])
            if key == "track":
                return "%d°" % int(plane["track"])
            if key == "distance":
                return "%.1fkm" % plane["distance"]
        except (TypeError, ValueError, KeyError):
            return ""
        return ""

    def _render(self, plane, cfg):
        image = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(image)

        title_color = parse_color(cfg.get("callsign_color", "#00d0ff"), (0, 208, 255))
        info_color = parse_color(cfg.get("info_color", "#ff8c1a"), (255, 140, 26))

        title = plane["flight"] or plane["reg"] or plane["hex"] or "SCONOSCIUTO"
        box = draw.textbbox((0, 0), title, font=self._font_big)
        draw.text(((self.width - (box[2] - box[0])) // 2 - box[0], 2),
                  title, font=self._font_big, fill=title_color)

        wanted = cfg.get("fields") or ["route", "type", "altitude", "speed", "distance"]
        details = []
        for key, _label in FIELD_LIST:
            if key not in wanted:
                continue
            value = self._format_field(key, plane)
            if value:
                details.append(value)
        if not details:
            details.append("%.1fkm" % plane["distance"])

        line = "  ".join(details)
        box = draw.textbbox((0, 0), line, font=self._font_small)
        while (box[2] - box[0]) > self.width - 4 and len(details) > 2:
            details.pop(-2)
            line = "  ".join(details)
            box = draw.textbbox((0, 0), line, font=self._font_small)

        draw.text(((self.width - (box[2] - box[0])) // 2 - box[0], self.height - 20),
                  line, font=self._font_small, fill=info_color)
        return image
