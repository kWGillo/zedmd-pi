# DMD Controller 4.8

Servizio unico che possiede il pannello LED (256×64, FM6373 + DP32020B) su un
Raspberry Pi e lo condivide fra più sorgenti di contenuto, con interfaccia web
di controllo in italiano e inglese.

Nasce come emulatore di **ZeDMD-WiFi** per un cabinato, ma il pannello resta
acceso anche quando non si gioca: l'obiettivo è un oggetto da salotto che
racconta qualcosa — l'ora, il traffico aereo che passa sopra casa, la musica
in ascolto, gli appuntamenti di domani — e che, quando serve, torna a fare il
DMD.

## Servizi

Si accendono e si spengono uno per uno dalla pagina **Servizi**, e ognuno ha
un interruttore anche in Home Assistant.

- **ZeDMD** — ricevitore del protocollo ZeDMD-WiFi: Batocera, `dmdserver`,
  dmd-extensions o VPX inviano frame a questo Raspberry credendo di parlare
  con un ZeDMD reale.
- **Clock** — orologio e data, con colori indipendenti, formato 12/24 ore e
  nomi dei giorni in italiano, francese o inglese. È la sorgente di riserva:
  quando non ha da dire niente nessun altro, c'è lui.
- **Media Player** — foto e video a rotazione dalla libreria, con intervallo
  casuale. Libreria raggiungibile via SMB e via upload dalla web UI. Supporta
  anche il materiale Pixelcade, utilizzabile a prescindere da Batocera.
- **Air Radar** — gli aerei in transito entro un raggio da una coordinata GPS,
  tramite le API pubbliche ADS-B della comunità, con le sigle tradotte in nomi
  leggibili e un registro CSV dei passaggi.
- **Now Playing** — il brano in ascolto da AirPlay 2 (shairport-sync),
  dall'API di Spotify o da un topic MQTT libero.
- **Rolling Banner** — dieci testi scorrevoli a comparsa periodica, ciascuno
  con colore, dimensione, velocità e lampeggio propri.
- **Compleanni** — l'augurio compare da solo nel giorno giusto.
- **Scadenze** — un semaforo accanto all'orologio dice se c'è qualcosa in
  arrivo, e ogni tanto il pannello mostra che cosa. Si inseriscono dalla web
  UI, da un CSV o da Home Assistant.
- **Google Calendar** — gli appuntamenti dei prossimi tre giorni, a giro.
  Sola lettura, e **senza semaforo**: un appuntamento succede quando succede.
- **Rifiuti** — il calendario della raccolta nella colonna libera accanto
  all'orologio, calcolato da una cadenza fissa senza interrogare nessun
  portale.

## Partite

Non sono servizi: si comincia e si finisce. Premuto «Gioca» i servizi si
fermano, il pannello è del gioco finché non si esce, e poi torna al suo
lavoro. Si comandano da tastiera, da pad o dalla pagina web.

- **Doom** — `doomgeneric` in un processo separato, con i propri WAD su una
  condivisione di rete.
- **Game Boy** — l'emulatore PyBoy, con le ROM su una condivisione di rete.
  Lo schermo 160×144 sta al centro del pannello in proporzione, con overscan e
  spostamento verticale per allargarlo, gamma regolabile e sei tavolozze di
  colore.
- **Breakout e Invaders** — scritti per questo pannello, senza dipendenze.

Il tasto Start del pad scorre il giro dei giochi; PS esce.

## Il resto

Fasce orarie: **Night mode** abbassa la luminosità, **Sleep mode** spegne il
display. Sleep ha la precedenza su Night. Entrambe si comandano anche da Home
Assistant.

**Aggiornamento via rete** da questo repository, con verifica dell'archivio e
ripristino automatico se il servizio non riparte.

**Home Assistant** via MQTT Discovery: il brano corrente, un interruttore per
ogni servizio, la luminosità, il semaforo delle scadenze e il calendario dei
rifiuti compaiono da soli, comandabili e non solo leggibili.

---

## Documentazione

I manuali stanno in `docs/`, in Markdown e in PDF già impaginato. Sono nel
repository e dentro l'archivio scaricato: si aprono direttamente da GitHub,
oppure si scaricano con `git clone` o dal pulsante *Code → Download ZIP*.

| Documento | PDF |
|---|---|
| Manuale completo: hardware, cablaggio, installazione, diagnostica | `docs/DMD_manuale_completo.pdf` |
| ZeDMD-WiFi: protocollo e collegamento dei client | `docs/DMD_zedmd_wifi.pdf` |
| Now Playing: AirPlay, Spotify, MQTT, Home Assistant | `docs/DMD_now_playing.pdf` |
| Doom sul pannello | `docs/DMD_doom.pdf` |
| Game Boy sul pannello | `docs/DMD_gameboy.pdf` |
| Google Calendar | `docs/DMD_calendario.pdf` |
| Taratura automatica del pannello | `docs/DMD_taratura.pdf` |
| Joypad: mappatura dei comandi | `docs/DMD_joypad.pdf` |

I PDF **non** vengono installati in `/opt/dmd`: sul Raspberry non servono, e
l'aggiornamento via rete copia solo ciò che il servizio esegue.

---

## Requisiti

Un Raspberry Pi già preparato secondo la procedura del progetto:

- audio integrato disattivato (`dtparam=audio=off`)
- `isolcpus=3` sui modelli quad-core
- libreria `rpi-rgb-led-matrix_pwm_experiment` clonata e compilata
- pannelli cablati e verificati con la demo

---

## Installazione

Dal Mac, copia la cartella sul Raspberry:

```bash
scp -r dmd gillo@dmdpi.local:~/
```

Poi via SSH:

```bash
cd ~/dmd
chmod +x install.sh
sudo ./install.sh
```

Lo script installa le dipendenze, compila i binding Python della libreria
matrice, copia i file in `/opt/dmd`, crea `/etc/dmd/config.json` e registra il
servizio systemd.

Se la libreria matrice non è nella home dell'utente:

```bash
sudo MATRIX_DIR=/percorso/della/libreria ./install.sh
```

---

## Configurazione iniziale

Prima del primo avvio controlla `/etc/dmd/config.json`, in particolare:

| Chiave | Valore |
|---|---|
| `panel.slowdown` | `1` Zero W · `3` Zero 2 W e Pi 3 · `5` Pi 4 |
| `panel.chain` | numero di pannelli in cascata |
| `panel.profile_dir` | impostato automaticamente dall'installer |
| `web.port` | `8080`, porta dell'interfaccia web |
| `zedmd.http_port` | `80`, riservata all'handshake ZeDMD |

Avvio e log:

```bash
sudo systemctl start dmd
journalctl -u dmd -f
```

L'interfaccia è su `http://dmdpi.local:8080/`. Aprendo l'indirizzo senza porta
si viene rediretti automaticamente.

### Aggiornare un'installazione esistente

```bash
cd ~/dmd && chmod +x update.sh && sudo ./update.sh
```

---

## Le tre porte

| Porta | Chi la usa | Servita da |
|---|---|---|
| 80 | handshake ZeDMD (cablata nel client) | server HTTP dedicato |
| 3333 | frame DMD, TCP e UDP | ricevitore ZeDMD |
| 8080 | interfaccia web | Flask |

L'handshake **non** passa da Flask, e non è un dettaglio estetico: il client di
libzedmd legge la risposta con una sola `recv()` e si ferma appena riceve meno
di 1024 byte. Flask invia header e corpo con due scritture separate, che sulla
rete diventano due pacchetti: il client leggerebbe solo gli header, vedrebbe un
corpo vuoto, e con tutti i campi a zero non riconoscerebbe il trasporto TCP,
ripiegando su UDP. Il server dedicato invia tutto in una sola `sendall()`.

## Collegare un client ZeDMD

Il servizio si presenta come un ZeDMD-WiFi. Nel client indica solo l'indirizzo
IP del Raspberry: userà da sé la porta 80 per l'handshake e la 3333 per i frame.

Su Batocera si configura in `/userdata/system/configs/dmdserver/config.ini`:

```ini
[DMDServer]
AltColor = 1

[ZeDMD]
Enabled = 0

[ZeDMD-WiFi]
Enabled = 1
WiFiAddr = 192.168.0.XXX
```

Poi va attivato il servizio `dmd_real` — dal menu di Batocera oppure:

```bash
batocera-services enable dmd_real
batocera-services start dmd_real
```

**Il `config.ini` da solo non avvia niente**: senza quel servizio non c'è
nessun processo che lo legga, e il Raspberry resta in ascolto senza mai vedere
un client. Si controlla così, e deve comparire un `dmdserver` con l'argomento
`-c /userdata/system/...`:

```bash
ps aux | grep dmdserver | grep -v grep
```

Verifica rapida dell'handshake:

```bash
curl http://dmdpi.local/handshake
```

Deve rispondere con 22 campi separati da `|`, i primi due sono larghezza e
altezza del display.

Dal lato Raspberry, `journalctl -u dmd` distingue i due guasti che da fuori si
somigliano: la riga `[zedmd-http] <ip> /handshake` dice che il client ha
raggiunto il Pi, la sua assenza che non ci ha mai provato — tipicamente un
`WiFiAddr` rimasto al vecchio indirizzo dopo aver cambiato scheda o Raspberry.

Un comportamento noto di EmulationStation, che non è un guasto: **tenendo
premuto il tasto di scorrimento l'immagine non si aggiorna**, e non si aggiorna
nemmeno al rilascio. ES apre una connessione verso `dmdserver` a ogni cambio di
selezione, ma durante la ripetizione automatica del tasto non ne apre nessuna.
Un tocco in più riallinea il pannello.

---

## Interfaccia web

Su `http://dmdpi.local:8080/`. Aprendo l'indirizzo senza porta si viene
rediretti automaticamente.

**Impostazioni** — luminosità con applicazione immediata, lingua
dell'interfaccia, regolazione fine del driver S-PWM, profili hardware del
pannello e **taratura automatica** (un pulsante: misura, e aggiunge il profilo
trovato al menu), esportazione e importazione della configurazione, indirizzo IP
locale, riavvio del servizio.

**Orologio** — colori di ora e data, formato 12/24 ore, lingua dei giorni,
lampeggio dei due punti, server NTP e fuso orario.

**Media** — libreria, caricamento, rilettura, anteprima immediata, durate e
intervalli, adattamento al pannello, modalità pixel art.

**Banner** — i dieci testi scorrevoli, uno per riga.

**Musica** — copertura delle sorgenti, collegamento dell'account Spotify,
aspetto del player, stato di MQTT e delle entità di Home Assistant.

**Compleanni** — l'elenco delle date, compleanni e anniversari.

**Scadenze** — le scadenze aperte con il loro semaforo, l'inserimento, il CSV,
il registro di quelle completate e le soglie dei tre colori.

**Calendario** — il collegamento dell'account Google e nient'altro, più
l'elenco in sola lettura degli appuntamenti che il pannello vede.

**Rifiuti** — le voci del calendario, i giorni della settimana e la cadenza di
ciascuna, e le due tabelle delle eccezioni.

**Radar** — coordinate e raggio, provider ADS-B, scelta dei parametri di volo,
registro CSV dei passaggi, tabelle di conversione dei codici, prova
diagnostica di una rotta.

**Giochi** — i giochi scritti per il pannello, i comandi di tastiera e pad, e
la scheda degli emulatori esterni che porta a Doom e al Game Boy.

**Doom** — preparazione, scelta del WAD, gamma, avvio e uscita.

**Game Boy** — installazione di PyBoy, condivisione delle ROM, scelta della
cartuccia, pad su schermo, overscan, spostamento verticale, gamma e tavolozza.

**Servizi** — attivazione dei servizi, indicazione della sorgente attualmente
a schermo e possibilità di forzarne una invece di lasciar decidere l'arbitro.

**Aggiornamenti** — controllo e installazione della nuova versione da questo
repository, con verifica dell'archivio e ripristino automatico se il servizio
non riparte.

---

## Come viene deciso chi va sul display

Un solo processo può pilotare i GPIO, quindi tutte le sorgenti convivono nello
stesso servizio e un arbitro sceglie chi vince:

| Priorità | Sorgente |
|---|---|
| 100 | ZeDMD |
| 90 | Anteprima (gestione media) |
| 60 | Air Radar |
| 59 | Google Calendar |
| 58 | Now Playing |
| 57 | Scadenze |
| 56 | Compleanni |
| 55 | Rolling Banner |
| 50 | Media Player |
| 10 | Clock |

**Nessuna coppia pareggia, e non è un caso.** A parità l'arbitro tiene chi si
è registrato per primo, quindi la seconda non andrebbe mai a schermo: il
Calendario era nato a 58, che è di Now Playing, e l'avviso non sarebbe mai
comparso mentre suona musica. Una prova rifiuta i pareggi.

Le partite — Doom, Game Boy, i giochi — non partecipano a questa gara: **prendono
il pannello** e lo tengono finché non si esce, sopra chiunque altro, ZeDMD
compreso. La stessa presa la usa la gestione della libreria media, con la
differenza che quella scade da sola se la pagina web smette di dare segni di
vita.

Sopra a tutto agiscono le fasce orarie: durante lo Sleep il display resta
spento qualunque sia la sorgente vincente (salvo il risveglio su frame ZeDMD,
se abilitato).

ZeDMD prende il controllo **immediatamente** appena un client si connette o
arriva un frame, e lo mantiene per `zedmd.grace_seconds` secondi dopo l'ultimo
segnale. Il tempo di grazia evita che l'orologio si intrometta durante le pause
di Batocera (menu, caricamenti); alzalo se vedi passaggi indesiderati.

---

## Struttura dei file

```
/opt/dmd/dmdd.py          servizio principale, arbitro e ciclo di rendering
/opt/dmd/display.py       proprietario esclusivo del pannello
/opt/dmd/dmdconf.py       configurazione persistente
/opt/dmd/webui.py         Flask: pagine + endpoint del protocollo ZeDMD
/opt/dmd/sources/         sorgenti di contenuto
/opt/dmd/mqttbus.py       client MQTT condiviso (ingresso metadati, uscita HA)
/opt/dmd/nowplaying.py    stato del brano corrente, indipendente dalla sorgente
/opt/dmd/spotifyapi.py    API web di Spotify (OAuth con PKCE)
/opt/dmd/gcalendar.py     API di Google Calendar (OAuth, sola lettura)
/opt/dmd/autotune.py      taratura automatica: misura, sceglie, salva il profilo
/opt/dmd/scadenze.py      scadenze, semaforo e registro
/opt/dmd/hass.py          entità di Home Assistant via MQTT Discovery
/opt/dmd/rifiuti.py       calendario della raccolta: cadenze ed eccezioni
/opt/dmd/diagnostica/     strumenti di misura del pannello, per la taratura
/opt/dmd/doom/            preparazione e ponte verso doomgeneric
/opt/dmd/gb/              preparazione e ponte verso PyBoy
/srv/dmd/media            libreria media, condivisa come \\<ip>\dmd-media
/srv/dmd/doom             WAD di Doom, condivisi come \\<ip>\dmd-doom
/srv/dmd/rom              ROM Game Boy, condivise come \\<ip>\dmd-rom
/var/lib/dmd/soppressioni.csv, straordinari.csv  eccezioni del calendario
/etc/dmd/config.json      configurazione
/var/lib/dmd/spotify.json token di Spotify, permessi 0600, fuori dall'export
/var/lib/dmd/google.json  token di Google, permessi 0600, fuori dall'export
```

Aggiungere un servizio significa quattro cose, e vanno fatte tutte e quattro:
scrivere la sorgente in `sources/`, registrarla nel `Runtime`, aggiungere la
chiave a `services` **con la sua riga nella pagina Servizi**, e la voce in
`hass.SWITCHES`. Le ultime due si dimenticano — è successo con i Compleanni e
di nuovo con le Scadenze — e il sintomo è sempre lo stesso: una sorgente che
funziona e che non si accende mai. Ora una prova le pretende entrambe.

---

## Il protocollo ZeDMD, in breve

Ricostruito dal sorgente di `PPUC/libzedmd`.

**HTTP porta 80** — `GET /handshake` risponde con 22 campi separati da `|`:
larghezza, altezza, versione firmware, flag S3, protocollo, porta, ritardo UDP,
write-at-once, luminosità, ordine RGB, parametri del pannello, SSID, id,
potenza, tipo dispositivo, line decoder. Esistono anche gli endpoint singoli di
fallback (`/get_width`, `/get_height`, …).

**TCP porta 3333** — flusso di payload:

```
b"FRAME" + [ b"ZeDMD" + cmd(1) + size_hi(1) + size_lo(1) + compresso(1) + dati ]*
```

I dati compressi usano deflate. Comandi principali: `0x05` zone RGB565,
`0x04` zone RGB888, `0x06` render, `0x08` frame intero RGB565,
`0x07` frame intero RGB888, `0x0a` clear, `0x0b` keep-alive, `0x16` luminosità.

Le zone sono una griglia fissa 16 × 8 (128 zone): ogni zona è preceduta dal suo
indice, e un indice ≥ 128 significa "zona interamente nera" senza pixel a
seguire. Dichiarando `TCP` nell'handshake si evita la frammentazione UDP e il
flusso arriva ordinato.

---

## Risoluzione problemi

| Sintomo | Causa probabile | Rimedio |
|---|---|---|
| Il servizio non parte, errore su `rgbmatrix` | binding Python non compilati | rilanciare `install.sh`, oppure `pip install . --break-system-packages` dalla cartella della libreria |
| Pannello nero ma servizio attivo | nessuna sorgente abilitata | attivare Media Player - Clock dalla pagina Servizi |
| L'handshake risponde 200 ma non arriva nessun frame, e il client riprova all'infinito | la porta 80 è servita da Flask invece che dal server dedicato | verificare `zedmd.http_port = 80` e `web.port = 8080`, poi riavviare |
| `Address already in use` sulla porta 80 | altro web server attivo | `sudo systemctl stop lighttpd` (o simili) |
| Immagine a scatti | `panel.slowdown` errato per il modello | correggere il valore e riavviare il servizio |
| L'orologio interrompe Batocera | tempo di grazia troppo corto | alzare `zedmd.grace_seconds` |


---

## Libreria media

Cartella predefinita: `/srv/dmd/media`, condivisa in rete come `\\<ip>\dmd-media`.

Si possono caricare i principali formati di immagine (jpg, png, bmp, webp, tif)
e di video o animazione (gif, mp4, mkv, avi, mov, webm, mpg). L'adattamento a
256×64 avviene al momento della riproduzione: le immagini con Pillow, i video
con ffmpeg. Le animazioni brevi vengono ripetute fino a coprire la durata
impostata, comportamento pensato per le GIF di Pixelcade.

Le sottocartelle sono esplorate ricorsivamente: una raccolta Pixelcade si può
copiare così com'è.

---

## Storico versioni

Il dettaglio completo, versione per versione, sta in
[`CHANGELOG.md`](CHANGELOG.md) e nell'intestazione di `version.py`. Qui solo
le tappe.

| Versione | Contenuto |
|---|---|
| 1.0 | Ricevitore ZeDMD-WiFi, orologio, web UI |
| 1.1 | Media Player, Night e Sleep mode, condivisione SMB |
| 1.2 | Regolazione fine del driver S-PWM dalla web UI |
| 1.3 | Air Radar dalle API pubbliche ADS-B |
| 1.5 | Aggiornamento via rete da GitHub, con ripristino automatico |
| 1.7 | Interfaccia web in italiano e inglese |
| 1.7.2 | Impronte md5 di tutti i file, verificate prima e dopo la copia |
| 1.8 | Esportazione e importazione della configurazione |
| 1.9 | Rolling banner |
| 1.10 | Now Playing: AirPlay 2, Spotify, MQTT, entità in Home Assistant |
| 1.11 | Radar: tabelle CSV che traducono i codici in nomi leggibili |
| 2.0 | Compleanni, profili hardware del pannello, Night e Sleep da Home Assistant |
| 3.0 | Doom sul pannello, con doomgeneric in un processo separato |
| 3.2 | Doom non è un servizio ma una partita: prende il pannello e lo restituisce |
| 3.3 | Pad PS4 e da PC, avvio da Home Assistant |
| 3.4 | Calendario della raccolta rifiuti accanto all'orologio |
| 3.8 | Breakout e Invaders, scritti per il pannello; il giro del tasto Start |
| 4.0 | Scadenze: semaforo accanto all'orologio, avviso periodico, registro, MQTT |
| 4.1 | L'interruttore delle Scadenze mancava nella pagina Servizi: la chiave c'era, la riga no |
| 4.2 | Cablaggio Adafruit RGB Matrix Bonnet selezionabile dalla web UI |
| 4.3 | Registri del driver modificabili a mano, per la caccia al ghosting |
| 4.4 | Un fotogramma identico al precedente non viene riscritto: meno traffico sul bus di memoria, meno righe chiare |
| 4.5 | Game Boy: l'emulatore PyBoy, con ROM su condivisione SMB, overscan e gamma |
| 4.5.4 | Il servizio non partiva: cablaggio prima della costruzione. Aggiunta `test_avvio.py`, che costruisce il Runtime vero |
| 4.6 | Spostamento verticale dell'immagine Game Boy |
| 4.6.1 | Tavolozze dello schermo Game Boy |
| **4.7** | **Google Calendar: gli appuntamenti dei prossimi tre giorni, senza semaforo. Token fuori dalla configurazione, revoca del permesso allo scollegamento** |

---

## Scadenze

Un semaforo a destra dell'orologio dice **se** c'è qualcosa in arrivo; un
avviso periodico dice **che cosa**. Le soglie sono in giorni e si regolano:
oltre la verde il semaforo resta spento, perché una scadenza fra un mese non è
una notizia e un pannello che segnala sempre qualcosa non segnala più niente.

Le scadenze si inseriscono dalla web UI, si importano da un CSV, o arrivano da
Home Assistant su un topic MQTT. Quelle ricorrenti si rigenerano da sole alla
cadenza scelta; quelle completate finiscono in un registro scaricabile.

---

## Google Calendar

Gli appuntamenti dei prossimi **tre giorni** compaiono sul pannello a giro: in
alto a destra *quando*, nel colore che l'orologio usa per la data, al centro
*che cosa*, e sotto *dove*. Un appuntamento compare tre giorni prima e sparisce
quando è passato.

**Niente semaforo, di proposito.** Il semaforo dice *manca poco*, e ha senso
per una bolletta, che si può pagare prima; non ne ha per un appuntamento, che
succede quando succede.

È una vetrina, non un'agenda: sola lettura (`calendar.readonly`), solo il
calendario principale, e le ricorrenze le espande Google — al pannello arrivano
occorrenze con una data ciascuna invece di regole da interpretare. Calendari
secondari, colori e promemoria sono ignorati.

L'autorizzazione si fa **dal browser del proprio computer**, perché il DMD non
ha tastiera: si apre il link, si accetta, e si incolla l'indirizzo su cui si è
finiti. I token stanno in `/var/lib/dmd/google.json` con permessi `0600`, fuori
dalla configurazione; il *client secret* viene tolto dall'export come la
password del broker MQTT. Scollegando, il DMD chiede anche a Google di revocare
il permesso, così non resta un consenso in piedi dal loro lato.

Procedura completa su Google Cloud — compreso il passo che si dimentica,
**pubblicare la schermata di consenso in produzione**, senza il quale Google
scollega tutto dopo sette giorni — in `docs/calendario.it.md`.

---

## Giochi ed emulatori

Non sono servizi: sono partite. Si comincia dalla pagina o dal pad, i servizi
si fermano, il pannello è del gioco finché non si esce.

**Doom** gira come processo separato (`doomgeneric`), con i WAD su
`\\<ip>\dmd-doom`. **Game Boy** usa PyBoy, con le ROM su `\\<ip>\dmd-rom`: lo
schermo 160×144 viene portato a 64 righe mantenendo la proporzione — 71 pixel
al centro, i lati spenti — e l'**overscan** toglie righe sopra e sotto per
allargarlo, con uno **spostamento verticale** che decide da quale parte
tagliare. Gamma e tavolozza sono regolabili. Le ROM e i WAD sono dell'utente:
in questo progetto non ce n'è nessuno e non ce ne saranno mai.

**Breakout** e **Invaders** sono scritti per il pannello e non hanno
dipendenze. Il tasto Start del pad scorre il giro dei giochi disponibili; PS
esce.

Entrambi gli emulatori girano in un processo separato e non dentro il servizio.
Il motivo principale è il GIL: un emulatore nel nostro processo si contenderebbe
l'interprete con il ciclo che disegna il pannello, e su questo progetto la
moneta è il microsecondo — è misurato che basta la contesa sul bus di memoria
per accendere una riga sbagliata.

---

## Air Radar

Interroga a intervalli regolari le reti ADS-B comunitarie e mostra i voli entro
il raggio impostato. Servizi supportati, tutti gratuiti e senza chiave:

| Servizio | Endpoint |
|---|---|
| adsb.fi | `https://opendata.adsb.fi/api/v3/lat/{lat}/lon/{lon}/dist/{nm}` |
| adsb.one | `https://api.adsb.one/v2/point/{lat}/{lon}/{nm}` |
| adsb.lol | `https://api.adsb.lol/v2/point/{lat}/{lon}/{nm}` |

Sono compatibili tra loro (formato ADSBexchange v2): se quello scelto non
risponde, gli altri vengono usati automaticamente come riserva. Il raggio si
indica in chilometri e viene convertito in miglia nautiche; la distanza di ogni
aereo viene poi ricalcolata con l'emisenoverso perché il filtro dell'API è
approssimativo.

La rotta origine → destinazione arriva dal servizio `routeset` di adsb.lol
(`POST https://api.adsb.lol/api/0/routeset`), che accetta fino a 100 voli per
richiesta: tutte le rotte di un giro si ottengono con una sola chiamata.
Vengono preferiti i codici IATA, più corti e leggibili su un pannello stretto,
con ricaduta sugli ICAO quando mancano — cosa che succede spesso, ed è il
motivo per cui la tabella di conversione conosce entrambe le grafie. Se il servizio non risponde si ripiega
su hexdb.io, volo per volo.

La ricerca avviene solo se il campo è selezionato o se la si vuole nel registro
CSV. È disponibile per i voli di linea, molto meno per cargo, aviazione
generale e voli di Stato: la riga di stato riporta quante rotte sono state
trovate e quante no, e la pagina Radar ha una prova diagnostica per un singolo
codice volo.

I parametri mostrati sul pannello si scelgono dalla pagina Radar: rotta,
modello, immatricolazione, quota, velocità, direzione, transponder, distanza e
codice Mode S. Il codice volo compare sempre in grande.

Ogni passaggio viene registrato in `/var/lib/dmd/flights.csv`, scaricabile
dalla web UI. Colonne: `timestamp, hex, callsign, registration, type,
altitude_ft, speed_kt, track_deg, squawk, distance_km, latitude, longitude,
route`. Lo stesso aereo non viene riscritto finché resta nel raggio, quindi c'è
una riga per passaggio.

Le coordinate impostate restano solo in `/etc/dmd/config.json` su questo
Raspberry: non fanno parte del software distribuito.

Non essendoci un'antenna locale la copertura dipende dai riceventi volontari
della zona: il traffico commerciale compare quasi sempre, aviazione generale e
voli militari spesso no.


---

## Aggiornamento via rete

Il servizio confronta la propria versione con il `version.py` del repository
GitHub configurato e, se ne trova una più recente, la può installare da solo
dalla pagina Impostazioni.

L'installazione procede in quest'ordine, e si ferma al primo intoppo:

1. scarica l'archivio del ramo in una cartella temporanea
2. rifiuta archivi con percorsi assoluti o risalite di cartella
3. verifica la presenza dei file attesi e compila tutto il Python
4. salva una copia dell'installazione corrente in `/var/lib/dmd/backup`
5. sostituisce i file e riavvia il servizio
6. interroga `/api/status` per verificare che sia davvero ripartito
7. se non risponde, ripristina la copia e riavvia di nuovo

L'ultimo passo è il motivo per cui l'aggiornamento gira in un processo
staccato: deve sopravvivere al riavvio del servizio che lo ha avviato.

La configurazione in `/etc/dmd/config.json` non viene mai toccata, e il diario
delle operazioni resta in `/var/lib/dmd/ota.log`, consultabile dalla web UI.

---

## Now Playing

Il pannello mostra che cosa stai ascoltando: titolo, artista, album, stato e
avanzamento del brano. Il DMD non riproduce audio e non si mette fra la
musica e le casse — si limita ad ascoltare i metadati.

### Come arrivano i metadati

**AirPlay 2.** `shairport-sync` gira sul Raspberry e si presenta in rete come
una cassa AirPlay. L'audio finisce nella scheda fittizia `snd_dummy` (che ha
un orologio vero, a differenza di `/dev/null`), i metadati escono su MQTT. Al
ricevitore AirPlay non importa quale applicazione stia suonando: Apple Music,
Spotify, Amazon Music e YouTube funzionano tutte allo stesso modo, senza
niente da configurare per ciascuna.

**Spotify.** Copre la musica che *non* passa da AirPlay: Spotify Connect
verso casse vere, il computer, un Echo. Autenticazione OAuth con PKCE, senza
segreto dell'applicazione; i token stanno in `/var/lib/dmd/spotify.json` con
permessi `0600` e non compaiono mai in una configurazione esportata.

**Topic MQTT libero.** Qualsiasi altra cosa può pubblicare un JSON con
`title`, `artist`, `album`, `duration`, `position` e `playing` — sono
accettati anche i nomi di Home Assistant (`media_title`, `media_artist`, …).
È il modo di coprire un HomePod avviato a voce o un Echo, che il DMD non
vedrebbe altrimenti.

Quando più sorgenti hanno qualcosa da dire comanda AirPlay: se sta arrivando
un flusso audio qui, quello è ciò che si sta ascoltando. A parità, vince chi
suona su chi è in pausa.

### Senza Home Assistant

Il broker predefinito è `127.0.0.1`, cioè un Mosquitto installato sul
Raspberry stesso. Home Assistant è una possibilità, non un requisito.

### Con Home Assistant

Con `mqtt.discovery` attivo il DMD si presenta da solo via MQTT Discovery. In
Home Assistant compare un dispositivo con il brano corrente (titolo come
stato, il resto come attributi), un interruttore per ogni servizio e la
luminosità come `number`. Sono comandabili, non solo leggibili. Le entità
sono legate al testamento MQTT: se il servizio si ferma diventano *non
disponibili* invece di restare congelate.

Quando Home Assistant riparte non serve sorvegliarlo, e il DMD non ha bisogno
di sapere dove sia: le dichiarazioni sono pubblicate con `retain`, quindi il
broker le riconsegna a chi si iscrive dopo, e in più Home Assistant pubblica
`online` su `homeassistant/status` all'avvio — il DMD è iscritto a quel topic
e si ridichiara, con un ritardo casuale per non sommare la propria risposta a
quella di tutti gli altri dispositivi della casa. La pagina Musica ha
comunque un pulsante per ridichiarare a mano e uno per rimuovere le entità.

### La posizione nel brano

AirPlay manda `prgr` — tre timestamp RTP a 44100 Hz — solo al cambio di
traccia e dopo un salto; Spotify risponde solo quando lo si interroga. Fra un
aggiornamento e l'altro il tempo lo conta il DMD, ripartendo dall'ultimo
valore certo. Il conteggio usa `time.monotonic()` e non l'orologio di
sistema: una correzione NTP non deve far saltare la barra.

### Perché non c'è la copertina

A 64 pixel di lato sarebbe illeggibile, ma soprattutto è fatta quasi solo di
mezzi toni — il contenuto peggiore possibile per un pannello S-PWM a refresh
basso. Per la stessa ragione il testo si disegna **senza antialiasing**
(le sfumature dei bordi sono anch'esse mezzi toni) e, con l'opzione *Solo
colori pieni*, in otto soli colori saturi: la gerarchia fra le righe si
ottiene cambiando tinta invece che luminosità.

### Installazione

```bash
sudo /opt/dmd/setup_nowplaying.sh
```

Chiede il nome della cassa e dove sta il broker, poi fa tutto: Mosquitto,
dipendenze, `nqptp`, `shairport-sync` compilato con AirPlay 2 e metadati,
scheda audio fittizia, file di configurazione, confinamento ai core 0-2 e
sezione MQTT del DMD. Ripetibile: salta i passi già fatti, compresa la
compilazione. `--verifica` controlla lo stato senza toccare niente.

Viene installato insieme al resto ma non viene mai lanciato in
automatico: è facoltativo, e la sola compilazione porta via un quarto d'ora.
Non dipende da nessun altro file, quindi si può anche scaricare da solo.

### Dipendenze

`python3-paho-mqtt`. Se manca, la pagina Musica lo dice e Now Playing resta
spento; il resto del DMD non se ne accorge.

Guida completa, anche per farlo a mano: `docs/now-playing.it.md`.


### Quando i parametri non stanno su una riga

La fascia bassa è larga 256 pixel: oltre i quattro o cinque campi qualcosa
deve cedere. Con nove parametri selezionati la riga misura circa 400 pixel.
La pagina Radar decide come comportarsi:

| Modalità | Che cosa fa |
|---|---|
| **A pagine** (predefinita) | I campi si dividono in gruppi che ci stanno per intero e si alternano ogni `page_seconds` secondi. Non se ne perde nessuno, e il testo resta fermo. |
| **Scorrevole** | La riga passa da destra a sinistra a `scroll_speed` pixel al secondo. Si legge senza attese, ma è l'unica parte del pannello in movimento continuo: su una matrice a 29 Hz lascia una scia leggera. Qui `display_seconds` diventa un **minimo**: una passata iniziata arriva in fondo, e si cambia aereo quando il testo è uscito del tutto da sinistra. |
| **Accorcia la riga** | Il comportamento fino alla 1.11.3: i campi in eccesso vengono scartati dal fondo. |

Identificativo e rotta non si muovono mai: cambia solo la fascia bassa, così
l'aereo non salta mentre lo stai leggendo. Finché i campi ci stanno tutti le
tre scelte si comportano allo stesso modo.

---

## Conversioni dei codici del radar

Il radar riceve sigle. Il modello arriva come **designatore ICAO** (`B738`).
Gli aeroporti delle rotte arrivano invece **in due grafie**: il servizio
routeset di adsb.lol è documentato per rispondere con i codici IATA di tre
lettere (`MXP`), ma quel campo spesso non c'è e sia routeset sia hexdb.io
ripiegano sui codici ICAO di quattro (`LIMC`). Le tabelle conoscono entrambe.

Due file CSV modificabili traducono le sigle in nomi leggibili:

```
/var/lib/dmd/aerei.csv       177 tipi di aeromobile
/var/lib/dmd/aeroporti.csv   326 aeroporti
/var/lib/dmd/compagnie.csv   129 compagnie aeree
```

La compagnia non arriva come campo a sé: sta nelle **prime tre lettere del
nominativo di volo**. In `AFR1732` la compagnia è `AFR`, Air France — il
designatore ICAO, non la sigla IATA di due lettere del biglietto. Un
nominativo che non ha quella forma non ha una compagnia da mostrare:
l'aviazione generale usa l'immatricolazione (`I-ABCD`), e quel campo resta
vuoto invece di inventarsi una sigla.

Ogni riga ha tre campi — `codice,forma breve,nome completo`. Nella prima
colonna possono stare **più codici separati da `/`**, e la riga risponde a
tutti: è così che un aeroporto porta le due grafie senza doverne tenere
allineate due righe.

```
MXP/LIMC,Malpensa,Milano Malpensa
```

Servono due forme perché il pannello è largo 256 px e la riga del radar porta già rotta,
quota, velocità e distanza: `737-800` ci sta, `Boeing 737-800` no. Il nome
completo va nella web UI e nelle due colonne nuove del registro
(`type_name`, `route_name`), dove lo spazio non manca.

**Un codice che non è in tabella viene mostrato com'è.** Non è un errore, è
il comportamento previsto. Il sistema tiene il conto dei codici che incontra
senza saper tradurre e li elenca nella pagina Radar, ordinati per frequenza:
è la lista di cosa conviene aggiungere per primo, invece di doverlo
indovinare. Un pulsante li aggiunge in coda al file come righe da
completare.

I file si modificano dalla pagina Radar oppure a mano via SSH o SMB: una
modifica esterna viene raccolta senza riavviare il servizio, perché la
rilettura è legata a data e dimensione del file.

**Non vengono mai sovrascritti dagli aggiornamenti.** Vivono in
`/var/lib/dmd` proprio per questo: `/opt/dmd` viene riscritto a ogni
installazione, e le aggiunte fatte a mano sparirebbero. Al primo avvio i file
si creano da un modello contenuto nel pacchetto; da quel momento sono
dell'utente.

### Le tre fasce

Dalla 1.11.1 la rotta ha una riga sua, al centro, fra l'identificativo e i
dettagli: quello spazio prima restava vuoto, e su una riga sola i nomi lunghi
facevano scartare modello e quota per far entrare tutto. Ora ci stanno
`Orio al Serio→Stansted` sopra e `737-800  34000ft  450kt  3.2km` sotto.

Se la rotta tradotta è comunque troppo larga si tornano a mostrare i codici,
che ci stanno sempre: meglio un'informazione completa e stringata che una
tagliata a metà. Senza rotta il disegno resta a due fasce, come prima.

Il colore della rotta è regolabile a parte; lasciato vuoto segue quello dei
dettagli, così chi non tocca nulla non vede cambiare niente.
