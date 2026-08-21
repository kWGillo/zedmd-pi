"""Traduzione dell'interfaccia web.

Due lingue: italiano e inglese. Niente gettext, niente dipendenze da
installare, niente file da compilare: un dizionario e una funzione.

Ogni voce e' una coppia `(italiano, inglese)`. La chiave e' un identificatore
stabile: se un testo cambia, la chiave resta e le traduzioni non si perdono.

La lingua si sceglie in tre modi, in ordine di precedenza:

  1. quella salvata in `web.language`, se l'utente l'ha scelta
  2. quella dichiarata dal browser in `Accept-Language`
  3. inglese

Questa lingua vale **solo per l'interfaccia**. Il testo che finisce sul
pannello — i nomi dei giorni dell'orologio — ha una sua impostazione
indipendente nella pagina Orologio, perche' chi guarda il cabinato non e'
necessariamente chi configura il sistema.
"""

LANGUAGES = [("it", "Italiano"), ("en", "English")]
CODES = [code for code, _ in LANGUAGES]
FALLBACK = "en"

# Ordine dei valori nelle tuple: italiano, inglese.
_ORDER = {"it": 0, "en": 1}

GITHUB_URL = "https://github.com/kWGillo/zedmd-pi"

STRINGS = {

    # ---------------------------------------------------------------- comuni
    "app.title": ("DMD Controller", "DMD Controller"),
    "nav.settings": ("Impostazioni", "Settings"),
    "nav.clock": ("Orologio", "Clock"),
    "nav.media": ("Media", "Media"),
    "nav.banner": ("Banner", "Banner"),
    "nav.radar": ("Radar", "Radar"),
    "nav.services": ("Servizi", "Services"),
    "nav.language": ("Lingua", "Language"),
    "footer.project": ("Progetto su GitHub", "Project on GitHub"),
    "footer.version": ("versione", "version"),
    "common.save": ("Salva", "Save"),
    "common.save_apply": ("Salva e applica", "Save and apply"),
    "common.apply": ("Applica", "Apply"),
    "common.yes": ("sì", "yes"),
    "common.no": ("no", "no"),
    "common.never": ("mai", "never"),
    "common.none": ("non rilevato", "not detected"),
    "common.default": ("predefinito", "default"),
    "common.from": ("Dalle", "From"),
    "common.to": ("Alle", "To"),
    "common.delete": ("Elimina", "Delete"),
    "common.port": ("porta", "port"),

    "banner.sleep": ("Sleep mode attivo: display spento.",
                     "Sleep mode active: display off."),
    "banner.night": ("Night mode attivo: luminosità ridotta.",
                     "Night mode active: reduced brightness."),

    # ------------------------------------------------------------ stati servizi
    "status.disabled": ("disabilitato", "disabled"),
    "status.zedmd.connected": ("connesso da %(addr)s via %(transport)s (%(frames)d frame)",
                               "connected from %(addr)s over %(transport)s (%(frames)d frames)"),
    "status.zedmd.idle": ("in attesa, ultimo frame %(idle)d s fa (%(frames)d totali)",
                          "idle, last frame %(idle)d s ago (%(frames)d total)"),
    "status.zedmd.listening": ("in ascolto su TCP/UDP %(port)d, nessun client",
                               "listening on TCP/UDP %(port)d, no client"),
    "status.clock.active": ("attivo, formato %(format)s, giorni in %(language)s",
                            "active, %(format)s format, day names in %(language)s"),
    "status.media.unread": ("in attesa, libreria non ancora letta",
                            "idle, library not read yet"),
    "status.media.empty": ("nessun file nella libreria", "no files in the library"),
    "status.media.playing": ("in riproduzione: %(name)s", "playing: %(name)s"),
    "status.media.waiting": ("in attesa, %(count)d file in libreria, %(shown)d mostrati",
                             "idle, %(count)d files in library, %(shown)d shown"),
    "status.media.error": ("errore su %(name)s: %(error)s",
                           "error on %(name)s: %(error)s"),
    "status.banner.empty": ("nessun testo attivo", "no active text"),
    "status.banner.showing": ("in scorrimento: %(text)s", "scrolling: %(text)s"),
    "status.banner.waiting": ("in attesa, %(count)d testi attivi, %(shown)d mostrati",
                              "idle, %(count)d active texts, %(shown)d shown"),
    "status.radar.waiting": ("in attesa", "waiting"),
    "status.radar.error": ("errore: %(error)s", "error: %(error)s"),
    "status.radar.nocoords": ("coordinate non impostate: apri la pagina Radar",
                              "coordinates not set: open the Radar page"),
    "status.radar.found": ("%(provider)s: %(count)d aerei nel raggio di %(radius).1f km",
                           "%(provider)s: %(count)d aircraft within %(radius).1f km"),
    "status.radar.routes": ("rotte trovate %(found)d, non disponibili %(missing)d",
                            "routes found %(found)d, unavailable %(missing)d"),

    # -------------------------------------------------------------- impostazioni
    "settings.brightness": ("Luminosità", "Brightness"),
    "settings.brightness.hint": (
        "Valore diurno di riferimento. La modifica è immediata sul pannello e "
        "viene salvata automaticamente.",
        "Daytime reference value. Changes apply to the panel immediately and "
        "are saved automatically."),

    "settings.modes": ("Night mode e Sleep mode", "Night mode and Sleep mode"),
    "settings.night": ("Night mode — abbassa la luminosità in una fascia oraria",
                       "Night mode — lowers brightness during a time range"),
    "settings.sleep": ("Sleep mode — spegne il display in una fascia oraria",
                       "Sleep mode — turns the display off during a time range"),
    "settings.wake": ("Risveglia il display se arrivano frame da Batocera durante lo Sleep",
                      "Wake the display if frames arrive from Batocera during Sleep"),
    "settings.modes.hint": (
        "Sleep ha la precedenza su Night. Le fasce possono attraversare la "
        "mezzanotte, ad esempio dalle 23:00 alle 07:00.",
        "Sleep takes precedence over Night. Ranges may cross midnight, for "
        "example from 23:00 to 07:00."),

    "settings.time": ("Ora e sincronizzazione", "Time and synchronisation"),
    "settings.ntp": ("Server NTP", "NTP server"),
    "settings.timezone": ("Fuso orario", "Time zone"),
    "settings.dst": ("Ora legale automatica (secondo il fuso orario selezionato)",
                     "Automatic daylight saving (per the selected time zone)"),
    "settings.utc": ("Scostamento UTC manuale (se l'automatismo è disattivato)",
                     "Manual UTC offset (when automatic mode is off)"),
    "settings.systime": ("Ora di sistema", "System time"),
    "settings.activetz": ("Fuso attivo", "Active time zone"),
    "settings.ntpon": ("NTP attivo", "NTP enabled"),
    "settings.synced": ("Sincronizzato", "Synchronised"),

    "settings.network": ("Rete", "Network"),
    "settings.hostname": ("Hostname", "Hostname"),
    "settings.localip": ("Indirizzo IP locale", "Local IP address"),
    "settings.handshake": ("Handshake ZeDMD", "ZeDMD handshake"),
    "settings.stream": ("Stream ZeDMD", "ZeDMD stream"),
    "settings.webui": ("Interfaccia web", "Web interface"),
    "settings.network.hint": (
        "Nel client ZeDMD indica solo questo indirizzo IP: userà da sé le "
        "porte corrette.",
        "In the ZeDMD client enter only this IP address: it picks the right "
        "ports by itself."),

    "settings.panel": ("Regolazione fine del pannello", "Panel fine tuning"),
    "settings.panel.hint": (
        "Se compaiono lampi o strisce bianche orizzontali, agisci prima su "
        "<em>cicli extra a fine frame</em>: aggiunge tempo dopo l'invio dei "
        "dati e copre il vuoto che genera il lampo. Parti da 1 e sali di uno "
        "alla volta. Campo vuoto = valore predefinito della libreria.",
        "If horizontal white flashes or stripes appear, start with "
        "<em>extra end-of-frame cycles</em>: it adds time after the data is "
        "sent and covers the gap that causes the flash. Start at 1 and go up "
        "one step at a time. An empty field means the library default."),
    "settings.panel.extra": ("Cicli extra a fine frame", "Extra end-of-frame cycles"),
    "settings.panel.sleep": ("Pausa tra frame (µs)", "Pause between frames (µs)"),
    "settings.panel.refresh": ("Refresh massimo (Hz)", "Maximum refresh (Hz)"),
    "settings.panel.pwm": ("Profondità PWM", "PWM depth"),
    "settings.panel.slowdown": ("Rallentamento GPIO", "GPIO slowdown"),
    "settings.panel.profile": ("Profilo di registro del chip", "Chip register profile"),
    "settings.panel.showrefresh": ("Scrivi il refresh rate nel log — utile durante la taratura",
                                   "Write the refresh rate to the log — useful while tuning"),
    "settings.panel.button": ("Salva e riavvia il servizio", "Save and restart the service"),
    "settings.panel.note": (
        "Queste impostazioni si applicano solo alla creazione del pannello, "
        "quindi il servizio viene riavviato: il display resta spento per "
        "qualche secondo. Segui l'effetto con",
        "These settings only apply when the panel is created, so the service "
        "is restarted and the display stays off for a few seconds. Watch the "
        "effect with"),

    "settings.updates": ("Aggiornamenti", "Updates"),
    "settings.update.current": ("Versione installata", "Installed version"),
    "settings.update.latest": ("Versione su GitHub", "Version on GitHub"),
    "settings.update.unchecked": ("non verificata", "not checked"),
    "settings.update.checked": ("Ultimo controllo", "Last check"),
    "settings.update.failed": ("Controllo non riuscito: %(error)s",
                               "Check failed: %(error)s"),
    "settings.update.available": ("È disponibile la versione %(version)s.",
                                  "Version %(version)s is available."),
    "settings.update.uptodate": ("Il software è aggiornato.", "The software is up to date."),
    "settings.update.checknow": ("Controlla ora", "Check now"),
    "settings.update.install": ("Installa la versione %(version)s",
                                "Install version %(version)s"),
    "settings.update.repo": ("Repository", "Repository"),
    "settings.update.branch": ("Ramo", "Branch"),
    "settings.update.interval": ("Controllo ogni (ore)", "Check every (hours)"),
    "settings.update.auto": ("Controlla automaticamente la disponibilità di aggiornamenti",
                             "Check for updates automatically"),
    "settings.update.hint": (
        "L'installazione scarica l'archivio dal ramo indicato, verifica che "
        "contenga i file attesi e che tutto il codice compili, salva una copia "
        "della versione in uso e solo allora sostituisce i file. Se dopo il "
        "riavvio il servizio non risponde, la versione precedente viene "
        "ripristinata da sola. La configurazione in %(path)s non viene mai toccata.",
        "The installer downloads the archive from the chosen branch, checks "
        "that it contains the expected files and that all the code compiles, "
        "backs up the running version, and only then replaces the files. If "
        "the service does not answer after the restart, the previous version "
        "is restored automatically. The configuration in %(path)s is never "
        "touched."),
    "settings.update.log": ("Diario degli aggiornamenti", "Update log"),

    "settings.lib": ("Libreria del pannello", "Panel library"),
    "settings.lib.hint": (
        "Il fork che pilota i pannelli S-PWM non usa numeri di versione: si "
        "aggiorna a commit. Qui si confronta quello installato con quello in "
        "cima al ramo remoto.",
        "The fork that drives S-PWM panels does not use version numbers: it is "
        "updated commit by commit. Here the installed one is compared with the "
        "head of the remote branch."),
    "settings.lib.repo": ("Repository", "Repository"),
    "settings.lib.path": ("Cartella locale", "Local folder"),
    "settings.lib.local": ("Commit installato", "Installed commit"),
    "settings.lib.remote": ("Commit su GitHub", "Commit on GitHub"),
    "settings.lib.checked": ("Ultimo controllo", "Last check"),
    "settings.lib.check": ("Controlla la libreria", "Check the library"),
    "settings.lib.uptodate": ("La libreria è aggiornata.", "The library is up to date."),
    "settings.lib.behind": (
        "Sul repository c'è un commit più recente di quello installato.",
        "The repository has a commit newer than the installed one."),
    "settings.lib.failed": ("Controllo non riuscito: %(error)s",
                            "Check failed: %(error)s"),
    "settings.lib.manual": (
        "L'aggiornamento <strong>non</strong> è automatico, di proposito: "
        "ricompilare la libreria e reinstallare i binding richiede una decina "
        "di minuti su una Pi Zero 2 W, con il pannello fermo, e può cambiare il "
        "comportamento di una taratura che funziona. È un'operazione da fare "
        "guardando il terminale. I comandi, nell'ordine:",
        "Updating is <strong>not</strong> automatic, deliberately: rebuilding "
        "the library and reinstalling the bindings takes some ten minutes on a "
        "Pi Zero 2 W, with the panel down, and can change the behaviour of a "
        "working setup. It is an operation to do while watching the terminal. "
        "The commands, in order:"),
    "settings.lib.doc": ("Guida alla taratura S-PWM del fork",
                         "The fork's S-PWM tuning guide"),

    "settings.config": ("Configurazione", "Configuration"),
    "settings.config.hint": (
        "Tutta la taratura del pannello, i colori, le fasce orarie e le "
        "impostazioni dei servizi stanno in un unico file. Esportalo dopo ogni "
        "modifica importante: se la scheda SD si guasta, rimettere in piedi il "
        "sistema diventa questione di minuti invece che di tentativi.",
        "The whole panel tuning, the colours, the time ranges and the service "
        "settings live in a single file. Export it after every significant "
        "change: if the SD card fails, rebuilding the system becomes a matter "
        "of minutes rather than guesswork."),
    "settings.config.export": ("Esporta la configurazione", "Export the configuration"),
    "settings.config.position": (
        "Includi le coordinate del radar",
        "Include the radar coordinates"),
    "settings.config.position.hint": (
        "Togli la spunta se il file va condiviso con qualcuno o allegato a una "
        "segnalazione: senza, le coordinate vengono esportate a zero.",
        "Clear this if the file is going to be shared or attached to a bug "
        "report: without it, the coordinates are exported as zero."),
    "settings.config.import": ("Importa una configurazione", "Import a configuration"),
    "settings.config.import.button": ("Importa e riavvia", "Import and restart"),
    "settings.config.import.hint": (
        "Il file viene adeguato alla versione in uso, quindi va bene anche se "
        "salvato da una versione precedente. Le chiavi sconosciute vengono "
        "ignorate. La configurazione attuale viene copiata in %(path)s prima "
        "di essere sostituita, e il servizio si riavvia: le impostazioni del "
        "pannello si applicano solo alla creazione della matrice.",
        "The file is adapted to the running version, so one saved by an older "
        "version works too. Unknown keys are ignored. The current "
        "configuration is copied to %(path)s before being replaced, and the "
        "service restarts: panel settings only apply when the matrix is "
        "created."),
    "settings.config.nofile": ("Nessun file selezionato.", "No file selected."),
    "settings.config.badjson": (
        "Il file non è un JSON leggibile: potrebbe essersi rovinato nel trasferimento.",
        "The file is not readable JSON: it may have been damaged in transfer."),
    "settings.config.rejected": ("Importazione rifiutata: %(error)s",
                                 "Import rejected: %(error)s"),
    "settings.config.imported": (
        "Configurazione importata. Il servizio si sta riavviando.",
        "Configuration imported. The service is restarting."),

    "settings.service": ("Servizio", "Service"),
    "settings.service.restart": ("Riavvia il servizio DMD", "Restart the DMD service"),

    "settings.language": ("Lingua dell'interfaccia", "Interface language"),
    "settings.language.hint": (
        "Vale solo per queste pagine. I nomi dei giorni che appaiono sul "
        "pannello si scelgono nella pagina Orologio, separatamente.",
        "Applies to these pages only. The weekday names shown on the panel "
        "are chosen separately, on the Clock page."),

    # ------------------------------------------------------------------ orologio
    "clock.title": ("Orologio", "Clock"),
    "clock.appearance": ("Aspetto dell'orologio", "Clock appearance"),
    "clock.timecolor": ("Colore dell'ora", "Time colour"),
    "clock.datecolor": ("Colore della data", "Date colour"),
    "clock.language": ("Lingua dei giorni della settimana", "Weekday name language"),
    "clock.language.hint": (
        "Riguarda il testo sul pannello, non queste pagine.",
        "This affects the text on the panel, not these pages."),
    "clock.format24": ("Formato 24 ore (se disattivato: 12 ore con indicatore AM/PM)",
                       "24-hour format (when off: 12-hour with AM/PM)"),
    "clock.showdate": ("Mostra la data", "Show the date"),
    "clock.blink": ("Due punti lampeggianti", "Blinking colon"),
    "clock.preview.date": ("LUN 18/08", "MON 18/08"),

    # --------------------------------------------------------------------- media
    "media.title": ("Media Player", "Media Player"),
    "media.noffmpeg": ("ffmpeg non è installato: i video non possono essere riprodotti.",
                       "ffmpeg is not installed: videos cannot be played."),
    "media.library": ("Libreria", "Library"),
    "media.folder": ("Cartella", "Folder"),
    "media.share": ("Condivisione di rete", "Network share"),
    "media.usable": ("File utilizzabili", "Usable files"),
    "media.upload": ("Carica immagini o video", "Upload images or videos"),
    "media.upload.button": ("Carica", "Upload"),
    "media.rescan.hint": (
        "L'elenco dei file viene tenuto in memoria per qualche minuto: con "
        "librerie molto grandi rileggere il disco a ogni richiesta rallenta "
        "il sistema e produce righe bianche sul pannello. Dopo aver copiato "
        "file dalla condivisione di rete, usa il pulsante qui sotto.",
        "The file list is kept in memory for a few minutes: with very large "
        "libraries, re-reading the disk on every request slows the system "
        "down and produces white lines on the panel. After copying files over "
        "the network share, use the button below."),
    "media.rescan.button": ("Rileggi la libreria", "Re-read the library"),
    "media.preview": ("Anteprima", "Preview"),
    "media.preview.hint": (
        "Interrompe l'attesa e manda subito sul pannello un contenuto scelto "
        "a caso dalla libreria.",
        "Skips the wait and immediately sends a randomly chosen item from the "
        "library to the panel."),
    "media.preview.button": ("Mostra subito un contenuto", "Show something now"),
    "media.playback": ("Riproduzione", "Playback"),
    "media.minint": ("Intervallo minimo (s)", "Minimum interval (s)"),
    "media.maxint": ("Intervallo massimo (s)", "Maximum interval (s)"),
    "media.interval.hint": (
        "Tra un contenuto e il successivo il sistema attende un tempo casuale "
        "compreso in questo intervallo.",
        "Between one item and the next the system waits a random time within "
        "this range."),
    "media.imgdur": ("Durata delle foto (s)", "Photo duration (s)"),
    "media.viddur": ("Durata dei video (s)", "Video duration (s)"),
    "media.duration.hint": (
        "Le animazioni brevi, come le GIF di Pixelcade, vengono ripetute fino "
        "a coprire la durata indicata.",
        "Short animations, such as Pixelcade GIFs, are looped to fill the "
        "given duration."),
    "media.fps": ("Fotogrammi al secondo", "Frames per second"),
    "media.scale": ("Adattamento al pannello", "Fit to panel"),
    "media.scale.fit": ("Adatta (bande nere)", "Fit (letterbox)"),
    "media.scale.fill": ("Riempi (ritaglia)", "Fill (crop)"),
    "media.pixelart": ("Modalità pixel art — bordi netti, consigliata per il materiale Pixelcade",
                       "Pixel art mode — hard edges, recommended for Pixelcade artwork"),
    "media.files": ("File presenti", "Files present"),
    "media.files.shown": ("Mostrati i primi %(shown)d di %(total)d.",
                          "Showing the first %(shown)d of %(total)d."),
    "media.files.empty": (
        "Nessun file. Caricane dalla sezione qui sopra oppure copiali nella "
        "condivisione di rete.",
        "No files. Upload some from the section above, or copy them into the "
        "network share."),

    # -------------------------------------------------------------------- banner
    "banner.title": ("Rolling Banner", "Rolling Banner"),
    "banner.intro": (
        "Fino a dieci testi scorrevoli. Compaiono a intervalli casuali come i "
        "contenuti del Media Player: il testo entra da destra, attraversa il "
        "pannello ed esce a sinistra, poi il display torna a chi lo aveva.",
        "Up to ten scrolling texts. They appear at random intervals like Media "
        "Player items: the text enters from the right, crosses the panel and "
        "exits to the left, then the display goes back to whoever had it."),
    "banner.texts": ("Testi", "Texts"),
    "banner.slot": ("Testo %(n)d", "Text %(n)d"),
    "banner.text": ("Testo", "Text"),
    "banner.text.placeholder": ("Lascia vuoto per non usare questa casella",
                                "Leave empty to skip this slot"),
    "banner.color": ("Colore", "Colour"),
    "banner.size": ("Dimensione", "Size"),
    "banner.size.small": ("Piccola", "Small"),
    "banner.size.medium": ("Media", "Medium"),
    "banner.size.large": ("Grande", "Large"),
    "banner.speed": ("Velocità (px/s)", "Speed (px/s)"),
    "banner.blink": ("Lampeggio", "Blinking"),
    "banner.enabled": ("Attivo", "Active"),
    "banner.slot.hint": (
        "Una casella entra nella rotazione solo se è attiva e contiene del testo.",
        "A slot joins the rotation only if it is active and contains text."),
    "banner.playback": ("Comparsa", "Appearance"),
    "banner.minint": ("Intervallo minimo (s)", "Minimum interval (s)"),
    "banner.maxint": ("Intervallo massimo (s)", "Maximum interval (s)"),
    "banner.interval.hint": (
        "Tra un banner e il successivo il sistema attende un tempo casuale "
        "compreso in questo intervallo.",
        "Between one banner and the next the system waits a random time within "
        "this range."),
    "banner.fps": ("Fotogrammi al secondo", "Frames per second"),
    "banner.shuffle": ("Ordine casuale invece che in sequenza",
                       "Random order instead of sequential"),
    "banner.speed.hint": (
        "La velocità è per singolo testo: a 60 px/s un testo attraversa il "
        "pannello in poco più di quattro secondi. Valori bassi si leggono "
        "meglio, valori alti si notano di più.",
        "Speed is per text: at 60 px/s a text crosses the panel in a little "
        "over four seconds. Lower values read better, higher ones draw more "
        "attention."),
    "banner.preview": ("Anteprima", "Preview"),
    "banner.preview.hint": (
        "Interrompe l'attesa e manda subito in scorrimento il testo successivo.",
        "Skips the wait and immediately scrolls the next text."),
    "banner.preview.button": ("Mostra subito un banner", "Show a banner now"),
    "banner.priority.hint": (
        "Il banner sta sopra al Media Player ma sotto ad Air Radar e a ZeDMD: "
        "durante una partita su Batocera non compare mai.",
        "The banner outranks the Media Player but stays below Air Radar and "
        "ZeDMD: it never appears during a game on Batocera."),

    # --------------------------------------------------------------------- radar
    "radar.title": ("Air Radar", "Air Radar"),
    "radar.nocoords": (
        "Coordinate non impostate: il servizio non interroga nulla finché non "
        "indichi una posizione qui sotto.",
        "Coordinates not set: the service queries nothing until you enter a "
        "position below."),
    "radar.state": ("Stato", "Status"),
    "radar.pollnow": ("Interroga adesso", "Query now"),
    "radar.probe": ("Prova la ricerca di una rotta", "Test a route lookup"),
    "radar.probe.button": ("Prova", "Test"),
    "radar.priority.hint": (
        "Air Radar ha priorità sul Media Player e sull'orologio, ma resta "
        "sempre sotto ZeDMD: durante una partita su Batocera non compare mai.",
        "Air Radar outranks the Media Player and the clock, but always stays "
        "below ZeDMD: it never appears during a game on Batocera."),
    "radar.position": ("Posizione e raggio", "Position and radius"),
    "radar.lat": ("Latitudine", "Latitude"),
    "radar.lon": ("Longitudine", "Longitude"),
    "radar.coords.hint": (
        "Coordinate decimali, con il punto come separatore. Su una mappa "
        "online si ottengono con un clic destro sul punto desiderato. Restano "
        "solo in %(path)s su questo Raspberry: non fanno parte del software e "
        "non finiscono in nessun pacchetto o repository.",
        "Decimal coordinates, using a dot as the separator. On an online map "
        "you get them by right-clicking the point you want. They stay only in "
        "%(path)s on this Raspberry Pi: they are not part of the software and "
        "never end up in any package or repository."),
    "radar.radius": ("Raggio (km)", "Radius (km)"),
    "radar.maxalt": ("Quota massima (ft)", "Maximum altitude (ft)"),
    "radar.provider": ("Servizio dati", "Data service"),
    "radar.filter.hint": (
        "Quota massima 0 = nessun filtro. Impostandola, ad esempio, a 15000 "
        "ft si ignorano i voli di alta quota mostrando solo chi sta davvero "
        "passando sopra di te. Se il servizio scelto non risponde, gli altri "
        "vengono usati automaticamente come riserva.",
        "Maximum altitude 0 means no filter. Setting it to, say, 15000 ft "
        "ignores high-altitude traffic and shows only what is really passing "
        "overhead. If the chosen service does not answer, the others are used "
        "as a fallback automatically."),
    "radar.interval": ("Intervallo interrogazioni (s)", "Query interval (s)"),
    "radar.duration": ("Durata a schermo (s)", "Time on screen (s)"),
    "radar.cooldown": ("Riposo per aereo (s)", "Per-aircraft cooldown (s)"),
    "radar.cooldown.hint": (
        "Il riposo evita che lo stesso volo venga riproposto in continuazione "
        "mentre resta nel raggio.",
        "The cooldown stops the same flight from being shown over and over "
        "while it stays within range."),
    "radar.fields": ("Parametri di volo da mostrare", "Flight details to show"),
    "radar.fields.hint": (
        "Il codice volo compare sempre in grande. Questi campi formano la riga "
        "di dettaglio sotto: se non ci stanno tutti, quelli centrali vengono "
        "tolti automaticamente per non sbordare.",
        "The flight number is always shown large. These fields form the detail "
        "line below it: if they do not all fit, the middle ones are dropped "
        "automatically."),
    "radar.route.hint": (
        "La rotta viene cercata solo se il campo è selezionato qui. È "
        "disponibile per i voli di linea, molto meno per cargo, aviazione "
        "generale e voli di Stato: conviene selezionare anche altri campi, "
        "altrimenti quando la rotta manca resta solo la distanza.",
        "The route is looked up only if the field is selected here. It is "
        "available for scheduled flights, much less so for cargo, general "
        "aviation and state flights: it is worth selecting other fields too, "
        "otherwise only the distance remains when the route is missing."),
    "radar.log.enable": ("Registra ogni passaggio nel file CSV",
                         "Log every pass to the CSV file"),
    "radar.log.route": (
        "Cerca la rotta anche per i voli registrati nel CSV che non vanno a schermo",
        "Look up the route also for flights logged to CSV that never reach the screen"),
    "radar.callsigncolor": ("Colore del codice volo", "Flight number colour"),
    "radar.infocolor": ("Colore dei dettagli", "Detail colour"),
    "radar.log": ("Registro dei passaggi", "Pass log"),
    "radar.log.file": ("File", "File"),
    "radar.log.rows": ("Voli registrati", "Flights logged"),
    "radar.log.size": ("Dimensione", "Size"),
    "radar.log.hint": (
        "Una riga per ogni volo a ogni passaggio, con data e ora, codice volo, "
        "immatricolazione, modello, quota, velocità, direzione, transponder, "
        "distanza, coordinate e rotta. Lo stesso aereo non viene riscritto "
        "finché resta nel raggio.",
        "One row per flight per pass, with date and time, flight number, "
        "registration, type, altitude, speed, heading, transponder, distance, "
        "coordinates and route. The same aircraft is not written again while "
        "it stays within range."),
    "radar.log.download": ("Scarica il CSV", "Download the CSV"),
    "radar.log.clear": ("Svuota il registro", "Clear the log"),
    "radar.notes": ("Note sui dati", "About the data"),
    "radar.notes.coverage": (
        "I dati arrivano dalle reti ADS-B comunitarie, gratuite e senza "
        "registrazione. Non essendoci un'antenna locale, la copertura dipende "
        "dai riceventi volontari della zona: il traffico commerciale compare "
        "quasi sempre, aviazione generale e voli militari spesso no.",
        "The data comes from the community ADS-B networks, free and without "
        "registration. With no local antenna, coverage depends on volunteer "
        "receivers in the area: commercial traffic almost always shows up, "
        "general aviation and military flights often do not."),
    "radar.notes.radius": (
        "Con un raggio di pochi chilometri le apparizioni possono essere rare: "
        "se non sei sotto una rotta o vicino a un aeroporto, conviene "
        "allargare il raggio per verificare che tutto funzioni.",
        "With a radius of a few kilometres sightings can be rare: if you are "
        "not under an airway or near an airport, widen the radius to check "
        "that everything works."),

    "radar.field.route": ("Rotta (origine → destinazione)", "Route (origin → destination)"),
    "radar.field.type": ("Modello di aeromobile", "Aircraft type"),
    "radar.field.reg": ("Immatricolazione", "Registration"),
    "radar.field.altitude": ("Quota", "Altitude"),
    "radar.field.speed": ("Velocità al suolo", "Ground speed"),
    "radar.field.track": ("Direzione", "Heading"),
    "radar.field.squawk": ("Codice transponder", "Transponder code"),
    "radar.field.distance": ("Distanza", "Distance"),
    "radar.field.hex": ("Codice Mode S", "Mode S code"),

    # ------------------------------------------------------------------ servizi
    "services.title": ("Servizi", "Services"),
    "services.onscreen": ("Sorgente a schermo", "Source on screen"),
    "services.current": ("Attualmente sul display:", "Currently on the display:"),
    "services.mode": ("Modalità", "Mode"),
    "services.auto": ("Automatica (per priorità)", "Automatic (by priority)"),
    "services.force": ("Forza %(name)s", "Force %(name)s"),
    "services.arbiter.hint": (
        "In automatico ZeDMD ha la precedenza appena riceve frame e la "
        "mantiene per %(grace)d secondi dopo l'ultimo segnale. Il Media Player "
        "si sovrappone all'orologio solo per la durata del contenuto.",
        "In automatic mode ZeDMD takes over as soon as it receives frames and "
        "holds the display for %(grace)d seconds after the last signal. The "
        "Media Player overrides the clock only for the length of the item."),
    "services.on": ("Attivo", "On"),
    "services.off": ("Spento", "Off"),
    "services.soon": ("In arrivo", "Coming soon"),
    "services.desc.zedmd": ("Riceve i frame DMD via rete da Batocera, dmdserver o VPX.",
                           "Receives DMD frames over the network from Batocera, dmdserver or VPX."),
    "services.desc.mediaplayer": ("Foto e video a rotazione dalla libreria, a intervalli casuali.",
                                  "Photos and videos from the library, at random intervals."),
    "services.desc.clock": ("Orologio e data, sorgente di riserva quando non c'è altro.",
                            "Clock and date, the fallback source when nothing else is on."),
    "services.desc.banner": ("Testi scorrevoli a intervalli casuali, fino a dieci.",
                             "Scrolling texts at random intervals, up to ten."),
    "services.desc.status_player": ("Notifiche sui giochi avviati dagli amici su Batocera.",
                                    "Notifications about games your friends launch on Batocera."),
    "services.desc.air_radar": ("Aerei in transito entro un raggio dalla posizione indicata.",
                                "Aircraft passing within a radius of the given position."),
}


def normalize(code):
    """Riporta un codice qualsiasi a una lingua supportata."""
    text = (code or "").strip().lower().replace("_", "-")
    if text in CODES:
        return text
    root = text.split("-")[0]
    return root if root in CODES else ""


def negotiate(header):
    """Sceglie la lingua a partire da un'intestazione Accept-Language.

    Il formato e' `it-IT,it;q=0.9,en;q=0.8`: una lista di preferenze con un
    peso facoltativo. Si prende quella con il peso piu' alto fra le lingue che
    sappiamo parlare; se non ce ne sono, inglese.
    """
    best = ("", -1.0)
    for chunk in (header or "").split(","):
        parts = chunk.split(";")
        code = normalize(parts[0])
        if not code:
            continue
        weight = 1.0
        for extra in parts[1:]:
            extra = extra.strip()
            if extra.startswith("q="):
                try:
                    weight = float(extra[2:])
                except ValueError:
                    weight = 0.0
        if weight > best[1]:
            best = (code, weight)
    return best[0] or FALLBACK


def resolve(saved, header):
    """La preferenza salvata vince sul browser; il browser vince sul default."""
    return normalize(saved) or negotiate(header)


def translate(key, lang="it", **values):
    """Testo tradotto. Le chiavi sconosciute tornano come sono.

    Una chiave che manca e' un errore di programmazione, non dell'utente:
    tornarla visibile la fa notare subito, invece di far sparire il testo.
    """
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry[_ORDER.get(normalize(lang) or FALLBACK, 1)]
    if values:
        try:
            return text % values
        except (KeyError, TypeError, ValueError):
            return text
    return text


def language_name(code):
    for value, name in LANGUAGES:
        if value == code:
            return name
    return code


def missing_keys():
    """Voci incomplete. Serve ai test, non all'esecuzione."""
    bad = []
    for key, entry in STRINGS.items():
        if len(entry) != len(CODES) or not all(str(v).strip() for v in entry):
            bad.append(key)
    return sorted(bad)
