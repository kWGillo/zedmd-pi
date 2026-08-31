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
import fasce
import i18n
import libcheck
import compleanni
import doomsetup
import lookup
import rifiuti
import nowplaying
import presets
import ota
import spotifyapi
from sources import (DOOM_PULSANTI, DOOM_TASTI, FIELD_LIST, HOLD_SECONDS,
                     LANGUAGES, OVERFLOW_MODES,
                     PROVIDER_LIST, SIZE_KEYS, SLOTS, UNIT_KEYS,
                     controlla_wad, giochi_elenco,
                     invalidate_scan, is_supported, joystick, normalize_list,
                     scan_media, have_ffmpeg, tastiere, usable)
from version import __version__

# Ogni quanto la pagina della gestione media dice che c'e' ancora qualcuno.
# Tre battiti stanno dentro il tempo di attesa dell'arbitro: uno perso per un
# wifi lento non fa cadere la modalita'.
MANAGER_BEAT = 10

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

    @app.template_filter("mmss")
    def _mmss(value):
        return nowplaying.format_time(value)

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
            hostname=socket.gethostname(),
            sleeping=runtime.sleeping, night=runtime.night,
            presets=presets.choices(), preset_now=presets.detect(cfg["panel"]),
            config_result=request.args.get("config_result"), page="settings")

    @app.route("/updates")
    def page_updates():
        """Aggiornamenti del programma e della libreria della matrice.

        Stanno insieme e fuori dalle Impostazioni perche' sono l'unica parte
        che *cambia il sistema* invece di regolarlo: ci si entra quando si
        vuole aggiornare, non mentre si cerca un colore o un orario.
        """
        return render_template(
            "updates.html", cfg=cfg,
            update=runtime.update_info, ota_log=ota.tail_log(12),
            lib=runtime.lib_info,
            lib_commands=libcheck.update_commands(libcheck.library_dir(cfg)),
            page="updates")

    @app.route("/birthdays")
    def page_birthdays():
        return render_template(
            "birthdays.html", cfg=cfg,
            elenco=compleanni.imminenti(cfg["birthdays"]["lead_hours"]),
            testo=compleanni.read_text(), info=compleanni.stats(),
            sizes=SIZE_KEYS, tipi=compleanni.TIPI,
            risultato=request.args.get("risultato", ""),
            errori=_birthday_errors(), page="birthdays")

    @app.route("/api/birthdays", methods=["POST"])
    def api_birthdays():
        conf = cfg["birthdays"]
        for key, low, high, default in (("lead_hours", 1, 720, 48),
                                        ("interval_minutes", 1, 1440, 20),
                                        ("seconds", 3, 120, 12),
                                        ("speed", 10, 200, 40)):
            try:
                conf[key] = max(low, min(high, int(request.form.get(key, default))))
            except ValueError:
                conf[key] = default
        misura = request.form.get("size", "medium")
        conf["size"] = misura if misura in SIZE_KEYS else "medium"
        conf["color"] = request.form.get("color", "#ff40a0")
        conf["blink"] = request.form.get("blink") == "on"
        conf["show_age"] = request.form.get("show_age") == "on"
        dmdconf.save()
        return redirect(url_for("page_birthdays"))

    @app.route("/api/birthdays/text", methods=["POST"])
    def api_birthdays_text():
        voci, errori = compleanni.save(request.form.get("text", ""))
        _birthday_errors(errori)
        runtime.birthdays.trigger_now()
        return redirect(url_for("page_birthdays",
                                risultato="saved:%d" % len(voci)))

    @app.route("/api/birthdays/add", methods=["POST"])
    def api_birthdays_add():
        errore = compleanni.aggiungi(request.form.get("data", ""),
                                     request.form.get("nome", ""),
                                     request.form.get("tipo", ""))
        runtime.birthdays.trigger_now()
        return redirect(url_for("page_birthdays",
                                risultato="error:%s" % errore if errore else "added"))

    @app.route("/api/birthdays/upload", methods=["POST"])
    def api_birthdays_upload():
        """Carica un CSV: lo aggiunge in coda invece di sostituire.

        Sostituire sarebbe piu' semplice ma cancellerebbe senza avviso quello
        che c'e' gia'. Chi vuole ripartire da zero svuota la casella di testo,
        che e' un gesto esplicito.
        """
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            return redirect(url_for("page_birthdays", risultato="error:nofile"))
        try:
            grezzo = upload.read().decode("utf-8", "replace")
        except Exception:
            return redirect(url_for("page_birthdays", risultato="error:read"))
        voci, errori = compleanni.parse(grezzo)
        esistenti = compleanni.read_text()
        righe = ["%02d/%02d%s,%s,%s" % (v["giorno"], v["mese"],
                                        "/%d" % v["anno"] if v["anno"] else "",
                                        v["nome"], v["tipo"]) for v in voci]
        nuovo = esistenti.rstrip("\n") + "\n" + "\n".join(righe) + "\n"
        _, errori_scrittura = compleanni.save(nuovo)
        _birthday_errors(errori + errori_scrittura)
        runtime.birthdays.trigger_now()
        return redirect(url_for("page_birthdays",
                                risultato="imported:%d" % len(voci)))

    @app.route("/clock")
    def page_clock():
        # Nome diverso da `languages`, che nel contesto globale sono le lingue
        # dell'interfaccia: queste sono quelle dei giorni sul pannello.
        return render_template(
            "clock.html", cfg=cfg, clock_languages=LANGUAGES,
            timezones=all_timezones(), ntp=ntp_status(),
            now=time.strftime("%d/%m/%Y %H:%M:%S"), page="clock")

    # Quanti file per pagina nell'elenco della libreria.
    MEDIA_PER_PAGINA = 200

    def _elenco_libreria():
        """Una pagina dell'elenco della libreria, con il peso di ogni file.

        Una libreria vera supera facilmente le poche centinaia di file:
        mostrarne solo i primi voleva dire non poter cancellare gli altri.
        """
        media_dir = cfg["mediaplayer"]["media_dir"]
        files = scan_media(media_dir)
        try:
            pagina = max(1, int(request.args.get("p", 1)))
        except ValueError:
            pagina = 1
        pagine = max(1, (len(files) + MEDIA_PER_PAGINA - 1) // MEDIA_PER_PAGINA)
        pagina = min(pagina, pagine)
        inizio = (pagina - 1) * MEDIA_PER_PAGINA

        listing = []
        for path in files[inizio:inizio + MEDIA_PER_PAGINA]:
            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0
            listing.append({
                "rel": os.path.relpath(path, media_dir),
                "size": "%.1f MB" % (size / 1048576) if size >= 1048576
                        else "%d kB" % max(1, size // 1024),
            })
        return {"media_dir": media_dir, "files": listing, "total": len(files),
                "pagina": pagina, "pagine": pagine, "primo": inizio + 1,
                "ultimo": inizio + len(listing)}

    @app.route("/media")
    def page_media():
        elenco = _elenco_libreria()
        return render_template(
            "media.html", cfg=cfg, total=elenco["total"],
            media_dir=elenco["media_dir"], ffmpeg=have_ffmpeg(),
            status=runtime.media.status(current_language()), page="media")

    @app.route("/manager")
    def page_manager():
        """Gestione della libreria, con il pannello riservato a chi guarda.

        Entrare qui sospende tutte le sorgenti — ZeDMD compreso — perche' il
        problema dell'anteprima non era di priorita' ma di tempi: fra un file
        e l'altro c'e' sempre una finestra in cui qualcun altro puo'
        infilarsi, e allora si guarda un aereo invece della GIF su cui si e'
        appena premuto. Qui la domanda e' una sola — che cos'e' questo file —
        e finche' resta aperta il pannello non risponde ad altri.
        """
        runtime.manager_enter()
        elenco = _elenco_libreria()
        return render_template(
            "manager.html", cfg=cfg, ffmpeg=have_ffmpeg(),
            anteprima=request.args.get("anteprima", ""),
            battito=MANAGER_BEAT, stato=runtime.manager_state(),
            page="manager", **elenco)

    # --------------------------------------------------------------- rifiuti

    @app.route("/rifiuti")
    def page_rifiuti():
        elenco = []
        for voce in rifiuti.voci(cfg):
            elenco.append(dict(voce, prossima=rifiuti.prossima(voce)))
        return render_template(
            "rifiuti.html", cfg=cfg, voci=elenco,
            giorni=rifiuti.GIORNI_LUNGHI, cadenze=rifiuti.CADENZE,
            attive=rifiuti.attive(cfg),
            soppressioni=rifiuti.leggi_testo(rifiuti.SOPPRESSIONI),
            straordinari=rifiuti.leggi_testo(rifiuti.STRAORDINARI),
            page="rifiuti")

    @app.route("/api/rifiuti", methods=["POST"])
    def api_rifiuti():
        conf = cfg.setdefault("rifiuti", {})
        for chiave, predefinito in (("ora_avviso", 18), ("ora_fine", 8)):
            try:
                conf[chiave] = max(0, min(23, int(request.form.get(chiave, predefinito))))
            except ValueError:
                conf[chiave] = predefinito

        nuove = []
        for indice, vecchia in enumerate(rifiuti.voci(cfg)):
            voce = dict(vecchia)
            voce["nome"] = request.form.get("nome%d" % indice, voce["nome"]).strip()                 or voce["nome"]
            voce["colore"] = request.form.get("colore%d" % indice, voce["colore"]).strip()
            tipo = request.form.get("tipo%d" % indice, voce["tipo"])
            voce["tipo"] = tipo if tipo in rifiuti.TIPI else rifiuti.TIPO_PREDEFINITO
            cadenza = request.form.get("cadenza%d" % indice, voce["cadenza"])
            voce["cadenza"] = cadenza if cadenza in rifiuti.CADENZE                 else rifiuti.CADENZA_PREDEFINITA
            voce["attiva"] = request.form.get("attiva%d" % indice) == "on"
            voce["giorni"] = [g for g in range(7)
                              if request.form.get("g%d_%d" % (indice, g)) == "on"]
            # La data si conserva come testo: e' quello che l'utente ha
            # scritto, e riscriverlo normalizzato gli farebbe credere di aver
            # sbagliato quando invece era giusto.
            voce["riferimento"] = request.form.get("riferimento%d" % indice, "").strip()
            for campo, chiave in (("oi", "ora_inizio"), ("of", "ora_fine")):
                try:
                    voce[chiave] = max(0, min(23, int(
                        request.form.get("%s%d" % (campo, indice), voce[chiave]))))
                except ValueError:
                    pass
            nuove.append(voce)
        conf["voci"] = nuove
        dmdconf.save()
        runtime.clock.invalidate()
        return redirect(url_for("page_rifiuti"))

    @app.route("/api/rifiuti/eccezioni", methods=["POST"])
    def api_rifiuti_eccezioni():
        quale = request.form.get("quale", "")
        nome = {"soppressioni": rifiuti.SOPPRESSIONI,
                "straordinari": rifiuti.STRAORDINARI}.get(quale)
        if nome:
            rifiuti.salva_testo(nome, request.form.get("testo", ""))
            runtime.clock.invalidate()
        return redirect(url_for("page_rifiuti"))

    # ---------------------------------------------------------------- giochi

    GIOCHI_PULSANTI = (("sinistra", "\u25c0"), ("destra", "\u25b6"),
                       ("fuoco", "FUOCO"), ("esci", "ESCI"))

    def _giochi_stato():
        stato = runtime.giochi_state()
        stato["testo"] = runtime.giochi.status(current_language())
        return stato

    @app.route("/giochi")
    def page_giochi():
        stato = _giochi_stato()
        conf = cfg.get("giochi") or {}
        errore = controlla_wad(cfg["doom"].get("wad", ""))
        return render_template(
            "giochi.html", cfg=cfg, stato=stato, stato_testo=stato["testo"],
            giochi=giochi_elenco(), record=(conf.get("record") or {}),
            pulsanti=GIOCHI_PULSANTI, pad=joystick(con_nome=True),
            doom_pronto=i18n.translate(
                "giochi.doom.no" if errore else "giochi.doom.si",
                current_language()),
            page="giochi")

    @app.route("/api/giochi/state")
    def api_giochi_state():
        return jsonify(_giochi_stato())

    @app.route("/api/giochi/play", methods=["POST"])
    def api_giochi_play():
        runtime.gioca("giochi", request.form.get("gioco", "").strip())
        if request.form.get("ajax"):
            return jsonify(_giochi_stato())
        return redirect(url_for("page_giochi"))

    @app.route("/api/giochi/stop", methods=["POST"])
    def api_giochi_stop():
        runtime.giochi.chiudi_sessione()
        if request.form.get("ajax"):
            return jsonify(_giochi_stato())
        return redirect(url_for("page_giochi"))

    @app.route("/api/giochi/tasto", methods=["POST"])
    def api_giochi_tasto():
        """Un comando dalla pagina web.

        Premuto e rilasciato arrivano separati, come da una tastiera vera:
        e' l'unico modo perche' tenere premuto il pulsante faccia scorrere la
        racchetta invece di farle fare un salto solo.
        """
        azione = request.form.get("azione", "").strip()
        if azione not in ("sinistra", "destra", "su", "giu", "fuoco",
                          "avvia", "esci"):
            return jsonify({"ok": False}), 400
        if "giu" in request.form:
            runtime.giochi.premi(azione, request.form.get("giu") == "1")
        else:
            runtime.giochi.tocca(azione)
        return jsonify(_giochi_stato())

    @app.route("/api/giochi", methods=["POST"])
    def api_giochi():
        conf = cfg.setdefault("giochi", {})
        for chiave in ("keyboard", "keyboard_starts",
                       "joystick", "joystick_starts"):
            conf[chiave] = request.form.get(chiave) == "on"
        for chiave in ("keyboard_device", "joystick_device"):
            if chiave in request.form:
                conf[chiave] = request.form.get(chiave, "").strip()
        try:
            conf["session_timeout"] = max(0, min(3600, int(
                request.form.get("session_timeout", 180))))
        except ValueError:
            conf["session_timeout"] = 180
        dmdconf.save()
        # La lettura dei comandi dipende da queste caselle: senza far ripartire
        # il lettore, spegnere la tastiera non avrebbe effetto fino al riavvio.
        runtime.giochi.stop()
        runtime.giochi.start()
        return redirect(url_for("page_giochi"))

    # ------------------------------------------------------------------ doom

    @app.route("/doom")
    def page_doom():
        return render_template(
            "doom.html", cfg=cfg, doom=cfg["doom"],
            stato=runtime.doom_state(), pulsanti=DOOM_PULSANTI,
            tastiere=tastiere(), pad=joystick(con_nome=True),
            prep=doomsetup.stato(cfg), page="doom")

    @app.route("/api/doom/setup", methods=["POST"])
    def api_doom_setup():
        """Compila Doom e prende i WAD, in sottofondo.

        Senza questo pulsante, per accendere una funzione bisognava aprire una
        sessione SSH — e dopo un aggiornamento via rete non c'e' nemmeno una
        cartella scompattata da cui lanciare lo script.
        """
        errore = doomsetup.avvia(cfg)
        return redirect(url_for("page_doom", prep="errore" if errore else "avviata"))

    @app.route("/api/doom/setup/state")
    def api_doom_setup_state():
        return jsonify(doomsetup.stato(cfg))

    @app.route("/api/doom/wad", methods=["POST"])
    def api_doom_wad():
        """Sceglie quale WAD usare fra quelli trovati."""
        scelto = request.form.get("wad", "").strip()
        disponibili = {w["path"] for w in doomsetup.wad_disponibili(cfg)}
        # Solo fra quelli trovati nella cartella: un percorso arbitrario da un
        # form e' un percorso che qualcuno puo' scrivere a mano.
        if scelto and scelto in disponibili:
            cfg["doom"]["wad"] = scelto
            dmdconf.save()
            # Si riavvia **sempre**, non solo se stava girando. Prima si
            # riavviava a condizione che il processo fosse vivo, e quella
            # condizione era falsa proprio nel caso in cui questo pulsante
            # serve: il WAD sbagliato aveva impedito l'avvio, si sceglieva
            # quello giusto e non succedeva niente.
            runtime.doom.chiudi_sessione(riavvia=False)
            runtime.doom.riavvia()
        return redirect(url_for("page_doom"))

    @app.route("/api/doom/key", methods=["POST"])
    def api_doom_key():
        """Un tasto verso Doom, dalla tastiera del browser o da un pulsante.

        `stato` vale `down`, `up` oppure `tap`. Il terzo esiste per i
        pulsanti sul telefono: un dito che scivola fuori dal pulsante non
        genera nessun rilascio, e un tasto rimasto premuto in Doom vuol dire
        camminare dentro un muro per sempre.
        """
        azione = request.form.get("azione", "")
        stato = request.form.get("stato", "tap")
        if azione not in DOOM_TASTI:
            return jsonify(ok=False, error="tasto sconosciuto"), 400
        if stato == "tap":
            ok = runtime.doom.tocca(azione)
        else:
            ok = runtime.doom.premi(azione, stato == "down")
        return jsonify(ok=bool(ok), **runtime.doom_state())

    @app.route("/api/doom/state")
    def api_doom_state():
        return jsonify(runtime.doom_state())

    @app.route("/api/doom/play", methods=["POST"])
    def api_doom_play():
        runtime.gioca("doom")
        if request.form.get("ajax"):
            return jsonify(runtime.doom_state())
        return redirect(url_for("page_doom"))

    @app.route("/api/doom/stop", methods=["POST"])
    def api_doom_stop():
        runtime.doom.chiudi_sessione()
        if request.form.get("ajax"):
            return jsonify(runtime.doom_state())
        return redirect(url_for("page_doom"))

    @app.route("/api/doom", methods=["POST"])
    def api_doom():
        conf = cfg["doom"]
        for chiave in ("binary", "wad", "work_dir", "keyboard_device",
                       "joystick_device", "start_map"):
            if chiave in request.form:
                conf[chiave] = request.form.get(chiave, "").strip()
        for chiave, basso, alto, default in (("band_top", 0, 190, 36),
                                             ("band_height", 8, 200, 96),
                                             ("skill", 1, 5, 3),
                                             ("session_timeout", 0, 3600, 180)):
            try:
                conf[chiave] = max(basso, min(alto, int(request.form.get(chiave, default))))
            except ValueError:
                conf[chiave] = default
        try:
            conf["gamma"] = max(0.2, min(2.0, float(request.form.get("gamma", 1.15))))
        except ValueError:
            conf["gamma"] = 1.15
        # La fascia non puo' sporgere dai 200 righe di Doom.
        if conf["band_top"] + conf["band_height"] > 200:
            conf["band_height"] = 200 - conf["band_top"]
        for chiave in ("keyboard", "keyboard_starts",
                       "joystick", "joystick_starts"):
            conf[chiave] = request.form.get(chiave) == "on"
        dmdconf.save()
        # La fascia e la gamma stanno nella riga di comando del processo:
        # cambiarle in configurazione non basta, va fatto ripartire. E si
        # riparte anche da fermo: se il processo era morto per un percorso
        # sbagliato, correggerlo qui deve bastare a rimetterlo in moto.
        runtime.doom.chiudi_sessione(riavvia=False)
        runtime.doom.riavvia()
        return redirect(url_for("page_doom"))

    @app.route("/api/manager/beat", methods=["POST"])
    def api_manager_beat():
        """Battito della pagina: rinnova la gestione e riferisce lo stato.

        Senza, una scheda chiusa lascerebbe il pannello fermo per sempre.
        """
        runtime.manager_enter()
        return jsonify(runtime.manager_state())

    @app.route("/api/manager/exit", methods=["POST"])
    def api_manager_exit():
        runtime.manager_leave()
        if request.form.get("beacon") or request.headers.get("X-Beacon"):
            return "", 204
        return redirect(url_for("page_media"))

    @app.route("/api/media/show", methods=["POST"])
    def api_media_show():
        """Mostra un file *preciso* della libreria sul pannello.

        Da non confondere con /api/media/preview, che fa avanzare il Media
        Player al contenuto successivo: qui si sceglie quale.

        Guardarlo sul computer non risponde alla domanda vera: come viene su
        *quel* pannello, con quella scala e quei colori.
        """
        media_dir = os.path.realpath(cfg["mediaplayer"]["media_dir"])
        rel = request.form.get("rel", "")
        percorso = os.path.realpath(os.path.join(media_dir, rel))
        pagina = request.form.get("p", "1")
        if not percorso.startswith(media_dir + os.sep) \
                or not os.path.isfile(percorso) or not is_supported(percorso):
            return redirect(url_for("page_manager", p=pagina, anteprima="error"))
        try:
            secondi = int(request.form.get("seconds", 0))
        except ValueError:
            secondi = 0
        # In gestione il file resta finche' non se ne chiede un altro: una GIF
        # continua a girare invece di fermarsi dopo dieci secondi.
        runtime.manager_enter()
        runtime.preview.show(percorso, rel, secondi or HOLD_SECONDS)
        return redirect(url_for("page_manager", p=pagina, anteprima=rel))

    @app.route("/media/file/<path:rel>")
    def media_file(rel):
        """Restituisce un file della libreria, per l'anteprima nella pagina.

        Prima di cancellare qualcosa serve vedere che cos'e': il nome del file
        raramente basta. Il percorso viene risolto e confrontato con la
        cartella della libreria, cosi' un `../` non porta da nessuna parte.
        """
        media_dir = os.path.realpath(cfg["mediaplayer"]["media_dir"])
        percorso = os.path.realpath(os.path.join(media_dir, rel))
        if not percorso.startswith(media_dir + os.sep):
            return "", 404
        if not os.path.isfile(percorso) or not is_supported(percorso):
            return "", 404
        return send_file(percorso)

    @app.route("/banner")
    def page_banner():
        return render_template(
            "banner.html", cfg=cfg,
            items=normalize_list(cfg["banner"]["items"]),
            sizes=SIZE_KEYS, slots=SLOTS,
            active=len(usable(cfg["banner"]["items"])),
            status=runtime.banner.status(current_language()), page="banner")

    @app.route("/nowplaying")
    def page_nowplaying():
        return render_template(
            "nowplaying.html", cfg=cfg,
            track=runtime.nowplaying.snapshot(),
            mqtt=runtime.mqtt.status(),
            spotify=runtime.spotify.status(),
            authorize_url=request.args.get("authorize", ""),
            result=request.args.get("result", ""),
            status=runtime.player.status(current_language()), page="nowplaying")

    @app.route("/radar")
    def page_radar():
        return render_template("radar.html", cfg=cfg, providers=PROVIDER_LIST,
                               fields=FIELD_LIST, overflow_modes=OVERFLOW_MODES,
                               unit_keys=UNIT_KEYS,
                               log=runtime.radar.log_info(),
                               status=runtime.radar.status(current_language()),
                               probe_callsign=request.args.get("callsign", ""),
                               probe_result=request.args.get("result"),
                               tables=[lookup.stats(k) for k in lookup.KINDS],
                               table_text={k: lookup.read_text(k)
                                           for k in lookup.KINDS},
                               unknown=lookup.unknown(),
                               data_dir=lookup.DATA_DIR,
                               lookup_result=request.args.get("lookup_result", ""),
                               lookup_errors=_lookup_errors(),
                               page="radar")

    def _lookup_errors():
        """Righe scartate all'ultimo salvataggio, passate via query string."""
        raw = request.args.get("lookup_bad", "")
        out = []
        for pezzo in raw.split("|"):
            if ":" in pezzo:
                numero, motivo = pezzo.split(":", 1)
                if numero.strip().isdigit():
                    out.append({"row": int(numero), "reason": motivo})
        return out

    @app.route("/services")
    def page_services():
        lang = current_language()

        def stato(nome):
            """Stato di una sorgente, vuoto se quella sorgente non c'e'.

            Questa e' la pagina dove si va quando qualcosa non funziona: deve
            aprirsi sempre. Una sorgente assente e' un caso da segnalare, non
            un motivo per far fallire l'unica pagina da cui si puo' rimediare.
            """
            sorgente = getattr(runtime, nome, None)
            try:
                return sorgente.status(lang) if sorgente else ""
            except Exception as exc:
                return str(exc)

        services = [
            {"key": "zedmd", "label": "ZeDMD", "ready": True,
             "status": stato("zedmd")},
            {"key": "mediaplayer", "label": "Media Player", "ready": True,
             "status": stato("media")},
            {"key": "banner", "label": "Rolling Banner", "ready": True,
             "status": stato("banner")},
            {"key": "nowplaying", "label": "Now Playing", "ready": True,
             "status": stato("player")},
            {"key": "birthdays", "label": "Compleanni", "ready": True,
             "status": stato("birthdays")},
            {"key": "clock", "label": "Clock", "ready": True,
             "status": stato("clock")},
            {"key": "status_player", "label": "Status Player", "ready": False,
             "status": ""},
            {"key": "air_radar", "label": "Air Radar", "ready": True,
             "status": stato("radar")},
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

    @app.route("/api/media/timer", methods=["POST"])
    def api_media_timer():
        """La fascia oraria del Media Player.

        Endpoint separato da quello della riproduzione perche' sono due
        moduli distinti nella stessa pagina: salvarne uno non deve azzerare
        i campi dell'altro, che e' quello che succederebbe leggendoli tutti
        da una richiesta che ne contiene meta'.
        """
        media = cfg["mediaplayer"]
        media["timer_enabled"] = request.form.get("timer_enabled") == "on"
        for chiave, predefinito in (("timer_start", fasce.MEDIA_INIZIO),
                                    ("timer_end", fasce.MEDIA_FINE)):
            valore = (request.form.get(chiave) or "").strip() or predefinito
            # Si riscrive normalizzato: "8:0" e "25:70" sono comunque un
            # orario, e vale la pena salvarli come tali invece di rifiutarli.
            minuti = fasce.parse_hhmm(valore, fasce.parse_hhmm(predefinito))
            media[chiave] = "%02d:%02d" % (minuti // 60, minuti % 60)
        dmdconf.save()
        # La fascia si applica al prossimo giro del ciclo comunque, ma
        # chiamarla qui vuol dire che la pagina che si ricarica dice gia' la
        # verita' invece di aspettare un secondo.
        try:
            runtime.arbiter.apply_services()
        except Exception:
            pass
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
        return redirect(url_for("page_manager"))

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
        # Cancellare il file che si sta guardando lascerebbe a schermo
        # l'anteprima di una cosa che non c'e' piu'.
        if runtime.preview.current == request.form.get("rel", ""):
            runtime.preview.cancel()
            runtime.manager_enter()
            runtime.preview.hold()
        return redirect(url_for("page_manager", p=request.form.get("p", "1")))

    @app.route("/api/media/rescan", methods=["POST"])
    def api_media_rescan():
        # I file copiati via SMB non passano da qui: questo pulsante forza la
        # rilettura senza aspettare la scadenza della cache.
        scan_media(cfg["mediaplayer"]["media_dir"], force=True)
        return redirect(url_for("page_manager"))

    @app.route("/api/media/preview", methods=["POST"])
    def api_media_preview():
        runtime.media.trigger_now()
        return redirect(url_for("page_media"))

    @app.route("/api/panel", methods=["POST"])
    def api_panel():
        panel = cfg["panel"]
        for key, low, high, default in (("limit_refresh", 0, 300, 60),
                                        ("pwm_bits", 1, 11, 11),
                                        ("pwm_lsb_nanoseconds", 50, 3000, 130),
                                        ("pwm_dither_bits", 0, 2, 0),
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

        # Il profilo si applica *dopo* i campi: scegliendone uno noto si
        # vuole tornare ai suoi valori, non salvare quelli che erano nella
        # pagina. Sceglierne uno solo per sbaglio non e' un rischio: la
        # configurazione precedente si riottiene riapplicando il profilo.
        scelto = request.form.get("preset", "")
        if scelto and (presets.known(scelto) or scelto == presets.CUSTOM):
            presets.apply(panel, scelto)
        else:
            panel["preset"] = presets.detect(panel)

        dmdconf.save()

        if request.form.get("restart") == "1":
            subprocess.Popen(["systemctl", "restart", "dmd"])
        return redirect(url_for("page_settings"))

    @app.route("/api/update/check", methods=["POST"])
    def api_update_check():
        runtime.check_update()
        return redirect(url_for("page_updates"))

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
        return redirect(url_for("page_updates"))

    @app.route("/api/update/install", methods=["POST"])
    def api_update_install():
        ota.start_update(cfg)
        return redirect(url_for("page_updates"))

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

    # ------------------------------------------------------------- now playing

    @app.route("/api/mqtt", methods=["POST"])
    def api_mqtt():
        conf = cfg["mqtt"]
        conf["enabled"] = request.form.get("enabled") == "on"
        conf["discovery"] = request.form.get("discovery") == "on"
        for key, default in (("host", "127.0.0.1"), ("username", ""),
                             ("password", ""), ("client_id", "dmd"),
                             ("base_topic", "dmd"),
                             ("shairport_topic", "shairport"),
                             ("external_topic", ""),
                             ("discovery_prefix", "homeassistant"),
                             ("node_id", "dmd"),
                             ("device_name", "kWGillo DMD Server")):
            conf[key] = request.form.get(key, default).strip()
        try:
            conf["port"] = max(1, min(65535, int(request.form.get("port", 1883))))
        except ValueError:
            conf["port"] = 1883
        # Un topic di base vuoto produrrebbe percorsi che iniziano con "/":
        # meglio riportarlo al valore predefinito che pubblicare a vuoto.
        conf["base_topic"] = conf["base_topic"] or "dmd"
        dmdconf.save()
        runtime.reconnect_mqtt()
        return redirect(url_for("page_nowplaying"))

    @app.route("/api/hass/announce", methods=["POST"])
    def api_hass_announce():
        # Via d'uscita manuale. Normalmente non serve: le dichiarazioni sono
        # ritenute dal broker e Home Assistant, quando riparte, annuncia la
        # propria presenza e il DMD si ridichiara da solo.
        ok = runtime.hass.reannounce()
        return _hass_result("nowplaying.hass.announced" if ok
                            else "nowplaying.hass.disabled")

    @app.route("/api/hass/remove", methods=["POST"])
    def api_hass_remove():
        runtime.hass.remove()
        return _hass_result("nowplaying.hass.removed")

    def _hass_result(key):
        return redirect(url_for("page_nowplaying", result=i18n.translate(
            key, current_language())))

    @app.route("/api/nowplaying", methods=["POST"])
    def api_nowplaying():
        conf = cfg["nowplaying"]
        for key in ("title_color", "artist_color", "album_color", "bar_color"):
            conf[key] = request.form.get(key, conf[key]).strip()
        try:
            conf["hold_seconds"] = max(5, min(3600,
                int(request.form.get("hold_seconds", 90))))
        except ValueError:
            conf["hold_seconds"] = 90
        conf["safe_colors"] = request.form.get("safe_colors") == "on"
        dmdconf.save()
        runtime.player.invalidate()
        return redirect(url_for("page_nowplaying"))

    @app.route("/api/nowplaying/test", methods=["POST"])
    def api_nowplaying_test():
        # Un brano finto con una durata plausibile e una scadenza breve: si
        # vede subito com'e' fatto il player, senza dover far partire musica.
        runtime.nowplaying.update(
            "external", title="Bohemian Rhapsody", artist="Queen",
            album="A Night at the Opera", duration=355.0, position=167.0,
            playing=True, active=True, client="test", expires=60)
        runtime.player.invalidate()
        return redirect(url_for("page_nowplaying"))

    # ------------------------------------------------------------------ spotify

    @app.route("/api/spotify", methods=["POST"])
    def api_spotify():
        conf = cfg["spotify"]
        conf["enabled"] = request.form.get("enabled") == "on"
        conf["client_id"] = request.form.get("client_id", "").strip()
        conf["redirect_uri"] = (request.form.get("redirect_uri", "").strip()
                                or spotifyapi.DEFAULT_REDIRECT)
        try:
            conf["poll_interval"] = max(3, min(300,
                int(request.form.get("poll_interval", 8))))
        except ValueError:
            conf["poll_interval"] = 8
        dmdconf.save()
        runtime.spotify.poll_now()
        return redirect(url_for("page_nowplaying"))

    @app.route("/api/spotify/authorize", methods=["POST"])
    def api_spotify_authorize():
        lang = current_language()
        try:
            target = spotifyapi.authorize_url(cfg)
        except ValueError as exc:
            return redirect(url_for("page_nowplaying", result=i18n.translate(
                "nowplaying.spotify.failed", lang, error=str(exc))))
        return redirect(url_for("page_nowplaying", authorize=target))

    @app.route("/api/spotify/complete", methods=["POST"])
    def api_spotify_complete():
        return _spotify_exchange(request.form.get("pasted", ""))

    @app.route("/api/spotify/callback")
    def api_spotify_callback():
        # Raggiungibile solo se qualcuno riesce davvero ad arrivare qui; il
        # percorso normale resta l'indirizzo incollato a mano.
        if request.args.get("error"):
            return _spotify_result("nowplaying.spotify.failed",
                                   error=request.args["error"])
        return _spotify_exchange(request.url)

    def _spotify_exchange(pasted):
        try:
            spotifyapi.complete(cfg, pasted)
        except Exception as exc:
            return _spotify_result("nowplaying.spotify.failed", error=str(exc))
        runtime.spotify.poll_now()
        return _spotify_result("nowplaying.spotify.ok")

    @app.route("/api/spotify/disconnect", methods=["POST"])
    def api_spotify_disconnect():
        spotifyapi.disconnect()
        runtime.nowplaying.clear("spotify")
        return _spotify_result("nowplaying.spotify.gone")

    def _spotify_result(key, **values):
        return redirect(url_for("page_nowplaying", result=i18n.translate(
            key, current_language(), **values)))

    # ------------------------------------------------------- libreria del pannello

    @app.route("/api/library/check", methods=["POST"])
    def api_library_check():
        runtime.check_library()
        return redirect(url_for("page_updates"))

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
                                        ("max_altitude_ft", 0, 60000, 0),
                                        ("page_seconds", 1, 30, 3),
                                        ("scroll_speed", 10, 200, 40),
                                        ("scroll_fps", 10, 60, 30)):
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
        # Una casella lasciata vuota fa seguire alla rotta il colore dei
        # dettagli: e' il comportamento di prima, quando la rotta stava in
        # quella riga.
        radar["route_color"] = request.form.get("route_color", "").strip()
        # Come comportarsi quando i campi scelti non stanno su una riga.
        modo = request.form.get("overflow", "pages")
        radar["overflow"] = modo if modo in OVERFLOW_MODES else "pages"
        for campo, ammessi in (("unit_altitude", UNIT_KEYS["altitude"]),
                               ("unit_speed", UNIT_KEYS["speed"]),
                               ("unit_distance", UNIT_KEYS["distance"])):
            scelta = request.form.get(campo, "")
            radar[campo] = scelta if scelta in ammessi else ammessi[0]
        dmdconf.save()
        runtime.radar.poll_now()
        return redirect(url_for("page_radar"))

    _birthday_state = {"errors": []}

    def _birthday_errors(nuovi=None):
        """Errori dell'ultimo salvataggio, da mostrare una volta sola."""
        if nuovi is not None:
            _birthday_state["errors"] = nuovi
            return nuovi
        fuori = _birthday_state["errors"]
        _birthday_state["errors"] = []
        return fuori

    @app.route("/api/radar/lookup", methods=["POST"])
    def api_radar_lookup():
        kind = request.form.get("kind", "")
        if kind not in lookup.KINDS:
            return redirect(url_for("page_radar"))
        entries, errors = lookup.save(kind, request.form.get("text", ""))
        lang = current_language()
        if errors:
            messaggio = i18n.translate("lookup.saved.errors", lang,
                                       count=len(entries), errors=len(errors))
            # Le prime righe scartate viaggiano nella query string: sono
            # l'unica cosa che serve davvero per correggere.
            bad = "|".join("%d:%s" % (n, motivo) for n, motivo, _ in errors[:8])
            return redirect(url_for("page_radar", lookup_result=messaggio,
                                    lookup_bad=bad))
        return redirect(url_for("page_radar", lookup_result=i18n.translate(
            "lookup.saved", lang, count=len(entries))))

    @app.route("/api/radar/lookup/reload", methods=["POST"])
    def api_radar_lookup_reload():
        lookup.invalidate()
        return redirect(url_for("page_radar", lookup_result=i18n.translate(
            "lookup.reloaded", current_language())))

    @app.route("/api/radar/lookup/add", methods=["POST"])
    def api_radar_lookup_add():
        lang = current_language()
        aggiunti = 0
        for kind in lookup.KINDS:
            codici = [item["code"] for item in lookup.unknown(kind)]
            aggiunti += lookup.append_missing(kind, codici)
        chiave = "lookup.added" if aggiunti else "lookup.added.none"
        if aggiunti:
            lookup.forget_unknown()
        return redirect(url_for("page_radar", lookup_result=i18n.translate(
            chiave, lang, count=aggiunti)))

    @app.route("/api/radar/lookup/forget", methods=["POST"])
    def api_radar_lookup_forget():
        lookup.forget_unknown()
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
        # Il riquadro vive nella pagina Orologio: si torna li'.
        return redirect(url_for("page_clock"))

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
        # Lo stato e' una fotografia, non un comando: una voce che manca non
        # deve far cadere la risposta intera. E' la lezione della 1.7.1
        # applicata a un campo alla volta.
        stato_gestione = getattr(runtime, "manager_state", None)
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
            nowplaying=runtime.nowplaying.snapshot(),
            manager=stato_gestione() if stato_gestione else {"on": False},
            doom=(runtime.doom_state()
                  if getattr(runtime, "doom_state", None) else {"enabled": False}),
            mqtt=runtime.mqtt.status(),
            time=time.strftime("%H:%M:%S"),
            update=runtime.update_info,
        )

    return app
