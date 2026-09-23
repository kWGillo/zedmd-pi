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
        # I parametri dei pannelli **classici**, quelli a indirizzamento
        # diretto che girano con la libreria standard di hzeller. Vuoto =
        # predefinito della libreria, ed e' cosi' per tutti finche' qualcuno
        # non ha un pannello che li vuole: i profili S-PWM non li usano.
        "row_address_type": "",
        "multiplexing": "",
        "scan_mode": "",
        "pixel_mapper": "",
        "led_rgb_sequence": "",
        "disable_hardware_pulsing": "",
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
        # E il volume, con la stessa logica della luminosita': di notte il DMD
        # abbassa la voce insieme alla luce. Zero = muto, ed e' il predefinito
        # perche' un avviso a volume pieno alle tre di notte non lo vuole
        # nessuno -- vale solo se il night mode e' acceso, quindi chi non lo
        # usa non se ne accorge.
        #
        # Vale per quello che il DMD dice **di sua iniziativa**: un aereo, un
        # compleanno, una notifica. Non per una partita, che e' una cosa che
        # stai facendo tu adesso -- la stessa eccezione che Sleep mode fa gia'
        # per chi tiene il pannello occupato.
        "night_volume": 0.0,
        "sleep_enabled": False,
        "sleep_start": "01:00",
        "sleep_end": "06:00",
        "sleep_wake_on_zedmd": True,
        # E lo stesso per una partita aperta a mano. Sono due cose diverse:
        # i frame da Batocera arrivano da soli, una partita la apre qualcuno
        # che e' li' davanti -- e spegnergli il pannello in faccia perche'
        # sono le due di notte e' proprio il caso in cui lo Sleep sbaglia.
        "sleep_wake_on_giochi": True,
        # Spegnimento a mano del pannello. Non e' Sleep mode: quello segue un
        # orario, questo e' una decisione presa adesso e che dura finche' non
        # si cambia idea -- anche dopo un riavvio, che e' voluto: uno
        # spegnimento che si annulla da solo aggiornando il servizio non
        # sarebbe uno spegnimento. Il Raspberry resta acceso e continua a fare
        # tutto -- il radar registra, le notifiche arrivano, la pagina web
        # risponde -- e' solo il vetro a essere nero.
        "off": False,
    },
    "clock": {
        "time_color": "#ff8c1a",
        "date_color": "#00a0d0",
        "format_24h": True,
        "show_date": True,
        "language": "it",
        "blink_colon": True,
        # Un colore diverso per le cifre a ogni ora, invece di `time_color`.
        # Spento di serie: chi ha scelto un colore se lo aspetta fermo.
        "colore_casuale": False,
        # Di quanti pixel spostare le cifre in verticale: negativo in alto,
        # positivo in basso. Vale sempre, e con il World Time acceso si somma
        # all'alzata automatica.
        #
        # Esiste perche' la posizione buona non e' la stessa per tutti: la
        # decide l'altezza a cui sta il pannello e da dove lo si guarda, e
        # sono due cose che da qui non si possono sapere.
        #
        # Due e non zero: il centro geometrico non e' il centro che si vede.
        # Un pannello sta su una mensola e lo si guarda **dal basso**, e da
        # li' le cifre centrate sembrano alte. Questi due pixel sono misurati
        # sul pannello vero, non calcolati -- e chi ha un'altra mensola muove
        # il cursore.
        "offset_v": 2,
        # World Time: che ore sono adesso dall'altra parte del mondo. Fino a
        # cinque localita', tre per volta sul pannello, in una banda sotto le
        # cifre -- che per farle stare salgono di tre pixel.
        #
        # Si salva il **fuso IANA** e non un'ora di scarto: «New York = UTC-5»
        # e' sbagliato per meta' dell'anno, e sbagliato in silenzio. Le regole
        # dell'ora legale stanno gia' nel database dei fusi del sistema.
        "world": {
            "enabled": False,
            # Le cinque caselle, riempite al primo caricamento da
            # sources.clock.normalizza_mondo.
            "voci": [],
            # Vuoti = il nome prende il colore della data e l'ora il grigio
            # chiaro. Sono due colori perche' sono due informazioni, e con tre
            # citta' affiancate uno solo si legge come una frase.
            "colore_nome": "",
            "colore_ora": "#c8c8c8",
        },
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
        # La musica di sottofondo dei giochi. Separata dagli effetti: chi
        # gioca la sera tardi vuole spesso gli uni e non l'altra.
        "musica": True,
        # Quanto e' forte il computer di Pongo: facile, normale, difficile.
        "pongo_livello": "normale",
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

    # Dove sta questo DMD. Una posizione sola per tutto il progetto: la usano
    # il radar, i satelliti e il meteo, e finche' e' stata una voce dentro
    # `air_radar` sembrava una preferenza del radar -- chi accendeva i
    # satelliti andava a cercarla nella pagina sbagliata.
    #
    # Nessuna coordinata preimpostata, mai. Il valore vero vive soltanto qui,
    # nella configurazione locale, e non esiste da nessuna parte nel codice
    # distribuito. Zero-zero sta in mezzo all'Atlantico ed e' il modo in cui il
    # progetto dice "nessuno l'ha ancora messa": ogni servizio che ne ha
    # bisogno se ne accorge e tace invece di mostrare il golfo di Guinea.
    "posizione": {
        "latitude": 0.0,
        "longitude": 0.0,
    },

    "air_radar": {
        # Le coordinate **non** stanno piu' qui: vedi `posizione`. Le due
        # chiavi restano, a zero, perche' una configurazione salvata da una
        # versione precedente le contiene e la migrazione le legge da li'.
        "latitude": 0.0,
        "longitude": 0.0,
        "radius_km": 3.0,
        # Quanto guardare **oltre** il raggio, senza mostrarlo. Gli aerei che
        # cadono in questa fascia non vanno sul pannello ne' nel registro: la
        # pagina Radar li elenca con la loro distanza, e la domanda "era
        # fuori dal raggio?" smette di essere un'opinione.
        "margine_km": 2.0,
        "provider": "adsb.fi",
        # Venti secondi, non trenta. Con un raggio di pochi chilometri un
        # aereo di linea attraversa il cerchio in meno di mezzo minuto:
        # interrogare piu' lentamente del transito vuol dire non vederlo mai.
        # Sotto i 15 non si scende comunque — e' un servizio gratuito della
        # comunita'.
        "poll_interval": 20,
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
        # I metadati di AirPlay letti dalla pipe locale di shairport-sync
        # invece che dal broker. E' la strada principale dalla 7.4: i due
        # programmi girano sulla stessa macchina, e farli parlare via rete
        # voleva dire tenere allineati un indirizzo e una password in due file
        # diversi -- che e' esattamente quello che si e' rotto.
        #
        # MQTT resta acceso e continua a funzionare: chi ha gia' tutto
        # configurato non deve toccare niente, e le due strade finiscono nella
        # stessa funzione. Spegnendo questa si torna al comportamento di
        # prima.
        "pipe": True,
        # Vuoto = il percorso predefinito di shairport-sync,
        # /tmp/shairport-sync-metadata. Si scrive qui solo se lo si e'
        # spostato a mano.
        "pipe_percorso": "",
        "title_color": "#ffffff",
        "artist_color": "#00ffff",
        "album_color": "#0000ff",
        "bar_color": "#ffff00",
        # Ogni componente portata a 0 o 255: restano gli otto colori pieni,
        # gli unici che su questo pannello non producono sfarfallio.
        "safe_colors": True,
        # La copertina del brano. L'indirizzo lo manda la sorgente insieme al
        # titolo: qui si decide solo se scaricarlo e disegnarlo.
        "artwork": True,
        # Dove sta Home Assistant, per gli indirizzi relativi. `entity_picture`
        # e' una strada -- `/api/media_player_proxy/...` -- non un indirizzo
        # intero: senza questo non si sa a chi chiederla. Vuoto vuol dire
        # niente copertine dagli indirizzi relativi, e nessun tentativo di
        # indovinare un host.
        #
        # Non e' una credenziale: quell'indirizzo porta **dentro di se'** un
        # token firmato da Home Assistant, quindi sul Raspberry non resta
        # nessun segreto da custodire. Se un giorno servisse un token vero,
        # questa strada andrebbe riprogettata invece che allargata.
        "artwork_base": "",
        # Il tetto alla larghezza, in pixel. Zero vuol dire meta' pannello.
        # Serve perche' l'altezza e' fissa e la larghezza no: una locandina
        # panoramica alta 64 sarebbe larga centoquaranta e lascerebbe i titoli
        # senza spazio.
        "artwork_larghezza_massima": 0,
        # Livelli di colore per canale, come la Funcam. **Non e' una
        # preferenza estetica**: fino alla 7.2 la copertina non si mostrava
        # affatto, e il motivo scritto nel progetto era che e' fatta quasi solo
        # di mezzi toni, cioe' il contenuto peggiore possibile per un pannello
        # S-PWM -- lo stesso motivo per cui esiste `safe_colors`.
        #
        # Quattro livelli con il disordine di Floyd-Steinberg tengono la
        # copertina riconoscibile togliendo la maggior parte dei mezzi toni.
        # Due danno gli otto colori pieni, quelli che non sfarfallano mai.
        # Zero lascia l'immagine com'e': da provare, non da dare per buono.
        "artwork_livelli": 4,
        # `sempre` come e' sempre stato, oppure `rotazione`: in rotazione il
        # brano prende il pannello una volta ogni `ogni_n_media` foto, per
        # `durata_turno` secondi. Senza Media Player acceso non c'e' niente
        # con cui alternarsi, e la rotazione decade a `sempre`.
        "modo": "sempre",
        "ogni_n_media": 5,
        "durata_turno": 20,
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
        # Il puntino verde nell'angolo in alto a destra dell'orologio quando
        # c'e' una versione nuova. Acceso di serie: il controllo quotidiano
        # esisteva gia' dalla 1.5 e scriveva soltanto una riga di log, cioe'
        # parlava a nessuno. Chi non lo vuole lo spegne qui, e il pannello
        # torna identico a com'era.
        "segnale": True,
    },
    # -------------------------------------------------------------- pulizia
    #
    # Le briciole che i Mac lasciano nelle condivisioni: `.DS_Store` e i file
    # AppleDouble (`._qualcosa`), uno per ogni file copiato. Non fanno danno,
    # ma su una libreria di migliaia di foto raddoppiano il numero di voci che
    # il Raspberry deve elencare a ogni giro.
    "pulizia": {
        "enabled": True,
        # Ogni quante ore. "Di tanto in dopo" e' abbastanza: le briciole si
        # accumulano quando si copia, cioe' di rado.
        "ore": 12,
        # Vuoto = le condivisioni note, prese dalla configurazione. Si
        # riempie solo per aggiungerne altre.
        "cartelle": [],
        # Il tetto per un solo giro: non e' contro i Mac, e' contro un errore
        # nostro. Meglio accorgersene a cinquemila file che a mezza libreria.
        "massimo": 5000,
    },

    # ------------------------------------------------------------ notifiche
    #
    # I messaggi che arrivano da Home Assistant. Il contratto e' piccolo di
    # proposito: un topic, un JSON con testo, livello e secondi. La politica
    # -- quando parlare, quando tacere, con che parole -- sta di la', dove
    # stanno gia' le automazioni.
    "notifiche": {
        "topic": "dmd/notifica",
        "secondi": 8,
        "velocita": 60,
        "fps": 30,
        "altezza": 0.5,
        # Quante notifiche si accodano prima di buttare via la piu' vecchia.
        # Una notifica di mezz'ora fa non interessa piu' a nessuno.
        "massimo_in_coda": 20,
        # Il colore dei tre livelli. Chi pubblica puo' scavalcarlo con il
        # campo `colore`, ma non deve essere obbligato a saperne niente.
        "colori": {
            "info": "#7ad7ff",
            "avviso": "#ffa000",
            "allarme": "#ff2a20",
        },
    },
    # OnAir: il pannello dice che si sta registrando. Lo stato `in_onda` sta
    # qui e non in memoria perche' deve sopravvivere a un riavvio del
    # servizio, e perche' l'interruttore di Home Assistant deve ritrovarlo
    # dov'era. Home Assistant lo riafferma comunque appena il DMD torna
    # disponibile, cosi' una porta aperta nel frattempo non lascia acceso un
    # ON AIR falso.
    "onair": {
        "testo": "ON AIR",
        "colore_sfondo": "#c00000",
        "colore_testo": "#000000",
        "ogni_n_media": 2,
        "al_massimo_dopo": 180,
        "secondi": 0,
        "in_onda": False,
    },

    # ------------------------------------------------------------- satelliti
    #
    # I passaggi visibili della Stazione Spaziale. Le coordinate non stanno
    # qui: sono quelle dell'Air Radar, perche' la casa e' una sola e due
    # posizioni che possono divergere sono due posizioni sbagliate.
    "satelliti": {
        # I gruppi di CelesTrak da scaricare. Solo le stazioni: i "cento piu'
        # luminosi" sono per due terzi stadi di razzo con sigle illeggibili.
        "gruppi": ["stazioni"],
        # Sopra quanti gradi dall'orizzonte vale la pena annunciare.
        #
        # Erano dieci, ed era la soglia sbagliata presa dal posto sbagliato:
        # dieci gradi e' la regola dei radioamatori, sotto cui l'atmosfera
        # attenua il segnale. Ma qui il ricevitore sono gli occhi di qualcuno
        # in terrazzo, e davanti a quegli occhi ci sono case.
        #
        # I conti, per un oggetto a 420 km: a dieci gradi e' a 1390 km di
        # distanza al suolo, la distanza obliqua passa da 420 a 1500 km, ed e'
        # **2,8 magnitudini piu' fioco** -- un fattore tredici. La ISS allo
        # zenit e' come Venere; a dieci gradi e' una stellina, quando non e'
        # dietro un tetto.
        #
        # Trenta gradi e' un terzo del cielo: bisogna alzare il naso, non
        # guardare fra i comignoli, e si perde solo 1,3 magnitudini. Costa
        # circa meta' degli annunci -- la frazione di passaggi che sopravvive a
        # una soglia e' la larghezza della fascia di tracce al suolo che la
        # produce, e da 10 a 30 gradi quella fascia passa da 1390 a 630 km.
        # Piu' su non si poteva andare: a sessanta gradi resterebbe il 16%
        # degli annunci, e con due soli oggetti noti il servizio smetterebbe
        # di esistere.
        "elevazione_minima": 30.0,
        # Quanto prima avvisare, e ogni quanto ricordarlo. Un passaggio dura
        # dai due ai sette minuti: annunciarlo mentre succede vuol dire
        # arrivare in terrazzo a cose finite.
        "preavviso_minuti": 10,
        "cadenza_minuti": 5,
        # Quanto resta a schermo un promemoria. Non e' una sorgente che occupa
        # il pannello per un quarto d'ora: sono due lampi brevi.
        "durata_avviso_secondi": 20,
        "finestra_ore": 24,
        "ricalcola_minuti": 360,
        "cartella_tle": "/var/lib/dmd/tle",
        # Registro dei passaggi, come quello dei voli. Ci finiscono anche i
        # passaggi **non** visibili, con la colonna che lo dice e l'altezza
        # del Sole che spiega perche': e' l'unico modo per rispondere a
        # "stasera il pannello non ha detto niente".
        "log_enabled": True,
        "log_path": "/var/lib/dmd/satelliti.csv",
        # Mostrare anche i passaggi che non si vedono. Non e' riempitivo: sono
        # quattro al giorno contro uno, e sul pannello arrivano in
        # grigio-azzurro, senza preavviso e senza lampeggio -- il colore dice
        # da solo che non e' un invito a uscire. Si vede l'arco, che e' la
        # parte bella, e la riga sotto dice perche' non si vede.
        "mostra_non_visibili": True,
        "durata_spento_secondi": 25,
        # Se acceso mostra anche gli oggetti di cui **non** conosciamo la
        # luminosita': si vedranno annunci per CubeSat invisibili a occhio
        # nudo. Sta qui per chi vuole sperimentare, non per l'uso normale.
        "tutti_gli_oggetti": False,
        # Quanto in alto puo' stare il Sole perche' il pannello mostri ancora i
        # satelliti, in gradi sopra l'orizzonte. A 3 il servizio si apre un
        # quarto d'ora prima del tramonto e si chiude poco dopo l'alba; a 0
        # esattamente al tramonto; a 90 non si chiude mai, che e' com'era prima
        # della 7.2.
        #
        # Non e' -6, la soglia con cui si decide se un passaggio si vede, e la
        # differenza e' il punto: il preavviso scatta dieci minuti prima che il
        # satellite sorga, e in dieci minuti il Sole scende di due o tre gradi.
        # Con il cancello a -6 sparirebbe proprio l'avviso della prima sera.
        "sole_massimo": 3.0,
    },

    # La sveglia. Le voci nascono spente: un orario predefinito che suona da
    # solo il giorno dopo l'aggiornamento sarebbe uno scherzo, non un valore
    # di fabbrica.
    # Le fasce orarie dei servizi, una voce per servizio che ne ha una accesa.
    # Vuoto = nessuno ha fasce, cioe' tutti lavorano sempre: e' il
    # comportamento di sempre, e chi aggiorna non si accorge di niente.
    #
    # Il Media Player non sta qui: la sua fascia esisteva gia' dalla 3.5 sotto
    # `mediaplayer.timer_*` e resta li'. Spostarla avrebbe voluto dire o
    # perdere l'impostazione di chi aggiorna, o tenerne due copie che prima o
    # poi divergono. La pagina Timing le mostra insieme lo stesso: dove un dato
    # e' scritto e' un fatto del programma, non dell'utente.
    "timing": {},
    "sveglia": {
        "colore": "#ff3b30",
        # Mentre squilla, il pulsante fisico e' suo. Vedi
        # `dmdd.Runtime._pulsante_di_turno`: prima il piedino lo apriva solo
        # la telecamera, quindi con la Funcam spenta una sveglia non si
        # poteva zittire col pulsante — e sembrava un guasto di saldatura.
        "pulsante": True,
        # Per quanto suona un timer scaduto. Piu' corta di una sveglia: chi ha
        # messo un timer e' in casa e a pochi metri, non sta dormendo.
        "durata_timer": 90,
        # Il suono del timer. Vuoto: quello della prima sveglia attiva, come
        # fino alla 10.0 -- che era l'unico modo di sceglierlo, e non si
        # sapeva.
        "suono_timer": "",
        # Le durate proposte dalla pagina, in minuti. Un elenco e non un campo
        # libero perche' con le mani bagnate si preme, non si digita -- il
        # campo libero c'e' lo stesso, accanto.
        "timer_rapidi": [3, 5, 10, 15],
        "voci": [
            {"enabled": False, "ora": "07:00", "giorni": [0, 1, 2, 3, 4],
             "suono": "", "etichetta": "", "durata": 120},
            {"enabled": False, "ora": "08:30", "giorni": [5, 6],
             "suono": "", "etichetta": "", "durata": 120},
            {"enabled": False, "ora": "07:00", "giorni": [],
             "suono": "", "etichetta": "", "durata": 120},
            {"enabled": False, "ora": "07:00", "giorni": [],
             "suono": "", "etichetta": "", "durata": 120},
        ],
    },
    "services": {
        "zedmd": True,
        # Acceso di suo, e non e' una contraddizione con le voci spente: qui
        # si dice che il servizio esiste, non che qualcuno debba svegliarsi.
        # Con tutte le voci spente non succede niente, e chi imposta un orario
        # si aspetta che suoni senza dover accendere un secondo interruttore.
        "sveglia": True,
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
        # Spento di suo perche' senza coordinate non ha niente da dire, e le
        # coordinate non le mettiamo noi: le prende da quelle del radar,
        # quando ci sono.
        "satelliti": False,
        # Spento di suo: senza un'automazione in Home Assistant che pubblichi
        # qualcosa, questa sorgente resta muta per sempre. Si accende quando
        # dall'altra parte c'e' qualcuno che parla.
        "notifiche": False,
        # Spento di suo: finche' non c'e' qualcosa che dica «in onda»
        # non ha niente da mostrare, e un interruttore acceso su un
        # servizio muto fa credere che qualcosa non funzioni.
        "onair": False,
        # Il Cielo: acceso di serie. Parla solo di notte, e solo quando il
        # turno con il meteo gli da' lo spazio -- non ha niente da configurare
        # prima di funzionare. Senza posizione mostra comunque la fase.
        "moon": True,
        "inutili": True,
        # Come i satelliti: senza coordinate non ha niente da dire, e le
        # coordinate non le mettiamo noi.
        "meteo": False,
    },
    # Info inutili. Il calendario (santo, nomi, giornata mondiale) e' nei CSV
    # del programma e non chiede niente a nessuno; i personaggi famosi
    # arrivano da Wikipedia e sono l'unica parte che vuole la rete: spenta
    # quella casella, il servizio resta intero, solo piu' corto.
    "inutili": {
        "calendario": True,
        "personaggi": True,
        "morti": True,
        "durata_slide": 6,
    },
    "moon": {
        # Quanti secondi sta a schermo una schermata del servizio Moon.
        "durata": 15,
    },
    "meteo": {
        # L'ora del bollettino del mattino, quello che racconta la giornata.
        # Sette e' l'ora della colazione; chi si alza alle cinque lo sposta.
        "ora_bollettino": 7,
        # Ogni quante ore si **chiedono** i dati a Open-Meteo. Quattro bastano
        # e avanzano: una previsione non cambia ogni venti minuti, e ogni
        # chiamata in piu' e' traffico verso un servizio gratuito che non
        # chiede niente in cambio.
        "ogni_ore": 4,
        # Ogni quanti minuti il meteo **prende il pannello**, con i dati che
        # ha gia' in mano. E' una cosa diversa dalla riga qui sopra, e fino
        # alla 7.4 erano la stessa: con il solo `ogni_ore` il meteo compariva
        # sei volte al giorno, un minuto e mezzo su ventiquattro ore, cioe'
        # praticamente mai. Adesso gira come il Rolling Banner.
        #
        # Zero spegne il giro e lascia solo il bollettino del mattino, gli
        # aggiornamenti a ogni chiamata e le allerte: e' il comportamento
        # della 7.4, per chi lo preferiva.
        #
        # Dalla 8.3 sono dieci e non venti. Venti erano stati scelti quando il
        # turno si bruciava anche senza mostrarsi: con quel difetto le
        # comparse vere erano 48 al giorno invece delle 72 previste, cioe' una
        # ogni mezz'ora. Corretto quello, dieci minuti danno circa 139
        # comparse al giorno e il due per cento del tempo del pannello.
        "ogni_minuti": 10,
        # La fascia del mattino: il meteo compare molto piu' spesso e mostra
        # il bollettino della giornata invece della temperatura del momento.
        # Dalle 6 alle 9, con i soli dieci minuti qui sopra, il meteo stava a
        # schermo il 2% del tempo: chi fa colazione davanti al pannello ne
        # vedeva uno se capitava. Fuori dalla fascia non cambia niente.
        "mattino": True,
        "mattino_inizio": "06:30",
        "mattino_fine": "09:00",
        "mattino_ogni_minuti": 2,
        "durata_bollettino": 22,
        "durata_aggiornamento": 12,
        "durata_allerta": 25,
        # Le allerte di MeteoAlarm. Il feed copre un paese intero e divide per
        # regione: senza regione scelta non si mostra **niente**, e non tutto.
        # Far comparire l'allerta della Sicilia a chi sta in Piemonte non e'
        # un'approssimazione, e' un allarme falso.
        "allerte": True,
        "regione": "",
        "paese": "italy",
        # "C" o "F". Le previsioni si chiedono **sempre** in Celsius e si
        # convertono al momento di scrivere: cosi' cambiare unita' non
        # invalida la previsione gia' scaricata, e su MQTT esce comunque
        # Celsius, che e' quello che Home Assistant sa riconvertire da solo.
        "unita": "C",
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
        # Il pulsante fisico. Spento di suo: senza un pulsante saldato
        # davvero, accenderlo vorrebbe dire una telecamera che non si accende
        # piu' e nessun modo evidente di capire perche'.
        "pulsante": {
            "enabled": False,
            # GPIO 25, che sul connettore a 40 piedini e' il piedino 22 e ha
            # una massa accanto, al 20. E' anche il piedino che Adafruit usa
            # per un pulsante su questa stessa scheda. I piedini possibili
            # sono pochi: quasi tutti li prende la matrice, e sceglierne uno
            # occupato vorrebbe dire un pannello che smette di funzionare.
            "gpio": 25,
        },
        # Sottocartella della libreria media dove finiscono foto e GIF, cosi'
        # il Media Player le rimette sul pannello da solo piu' avanti.
        "cartella": "telecamera",
    },
    "audio": {
        # Spento di suo: senza una scheda USB collegata non c'e' niente da
        # accendere, e l'audio interno del Raspberry con questo pannello non
        # si puo' usare — la libreria della matrice si prende lo stesso
        # blocco PWM, e infatti l'installazione lo disattiva.
        "enabled": False,
        # Vuoto = l'ultima scheda comparsa, che con una chiavetta USB appena
        # infilata e' quasi sempre quella giusta. Si scrive un `plughw:N,0`
        # per sceglierne una in particolare.
        "device": "",
        "volume": 0.7,
        # Il volume di una partita, che e' una cosa diversa dal volume del
        # DMD e per mesi non lo e' stata. `volume` lo si regola pensando agli
        # avvisi: il pannello parla da solo, magari di sera, e chi lo tiene
        # in casa lo mette basso — sul DMD di chi scrive era a 0,05. Ma gli
        # effetti di un gioco non sono un avviso: sono la risposta a un tasto
        # che hai appena premuto, durano cinquanta millesimi, e l'orecchio
        # integra il volume su due decimi di secondo — un suono cosi' corto
        # si sente parecchio piu' piano di uno lungo con la stessa ampiezza.
        # A 0,05 sparivano, mentre Doom e il Game Boy — che scrivono sulla
        # scheda per conto loro, a fondo scala — si sentivano benissimo. Non
        # era un difetto del mixer: era che i giochi usavano il volume di
        # qualcun altro.
        "volume_giochi": 0.9,
        # L'ampiezza del sottofondo che tiene sveglia la scheda durante una
        # partita. Vedi `suoni.Mixer._blocco_muto`: molti convertitori USB si
        # automutano quando ricevono zero digitale esatto, e la rampa di
        # risveglio si mangia un effetto corto intero. 32 su 32767 sono
        # −60 dBFS, cioe' sotto il fruscio di qualunque stanza. Zero disattiva
        # il sottofondo e riporta il comportamento di prima.
        "sottofondo": 32,
        # Il file di avviso per ogni servizio, come percorso dentro la
        # libreria media. Vuoto = quel servizio resta muto.
        "servizi": {},
        # Gli effetti dei giochi scritti per il pannello. Stanno accanto al
        # programma, non fra i contenuti dell'utente.
        "giochi": True,
        # L'audio di Doom. Voce a parte perche' e' l'unico suono continuo, ed
        # e' quindi l'unico che si paghi davvero in traffico sul bus.
        "doom": True,
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

    # 7.0: la posizione esce da `air_radar` e diventa una voce sua.
    #
    # Era una preferenza del radar quando il radar era l'unico a usarla. Poi
    # sono arrivati i satelliti e il meteo, e chi accendeva i satelliti andava
    # a cercare le coordinate nella pagina sbagliata -- o peggio, non le
    # trovava e concludeva che il servizio fosse rotto.
    #
    # La migrazione copia e **non cancella**: le due chiavi vecchie restano
    # dove sono, a disposizione di una configurazione che venisse riletta da
    # una versione precedente dopo un ripristino. Una posizione persa vuol dire
    # tre servizi muti e nessun messaggio che spieghi perche'.
    vecchio = raw.get("air_radar") or {}
    nuovo = raw.setdefault("posizione", {})
    for chiave in ("latitude", "longitude"):
        if not nuovo.get(chiave) and vecchio.get(chiave):
            nuovo[chiave] = vecchio[chiave]

    # 1.9: le dieci caselle del Rolling banner devono esserci sempre, anche
    # in una configurazione salvata prima che la funzione esistesse.
    from sources.banner import normalize_list
    banner = raw.setdefault("banner", {})
    banner["items"] = normalize_list(banner.get("items"))

    # 9.9: le cinque caselle del World Time, con la stessa regola dei banner.
    from sources.clock import normalizza_mondo
    mondo = raw.setdefault("clock", {}).setdefault("world", {})
    mondo["voci"] = normalizza_mondo(mondo.get("voci"))

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

    # 8.8: l'elevazione minima dei satelliti passa da 10 a 30 gradi.
    #
    # Stessa regola del gamma di Doom e del giro del meteo: si corregge
    # **solo** chi ha ancora il vecchio predefinito esatto. Chi ha scritto un
    # numero suo conosce il proprio orizzonte meglio di noi.
    satelliti_conf = raw.setdefault("satelliti", {})
    if satelliti_conf.get("elevazione_minima") == 10.0:
        satelliti_conf["elevazione_minima"] = 30.0

    # 8.3: il giro del meteo passa da venti a dieci minuti.
    #
    # Stessa regola del gamma di Doom qui sopra: si corregge **solo** chi ha
    # ancora il vecchio predefinito esatto. Venti era il numero scelto quando
    # una finestra persa costava un turno intero; adesso che una finestra
    # persa costa un minuto, venti sono il doppio del necessario. Chi ha
    # scritto un numero suo lo tiene: e' una sua decisione e vale piu' della
    # nostra.
    meteo_conf = raw.setdefault("meteo", {})
    if meteo_conf.get("ogni_minuti") == 20:
        meteo_conf["ogni_minuti"] = 10

    wad = doom.get("wad") or ""
    if wad and not os.path.exists(wad):
        candidato = os.path.join("/srv/dmd/doom", os.path.basename(wad))
        if os.path.exists(candidato):
            doom["wad"] = candidato
    return raw


def posizione(cfg=None):
    """Dove sta il DMD: (latitudine, longitudine), oppure None.

    Un punto solo per tutto il progetto. `None` vuol dire "nessuno l'ha ancora
    messa", e ogni servizio che ne ha bisogno la tratta come tale: il radar non
    interroga, i satelliti non calcolano, il meteo non chiede. Zero-zero non e'
    un posto, e' l'assenza di un posto -- e il golfo di Guinea non aiuta
    nessuno a capire che manca una configurazione.

    Legge dalla voce nuova e ricade su quella vecchia dentro `air_radar`: la
    migrazione copia gia' all'avvio, ma questa funzione viene chiamata anche
    con dizionari costruiti a mano nelle prove, che la migrazione non l'hanno
    vista.
    """
    cfg = cfg if cfg is not None else load()
    for sezione in ("posizione", "air_radar"):
        dati = cfg.get(sezione) or {}
        try:
            lat = float(dati.get("latitude") or 0.0)
            lon = float(dati.get("longitude") or 0.0)
        except (TypeError, ValueError):
            continue
        if abs(lat) >= 0.01 or abs(lon) >= 0.01:
            return lat, lon
    return None


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
        # Si azzerano **tutti e due** i posti in cui la posizione puo' stare:
        # quello nuovo e quello vecchio lasciato dalla migrazione. Azzerarne
        # uno solo darebbe un file che sembra ripulito e non lo e', che e'
        # peggio di uno che non lo e' e si vede.
        data["posizione"]["latitude"] = 0.0
        data["posizione"]["longitude"] = 0.0
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
