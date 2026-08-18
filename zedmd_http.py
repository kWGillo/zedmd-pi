"""Server HTTP minimo per il protocollo ZeDMD (porta 80).

Perché non usare Flask anche qui: il client di libzedmd legge la risposta
con una sola recv() e si ferma appena riceve meno di 1024 byte. Se header e
corpo arrivano in due pacchetti TCP distinti — cosa che Flask/Werkzeug fa
regolarmente — il client vede solo gli header e interpreta il corpo come
vuoto: tutti i campi dell'handshake restano a zero, non riconosce il
trasporto TCP e ripiega su UDP.

Questo server costruisce header e corpo in un unico buffer e li invia con
una sola sendall(), garantendo la lettura in un colpo solo.

Ogni percorso non riconosciuto viene rediretto alla web UI.
"""

import socket
import threading


class ZeDMDHttpServer:
    def __init__(self, runtime, port=80, ui_port=8080):
        self.runtime = runtime
        self.port = port
        self.ui_port = ui_port
        self._sock = None
        self._running = False
        self._thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._serve, name="zedmd-http", daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    # ------------------------------------------------------------------

    def _serve(self):
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind(("0.0.0.0", self.port))
            self._sock.listen(8)
            self._sock.settimeout(1.0)
        except OSError as exc:
            print("[zedmd-http] impossibile aprire la porta %d: %s" % (self.port, exc))
            self._running = False
            return

        print("[zedmd-http] handshake in ascolto su TCP %d" % self.port)
        while self._running:
            try:
                client, addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle, args=(client, addr), daemon=True).start()

    def _handle(self, client, addr):
        try:
            client.settimeout(5.0)
            request = b""
            while b"\r\n\r\n" not in request and len(request) < 8192:
                chunk = client.recv(2048)
                if not chunk:
                    break
                request += chunk
            if not request:
                return

            line = request.split(b"\r\n", 1)[0].decode("latin-1")
            parts = line.split()
            path = parts[1] if len(parts) >= 2 else "/"
            if "?" in path:
                path = path.split("?", 1)[0]

            body = self._route(path)
            if body is None:
                response = self._redirect(addr)
            else:
                response = self._ok(body)

            # Una sola scrittura: header e corpo nello stesso segmento TCP.
            client.sendall(response)
        except OSError:
            pass
        finally:
            try:
                client.close()
            except OSError:
                pass

    # ------------------------------------------------------------------

    def _route(self, path):
        cfg = self.runtime.cfg
        zedmd = self.runtime.zedmd

        if path == "/handshake":
            return zedmd.handshake_string()
        if path == "/get_width":
            return str(self.runtime.display.width)
        if path == "/get_height":
            return str(self.runtime.display.height)
        if path == "/get_version":
            return str(cfg["zedmd"]["firmware_version"])
        if path == "/get_s3":
            return "1"
        if path == "/get_protocol":
            return str(cfg["zedmd"]["transport"])
        if path == "/get_port":
            return str(cfg["zedmd"]["stream_port"])
        if path == "/get_udp_delay":
            return "5"
        if path == "/get_brightness":
            return str(zedmd._brightness_0_15())
        if path == "/get_rgb_order":
            return "0"
        return None

    def _ok(self, body):
        payload = body.encode("utf-8")
        head = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: %d\r\n"
            "Connection: close\r\n"
            "\r\n" % len(payload)
        )
        return head.encode("latin-1") + payload

    def _redirect(self, addr):
        host = self._own_ip(addr)
        location = "http://%s:%d/" % (host, self.ui_port)
        body = ("Interfaccia web su %s\n" % location).encode("utf-8")
        head = (
            "HTTP/1.1 302 Found\r\n"
            "Location: %s\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n"
            "Content-Length: %d\r\n"
            "Connection: close\r\n"
            "\r\n" % (location, len(body))
        )
        return head.encode("latin-1") + body

    def _own_ip(self, addr):
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            probe.connect((addr[0], 9))
            ip = probe.getsockname()[0]
            probe.close()
            return ip
        except OSError:
            return socket.gethostname()
