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
    "app.title": ("kWGillo DMD Server", "kWGillo DMD Server"),
    "nav.settings": ("Impostazioni", "Settings"),
    "nav.clock": ("Orologio", "Clock"),
    "nav.media": ("Media", "Media"),
    "nav.banner": ("Banner", "Banner"),
    "nav.nowplaying": ("Musica", "Music"),
    # ------------------------------------------------------------- compleanni
    "nav.birthdays": ("Compleanni", "Birthdays"),
    "birthdays.title": ("Compleanni e anniversari", "Birthdays and anniversaries"),
    "birthdays.intro": (
        "Un elenco di date e nomi, compleanni o anniversari. Quando la "
        "ricorrenza si avvicina, il "
        "pannello lo ricorda con un messaggio che scorre, come i banner. La "
        "data si scrive giorno/mese/anno; l'anno si può omettere, ma senza "
        "non si può mostrare l'età.",
        "A list of dates and names. When a birthday approaches, the panel "
        "reminds you with a scrolling message, like the banners. Dates are "
        "day/month/year; the year is optional, but without it the age cannot "
        "be shown."),
    "birthdays.upcoming": ("In arrivo", "Coming up"),
    "birthdays.upcoming.hint": (
        "Chi compie gli anni entro le prossime %(hours)s ore.",
        "Whose birthday falls within the next %(hours)s hours."),
    "birthdays.upcoming.none": ("Nessuno in vista.", "Nobody in sight."),
    "birthdays.today": ("oggi", "today"),
    "birthdays.tomorrow": ("domani", "tomorrow"),
    "birthdays.in.days": ("fra %(days)d giorni", "in %(days)d days"),
    "birthdays.age": ("compie %(years)d anni", "turns %(years)d"),
    "birthdays.add": ("Aggiungi una persona", "Add a person"),
    "birthdays.add.hint": (
        "La data si scrive 30/03/1976. Va bene anche senza anno: 30/03.",
        "Write the date as 30/03/1976. Without the year is fine too: 30/03."),
    "birthdays.kind": ("Tipo", "Kind"),
    "birthdays.kind.compleanno": ("Compleanno", "Birthday"),
    "birthdays.kind.anniversario": ("Anniversario", "Anniversary"),
    "birthdays.date": ("Data", "Date"),
    "birthdays.name": ("Nome", "Name"),
    "birthdays.add.button": ("Aggiungi", "Add"),
    "birthdays.import": ("Importa un CSV", "Import a CSV"),
    "birthdays.import.hint": (
        "Due colonne, data e nome. Le righe vengono aggiunte in coda a quelle "
        "già presenti, non le sostituiscono: per ripartire da zero svuota "
        "prima la casella qui sotto.",
        "Two columns, date and name. Rows are appended to the existing ones "
        "rather than replacing them: to start over, empty the box below "
        "first."),
    "birthdays.import.button": ("Importa", "Import"),
    "birthdays.file": ("Elenco completo", "Full list"),
    "birthdays.file.hint": (
        "Si modifica anche a mano, da qui o via SSH. Le righe che iniziano "
        "con # sono commenti, e una riga sbagliata si perde da sola senza "
        "compromettere le altre.",
        "It can also be edited by hand, here or over SSH. Rows starting with "
        "# are comments, and a broken row is dropped on its own without "
        "affecting the others."),
    "birthdays.count": ("%(count)d persone", "%(count)d people"),
    "birthdays.settings": ("Impostazioni", "Settings"),
    "birthdays.lead": ("Anticipo (ore)", "Lead time (hours)"),
    "birthdays.lead.hint": (
        "L'anticipo dice quanto prima comincia il promemoria: 48 ore vuol "
        "dire da due giorni prima. L'intervallo è ogni quanto ricompare; "
        "se ci sono più compleanni insieme si alternano nello stesso giro.",
        "The lead time says how early the reminder starts: 48 hours means "
        "two days ahead. The interval is how often it comes back; when "
        "several birthdays fall together they alternate within the same "
        "round."),
    "birthdays.interval": ("Intervallo (minuti)", "Interval (minutes)"),
    "birthdays.seconds": ("Durata (s)", "Duration (s)"),
    "birthdays.size": ("Dimensione", "Size"),
    "birthdays.speed": ("Velocità (px/s)", "Speed (px/s)"),
    "birthdays.color": ("Colore", "Colour"),
    "birthdays.show_age": ("Mostra l'età compiuta", "Show the age reached"),
    "birthdays.blink": ("Lampeggiante", "Blinking"),
    "birthdays.saved": ("Salvato: %(count)d persone.", "Saved: %(count)d people."),
    "birthdays.imported": ("Importate %(count)d persone.",
                           "Imported %(count)d people."),
    "birthdays.added": ("Persona aggiunta.", "Person added."),
    "birthdays.error": ("Non riuscito: %(reason)s", "Failed: %(reason)s"),
    "birthdays.errors": ("Righe scartate", "Dropped rows"),
    "status.birthdays.next": (
        "prossimo: %(name)s fra %(days)d giorni (%(count)d in vista, "
        "%(shown)d promemoria mostrati)",
        "next: %(name)s in %(days)d days (%(count)d coming up, %(shown)d "
        "reminders shown)"),
    "status.birthdays.none": (
        "nessun compleanno nelle prossime %(hours)d ore",
        "no birthday in the next %(hours)d hours"),

    # ---------------------------------------------------------- profili pannello
    "preset.label": ("Profilo del pannello", "Panel profile"),
    "preset.custom": ("Personalizzata", "Custom"),
    "preset.hint": (
        "Un profilo applica in blocco tutti i parametri di quel tipo di "
        "pannello: geometria, driver, indirizzamento e taratura fine. Serve "
        "soprattutto a tornare indietro — un parametro sbagliato non dà un "
        "errore, dà un display illeggibile, e da lì non si torna a memoria. "
        "Scegliendo un profilo noto i campi qui sotto vengono sovrascritti "
        "al salvataggio; scegliendo Personalizzata restano quelli che vedi.",
        "A profile applies every parameter of that panel type at once: "
        "geometry, driver, addressing and fine tuning. Its main use is going "
        "back — a wrong parameter gives no error, it gives an unreadable "
        "display, and from there memory is no help. Picking a known profile "
        "overwrites the fields below on save; picking Custom keeps what you "
        "see."),

    # ------------------------------------------------------------- cablaggio
    "cablaggio.label": ("Collegamento del pannello", "Panel wiring"),
    "cablaggio.regular": ("Fili diretti sui GPIO", "Direct GPIO wiring"),
    "cablaggio.adafruit-hat": ("Adafruit RGB Matrix Bonnet",
                              "Adafruit RGB Matrix Bonnet"),
    "cablaggio.adafruit-hat-pwm": (
        "Adafruit Bonnet con modifica PWM (GPIO 4–18 saldati)",
        "Adafruit Bonnet with the PWM mod (GPIO 4–18 soldered)"),
    "cablaggio.hint": (
        "Come i segnali arrivano al pannello. È una caratteristica della "
        "macchina, non del pannello: il profilo qui sopra non la tocca, così "
        "riapplicarlo non riporta l'uscita sui piedini sbagliati. Ha effetto "
        "al riavvio del servizio.",
        "How the signals reach the panel. It belongs to the machine, not to "
        "the panel: the profile above never touches it, so re-applying the "
        "profile cannot send the output back to the wrong pins. Takes effect "
        "when the service restarts."),
    "cablaggio.avviso.soft": (
        "Senza la modifica PWM l'OE sta sul GPIO 4, che non è un piedino PWM: "
        "gli impulsi li genera il software e l'immagine può tremolare. "
        "Unendo a saldare GPIO 4 e GPIO 18 si passa alla voce con modifica.",
        "Without the PWM mod, OE sits on GPIO 4, which is not a PWM pin: the "
        "pulses are generated in software and the image may flicker. "
        "Soldering GPIO 4 to GPIO 18 enables the modded option."),
    "cablaggio.avviso.pwm": (
        "Richiede il ponticello a saldare fra GPIO 4 e GPIO 18 sulla Bonnet e "
        "il modulo audio snd_bcm2835 in blacklist. Senza il ponticello il "
        "pannello resta spento.",
        "Requires the solder bridge between GPIO 4 and GPIO 18 on the Bonnet "
        "and the snd_bcm2835 audio module blacklisted. Without the bridge the "
        "panel stays dark."),

    # ------------------------------------------------------- unita' del radar
    "radar.units": ("Unità di misura", "Units"),
    "radar.units.hint": (
        "I dati arrivano sempre in piedi e nodi: la conversione riguarda "
        "solo come vengono scritti sul pannello. Il registro CSV resta nelle "
        "unità originali, così i passaggi vecchi e nuovi restano confrontabili.",
        "The data always arrives in feet and knots: the conversion only "
        "affects how it is written on the panel. The CSV log stays in the "
        "original units, so old and new passes remain comparable."),
    "radar.unit.ft": ("piedi (ft)", "feet (ft)"),
    "radar.unit.m": ("metri (m)", "metres (m)"),
    "radar.unit.kt": ("nodi (kt)", "knots (kt)"),
    "radar.unit.kmh": ("km/h", "km/h"),
    "radar.unit.mph": ("mph", "mph"),
    "radar.unit.km": ("chilometri (km)", "kilometres (km)"),
    "radar.unit.mi": ("miglia (mi)", "miles (mi)"),
    "radar.unit.nm": ("miglia nautiche (nm)", "nautical miles (nm)"),
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
    "status.zedmd.connected": (
        "connesso da %(addr)s via %(transport)s, %(frames)d frame ricevuti "
        "(%(fps).1f/s), %(shown)d mostrati, ultimo %(idle)d s fa",
        "connected from %(addr)s over %(transport)s, %(frames)d frames "
        "received (%(fps).1f/s), %(shown)d shown, last one %(idle)d s ago"),
    "status.zedmd.connected.silent": (
        "connesso da %(addr)s via %(transport)s da %(since)d s, "
        "ma non ha ancora mandato nessun fotogramma",
        "connected from %(addr)s over %(transport)s for %(since)d s, "
        "but it has not sent a single frame yet"),
    "status.zedmd.idle": ("in attesa, ultimo frame %(idle)d s fa (%(frames)d totali)",
                          "idle, last frame %(idle)d s ago (%(frames)d total)"),
    "status.zedmd.handshake": (
        "handshake da %(addr)s %(ago)d s fa (%(count)d richieste), "
        "ma nessun flusso sulla porta %(port)d",
        "handshake from %(addr)s %(ago)d s ago (%(count)d requests), "
        "but no stream on port %(port)d"),
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
    "status.media.offhours": (
        "fermo: fuori dalla fascia %(start)s\u2013%(end)s",
        "stopped: outside the %(start)s\u2013%(end)s window"),
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
    "status.nowplaying.idle": ("nessun brano in riproduzione", "nothing playing"),
    "status.nowplaying.playing": ("%(title)s — %(artist)s (da %(source)s)",
                                  "%(title)s — %(artist)s (from %(source)s)"),
    "status.nowplaying.paused": ("in pausa: %(title)s — %(artist)s",
                                 "paused: %(title)s — %(artist)s"),

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
    "settings.panel.lsb": ("Durata bit minimo (ns)", "Least significant bit (ns)"),
    "settings.panel.dither": ("Bit con dithering", "Dithered bits"),
    "settings.panel.slowdown": ("Rallentamento GPIO", "GPIO slowdown"),
    "settings.panel.depth.hint": (
        "Se le immagini con mezzi toni tremolano mentre i colori pieni restano "
        "fermi, il refresh reale è troppo basso: i pixel a intensità "
        "intermedia vengono accesi e spenti a una frequenza che l'occhio "
        "percepisce. Abbassare la <em>profondità PWM</em> risolve ma toglie "
        "sfumature. Questi due campi alzano il refresh <strong>tenendo</strong> "
        "la profondità: <em>durata bit minimo</em> accorcia ogni sotto-frame "
        "(130 ns è il predefinito, 100 dà circa un terzo di refresh in più, "
        "sotto gli 80 i toni scuri diventano imprecisi); <em>bit con "
        "dithering</em> rende i bit più bassi alternandoli nel tempo invece "
        "che con la durata — 1 bit raddoppia il refresh a parità di "
        "profondità dichiarata, al prezzo di un po' di brulichio sulle "
        "sfumature più fini.",
        "If images with mid-tones shimmer while solid colours stay still, the "
        "real refresh rate is too low: pixels at intermediate intensity are "
        "switched on and off at a rate the eye can follow. Lowering the "
        "<em>PWM depth</em> fixes it but costs shades. These two fields raise "
        "the refresh while <strong>keeping</strong> the depth: <em>least "
        "significant bit</em> shortens every sub-frame (130 ns is the "
        "default, 100 gives about a third more refresh, below 80 dark tones "
        "become inaccurate); <em>dithered bits</em> renders the lowest bits by "
        "alternating them over time instead of by duration — 1 bit doubles the "
        "refresh at the same nominal depth, at the cost of some shimmer on the "
        "finest gradients."),
    "settings.panel.profile": ("Profilo di registro del chip", "Chip register profile"),
    "settings.panel.registri": ("Registri RGB forzati", "Forced RGB registers"),
    "settings.panel.registri.vuoto": ("vuoto = quelli del profilo qui sopra",
                                      "empty = the ones from the profile above"),
    "settings.panel.registri.hint": (
        "Scavalca il blocco di registro RGB del profilo. Parole esadecimali "
        "di quattro cifre separate da virgola, uguali per i tre canali, "
        "oppure una lista per canale nella forma R:…;G:…;B:… . Serve quando "
        "nessun profilo del catalogo va bene del tutto e si vuole provare "
        "una parola sola alla volta partendo da uno che funziona. Campo "
        "vuoto = si torna al profilo, che è sempre la via d'uscita.",
        "Overrides the profile's RGB register block. Four-digit hex words "
        "separated by commas, the same for all three channels, or one list "
        "per channel as R:…;G:…;B:… . Use it when no catalog profile is quite "
        "right and you want to try a single word at a time starting from one "
        "that works. Empty = back to the profile, which is always the way "
        "out."),
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
    "media.timer": ("Fascia oraria", "Time window"),
    "media.timer.hint": (
        "Le ore in cui il Media Player pu\u00f2 lavorare. Fuori dalla fascia il "
        "servizio si ferma davvero \u2014 niente decodifica, niente letture "
        "dalla scheda SD \u2014 e riparte da solo quando la fascia si riapre.",
        "The hours during which the Media Player may work. Outside the window "
        "the service really stops \u2014 no decoding, no reads from the SD "
        "card \u2014 and starts again by itself when the window reopens."),
    "media.timer.enabled": (
        "Rispetta la fascia oraria (spento: il Media Player lavora sempre)",
        "Respect the time window (off: the Media Player always works)"),
    "media.timer.sleep": (
        "Lo Sleep mode ha comunque la precedenza: dentro la fascia di Sleep il "
        "pannello resta spento anche se il Media Player \u00e8 nella sua. La "
        "fascia pu\u00f2 scavalcare la mezzanotte.",
        "Sleep mode still takes precedence: during the Sleep window the panel "
        "stays off even if the Media Player is inside its own. The window may "
        "cross midnight."),
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

    # --------------------------------------------------------------- now playing
    "nowplaying.title": ("Now Playing", "Now Playing"),
    "nowplaying.intro": (
        "Il DMD mostra che cosa stai ascoltando: titolo, artista, album, stato "
        "e avanzamento del brano. Non riproduce audio e non si mette in mezzo "
        "fra la musica e le casse: si limita ad ascoltare i metadati.",
        "The DMD shows what you are listening to: title, artist, album, state "
        "and progress. It plays no audio and never sits between the music and "
        "your speakers: it only listens for the metadata."),
    "nowplaying.coverage.title": ("Che cosa viene rilevato", "What gets picked up"),
    "nowplaying.coverage.airplay": (
        "Tutto quello che parte da un iPhone, un iPad o un Mac via AirPlay, "
        "purché il DMD sia selezionato fra le casse. Non conta l'applicazione: "
        "Apple Music, Spotify, Amazon Music, YouTube funzionano allo stesso modo.",
        "Anything sent from an iPhone, iPad or Mac over AirPlay, as long as the "
        "DMD is selected among the speakers. The app does not matter: Apple "
        "Music, Spotify, Amazon Music and YouTube all work the same way."),
    "nowplaying.coverage.spotify": (
        "Spotify anche quando non passa da AirPlay: casse Connect, computer, "
        "Echo. Lo stato arriva direttamente da Spotify.",
        "Spotify even when it does not go through AirPlay: Connect speakers, "
        "computers, Echo devices. The state comes straight from Spotify."),
    "nowplaying.coverage.external": (
        "Qualunque altra cosa, tramite un JSON pubblicato su MQTT da "
        "un'automazione di Home Assistant.",
        "Anything else, through a JSON message published to MQTT by a Home "
        "Assistant automation."),
    "nowplaying.coverage.gap": (
        "Resta fuori la musica che nasce e muore su un altro apparecchio senza "
        "passare di qui: un HomePod a cui chiedi un brano a voce, o Amazon "
        "Music su un Echo. Per quelli serve Home Assistant, che li legge e "
        "ripubblica sul topic esterno qui sotto.",
        "What stays out is music that starts and ends on another device "
        "without passing through here: a HomePod asked by voice, or Amazon "
        "Music on an Echo. Those need Home Assistant, which can read them and "
        "republish to the external topic below."),
    "nowplaying.priority.hint": (
        "Mentre suona qualcosa il player resta a schermo al posto di foto e "
        "banner, ma lascia passare Air Radar e si toglie di mezzo appena "
        "arrivano frame da Batocera.",
        "While something is playing the player stays on screen instead of "
        "photos and banners, but it lets Air Radar through and steps aside as "
        "soon as frames arrive from Batocera."),
    "nowplaying.current": ("In riproduzione adesso", "Playing now"),
    "nowplaying.nothing": ("Niente in riproduzione.", "Nothing playing."),
    "nowplaying.source": ("Sorgente", "Source"),
    "nowplaying.device": ("Dispositivo", "Device"),
    "nowplaying.test": ("Prova senza musica", "Try it without music"),
    "nowplaying.test.hint": (
        "Mette un brano finto nello stato del player, per vedere subito come "
        "viene sul pannello senza dover far partire nulla. Sparisce da solo.",
        "Puts a fake track into the player state, so you can see how it looks "
        "on the panel without starting anything. It clears itself."),
    "nowplaying.test.button": ("Mostra un brano di prova", "Show a test track"),

    "nowplaying.broker": ("Broker MQTT", "MQTT broker"),
    "nowplaying.broker.hint": (
        "I metadati di AirPlay arrivano qui passando da un broker MQTT. Il "
        "valore predefinito è un Mosquitto installato sul Raspberry stesso: "
        "così la funzione lavora da sola, senza Home Assistant. Se hai già un "
        "broker sotto Home Assistant, scrivi quel suo indirizzo e ottieni le "
        "due cose insieme.",
        "AirPlay metadata reaches the DMD through an MQTT broker. The default "
        "is a Mosquitto running on the Raspberry Pi itself, so the feature "
        "works on its own without Home Assistant. If you already run a broker "
        "under Home Assistant, put its address here and get both at once."),
    "nowplaying.mqtt.enabled": ("Collega il DMD al broker",
                                "Connect the DMD to the broker"),
    "nowplaying.mqtt.host": ("Indirizzo", "Address"),
    "nowplaying.mqtt.username": ("Utente", "Username"),
    "nowplaying.mqtt.password": ("Password", "Password"),
    "nowplaying.mqtt.password.hint": (
        "La password non finisce mai in un file di configurazione esportato: "
        "viene tolta all'esportazione e va riscritta dopo un'importazione.",
        "The password never ends up in an exported configuration file: it is "
        "stripped on export and must be typed again after an import."),
    "nowplaying.mqtt.client_id": ("Nome del client", "Client name"),
    "nowplaying.mqtt.base_topic": ("Topic di base del DMD", "DMD base topic"),
    "nowplaying.mqtt.shairport": ("Topic di shairport-sync", "shairport-sync topic"),
    "nowplaying.mqtt.shairport.hint": (
        "Lo stesso valore scritto in `mqtt.topic` dentro "
        "/etc/shairport-sync.conf. Il DMD si iscrive a tutto quello che ci sta "
        "sotto.",
        "The same value set as `mqtt.topic` in /etc/shairport-sync.conf. The "
        "DMD subscribes to everything below it."),
    "nowplaying.mqtt.external": ("Topic esterno", "External topic"),
    "nowplaying.mqtt.external.hint": (
        "Topic facoltativo su cui qualsiasi cosa può pubblicare un JSON con "
        "title, artist, album, duration, position e playing. Serve a coprire "
        "gli apparecchi che il DMD non vede da solo. Lascialo vuoto per non "
        "ascoltare nulla.",
        "Optional topic where anything can publish a JSON with title, artist, "
        "album, duration, position and playing. It covers devices the DMD "
        "cannot see by itself. Leave it empty to listen to nothing."),
    "nowplaying.mqtt.missing": (
        "La libreria MQTT non è installata. Sul Raspberry: "
        "sudo apt install %(package)s",
        "The MQTT library is not installed. On the Raspberry Pi: "
        "sudo apt install %(package)s"),
    "nowplaying.setup.hint": (
        "Se non hai ancora preparato il sistema, non compilare queste caselle "
        "a mano: c'è uno script che installa e configura tutto, e le riempie "
        "lui. Da SSH sul Raspberry: %(command)s",
        "If you have not set the system up yet, do not fill these fields in by "
        "hand: a script installs and configures everything and fills them in "
        "for you. Over SSH on the Raspberry Pi: %(command)s"),
    "nowplaying.mqtt.state": ("Stato", "State"),
    "nowplaying.mqtt.connected": ("connesso a %(host)s:%(port)s",
                                  "connected to %(host)s:%(port)s"),
    "nowplaying.mqtt.disconnected": ("non connesso", "not connected"),
    "nowplaying.mqtt.off": ("disattivato", "disabled"),
    "nowplaying.mqtt.messages": ("%(count)d messaggi ricevuti",
                                 "%(count)d messages received"),
    "nowplaying.mqtt.apply": ("Salva e riconnetti", "Save and reconnect"),

    "nowplaying.hass": ("Home Assistant", "Home Assistant"),
    "nowplaying.hass.enabled": ("Crea le entità automaticamente",
                                "Create the entities automatically"),
    "nowplaying.hass.hint": (
        "Il DMD si presenta da solo a Home Assistant tramite MQTT Discovery. "
        "Compare un dispositivo con il brano in riproduzione, un interruttore "
        "per ogni servizio e la luminosità, tutti comandabili. Se Home "
        "Assistant non c'è, questi messaggi non li legge nessuno e non "
        "cambia niente.",
        "The DMD announces itself to Home Assistant through MQTT Discovery. A "
        "device appears with the current track, a switch for every service and "
        "the brightness, all controllable. If Home Assistant is not there, "
        "nobody reads those messages and nothing changes."),
    "nowplaying.hass.birth": (
        "Non serve sorvegliare Home Assistant: quando riparte lo annuncia da "
        "solo sul topic %(topic)s, e il DMD si ridichiara. In più le "
        "dichiarazioni restano depositate sul broker, che le riconsegna a chi "
        "si collega dopo. I due pulsanti qui sotto servono solo come "
        "scorciatoia manuale.",
        "There is no need to watch Home Assistant: when it restarts it "
        "announces itself on %(topic)s and the DMD re-declares. On top of "
        "that the declarations stay on the broker, which hands them to "
        "whoever subscribes later. The two buttons below are just a manual "
        "shortcut."),
    "nowplaying.hass.announce": ("Ridichiara le entità", "Re-declare the entities"),
    "nowplaying.hass.announced": ("Entità ridichiarate.", "Entities re-declared."),
    "nowplaying.hass.disabled": (
        "Non ho ridichiarato nulla: il broker o la creazione automatica sono "
        "disattivati.",
        "Nothing was re-declared: the broker or the automatic creation is "
        "disabled."),
    "nowplaying.hass.remove": ("Rimuovi le entità", "Remove the entities"),
    "nowplaying.hass.removed": (
        "Entità rimosse da Home Assistant.", "Entities removed from Home Assistant."),
    "nowplaying.hass.remove.hint": (
        "Cancella il dispositivo da Home Assistant. Da usare se cambi "
        "identificativo o se smetti di usare l'integrazione: senza, le "
        "vecchie entità resterebbero depositate sul broker come fantasmi.",
        "Deletes the device from Home Assistant. Use it if you change the "
        "device id or stop using the integration: without it the old entities "
        "would stay on the broker as ghosts."),
    "nowplaying.hass.prefix": ("Prefisso discovery", "Discovery prefix"),
    "nowplaying.hass.node": ("Identificativo del dispositivo", "Device id"),
    "nowplaying.hass.device": ("Nome mostrato", "Displayed name"),

    "nowplaying.spotify": ("Spotify", "Spotify"),
    "nowplaying.spotify.hint": (
        "Serve solo per la musica che non passa da AirPlay. Se ascolti "
        "Spotify dall'iPhone mandandolo al DMD come cassa, questa sezione "
        "puoi lasciarla spenta.",
        "This is only for music that does not go through AirPlay. If you play "
        "Spotify from your iPhone and send it to the DMD as a speaker, you can "
        "leave this section off."),
    "nowplaying.spotify.enabled": ("Interroga Spotify", "Poll Spotify"),
    "nowplaying.spotify.client_id": ("Client ID", "Client ID"),
    "nowplaying.spotify.redirect": ("Indirizzo di ritorno", "Redirect URI"),
    "nowplaying.spotify.redirect.hint": (
        "Va registrato identico nella tua applicazione su Spotify. Deve "
        "restare un indirizzo di loopback: Spotify non accetta più http su un "
        "indirizzo di rete.",
        "It must be registered exactly like this in your Spotify application. "
        "Keep it a loopback address: Spotify no longer accepts plain http on a "
        "network address."),
    "nowplaying.spotify.poll": ("Ogni quanti secondi", "Poll every (s)"),
    "nowplaying.spotify.steps": ("Come si collega", "How to link it"),
    "nowplaying.spotify.step1": (
        "Su developer.spotify.com crea un'applicazione e copia qui il suo "
        "Client ID. Il segreto non serve.",
        "On developer.spotify.com create an application and copy its Client ID "
        "here. The secret is not needed."),
    "nowplaying.spotify.step2": (
        "Nella stessa applicazione aggiungi l'indirizzo di ritorno qui sopra, "
        "scritto identico.",
        "In the same application add the redirect URI above, written exactly "
        "the same."),
    "nowplaying.spotify.step3": (
        "Salva, poi premi il pulsante qui sotto e apri l'indirizzo dal browser "
        "di un computer qualsiasi.",
        "Save, then press the button below and open the address in the browser "
        "of any computer."),
    "nowplaying.spotify.step4": (
        "Dopo aver autorizzato, la pagina non si aprirà: è previsto. Copia "
        "l'intero indirizzo dalla barra del browser e incollalo qui.",
        "After authorising, the page will not load: that is expected. Copy the "
        "whole address from the browser bar and paste it here."),
    "nowplaying.spotify.authorize": ("Genera l'indirizzo di autorizzazione",
                                     "Generate the authorisation address"),
    "nowplaying.spotify.open": ("Apri questo indirizzo nel browser",
                                "Open this address in your browser"),
    "nowplaying.spotify.paste": ("Indirizzo o codice di ritorno",
                                 "Returned address or code"),
    "nowplaying.spotify.complete": ("Collega l'account", "Link the account"),
    "nowplaying.spotify.connected": ("account collegato: %(name)s",
                                     "account linked: %(name)s"),
    "nowplaying.spotify.connected.anon": ("account collegato", "account linked"),
    "nowplaying.spotify.notconnected": ("account non collegato",
                                        "account not linked"),
    "nowplaying.spotify.disconnect": ("Scollega l'account", "Unlink the account"),
    "nowplaying.spotify.tokens.hint": (
        "I token restano in /var/lib/dmd/spotify.json, leggibile solo da root, "
        "e non finiscono mai nel file di configurazione esportato.",
        "The tokens live in /var/lib/dmd/spotify.json, readable only by root, "
        "and never end up in an exported configuration file."),
    "nowplaying.spotify.ok": ("Account collegato.", "Account linked."),
    "nowplaying.spotify.failed": ("Collegamento non riuscito: %(error)s",
                                  "Linking failed: %(error)s"),
    "nowplaying.spotify.gone": ("Account scollegato.", "Account unlinked."),

    "nowplaying.appearance": ("Aspetto sul pannello", "Panel appearance"),
    "nowplaying.color.title": ("Titolo", "Title"),
    "nowplaying.color.artist": ("Artista", "Artist"),
    "nowplaying.color.album": ("Album", "Album"),
    "nowplaying.color.bar": ("Barra di avanzamento", "Progress bar"),
    "nowplaying.safe_colors": ("Solo colori pieni", "Fully saturated colours only"),
    "nowplaying.safe_colors.hint": (
        "Porta ogni componente a 0 o 255, lasciando otto colori in tutto. Sono "
        "gli stessi otto di una PNG a palette, gli unici che su questo "
        "pannello non tremolano: le intensità intermedie sono la causa dello "
        "sfarfallio, non il numero di colori. La differenza fra le righe si "
        "ottiene cambiando tinta invece che luminosità.",
        "Rounds every channel to 0 or 255, leaving eight colours in total. "
        "They are the same eight as a palette PNG, the only ones that do not "
        "flicker on this panel: intermediate intensities cause the flicker, "
        "not the number of colours. The hierarchy between lines comes from "
        "changing hue rather than brightness."),
    "nowplaying.hold": ("Permanenza in pausa (s)", "Hold when paused (s)"),
    "nowplaying.hold.hint": (
        "Quanto resta a schermo un brano messo in pausa prima di restituire il "
        "display. Un brano in riproduzione non scade mai da solo.",
        "How long a paused track stays on screen before handing the display "
        "back. A playing track never expires on its own."),
    "nowplaying.nocover": (
        "La copertina dell'album non viene mostrata di proposito: a 64 pixel "
        "sarebbe illeggibile, ed essendo fatta quasi solo di mezzi toni "
        "sarebbe il contenuto peggiore possibile per questo pannello.",
        "Album artwork is deliberately not shown: at 64 pixels it would be "
        "unreadable, and being made almost entirely of mid-tones it would be "
        "the worst possible content for this panel."),
    "nowplaying.panel.playing": ("in riproduzione", "playing"),
    "nowplaying.panel.paused": ("in pausa", "paused"),

    "radar.route_color": ("Colore della rotta", "Route colour"),
    "radar.route_color.hint": (
        "La rotta ha una riga sua, al centro, fra il numero di volo e i "
        "dettagli: quello spazio prima restava vuoto, e su una riga sola i "
        "nomi lunghi facevano scartare modello e quota. Lascia il colore "
        "vuoto per usare lo stesso dei dettagli.",
        "The route has its own line, in the middle, between the flight number "
        "and the details: that space used to be empty, and on a single line "
        "long names pushed the model and altitude out. Leave the colour empty "
        "to use the same as the details."),

    # ------------------------------------------------------ conversioni codici
    "lookup.title": ("Conversioni dei codici", "Code translations"),
    "lookup.intro": (
        "Il radar riceve sigle: il modello arriva come designatore ICAO "
        "(B738), gli aeroporti delle rotte come codice IATA (MXP) oppure "
        "ICAO (LIMC), a seconda di che cosa risponde il servizio delle "
        "rotte. Queste due tabelle li trasformano in nomi leggibili. Un "
        "codice che non è in tabella viene mostrato com'è: non è un errore.",
        "The radar receives codes: the aircraft model as an ICAO designator "
        "(B738), route airports as either an IATA code (MXP) or an ICAO one "
        "(LIMC), depending on what the route service answers. These two "
        "tables turn them into readable names. A code that is not in the "
        "table is shown as it is: that is not an error."),
    "lookup.iata.warning": (
        "Gli aeroporti si possono scrivere con entrambi i codici sulla "
        "stessa riga, separati da una barra: MXP/LIMC. Il servizio delle "
        "rotte a volte risponde con il codice IATA di tre lettere e a volte "
        "con quello ICAO di quattro: basta che uno dei due corrisponda. La "
        "tabella di partenza li porta già tutti e due.",
        "Airports can carry both codes on the same row, separated by a "
        "slash: MXP/LIMC. The route service sometimes answers with the "
        "three-letter IATA code and sometimes with the four-letter ICAO one: "
        "either match is enough. The bundled table already carries both."),
    "lookup.format": (
        "Una riga per voce: codice, forma breve, nome completo. Nella prima "
        "colonna si possono mettere più codici separati da una barra, e la "
        "riga risponde a tutti. La forma "
        "breve va sul pannello, dove lo spazio è poco; il nome completo nella "
        "web UI e nel registro. Le righe che iniziano con # sono commenti, e "
        "una riga sbagliata si perde da sola senza compromettere le altre.",
        "One row per entry: code, short form, full name. The first column can "
        "hold several codes separated by a slash, and the row answers to all "
        "of them. The short form goes "
        "on the panel, where space is tight; the full name in the web "
        "interface and the log. Rows starting with # are comments, and a "
        "broken row is dropped on its own without affecting the others."),
    "lookup.persist": (
        "I file vivono in %(dir)s e non vengono mai sovrascritti dagli "
        "aggiornamenti: le tue aggiunte restano.",
        "The files live in %(dir)s and are never overwritten by updates: your "
        "additions stay."),
    "lookup.aircraft": ("Modelli di aeromobile", "Aircraft models"),
    "lookup.airport": ("Aeroporti", "Airports"),
    "lookup.airline": ("Compagnie aeree", "Airlines"),
    "lookup.airline.hint": (
        "Il codice è il prefisso di tre lettere del nominativo di volo: in "
        "AFR1732 la compagnia è AFR, cioè Air France. È il designatore ICAO, "
        "non la sigla IATA di due lettere che compare sul biglietto. I voli "
        "senza compagnia — aviazione generale, che usa l'immatricolazione — "
        "non mostrano nulla in quel campo, invece di inventarsi una sigla.",
        "The code is the three-letter prefix of the callsign: in AFR1732 the "
        "airline is AFR, that is Air France. It is the ICAO designator, not "
        "the two-letter IATA code printed on the ticket. Flights with no "
        "airline — general aviation, which uses the registration — show "
        "nothing in that field instead of inventing a code."),
    "lookup.count": ("%(count)d voci in tabella", "%(count)d entries in the table"),
    "lookup.saved": ("Salvato: %(count)d voci valide.",
                     "Saved: %(count)d valid entries."),
    "lookup.saved.errors": (
        "Salvato: %(count)d voci valide, %(errors)d righe scartate.",
        "Saved: %(count)d valid entries, %(errors)d rows dropped."),
    "lookup.errors": ("Righe scartate", "Dropped rows"),
    "lookup.error.row": ("riga %(row)d: %(reason)s", "row %(row)d: %(reason)s"),
    "lookup.reload": ("Rileggi i file dal disco", "Re-read the files from disk"),
    "lookup.reload.hint": (
        "Serve solo se hai modificato i file da fuori e vuoi vedere subito "
        "l'effetto: normalmente il sistema si accorge da sé che sono cambiati.",
        "Only needed if you edited the files elsewhere and want to see the "
        "effect immediately: normally the system notices the change by itself."),
    "lookup.reloaded": ("File riletti.", "Files re-read."),
    "lookup.unknown": ("Codici incontrati e non tradotti",
                       "Codes seen and not translated"),
    "lookup.unknown.hint": (
        "Ordinati per quante volte sono passati davvero: è la lista di cosa "
        "conviene aggiungere per primo, invece di doverlo indovinare.",
        "Sorted by how often they actually appeared: this is the list of what "
        "is worth adding first, instead of having to guess."),
    "lookup.unknown.none": ("Nessuno: tutto quello che è passato era in tabella.",
                            "None: everything seen so far was in the table."),
    "lookup.unknown.times": ("%(count)d volte", "%(count)d times"),
    "lookup.add": ("Aggiungi in coda al file", "Append them to the file"),
    "lookup.add.hint": (
        "Aggiunge i codici come righe da completare, con le due colonne del "
        "nome vuote. Finché restano vuote non traducono nulla, ma il codice è "
        "lì e non devi più andarlo a cercare.",
        "Adds the codes as rows to fill in, with the two name columns empty. "
        "While empty they translate nothing, but the code is there and you no "
        "longer have to hunt for it."),
    "lookup.added": ("Aggiunti %(count)d codici da completare.",
                     "Added %(count)d codes to fill in."),
    "lookup.added.none": ("Nessun codice nuovo da aggiungere.",
                          "No new code to add."),
    "lookup.forget": ("Azzera l'elenco", "Clear the list"),

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
    # Corta di proposito: e' la prima di tre caselle affiancate, e
    # un'etichetta che va a capo sfalsa la riga.
    "radar.overflow": ("Disposizione informazioni", "Details layout"),
    "radar.overflow.hint": (
        "La riga in basso è larga 256 pixel: oltre i quattro o cinque campi "
        "qualcosa deve cedere. Le pagine non perdono nulla e lasciano il "
        "pannello fermo; lo scorrimento si legge senza attese ma tiene il "
        "testo sempre in movimento. Finché i campi ci stanno tutti le tre "
        "scelte si comportano allo stesso modo. Con lo scorrimento la durata "
        "a schermo diventa un minimo: una passata iniziata arriva in fondo, "
        "e si cambia aereo quando il testo è uscito del tutto.",
        "The bottom line is 256 pixels wide: past four or five fields "
        "something has to give. Pages lose nothing and keep the panel still; "
        "scrolling reads without waiting but keeps the text always moving. As "
        "long as every field fits, the three choices behave identically. With "
        "scrolling the time on screen becomes a minimum: a pass that has "
        "started runs to the end, and the aircraft changes once the text has "
        "left the panel."),
    "radar.overflow.crop": ("Accorcia la riga (comportamento storico)",
                            "Shorten the line (historical behaviour)"),
    "radar.overflow.pages": ("A pagine, a turno", "Pages, in turn"),
    "radar.overflow.scroll": ("Scorrevole", "Scrolling"),
    "radar.page_seconds": ("Secondi per pagina", "Seconds per page"),
    "radar.scroll_speed": ("Velocità (px/s)", "Speed (px/s)"),
    "radar.scroll_fps": ("Fotogrammi al secondo", "Frames per second"),
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
    "radar.field.airline": ("Compagnia aerea", "Airline"),
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
    "services.desc.nowplaying": (
        "Titolo, artista e avanzamento del brano in ascolto, da AirPlay o Spotify.",
        "Title, artist and progress of the current track, from AirPlay or Spotify."),
    "services.desc.status_player": ("Notifiche sui giochi avviati dagli amici su Batocera.",
                                    "Notifications about games your friends launch on Batocera."),
    "nav.updates": ("Aggiornamenti", "Updates"),
    "updates.intro": (
        "Qui si aggiorna il sistema: il programma dal repository e la "
        "libreria della matrice. Sono le uniche due cose che cambiano il "
        "software installato invece di regolarlo, ed è la ragione per cui "
        "stanno fuori dalle Impostazioni.",
        "This is where the system gets updated: the program from the "
        "repository and the matrix library. They are the only two things "
        "that change the installed software rather than tune it, which is "
        "why they live outside Settings."),
    # ----------------------------------------------------------------- rifiuti
    "nav.scadenze": ("Scadenze", "Deadlines"),
    "scadenze.title": ("Scadenze e appuntamenti", "Deadlines and appointments"),
    "scadenze.intro": (
        "Un semaforo a destra dell\u2019orologio dice se c\u2019\u00e8 qualcosa "
        "in arrivo, e ogni tanto il pannello mostra che cosa. Le scadenze si "
        "scrivono qui, si importano da un CSV, o arrivano da Home Assistant.",
        "A traffic light to the right of the clock says whether something is "
        "due, and now and then the panel shows what. Deadlines are written "
        "here, imported from a CSV, or sent from Home Assistant."),
    "scadenze.aperte": ("Scadenze aperte", "Open deadlines"),
    "scadenze.nessuna": ("Nessuna scadenza aperta.", "No open deadlines."),
    "scadenze.nuova": ("Aggiungi una scadenza", "Add a deadline"),
    "scadenze.titolo": ("Titolo", "Title"),
    "scadenze.data": ("Scadenza", "Due date"),
    "scadenze.cadenza": ("Ricorrenza", "Recurrence"),
    "scadenze.descrizione": ("Descrizione", "Description"),
    "scadenze.aggiungi": ("Aggiungi", "Add"),
    "scadenze.completa": ("Fatto", "Done"),
    "scadenze.riapri": ("Annulla", "Undo"),
    "scadenze.elimina": ("Elimina", "Delete"),
    "scadenze.giorni": ("giorni", "days"),
    "scadenze.cadenza.una_tantum": ("Una tantum", "One-off"),
    "scadenze.cadenza.mensile": ("Mensile", "Monthly"),
    "scadenze.cadenza.bimestrale": ("Bimestrale", "Every two months"),
    "scadenze.cadenza.trimestrale": ("Trimestrale", "Quarterly"),
    "scadenze.cadenza.semestrale": ("Semestrale", "Every six months"),
    "scadenze.cadenza.annuale": ("Annuale", "Yearly"),
    "scadenze.stato.spento": ("lontana", "far off"),
    "scadenze.stato.verde": ("in avvicinamento", "approaching"),
    "scadenze.stato.giallo": ("vicina", "close"),
    "scadenze.stato.rosso": ("imminente", "imminent"),
    "scadenze.stato.scaduta": ("SCADUTA", "OVERDUE"),
    "scadenze.csv": ("Elenco in formato CSV", "List in CSV format"),
    "scadenze.csv.hint": (
        "Una riga per scadenza: id;titolo;data;ricorrenza;descrizione;attiva;"
        "completate. Si pu\u00f2 incollare quello che esce da un foglio di "
        "calcolo \u2014 il separatore, punto e virgola o virgola, viene "
        "riconosciuto da solo, e le righe senza una data valida si saltano.",
        "One row per deadline: id;title;date;recurrence;description;active;"
        "completed. You can paste what a spreadsheet exports \u2014 the "
        "separator, semicolon or comma, is detected automatically, and rows "
        "without a valid date are skipped."),
    "scadenze.soglie": ("Semaforo", "Traffic light"),
    "scadenze.soglie.hint": (
        "Giorni che mancano alla scadenza. Oltre la soglia verde il semaforo "
        "resta spento: una scadenza fra un mese non \u00e8 una notizia, e un "
        "pannello che segnala sempre qualcosa non segnala pi\u00f9 niente. "
        "Superata la data, il rosso lampeggia.",
        "Days remaining. Beyond the green threshold the light stays off: "
        "something due in a month is not news, and a panel that always signals "
        "something signals nothing. Past the date, red blinks."),
    "scadenze.soglia_verde": ("Verde entro", "Green within"),
    "scadenze.soglia_giallo": ("Giallo entro", "Yellow within"),
    "scadenze.soglia_rosso": ("Rosso entro", "Red within"),
    "scadenze.sempre": ("Mostra le lampade anche quando sono tutte spente",
                        "Show the lamps even when they are all off"),
    "scadenze.avviso": ("Avviso sul pannello", "Panel reminder"),
    "scadenze.interval": ("Ogni (minuti)", "Every (minutes)"),
    "scadenze.seconds": ("Durata (secondi)", "Duration (seconds)"),
    "scadenze.speed": ("Velocit\u00e0 dello scorrimento", "Scroll speed"),
    "scadenze.registro": ("Registro", "Log"),
    "scadenze.registro.hint": (
        "Ogni occorrenza con l\u2019ora in cui \u00e8 stata inserita e quella "
        "in cui \u00e8 stata completata. Non si cancella mai: \u00e8 l\u2019unico "
        "posto in cui resta traccia di che cosa \u00e8 stato pagato e quando.",
        "Every occurrence with the time it was created and the time it was "
        "completed. Never erased: it is the only place where a record of what "
        "was paid, and when, survives."),
    "scadenze.registro.scarica": ("Scarica il registro CSV", "Download the CSV log"),
    "scadenze.panel.mancano": ("- %(giorni)dgg", "- %(giorni)dd"),
    "scadenze.panel.oggi": ("OGGI", "TODAY"),
    "scadenze.panel.scaduta": ("+%(giorni)dgg", "+%(giorni)dd"),
    "status.scadenze.nessuna": ("nessuna scadenza in vista", "no deadlines in sight"),
    "status.scadenze.attesa": ("%(count)d in scadenza, %(shown)d avvisi mostrati",
                               "%(count)d due, %(shown)d reminders shown"),
    "status.scadenze.mostra": ("in mostra: %(titolo)s", "showing: %(titolo)s"),
    "status.scadenze.errore": ("errore: %(error)s", "error: %(error)s"),
    "nav.giochi": ("Giochi", "Games"),
    "giochi.title": ("Giochi sul pannello", "Games on the panel"),
    "giochi.intro": (
        "Scritti per 256x64, non adattati da uno schermo 4:3: il campo di "
        "gioco prende i 200 pixel di sinistra e i 56 di destra sono il "
        "tabellone. Non sono un servizio ma una partita \u2014 si preme "
        "Gioca, tutti i servizi si fermano, si esce e riprendono da dove "
        "stavano.",
        "Written for 256x64, not adapted from a 4:3 screen: the playfield "
        "takes the left 200 pixels and the right 56 are the scoreboard. They "
        "are not a service but a game \u2014 press Play, every service stops, "
        "quit and they resume where they were."),
    "giochi.play": ("Gioca", "Play"),
    "giochi.esci": ("Esci dalla partita", "Quit the game"),
    "giochi.record": ("Record:", "High score:"),
    "giochi.breakout.hint": (
        "Il muro \u00e8 largo per natura, ed \u00e8 il gioco che soffre meno "
        "il pannello. Fra muro e racchetta ci sono trenta pixel invece di "
        "duecento: la palla parte lenta e accelera a ogni quattro mattoni.",
        "The wall is wide by nature, and this is the game the panel suits "
        "best. There are thirty pixels between wall and paddle instead of two "
        "hundred: the ball starts slow and speeds up every four bricks."),
    "giochi.invaders.hint": (
        "Tre file invece di cinque: su sessantaquattro righe la discesa "
        "originale non ci sta, e schiacciarla vorrebbe dire alieni alti due "
        "pixel. Un colpo per volta, e la schiera accelera man mano che si "
        "svuota.",
        "Three rows instead of five: the original descent does not fit in "
        "sixty-four rows, and squashing it would mean two-pixel aliens. One "
        "shot at a time, and the swarm speeds up as it empties."),
    "giochi.doom.hint": (
        "Doom gira come processo separato, per una ragione di licenza, e ha "
        "una pagina sua: preparazione, scelta del WAD e taratura della fascia.",
        "Doom runs as a separate process, for licensing reasons, and has its "
        "own page: setup, WAD choice and band tuning."),
    "giochi.doom.apri": ("Apri la pagina di Doom", "Open the Doom page"),
    "giochi.gb.apri": ("Apri la pagina di PyBoy", "Open the PyBoy page"),
    "giochi.esterni": ("Emulatori esterni", "External emulators"),
    "giochi.esterni.hint": (
        "Doom e il Game Boy non sono giochi scritti per il pannello: sono "
        "programmi che girano per conto loro e prendono il pannello per il "
        "tempo della partita. Ognuno ha la sua pagina, con la preparazione e "
        "la taratura dell'immagine.",
        "Doom and the Game Boy are not games written for the panel: they are "
        "programs that run on their own and take the panel for the length of "
        "a session. Each has its own page, with setup and picture tuning."),
    "giochi.doom.stato": ("WAD:", "WAD:"),
    "giochi.doom.si": ("pronto", "ready"),
    "giochi.doom.no": ("da preparare", "needs setup"),
    "giochi.comandi": ("Comandi", "Controls"),
    "giochi.comandi.hint": (
        "Si gioca dalla tastiera del cabinato o dal pad; questi pulsanti "
        "servono per provare senza alzarsi.",
        "Play from the cabinet keyboard or the pad; these buttons are for "
        "trying it out without getting up."),
    "giochi.controlli": ("Tastiera e joystick", "Keyboard and joystick"),
    "giochi.keyboard": ("Accetta comandi dalla tastiera",
                        "Accept commands from the keyboard"),
    "giochi.keyboard_starts": (
        "Un tasto pu\u00f2 far cominciare una partita (spento: il pannello non "
        "se lo porta via un tasto sfiorato per caso)",
        "A key may start a game (off: a key brushed by accident cannot take "
        "the panel away)"),
    "giochi.joystick": ("Accetta comandi dal joystick",
                        "Accept commands from the joystick"),
    "giochi.joystick_starts": (
        "Options sul pad pu\u00f2 far cominciare una partita",
        "Options on the pad may start a game"),
    "giochi.pad.trovati": ("Pad riconosciuti:", "Pads detected:"),
    "giochi.pad.nessuno": ("Nessun pad collegato in questo momento.",
                           "No pad connected right now."),
    "giochi.device.tastiera": ("Tastiera (percorso)", "Keyboard (path)"),
    "giochi.device.pad": ("Joystick (percorso)", "Joystick (path)"),
    "giochi.device.auto": ("automatico", "automatic"),
    "giochi.device.hint": (
        "Vuoto = tutti quelli che il kernel dichiara come tastiera o come "
        "joystick. Serve indicarne uno solo se il riconoscimento automatico "
        "sbaglia: il percorso \u00e8 del tipo /dev/input/event3, e si trova "
        "con «cat /proc/bus/input/devices».",
        "Empty = every device the kernel reports as a keyboard or a joystick. "
        "Naming one is only needed if automatic detection gets it wrong: the "
        "path looks like /dev/input/event3, and «cat /proc/bus/input/devices» "
        "lists them."),
    "giochi.ciclo.hint": (
        "Il tasto Start del pad scorre i giochi: premuto una volta si gioca, "
        "premuto ancora si passa al successivo. Select esce. Sulla tastiera "
        "del cabinato fanno lo stesso i due tasti qui sotto.",
        "The Start button on the pad cycles through the games: press once to "
        "play, press again for the next one. Select quits. On the cabinet "
        "keyboard the two keys below do the same."),
    "giochi.tasto.ciclo": ("Tasto che scorre i giochi",
                           "Key that cycles the games"),
    "giochi.tasto.esci": ("Tasto che esce dalla partita",
                          "Key that quits the game"),
    "giochi.impara": ("Impara", "Learn"),
    "giochi.impara.hint": (
        "I codici predefiniti sono quelli di invio ed escape. Una pulsantiera "
        "da flipper ne manda altri: premi «Impara» e poi il pulsante sul "
        "cabinato.",
        "The defaults are the codes for Enter and Escape. A pinball button "
        "panel sends different ones: press \u00abLearn\u00bb and then the "
        "button on the cabinet."),
    "giochi.impara.premi": ("In ascolto: premi ora il pulsante sul cabinato.",
                            "Listening: press the button on the cabinet now."),
    "giochi.impara.fatto": ("Riconosciuto, codice", "Recognised, code"),
    "giochi.ciclo_doom": (
        "Comprendi anche Doom nel giro dei giochi (parte in qualche secondo e "
        "vuole un WAD preparato)",
        "Include Doom in the game cycle too (it takes a few seconds to start "
        "and needs a prepared WAD)"),
    "giochi.ciclo_gameboy": ("Il tasto Start scorre anche il Game Boy",
                             "The Start button also cycles the Game Boy"),
    "giochi.ciclo_gameboy.hint": (
        "Entra nel giro solo se PyBoy è installato e la cartuccia scelta è "
        "valida. Mentre il Game Boy gioca, Start e Select appartengono alla "
        "console — servono a giocare — e per uscire si usa il tasto PS.",
        "It joins the rotation only if PyBoy is installed and the chosen "
        "cartridge is valid. While the Game Boy is playing, Start and Select "
        "belong to the console — they are game buttons — and the PS button "
        "is the way out."),
    "giochi.timeout": ("Chiudi la partita dopo (secondi senza comandi)",
                       "Close the game after (seconds with no input)"),
    "giochi.timeout.hint": (
        "Una partita lasciata a met\u00e0 non deve tenersi il pannello per "
        "sempre. Zero per non chiuderla mai.",
        "A game left half-played must not keep the panel forever. Zero to "
        "never close it."),
    "status.giochi.ferma": ("nessuna partita in corso", "no game running"),
    "status.giochi.partita": (
        "%(gioco)s: %(punteggio)d punti, %(vite)d vite",
        "%(gioco)s: %(punteggio)d points, %(vite)d lives"),
    "nav.rifiuti": ("Rifiuti", "Waste"),
    "rifiuti.title": ("Raccolta rifiuti e attività comunali",
                      "Waste collection and municipal activities"),
    "rifiuti.intro": (
        "La raccolta non è un elenco di date, è una regola: due o tre giorni "
        "fissi alla settimana per ogni frazione, e qualche eccezione all'anno "
        "per le feste. Scritta la regola, le date si calcolano da sole — "
        "senza dipendere da nessun servizio esterno e senza niente che si "
        "possa rompere. Le voci compaiono a sinistra dell'orologio, ciascuna "
        "col suo colore.",
        "Collection is not a list of dates, it is a rule: two or three fixed "
        "days a week per stream, plus a handful of exceptions a year for "
        "holidays. Write the rule and the dates follow — with no external "
        "service to depend on and nothing that can break. The entries appear "
        "to the left of the clock, each in its own colour."),
    "rifiuti.now": ("Da esporre adesso:", "To put out now:"),
    "rifiuti.now.none": ("Adesso non c'è niente da esporre.",
                         "Nothing to put out right now."),
    "rifiuti.voci": ("Frazioni e attività", "Streams and activities"),
    "rifiuti.voci.hint": (
        "Una voce senza nessun giorno spuntato non compare da nessuna parte: "
        "è così che si spegne quello che il tuo comune non raccoglie.",
        "An entry with no day ticked appears nowhere: that is how you switch "
        "off what your municipality does not collect."),
    "rifiuti.nome": ("Nome", "Name"),
    "rifiuti.colore": ("Colore", "Colour"),
    "rifiuti.tipo": ("Tipo", "Kind"),
    "rifiuti.tipo.rifiuto": ("Rifiuto da esporre", "Waste to put out"),
    "rifiuti.tipo.attivita": ("Attività comunale (divieto)",
                              "Municipal activity (restriction)"),
    "rifiuti.cadenza": ("Cadenza", "Frequency"),
    "rifiuti.cadenza.settimanale": ("Ogni settimana", "Every week"),
    "rifiuti.cadenza.quindicinale": ("Ogni due settimane", "Every two weeks"),
    "rifiuti.cadenza.mensile_1_3": ("1° e 3° del mese", "1st and 3rd of the month"),
    "rifiuti.cadenza.mensile_2_4": ("2° e 4° del mese", "2nd and 4th of the month"),
    "rifiuti.riferimento": ("Data di riferimento", "Reference date"),
    "rifiuti.attiva": ("Attiva", "Active"),
    "rifiuti.ora_inizio": ("Divieto dalle", "Restriction from"),
    "rifiuti.ora_fine_divieto": ("Divieto fino alle", "Restriction until"),
    "rifiuti.prossima": ("Prossima: %(data)s", "Next: %(data)s"),
    "rifiuti.prossima.mai": ("Nessuna data nei prossimi mesi.",
                             "No date in the coming months."),
    "rifiuti.avviso": ("Avvisa dalle ore", "Warn from"),
    "rifiuti.fine": ("Togli l'avviso alle ore", "Clear the warning at"),
    "rifiuti.orari.hint": (
        "Il promemoria compare alle 18 della sera prima e sparisce alle 8 del "
        "giorno di raccolta: si espone il bidone la sera, e dopo il passaggio "
        "ricordarlo ancora sarebbe rumore. Per le attività comunali la fine è "
        "quella del divieto, che si imposta sulla singola voce.",
        "The reminder appears at 18:00 the evening before and clears at 08:00 "
        "on collection day: you put the bin out in the evening, and after the "
        "truck has been, still showing it would be noise. For municipal "
        "activities the end is the end of the restriction, set per entry."),
    "rifiuti.soppressioni": ("Giorni di mancato servizio", "Days with no service"),
    "rifiuti.soppressioni.hint": (
        "Una data per riga, «gg/mm/aaaa,voce,nota». La voce è facoltativa: "
        "lasciata vuota vale per tutte, che è il caso normale — quando la "
        "raccolta salta per una festività di solito salta tutta.",
        "One date per line, “dd/mm/yyyy,entry,note”. The entry is optional: "
        "left empty it applies to all, which is the normal case — when "
        "collection is skipped for a holiday it is usually skipped for all."),
    "rifiuti.straordinari": ("Giorni di servizio straordinario",
                             "Days with extra service"),
    "rifiuti.straordinari.hint": (
        "Stessa forma. Serve ai recuperi dopo una festività: «non si fa lunedì "
        "25, si recupera mercoledì 27» sono due righe, una per tabella. Uno "
        "straordinario vale anche in un giorno soppresso — è esattamente il "
        "caso del recupero, e sarebbe assurdo che si annullassero a vicenda.",
        "Same shape. It is for catch-ups after a holiday: “skipped on Monday "
        "the 25th, caught up on Wednesday the 27th” is two lines, one per "
        "table. An extra service counts even on a suppressed day — that is "
        "exactly what a catch-up is, and it would be absurd for the two to "
        "cancel out."),

    # -------------------------------------------------------------------- doom
    "nav.doom": ("Doom", "Doom"),
    "doom.title": ("Doom", "Doom"),
    "doom.intro": (
        "Doom non è un servizio che gira in sottofondo: è una partita. "
        "Premendo «Gioca» tutti i servizi si fermano e il pannello diventa "
        "suo — Batocera compreso — finché non esci o finché non lo lasci "
        "fermo abbastanza a lungo. Uscendo, tutto riprende da dove stava.",
        "Doom is not a service running in the background: it is a game. "
        "Press “Play” and every service stops, the panel becomes its own — "
        "Batocera included — until you leave or let it sit idle long enough. "
        "On leaving, everything resumes where it was."),
    "doom.play": ("Gioca", "Play"),
    "doom.leave": ("Esci dalla partita", "Leave the game"),
    "doom.pad": ("Comandi", "Controls"),
    "doom.pad.hint": (
        "I pulsanti si tengono premuti: tenendo il dito su una freccia si "
        "cammina davvero, invece di fare un passo alla volta.",
        "The buttons are held down: keeping your finger on an arrow really "
        "walks, instead of taking one step at a time."),
    "doom.keyboard.hint": (
        "Funziona anche la tastiera di questo computer — frecce o WASD, ctrl "
        "spara, spazio apre, shift corre — e quella collegata al Raspberry, "
        "che è la via più diretta: non passa dalla rete.",
        "The keyboard of this computer works too — arrows or WASD, ctrl "
        "fires, space opens, shift runs — and so does the one plugged into "
        "the Raspberry Pi, which is the most direct route: it does not go "
        "through the network."),
    "doom.key.fire": ("Fuoco", "Fire"),
    "doom.key.use": ("Apri", "Use"),
    "doom.key.run": ("Corri", "Run"),
    "doom.key.menu": ("Menu", "Menu"),
    "doom.key.enter": ("Invio", "Enter"),
    "doom.key.map": ("Mappa", "Map"),
    "doom.tuning": ("Immagine e partita", "Picture and game"),
    "doom.tuning.hint": (
        "Salvando si fa ripartire Doom: la fascia e la gamma stanno nella "
        "riga di comando del programma, non in un file che rilegge.",
        "Saving restarts Doom: the band and the gamma live on the program's "
        "command line, not in a file it re-reads."),
    "doom.band.top": ("Prima riga della fascia", "First row of the band"),
    "doom.band.height": ("Altezza della fascia", "Height of the band"),
    "doom.band.hint": (
        "Doom disegna 320×200, il pannello è 256×64: schiacciando tutto un "
        "nemico sarebbe alto otto pixel. Si ritaglia una fascia attorno "
        "all'orizzonte, dove stanno i nemici, e si buttano via pavimento e "
        "soffitto. Da riga 36 per 96 righe è il punto di partenza; la "
        "taratura vera si fa guardando il pannello.",
        "Doom draws 320×200 while the panel is 256×64: squashing it all would "
        "make an enemy eight pixels tall. A band around the horizon is cropped "
        "instead — that is where the enemies are — and floor and ceiling are "
        "thrown away. Row 36 for 96 rows is the starting point; the real "
        "tuning is done by looking at the panel."),
    "doom.gamma": ("Gamma", "Gamma"),
    "doom.gamma.hint": (
        "Doom è un gioco buio e un LED non ha il nero di un CRT: sotto 1 "
        "schiarisce. La difficoltà va da 1 a 5, e il livello si scrive "
        "«episodio mappa», per esempio «1 1».",
        "Doom is a dark game and an LED has none of a CRT's black: below 1 "
        "brightens it. Skill goes from 1 to 5, and the level is written "
        "“episode map”, for example “1 1”."),
    "doom.skill": ("Difficoltà", "Skill"),
    "doom.map": ("Livello iniziale", "Starting level"),
    "doom.timeout": ("Fine partita dopo (s)", "End game after (s)"),
    "doom.device": ("Tastiera da usare", "Keyboard to use"),
    "doom.device.auto": ("tutte quelle collegate", "every one connected"),
    "doom.device.found": ("Tastiere trovate: %(list)s",
                          "Keyboards found: %(list)s"),
    "doom.device.none": (
        "Nessuna tastiera collegata al Raspberry in questo momento. Si gioca "
        "lo stesso da questa pagina.",
        "No keyboard connected to the Raspberry Pi right now. You can still "
        "play from this page."),
    "doom.keyboard": ("Leggi la tastiera collegata al Raspberry",
                      "Read the keyboard plugged into the Raspberry Pi"),
    "doom.pad.device": ("Joystick da usare", "Joystick to use"),
    "doom.pad.read": ("Leggi i joystick collegati al Raspberry",
                      "Read the joysticks plugged into the Raspberry Pi"),
    "doom.pad.starts": ("Options sul pad può far cominciare una partita",
                        "Options on the pad can start a game"),
    "doom.pad.starts.hint": (
        "Nessun pulsante del pad fa cominciare Doom: Start e PS scorrono i "
        "giochi e Select esce, e sono gli stessi ovunque. A Doom ci si arriva "
        "dal giro dei giochi — se lo si \u00e8 incluso nella pagina Giochi — "
        "dal pulsante Gioca qui sopra, o da Home Assistant. Sul pad, durante "
        "la partita, L3 apre il menu di Doom e R3 conferma.",
        "No pad button starts Doom: Start and PS cycle the games and Select "
        "quits, and they mean the same everywhere. Doom is reached from the "
        "game cycle \u2014 if you included it on the Games page \u2014 from "
        "the Play button above, or from Home Assistant. On the pad, during a "
        "game, L3 opens Doom's menu and R3 confirms."),
    "doom.pad.found": ("Joystick trovati: %(list)s", "Joysticks found: %(list)s"),
    "doom.pad.none": (
        "Nessun joystick collegato al Raspberry in questo momento.",
        "No joystick connected to the Raspberry Pi right now."),
    "doom.pad.hint2": (
        "Con un pad PS4 o compatibile: levetta sinistra per camminare e per "
        "il passo laterale, levetta destra per girare, croce direzionale per "
        "camminare e girare. R2 o croce sparano, cerchio e quadrato aprono, "
        "L1 corre, triangolo è la mappa, Options il menu.",
        "With a PS4 or compatible pad: left stick to walk and strafe, right "
        "stick to turn, D-pad to walk and turn. R2 or cross fire, circle and "
        "square open, L1 runs, triangle is the map, Options the menu."),
    "doom.binary": ("Programma", "Program"),
    "doom.wad": ("WAD", "WAD"),
    "doom.nobinary": (
        "Doom non è ancora pronto: va preparato una volta sola, con il "
        "pulsante qui sotto.",
        "Doom is not ready yet: it has to be prepared once, with the button "
        "below."),
    "doom.stale": (
        "Il programma è stato compilato prima dell'ultimo aggiornamento: "
        "funziona, ma non è quello che dice il sorgente installato. "
        "Ricompilalo quando ti fa comodo.",
        "The program was compiled before the last update: it works, but it is "
        "not what the installed source says. Rebuild it whenever you like."),
    "doom.prep": ("Preparazione", "Preparation"),
    "doom.prep.hint": (
        "Doom ha bisogno di due cose che non arrivano con il pacchetto: il "
        "programma, che va compilato (i sorgenti sono GPL2 e questo progetto "
        "è GPLv3, quindi si scaricano al momento invece di essere inclusi), e "
        "un WAD, cioè il file con i livelli. Il pulsante fa entrambe le cose "
        "e ci mette un paio di minuti su un Raspberry 3B+.",
        "Doom needs two things the package does not carry: the program, which "
        "has to be compiled (the sources are GPL2 while this project is "
        "GPLv3, so they are fetched rather than bundled), and a WAD, the file "
        "with the levels. The button does both, and takes a couple of minutes "
        "on a Raspberry Pi 3B+."),
    "doom.prep.button": ("Prepara Doom", "Prepare Doom"),
    "doom.prep.again": ("Ricompila", "Rebuild"),
    "doom.prep.running": (
        "Preparazione in corso: scaricamento e compilazione. Un paio di "
        "minuti, e la pagina si aggiorna da sola quando ha finito.",
        "Preparation in progress: downloading and compiling. A couple of "
        "minutes, and the page refreshes itself when it is done."),
    "doom.prep.nolog": ("Mai preparato su questa macchina.",
                        "Never prepared on this machine."),
    "doom.wads": ("WAD trovati", "WADs found"),
    "doom.wads.hint": (
        "Il WAD è il file con i livelli, la grafica e i suoni. Freedoom è "
        "libero e lo scarica la preparazione. Quelli di id Software non si "
        "possono ridistribuire: se hai comprato Doom, copia il tuo "
        "(doom.wad, doom1.wad, doom2.wad…) nella cartella qui sopra e "
        "sceglilo da qui — la preparazione lo riconosce e non scarica "
        "Freedoom.",
        "The WAD is the file with the levels, artwork and sounds. Freedoom is "
        "free and the preparation downloads it. The id Software ones cannot "
        "be redistributed: if you bought Doom, copy yours (doom.wad, "
        "doom1.wad, doom2.wad…) into the folder above and pick it here — the "
        "preparation recognises it and skips the Freedoom download."),
    "doom.wads.none": (
        "Nessun WAD in %(dir)s. Premi «Prepara Doom» per scaricare Freedoom, "
        "oppure copia lì il tuo.",
        "No WAD in %(dir)s. Press “Prepare Doom” to download Freedoom, or "
        "copy yours there."),
    "doom.wad.dir": ("Cartella dei WAD", "WAD folder"),
    "doom.wad.share": ("Condivisione di rete", "Network share"),
    "doom.keyboard.starts": (
        "Un tasto sulla tastiera può far cominciare una partita",
        "A key on the keyboard can start a game"),
    "doom.keyboard.starts.hint": (
        "Spento, la partita comincia solo da «Gioca». Il DMD sta in mezzo a "
        "un flipper: un tasto sfiorato per caso non deve portarsi via il "
        "pannello a metà partita. A partita aperta la tastiera comanda "
        "comunque il gioco.",
        "Off, a game starts only from “Play”. The DMD sits in the middle of a "
        "pinball cabinet: a key brushed by accident must not take the panel "
        "away mid-game. Once a game is running the keyboard controls it "
        "regardless."),
    "doom.wad.free": ("libero", "free"),
    "doom.wad.use": ("Usa questo", "Use this one"),
    "doom.nowad": (
        "Manca il WAD %(path)s. Lo scarica «sudo /opt/dmd/doom/setup_doom.sh», "
        "oppure mettine uno tuo e correggi il percorso qui sotto.",
        "The WAD %(path)s is missing. “sudo /opt/dmd/doom/setup_doom.sh” "
        "downloads it, or put one of your own there and fix the path below."),
    "status.doom.idle": ("fermo: si comincia da «Gioca»",
                         "stopped: start it with “Play”"),
    "status.doom.playing": ("partita in corso, fermo da %(seconds)d s",
                            "game in progress, idle for %(seconds)d s"),
    "status.doom.stopped": ("programma non in esecuzione", "program not running"),
    "status.doom.error": ("Doom non parte: %(error)s", "Doom does not start: %(error)s"),

    "media.view": ("Vedi", "View"),
    # ---------------------------------------------------------- gestione media
    "nav.manager": ("Gestione media", "Media manager"),
    "manager.title": ("Gestione media", "Media manager"),
    "manager.hold": (
        "Pannello riservato alla gestione media: tutte le sorgenti sono "
        "sospese, ZeDMD compreso.",
        "The panel is reserved for the media manager: every source is on "
        "hold, ZeDMD included."),
    "manager.hint": (
        "Finché questa pagina resta aperta il pannello è tuo: nessun aereo, "
        "nessun compleanno e nessuna partita possono prendere il posto del "
        "file che stai guardando. Chiudendo la scheda il pannello torna al "
        "suo lavoro entro %(seconds)d secondi.",
        "While this page stays open the panel is yours: no aircraft, no "
        "birthday and no game can take the place of the file you are looking "
        "at. Close the tab and the panel goes back to work within "
        "%(seconds)d seconds."),
    "manager.exit": ("Esci dalla gestione", "Leave the manager"),
    "manager.view.hint": (
        "«Vedi» manda il file sul pannello, non nel browser: quello che conta "
        "è come viene lì, con quella scala e quei colori. Il file resta a "
        "schermo finché non ne scegli un altro.",
        "“View” sends the file to the panel, not to the browser: what matters "
        "is how it looks there, at that scale and with those colours. It stays "
        "on screen until you pick another one."),
    "media.manager.hint": (
        "L'elenco dei file, il caricamento e le anteprime sul pannello stanno "
        "nella Gestione media: entrandoci le sorgenti si fermano, così quello "
        "che guardi non viene scavalcato da un aereo o da una partita.",
        "The file list, uploads and panel previews live in the Media manager: "
        "entering it puts every source on hold, so what you are looking at is "
        "not pushed aside by an aircraft or a game."),
    "panel.manager": ("Gestione media", "Media manager"),
    "media.view.now": ("Sul pannello: %(name)s", "On the panel: %(name)s"),
    "media.view.failed": ("File non mostrabile.", "File cannot be shown."),
    "status.preview.showing": ("sul pannello: %(name)s", "on the panel: %(name)s"),
    "status.preview.idle": ("in attesa (%(count)d anteprime mostrate)",
                            "idle (%(count)d previews shown)"),
    "status.preview.error": ("ultima anteprima fallita: %(error)s",
                             "last preview failed: %(error)s"),
    "media.page": (
        "File da %(first)d a %(last)d di %(total)d — pagina %(page)d di %(pages)d",
        "Files %(first)d to %(last)d of %(total)d — page %(page)d of %(pages)d"),
    "services.desc.birthdays": (
        "Promemoria di compleanni e anniversari, a scorrimento, nei giorni "
        "precedenti la ricorrenza.",
        "Reminders for birthdays and anniversaries, scrolling, in the days "
        "before the date."),
    "services.desc.air_radar": ("Aerei in transito entro un raggio dalla posizione indicata.",
                                "Aircraft passing within a radius of the given position."),
    # -------------------------------------------------------------- game boy
    "nav.gameboy": ("Game Boy", "Game Boy"),
    "gb.title": ("Game Boy", "Game Boy"),
    "gb.intro": (
        "L'emulatore gira come processo separato e prende il pannello per il "
        "tempo della partita, come Doom. Lo schermo del Game Boy \u00e8 160\u00d7144: "
        "portato a 64 righe tenendo le proporzioni sta in 71 pixel al centro "
        "del pannello, con il resto spento.",
        "The emulator runs as a separate process and takes the panel for the "
        "length of the session, like Doom. The Game Boy screen is 160\u00d7144: "
        "scaled to 64 rows keeping its proportions it occupies 71 pixels in "
        "the middle of the panel, with the rest dark."),
    "gb.prep": ("Preparazione", "Setup"),
    "gb.prep.hint": (
        "Installa l'emulatore PyBoy e apre la condivisione %(cartella)s dove "
        "mettere le ROM. Si fa una volta sola: l'aggiornamento del DMD passa "
        "dalla rete e non tocca i pacchetti di sistema.",
        "Installs the PyBoy emulator and opens the %(cartella)s share where "
        "the ROMs go. Once only: DMD updates come over the network and do not "
        "touch system packages."),
    "gb.prep.avvia": ("Installa l'emulatore e apri la condivisione",
                      "Install the emulator and open the share"),
    "gb.prep.ripeti": ("Ripeti la preparazione", "Run the setup again"),
    "gb.prep.pyboy": ("Emulatore PyBoy", "PyBoy emulator"),
    "gb.prep.cartella": ("Cartella delle ROM", "ROM folder"),
    "gb.prep.condivisione": ("Condivisione SMB", "SMB share"),
    "gb.si": ("presente", "present"),
    "gb.no": ("da fare", "to do"),
    "gb.prep.corso": ("Installazione in corso\u2026", "Installing\u2026"),
    "gb.rom": ("Cartuccia", "Cartridge"),
    "gb.rom.vuoto": (
        "Nessuna ROM in %(cartella)s. Copiale nella condivisione: sono file "
        ".gb o .gbc, e restano tue \u2014 in questo progetto non ce n'\u00e8 "
        "nessuna e non ce ne saranno mai.",
        "No ROMs in %(cartella)s. Copy them into the share: they are .gb or "
        ".gbc files, and they stay yours \u2014 this project ships none and "
        "never will."),
    "gb.gioca": ("Gioca", "Play"),
    "gb.esci": ("Esci dalla partita", "Leave the game"),
    "gb.video": ("Immagine", "Picture"),
    "gb.video.hint": (
        "Hanno effetto alla partenza del processo: cambiandoli durante una "
        "partita, la partita riparte.",
        "These apply when the process starts: changing them during a session "
        "restarts it."),
    "gb.overscan": ("Overscan (%)", "Overscan (%)"),
    "gb.gamma": ("Gamma", "Gamma"),
    "gb.fps": ("Fotogrammi al secondo", "Frames per second"),
    "gb.spostamento": ("Spostamento verticale (righe)",
                       "Vertical shift (rows)"),
    "gb.spostamento.hint": (
        "L'overscan taglia met\u00e0 sopra e met\u00e0 sotto, ma i giochi non sono "
        "simmetrici: il punteggio sta in alto, la barra della vita in basso. "
        "Con un numero negativo la finestra sale e si vede la parte alta dello "
        "schermo, con uno positivo scende e si vede quella bassa. La finestra "
        "non esce mai dallo schermo del Game Boy: oltre il bordo il valore "
        "smette semplicemente di avere effetto. Senza overscan non c'\u00e8 niente "
        "da spostare.",
        "Overscan cuts half from the top and half from the bottom, but games "
        "are not symmetric: the score sits at the top, the health bar at the "
        "bottom. A negative number moves the window up and shows the upper "
        "part of the screen, a positive one moves it down. The window never "
        "leaves the Game Boy screen: past the edge the value simply stops "
        "having an effect. With no overscan there is nothing to shift."),
    "gb.overscan.hint": (
        "L'overscan toglie righe sopra e sotto allo schermo del Game Boy: si "
        "perde una fascia di cielo e una di terreno, ma a parit\u00e0 di 64 "
        "righe l'immagine sul pannello diventa pi\u00f9 larga \u2014 71 pixel a "
        "zero, 88 al 20%%, 116 al 40%%. Il gamma sotto 1 schiarisce e sopra 1 "
        "scurisce, come in Doom. Trenta fotogrammi al secondo bastano "
        "all'occhio e dimezzano il traffico verso il pannello.",
        "Overscan drops rows from the top and bottom of the Game Boy screen: "
        "you lose a band of sky and a band of ground, but with the same 64 "
        "rows the picture gets wider \u2014 71 pixels at zero, 88 at 20%%, 116 "
        "at 40%%. Gamma below 1 brightens and above 1 darkens, as in Doom. "
        "Thirty frames per second are enough for the eye and halve the "
        "traffic towards the panel."),
    "gb.comandi": ("Comandi", "Controls"),
    "gb.cartella": ("Cartella delle ROM", "ROM folder"),
    "gb.keyboard.starts": (
        "Un tasto della tastiera pu\u00f2 far cominciare una partita",
        "A keyboard key may start a session"),
    "gb.pad.hint": (
        "Sul pad: croce e cerchio sono A e B, la croce direzionale muove. "
        "Start e Select del Game Boy stanno sulle levette premute (L3 e R3), "
        "perch\u00e9 i pulsanti fisici con quel nome sono gi\u00e0 impegnati: Start "
        "e PS scorrono i giochi, Select esce.",
        "On the pad: cross and circle are A and B, the d-pad moves. The Game "
        "Boy's Start and Select are on the pressed sticks (L3 and R3), "
        "because the physical buttons with those names are already taken: "
        "Start and PS cycle the games, Select leaves."),
    "gb.pad.tasti": (
        "Dal pad non si apre mai una partita: un pulsante deve avere un "
        "significato solo. Si comincia da questa pagina, o dalla tastiera se "
        "lo si \u00e8 chiesto qui sopra.",
        "The pad never starts a session: a button must mean one thing only. "
        "You start from this page, or from the keyboard if enabled above."),
    "gb.tasto.su": ("Su", "Up"),
    "gb.tasto.giu": ("Gi\u00f9", "Down"),
    "gb.tasto.sinistra": ("Sinistra", "Left"),
    "gb.tasto.destra": ("Destra", "Right"),
    "gb.tasto.a": ("A", "A"),
    "gb.tasto.b": ("B", "B"),
    "gb.tasto.start": ("Start", "Start"),
    "gb.tasto.select": ("Select", "Select"),
    "status.gb.idle": ("In attesa \u2014 %(count)d cartucce disponibili",
                       "Idle \u2014 %(count)d cartridges available"),
    "status.gb.playing": ("In partita: %(name)s", "Playing: %(name)s"),
    "status.gb.stopped": ("Emulatore fermo", "Emulator stopped"),
    "status.gb.missing": ("PyBoy non installato", "PyBoy not installed"),
    "status.gb.error": ("Errore: %(error)s", "Error: %(error)s"),
    "services.desc.scadenze": (
        "Avviso periodico delle scadenze aperte e semaforo accanto all'orologio.",
        "Periodic notice of open deadlines, plus the traffic light next to the clock."),
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
