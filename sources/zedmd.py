"""Ricevitore ZeDMD-WiFi.

Reimplementa il lato dispositivo del protocollo di libzedmd (PPUC), cosi'
che qualsiasi client ZeDMD (Batocera, dmdserver, dmd-extensions, VPX)
possa inviare frame a questo Raspberry Pi credendo di parlare con un ZeDMD.

Protocollo, dal sorgente di libzedmd:

  Scoperta e configurazione : HTTP sulla porta 80
      GET /handshake  -> 22 campi separati da '|'
      GET /get_width, /get_height, /get_version, /get_s3,
          /get_protocol, /get_port, /get_udp_delay  (fallback)

  Stream dei frame : TCP (o UDP) sulla porta 3333
      payload = b"FRAME" + blocchi
      blocco  = b"ZeDMD" + cmd(1) + size_hi(1) + size_lo(1) + compresso(1) + dati

  I dati compressi usano deflate/zlib.

  Comandi rilevanti:
      0x04 RGB888ZonesStream   0x05 RGB565ZonesStream
      0x06 RenderFrame         0x07 RGB888Stream
      0x08 RGB565Stream        0x0a ClearScreen
      0x0b KeepAlive           0x16 Brightness      0x17 RGBOrder

  Zone: griglia fissa 16 x 8 = 128 zone.
        larghezza zona = width/16, altezza zona = height/8.
        Ogni zona: 1 byte indice + pixel. Indice >= 128 significa
        "zona numero indice-128 completamente nera", senza pixel a seguire.

Dichiarando TCP nell'handshake evitiamo del tutto la frammentazione UDP:
il flusso arriva ordinato e completo.
"""

import socket
import threading
import time
import zlib

import numpy as np
from PIL import Image

from .base import Source

FRAME_MAGIC = b"FRAME"
BLOCK_MAGIC = b"ZeDMD"

CMD_RGB888_ZONES = 0x04
CMD_RGB565_ZONES = 0x05
CMD_RENDER_FRAME = 0x06
CMD_RGB888_STREAM = 0x07
CMD_RGB565_STREAM = 0x08
CMD_CLEAR_SCREEN = 0x0A
CMD_KEEP_ALIVE = 0x0B
CMD_LED_TEST = 0x10
CMD_BRIGHTNESS = 0x16
CMD_RGB_ORDER = 0x17

ZONES_PER_ROW = 16
ZONE_ROWS = 8

# Quanto si aspetta un RenderFrame prima di mostrare comunque le zone gia'
# scritte. Le zone sono aggiornamenti parziali: il protocollo prevede che sia
# RenderFrame a dire "adesso e' completo", e pubblicare subito rischierebbe di
# far vedere mezza immagine. Ma se quel comando non arriva — e non sempre
# arriva — il pannello resta indietro finche' non cambia qualcos'altro.
# Un ottavo di secondo non si nota durante il gioco, dove RenderFrame arriva a
# ogni fotogramma e questa rete di sicurezza non scatta mai.
PENDING_FLUSH = 0.12


def rgb565_to_rgb888(raw):
    """Converte un blocco di pixel RGB565 little-endian in un array (n, 3)."""
    values = np.frombuffer(raw, dtype="<u2")
    red = ((values >> 8) & 0xF8).astype(np.uint8)
    green = ((values >> 3) & 0xFC).astype(np.uint8)
    blue = ((values << 3) & 0xF8).astype(np.uint8)
    return np.stack((red, green, blue), axis=-1)


class ZeDMDSource(Source):
    name = "zedmd"
    label = "ZeDMD"
    priority = 100

    def __init__(self, cfg, width, height, on_brightness=None):
        super().__init__(cfg, width, height)
        self.on_brightness = on_brightness

        self.zone_width = max(1, width // ZONES_PER_ROW)
        self.zone_height = max(1, height // ZONE_ROWS)

        self._buffer = np.zeros((height, width, 3), dtype=np.uint8)
        self._lock = threading.Lock()
        self._dirty = True

        self._server = None
        self._udp_server = None
        self._thread = None
        self._udp_thread = None
        self._udp_pending = bytearray()
        self._running = False
        self._client_addr = None
        self._last_activity = 0.0
        self._frames = 0
        self._transport = None
        self._azzera_contatti()

    # ------------------------------------------------------------------ ciclo di vita

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._serve, name="zedmd-tcp", daemon=True)
        self._thread.start()
        # L'UDP è la rete di sicurezza: se un client ignora il trasporto TCP
        # dichiarato nell'handshake, i frame arrivano comunque.
        self._udp_thread = threading.Thread(target=self._serve_udp, name="zedmd-udp", daemon=True)
        self._udp_thread.start()

    def stop(self):
        self._running = False
        for sock in (self._server, self._udp_server):
            if sock:
                try:
                    sock.close()
                except OSError:
                    pass
        self._server = None
        self._udp_server = None
        self._client_addr = None
        self._transport = None
        self._last_activity = 0.0
        self._azzera_contatti()

    def _azzera_contatti(self):
        """Gli istanti che raccontano il rapporto con il client.

        Stanno insieme in un metodo perche' vanno azzerati negli stessi due
        momenti — alla costruzione e allo spegnimento — e tenerli allineati a
        mano e' esattamente il genere di cosa che si dimentica: nella 1.12.1
        li avevo messi solo nello spegnimento, e la pagina dei servizi andava
        in errore finche' non arrivava il primo handshake.
        """
        # Il colloquio HTTP che precede il flusso. Tenerne traccia separa due
        # guasti che da fuori si somigliano: "il client non ha mai parlato con
        # il Pi" e "si sono parlati, ma il flusso non e' partito". Senza questo
        # dato restava solo "nessun client", che li confonde.
        self._last_handshake = 0.0
        self._handshake_addr = None
        self._handshakes = 0
        self._connected_at = 0.0
        # Ultimo *fotogramma* ricevuto, che non e' l'ultimo byte: il protocollo
        # manda keep-alive ogni 100 ms, quindi un client collegato e fermo
        # sembra vivissimo se si guarda il traffico.
        self._last_frame = 0.0
        # Zone scritte in attesa del RenderFrame che le renda visibili.
        self._pending_since = 0.0
        self._flushed = 0
        # Ritmo. Serve a rispondere all'unica domanda che conta quando
        # l'immagine arriva in ritardo: se il Pi riceve poco, il collo di
        # bottiglia e' a monte — rete o client — e ottimizzare qui non
        # servirebbe a niente. `_shown` conta i fotogrammi finiti davvero sul
        # pannello: se e' molto minore di quelli ricevuti, il limite e' il
        # ciclo di disegno, non il flusso.
        self._shown = 0
        self._fps_value = 0.0
        self._fps_count = 0
        self._fps_since = 0.0

    # ------------------------------------------------------------------ arbitro

    def active(self):
        """Chi ha diritto al pannello, fra ZeDMD e le sorgenti locali.

        La regola e' in due parti, e ciascuna nasce da un guasto vero.

        **Client collegato.** Su Batocera dmdserver e' un servizio permanente:
        si aggancia all'avvio e resta li' anche a menu fermo, mandando
        keep-alive ogni 100 ms. Se la sola connessione bastasse, il pannello
        gli resterebbe assegnato per sempre — nero, perche' prima che
        qualcuno selezioni qualcosa non manda niente — e orologio, radar e
        banner non ricomparirebbero mai. Quindi un client collegato che non ha
        **mai** mandato un fotogramma tiene il pannello solo per la finestra
        di cortesia, poi lo cede.

        Ma una volta che ha mandato qualcosa, il pannello e' suo finche' resta
        collegato. Sul cabinato l'immagine del tavolo selezionato puo' restare
        ferma per minuti: farla sparire dopo un minuto perche' "non arriva
        niente di nuovo" sarebbe un guasto, non un risparmio. E' l'errore che
        ho commesso nella 1.12.2 legando tutto all'ultimo fotogramma.

        **Client scollegato.** Qui vale la finestra di cortesia sull'ultimo
        fotogramma: copre le riconnessioni brevi senza far lampeggiare
        l'orologio fra una partita e l'altra.
        """
        if not self._running:
            return False
        grace = self.cfg["zedmd"]["grace_seconds"]
        if self._client_addr is not None:
            if self._frames:
                return True
            return (time.time() - self._connected_at) < grace
        return (time.time() - self._last_frame) < grace

    def cede_a_riempitivo(self):
        """Batocera e' collegato ma non manda niente di nuovo da un pezzo.

        La 3.0 aveva un difetto che si vedeva solo su un cabinato vero: Doom
        in attract mode non compariva **mai**. La ragione non era Doom ma
        questa sorgente — finche' Batocera e' collegato e ha mandato almeno un
        fotogramma il pannello e' suo, e su un cabinato acceso quella
        condizione e' sempre vera. La funzione era descritta come "quando
        nessuno tocca niente Doom gioca da solo" e nella pratica non esisteva.

        Il rimedio non e' alzare la priorita' di Doom: cosi' vincerebbe anche
        durante una partita, che e' molto peggio. E non e' nemmeno tornare
        alla regola della 1.12.2, che faceva sparire l'immagine del tavolo
        dopo un minuto per lasciare il posto all'**orologio** — quello era un
        guasto, ed e' stato corretto apposta.

        La distinzione giusta e' fra *avere diritto al pannello* e *avere
        qualcosa da dire*. L'immagine del tavolo selezionato resta ferma per
        minuti mentre si scorre il menu: passato quel tempo, un riempitivo che
        si muove vale piu' di un fermo immagine, e al primo fotogramma nuovo
        il pannello torna qui immediatamente. Zero disattiva la deroga.
        """
        if not self._running or self._client_addr is None or not self._frames:
            return False
        try:
            limite = int(self.cfg["zedmd"].get("idle_seconds", 60))
        except (TypeError, ValueError):
            limite = 60
        if limite <= 0:
            return False
        return (time.time() - self._last_frame) > limite

    def fermo_da(self):
        """Secondi dall'ultimo fotogramma ricevuto, per la web UI."""
        if not self._frames:
            return 0
        return max(0, int(time.time() - self._last_frame))

    def frame(self):
        with self._lock:
            if not self._dirty and not self._scaduta_l_attesa():
                return None
            self._dirty = False
            self._pending_since = 0.0
            self._shown += 1
            # fromarray copia già: una seconda copia sarebbe sprecata.
            return Image.fromarray(self._buffer, "RGB")

    def _nota_ritmo(self):
        """Un fotogramma completo in piu'. Va chiamata con il lock preso."""
        now = time.time()
        self._frames += 1
        self._last_frame = now
        self._fps_count += 1
        if not self._fps_since:
            self._fps_since = now
            return
        span = now - self._fps_since
        if span >= 3.0:
            self._fps_value = self._fps_count / span
            self._fps_count = 0
            self._fps_since = now

    def _scaduta_l_attesa(self):
        """Vero se ci sono zone scritte e il RenderFrame non e' mai arrivato.

        Va chiamata con il lock gia' preso. Il conteggio separato serve a
        distinguere, guardando lo stato, un client che segue il protocollo da
        uno che si affida al dispositivo per decidere quando disegnare.
        """
        if not self._pending_since:
            return False
        if (time.time() - self._pending_since) < PENDING_FLUSH:
            return False
        self._flushed += 1
        self._nota_ritmo()
        if self._flushed == 1:
            print("[zedmd] zone senza RenderFrame: pubblicate dopo %d ms"
                  % int(PENDING_FLUSH * 1000))
        return True

    def status(self, lang=None):
        if not self._running:
            return self.t("status.disabled", lang)
        if self._client_addr:
            if not self._frames:
                # Collegato ma muto: e' lo stato di dmdserver a menu fermo, e
                # senza dirlo si vede solo un pannello nero.
                return self.t("status.zedmd.connected.silent", lang,
                              addr=self._client_addr[0],
                              transport=self._transport or "TCP",
                              since=int(time.time() - self._connected_at))
            return self.t("status.zedmd.connected", lang,
                          addr=self._client_addr[0],
                          transport=self._transport or "TCP",
                          frames=self._frames,
                          fps=self._fps_value,
                          shown=self._shown,
                          idle=int(time.time() - self._last_frame))
        if self._last_activity:
            return self.t("status.zedmd.idle", lang,
                          idle=int(time.time() - self._last_activity),
                          frames=self._frames)
        if self._last_handshake:
            return self.t("status.zedmd.handshake", lang,
                          addr=self._handshake_addr or "?",
                          ago=int(time.time() - self._last_handshake),
                          count=self._handshakes,
                          port=self.cfg["zedmd"]["stream_port"])
        return self.t("status.zedmd.listening", lang,
                      port=self.cfg["zedmd"]["stream_port"])

    def note_handshake(self, addr, path):
        """Registra una richiesta HTTP del client, per poterla raccontare."""
        self._last_handshake = time.time()
        self._handshake_addr = addr
        self._handshakes += 1

    # ------------------------------------------------------------------ handshake HTTP

    def handshake_string(self):
        """I 22 campi che libzedmd si aspetta da GET /handshake."""
        zc = self.cfg["zedmd"]
        fields = [
            self.width,                        # 0  larghezza
            self.height,                       # 1  altezza
            zc["firmware_version"],            # 2  versione firmware
            1,                                 # 3  flag ESP32-S3
            zc["transport"],                   # 4  TCP oppure UDP
            zc["stream_port"],                 # 5  porta di streaming
            5,                                 # 6  ritardo UDP (ms)
            1920,                              # 7  write at once (solo seriale)
            self._brightness_0_15(),           # 8  luminosita' 0-15
            0,                                 # 9  ordine RGB
            0,                                 # 10 clock phase pannello
            2,                                 # 11 driver pannello
            0,                                 # 12 i2s speed
            2,                                 # 13 latch blanking
            30,                                # 14 refresh minimo
            0,                                 # 15 offset verticale
            zc["device_name"],                 # 16 SSID
            0,                                 # 17 half
            0,                                 # 18 id
            80,                                # 19 potenza WiFi
            1,                                 # 20 device type (1 = ESP32-S3)
            0,                                 # 21 line decoder
        ]
        return "|".join(str(f) for f in fields)

    def _brightness_0_15(self):
        percent = self.cfg["display"]["brightness"]
        return max(0, min(15, round(percent * 15 / 100)))

    # ------------------------------------------------------------------ server TCP

    def _serve(self):
        port = self.cfg["zedmd"]["stream_port"]
        try:
            self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server.bind(("0.0.0.0", port))
            self._server.listen(1)
            self._server.settimeout(1.0)
        except OSError as exc:
            print("[zedmd] impossibile aprire la porta %d: %s" % (port, exc))
            self._running = False
            return

        print("[zedmd] in ascolto su TCP %d" % port)
        while self._running:
            try:
                client, addr = self._server.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            print("[zedmd] client connesso via TCP: %s" % (addr,))
            self._client_addr = addr
            self._connected_at = time.time()
            self._transport = "TCP"
            self._last_activity = time.time()
            try:
                client.settimeout(5.0)
                client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                try:
                    client.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
                    client.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    for opt, value in (("TCP_KEEPIDLE", 5), ("TCP_KEEPINTVL", 2), ("TCP_KEEPCNT", 3)):
                        if hasattr(socket, opt):
                            client.setsockopt(socket.IPPROTO_TCP, getattr(socket, opt), value)
                except OSError:
                    pass
                self._handle_client(client)
            except OSError:
                pass
            finally:
                try:
                    client.close()
                except OSError:
                    pass
                self._client_addr = None
                print("[zedmd] client disconnesso")

    def _serve_udp(self):
        port = self.cfg["zedmd"]["stream_port"]
        try:
            self._udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._udp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._udp_server.bind(("0.0.0.0", port))
            self._udp_server.settimeout(1.0)
        except OSError as exc:
            print("[zedmd] UDP %d non disponibile: %s" % (port, exc))
            return

        announced = False
        while self._running:
            try:
                data, addr = self._udp_server.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            if not data:
                continue
            if not announced:
                print("[zedmd] frame in arrivo via UDP da %s" % (addr,))
                announced = True
                self._connected_at = time.time()
            self._transport = "UDP"
            self._last_activity = time.time()
            self._udp_pending.extend(data)
            self._consume(self._udp_pending)

    def _handle_client(self, client):
        pending = bytearray()
        dead_after = self.cfg["zedmd"].get("client_timeout", 10)
        client.settimeout(1.0)
        last_data = time.time()
        while self._running:
            try:
                chunk = client.recv(262144)
            except socket.timeout:
                # Il protocollo invia keep-alive ogni 100 ms su TCP: un silenzio
                # prolungato vuol dire client sparito, tipicamente spento di colpo
                # senza chiudere la connessione.
                if time.time() - last_data > dead_after:
                    print("[zedmd] nessun dato da %d s: connessione considerata caduta" % dead_after)
                    return
                continue
            if not chunk:
                return
            last_data = time.time()
            pending.extend(chunk)
            self._last_activity = time.time()
            self._consume(pending)

    # ------------------------------------------------------------------ parser

    def _consume(self, pending):
        """Estrae tutti i blocchi completi presenti nel buffer."""
        while True:
            if pending.startswith(FRAME_MAGIC):
                del pending[:len(FRAME_MAGIC)]
                continue

            if pending.startswith(BLOCK_MAGIC):
                if len(pending) < 9:
                    return
                command = pending[5]
                size = (pending[6] << 8) | pending[7]
                compressed = pending[8]
                if len(pending) < 9 + size:
                    return
                payload = bytes(pending[9:9 + size])
                del pending[:9 + size]
                if compressed and payload:
                    try:
                        payload = zlib.decompress(payload)
                    except zlib.error:
                        continue
                self._dispatch(command, payload)
                continue

            # Risincronizzazione: cerca la prossima intestazione valida.
            if len(pending) < 5:
                return
            next_frame = pending.find(FRAME_MAGIC, 1)
            next_block = pending.find(BLOCK_MAGIC, 1)
            candidates = [p for p in (next_frame, next_block) if p != -1]
            if not candidates:
                del pending[:len(pending) - 4]
                return
            del pending[:min(candidates)]

    def _dispatch(self, command, payload):
        if command == CMD_KEEP_ALIVE:
            return

        if command == CMD_RENDER_FRAME:
            with self._lock:
                self._dirty = True
                self._pending_since = 0.0
                self._nota_ritmo()
            return

        if command == CMD_CLEAR_SCREEN:
            with self._lock:
                self._buffer[:] = 0
                self._dirty = True
                self._pending_since = 0.0
            return

        if command == CMD_BRIGHTNESS and payload:
            percent = max(0, min(100, round(payload[0] * 100 / 15)))
            if self.on_brightness:
                self.on_brightness(percent)
            return

        if command == CMD_LED_TEST:
            self._led_test()
            return

        if command == CMD_RGB565_ZONES:
            self._write_zones(payload, bytes_per_pixel=2)
            return

        if command == CMD_RGB888_ZONES:
            self._write_zones(payload, bytes_per_pixel=3)
            return

        if command == CMD_RGB565_STREAM:
            self._write_full(payload, bytes_per_pixel=2)
            return

        if command == CMD_RGB888_STREAM:
            self._write_full(payload, bytes_per_pixel=3)
            return

        # 0x17 RGBOrder e altri comandi di configurazione: ignorati.

    # ------------------------------------------------------------------ scrittura pixel

    def _write_zones(self, payload, bytes_per_pixel):
        zw = self.zone_width
        zh = self.zone_height
        zone_bytes = zw * zh * bytes_per_pixel
        pos = 0
        length = len(payload)

        with self._lock:
            scritto = False
            while pos < length:
                index = payload[pos]
                pos += 1

                if index >= 128:
                    zone = index - 128
                    x0, y0 = self._zone_origin(zone)
                    self._buffer[y0:y0 + zh, x0:x0 + zw] = 0
                    scritto = True
                    continue

                if pos + zone_bytes > length:
                    break
                raw = payload[pos:pos + zone_bytes]
                pos += zone_bytes

                if bytes_per_pixel == 2:
                    pixels = rgb565_to_rgb888(raw).reshape(zh, zw, 3)
                else:
                    pixels = np.frombuffer(raw, dtype=np.uint8).reshape(zh, zw, 3)

                x0, y0 = self._zone_origin(index)
                self._buffer[y0:y0 + zh, x0:x0 + zw] = pixels
                scritto = True

            if scritto:
                # Contenuto arrivato: vale come segno di vita anche se il
                # RenderFrame non si vedra' mai, altrimenti dopo un minuto
                # l'arbitro toglierebbe il pannello a una sorgente che sta
                # trasmettendo.
                self._last_frame = time.time()
                if not self._pending_since:
                    self._pending_since = self._last_frame

    def _zone_origin(self, index):
        return (index % ZONES_PER_ROW) * self.zone_width, (index // ZONES_PER_ROW) * self.zone_height

    def _write_full(self, payload, bytes_per_pixel):
        expected = self.width * self.height * bytes_per_pixel
        if len(payload) < expected:
            return
        raw = payload[:expected]
        if bytes_per_pixel == 2:
            pixels = rgb565_to_rgb888(raw).reshape(self.height, self.width, 3)
        else:
            pixels = np.frombuffer(raw, dtype=np.uint8).reshape(self.height, self.width, 3)
        with self._lock:
            self._buffer[:] = pixels
            self._dirty = True
            self._pending_since = 0.0
            self._nota_ritmo()

    def _led_test(self):
        with self._lock:
            third = max(1, self.width // 3)
            self._buffer[:] = 0
            self._buffer[:, 0:third] = (255, 0, 0)
            self._buffer[:, third:2 * third] = (0, 255, 0)
            self._buffer[:, 2 * third:] = (0, 0, 255)
            self._dirty = True
