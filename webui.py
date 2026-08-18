"""Interfaccia web del DMD.

Gira sulla porta 8080. La porta 80 e' riservata all'handshake ZeDMD,
servito da `zedmd_http.py`, che redirige qui ogni altro percorso.
"""

import os
import socket
import subprocess
import time

from flask import (Flask, jsonify, redirect, render_template, request,
                   url_for)
from werkzeug.utils import secure_filename

import dmdconf
from sources import LANGUAGES, is_supported, scan_media, have_ffmpeg
from version import __version__

COMMON_TIMEZONES = [
    "Europe/Rome", "Europe/London", "Europe/Paris", "Europe/Berlin",
    "Europe/Madrid", "Europe/Lisbon", "Europe/Amsterdam", "Europe/Zurich",
    "Europe/Vienna", "Europe/Athens", "UTC", "America/New_York",
    "America/Los_Angeles", "Asia/Tokyo", "Australia/Sydney",
]


def all_timezones():
    try:
        from zoneinfo import available_timezones
        return sorted(available_timezones())
    except Exception:
        return COMMON_TIMEZONES


def local_ips():
    found = []
    try:
        out = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=5)
        for token in out.stdout.split():
            if ":" not in token and not token.startswith("127."):
                found.append(token)
    except Exception:
        pass
    if not found:
        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            probe.connect(("8.8.8.8", 80))
            found.append(probe.getsockname()[0])
            probe.close()
        except Exception:
            pass
    return found


def run_cmd(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=15)
        return result.returncode == 0, (result.stdout + result.stderr).strip()
    except Exception as exc:
        return False, str(exc)


def apply_timezone(cfg):
    time_cfg = cfg["time"]
    if time_cfg["dst_auto"]:
        target = time_cfg["timezone"]
    else:
        # Convenzione POSIX: il segno di Etc/GMT e' invertito.
        target = "Etc/GMT%+d" % (-int(time_cfg["utc_offset"]))
    ok, message = run_cmd(["timedatectl", "set-timezone", target])
    if ok:
        os.environ["TZ"] = target
        time.tzset()
    return ok, message


def apply_ntp(cfg):
    server = cfg["time"]["ntp_server"].strip()
    if not server:
        return False, "server NTP vuoto"
    try:
        with open("/etc/systemd/timesyncd.conf", "w") as handle:
            handle.write("[Time]\nNTP=%s\nFallbackNTP=pool.ntp.org\n" % server)
    except OSError as exc:
        return False, str(exc)
    run_cmd(["timedatectl", "set-ntp", "true"])
    return run_cmd(["systemctl", "restart", "systemd-timesyncd"])


def ntp_status():
    ok, out = run_cmd(["timedatectl", "show",
                       "-p", "NTP", "-p", "NTPSynchronized", "-p", "Timezone"])
    info = {}
    if ok:
        for line in out.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                info[key] = value
    return info


def create_app(runtime):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 512 * 1024 * 1024
    cfg = runtime.cfg

    @app.context_processor
    def inject_globals():
        return {"version": __version__}

    # ------------------------------------------------------------ protocollo ZeDMD
    # Serviti anche qui per poterli provare con curl sulla porta 8080;
    # il client reale usa il server dedicato sulla porta 80.

    def plain(body):
        return app.response_class(str(body), mimetype="text/plain")

    @app.route("/handshake")
    def zedmd_handshake():
        return plain(runtime.zedmd.handshake_string())

    @app.route("/get_width")
    def zedmd_width():
        return plain(runtime.display.width)

    @app.route("/get_height")
    def zedmd_height():
        return plain(runtime.display.height)

    @app.route("/get_version")
    def zedmd_version():
        return plain(cfg["zedmd"]["firmware_version"])

    @app.route("/get_protocol")
    def zedmd_protocol():
        return plain(cfg["zedmd"]["transport"])

    # ------------------------------------------------------------ pagine

    @app.route("/")
    def page_settings():
        return render_template(
            "settings.html", cfg=cfg, ips=local_ips(),
            hostname=socket.gethostname(), timezones=all_timezones(),
            ntp=ntp_status(), now=time.strftime("%d/%m/%Y %H:%M:%S"),
            sleeping=runtime.sleeping, night=runtime.night, page="settings")

    @app.route("/clock")
    def page_clock():
        return render_template("clock.html", cfg=cfg, languages=LANGUAGES, page="clock")

    @app.route("/media")
    def page_media():
        media_dir = cfg["mediaplayer"]["media_dir"]
        files = scan_media(media_dir)
        listing = []
        for path in files[:400]:
            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0
            listing.append({
                "rel": os.path.relpath(path, media_dir),
                "size": "%.1f MB" % (size / 1048576) if size >= 1048576
                        else "%d kB" % max(1, size // 1024),
            })
        return render_template(
            "media.html", cfg=cfg, files=listing, total=len(files),
            media_dir=media_dir, ffmpeg=have_ffmpeg(),
            status=runtime.media.status(), page="media")

    @app.route("/services")
    def page_services():
        services = [
            {"key": "zedmd", "label": "ZeDMD", "ready": True,
             "desc": "Riceve i frame DMD via rete da Batocera, dmdserver o VPX.",
             "status": runtime.zedmd.status()},
            {"key": "mediaplayer", "label": "Media Player", "ready": True,
             "desc": "Foto e video a rotazione dalla libreria, a intervalli casuali.",
             "status": runtime.media.status()},
            {"key": "clock", "label": "Clock", "ready": True,
             "desc": "Orologio e data, mostrati quando nessun altro servizio è attivo.",
             "status": runtime.clock.status()},
            {"key": "status_player", "label": "Status Player", "ready": False,
             "desc": "Attività e punteggi RetroAchievements, propri e degli amici.",
             "status": "non ancora implementato"},
            {"key": "air_radar", "label": "Air Radar", "ready": False,
             "desc": "Aerei in transito entro un raggio configurabile dalle coordinate GPS.",
             "status": "non ancora implementato"},
        ]
        current = runtime.arbiter.current
        return render_template(
            "services.html", cfg=cfg, services=services,
            current=current.label if current else "nessuna",
            sleeping=runtime.sleeping, night=runtime.night, page="services")

    # ------------------------------------------------------------ API

    @app.route("/api/brightness", methods=["POST"])
    def api_brightness():
        value = runtime.set_brightness(int(request.form.get("value", 50)))
        return jsonify(ok=True, value=value)

    @app.route("/api/display", methods=["POST"])
    def api_display():
        display = cfg["display"]
        display["night_enabled"] = request.form.get("night_enabled") == "on"
        display["night_start"] = request.form.get("night_start", "22:00")
        display["night_end"] = request.form.get("night_end", "07:00")
        display["sleep_enabled"] = request.form.get("sleep_enabled") == "on"
        display["sleep_start"] = request.form.get("sleep_start", "01:00")
        display["sleep_end"] = request.form.get("sleep_end", "06:00")
        display["sleep_wake_on_zedmd"] = request.form.get("sleep_wake_on_zedmd") == "on"
        try:
            display["night_brightness"] = max(0, min(100, int(request.form.get("night_brightness", 15))))
        except ValueError:
            display["night_brightness"] = 15
        dmdconf.save()
        runtime._applied_brightness = None
        return redirect(url_for("page_settings"))

    @app.route("/api/clock", methods=["POST"])
    def api_clock():
        clock = cfg["clock"]
        clock["time_color"] = request.form.get("time_color", "#ff8c1a")
        clock["date_color"] = request.form.get("date_color", "#00a0d0")
        clock["format_24h"] = request.form.get("format_24h") == "on"
        clock["show_date"] = request.form.get("show_date") == "on"
        clock["blink_colon"] = request.form.get("blink_colon") == "on"
        language = request.form.get("language", "it")
        clock["language"] = language if language in dict(LANGUAGES) else "it"
        dmdconf.save()
        runtime.clock.invalidate()
        return redirect(url_for("page_clock"))

    @app.route("/api/media", methods=["POST"])
    def api_media():
        media = cfg["mediaplayer"]
        for key, low, high, default in (("min_interval", 3, 3600, 20),
                                        ("max_interval", 3, 3600, 30),
                                        ("image_duration", 1, 120, 5),
                                        ("video_duration", 1, 300, 8),
                                        ("video_fps", 5, 60, 20)):
            try:
                media[key] = max(low, min(high, int(request.form.get(key, default))))
            except ValueError:
                media[key] = default
        if media["max_interval"] < media["min_interval"]:
            media["max_interval"] = media["min_interval"]
        mode = request.form.get("scale_mode", "fit")
        media["scale_mode"] = mode if mode in ("fit", "fill") else "fit"
        media["pixel_art"] = request.form.get("pixel_art") == "on"
        dmdconf.save()
        return redirect(url_for("page_media"))

    @app.route("/api/media/upload", methods=["POST"])
    def api_media_upload():
        media_dir = cfg["mediaplayer"]["media_dir"]
        os.makedirs(media_dir, exist_ok=True)
        for storage in request.files.getlist("files"):
            if not storage or not storage.filename:
                continue
            name = secure_filename(storage.filename)
            if not name or not is_supported(name):
                continue
            storage.save(os.path.join(media_dir, name))
        return redirect(url_for("page_media"))

    @app.route("/api/media/delete", methods=["POST"])
    def api_media_delete():
        media_dir = os.path.realpath(cfg["mediaplayer"]["media_dir"])
        target = os.path.realpath(os.path.join(media_dir, request.form.get("rel", "")))
        # Non si esce dalla cartella della libreria.
        if target.startswith(media_dir + os.sep) and os.path.isfile(target):
            try:
                os.remove(target)
            except OSError:
                pass
        return redirect(url_for("page_media"))

    @app.route("/api/media/preview", methods=["POST"])
    def api_media_preview():
        runtime.media.trigger_now()
        return redirect(url_for("page_media"))

    @app.route("/api/time", methods=["POST"])
    def api_time():
        cfg["time"]["ntp_server"] = request.form.get("ntp_server", "pool.ntp.org").strip()
        cfg["time"]["timezone"] = request.form.get("timezone", "Europe/Rome")
        cfg["time"]["dst_auto"] = request.form.get("dst_auto") == "on"
        try:
            cfg["time"]["utc_offset"] = int(request.form.get("utc_offset", 1))
        except ValueError:
            cfg["time"]["utc_offset"] = 1
        dmdconf.save()
        apply_timezone(cfg)
        apply_ntp(cfg)
        runtime.clock.invalidate()
        return redirect(url_for("page_settings"))

    @app.route("/api/service", methods=["POST"])
    def api_service():
        key = request.form.get("key")
        if key in cfg["services"]:
            cfg["services"][key] = request.form.get("value") == "1"
            dmdconf.save()
            runtime.arbiter.apply_services()
        return redirect(url_for("page_services"))

    @app.route("/api/force", methods=["POST"])
    def api_force():
        cfg["arbiter"]["force_source"] = request.form.get("source", "auto")
        dmdconf.save()
        return redirect(url_for("page_services"))

    @app.route("/api/status")
    def api_status():
        current = runtime.arbiter.current
        return jsonify(
            version=__version__,
            current=current.name if current else None,
            brightness=cfg["display"]["brightness"],
            sleeping=runtime.sleeping,
            night=runtime.night,
            zedmd=runtime.zedmd.status(),
            media=runtime.media.status(),
            time=time.strftime("%H:%M:%S"),
        )

    return app
