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
    # La pulizia delle briciole dei Mac, nella pagina Media.
    "pulizia.title": ("Briciole dei Mac", "Mac leftovers"),
    "pulizia.hint": (
        "Toglie i file che i Mac lasciano sulle condivisioni: «.DS_Store» e i gemelli «._».",
        "Removes the files Macs leave on shares: “.DS_Store” and the “._” twins."),
    "pulizia.enabled": ("Pulisci da solo, ogni tanto",
                        "Clean up by itself, every so often"),
    "pulizia.hours": ("Ogni quante ore", "Every how many hours"),
    "pulizia.where": ("Cartelle pulite:", "Folders cleaned:"),
    "pulizia.never": ("Nessuna pulizia ancora fatta.", "No cleanup done yet."),
    "pulizia.last": ("Ultima pulizia: %(count)d file tolti, %(when)s.",
                     "Last cleanup: %(count)d files removed, %(when)s."),
    "pulizia.look": ("Guarda e basta", "Just look"),
    "pulizia.now": ("Pulisci adesso", "Clean now"),
    "pulizia.found": ("Ci sono %(count)d briciole da togliere. Non ho "
                      "cancellato niente.",
                      "There are %(count)d leftovers to remove. Nothing was "
                      "deleted."),
    "pulizia.done": ("Tolti %(count)d file.", "Removed %(count)d files."),
    "pulizia.clean": ("Nessuna briciola: le condivisioni sono pulite.",
                      "No leftovers: the shares are clean."),
    "nav.banner": ("Banner", "Banner"),
    "nav.nowplaying": ("Musica", "Music"),
    # ------------------------------------------------------------- compleanni
    "nav.birthdays": ("Compleanni", "Birthdays"),
    "birthdays.title": ("Compleanni e anniversari", "Birthdays and anniversaries"),
    "birthdays.intro": (
        "Date e nomi: quando la ricorrenza si avvicina il pannello lo ricorda con un testo.",
        "Dates and names: as the day approaches the panel reminds you with a scrolling text."),
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
        "Due colonne, data e nome. Le righe si aggiungono in coda, non sostituiscono.",
        "Two columns, date and name. Rows are appended, they do not replace."),
    "birthdays.import.button": ("Importa", "Import"),
    "birthdays.file": ("Elenco completo", "Full list"),
    "birthdays.file.hint": (
        "Si modifica anche a mano. Le righe che iniziano con # sono commenti.",
        "It can be edited by hand. Lines starting with # are comments."),
    "birthdays.count": ("%(count)d persone", "%(count)d people"),
    "birthdays.settings": ("Impostazioni", "Settings"),
    "birthdays.lead": ("Anticipo (ore)", "Lead time (hours)"),
    "birthdays.lead.hint": (
        "L'anticipo dice quanto prima comincia il promemoria; l'intervallo ogni quanto torna.",
        "The lead says how early the reminder starts; the interval how often it returns."),
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

    # ------------------------------------------------------------- satelliti
    # La freccia al posto di "FRA". Segnalato dal campo: «quel FRA sta proprio
    # male». Aveva ragione per una ragione che si vede solo sul vetro -- su un
    # pannello a LED le parole corte in stampatello si leggono come sigle, e
    # una sigla accanto a un numero sembra un'unita' di misura. La freccia non
    # si puo' leggere male, ed e' due caratteri piu' corta: spazio guadagnato
    # proprio nella riga che rischiava di affollarsi.
    "satelliti.in": ("\u2192 %(min)d MIN", "\u2192 %(min)d MIN"),
    # Sul pannello, sotto il conto alla rovescia. L'etichetta esiste perche'
    # senza, `21:10` nella posizione dell'orologio veniva letto come "sono le
    # 21:10" invece che "sorge alle 21:10".
    "satelliti.rises": ("SORGE %(time)s", "RISES %(time)s"),
    "satelliti.lasts.min": ("PER %(min)d MIN", "FOR %(min)d MIN"),
    "satelliti.lasts.sec": ("PER %(sec)d S", "FOR %(sec)d S"),
    # --- pagina Satelliti
    "nav.satelliti": ("Satelliti", "Satellites"),
    "satelliti.title": ("Satelliti", "Satellites"),
    "satelliti.intro": (
        "Avvisa dieci minuti prima di un passaggio della Stazione Spaziale, e dice dove guardare.",
        "It warns ten minutes before a Space Station pass, and shows where to look."),
    "satelliti.nocoords": (
        "Mancano le coordinate: le prende da quelle dell'Air Radar.",
        "Coordinates are missing: they come from the Air Radar ones."),
    "satelliti.next": ("Prossimi passaggi", "Upcoming passes"),
    "satelliti.next.hint": (
        "Ci sono anche quelli che non si vedono, con il motivo accanto.",
        "The ones you cannot see are listed too, with the reason next to them."),
    "satelliti.col.sat": ("Satellite", "Satellite"),
    "satelliti.col.rise": ("Sorge", "Rises"),
    "satelliti.col.len": ("Durata", "Length"),
    "satelliti.col.max": ("Max", "Max"),
    "satelliti.col.dir": ("Da / a", "From / to"),
    "satelliti.col.vis": ("Visibile", "Visible"),
    "satelliti.col.group": ("Gruppo", "Group"),
    "satelliti.col.objects": ("Oggetti", "Objects"),
    "satelliti.col.age": ("Aggiornato", "Updated"),
    "satelliti.vis.yes": ("si'", "yes"),
    "satelliti.vis.no": ("no", "no"),
    "satelliti.vanishes": ("sparisce alle %(time)s", "vanishes at %(time)s"),
    "satelliti.why.sun": ("Sole a %(sun)+d\u00b0", "Sun at %(sun)+d\u00b0"),
    "satelliti.why.shadow": ("in ombra", "in shadow"),
    "satelliti.settings": ("Impostazioni", "Settings"),
    "satelliti.elev": ("Elevazione minima", "Minimum elevation"),
    "satelliti.elev.hint": (
        "Quanti gradi sopra l'orizzonte deve arrivare il passaggio. A 30 resta metà degli annunci.",
        "How high above the horizon the pass must reach. At 30 about half the announcements stay."),
    "satelliti.lead": ("Preavviso (min)", "Lead time (min)"),
    "satelliti.lead.hint": (
        "Un passaggio dura fra i due e i sette minuti: annunciarlo mentre succede è tardi.",
        "A pass lasts two to seven minutes: announcing it as it happens is too late."),
    "satelliti.step": ("Promemoria ogni (min)", "Reminder every (min)"),
    "satelliti.step.hint": (
        "Con preavviso 10 e cadenza 5 compaiono due avvisi: a T-10 e a T-5.",
        "With lead 10 and step 5 there are two reminders: at T-10 and T-5."),
    "satelliti.groups": ("Famiglie", "Families"),
    "satelliti.groups.hint": (
        "Le famiglie le pubblica CelesTrak. Più se ne scelgono, più il calcolo è lungo.",
        "The families come from CelesTrak. The more you pick, the longer the computation."),
    "satelliti.showdim": (
        "Mostra anche i passaggi che non si vedono",
        "Show passes that are not visible too"),
    "satelliti.showdim.hint": (
        "Sono quattro al giorno contro uno. Arrivano in grigio-azzurro, senza preavviso.",
        "Four a day against one. They arrive in grey-blue, with no advance warning."),
    "satelliti.allobjects": (
        "Anche gli oggetti di luminosita' sconosciuta",
        "Objects of unknown brightness too"),
    "satelliti.allobjects.hint": (
        "Sconsigliato: il gruppo contiene anche i CubeSat, invisibili a occhio nudo.",
        "Not recommended: the group also holds CubeSats, invisible to the naked eye."),
    "satelliti.sunmax": ("Sole al massimo a (gradi)",
                         "Sun at most at (degrees)"),
    "satelliti.sunmax.hint": (
        "Sopra questa altezza del Sole non si mostrano: a 0 la finestra si apre al tramonto.",
        "Above this sun elevation nothing is shown: at 0 the window opens at sunset."),
    "satelliti.attesa.buio": (
        "in attesa del tramonto (Sole a %(sole)d°, soglia %(soglia)d°)",
        "waiting for sunset (sun at %(sole)d°, threshold %(soglia)d°)"),
    "satelliti.tle": ("Elementi orbitali", "Orbital elements"),
    "satelliti.tle.hint": (
        "Si scaricano da CelesTrak ogni sei ore e invecchiano in giorni, non in minuti.",
        "Downloaded from CelesTrak every six hours, they age in days, not minutes."),
    "satelliti.tle.never": ("mai", "never"),
    "satelliti.log": ("Registro dei passaggi", "Pass log"),
    "satelliti.log.hint": (
        "Un CSV con tutti i passaggi a cose fatte, visibili e non.",
        "A CSV with every pass after the fact, visible or not."),
    "satelliti.log.rows": ("%(rows)d passaggi, %(size)s kB",
                           "%(rows)d passes, %(size)s kB"),
    "satelliti.log.enabled": ("Registra i passaggi", "Log the passes"),
    "satelliti.log.clear": ("Svuota il registro", "Clear the log"),

    "satelliti.manca": (
        "manca la libreria sgp4: "
        "sudo pip3 install sgp4 --break-system-packages",
        "the sgp4 library is missing: "
        "sudo pip3 install sgp4 --break-system-packages"),
    "status.satelliti.next": (
        "prossimo: %(name)s alle %(time)s, fino a %(elev)d gradi",
        "next: %(name)s at %(time)s, up to %(elev)d degrees"),
    "status.satelliti.none": (
        "nessun passaggio visibile in vista",
        "no visible pass coming up"),

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
        "I dati arrivano in piedi e nodi: la conversione riguarda solo il pannello, non il CSV.",
        "Data arrives in feet and knots: the conversion is for the panel only, not the CSV."),
    "radar.unit.ft": ("piedi (ft)", "feet (ft)"),
    "radar.unit.m": ("metri (m)", "metres (m)"),
    "radar.unit.kt": ("nodi (kt)", "knots (kt)"),
    "radar.unit.kmh": ("km/h", "km/h"),
    "radar.unit.mph": ("mph", "mph"),
    "radar.unit.km": ("chilometri (km)", "kilometres (km)"),
    "radar.unit.mi": ("miglia (mi)", "miles (mi)"),
    "radar.unit.nm": ("miglia nautiche (nm)", "nautical miles (nm)"),
    "nav.radar": ("Radar", "Radar"),
    "radar.vicini": ("Passati appena fuori", "Passed just outside"),
    "radar.vicini.hint": (
        "Aerei visti oltre i %(raggio)s km ma poco fuori: non vanno sul pannello né nel registro.",
        "Aircraft seen just beyond %(raggio)s km: they reach neither the panel nor the log."),
    "radar.col.flight": ("Volo", "Flight"),
    "radar.col.dist": ("Distanza", "Distance"),
    "radar.col.when": ("Quando", "When"),
    "nav.services": ("Servizi", "Services"),
    "nav.language": ("Lingua", "Language"),
    "footer.project": ("Progetto su GitHub", "Project on GitHub"),
    "footer.version": ("versione", "version"),
    "common.download": ("Scarica il CSV", "Download the CSV"),
    # Alias storico: i template lo usano, e senza questa riga il pulsante di
    # salvataggio di Now Playing si chiamava "form.save".
    "form.save": ("Salva", "Save"),
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
    # Distinto da quello di Sleep mode, e non per pignoleria: uno spegnimento
    # deciso a mano non si annulla da solo a un orario, e chi trova il pannello
    # nero deve sapere quale delle due cose sta guardando.
    "banner.off": ("Pannello spento a mano: resta così finché non lo riaccendi.",
                   "Panel switched off by hand: it stays off until you turn "
                   "it back on."),

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
    "status.radar.found": ("%(provider)s: %(count)d aerei nel raggio di %(radius).1f km, "
                           "interrogato ogni %(cadence)d s",
                           "%(provider)s: %(count)d aircraft within %(radius).1f km, "
                           "polled every %(cadence)d s"),
    "status.radar.revived": (
        "ciclo riavviato %(count)d volte, l'ultima il %(when)s",
        "loop restarted %(count)d times, last on %(when)s"),
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
        "Valore diurno. La modifica è immediata sul pannello e viene salvata da sola.",
        "Daytime value. The change is immediate on the panel and saved automatically."),

    "settings.brightness.night": (

        "Night mode è attivo: vale la luminosità notturna ({valore}%), che si cambia qui sotto.",

        "Night mode is on: the night brightness ({valore}%) applies, and it is set below."),

    "settings.position": ("Posizione del DMD", "Where the DMD is"),
    "settings.position.hint": (
        "Una posizione sola per radar, satelliti e meteo. A zero restano tutti e tre in silenzio.",
        "One position for radar, satellites and weather. At zero all three stay silent."),
    "radar.coords.moved": (
        "Le coordinate sono passate in Impostazioni, perché le usano anche i "
        "satelliti e il meteo. Adesso sono %(lat)s, %(lon)s.",
        "The coordinates moved to Settings, because the satellites and the "
        "weather use them too. They are now %(lat)s, %(lon)s."),

    "settings.power": ("Pannello", "Panel"),
    "settings.power.on": ("Il pannello è acceso", "The panel is on"),
    "settings.power.off": ("Il pannello è spento", "The panel is off"),
    "settings.power.turn_off": ("Spegni il pannello", "Turn the panel off"),
    "settings.power.turn_on": ("Accendi il pannello", "Turn the panel on"),
    "settings.power.hint": (
        "Spegne solo il vetro: il Raspberry resta acceso e continua a fare tutto.",
        "Turns off the glass only: the Raspberry stays on and keeps doing everything."),

    "settings.modes": ("Night mode e Sleep mode", "Night mode and Sleep mode"),
    "settings.night": ("Night mode — abbassa la luminosità in una fascia oraria",
                       "Night mode — lowers brightness during a time range"),
    "settings.modes.spostati": (
        "Night mode, Sleep mode e le fasce orarie di tutti i servizi stanno "
        "adesso in un posto solo:",
        "Night mode, Sleep mode and every service's time window now live in "
        "one place:"),
    "timing.title": ("Timing", "Timing"),
    "timing.intro": (
        "Quando ogni servizio può prendere il pannello. Il valore predefinito "
        "è «sempre»: finché non accendi una fascia, tutto si comporta come si "
        "è sempre comportato.",
        "When each service may take the panel. The default is “always”: until "
        "you switch a window on, everything behaves as it always has."),
    "timing.avviso": (
        "La colonna a destra dice se il servizio sta lavorando **adesso** e, "
        "se no, chi lo sta fermando. È il motivo per cui questa pagina esiste: "
        "una fascia per servizio moltiplica i modi in cui qualcosa può non "
        "comparire, e senza una risposta scritta si finisce a indovinare.",
        "The right-hand column says whether the service is working **right "
        "now** and, if not, what is stopping it. That is why this page exists: "
        "a window per service multiplies the ways something can fail to show "
        "up, and without a written answer you end up guessing."),
    "timing.sempre": ("Sempre attivo", "Always on"),
    "timing.ora.attivo": ("attivo adesso", "on right now"),
    "timing.salvata": ("Fascia salvata.", "Window saved."),
    "timing.sveglia.nota": (
        "La Sveglia non rispetta né Night mode né Sleep: mentre squilla non "
        "esiste nessuna fascia, luminosità diurna compresa. È l'unico servizio "
        "che esiste per interrompere.",
        "The Alarm obeys neither Night mode nor Sleep: while it rings no "
        "window applies, daytime brightness included. It is the only service "
        "that exists in order to interrupt."),
    "settings.wake.giochi": (
        "Risveglia il display se qualcuno apre una partita durante lo Sleep",
        "Wake the display if someone opens a game during Sleep"),
    "suoni.title": ("Suoni", "Sounds"),
    "suoni.intro": (
        "Il suono che ogni servizio fa quando prende il pannello: una volta, quando compare.",
        "The sound each service makes when it takes the panel: once, as it appears."),
    "suoni.notifica.info": (
        "Notifica · info — MQTT / Home Assistant",
        "Notification · info — MQTT / Home Assistant"),
    "suoni.notifica.avviso": (
        "Notifica · avviso — MQTT / Home Assistant",
        "Notification · warning — MQTT / Home Assistant"),
    "suoni.onair": ("OnAir — alla chiusura della porta",
                    "OnAir — when the door closes"),
    "suoni.notifica.allarme": (
        "Notifica · allarme — MQTT / Home Assistant",
        "Notification · alarm — MQTT / Home Assistant"),
    "suoni.vuoto": (
        "Non c'è nessun file nella libreria media: copiane qualcuno nella "
        "condivisione di rete e ricompariranno qui.",
        "There are no files in the media library: copy some into the network "
        "share and they will show up here."),
    "suoni.sveglia.title": ("E la sveglia?", "What about the alarm?"),
    "suoni.sveglia.hint": (
        "Il suono della sveglia si sceglie per ogni orario, insieme al resto, "
        "nella sua pagina:",
        "The alarm sound is chosen per time, together with everything else, on "
        "its own page:"),
    "nav.sveglia": ("Sveglia", "Alarm"),
    "nav.onair": ("OnAir", "OnAir"),
    "nav.moon": ("Moon", "Moon"),
    "moon.title": ("Moon", "Moon"),
    "moon.intro": ("La Luna e il cielo di stasera: si mostrano di notte, a turno con il meteo.",
                   "Tonight's Moon and sky: shown at night, taking turns with the weather."),
    "moon.errore": ("Calcolo non riuscito", "Calculation failed"),
    "moon.attivo": ("Servizio attivo", "Service enabled"),
    "moon.durata": ("Secondi a schermo", "Seconds on screen"),
    "moon.durata.hint": ("Per ogni schermata, da 4 a 60.", "For each screen, 4 to 60."),
    "moon.salvato": ("Impostazioni di Moon salvate.", "Moon settings saved."),
    "moon.stasera": ("Stasera", "Tonight"),
    "moon.senza_posizione": ("Senza la posizione (Impostazioni) mancano sorgere, tramonto e serata.",
                             "Without a location (Settings) there is no rise, set or evening."),
    "moon.fase": ("Fase", "Phase"),
    "moon.fase.nuova": ("Luna nuova", "New moon"),
    "moon.fase.crescente": ("Falce crescente", "Waxing crescent"),
    "moon.fase.primo_quarto": ("Primo quarto", "First quarter"),
    "moon.fase.gibbosa_crescente": ("Gibbosa crescente", "Waxing gibbous"),
    "moon.fase.piena": ("Luna piena", "Full moon"),
    "moon.fase.gibbosa_calante": ("Gibbosa calante", "Waning gibbous"),
    "moon.fase.ultimo_quarto": ("Ultimo quarto", "Last quarter"),
    "moon.fase.calante": ("Falce calante", "Waning crescent"),
    "moon.crescente": ("crescente", "waxing"),
    "moon.calante": ("calante", "waning"),
    "moon.sorge": ("Sorge", "Rises"),
    "moon.tramonta": ("Tramonta", "Sets"),
    "moon.piena": ("Prossima luna piena", "Next full moon"),
    "moon.serata": ("Serata da guardare", "Evening for stargazing"),
    "moon.serata.buona": ("Sì", "Yes"),
    "moon.nuvole": ("nuvole %(valore)s%%", "clouds %(valore)s%%"),
    "moon.serata.no.luna": ("No: la Luna illumina il cielo", "No: the Moon lights up the sky"),
    "moon.serata.no.nuvole": ("No: troppe nuvole", "No: too many clouds"),
    "moon.serata.no.nuvole_ignote": ("Non si sa: manca la previsione delle nuvole",
                                     "Unknown: no cloud forecast"),
    "moon.serata.no.poco_buio": ("No: meno di un'ora e mezza di buio", "No: less than 90 minutes of dark"),
    "moon.anteprime": ("Le schermate di stasera", "Tonight's screens"),
    "moon.anteprime.hint": ("Le stesse immagini del pannello, nell'ordine in cui girano.",
                            "The same images as the panel, in the order they rotate."),
    "moon.schermata.luna": ("la Luna", "the Moon"),
    "moon.schermata.serata": ("la serata", "the evening"),
    "moon.schermata.stagione": ("la stagione", "the season"),
    "moon.schermata.luna_nome": ("la luna con un nome", "the named moon"),
    "moon.schermata.sciame": ("lo sciame", "the meteor shower"),
    "moon.mostra": ("Mostra sul pannello", "Show on the panel"),
    "moon.prossimi": ("I prossimi appuntamenti", "Coming up"),
    "moon.prossimi.hint": ("Sul pannello compaiono dal terzo giorno prima.",
                           "They appear on the panel from three days before."),
    "moon.nome.raccolto": ("Luna del Raccolto", "Harvest Moon"),
    "moon.nome.superluna": ("Superluna", "Supermoon"),
    "moon.nome.blu": ("Luna blu", "Blue moon"),
    "moon.stagione.equinozio_primavera": ("Equinozio di primavera", "Spring equinox"),
    "moon.stagione.solstizio_estate": ("Solstizio d'estate", "Summer solstice"),
    "moon.stagione.equinozio_autunno": ("Equinozio d'autunno", "Autumn equinox"),
    "moon.stagione.solstizio_inverno": ("Solstizio d'inverno", "Winter solstice"),
    "moon.sciame.sottile": ("la Luna non disturba", "the Moon won't interfere"),
    "moon.sciame.tramonta": ("Luna al %(valore)s%%, giù alle %(ora)s", "Moon at %(valore)s%%, sets at %(ora)s"),
    "moon.sciame.copre": ("Luna al %(valore)s%%: ne copre molte", "Moon at %(valore)s%%: hides many"),
    "world.title": ("World Time", "World Time"),
    "world.intro": (
        "Che ore sono adesso altrove, in una riga sotto l'orologio.",
        "What time it is elsewhere, on a line under the clock."),
    "world.enabled": ("Mostra gli orari del mondo", "Show world times"),
    "world.citta": ("Città", "City"),
    "world.fuso": ("Fuso", "Time zone"),
    "world.etichetta": ("Sul pannello", "On the panel"),
    "world.adesso": ("Adesso", "Now"),
    "world.scegli": ("— scegli —", "— pick one —"),
    "world.fuso.hint": (
        "La tendina riempie la casella e torna indietro. Vale la casella.",
        "The menu fills the field in, then resets. The field is what counts."),
    "world.etichetta.hint": (
        "Etichette corte fanno stare più città insieme: «NY» invece di "
        "«New York».",
        "Short labels fit more cities at once: “NY” instead of “New York”."),
    "world.colore.nome": ("Colore del nome", "Name colour"),
    "world.colore.ora": ("Colore dell'ora", "Time colour"),
    "world.nodb": (
        "Il database dei fusi non c'è su questo sistema: installa «tzdata».",
        "The time-zone database is missing on this system: install “tzdata”."),
    "onair.title": ("OnAir", "OnAir"),
    "onair.intro": (
        "Il pannello dice che si sta registrando: scritta fissa e trattino "
        "rosso sull'orologio.",
        "The panel says a recording is in progress: a fixed sign and a red "
        "tick on the clock."),
    "onair.accendi": ("Vai in onda", "Go on air"),
    "onair.spegni": ("Chiudi la diretta", "End the broadcast"),
    "onair.scritta": ("La scritta", "The sign"),
    "onair.testo": ("Testo", "Text"),
    "onair.testo.hint": (
        "Va a capo da solo e si taglia con i puntini se non ci sta.",
        "It wraps by itself, and is cut with an ellipsis if it does not fit."),
    "onair.sfondo": ("Colore di fondo", "Background colour"),
    "onair.inchiostro": ("Colore del testo", "Text colour"),
    "onair.secondi": ("Secondi a schermo", "Seconds on screen"),
    "onair.secondi.hint": ("0 = quanto una foto del Media Player.",
                           "0 = as long as a Media Player photo."),
    "onair.ogni": ("Ricompare ogni", "Reappears every"),
    "onair.ogni.hint": ("Contenuti del Media Player fra una comparsa e l'altra.",
                        "Media Player items between one appearance and the next."),
    "onair.tetto": ("Al massimo dopo (s)", "At the latest after (s)"),
    "onair.tetto.hint": (
        "Compare comunque, anche se i media non passano. 0 = nessun tetto.",
        "It appears anyway, even if no media plays. 0 = no ceiling."),
    "onair.ha": ("Home Assistant", "Home Assistant"),
    "onair.ha.hint": (
        "Il sensore della porta lo scegli in Home Assistant: il DMD sa solo "
        "se è in onda.",
        "You pick the door sensor in Home Assistant: the DMD only knows "
        "whether it is on air."),
    "onair.ha.servizio": ("Servizio acceso", "Service on"),
    "onair.ha.diretta": ("In onda", "On air"),
    "onair.ha.proposti": (
        "Nomi proposti: HA può assegnarne altri. Il vero si legge in "
        "Entità, cercando «onda».",
        "Suggested names: HA may assign others. Read the real one under "
        "Entities, searching “onda”."),
    "onair.ha.file": (
        "Guida e automazione pronta: docs/onair-automazione.it.md.",
        "Guide and ready-made automation: docs/onair-automazione.it.md."),
    "timer.title": ("Timer", "Timer"),
    "timer.intro": (
        "Un conto alla rovescia per le cose che scadono «fra quanto», non a un'ora.",
        "A countdown for things that are due “in so long”, not at a given time."),
    "timer.nome": ("Per cosa (facoltativo)", "What for (optional)"),
    "timer.nome.esempio": ("Pasta", "Pasta"),
    "timer.minuti": ("%(n)s min", "%(n)s min"),
    "timer.altro": ("Oppure scrivi i minuti", "Or type the minutes"),
    "timer.suono": ("Suono del timer", "Timer sound"),
    "timer.suono.come": ("Lo stesso della prima sveglia attiva",
                         "The same as the first active alarm"),
    "timer.suono.salvato": ("Suono del timer salvato.", "Timer sound saved."),
    "timer.avvia": ("Avvia", "Start"),
    "timer.annulla": ("Annulla il timer", "Cancel the timer"),
    "timer.in.corso": ("Timer in corso: mancano %(resta)s%(nome)s.",
                       "Timer running: %(resta)s left%(nome)s."),
    "timer.avviato": ("Timer avviato: %(minuti)s minuti.",
                      "Timer started: %(minuti)s minutes."),
    "timer.no": ("Timer non avviato: %(error)s", "Timer not started: %(error)s"),
    "timer.annullato": ("Timer annullato.", "Timer cancelled."),
    "timer.nessuno": ("Non c'era nessun timer in corso.",
                      "There was no timer running."),
    "timer.occupato": (
        "Ce n'è già uno in corso: per cambiarlo, annullalo e rifallo.",
        "One is already running: to change it, cancel it and set it again."),
    "status.sveglia.timer": ("timer: mancano %(minuti)s",
                             "timer: %(minuti)s left"),
    "sveglia.title": ("Sveglia", "Alarm clock"),
    "sveglia.intro": (
        "Fino a quattro orari. Quando uno scatta il pannello lampeggia e la scheda audio suona.",
        "Up to four times. When one goes off the panel blinks and the sound card rings."),
    "sveglia.servizio.spento": (
        "Il servizio Sveglia è spento nella pagina Servizi: gli orari qui "
        "sotto restano salvati ma non suonerà niente.",
        "The Alarm service is off in the Services page: the times below are "
        "saved but nothing will ring."),
    "sveglia.numero": ("Sveglia %(n)s", "Alarm %(n)s"),
    "sveglia.attiva": ("Attiva", "On"),
    "sveglia.ora": ("Ora", "Time"),
    "sveglia.giorni": ("Giorni", "Days"),
    "sveglia.durata": ("Suona per (secondi)", "Rings for (seconds)"),
    "sveglia.suono": ("Suono", "Sound"),
    "sveglia.suono.predefinito": ("Suono del programma",
                                  "Built-in sound"),
    "sveglia.etichetta": ("Etichetta (facoltativa)", "Label (optional)"),
    "sveglia.etichetta.esempio": ("Lavoro", "Work"),
    "sveglia.salvata": ("Sveglia %(n)s salvata.", "Alarm %(n)s saved."),
    "sveglia.suona.adesso": ("STA SUONANDO la sveglia delle %(ora)s.",
                             "The %(ora)s alarm IS RINGING."),
    "sveglia.zittisci": ("Ferma la sveglia", "Stop the alarm"),
    "sveglia.zittita": ("Sveglia fermata.", "Alarm stopped."),
    "sveglia.gia.zitta": ("Non stava suonando niente.",
                          "Nothing was ringing."),
    "sveglia.prossima": ("Prossima sveglia: %(ora)s di %(quando)s.",
                         "Next alarm: %(ora)s on %(quando)s."),
    "sveglia.nessuna": ("Nessuna sveglia attiva.", "No alarm is on."),
    "sveglia.prova.title": ("Prova", "Test"),
    "sveglia.prova.hint": (
        "Fa squillare adesso per quindici secondi, con il suono della prima sveglia attiva.",
        "Rings now for fifteen seconds, with the sound of the first active alarm."),
    "sveglia.prova.button": ("Fai squillare adesso", "Ring now"),
    "sveglia.prova.ok": (
        "Sta squillando: premi il pulsante della FunCAM, o aspetta quindici secondi.",
        "Ringing: press the FunCAM button, or wait fifteen seconds."),
    "sveglia.prova.no": ("Non è partita: %(error)s", "It did not start: %(error)s"),
    "sveglia.regole.title": ("Che cosa la ferma e che cosa no",
                             "What stops it and what does not"),
    "sveglia.regole.sleep": (
        "Passa sopra allo Sleep mode e al display spento a mano.",
        "It overrides Sleep mode and a manually switched-off display."),
    "sveglia.regole.volume": (
        "Il volume notturno non la tocca: suona al volume di giorno.",
        "The night volume does not apply: it rings at the daytime volume."),
    "sveglia.regole.audio": (
        "Se l'audio generale è spento non suona, e il pannello lampeggia lo stesso.",
        "If the master sound is off it stays silent, and the panel blinks anyway."),
    "sveglia.regole.pulsante": (
        "La ferma il pulsante fisico: mentre squilla è suo, e non scatta nessuna foto.",
        "The physical button stops it: while ringing it is the alarm's, and takes no photo."),
    "status.sveglia.suona": ("sta suonando (%(ora)s)", "ringing (%(ora)s)"),
    "status.sveglia.prossima": ("prossima: %(ora)s di %(giorno)s",
                                "next: %(ora)s on %(giorno)s"),
    "status.sveglia.nessuna": ("nessuna sveglia attiva", "no alarm set"),
    "settings.night.volume": ("Volume %", "Volume %"),
    "settings.night.volume.hint": (
        "Il volume degli avvisi durante il Night mode. Zero vuol dire muto, ed è il predefinito.",
        "Volume of the DMD's own chimes during Night mode. Zero means muted, and is the default."),
    "settings.sleep": ("Sleep mode — spegne il display in una fascia oraria",
                       "Sleep mode — turns the display off during a time range"),
    "settings.wake": ("Risveglia il display se arrivano frame da Batocera durante lo Sleep",
                      "Wake the display if frames arrive from Batocera during Sleep"),
    "settings.modes.hint": (
        "Sleep ha la precedenza su Night. Le fasce possono attraversare la mezzanotte.",
        "Sleep takes precedence over Night. Bands may cross midnight."),

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
        "Scarica, verifica, salva una copia e sostituisce. Se non riparte, torna indietro da sola.",
        "Downloads, verifies, keeps a copy and replaces. If it fails to restart, it rolls back."),
    "settings.update.log": ("Diario degli aggiornamenti", "Update log"),
    "settings.update.fonte": ("Il controllo guarda", "The check looks at"),
    "settings.update.fonte.release": ("l'ultima release pubblicata",
                                      "the latest published release"),
    "settings.update.fonte.ramo": ("il ramo (l'API delle release non ha risposto)",
                                   "the branch (the releases API did not answer)"),
    "settings.update.note": ("Cosa cambia", "What's new"),
    "settings.update.vedi": ("Apri la release su GitHub", "Open the release on GitHub"),
    "settings.update.segnale": ("Segnala la versione nuova sul pannello",
                                "Show a mark on the panel when a new version is out"),
    "settings.update.segnale.hint": (
        "Un puntino verde nell'angolo in alto a destra dell'orologio. Niente altro.",
        "A green dot in the top right corner of the clock. Nothing else."),
    "settings.update.esito.ok": ("Aggiornamento riuscito: ora è attiva la %(version)s.",
                                 "Update succeeded: version %(version)s is now running."),
    "settings.update.esito.back": (
        "La %(version)s non è ripartita: ripristinata la %(active)s.",
        "Version %(version)s did not start: rolled back to %(active)s."),
    "settings.update.esito.bad": ("Aggiornamento alla %(version)s non riuscito.",
                                  "Update to version %(version)s failed."),
    "settings.update.esito.ok_letto": ("Ho letto", "Got it"),

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
        "Taratura, colori, fasce e servizi in un file solo. Esportalo dopo ogni modifica.",
        "Tuning, colours, time bands and services in one file. Export it after every big change."),
    "settings.config.export": ("Esporta la configurazione", "Export the configuration"),
    "settings.config.position": (
        "Includi le coordinate del radar",
        "Include the radar coordinates"),
    "settings.config.position.hint": (
        "Togli la spunta se il file va condiviso: senza, le coordinate escono a zero.",
        "Untick it if you are sharing the file: otherwise the coordinates are exported as zero."),
    "settings.config.import": ("Importa una configurazione", "Import a configuration"),
    "settings.config.import.button": ("Importa e riavvia", "Import and restart"),
    "settings.config.import.hint": (
        "Il file viene adeguato alla versione in uso. Quella attuale finisce in %(path)s.",
        "The file is adapted to this version. The current configuration is saved to %(path)s."),
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
        "Vale solo per queste pagine. I giorni sul pannello si scelgono nella pagina Orologio.",
        "For these pages only. The day names on the panel are chosen on the Clock page."),

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
    "clock.casuale": ("Colore casuale, diverso a ogni ora", "Random colour, a new one every hour"),
    "clock.casuale.adesso": ("Il colore di quest'ora:", "This hour's colour:"),
    "clock.offset": ("Posizione verticale dell'ora", "Vertical position of the time"),
    "clock.offset.su": ("più in alto", "higher"),
    "clock.offset.giu": ("più in basso", "lower"),
    "clock.offset.hint": (
        "Scostamento dalla posizione normale. Oltre il bordo non va.",
        "Offset from the normal position. It will not go past the edge."),
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
        "L'elenco dei file resta in memoria qualche minuto: dopo aver copiato file, premi qui.",
        "The file list is cached for a few minutes: after copying files, press this."),
    "media.rescan.button": ("Rileggi la libreria", "Re-read the library"),
    "media.timer": ("Fascia oraria", "Time window"),
    "media.timer.hint": (
        "Le ore in cui il Media Player lavora. Fuori dalla fascia si ferma davvero.",
        "The hours when the Media Player works. Outside the band it really stops."),
    "media.timer.enabled": (
        "Rispetta la fascia oraria (spento: il Media Player lavora sempre)",
        "Respect the time window (off: the Media Player always works)"),
    "media.timer.sleep": (
        "Lo Sleep mode ha comunque la precedenza. La fascia può scavalcare la mezzanotte.",
        "Sleep mode still takes precedence. The band may cross midnight."),
    "media.preview": ("Anteprima", "Preview"),
    "media.preview.hint": (
        "Manda subito sul pannello un contenuto scelto a caso dalla libreria.",
        "Sends a random item from the library to the panel right away."),
    "media.preview.button": ("Mostra subito un contenuto", "Show something now"),
    "media.playback": ("Riproduzione", "Playback"),
    "media.minint": ("Intervallo minimo (s)", "Minimum interval (s)"),
    "media.maxint": ("Intervallo massimo (s)", "Maximum interval (s)"),
    "media.interval.hint": (
        "Fra un contenuto e il successivo si attende un tempo casuale in questo intervallo.",
        "Between one item and the next a random time in this range is waited."),
    "media.imgdur": ("Durata delle foto (s)", "Photo duration (s)"),
    "media.viddur": ("Durata dei video (s)", "Video duration (s)"),
    "media.duration.hint": (
        "Le animazioni brevi vengono ripetute fino a coprire la durata indicata.",
        "Short animations are repeated until they cover the chosen duration."),
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
        "Fino a dieci testi scorrevoli, a intervalli casuali come i contenuti del Media Player.",
        "Up to ten scrolling texts, at random intervals like the Media Player's content."),
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
        "Fra un banner e il successivo si attende un tempo casuale in questo intervallo.",
        "Between one banner and the next a random time in this range is waited."),
    "banner.fps": ("Fotogrammi al secondo", "Frames per second"),
    "banner.shuffle": ("Ordine casuale invece che in sequenza",
                       "Random order instead of sequential"),
    "banner.speed.hint": (
        "A 60 px/s un testo attraversa il pannello in poco più di quattro secondi.",
        "At 60 px/s a text crosses the panel in a little over four seconds."),
    "banner.preview": ("Anteprima", "Preview"),
    "banner.preview.hint": (
        "Interrompe l'attesa e manda subito in scorrimento il testo successivo.",
        "Skips the wait and immediately scrolls the next text."),
    "banner.preview.button": ("Mostra subito un banner", "Show a banner now"),
    "banner.priority.hint": (
        "Sta sopra al Media Player ma sotto ad Air Radar e a ZeDMD.",
        "It sits above the Media Player but below Air Radar and ZeDMD."),

    # --------------------------------------------------------------- now playing
    "nowplaying.title": ("Now Playing", "Now Playing"),
    "nowplaying.coverage.title": ("Che cosa viene rilevato", "What gets picked up"),
    "nowplaying.coverage.airplay": (
        "Tutto ciò che parte da iPhone, iPad o Mac via AirPlay, con il DMD scelto fra le casse.",
        "Anything sent from an iPhone, iPad or Mac over AirPlay, with the DMD chosen as speaker."),
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
        "Musica proveniente da HomePod non intercettabile",
        "Music coming from a HomePod cannot be picked up"),
    "nowplaying.current": ("In riproduzione adesso", "Playing now"),
    "nowplaying.nothing": ("Niente in riproduzione.", "Nothing playing."),
    "nowplaying.source": ("Sorgente", "Source"),
    "nowplaying.device": ("Dispositivo", "Device"),
    "nowplaying.test": ("Prova senza musica", "Try it without music"),
    "nowplaying.test.hint": (
        "Mette un brano finto nel player per vedere come viene sul pannello. Sparisce da solo.",
        "Puts a fake track in the player to see how it looks. It clears itself."),
    "nowplaying.test.button": ("Mostra un brano di prova", "Show a test track"),

    # Le chiavi qui sotto tengono il prefisso `nowplaying.` per ragioni di
    # anzianita': il modulo e' nato nella pagina Musica, dove il broker
    # serviva solo ad AirPlay. Dalla 6.2 sta nella pagina Rete, ma
    # rinominare venticinque chiavi per una questione di etichetta avrebbe
    # prodotto un cambiamento grande e rischioso in cambio di niente: le
    # chiavi sono identificatori, e questo commento e' piu' economico.
    "nowplaying.broker": ("Broker MQTT", "MQTT broker"),
    "nowplaying.broker.hint": (
        "Il broker MQTT da cui passano brano, interruttori, scadenze e notifiche.",
        "The MQTT broker carrying the track, switches, deadlines and notifications."),
    # I due rimandi fra la pagina Rete e la pagina Musica. Finiscono davanti a
    # un collegamento, quindi la frase si chiude con il nome della pagina.
    "rete.mqtt.elsewhere": (
        "I due topic da cui arriva il brano in ascolto si impostano in",
        "The two topics the playing track comes from are set in"),
    "nowplaying.broker.moved": (
        "Broker, credenziali e Home Assistant si impostano in",
        "Broker, credentials and Home Assistant are set in"),
    "nowplaying.topics": ("Topic della musica", "Music topics"),
    "nowplaying.mqtt.enabled": ("Collega il DMD al broker",
                                "Connect the DMD to the broker"),
    "nowplaying.mqtt.host": ("Indirizzo", "Address"),
    "nowplaying.mqtt.username": ("Utente", "Username"),
    "nowplaying.mqtt.password": ("Password", "Password"),
    "nowplaying.mqtt.password.hint": (
        "La password non finisce nella configurazione esportata: va riscritta dopo l'importazione.",
        "The password never leaves in an exported configuration: type it again after an import."),
    "nowplaying.mqtt.client_id": ("Nome del client", "Client name"),
    "nowplaying.mqtt.base_topic": ("Topic di base del DMD", "DMD base topic"),
    "nowplaying.mqtt.shairport": ("Topic di shairport-sync", "shairport-sync topic"),
    "nowplaying.mqtt.shairport.hint": (
        "Lo stesso valore di `mqtt.topic` in /etc/shairport-sync.conf.",
        "The same value as `mqtt.topic` in /etc/shairport-sync.conf."),
    "nowplaying.mqtt.external": ("Topic esterno", "External topic"),
    "nowplaying.mqtt.external.hint": (
        "Topic facoltativo dove pubblicare un JSON con il brano. Vuoto: non si ascolta nulla.",
        "Optional topic where a JSON with the track can be published. Empty: nothing is heard."),
    "nowplaying.mqtt.missing": (
        "La libreria MQTT non è installata. Sul Raspberry: "
        "sudo apt install %(package)s",
        "The MQTT library is not installed. On the Raspberry Pi: "
        "sudo apt install %(package)s"),
    "nowplaying.setup.hint": (
        "Non compilare a mano: c'è uno script che configura tutto. Da SSH: %(command)s",
        "Do not fill these in by hand: a script sets it all up. Over SSH: %(command)s"),
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
        "Il DMD si presenta a Home Assistant via MQTT: brano, interruttori e luminosità.",
        "The DMD announces itself to Home Assistant: track, switches and brightness."),
    "nowplaying.hass.birth": (
        "Se Home Assistant riparte il DMD si ridichiara da solo: i pulsanti sono una scorciatoia.",
        "If Home Assistant restarts the DMD re-declares itself: these buttons are a shortcut."),
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
        "Cancella il dispositivo da Home Assistant, così non restano entità fantasma.",
        "Removes the device from Home Assistant, so no ghost entities are left behind."),
    "nowplaying.hass.prefix": ("Prefisso discovery", "Discovery prefix"),
    "nowplaying.hass.node": ("Identificativo del dispositivo", "Device id"),
    "nowplaying.hass.device": ("Nome mostrato", "Displayed name"),

    "nowplaying.spotify": ("Spotify", "Spotify"),
    "nowplaying.spotify.hint": (
        "Serve solo per la musica che non passa da AirPlay. Altrimenti lascia spento.",
        "Only for music that does not go through AirPlay. Otherwise leave it off."),
    "nowplaying.spotify.enabled": ("Interroga Spotify", "Poll Spotify"),
    "nowplaying.spotify.client_id": ("Client ID", "Client ID"),
    "nowplaying.spotify.redirect": ("Indirizzo di ritorno", "Redirect URI"),
    "nowplaying.spotify.redirect.hint": (
        "Va registrato identico nell'app Spotify, e deve restare un indirizzo di loopback.",
        "Register it identically in your Spotify app, and keep it a loopback address."),
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
        "La pagina non si aprirà: è previsto. Copia l'indirizzo dalla barra e incollalo qui.",
        "The page will not load: that is expected. Copy the address and paste it here."),
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
        "I token restano in /var/lib/dmd/spotify.json, leggibile solo da root.",
        "The tokens live in /var/lib/dmd/spotify.json, readable only by root."),
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
        "Porta ogni componente a 0 o 255: otto colori, gli unici che non tremolano.",
        "Rounds every channel to 0 or 255: eight colours, the only ones that never flicker."),
    "nowplaying.hold": ("Permanenza in pausa (s)", "Hold when paused (s)"),
    "nowplaying.hold.hint": (
        "Quanto resta a schermo un brano in pausa. Un brano che suona non scade mai.",
        "How long a paused track stays on screen. A playing track never expires."),
    "nowplaying.nocover": (
        "Le copertine sono fatte di mezzi toni: se vedi righe o sfarfallio, abbassa i livelli.",
        "Artwork is made of mid-tones: if you see rows or flicker, lower the levels."),
    "nowplaying.artwork": ("Mostra la copertina", "Show the artwork"),
    "nowplaying.artwork.base": ("Indirizzo di Home Assistant",
                                "Home Assistant address"),
    "nowplaying.artwork.base.hint": (
        "Serve solo se la sorgente manda indirizzi relativi. Vuoto: niente copertine.",
        "Only needed if the source sends relative addresses. Empty: no artwork."),
    "nowplaying.artwork.levels": ("Livelli di colore", "Colour levels"),
    "nowplaying.artwork.levels.hint": (
        "Da 2 a 6 livelli per canale, 0 per non toccare l'immagine. Meno livelli, meno sfarfallio.",
        "2 to 6 levels per channel, 0 to leave the image alone. Fewer levels, less flicker."),
    "nowplaying.mode": ("Quando si vede", "When it shows"),
    "nowplaying.mode.always": ("Sempre, finché suona",
                               "Always, while something plays"),
    "nowplaying.mode.rotation": ("A rotazione con le foto",
                                 "In rotation with the photos"),
    "nowplaying.mode.every": ("Una volta ogni (media)", "Once every (media)"),
    "nowplaying.mode.duration": ("Per (secondi)", "For (seconds)"),
    "nowplaying.mode.hint": (
        "In rotazione il brano prende il pannello una volta ogni tot foto, invece di tenerlo.",
        "In rotation the track takes the panel once every so many photos, instead of holding it."),
    "nowplaying.panel.playing": ("in riproduzione", "playing"),
    "nowplaying.panel.paused": ("in pausa", "paused"),

    "radar.route_color": ("Colore della rotta", "Route colour"),
    "radar.route_color.hint": (
        "La rotta ha una riga sua, al centro. Vuoto: lo stesso colore dei dettagli.",
        "The route gets a line of its own, in the middle. Empty: the same colour as details."),

    # ------------------------------------------------------ conversioni codici
    "lookup.title": ("Conversioni dei codici", "Code translations"),
    "lookup.intro": (
        "Il radar riceve sigle: queste due tabelle le trasformano in nomi leggibili.",
        "The radar receives codes: these two tables turn them into readable names."),
    "lookup.iata.warning": (
        "Gli aeroporti si scrivono con entrambi i codici sulla stessa riga: MXP/LIMC.",
        "Airports can carry both codes on one row, separated by a slash: MXP/LIMC."),
    "lookup.format": (
        "Una riga per voce: codice, forma breve, nome completo. Con # sono commenti.",
        "One row per entry: code, short form, full name. Lines with # are comments."),
    "lookup.persist": (
        "I file vivono in %(dir)s e non vengono mai sovrascritti dagli "
        "aggiornamenti: le tue aggiunte restano.",
        "The files live in %(dir)s and are never overwritten by updates: your "
        "additions stay."),
    "lookup.aircraft": ("Modelli di aeromobile", "Aircraft models"),
    "lookup.airport": ("Aeroporti", "Airports"),
    "lookup.airline": ("Compagnie aeree", "Airlines"),
    "lookup.airline.hint": (
        "Il prefisso di tre lettere del nominativo: in AFR1732 è AFR, cioè il codice ICAO.",
        "The three-letter callsign prefix: in AFR1732 it is AFR, the ICAO designator."),
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
        "Serve solo se hai modificato i file da fuori: di solito se ne accorge da sé.",
        "Only needed if you edited the files elsewhere: normally it notices by itself."),
    "lookup.reloaded": ("File riletti.", "Files re-read."),
    "lookup.unknown": ("Codici incontrati e non tradotti",
                       "Codes seen and not translated"),
    "lookup.unknown.hint": (
        "Ordinati per quante volte sono passati: è la lista di cosa aggiungere per primo.",
        "Sorted by how often they really passed: the list of what to add first."),
    "lookup.unknown.none": ("Nessuno: tutto quello che è passato era in tabella.",
                            "None: everything seen so far was in the table."),
    "lookup.unknown.times": ("%(count)d volte", "%(count)d times"),
    "lookup.unknown.tagliati": (
        "Le prime 40 di %(totale)d: il pulsante qui sotto le aggiunge tutte.",
        "The first 40 of %(totale)d: the button below adds them all."),
    "lookup.add": ("Aggiungi in coda al file", "Append them to the file"),
    "lookup.add.hint": (
        "Aggiunge i codici come righe da completare, con le colonne del nome vuote.",
        "Adds the codes as rows to fill in, with the name columns left empty."),
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
        "Ha priorità sul Media Player e sull'orologio, ma resta sempre sotto ZeDMD.",
        "It outranks the Media Player and the clock, but always stays under ZeDMD."),
    "radar.position": ("Posizione e raggio", "Position and radius"),
    "radar.lat": ("Latitudine", "Latitude"),
    "radar.lon": ("Longitudine", "Longitude"),
    "radar.coords.hint": (
        "Coordinate decimali col punto. Restano solo in %(path)s: non finiscono in nessun pacchetto.",
        "Decimal coordinates with a dot. They stay only in %(path)s: never in any package."),
    "radar.radius": ("Raggio (km)", "Radius (km)"),
    "radar.maxalt": ("Quota massima (ft)", "Maximum altitude (ft)"),
    "radar.provider": ("Servizio dati", "Data service"),
    "radar.filter.hint": (
        "Quota massima 0 = nessun filtro. Se il servizio scelto non risponde, si usano gli altri.",
        "Maximum altitude 0 = no filter. If the chosen service fails, the others are used."),
    "radar.interval": ("Intervallo interrogazioni (s)", "Query interval (s)"),
    "radar.duration": ("Durata a schermo (s)", "Time on screen (s)"),
    "radar.cooldown": ("Riposo per aereo (s)", "Per-aircraft cooldown (s)"),
    "radar.cooldown.hint": (
        "Evita che lo stesso volo venga riproposto di continuo mentre resta nel raggio.",
        "Stops the same flight being shown over and over while it stays in range."),
    "radar.fields": ("Parametri di volo da mostrare", "Flight details to show"),
    # Corta di proposito: e' la prima di tre caselle affiancate, e
    # un'etichetta che va a capo sfalsa la riga.
    "radar.overflow": ("Disposizione informazioni", "Details layout"),
    "radar.overflow.crop": ("Accorcia la riga (comportamento storico)",
                            "Shorten the line (historical behaviour)"),
    "radar.overflow.pages": ("A pagine, a turno", "Pages, in turn"),
    "radar.overflow.scroll": ("Scorrevole", "Scrolling"),
    "radar.page_seconds": ("Secondi per pagina", "Seconds per page"),
    "radar.scroll_speed": ("Velocità (px/s)", "Speed (px/s)"),
    "radar.scroll_fps": ("Fotogrammi al secondo", "Frames per second"),
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
        "Una riga per ogni volo a ogni passaggio, senza riscrivere chi è ancora nel raggio.",
        "One row per flight per pass, without repeating an aircraft still in range."),
    "radar.log.download": ("Scarica il CSV", "Download the CSV"),
    "radar.log.clear": ("Svuota il registro", "Clear the log"),
    "radar.notes": ("Note sui dati", "About the data"),
    "radar.notes.coverage": (
        "I dati vengono dalle reti ADS-B comunitarie: la copertura dipende dai riceventi in zona.",
        "Data comes from community ADS-B networks: coverage depends on nearby receivers."),

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
        "In automatico ZeDMD ha la precedenza e la tiene per %(grace)d secondi dopo l'ultimo frame.",
        "In auto, ZeDMD takes precedence and holds it %(grace)d seconds after the last frame."),
    "services.on": ("Attivo", "On"),
    "services.off": ("Spento", "Off"),
    "services.soon": ("In arrivo", "Coming soon"),
    "services.mqtt": ("MQTT e Home Assistant", "MQTT and Home Assistant"),
    "services.mqtt.desc": (
        "Il collegamento al broker: interruttori in Home Assistant e brano da AirPlay.",
        "The broker connection: switches in Home Assistant and the AirPlay track."),
    "services.mqtt.hint": (
        "Spegnendolo, in Home Assistant il dispositivo passa a «non disponibile».",
        "Turn it off and the device in Home Assistant goes “unavailable”."),
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
    "audio.title": ("Audio", "Audio"),
    "audio.nocard": (
        "Nessuna scheda audio collegata. Infilane una USB: compare qui senza "
        "bisogno di riavviare.",
        "No sound card connected. Plug in a USB one: it appears here without "
        "a restart."),
    "audio.error": ("Ultimo errore: %(error)s", "Last error: %(error)s"),
    "audio.enabled": (
        "Altoparlante attivo",
        "Speaker on"),
    "audio.off": (
        "Il suono è spento: avvisi ed effetti non suonano. Il pulsante di prova funziona lo stesso.",
        "Sound is off: chimes and game effects stay silent. The test button still works."),
    "audio.device": ("Uscita audio", "Audio output"),
    "audio.device.auto": ("L'ultima collegata", "The last one connected"),
    "audio.volume": (
        "Volume effetti sonori servizi",
        "Service sound effects volume"),
    "audio.volume.giochi": ("Volume dei giochi (0-100)",
                            "Games volume (0-100)"),
    "audio.volume.giochi.hint": (
        "Vale per tutti: giochi integrati, Doom e Game Boy. Cambia anche a partita aperta.",
        "Applies to all: built-in games, Doom and Game Boy. Also changes mid-game."),
    "audio.livello": (
        "Livello hardware della scheda: %(valore)s%%.",
        "Card hardware level: %(valore)s%%."),
    "audio.livello.basso": (
        "È basso e penalizza tutto. Si alza con «amixer -c N set PCM 100%» e «alsactl store».",
        "Low, and it penalises everything. Raise it with “amixer -c N set PCM 100%”."),
    "audio.notte": (
        "Night mode attivo: gli avvisi escono al %(valore)s%% del volume. Le partite non cambiano.",
        "Night mode is on: chimes play at %(valore)s%% of the volume. Games are not affected."),
    "audio.giochi": ("Effetti dei giochi (Breakout, Invaders)",
                     "Game effects (Breakout, Invaders)"),
    "audio.doom": ("Audio di Doom", "Doom audio"),
    "audio.test": ("Prova il suono", "Test the sound"),
    "audio.tested": ("Suono inviato alla scheda.", "Sound sent to the card."),
    "audio.tested.off": (
        "Il tono si è sentito, ma «Suono acceso» è spento. Spuntalo e premi Applica.",
        "The tone played, but “Sound on” is off. Tick it and press Apply."),
    "audio.failed": ("Non ha suonato: %(error)s", "It did not play: %(error)s"),
    "audio.services.hint": (
        "Il file di avviso di ogni servizio si sceglie nella pagina Servizi.",
        "Each service's chime file is chosen on the Services page."),
    "audio.none": ("Nessun suono", "No sound"),
    "audio.play": ("Ascolta", "Play"),
    "audio.device.finta": ("scheda fittizia, non suona",
                           "dummy card, makes no sound"),

    "cassa.title": (

        "Uscita musicale (solo AirPlay)",

        "Music output (AirPlay only)"),
    "cassa.intro": (
        "Con questo acceso la musica AirPlay esce dalla scheda audio del DMD.",
        "With this on, AirPlay music comes out of the DMD's sound card."),
    "cassa.enabled": (
        "Usa cassa integrata",
        "Use the built-in speaker"),
    # Non è una scelta da fare qui: la scheda si sceglie in Impostazioni, e
    # questa riga dice soltanto dove sta andando la musica adesso. Scritta
    # com'era — solo `hw:3,0` — sembrava un campo da compilare.
    "cassa.nessuna.uscita": (
        "Ora la musica non si sente. Accendendo l'interruttore uscirà da «%(scheda)s».",
        "The music is not audible. Turn the switch on to play it through “%(scheda)s”."),
    "cassa.senza.scheda": (
        "Non c'è nessuna scheda audio utilizzabile: scegline una in "
        "Impostazioni, oppure collegane una.",
        "There is no usable sound card: choose one in Settings, or plug one "
        "in."),
    "cassa.divergenza": (
        "Attenzione: shairport-sync usa %(adesso)s, qui è scelta %(voluta)s. Salva di nuovo.",
        "Warning: shairport-sync uses %(adesso)s, Settings selects %(voluta)s. Save again."),

    "metadati.title": ("Metadati del brano", "Track metadata"),
    "metadati.intro": (
        "Da dove il pannello sa che cosa stai ascoltando: una pipe locale di shairport-sync.",
        "How the panel knows what you are listening to: a local shairport-sync pipe."),
    "metadati.pipe": ("Pipe", "Pipe"),
    "metadati.scrive": ("shairport-sync ci scrive", "shairport-sync writes to it"),
    "metadati.legge": ("il DMD la sta leggendo", "the DMD is reading it"),
    "metadati.ok": ("Funziona: %(quanti)s elementi ricevuti da quando il "
                    "servizio è partito.",
                    "Working: %(quanti)s items received since the service "
                    "started."),
    "metadati.attesa": (
        "In ascolto. Finché non metti musica non arriva niente, ed è normale.",
        "Listening. Nothing arrives until you play something, which is "
        "normal."),
    "metadati.rotta": ("La pipe non si riesce a leggere: %(error)s",
                       "The pipe cannot be read: %(error)s"),
    "metadati.spenta": (
        "Lettura della pipe disattivata: i metadati arrivano solo dal broker.",
        "Pipe reading is off: metadata arrives only through the broker."),
    "metadati.button": ("Riattiva la pipe", "Re-enable the pipe"),
    "metadati.on": ("Pipe attivata su %(percorso)s e shairport-sync riavviato.",
                    "Pipe enabled on %(percorso)s and shairport-sync "
                    "restarted."),
    "metadati.failed": ("Non è stato cambiato niente: %(error)s",
                        "Nothing was changed: %(error)s"),
    "cassa.missing": (
        "shairport-sync non risulta installato: questo interruttore serve "
        "dopo aver lanciato setup_nowplaying.sh.",
        "shairport-sync does not appear to be installed: this switch is for "
        "after running setup_nowplaying.sh."),
    "cassa.on": (
        "Uscita musicale accesa. Il tono che hai sentito è la prova che la "
        "scheda regge il formato di AirPlay.",
        "Music output on. The tone you heard proves the card handles the "
        "AirPlay format."),
    "cassa.on.convertitore": (
        "Uscita accesa, con il convertitore ALSA davanti alla scheda. Il tono conferma.",
        "Output on, with the ALSA converter in front of the card. The tone confirms it."),
    "cassa.convertitore": (
        "La frequenza passa dal convertitore di ALSA: questa scheda non fa i "
        "44100 Hz di AirPlay.",
        "The rate goes through the ALSA converter: this card cannot do "
        "AirPlay's 44100 Hz."),
    "cassa.off": ("Uscita musicale spenta: la musica torna alla scheda "
                  "fittizia e restano i soli metadati.",
                  "Music output off: audio goes back to the dummy card and "
                  "only the metadata remains."),
    "cassa.failed": ("Non è stato cambiato niente: %(error)s",
                     "Nothing was changed: %(error)s"),
    "nav.telecamera": (
        "FunCAM",
        "FunCAM"),
    "webcam.title": (
        "FunCAM",
        "FunCAM"),
    "webcam.nocam": (
        "Nessuna telecamera collegata. Attaccane una alla porta USB: compare "
        "qui senza bisogno di riavviare.",
        "No camera connected. Plug one into the USB port: it shows up here "
        "without a restart."),
    "webcam.state.off": (
        "Servizio spento: la telecamera non si può accendere, né dalla "
        "pagina né dal pulsante. Si abilita dalla pagina Servizi.",
        "Service off: the camera cannot be turned on, neither from the page "
        "nor from the button. Enable it from the Services page."),
    "webcam.status.live": ("in ripresa da %(device)s", "live from %(device)s"),
    "webcam.status.paused": (
        "in pausa: il pannello è di qualcun altro, e una telecamera che "
        "nessuno guarda è solo traffico sul bus",
        "paused: the panel belongs to someone else, and a camera nobody "
        "watches is just traffic on the bus"),
    "webcam.status.recording": ("sto registrando…", "recording…"),
    "webcam.status.error": ("non funziona: %(error)s", "not working: %(error)s"),
    "webcam.status.retry": (
        "non funziona: %(error)s — riprovo fra %(seconds)d secondi",
        "not working: %(error)s — retrying in %(seconds)d seconds"),
    "webcam.shoot": ("Scatta", "Capture"),
    "webcam.shoot.photo": ("Foto", "Photo"),
    "webcam.shoot.gif": ("GIF di %(seconds)s secondi", "%(seconds)s second GIF"),
    "webcam.shot": ("Salvata %(name)s.", "Saved %(name)s."),
    "webcam.recording": ("Registro per %(seconds)s secondi…",
                         "Recording for %(seconds)s seconds…"),
    "webcam.failed": ("Non è stato possibile: %(error)s",
                      "It did not work: %(error)s"),
    "webcam.settings": ("Impostazioni", "Settings"),
    "webcam.device": ("Telecamera", "Camera"),
    "webcam.device.auto": ("La prima collegata", "The first one connected"),
    "webcam.style": ("Aspetto", "Look"),
    "webcam.style.colori": ("Colori, con dithering", "Colours, dithered"),
    "webcam.style.gameboy": ("Verde Game Boy", "Game Boy green"),
    "webcam.style.grigi": ("Grigi, poche sfumature", "Greys, few shades"),
    "webcam.depth": ("Livelli per canale", "Levels per channel"),
    "webcam.depth.hint": (
        "Adesso %(colori)d colori: i livelli valgono per ogni canale, quindi 2 danno 8 e 4 danno 64.",
        "Now %(colori)d colours: levels apply per channel, so 2 give 8 and 4 give 64."),
    "webcam.levels": ("Sfumature (verde e grigi)", "Shades (green and greys)"),
    "webcam.fps": ("Fotogrammi al secondo", "Frames per second"),
    "webcam.width": ("Larghezza di cattura", "Capture width"),
    "webcam.height": ("Altezza di cattura", "Capture height"),
    "webcam.button": ("Pulsante fisico", "Hardware button"),
    "webcam.button.enable": ("Accendilo", "Turn it on"),
    "webcam.button.enable.label": (
        "Usa il pulsante fisico (il servizio arma, non accende)",
        "Use the hardware button (the service arms, it does not turn on)"),
    "webcam.button.gpio": ("Piedino del pulsante", "Button GPIO"),
    "webcam.button.suggested": ("consigliato", "recommended"),
    "webcam.button.wiring.hint": (
        "Il pulsante va fra GPIO %(gpio)s e massa, senza resistenze.",
        "The button goes between GPIO %(gpio)s and ground, with no resistors."),
    "webcam.button.click": ("Un clic, telecamera spenta",
                            "One click, camera off"),
    "webcam.button.click.what": ("si accende", "it turns on"),
    "webcam.button.click2": ("Un clic, telecamera accesa",
                             "One click, camera on"),
    "webcam.button.click2.what": (
        "scatta una foto dopo tre secondi, con il conto alla rovescia sul "
        "pannello",
        "takes a photo after three seconds, counting down on the panel"),
    "webcam.button.hold": ("Tenuto premuto tre secondi",
                           "Held for three seconds"),
    "webcam.button.hold.what": (
        "si spegne, mentre tieni ancora il dito sopra",
        "it turns off, while your finger is still down"),
    "webcam.button.now": ("Adesso", "Right now"),
    "webcam.button.on": ("Accendi la telecamera", "Turn the camera on"),
    "webcam.button.off": ("Spegni la telecamera", "Turn the camera off"),
    "webcam.gpiozero": ("Libreria del pulsante", "Button library"),
    "webcam.gpiozero.ok": ("%(package)s è installata.",
                           "%(package)s is installed."),
    "webcam.gpiozero.install": ("Installa %(package)s", "Install %(package)s"),
    "webcam.gpiozero.started": (
        "Installazione avviata. Ci vuole un minuto: la pagina si aggiorna da "
        "sola.",
        "Installation started. It takes a minute: the page refreshes by "
        "itself."),
    "webcam.gpiozero.running": ("Installazione in corso…",
                                "Installation in progress…"),
    "webcam.button.rearm": ("Apri il pulsante", "Open the button"),
    "webcam.button.ready": ("Pulsante aperto.", "Button open."),
    "webcam.button.nolib": (
        "Manca gpiozero: il pulsante non si può leggere. «sudo apt install python3-gpiozero».",
        "gpiozero is missing: the button cannot be read. “sudo apt install python3-gpiozero”."),
    "webcam.status.armed": (
        "spenta, in attesa del pulsante su GPIO %(gpio)s",
        "off, waiting for the button on GPIO %(gpio)s"),
    "webcam.status.armed.page": (
        "spenta: si accende dalla pagina FunCAM",
        "off: turn it on from the FunCAM page"),
    "webcam.status.countdown": ("scatto fra %(seconds)d…",
                                "shooting in %(seconds)d…"),
    "webcam.status.button.error": ("pulsante non disponibile: %(error)s",
                                   "button not available: %(error)s"),
    "webcam.gifsec": ("Durata della GIF (secondi)", "GIF length (seconds)"),
    "webcam.mirror": ("Come allo specchio", "Mirrored"),
    "webcam.autocontrast": ("Allarga il contrasto da solo",
                            "Stretch the contrast automatically"),
    "webcam.gallery": ("Ultimi scatti", "Latest captures"),
    "webcam.privacy": ("Dove finiscono le immagini", "Where the images go"),
    "services.desc.webcam": (
        "La webcam sul pannello, dal vivo e con pochi colori.",
        "The webcam on the panel, live and in few colours."),
    "services.desc.sveglia": (
        "Quattro orari con i loro giorni, più il timer. Suona anche con lo "
        "Sleep acceso.",
        "Four times with their days, plus the timer. It rings even with "
        "Sleep on."),
    "services.desc.onair": (
        "La porta si chiude e il pannello lo dice a chi entra, con un "
        "trattino rosso sull'orologio.",
        "The door closes and the panel tells whoever walks in, with a red "
        "tick on the clock."),
    "services.desc.moon": (
        "Di sera, a turno con il meteo: la Luna, le lune con un nome, "
        "stagioni, sciami e le serate buone.",
        "In the evening, taking turns with the weather: the Moon, named "
        "moons, seasons, showers and good nights."),
    "services.desc.notifiche": (
        "I messaggi che Home Assistant manda al pannello: la porta che si "
        "apre, l'allarme inserito, la lavatrice finita.",
        "Messages Home Assistant sends to the panel: the door opening, the "
        "alarm armed, the washing machine done."),
    # Il pulsante di prova nella pagina Servizi. Le due risposte sono
    # diverse apposta: dicono **quale meta' della catena** ha funzionato, che
    # e' l'unica cosa che si voglia sapere premendo un pulsante di prova.
    "notifiche.prova": ("Manda una prova", "Send a test"),
    "notifiche.prova.placeholder": ("Testo della notifica",
                                    "Notification text"),
    "notifiche.prova.testo": ("Prova dal pannello", "Test from the panel"),
    "notifiche.livello.info": ("info", "info"),
    "notifiche.livello.avviso": ("avviso", "warning"),
    "notifiche.livello.allarme": ("allarme", "alarm"),
    "notifiche.prova.broker": (
        "Notifica pubblicata su %(topic)s e tornata indietro dal broker: la catena funziona.",
        "Notification published on %(topic)s and echoed back by the broker: the chain works."),
    "notifiche.prova.diretta": (
        "Broker irraggiungibile: la notifica è andata diretta. Quelle di Home Assistant no.",
        "Broker unreachable: the notification went direct. Home Assistant's will not arrive."),
    "notifiche.prova.spento": (
        "Il servizio Notifiche è spento: accendilo qui sopra, altrimenti la "
        "prova non ha niente da mostrare.",
        "The Notifications service is off: turn it on above, otherwise the "
        "test has nothing to show."),
    "status.notifiche.waiting": (
        "in ascolto su %(topic)s — %(shown)d mostrate, %(dropped)d scartate",
        "listening on %(topic)s — %(shown)d shown, %(dropped)d dropped"),
    "status.notifiche.showing": ("a schermo: %(text)s", "on screen: %(text)s"),
    "cielo.status.giorno": ("di giorno tace: parla dal tramonto all'alba",
                            "quiet by day: it speaks from sunset to sunrise"),
    "cielo.status.notte": ("stanotte: %(shown)d a schermo, %(lost)d perse",
                           "tonight: %(shown)d on screen, %(lost)d missed"),
    "cielo.prova": ("Mostra la Luna adesso", "Show the Moon now"),
    "status.onair.riposo": ("non in onda", "not on air"),
    "status.onair.attivo": (
        "in onda da %(minuti)d min — %(shown)d comparse",
        "on air for %(minuti)d min — shown %(shown)d times"),
    "status.onair.schermo": ("a schermo: %(text)s", "on screen: %(text)s"),
    "status.notifiche.error": ("ultimo messaggio scartato: %(error)s",
                               "last message dropped: %(error)s"),
    "services.desc.satelliti": (
        "Avvisa dieci minuti prima che la Stazione Spaziale passi sopra casa, "
        "e durante il passaggio mostra dove guardare.",
        "Warns ten minutes before the Space Station flies over, and during "
        "the pass shows where to look."),
    # ---------------------------------------------------------------- meteo
    "services.meteo": ("Meteo", "Weather"),
    "services.desc.meteo": (
        "Il bollettino del mattino e un aggiornamento ogni poche ore. Usa la posizione comune.",
        "The morning forecast and an update every few hours. It uses the shared position."),
    "meteo.status.ok": (
        "%(temperatura)s %(descrizione)s · oggi %(massima)s / %(minima)s · "
        "dato di %(minuti)d minuti fa",
        "%(temperatura)s %(descrizione)s · today %(massima)s / %(minima)s · "
        "data from %(minuti)d minutes ago"),
    "meteo.status.waiting": ("in attesa della prima previsione",
                             "waiting for the first forecast"),
    "meteo.status.nopos": (
        "nessuna posizione: si configura nella pagina Radar",
        "no position set: configure it on the Radar page"),
    "meteo.status.error": ("previsione non aggiornata: %(motivo)s",
                           "forecast not updated: %(motivo)s"),
    "meteo.title": ("Meteo", "Weather"),
    "meteo.hour": ("Ora del bollettino del mattino",
                   "Morning bulletin hour"),
    "meteo.rotation": ("Senza media, compare ogni (minuti, 0 = mai)",
                       "Without media, appears every (minutes, 0 = never)"),
    "meteo.every": ("Dati richiesti ogni (ore)", "Fetch data every (hours)"),
    "meteo.mattino": ("Fascia del mattino: il bollettino più spesso",
                      "Morning window: the forecast more often"),
    "meteo.mattino.dalle": ("Dalle", "From"),
    "meteo.mattino.alle": ("Alle", "To"),
    "meteo.mattino.ogni": ("Nella fascia, ogni (minuti)", "In the window, every (minutes)"),
    "meteo.duration.bulletin": ("Durata del bollettino (secondi)",
                                "Bulletin duration (seconds)"),
    "meteo.duration.update": ("Durata dell'aggiornamento (secondi)",
                              "Update duration (seconds)"),
    "meteo.test": ("Mostra adesso sul pannello", "Show on the panel now"),
    "meteo.test.bulletin": ("Prova il bollettino", "Try the bulletin"),
    "meteo.source": (
        "Le previsioni vengono da Open-Meteo, senza chiavi. La posizione è quella di Impostazioni.",
        "Forecasts come from Open-Meteo, no key needed. The position is the one in Settings."),
    "meteo.unit": ("Unità della temperatura", "Temperature unit"),
    "meteo.unit.c": ("Celsius (°C)", "Celsius (°C)"),
    "meteo.unit.f": ("Fahrenheit (°F)", "Fahrenheit (°F)"),
    "meteo.region": ("Regione per le allerte", "Region for alerts"),
    "meteo.region.none": ("— nessuna, niente allerte —",
                          "— none, no alerts —"),
    "meteo.alerts": ("Mostra le allerte", "Show alerts"),
    "meteo.test.alert": ("Prova l'allerta", "Try the alert"),
    "meteo.alert.source": (
        "Le allerte vengono da MeteoAlarm. Senza una regione scelta non se ne mostra nessuna.",
        "Alerts come from MeteoAlarm. With no region chosen, none are shown."),
    "meteo.status.alert": ("allerta %(livello)s: %(evento)s",
                           "%(livello)s alert: %(evento)s"),

    "nav.rete": ("Rete", "Network"),
    "rete.title": ("Rete wifi", "Wi-Fi network"),
    "rete.current": ("Collegamento attuale", "Current connection"),
    "rete.state": ("Stato", "State"),
    "rete.interface": ("Interfaccia", "Interface"),
    "rete.connected": ("collegato a %(name)s", "connected to %(name)s"),
    "rete.connected.noname": ("collegato", "connected"),
    "rete.disconnected": ("non collegato", "not connected"),
    "rete.nonmcli": (
        "Su questa macchina non c'è nmcli: la rete si cambia da riga di comando, qui sotto.",
        "There is no nmcli here: the network is changed from the command line, below."),
    "rete.addresses": ("Il DMD risponde a:", "The DMD answers at:"),
    "rete.scan": ("Reti visibili", "Networks in range"),
    "rete.scan.button": ("Cerca le reti", "Scan"),
    "rete.scan.hint": (
        "La ricerca dura qualche secondo e disturba il pannello: si fa quando serve.",
        "A scan takes a few seconds and disturbs the panel: do it when needed."),
    "rete.none": ("Nessuna rete trovata.", "No networks found."),
    "rete.open": ("aperta", "open"),
    "rete.known": ("già salvata", "saved"),
    "rete.name": ("Nome della rete", "Network name"),
    "rete.password": ("Password", "Password"),
    "rete.password.keep": ("Vuoto = quella salvata", "Empty = the saved one"),
    "rete.connect": ("Collega", "Connect"),
    "rete.hidden": ("Rete nascosta", "Hidden network"),
    "rete.hidden.hint": (
        "Una rete che non trasmette il proprio nome non compare nell'elenco: "
        "va scritto a mano.",
        "A network that does not broadcast its name is not listed: type it "
        "in by hand."),
    "rete.saved": ("Reti salvate", "Saved networks"),
    "rete.saved.hint": (
        "Il DMD si ricollega da solo, in ordine di segnale. Quella in uso non si può dimenticare.",
        "The DMD reconnects on its own, by signal. The one in use cannot be forgotten."),
    "rete.forget": ("Dimentica", "Forget"),
    "rete.forgotten": ("Rete %(name)s dimenticata.", "Network %(name)s forgotten."),
    "rete.trying": (
        "Provo a collegarmi a %(name)s. Se riesce, riapri la pagina su un indirizzo qui sopra.",
        "Connecting to %(name)s. If it works, reopen this page on one of the addresses above."),
    "rete.failed": ("Non è stato possibile: %(error)s",
                    "It did not work: %(error)s"),
    "rete.attempt.running": ("tentativo su %(name)s in corso…",
                             "attempt on %(name)s in progress…"),
    "rete.attempt.ok": ("ultimo tentativo: %(name)s, riuscito",
                        "last attempt: %(name)s, succeeded"),
    "rete.attempt.failed": ("ultimo tentativo: %(name)s, fallito",
                            "last attempt: %(name)s, failed"),
    "rete.console": ("Se questa pagina non basta", "If this page is not enough"),
    "rete.console.hint": (
        "Da SSH o da tastiera attaccata al Raspberry, con l'utente root o "
        "con sudo:",
        "Over SSH, or with a keyboard attached to the Raspberry, as root or "
        "with sudo:"),
    "nav.updates": ("Aggiornamenti", "Updates"),
    "nav.updates.badge": ("C'è una versione nuova", "A new version is available"),
    "nav.updates.esito": ("L'ultimo aggiornamento è finito male",
                          "The last update ended badly"),
    "updates.intro": (
        "Qui si aggiornano il programma e la libreria della matrice.",
        "Here you update the program and the matrix library."),
    # ----------------------------------------------------------------- rifiuti
    "nav.scadenze": ("Scadenze", "Deadlines"),
    "scadenze.title": ("Scadenze e appuntamenti", "Deadlines and appointments"),
    "scadenze.intro": (
        "Un semaforo a destra dell'orologio dice se c'è qualcosa in arrivo.",
        "A traffic light beside the clock says whether something is due."),
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
        "Una riga per scadenza: id;titolo;data;ricorrenza;descrizione;attiva;completate.",
        "One row per deadline: id;title;date;recurrence;description;active;done."),
    "scadenze.soglie": ("Semaforo", "Traffic light"),
    "scadenze.soglie.hint": (
        "Giorni che mancano. Oltre la soglia verde il semaforo è spento; scaduta, lampeggia.",
        "Days remaining. Past the green threshold the light stays off; overdue, it blinks."),
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
        "Ogni occorrenza con l'ora in cui è stata inserita e completata. Non si cancella mai.",
        "Every occurrence with when it was added and when it was done. It is never erased."),
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
        "Scritti per 256x64: campo di gioco a sinistra, tabellone a destra. Si preme Gioca.",
        "Written for 256x64: playfield on the left, scoreboard on the right. Press Play."),
    "giochi.play": ("Gioca", "Play"),
    "giochi.esci": ("Esci dalla partita", "Quit the game"),
    "giochi.record": ("Record:", "High score:"),
    "giochi.breakout.hint": (
        "Fra muro e racchetta ci sono trenta pixel: la palla accelera ogni quattro mattoni.",
        "Thirty pixels between wall and paddle: the ball speeds up every four bricks."),
    "giochi.invaders.hint": (
        "Tre file invece di cinque: su sessantaquattro righe la discesa originale non ci sta.",
        "Three rows instead of five: the original descent does not fit in sixty-four rows."),
    "giochi.pongo.hint": (
        "Tu contro il computer. Su e giù, avanti fino a metà campo; vince chi fa undici.",
        "You against the computer. Up, down, forward to midfield; first to eleven wins."),
    "giochi.musica": ("Musica di sottofondo nei giochi (separata dagli effetti)",
                      "Background music in games (separate from sound effects)"),
    "giochi.gnam.hint": (
        "Il labirinto, le palline e quattro fantasmi, ognuno col suo modo di inseguire.",
        "The maze, the dots and four ghosts, each chasing in its own way."),
    "giochi.squadriglia.hint": (
        "Un caccia contro le squadriglie, in stile 1942. Cerchio per il looping.",
        "A fighter against enemy squadrons, 1942 style. Circle for the loop."),
    "giochi.pongo.record": ("Scambio più lungo:", "Longest rally:"),
    "giochi.azzera": ("Azzera", "Reset"),
    "giochi.azzera.titolo": ("Azzera il record", "Reset the high score"),
    "giochi.azzera.conferma": ("Azzerare il record di %(gioco)s? Non si torna indietro.",
                               "Reset the %(gioco)s high score? This cannot be undone."),
    "giochi.pongo.livello": ("Computer", "Computer"),
    "giochi.pongo.facile": ("Facile", "Easy"),
    "giochi.pongo.normale": ("Normale", "Normal"),
    "giochi.pongo.difficile": ("Difficile", "Hard"),
    "giochi.snake.hint": (
        "Il serpente dei Nokia su una griglia 49x15. Quattro direzioni, e il bordo uccide.",
        "The Nokia snake on a 49x15 grid. Four directions, and the wall kills."),
    "giochi.doom.hint": (
        "Doom gira come processo separato e ha una pagina sua.",
        "Doom runs as a separate process and has a page of its own."),
    "giochi.doom.apri": ("Apri la pagina di Doom", "Open the Doom page"),
    "giochi.gb.apri": ("Apri la pagina di PyBoy", "Open the PyBoy page"),
    "giochi.esterni": ("Emulatori esterni", "External emulators"),
    "giochi.esterni.hint": (
        "Doom e il Game Boy girano per conto loro e hanno una pagina ciascuno.",
        "Doom and the Game Boy run on their own and have a page each."),
    "giochi.doom.stato": ("WAD:", "WAD:"),
    "giochi.doom.si": ("pronto", "ready"),
    "giochi.doom.no": ("da preparare", "needs setup"),
    "giochi.comandi": ("Comandi", "Controls"),
    "giochi.comandi.hint": (
        "Si gioca con il pad o con una tastiera; questi pulsanti servono per provare dal telefono.",
        "Play with the pad or a keyboard; these buttons are for trying it from the phone."),
    "settings.update.cache": (
        "La risposta di GitHub può essere vecchia di cinque minuti.",
        "GitHub's answer can be up to five minutes old."),
    "meteo.status.vista": (
        "vista %(minuti)d min fa (%(comparse)d volte, %(perse)d turni persi)",
        "seen %(minuti)d min ago (%(comparse)d times, %(perse)d turns lost)"),
    "meteo.giorno.oggi": ("OGGI", "TODAY"),
    "meteo.giorno.domani": ("DOMANI", "TOMORROW"),
    "giochi.audio": ("Audio della partita", "Game audio"),
    "giochi.audio.hint": (
        "Quanti effetti ha chiesto il gioco e quanti ne sono usciti davvero dalla scheda.",
        "How many effects the game asked for, and how many really left the card."),
    "giochi.audio.chiesti": ("Chiesti dal gioco", "Asked by the game"),
    "giochi.audio.resi": ("Usciti davvero", "Actually played"),
    "giochi.audio.resa": ("Resa", "Delivered"),
    "giochi.audio.scaduti": ("Scaduti in attesa", "Expired waiting"),
    "giochi.audio.scartati": ("Buttati per pieno", "Dropped, queue full"),
    "giochi.audio.morti": ("Cadute del riproduttore", "Player crashes"),
    "giochi.audio.riavvii": ("Riaperture della scheda", "Card reopenings"),
    "giochi.audio.vuoti": ("Buchi della scheda (underrun)",
                           "Card gaps (underrun)"),
    "giochi.audio.cuscino": ("Cuscino", "Cushion"),
    "giochi.audio.buffer": ("Buffer concesso dalla scheda",
                            "Buffer granted by the card"),
    "giochi.audio.spento": (
        "Il mixer non e' aperto: la partita e' muta.",
        "The mixer is not open: this game is silent."),
    "giochi.audio.arreso": (
        "La scheda audio non si e' liberata e il mixer ha smesso di provare.",
        "The sound card never freed up and the mixer stopped trying."),
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
        "Vuoto = tutti i dispositivi visti come tastiera o joystick. Es: /dev/input/event3.",
        "Empty = every device the kernel calls a keyboard or a joystick. E.g. /dev/input/event3."),
    "giochi.ciclo.hint": (
        "Start scorre i giochi, Select esce. Sulla tastiera fanno lo stesso i tasti qui sotto.",
        "Start cycles the games, Select exits. On a keyboard the keys below do the same."),
    "giochi.tasto.ciclo": ("Tasto che scorre i giochi",
                           "Key that cycles the games"),
    "giochi.tasto.esci": ("Tasto che esce dalla partita",
                          "Key that quits the game"),
    "giochi.impara": ("Impara", "Learn"),
    "giochi.impara.hint": (
        "I predefiniti sono invio ed escape. Per un altro tasto: premi «Impara», poi il tasto.",
        "The defaults are enter and escape. For another key press “Learn”, then the key."),
    "giochi.impara.premi": ("In ascolto: premi ora il tasto che vuoi usare.",
                            "Listening: press the key you want to use now."),
    "giochi.impara.fatto": ("Riconosciuto, codice", "Recognised, code"),
    "giochi.ciclo_doom": (
        "Comprendi anche Doom nel giro dei giochi (parte in qualche secondo e "
        "vuole un WAD preparato)",
        "Include Doom in the game cycle too (it takes a few seconds to start "
        "and needs a prepared WAD)"),
    "giochi.ciclo_gameboy": ("Il tasto Start scorre anche il Game Boy",
                             "The Start button also cycles the Game Boy"),
    "giochi.ciclo_gameboy.hint": (
        "Entra nel giro solo con PyBoy installato e una cartuccia valida. Per uscire, il tasto PS.",
        "Joins the cycle only with PyBoy installed and a valid cartridge. Exit with the PS button."),
    "giochi.timeout": ("Chiudi la partita dopo (secondi senza comandi)",
                       "Close the game after (seconds with no input)"),
    "giochi.timeout.hint": (
        "Una partita lasciata a metà non tiene il pannello per sempre. Zero per non chiuderla mai.",
        "A game left half-played does not keep the panel forever. Zero never closes it."),
    "status.giochi.ferma": ("nessuna partita in corso", "no game running"),
    "status.giochi.partita": (
        "%(gioco)s: %(punteggio)d punti, %(vite)d vite",
        "%(gioco)s: %(punteggio)d points, %(vite)d lives"),
    "nav.rifiuti": ("Rifiuti", "Waste"),
    "rifiuti.title": ("Raccolta rifiuti e attività comunali",
                      "Waste collection and municipal activities"),
    "rifiuti.intro": (
        "La raccolta è una regola, non un elenco di date: giorni fissi più qualche eccezione.",
        "Collection is a rule, not a list of dates: fixed days plus a few exceptions."),
    "rifiuti.now": ("Da esporre adesso:", "To put out now:"),
    "rifiuti.now.none": ("Adesso non c'è niente da esporre.",
                         "Nothing to put out right now."),
    "rifiuti.voci": ("Frazioni e attività", "Streams and activities"),
    "rifiuti.voci.hint": (
        "Una voce senza nessun giorno spuntato non compare da nessuna parte.",
        "An item with no day ticked does not appear anywhere."),
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
        "Il promemoria compare alle 18 della sera prima e sparisce alle 8 del giorno di raccolta.",
        "The reminder appears at 18 the evening before and clears at 8 on collection day."),
    "rifiuti.soppressioni": ("Giorni di mancato servizio", "Days with no service"),
    "rifiuti.soppressioni.hint": (
        "Una data per riga, «gg/mm/aaaa,voce,nota». La voce vuota vale per tutte.",
        "One date per row, “dd/mm/yyyy,item,note”. An empty item applies to all."),
    "rifiuti.straordinari": ("Giorni di servizio straordinario",
                             "Days with extra service"),
    "rifiuti.straordinari.hint": (
        "Stessa forma. Serve ai recuperi dopo una festività, e vale anche in un giorno soppresso.",
        "Same format. For catch-ups after a holiday, and it works on a suppressed day too."),

    # -------------------------------------------------------------------- doom
    "nav.doom": ("Doom", "Doom"),
    "doom.title": ("Doom", "Doom"),
    "doom.intro": (
        "Non è un servizio ma una partita: prende il pannello, e all'uscita tutto riprende.",
        "Not a service but a game: it takes the panel, and on exit everything resumes."),
    "doom.play": ("Gioca", "Play"),
    "doom.leave": ("Esci dalla partita", "Leave the game"),
    "doom.pad": ("Comandi", "Controls"),
    "doom.pad.hint": (
        "I pulsanti si tengono premuti: tenendo il dito su una freccia si cammina davvero.",
        "Buttons are held down: keeping a finger on an arrow really walks."),
    "doom.keyboard.hint": (
        "Vanno sia la tastiera di questo computer sia quella collegata al Raspberry.",
        "Both this computer's keyboard and the one attached to the Raspberry work."),
    "doom.key.fire": ("Fuoco", "Fire"),
    "doom.key.use": ("Apri", "Use"),
    "doom.key.run": ("Corri", "Run"),
    "doom.key.menu": ("Menu", "Menu"),
    "doom.key.enter": ("Invio", "Enter"),
    "doom.key.map": ("Mappa", "Map"),
    "doom.tuning": ("Immagine e partita", "Picture and game"),
    "doom.tuning.hint": (
        "Salvando, Doom riparte: fascia e gamma stanno nella riga di comando del programma.",
        "Saving restarts Doom: band and gamma live on the program's command line."),
    "doom.band.top": ("Prima riga della fascia", "First row of the band"),
    "doom.band.height": ("Altezza della fascia", "Height of the band"),
    "doom.band.hint": (
        "Si ritaglia una fascia attorno all'orizzonte: riga 36 per 96 righe è il punto di partenza.",
        "A band around the horizon is cropped: row 36 for 96 rows is the starting point."),
    "doom.gamma": ("Gamma", "Gamma"),
    "doom.gamma.hint": (
        "Sotto 1 schiarisce. Difficoltà da 1 a 5; il livello si scrive «episodio mappa», es. «1 1».",
        "Below 1 brightens. Skill 1 to 5; the level is written “episode map”, e.g. “1 1”."),
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
    "doom.keyboard.device": ("Tastiera da usare", "Keyboard to use"),
    "doom.keyboard.read": ("Leggi la tastiera collegata al Raspberry",
                           "Read the keyboard plugged into the Raspberry Pi"),
    "doom.pad.device": ("Joystick da usare", "Joystick to use"),
    "doom.pad.read": ("Leggi i joystick collegati al Raspberry",
                      "Read the joysticks plugged into the Raspberry Pi"),
    "doom.pad.starts": ("Options sul pad può far cominciare una partita",
                        "Options on the pad can start a game"),
    "doom.pad.starts.hint": (
        "Dal pad Doom non si apre: Start scorre i giochi e Select esce. Si parte da «Gioca».",
        "The pad does not open Doom: Start cycles games and Select exits. Start it from “Play”."),
    "doom.pad.found": ("Joystick trovati: %(list)s", "Joysticks found: %(list)s"),
    "doom.pad.none": (
        "Nessun joystick collegato al Raspberry in questo momento.",
        "No joystick connected to the Raspberry Pi right now."),
    "doom.pad.hint2": (
        "Levette per camminare e girare, R2 o croce sparano, L1 corre, triangolo è la mappa.",
        "Sticks walk and turn, R2 or cross shoot, L1 runs, triangle is the map."),
    "doom.binary": ("Programma", "Program"),
    "doom.wad": ("WAD", "WAD"),
    "doom.nobinary": (
        "Doom non è ancora pronto: va preparato una volta sola, con il "
        "pulsante qui sotto.",
        "Doom is not ready yet: it has to be prepared once, with the button "
        "below."),
    "doom.mute": (
        "Il programma è stato compilato senza audio, quindi «Audio di Doom» "
        "nelle Impostazioni non può funzionare: fino alla 5.4 nessun modulo "
        "sonoro veniva compilato. Premi «Prepara Doom» qui sotto per "
        "installare SDL2 e ricompilare — sono un paio di minuti.",
        "The program was compiled without audio, so «Doom audio» in Settings "
        "cannot work: until 5.4 no sound module was compiled in at all. Press "
        "«Prepare Doom» below to install SDL2 and rebuild — a couple of "
        "minutes."),
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
        "Spento, la partita comincia solo da «Gioca». A partita aperta la tastiera comanda comunque.",
        "Off, the game starts only from “Play”. Once open, the keyboard still controls it."),
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
        "Finché questa pagina è aperta il pannello è tuo. Chiudendola torna al suo lavoro.",
        "While this page is open the panel is yours. Close it and it goes back to work."),
    "manager.exit": ("Esci dalla gestione", "Leave the manager"),
    "manager.view.hint": (
        "«Vedi» manda il file sul pannello, non nel browser. Resta finché non ne scegli un altro.",
        "“View” sends the file to the panel, not the browser. It stays until you pick another."),
    "media.manager.hint": (
        "Elenco, caricamento e anteprime stanno nella Gestione media, dove le sorgenti si fermano.",
        "The list, uploads and previews live in Media manager, where the sources pause."),
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
        "L'emulatore prende il pannello per il tempo della partita, come Doom.",
        "The emulator takes the panel for the length of the game, like Doom."),
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
        "Hanno effetto alla partenza: cambiandoli durante una partita, la partita riparte.",
        "They take effect at start-up: changing them mid-game restarts the game."),
    "gb.overscan": ("Overscan (%)", "Overscan (%)"),
    "gb.gamma": ("Gamma", "Gamma"),
    "gb.fps": ("Fotogrammi al secondo", "Frames per second"),
    "gb.palette": ("Colori dello schermo", "Screen colours"),
    "gb.palette.livello": ("Livello %(n)d", "Level %(n)d"),
    "gb.palette.hint": (
        "Il Game Boy ha quattro gradazioni. I quattro riquadri valgono solo con Personalizzata.",
        "The Game Boy has four shades. The four swatches apply only with Custom."),
    "gb.spostamento": ("Spostamento verticale (righe)",
                       "Vertical shift (rows)"),
    "gb.spostamento.hint": (
        "Con l'overscan, un numero negativo alza la finestra e uno positivo la abbassa.",
        "With overscan on, a negative number raises the window and a positive one lowers it."),
    "gb.overscan.hint": (
        "Toglie righe sopra e sotto: l'immagine diventa più larga. 71 pixel a zero, 116 al 40%%.",
        "Cuts rows above and below, so the picture gets wider: 71 pixels at zero, 116 at 40%%."),
    "gb.comandi": ("Comandi", "Controls"),
    "gb.cartella": ("Cartella delle ROM", "ROM folder"),
    "gb.keyboard.starts": (
        "Un tasto della tastiera pu\u00f2 far cominciare una partita",
        "A keyboard key may start a session"),
    "gb.pad.hint": (
        "Croce e cerchio sono A e B; Start e Select stanno sulle levette premute, L3 e R3.",
        "Cross and circle are A and B; Start and Select are the pressed sticks, L3 and R3."),
    "gb.pad.tasti": (
        "Dal pad non si apre una partita: si comincia da questa pagina o dalla tastiera.",
        "The pad never opens a game: start it from this page or from the keyboard."),
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

    # -------------------------------------------------------------- calendario
    "nav.calendario": ("Calendario", "Calendar"),
    "calendario.title": ("Google Calendar", "Google Calendar"),
    "calendario.intro": (
        "Il pannello mostra gli appuntamenti dei prossimi %(giorni)s giorni. Si scrivono su Google.",
        "The panel shows the next %(giorni)s days of appointments. You write them in Google."),
    "calendario.connected": ("Collegato come %(name)s.", "Connected as %(name)s."),
    "calendario.connected.anon": ("Account collegato.", "Account connected."),
    "calendario.notconnected": ("Nessun account collegato.",
                                "No account connected."),
    "calendario.client_id": ("Client ID", "Client ID"),
    "calendario.client_secret": ("Client secret", "Client secret"),
    "calendario.secret.kept": ("già salvato, lascia vuoto per tenerlo",
                               "already saved, leave empty to keep it"),
    "calendario.redirect": ("Indirizzo di ritorno", "Redirect URI"),
    "calendario.redirect.hint": (
        "Dev'essere identico a quello scritto nel client OAuth su Google Cloud.",
        "It must match the one set in the OAuth client on Google Cloud, character for character."),
    "calendario.steps": ("Come collegare l’account",
                         "How to link the account"),
    "calendario.step1": (
        "Su console.cloud.google.com crea un progetto e abilita la Google "
        "Calendar API.",
        "On console.cloud.google.com create a project and enable the Google "
        "Calendar API."),
    "calendario.step2": (
        "Aggiungi il permesso calendar.readonly e pubblica in produzione, o Google scollega.",
        "Add the calendar.readonly scope and publish to production, or Google disconnects."),
    "calendario.step3": (
        "Crea credenziali di tipo Applicazione web e incolla qui sopra Client "
        "ID e Client secret.",
        "Create credentials of type Web application and paste Client ID and "
        "Client secret above."),
    "calendario.step4": (
        "Aggiungi l’indirizzo di ritorno qui sopra fra gli URI "
        "autorizzati del client.",
        "Add the redirect URI above to the client’s authorized URIs."),
    "calendario.step5": (
        "Premi Autorizza, apri il link dal browser del tuo computer, accetta, "
        "e incolla qui sotto l’indirizzo su cui sei finito.",
        "Press Authorize, open the link in your computer’s browser, "
        "accept, then paste below the address you ended up on."),
    "calendario.authorize": ("Autorizza", "Authorize"),
    "calendario.open": (
        "Apri questo indirizzo nel browser e accetta:",
        "Open this address in your browser and accept:"),
    "calendario.paste": (
        "Indirizzo su cui sei finito dopo aver accettato",
        "Address you landed on after accepting"),
    "calendario.complete": ("Completa il collegamento", "Complete linking"),
    "calendario.disconnect": ("Scollega l’account", "Disconnect account"),
    "calendario.disconnect.hint": (
        "Cancella i token e chiede a Google di revocare il permesso. Client ID e secret restano.",
        "Deletes the tokens and asks Google to revoke access. Client ID and secret stay."),
    "calendario.tokens.hint": (
        "I token stanno in /var/lib/dmd/google.json, leggibili solo da root.",
        "The tokens live in /var/lib/dmd/google.json, readable only by root."),
    "calendario.next": ("Prossimi appuntamenti", "Upcoming appointments"),
    "calendario.next.hint": (
        "I prossimi %(giorni)s giorni del calendario principale, come li vede il pannello.",
        "The next %(giorni)s days of the main calendar, as the panel sees them."),
    "calendario.next.none": ("Nessun appuntamento nella finestra.",
                             "No appointments in the window."),
    "calendario.refresh": ("Rileggi da Google", "Refresh from Google"),
    "calendario.google.ok": ("Account Google collegato.",
                             "Google account linked."),
    "calendario.google.gone": (
        "Account scollegato. Google non ha confermato la revoca: puoi chiuderla anche da lì.",
        "Account disconnected. Google did not confirm the revocation: you can close it there too."),
    "calendario.google.revoked": (
        "Account Google scollegato e permesso revocato.",
        "Google account disconnected and permission revoked."),
    "calendario.google.refreshed": ("Calendario riletto.",
                                    "Calendar refreshed."),
    "calendario.google.failed": ("Collegamento non riuscito: %(error)s",
                                 "Linking failed: %(error)s"),
    "services.desc.calendario": (
        "Avviso periodico degli appuntamenti di Google Calendar. Senza semaforo.",
        "Periodic notice of Google Calendar appointments. No traffic light."),
    "status.calendario.scollegato": ("account Google non collegato",
                                     "Google account not linked"),
    "status.calendario.errore": ("errore: %(error)s", "error: %(error)s"),
    "status.calendario.nessuno": (
        "nessun appuntamento nei prossimi %(giorni)s giorni",
        "no appointments in the next %(giorni)s days"),
    "status.calendario.attesa": (
        "%(count)d appuntamenti, %(shown)d avvisi mostrati",
        "%(count)d appointments, %(shown)d notices shown"),
    "status.calendario.mostra": ("in mostra: %(titolo)s", "showing: %(titolo)s"),

    # ---------------------------------------------------------------- taratura
    "settings.autotune": ("Avvia taratura", "Start tuning"),
    "settings.autotune.title": ("Taratura automatica", "Automatic tuning"),
    "settings.autotune.hint": (
        "Misura il pannello a vari rallentamenti e aggiunge il profilo. Circa quaranta minuti.",
        "Measures the panel at several slowdowns and adds the profile found. About forty minutes."),
    "settings.autotune.running": ("Taratura in corso: %(fatte)s su %(totale)s.",
                                  "Tuning: %(fatte)s of %(totale)s."),
    "settings.autotune.stop": ("Ferma la taratura", "Stop tuning"),
    "settings.autotune.started": ("Taratura avviata.", "Tuning started."),
    "settings.autotune.stopping": ("Mi fermo a fine misura.",
                                   "Stopping at the end of this measurement."),
    "settings.autotune.failed": ("Taratura non avviata: %(error)s",
                                 "Tuning not started: %(error)s"),
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
