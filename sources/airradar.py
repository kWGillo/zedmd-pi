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

import lookup

from .base import Source
from .clock import _load_font, parse_color

KM_PER_NM = 1.852

# Tela minuscola usata solo per misurare i testi: serve un contesto di
# disegno, non un'immagine vera, e crearne una nuova a ogni misura sarebbe
# sprecato visto quante volte si misura per impaginare.
_SCRATCH = Image.new("RGB", (1, 1))

# Che cosa fare quando la riga dei dettagli e' piu' larga del pannello.
OVERFLOW_MODES = ("crop", "pages", "scroll")

# Separatore fra origine e destinazione. Gli spazi ci sono di proposito: su un
# pannello a LED due nomi attaccati alla freccia si leggono come una parola
# sola, e un po' di respiro costa meno di un fraintendimento.
FRECCIA = " \u2192 "

# Margine dal bordo e distanza fra identificativo e codici della rotta.
MARGINE = 2
SPAZIO = 5

# ------------------------------------------------------------ unita' di misura
#
# I dati arrivano sempre in piedi e nodi, e la distanza la calcoliamo in
# chilometri: la conversione riguarda solo la lettura. Ogni voce porta fattore
# e simbolo, cosi' aggiungerne una non tocca il codice che disegna.
UNITS = {
    "altitude": {
        "ft": (1.0, "ft"),
        "m": (0.3048, "m"),
    },
    "speed": {
        "kt": (1.0, "kt"),
        "kmh": (1.852, "km/h"),
        "mph": (1.15078, "mph"),
    },
    "distance": {
        "km": (1.0, "km"),
        "mi": (1.0 / 1.609344, "mi"),
        "nm": (1.0 / KM_PER_NM, "nm"),
    },
}

UNIT_KEYS = {kind: tuple(scelte) for kind, scelte in UNITS.items()}


def convert(kind, valore, scelta):
    """(numero, simbolo) nell'unita' scelta, o (None, '') se il dato manca."""
    if valore is None:
        return None, ""
    tabella = UNITS[kind]
    fattore, simbolo = tabella.get(scelta) or tabella[next(iter(tabella))]
    return float(valore) * fattore, simbolo

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
    ("airline", "Compagnia aerea"),
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
               "distance_km", "latitude", "longitude", "route",
               # I codici grezzi restano dove sono: sono il dato certo, e
               # servono per rielaborare il registro. Accanto ci si mette il
               # nome leggibile, che e' quello che si vuole aprendo il CSV.
               "type_name", "route_name", "airline_name"]


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
            if not is_new and self._header_changed(path):
                # Aggiungere colonne a un file che ne ha meno produrrebbe
                # righe disallineate, illeggibili in un foglio di calcolo.
                # Il registro precedente si mette da parte con la data nel
                # nome: i dati restano, e il nuovo parte pulito.
                storico = "%s.%s.csv" % (path[:-4] if path.endswith(".csv") else path,
                                         time.strftime("%Y%m%d-%H%M%S"))
                try:
                    os.rename(path, storico)
                    print("[airradar] registro precedente conservato in %s" % storico)
                except OSError:
                    pass
                is_new = True
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
                        lookup.full("aircraft", plane["type"]) if plane["type"] else "",
                        lookup.route(route, 1),
                        lookup.airline(plane["flight"], 1),
                    ])
        except OSError as exc:
            print("[airradar] registro non scrivibile: %s" % exc)

    @staticmethod
    def _header_changed(path):
        """True se il registro esistente ha un'intestazione diversa."""
        try:
            with open(path, newline="") as handle:
                first = next(csv.reader(handle), [])
        except (OSError, StopIteration):
            return False
        return bool(first) and first != CSV_COLUMNS

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

            self._showing = True
            self._mostra(plane, cfg, duration)

        self._showing = False

    def _pubblica(self, image):
        with self._lock:
            self._image = image
            self._dirty = True

    def _mostra(self, plane, cfg, duration):
        """Tiene un aereo sul pannello per il tempo previsto.

        Con pochi campi selezionati non succede niente di speciale: si disegna
        una volta e si aspetta. Il resto di questo metodo esiste per il caso
        in cui i campi scelti sono piu' di quanti ne stiano su una riga, e
        serve decidere che cosa sacrificare: un'informazione, un po' di
        attesa, o l'immobilita' del pannello.
        """
        layout = self._layout(plane, cfg)
        deadline = time.time() + duration
        intera = "  ".join(layout["details"])

        if (not layout["details"]
                or self._text_width(intera, self._font_small) <= self.width - 4):
            # Ci sta tutto: nessuna modalita' ha motivo di comportarsi
            # diversamente, e il pannello resta fermo.
            self._pubblica(self._render_details(layout, intera))
            self._attendi(deadline)
            return

        mode = cfg.get("overflow", "pages")
        if mode not in OVERFLOW_MODES:
            mode = "pages"

        if mode == "crop":
            self._pubblica(self._render_details(layout, self._troncata(layout["details"])))
            self._attendi(deadline)
        elif mode == "scroll":
            self._scorri(layout, intera, cfg, deadline)
        else:
            self._impagina(layout, cfg, deadline)

    def _attendi(self, deadline):
        while self._running and time.time() < deadline:
            time.sleep(0.1)

    def _impagina(self, layout, cfg, deadline):
        """Alterna gruppi di campi, ognuno dei quali ci sta per intero.

        Le prime due fasce non si toccano: cambia solo il fondo, quindi
        l'aereo non "salta" mentre lo stai leggendo. Se il tempo dell'aereo
        non basta per tutte le pagine, quelle che restano si vedranno al
        passaggio successivo: meglio che non vederle mai.
        """
        pages = self._pagine(layout["details"])
        durata = max(1, int(cfg.get("page_seconds", 3)))
        index = 0
        while self._running and time.time() < deadline:
            self._pubblica(self._render_details(layout, "  ".join(pages[index])))
            # Una pagina cominciata si vede per intero: il tempo dell'aereo e'
            # un minimo, non una ghigliottina. Tagliarla a meta' del suo turno
            # e' esattamente cio' che si e' voluto evitare impaginando.
            self._attendi(time.time() + durata)
            index = (index + 1) % len(pages)

    def _scorri(self, layout, line, cfg, deadline):
        """Fa scorrere la sola fascia dei dettagli, da destra a sinistra.

        Il testo che scorre si legge senza aspettare, ma e' anche l'unica
        parte del pannello in movimento continuo: su una matrice a 38 Hz
        lascia una scia leggera. E' il motivo per cui non e' la modalita'
        predefinita.

        **Una passata cominciata si porta a termine.** Il tempo dell'aereo qui
        e' un minimo, non una scadenza: interromperlo a meta' significherebbe
        far sparire una riga che si sta ancora leggendo, che e' il difetto per
        cui lo scorrimento esisteva. Si cambia aereo solo quando l'ultimo
        carattere e' uscito da sinistra e il tempo previsto e' passato.
        """
        strip = self._striscia(layout, line)
        fondo = self._base(layout)
        fps = max(10, min(60, int(cfg.get("scroll_fps", 30))))
        speed = max(10, int(cfg.get("scroll_speed", 40)))
        step = speed / float(fps)
        end = -float(strip.width)

        while self._running:
            position = float(self.width)
            while self._running and position > end:
                canvas = fondo.copy()
                canvas.paste(strip, (int(round(position)), layout["bottom"]))
                self._pubblica(canvas)
                position -= step
                time.sleep(1.0 / fps)
            # Fuori campo a sinistra: qui, e solo qui, si guarda l'orologio.
            if time.time() >= deadline:
                return

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
            # I codici IATA sono piu' corti e leggibili su un pannello
            # stretto, ma spesso il servizio non li ha e resta solo la grafia
            # ICAO: la tabella di conversione conosce entrambe, quindi
            # ripiegare qui non costa piu' la traduzione.
            codes = row.get("_airport_codes_iata") or ""
            if not codes or codes == "unknown":
                codes = row.get("airport_codes") or ""
            if not codes or codes == "unknown" or "-" not in codes:
                self._route_cache[callsign] = ""
                self._routes_missing += 1
                continue
            route = FRECCIA.join(part.strip() for part in codes.split("-") if part.strip())
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
                    route = FRECCIA.join(part.strip() for part in text.split("-") if part.strip())
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
    def _format_field(key, plane, cfg=None):
        """Il valore di un campo, gia' formattato per il pannello.

        `cfg` porta le unita' di misura scelte. E' facoltativo perche' questa
        funzione la chiamano anche il registro e le prove, dove le unita'
        predefinite vanno benissimo.
        """
        scelte = cfg or {}
        try:
            if key == "route":
                # Il codice grezzo resta nel dato; qui si converte solo cio'
                # che finisce sul pannello, dove ci stanno pochi caratteri.
                return lookup.route(plane.get("route") or "")
            if key == "type":
                return lookup.short("aircraft", plane.get("type") or "")
            if key == "airline":
                # Non e' un campo che arriva dal servizio: sta nelle prime
                # tre lettere del nominativo.
                return lookup.airline(plane.get("flight") or "")
            if key == "reg":
                return plane.get("reg") or ""
            if key == "hex":
                return plane.get("hex") or ""
            if key == "squawk":
                return plane.get("squawk") or ""
            if key == "altitude":
                if plane.get("altitude") is None:
                    return ""
                valore, simbolo = convert("altitude", plane["altitude"],
                                          scelte.get("unit_altitude", "ft"))
                return "%d%s" % (round(valore), simbolo)
            if key == "speed":
                valore, simbolo = convert("speed", plane["speed"],
                                          scelte.get("unit_speed", "kt"))
                return "%d%s" % (round(valore), simbolo)
            if key == "track":
                return "%d°" % int(plane["track"])
            if key == "distance":
                valore, simbolo = convert("distance", plane["distance"],
                                          scelte.get("unit_distance", "km"))
                return "%.1f%s" % (valore, simbolo)
        except (TypeError, ValueError, KeyError):
            return ""
        return ""

    # -------------------------------------------------------------- disegno

    def _text_width(self, text, font):
        return ImageDraw.Draw(_SCRATCH).textbbox((0, 0), text, font=font)[2]

    def _layout(self, plane, cfg):
        """Quello che va disegnato, prima di decidere *come* disegnarlo.

        Separare il calcolo dal disegno serve perche' la fascia dei dettagli
        ha tre comportamenti possibili quando non ci sta — troncata, a pagine,
        scorrevole — e tutti e tre partono dagli stessi campi, dagli stessi
        colori e dalle stesse tre fasce.
        """
        wanted = cfg.get("fields") or ["route", "type", "altitude", "speed", "distance"]

        # La rotta prende la fascia centrale e lascia il fondo agli altri campi.
        route_line = ""
        if "route" in wanted:
            grezza = plane.get("route") or ""
            if grezza:
                route_line = lookup.route(grezza)
                if self._text_width(route_line, self._font_small) > self.width - 4:
                    # I nomi non ci stanno: meglio i codici, che ci stanno
                    # sempre, che un testo tagliato a meta'.
                    route_line = grezza

        details = []
        for key, _label in FIELD_LIST:
            if key not in wanted or (key == "route" and route_line):
                continue
            value = self._format_field(key, plane, cfg)
            if value:
                details.append(value)
        if not details and not route_line:
            details.append("%.1fkm" % plane["distance"])

        info_color = parse_color(cfg.get("info_color", "#ff8c1a"), (255, 140, 26))

        # Le tre fasce si ricavano dall'altezza, non da numeri fissi: il
        # pannello potrebbe non essere alto 64 pixel.
        bottom = self.height - max(14, int(self.height * 0.31))
        middle = 2 + max(14, int(self.height * 0.40)) + 1
        # Se le due righe si toccherebbero, la rotta sale di quel poco.
        middle = min(middle, bottom - max(9, int(self.height * 0.20)) - 1)

        return {
            "title": plane["flight"] or plane["reg"] or plane["hex"] or "SCONOSCIUTO",
            # I codici della rotta accanto all'identificativo: corti, sempre
            # della stessa lunghezza, dicono in un colpo d'occhio da dove a
            # dove. Si mostrano nella forma **IATA** anche quando il servizio
            # ha risposto in ICAO: tre lettere invece di quattro, e sono
            # quelle stampate sul biglietto.
            "codes": lookup.route((plane.get("route") or "").strip(), index=2),
            "title_color": parse_color(cfg.get("callsign_color", "#00d0ff"),
                                       (0, 208, 255)),
            "route": route_line,
            # Vuoto = segue il colore dei dettagli, cosi' chi non tocca nulla
            # non vede cambiare niente.
            "route_color": parse_color(cfg.get("route_color") or "", info_color),
            "details": details,
            "info_color": info_color,
            "middle": middle,
            "bottom": bottom,
        }

    def _base(self, layout):
        """Le due fasce che non cambiano mai: identificativo e rotta.

        L'identificativo sta a **sinistra**, non al centro, e i codici della
        rotta all'estremita' opposta, in caratteri piccoli e centrati
        verticalmente rispetto a lui. Il numero di volo ha lunghezza
        variabile: centrarlo lo faceva ballare da un aereo all'altro, mentre
        ancorato al bordo resta fermo e lo sguardo lo trova sempre nello
        stesso punto.
        """
        image = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(image)

        def misura(text, font):
            box = draw.textbbox((0, 0), text, font=font)
            return box[2] - box[0], box[3] - box[1], box[0], box[1]

        def centrato(text, font, y, color):
            w, _h, off_x, _off_y = misura(text, font)
            draw.text(((self.width - w) // 2 - off_x, y), text, font=font, fill=color)

        titolo = layout["title"]
        w_titolo, h_titolo, off_x, off_y = misura(titolo, self._font_big)
        draw.text((MARGINE - off_x, 2), titolo, font=self._font_big,
                  fill=layout["title_color"])

        codici = layout.get("codes") or ""
        if codici:
            w_cod, h_cod, off_cx, off_cy = misura(codici, self._font_small)
            x_codici = self.width - MARGINE - w_cod - off_cx
            if x_codici >= MARGINE + w_titolo + SPAZIO:
                # Centrati sull'altezza dell'identificativo: due corpi diversi
                # sulla stessa riga si leggono come una cosa sola quando
                # condividono l'asse, non la base.
                centro = 2 + off_y + h_titolo / 2.0
                y_codici = int(round(centro - h_cod / 2.0)) - off_cy
                draw.text((x_codici, max(0, y_codici)), codici,
                          font=self._font_small, fill=layout["route_color"])

        if layout["route"]:
            centrato(layout["route"], self._font_small,
                     layout["middle"], layout["route_color"])
        return image

    def _troncata(self, details):
        """La riga piu' lunga che ci sta, buttando via campi dal fondo.

        E' il comportamento storico: semplice, ma qualche informazione si
        perde senza dirlo. Resta disponibile per chi preferisce un pannello
        immobile.
        """
        details = list(details)
        line = "  ".join(details)
        while (self._text_width(line, self._font_small) > self.width - 4
               and len(details) > 1):
            details.pop(-2 if len(details) > 2 else -1)
            line = "  ".join(details)
        return line

    def _pagine(self, details):
        """Divide i dettagli in gruppi che ci stanno per intero.

        Nessun campo viene perso: quelli che non entrano nella prima pagina
        vanno nella seconda. Un campo cosi' lungo da non starci da solo resta
        comunque una pagina sua, tagliata dal bordo: e' il caso limite, e
        toglierlo del tutto sarebbe peggio.
        """
        pages = []
        current = []
        for value in details:
            prova = current + [value]
            if current and self._text_width("  ".join(prova),
                                            self._font_small) > self.width - 4:
                pages.append(current)
                current = [value]
            else:
                current = prova
        if current:
            pages.append(current)
        return pages or [[]]

    def _render_details(self, layout, line):
        image = self._base(layout)
        if not line:
            return image
        draw = ImageDraw.Draw(image)
        box = draw.textbbox((0, 0), line, font=self._font_small)
        draw.text(((self.width - (box[2] - box[0])) // 2 - box[0],
                   layout["bottom"]), line,
                  font=self._font_small, fill=layout["info_color"])
        return image

    def _striscia(self, layout, line):
        """La riga dei dettagli su tela propria, per farla scorrere.

        Alta quanto la sola fascia bassa, non quanto il pannello: cosi'
        scorrendo passa sotto identificativo e rotta senza cancellarli.
        """
        larghezza = max(1, self._text_width(line, self._font_small))
        altezza = max(1, self.height - layout["bottom"])
        strip = Image.new("RGB", (larghezza, altezza), (0, 0, 0))
        draw = ImageDraw.Draw(strip)
        box = draw.textbbox((0, 0), line, font=self._font_small)
        draw.text((-box[0], 0), line,
                  font=self._font_small, fill=layout["info_color"])
        return strip

    def _render(self, plane, cfg):
        """Tre fasce: identificativo, rotta, dettagli.

        Fra il numero di volo in alto e la riga dei dettagli in basso restava
        una banda vuota di una ventina di pixel. Metterci la rotta non serve
        solo a riempirla: le toglie di dosso la concorrenza per la larghezza.
        Su una riga sola, "Orio al Serio->Stansted" mangiava lo spazio di
        modello e quota, che venivano scartati per far stare tutto.

        Questa e' l'immagine singola: la usano l'anteprima della web UI e i
        casi in cui i dettagli ci stanno tutti. Quando non ci stanno, la
        scelta fra troncare, impaginare e far scorrere la prende `_mostra`.
        """
        layout = self._layout(plane, cfg)
        return self._render_details(layout, self._troncata(layout["details"]))
