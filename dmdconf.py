"""Gestione della configurazione persistente del DMD.

La configurazione vive in un unico file JSON. Ogni modifica dalla web UI
viene scritta subito su disco, cosi' sopravvive al riavvio.
"""

import json
import os
import threading

CONFIG_PATH = os.environ.get("DMD_CONFIG", "/etc/dmd/config.json")

DEFAULTS = {
    "panel": {
        "rows": 64,
        "cols": 128,
        "chain": 2,
        "parallel": 1,
        "hardware_mapping": "regular",
        # Taratura trovata sul campo con i pannelli FM6373 + DP32020B: sono i
        # valori che il pannello vuole davvero, non quelli generici della
        # libreria. Chi installa da zero parte da qui invece di ripercorrere
        # la campagna di prove.
        "slowdown": 5,
        "panel_type": "fm6373",
        "spwm_row_address_type": 1,
        "spwm_scan_rows": 64,
        "spwm_data_layout": 0,
        "spwm_register_config": 2,
        "limit_refresh": 0,
        "pwm_bits": 10,
        # Durata del bit meno significativo. Accorciarla riduce il tempo di
        # un frame intero, quindi alza il refresh senza togliere profondita'.
        "pwm_lsb_nanoseconds": 200,
        # Bit bassi resi con dithering temporale invece che con tempo di
        # accensione: 1 bit di dithering raddoppia il refresh a parita' di
        # profondita' dichiarata.
        "pwm_dither_bits": 1,
        "profile_dir": "/home/gillo/rpi-rgb-led-matrix_pwm_experiment/lib/spwm/registertest/data",
        # Blocco di registro RGB scritto a mano, che scavalca quello del
        # profilo. Vuoto = si usa il profilo, ed e' quello che vuole il 99%
        # dei casi: serve per provare una parola sola alla volta quando
        # nessun profilo del catalogo va bene del tutto.
        "spwm_force_register": "",
        "show_refresh": False,
        # Cartella del fork della libreria matrice. Vuoto = dedotta da
        # profile_dir, che ne e' una sottocartella.
        "library_dir": "",
        # Profilo hardware. Un nome noto applica in blocco tutti i parametri
        # di quel tipo di pannello; "custom" li lascia come sono. Serve a
        # tornare indietro dopo una configurazione sbagliata senza dover
        # ricordare venti numeri.
        "preset": "fm6373_dp32020b",
        # Regolazioni fini del driver S-PWM, applicate come variabili d'ambiente.
        # Vuoto = valore predefinito della libreria.
        "spwm_env": {
            "SPWM_END_OF_FRAME_EXTRA_ROW_CYCLES": "1",
            "SPWM_FRAME_END_SLEEP_US": "300",
        },
    },
    "display": {
        "brightness": 50,
        "night_enabled": False,
        "night_start": "22:00",
        "night_end": "07:00",
        "night_brightness": 15,
        "sleep_enabled": False,
        "sleep_start": "01:00",
        "sleep_end": "06:00",
        "sleep_wake_on_zedmd": True,
    },
    "clock": {
        "time_color": "#ff8c1a",
        "date_color": "#00a0d0",
        "format_24h": True,
        "show_date": True,
        "language": "it",
        "blink_colon": True,
    },
    "mediaplayer": {
        "media_dir": "/srv/dmd/media",
        "min_interval": 20,
        "max_interval": 30,
        "image_duration": 5,
        "video_duration": 8,
        "video_fps": 20,
        "scale_mode": "fit",
        "pixel_art": True,
        # Fascia oraria del Media Player, con la stessa forma di Night mode.
        # Il flag spento — cioe' il predefinito — vuol dire "lavora sempre":
        # chi aggiorna non si accorge di niente.
        "timer_enabled": False,
        "timer_start": "08:00",
        "timer_end": "23:00",
    },
    "banner": {
        "min_interval": 30,
        "max_interval": 60,
        "fps": 30,
        "shuffle": False,
        # Dieci caselle, riempite al primo caricamento da sources.banner.
        "items": [],
    },
    "birthdays": {
        # Con quanto anticipo comincia il promemoria, e ogni quanto ricompare.
        "lead_hours": 48,
        "interval_minutes": 20,
        "seconds": 12,
        "speed": 40,
        "color": "#ff40a0",
        "size": "medium",
        "blink": False,
        # Mostra anche l'eta' compiuta, quando l'anno di nascita c'e'.
        "show_age": True,
    },
    "rifiuti": {
        # Il promemoria compare alle 18 della sera prima e sparisce alle 8 del
        # giorno di raccolta: si espone il bidone la sera, e dopo il passaggio
        # ricordarlo ancora sarebbe rumore. Per le attivita' comunali la fine
        # e' quella del divieto, che ogni comune fissa a modo suo.
        "ora_avviso": 18,
        "ora_fine": 8,
        # Le frazioni che quasi ogni comune ha. Nascono senza giorni: finche'
        # non se ne spunta almeno uno la voce non compare da nessuna parte, e
        # un pannello che ricorda raccolte inventate sarebbe peggio di niente.
        "voci": [
            {"nome": "Carta", "colore": "#ffffff", "tipo": "rifiuto",
             "giorni": [], "cadenza": "settimanale", "riferimento": "",
             "attiva": True, "ora_inizio": 0, "ora_fine": 6},
            {"nome": "Plastica", "colore": "#2060ff", "tipo": "rifiuto",
             "giorni": [], "cadenza": "settimanale", "riferimento": "",
             "attiva": True, "ora_inizio": 0, "ora_fine": 6},
            {"nome": "Vetro", "colore": "#ff8c1a", "tipo": "rifiuto",
             "giorni": [], "cadenza": "settimanale", "riferimento": "",
             "attiva": True, "ora_inizio": 0, "ora_fine": 6},
            {"nome": "Umido", "colore": "#20c040", "tipo": "rifiuto",
             "giorni": [], "cadenza": "settimanale", "riferimento": "",
             "attiva": True, "ora_inizio": 0, "ora_fine": 6},
            {"nome": "Secco", "colore": "#c07830", "tipo": "rifiuto",
             "giorni": [], "cadenza": "settimanale", "riferimento": "",
             "attiva": True, "ora_inizio": 0, "ora_fine": 6},
            {"nome": "Sosta", "colore": "#ff2020", "tipo": "attivita",
             "giorni": [], "cadenza": "settimanale", "riferimento": "",
             "attiva": True, "ora_inizio": 0, "ora_fine": 6},
        ],
    },
    "scadenze": {
        # Soglie del semaforo, in giorni. Sopra la verde il semaforo resta
        # spento: una scadenza fra un mese non e' una notizia, e un pannello
        # che segnala sempre qualcosa non segnala piu' niente.
        "soglia_verde": 10,
        "soglia_giallo": 7,
        "soglia_rosso": 3,
        # Mostra le tre lampade anche quando sono tutte spente. Spento: il
        # pannello resta pulito quando non c'e' niente in scadenza.
        "semaforo_sempre": False,
        # Segnaposto della migrazione 4.1: dice che l'interruttore del
        # servizio e' stato deciso una volta, cosi' chi lo spegne lo trova
        # ancora spento al prossimo aggiornamento.
        "servizio_scelto": False,
        # L'avviso periodico sul pannello, con la stessa forma di quello del
        # radar: ogni quanto compare, e quanto resta.
        "interval_minutes": 20,
        "seconds": 10,
        "speed": 40,
    },
    # I giochi scritti per il pannello. Non sono un servizio e non compaiono
    # fra gli interruttori: sono una partita che comincia e finisce, come Doom
    # dalla 3.2. Qui stanno solo i comandi e i record.
    "giochi": {
        "keyboard": True,
        "keyboard_device": "",
        # Come per Doom: un tasto del cabinato non fa cominciare una partita a
        # meno che non lo si chieda, Options sul pad si'.
        "keyboard_starts": False,
        "joystick": True,
        "joystick_device": "",
        "joystick_starts": True,
        # Dopo quanti secondi senza comandi la partita si chiude da sola e il
        # pannello torna alle sorgenti. Zero per non chiuderla mai.
        "session_timeout": 180,
        "ultimo": "breakout",
        "record": {},
        # Il tasto Start del cabinato scorre i giochi: premuto una volta si
        # gioca, premuto ancora si passa al successivo. I codici sono quelli
        # di una tastiera normale (invio, escape) ma su una pulsantiera da
        # flipper sono altri, e si imparano dalla pagina premendo il pulsante.
        "tasto_ciclo": 28,
        "tasto_esci": 1,
        # Doom nel giro del tasto Start. **Acceso**: dalla 3.8.2 il pad non
        # apre piu' Doom da solo, quindi il giro e' l'unica strada che resta
        # dal cabinato, e nascere spenta la rendeva irraggiungibile. Non c'e'
        # il rischio di finirci dentro per sbaglio con un Doom non preparato:
        # senza un WAD valido Doom non entra proprio nel giro.
        "ciclo_doom": True,
        # E il Game Boy, alle stesse condizioni: entra nel giro solo se PyBoy
        # e' installato e la cartuccia scelta e' valida, quindi una casella su
        # cui Start non fa niente non puo' esistere.
        "ciclo_gameboy": True,
        # Marca che la scelta l'ha fatta una persona: serve solo alla
        # migrazione, per non sovrascrivere due volte una decisione altrui.
        "ciclo_scelto": False,
    },
    "doom": {
        # Il binario lo compila doom/setup_doom.sh: non arriva gia' fatto
        # perche' i sorgenti di doomgeneric sono GPL2 e questo progetto e'
        # GPLv3 (vedi doom/setup_doom.sh).
        "binary": "/var/lib/dmd/doom/doom-dmd",
        "wad": "/srv/dmd/doom/freedoom1.wad",
        # Doom scrive configurazione e salvataggi nella cartella di lavoro:
        # fuori da /opt/dmd, che deve restare uguale alle sue impronte.
        "work_dir": "/var/lib/dmd/doom/stato",
        # La fascia ritagliata dai 200 righe di Doom. Doom e' 1,6:1 e il
        # pannello e' 4:1: schiacciare tutto renderebbe un nemico alto otto
        # pixel. La taratura vera si fa guardando il pannello.
        "band_top": 36,
        "band_height": 96,
        # Sotto 1 schiarisce, sopra 1 scurisce. Trovato sul pannello vero:
        # schiarire sbiancava e rendeva illeggibili i menu.
        "gamma": 1.15,
        # Tastiera USB collegata al Pi. Vuoto = tutte quelle che trova.
        "keyboard": True,
        "keyboard_device": "",
        # Se un tasto sul cabinato puo' *far cominciare* una partita. Spento:
        # il DMD sta in mezzo a un flipper, e un tasto sfiorato per caso non
        # deve portarsi via il pannello a meta' partita. A sessione aperta la
        # tastiera comanda comunque il gioco.
        "keyboard_starts": False,
        # Joystick: PS4 e compatibili, o un pad da PC. Sotto Linux sono
        # dispositivi di /dev/input come le tastiere, quindi si leggono con lo
        # stesso codice. Qui l'avvio della partita e' **acceso**: un pulsante
        # preciso su un pad che si tiene in mano non si preme per sbaglio.
        "joystick": True,
        "joystick_device": "",
        "joystick_starts": True,
        # Dopo quanti secondi senza comandi la partita si chiude da sola e i
        # servizi riprendono. Zero = mai.
        "session_timeout": 180,
        # Difficolta' (1-5) e livello da cui parte una partita.
        "skill": 3,
        "start_map": "1 1",
    },

    "gameboy": {
        # L'emulatore gira come processo separato: qui c'e' il programma che
        # lo ospita, non una libreria da importare. Vedi gb/gb_dmd.py.
        "host": "/opt/dmd/gb/gb_dmd.py",
        # Condivisione SMB dove finiscono le ROM. La crea gb/setup_gb.sh.
        "rom_dir": "/srv/dmd/rom",
        # Nome con cui la condivisione compare in rete: \\<ip>\dmd-rom.
        "share": "dmd-rom",
        # L'ultima cartuccia scelta: si riapre quella, senza doverla ricercare.
        "rom": "",
        # Sotto 1 schiarisce, sopra 1 scurisce. Stessa convenzione di Doom.
        "gamma": 1.0,
        # Percentuale di righe tolte sopra e sotto alla sorgente. A 0 lo
        # schermo Game Boy sta in 71 pixel al centro del pannello; salendo
        # perde cielo e terreno ma diventa piu' largo, fino a riempirlo.
        "overscan": 0,
        # Di quante righe spostare la finestra visibile dentro lo schermo del
        # Game Boy: negativo verso l'alto, positivo verso il basso. L'overscan
        # taglia simmetrico, ma i giochi non sono simmetrici — il punteggio
        # sta in alto, la barra della vita in basso.
        "spostamento": 0,
        # I quattro livelli dello schermo. Un nome dall'elenco di
        # sources/gameboy.py, oppure "personalizzata" e i colori qui sotto.
        "palette": "verde",
        "palette_custom": ["#e0f8d0", "#88c070", "#346856", "#081820"],
        # Fotogrammi al secondo mandati al pannello. Il Game Boy ne fa 59,7:
        # trenta bastano all'occhio e dimezzano il traffico sulla pipe.
        "fps": 30,
        "keyboard": True,
        "keyboard_device": "",
        # Se un tasto della tastiera puo' *far cominciare* una partita.
        # Spento come in Doom: dal pad non si apre mai (vedi sources/gameboy.py).
        "keyboard_starts": False,
        "joystick": True,
        "joystick_device": "",
        # Dopo quanti secondi senza comandi la sessione si chiude da sola.
        # Piu' lungo di Doom: a un gioco di ruolo si sta fermi a leggere.
        "session_timeout": 300,
    },

    "air_radar": {
        # Nessuna posizione preimpostata: va indicata dall'utente nella web UI.
        # Il servizio non interroga nulla finche' le coordinate sono a zero.
        "latitude": 0.0,
        "longitude": 0.0,
        "radius_km": 3.0,
        "provider": "adsb.fi",
        "poll_interval": 30,
        "display_seconds": 10,
        "cooldown": 600,
        "max_altitude_ft": 0,
        "log_route": True,
        "fields": ["route", "type", "altitude", "speed", "distance"],
        "log_enabled": True,
        "log_path": "/var/lib/dmd/flights.csv",
        "callsign_color": "#00d0ff",
        "info_color": "#ff8c1a",
        # Colore della rotta, che ora ha una riga sua al centro. Vuoto =
        # segue il colore dei dettagli: chi non tocca nulla non vede
        # cambiare niente.
        "route_color": "",
        # Che fare quando i campi scelti non stanno su una riga sola:
        #   crop   la riga viene accorciata buttando via campi (com'era)
        #   pages  i campi si alternano a gruppi, senza perderne nessuno
        #   scroll la riga scorre da destra a sinistra
        # Unita' di misura dei parametri di volo. I dati arrivano sempre in
        # piedi e nodi: la conversione e' solo per la lettura.
        "unit_altitude": "ft",     # ft | m
        "unit_speed": "kt",        # kt | kmh | mph
        "unit_distance": "km",     # km | mi | nm
        "overflow": "pages",
        "page_seconds": 3,
        "scroll_speed": 40,
        "scroll_fps": 30,
    },
    "mqtt": {
        # Predefinito: un Mosquitto sul Raspberry stesso. Cosi' la funzione
        # lavora senza Home Assistant. Chi ha gia' un broker sotto Home
        # Assistant mette qui quell'indirizzo e ottiene le due cose insieme.
        "enabled": False,
        "host": "127.0.0.1",
        "port": 1883,
        "username": "",
        "password": "",
        "client_id": "dmd",
        "base_topic": "dmd",
        # Topic su cui shairport-sync pubblica i metadati AirPlay.
        "shairport_topic": "shairport",
        # Topic facoltativo su cui qualsiasi altra cosa (tipicamente
        # un'automazione di Home Assistant) puo' scrivere un JSON con il
        # brano corrente. Vuoto = non si ascolta nulla.
        "external_topic": "dmd/external/nowplaying",
        # Entita' create automaticamente in Home Assistant.
        "discovery": True,
        "discovery_prefix": "homeassistant",
        "node_id": "dmd",
        "device_name": "kWGillo DMD Server",
    },
    "nowplaying": {
        # Quanto resta a schermo un brano in pausa prima di lasciare il posto.
        "hold_seconds": 90,
        # Per quanti secondi l'orologio del brano continua ad avanzare senza
        # ricevere nulla. E' un fondo di sicurezza per sorgenti che non
        # annunciano la pausa: durante la riproduzione normale il silenzio di
        # decine di secondi e' normale, quindi il valore va tenuto largo.
        "advance_timeout": 600,
        "title_color": "#ffffff",
        "artist_color": "#00ffff",
        "album_color": "#0000ff",
        "bar_color": "#ffff00",
        # Ogni componente portata a 0 o 255: restano gli otto colori pieni,
        # gli unici che su questo pannello non producono sfarfallio.
        "safe_colors": True,
    },
    "spotify": {
        # Copre la musica che non passa da AirPlay: Spotify Connect verso
        # casse vere, il computer, un Echo. I token non stanno qui ma in
        # /var/lib/dmd/spotify.json, per non finire in un export condiviso.
        "enabled": False,
        "client_id": "",
        "redirect_uri": "http://127.0.0.1:8080/api/spotify/callback",
        "poll_interval": 8,
    },
    "google": {
        # Google Calendar in sola lettura. I token non stanno qui ma in
        # /var/lib/dmd/google.json, per non finire in un export condiviso; il
        # segreto del client viene tolto dall'esportazione come la password
        # del broker MQTT.
        "client_id": "",
        "client_secret": "",
        "redirect_uri": "http://localhost:8080/api/google/callback",
        # Quanti giorni prima l'appuntamento comincia a comparire. Tre: sotto,
        # il pannello mostrerebbe la fine del mese, che non e' una notizia.
        "giorni": 3,
        # Ogni quanto si chiede a Google, in minuti. Un calendario non cambia
        # trenta volte al secondo.
        "poll_minutes": 15,
        "max_eventi": 10,
        # L'avviso periodico sul pannello, con la stessa forma di quello delle
        # scadenze: ogni quanto compare, quanto resta, quanto scorre.
        "interval_minutes": 20,
        "seconds": 10,
        "speed": 40,
    },
    "time": {
        "ntp_server": "pool.ntp.org",
        "timezone": "Europe/Rome",
        "dst_auto": True,
        "utc_offset": 1,
    },
    "web": {
        "port": 8080,
        # Lingua dell'interfaccia: "it", "en", oppure vuoto per lasciar
        # decidere al browser tramite Accept-Language. Non ha effetto sul
        # testo mostrato sul pannello, che segue clock.language.
        "language": "",
    },
    "ota": {
        "repo": "kWGillo/zedmd-pi",
        "branch": "main",
        "auto_check": True,
        "check_interval_hours": 24,
    },
    "services": {
        "zedmd": True,
        "clock": True,
        "mediaplayer": False,
        "banner": False,
        "nowplaying": False,
        "birthdays": False,
        # Acceso di suo: senza scadenze inserite non disegna niente, quindi
        # non ruba spazio a nessuno, e chi inserisce una scadenza si aspetta
        # di vederla senza dover accendere un secondo interruttore.
        "scadenze": True,
        # Spento di suo: finche' non si collega un account Google non c'e'
        # niente da mostrare, e un interruttore acceso su un servizio muto
        # fa credere che qualcosa non funzioni.
        "calendario": False,
        "status_player": False,
        "air_radar": False,
        # Spento di suo, e non e' prudenza formale: e' una telecamera accesa
        # in soggiorno. Si accende quando qualcuno decide di accenderla.
        "webcam": False,
    },
    "webcam": {
        # Vuoto = la prima telecamera collegata. Si scrive un /dev/videoN
        # solo quando ce n'e' piu' d'una e si vuole scegliere.
        "device": "",
        # Quanto si chiede alla telecamera, non quanto si mostra.
        "capture_width": 640,
        "capture_height": 480,
        # Dieci al secondo, e non e' un filtro dopo la cattura: e' cio' che si
        # chiede alla telecamera di **produrre**. I fotogrammi in piu' non
        # esistono, invece di essere prodotti, trasportati sull'USB e poi
        # buttati. Scartare dopo risparmia CPU; non chiedere risparmia anche
        # il bus, che e' quello che si vede come righe chiare sul pannello.
        "fps": 10,
        # colori | gameboy | grigi
        "stile": "colori",
        # Livelli **per canale** dello stile a colori: i colori sono il cubo,
        # cioe' livelli**3. Due danno gli otto pieni — gli unici che di sicuro
        # non tremano su questo pannello — sei ne danno 216, che e' in pratica
        # la tavolozza da 256 colori di allora. Si parte da due e si sale
        # guardando il pannello: se le tinte intermedie sfarfallano si vede
        # subito, e non c'e' modo di saperlo se non provando.
        "livelli_colore": 2,
        "livelli_grigio": 4,
        # Ci si aspetta di vedersi come allo specchio: alzando la mano destra
        # si alza la mano a destra sul pannello.
        "specchio": True,
        # Un soggiorno di sera esce come una poltiglia grigia stretta fra 40 e
        # 90: senza allargare la gamma, ridotta a otto colori e' un
        # rettangolo nero.
        "contrasto_auto": True,
        "gif_secondi": 3,
        # Sottocartella della libreria media dove finiscono foto e GIF, cosi'
        # il Media Player le rimette sul pannello da solo piu' avanti.
        "cartella": "telecamera",
    },
    "zedmd": {
        "stream_port": 3333,
        "http_port": 80,
        "transport": "TCP",
        "grace_seconds": 60,
        "client_timeout": 10,
        "device_name": "ZeDMD-Pi",
        "firmware_version": "6.0.0",
    },
    "arbiter": {
        "force_source": "auto",
    },
}

_lock = threading.Lock()
_config = None


def _merge(base, override):
    """Fonde ricorsivamente l'override sui default.

    Due direzioni, e la seconda e' costata una taratura intera.

    **Dai default al risultato**: una chiave aggiunta da una versione nuova
    compare anche in una configurazione scritta da una vecchia, con il suo
    valore predefinito. E' il motivo per cui l'aggiornamento via rete puo'
    non eseguire nessuno script di migrazione.

    **Dal file al risultato**: una chiave che sta nel file ma **non** nei
    default va tenuta lo stesso. Prima non era cosi': il risultato si
    costruiva scorrendo solo i default, e tutto il resto spariva senza dire
    niente. La taratura scriveva `panel.autotune` nel file, il servizio
    ripartiva, il caricamento lo buttava via, e il primo salvataggio lo
    cancellava anche dal disco — con il profilo che non compariva mai nel
    menu e nessun errore da nessuna parte.

    Buttare una chiave sconosciuta e' sempre stata una decisione sbagliata:
    di roba scritta da una versione **piu' nuova**, o da una funzione che
    scrive fuori dai default, non si sa niente — e non sapere niente non
    autorizza a cancellare.
    """
    override = override or {}
    out = {}
    for key, value in base.items():
        if isinstance(value, dict):
            sotto = override.get(key)
            out[key] = _merge(value, sotto if isinstance(sotto, dict) else {})
        else:
            out[key] = override.get(key, value)
    for key, value in override.items():
        if key not in out:
            out[key] = value
    return out


def _migrate(raw):
    """Adegua configurazioni scritte da versioni precedenti."""
    services = raw.setdefault("services", {})
    # 1.0 aveva un unico servizio "mediaplayer_clock".
    if "mediaplayer_clock" in services:
        legacy = bool(services.pop("mediaplayer_clock"))
        services.setdefault("clock", legacy)
        services.setdefault("mediaplayer", False)
    if raw.get("arbiter", {}).get("force_source") == "mediaplayer_clock":
        raw["arbiter"]["force_source"] = "clock"
    if raw.get("web", {}).get("port") == 80:
        raw["web"]["port"] = 8080
    # 4.10 chiamava "otto" lo stile a colori della telecamera, perche' otto
    # erano. Adesso i livelli per canale si scelgono, quindi il nome sarebbe
    # diventato una bugia: il valore vecchio si traduce, e chi lo aveva si
    # ritrova con gli stessi otto colori di prima.
    if raw.get("webcam", {}).get("stile") == "otto":
        raw["webcam"]["stile"] = "colori"
        raw["webcam"].setdefault("livelli_colore", 2)

    # 1.9: le dieci caselle del Rolling banner devono esserci sempre, anche
    # in una configurazione salvata prima che la funzione esistesse.
    from sources.banner import normalize_list
    banner = raw.setdefault("banner", {})
    banner["items"] = normalize_list(banner.get("items"))

    # 1.10: il servizio Now Playing deve comparire fra i toggle anche in una
    # configurazione salvata prima che esistesse, altrimenti la pagina Servizi
    # non lo mostra e non lo si puo' accendere.
    services.setdefault("nowplaying", False)

    # 4.1: la 4.0 scriveva services.scadenze = False perche' l'interruttore
    # non c'era ancora in pagina, ma il semaforo si disegnava lo stesso. Ora
    # l'interruttore comanda anche il semaforo: lasciare quel False vorrebbe
    # dire spegnere, aggiornando, una cosa che l'utente sta gia' vedendo.
    if not raw.get("scadenze", {}).get("servizio_scelto"):
        services["scadenze"] = True
        raw.setdefault("scadenze", {})["servizio_scelto"] = True

    # 3.8.3: fino alla 3.8.2 Doom si apriva premendo Options, perche' era il
    # suo lettore ad aprirlo. Quella strada e' stata tolta — Options ora scorre
    # i giochi — e chi aggiorna con "Doom nel giro" spento se lo ritroverebbe
    # irraggiungibile dal cabinato. Lo si mette nel giro una volta sola; da li'
    # in poi la casella e' sua e non la tocca piu' nessuno.
    giochi = raw.setdefault("giochi", {})
    if not giochi.get("ciclo_scelto"):
        giochi["ciclo_doom"] = True
        giochi["ciclo_scelto"] = True

    # 3.1: i WAD sono passati a una cartella condivisa in rete, e il percorso
    # salvato punta ancora alla vecchia posizione.
    #
    # Questa migrazione stava in update.sh, ed e' stato un errore: **l'OTA non
    # esegue update.sh**. Copia i file e riavvia il servizio, e basta. Le
    # aggiunte di chiavi nuove sopravvivono lo stesso, perche' `_merge` fonde
    # i default a ogni caricamento — ma una *trasformazione di valore* come
    # questa no, e chi aggiorna via rete, cioe' tutti, restava con un WAD che
    # puntava a un file spostato. Doom si rifiutava di partire e sembrava
    # rotto. Le trasformazioni vanno qui, che e' l'unico punto attraversato da
    # qualunque strada di aggiornamento.
    doom = raw.setdefault("doom", {})

    # 3.3: il gamma predefinito passa da 0.70 a 1.15. Si corregge **solo** chi
    # ha ancora il vecchio predefinito esatto: se qualcuno ha tarato il proprio
    # pannello, quel numero vale piu' del nostro e non si tocca.
    if doom.get("gamma") == 0.70:
        doom["gamma"] = 1.15

    wad = doom.get("wad") or ""
    if wad and not os.path.exists(wad):
        candidato = os.path.join("/srv/dmd/doom", os.path.basename(wad))
        if os.path.exists(candidato):
            doom["wad"] = candidato
    return raw


def load():
    global _config
    with _lock:
        if _config is not None:
            return _config
        raw = {}
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH) as handle:
                    raw = json.load(handle)
            except (OSError, ValueError):
                raw = {}
        _config = _merge(DEFAULTS, _migrate(raw))
        return _config


def get():
    return load()


def _apply_in_place(target, source):
    """Riversa `source` dentro `target` senza cambiare l'identita' dei dizionari.

    Le sorgenti tengono un riferimento alla configurazione e ai suoi rami
    (`self.cfg`, `cfg["air_radar"]`, ...). Sostituire il dizionario con uno
    nuovo lascerebbe meta' del programma a guardare quello vecchio: qui si
    aggiorna il contenuto, non il contenitore.
    """
    for key in list(target):
        if key not in source:
            del target[key]
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _apply_in_place(target[key], value)
        else:
            target[key] = value


KNOWN_SECTIONS = set(DEFAULTS)


def looks_like_config(raw):
    """Un file di configurazione plausibile, non un JSON qualsiasi."""
    if not isinstance(raw, dict):
        return False
    return bool(KNOWN_SECTIONS & set(raw))


def replace(raw):
    """Sostituisce la configurazione con quella indicata e la salva.

    Il contenuto passa dagli stessi `_migrate` e `_merge` del caricamento
    normale: un file salvato da una versione precedente viene adeguato, e le
    chiavi che non conosciamo vengono ignorate invece di far danni.
    """
    if not looks_like_config(raw):
        raise ValueError("il file non contiene una configurazione del DMD")
    merged = _merge(DEFAULTS, _migrate(dict(raw)))
    with _lock:
        if _config is None:
            raise RuntimeError("configurazione non ancora caricata")
        _apply_in_place(_config, merged)
    save()
    return _config


def snapshot(include_position=True):
    """Copia della configurazione da esportare.

    Senza `include_position` le coordinate del radar tornano a zero: un file
    di configurazione condiviso o allegato a una segnalazione non deve
    portarsi dietro l'indirizzo di casa.

    La password del broker MQTT viene tolta sempre, senza opzione. Un file di
    configurazione gira: finisce in un backup, in un allegato, in una
    segnalazione. Chi lo reimporta riscrive la password una volta sola; se
    invece fosse dentro, basterebbe una disattenzione per regalarla. I token
    di Spotify non compaiono qui affatto: vivono in un file loro.
    """
    import copy
    data = copy.deepcopy(load())
    if not include_position:
        data["air_radar"]["latitude"] = 0.0
        data["air_radar"]["longitude"] = 0.0
    if isinstance(data.get("mqtt"), dict):
        data["mqtt"]["password"] = ""
    # Stesso ragionamento per il segreto del client Google: e' una credenziale
    # dell'applicazione, e chi reimporta la riscrive una volta sola.
    if isinstance(data.get("google"), dict):
        data["google"]["client_secret"] = ""
    return data


def save():
    with _lock:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        tmp = CONFIG_PATH + ".tmp"
        with open(tmp, "w") as handle:
            json.dump(_config, handle, indent=2)
        os.replace(tmp, CONFIG_PATH)
