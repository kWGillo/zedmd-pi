"""Interfaccia web del DMD.

Gira sulla porta 8080. La porta 80 e' riservata all'handshake ZeDMD,
servito da `zedmd_http.py`, che redirige qui ogni altro percorso.
"""

import json
import os
import socket
import subprocess
import time

from flask import (Flask, has_request_context, jsonify, redirect,
                   render_template, request, send_file, url_for)
from werkzeug.utils import secure_filename

import dmdconf
import i18n
import libcheck
import ota
from sources import (FIELD_LIST, LANGUAGES, PROVIDER_LIST, SIZE_KEYS, SLOTS,
                     invalidate_scan, is_supported, normalize_list, scan_media,
                     have_ffmpeg, usable)
from version import __version__

# Dove finiscono le copie della configurazione prima di un'importazione.
BACKUP_DIR = "/var/lib/dmd"

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

    def current_language():
        """Lingua di questa richiesta: preferenza salvata, poi browser.

        Fuori da una richiesta — un errore in fase di avvio, un template reso
        da codice di servizio — `request` non esiste: chiederglielo
        solleverebbe un'eccezione, quindi si guarda prima se il contesto c'e'.
        """
        header = ""
        if has_request_context():
            header = request.headers.get("Accept-Language", "")
        return i18n.resolve(cfg["web"].get("language"), header)

    @app.context_processor
    def inject_globals():
        lang = current_language()
        return {
            "version": __version__,
            "lang": lang,
            "languages": i18n.LANGUAGES,
            "github_url": i18n.GITHUB_URL,
            # `t` chiude sulla lingua della richiesta: nei template basta
            # scrivere t('chiave'), senza ripetere ogni volta la lingua.
            "t": lambda key, **values: i18n.translate(key, lang, **values),
        }

    @app.template_filter("timestamp")
    def _timestamp(value):
        try:
            return time.strftime("%d/%m/%Y %H:%M", time.localtime(float(value)))
        except (TypeError, ValueError):
            return i18n.translate("common.never", current_language())

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
            sleeping=runtime.sleeping, night=runtime.night,
            update=runtime.update_info, ota_log=ota.tail_log(12),
            lib=runtime.lib_info,
            lib_commands=libcheck.update_commands(libcheck.library_dir(cfg)),
            config_result=request.args.get("config_result"), page="settings")

    @app.route("/clock")
    def page_clock():
        # Nome diverso da `languages`, che nel contesto globale sono le lingue
        # dell'interfaccia: queste sono quelle dei giorni sul pannello.
        return render_template("clock.html", cfg=cfg, clock_languages=LANGUAGES,
                               page="clock")

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
            status=runtime.media.status(current_language()), page="media")

    @app.route("/banner")
    def page_banner():
        return render_template(
            "banner.html", cfg=cfg,
            items=normalize_list(cfg["banner"]["items"]),
            sizes=SIZE_KEYS, slots=SLOTS,
            active=len(usable(cfg["banner"]["items"])),
            status=runtime.banner.status(current_language()), page="banner")

    @app.route("/radar")
    def page_radar():
        return render_template("radar.html", cfg=cfg, providers=PROVIDER_LIST,
                               fields=FIELD_LIST, log=runtime.radar.log_info(),
                               status=runtime.radar.status(current_language()),
                               probe_callsign=request.args.get("callsign", ""),
                               probe_result=request.args.get("result"), page="radar")

    @app.route("/services")
    def page_services():
        lang = current_language()
        services = [
            {"key": "zedmd", "label": "ZeDMD", "ready": True,
             "status": runtime.zedmd.status(lang)},
            {"key": "mediaplayer", "label": "Media Player", "ready": True,
             "status": runtime.media.status(lang)},
            {"key": "banner", "label": "Rolling Banner", "ready": True,
             "status": runtime.banner.status(lang)},
            {"key": "clock", "label": "Clock", "ready": True,
             "status": runtime.clock.status(lang)},
            {"key": "status_player", "label": "Status Player", "ready": False,
             "status": ""},
            {"key": "air_radar", "label": "Air Radar", "ready": True,
             "status": runtime.radar.status(lang)},
        ]
        current = runtime.arbiter.current
        return render_template(
            "services.html", cfg=cfg, services=services,
            current=current.label if current else "—",
            sleeping=runtime.sleeping, night=runtime.night, page="services")

    # ------------------------------------------------------------ API

    @app.route("/api/language", methods=["POST"])
    def api_language():
        # Stringa vuota ammessa: significa "torna a seguire il browser".
        cfg["web"]["language"] = i18n.normalize(request.form.get("language", ""))
        dmdconf.save()
        target = request.form.get("next") or url_for("page_settings")
        # Solo percorsi interni: un redirect verso l'esterno non deve passare.
        if not target.startswith("/") or target.startswith("//"):
            target = url_for("page_settings")
        return redirect(target)

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
        invalidate_scan(media_dir)
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
            invalidate_scan(cfg["mediaplayer"]["media_dir"])
        return redirect(url_for("page_media"))

    @app.route("/api/media/rescan", methods=["POST"])
    def api_media_rescan():
        # I file copiati via SMB non passano da qui: questo pulsante forza la
        # rilettura senza aspettare la scadenza della cache.
        scan_media(cfg["mediaplayer"]["media_dir"], force=True)
        return redirect(url_for("page_media"))

    @app.route("/api/media/preview", methods=["POST"])
    def api_media_preview():
        runtime.media.trigger_now()
        return redirect(url_for("page_media"))

    @app.route("/api/panel", methods=["POST"])
    def api_panel():
        panel = cfg["panel"]
        for key, low, high, default in (("limit_refresh", 0, 300, 60),
                                        ("pwm_bits", 1, 11, 11),
                                        ("slowdown", 0, 6, 3),
                                        ("spwm_register_config", 0, 77, 2)):
            try:
                panel[key] = max(low, min(high, int(request.form.get(key, default))))
            except ValueError:
                panel[key] = default
        panel["show_refresh"] = request.form.get("show_refresh") == "on"

        env = panel.setdefault("spwm_env", {})
        for name in list(env.keys()):
            raw = request.form.get(name, "").strip()
            # Un campo vuoto rimuove l'override e ripristina il predefinito.
            env[name] = str(int(raw)) if raw.lstrip("-").isdigit() else ""
        dmdconf.save()

        if request.form.get("restart") == "1":
            subprocess.Popen(["systemctl", "restart", "dmd"])
        return redirect(url_for("page_settings"))

    @app.route("/api/update/check", methods=["POST"])
    def api_update_check():
        runtime.check_update()
        return redirect(url_for("page_settings"))

    @app.route("/api/update/settings", methods=["POST"])
    def api_update_settings():
        conf = cfg["ota"]
        conf["repo"] = request.form.get("repo", conf["repo"]).strip()
        conf["branch"] = request.form.get("branch", "main").strip() or "main"
        conf["auto_check"] = request.form.get("auto_check") == "on"
        try:
            conf["check_interval_hours"] = max(1, min(720,
                int(request.form.get("check_interval_hours", 24))))
        except ValueError:
            conf["check_interval_hours"] = 24
        dmdconf.save()
        runtime.check_update()
        return redirect(url_for("page_settings"))

    @app.route("/api/update/install", methods=["POST"])
    def api_update_install():
        ota.start_update(cfg)
        return redirect(url_for("page_settings"))

    @app.route("/api/restart", methods=["POST"])
    def api_restart():
        subprocess.Popen(["systemctl", "restart", "dmd"])
        return redirect(url_for("page_settings"))

    # ------------------------------------------------------------ rolling banner

    @app.route("/api/banner", methods=["POST"])
    def api_banner():
        banner = cfg["banner"]
        items = []
        for index in range(SLOTS):
            def field(name, default=""):
                return request.form.get("%s_%d" % (name, index), default)
            items.append({
                "text": field("text"),
                "color": field("color", "#ff8c1a"),
                "size": field("size", "medium"),
                "speed": field("speed", 60),
                # Una casella spuntata arriva come "on"; una non spuntata
                # non arriva affatto, per questo si guarda la presenza.
                "blink": request.form.get("blink_%d" % index) == "on",
                "enabled": request.form.get("enabled_%d" % index) == "on",
            })
        # La normalizzazione e' la stessa del caricamento: un valore fuori
        # scala torna nei limiti invece di essere rifiutato.
        banner["items"] = normalize_list(items)

        for key, low, high, default in (("min_interval", 3, 3600, 30),
                                        ("max_interval", 3, 3600, 60),
                                        ("fps", 10, 60, 30)):
            try:
                banner[key] = max(low, min(high, int(request.form.get(key, default))))
            except ValueError:
                banner[key] = default
        if banner["max_interval"] < banner["min_interval"]:
            banner["max_interval"] = banner["min_interval"]
        banner["shuffle"] = request.form.get("shuffle") == "on"

        dmdconf.save()
        return redirect(url_for("page_banner"))

    @app.route("/api/banner/preview", methods=["POST"])
    def api_banner_preview():
        runtime.banner.trigger_now()
        return redirect(url_for("page_banner"))

    # ------------------------------------------------------- libreria del pannello

    @app.route("/api/library/check", methods=["POST"])
    def api_library_check():
        runtime.check_library()
        return redirect(url_for("page_settings"))

    # ------------------------------------------------------------ configurazione

    @app.route("/api/config/export")
    def api_config_export():
        keep = request.args.get("position") == "1"
        data = dmdconf.snapshot(include_position=keep)
        body = json.dumps(data, indent=2, ensure_ascii=False)
        name = "dmd-config-%s-%s-%s.json" % (
            socket.gethostname(), __version__, time.strftime("%Y%m%d"))
        response = app.response_class(body, mimetype="application/json")
        response.headers["Content-Disposition"] = 'attachment; filename="%s"' % name
        return response

    @app.route("/api/config/import", methods=["POST"])
    def api_config_import():
        lang = current_language()
        storage = request.files.get("file")
        if not storage or not storage.filename:
            return _config_result(lang, "settings.config.nofile")

        try:
            raw = json.loads(storage.read().decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return _config_result(lang, "settings.config.badjson")

        # Copia di sicurezza prima di sovrascrivere: se il file importato non
        # e' quello che l'utente credeva, deve poter tornare indietro.
        backup = ""
        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            backup = os.path.join(BACKUP_DIR, "config-%s.json"
                                  % time.strftime("%Y%m%d-%H%M%S"))
            with open(backup, "w") as handle:
                json.dump(dmdconf.get(), handle, indent=2)
        except OSError:
            backup = ""

        try:
            dmdconf.replace(raw)
        except (ValueError, RuntimeError) as exc:
            return _config_result(lang, "settings.config.rejected", error=str(exc))

        runtime.clock.invalidate()
        runtime._applied_brightness = None
        # Le impostazioni del pannello valgono solo alla creazione della
        # matrice: senza riavvio ne resterebbe applicata solo una parte.
        subprocess.Popen(["systemctl", "restart", "dmd"])
        return _config_result(lang, "settings.config.imported", backup=backup)

    def _config_result(lang, key, **values):
        return redirect(url_for("page_settings",
                                config_result=i18n.translate(key, lang, **values)))

    @app.route("/api/radar", methods=["POST"])
    def api_radar():
        radar = cfg["air_radar"]
        for key, low, high, default in (("latitude", -90.0, 90.0, 0.0),
                                        ("longitude", -180.0, 180.0, 0.0),
                                        ("radius_km", 0.5, 400.0, 3.0)):
            try:
                radar[key] = max(low, min(high, float(request.form.get(key, default)
                                                     .replace(",", "."))))
            except (ValueError, AttributeError):
                radar[key] = default
        for key, low, high, default in (("poll_interval", 15, 3600, 30),
                                        ("display_seconds", 2, 120, 10),
                                        ("cooldown", 30, 86400, 600),
                                        ("max_altitude_ft", 0, 60000, 0)):
            try:
                radar[key] = max(low, min(high, int(request.form.get(key, default))))
            except ValueError:
                radar[key] = default
        provider = request.form.get("provider", "adsb.fi")
        radar["provider"] = provider if provider in dict(PROVIDER_LIST) else "adsb.fi"
        radar["log_route"] = request.form.get("log_route") == "on"
        chosen = request.form.getlist("fields")
        valid = [key for key, _ in FIELD_LIST]
        radar["fields"] = [k for k in valid if k in chosen]
        radar["log_enabled"] = request.form.get("log_enabled") == "on"
        radar["callsign_color"] = request.form.get("callsign_color", "#00d0ff")
        radar["info_color"] = request.form.get("info_color", "#ff8c1a")
        dmdconf.save()
        runtime.radar.poll_now()
        return redirect(url_for("page_radar"))

    @app.route("/api/radar/poll", methods=["POST"])
    def api_radar_poll():
        runtime.radar.poll_now()
        return redirect(url_for("page_radar"))

    @app.route("/api/radar/probe", methods=["POST"])
    def api_radar_probe():
        callsign = (request.form.get("callsign") or "").strip().upper()
        if not callsign:
            return redirect(url_for("page_radar"))
        radar = runtime.radar
        radar._route_cache.pop(callsign, None)
        radar.resolve_routes([{"flight": callsign,
                               "lat": cfg["air_radar"]["latitude"],
                               "lon": cfg["air_radar"]["longitude"]}])
        route = radar._route_cache.get(callsign) or radar._lookup_route(callsign)
        result = ("rotta di %s: %s" % (callsign, route) if route
                  else "nessuna rotta disponibile per %s" % callsign)
        return redirect(url_for("page_radar", callsign=callsign, result=result))

    @app.route("/api/radar/log")
    def api_radar_log():
        info = runtime.radar.log_info()
        if not info["exists"]:
            return plain("Nessun volo registrato.")
        return send_file(info["path"], as_attachment=True,
                         download_name="voli.csv", mimetype="text/csv")

    @app.route("/api/radar/log/clear", methods=["POST"])
    def api_radar_log_clear():
        runtime.radar.clear_log()
        return redirect(url_for("page_radar"))

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
        lang = current_language()
        return jsonify(
            version=__version__,
            current=current.name if current else None,
            brightness=cfg["display"]["brightness"],
            sleeping=runtime.sleeping,
            night=runtime.night,
            zedmd=runtime.zedmd.status(lang),
            media=runtime.media.status(lang),
            banner=runtime.banner.status(lang),
            radar=runtime.radar.status(lang),
            time=time.strftime("%H:%M:%S"),
            update=runtime.update_info,
        )

    return app
