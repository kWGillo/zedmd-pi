# DMD Controller 1.10

Servizio unico che possiede il pannello LED (256x64, FM6373) e lo condivide fra
più sorgenti di contenuto, con interfaccia web di controllo.

Servizi implementati:

- **ZeDMD** — ricevitore del protocollo ZeDMD-WiFi: Batocera, `dmdserver`,
  dmd-extensions o VPX possono inviare frame a questo Raspberry credendo di
  parlare con un ZeDMD reale.
- **Media Player** — foto e video a rotazione dalla libreria, con intervallo
  casuale. Libreria raggiungibile via SMB e via upload dalla web UI. Supporta
  anche il materiale Pixelcade, utilizzabile a prescindere da Batocera.
- **Clock** — orologio e data, con colori indipendenti, formato 12/24 ore e
  nomi dei giorni in italiano, francese o inglese.
- **Air Radar** — informazioni degli aerei in transito entro un raggio dato da
  una coordinata GPS, tramite le API pubbliche ADS-B della comunità.
- **Status Player** — presente nell'interfaccia ma non ancora implementato.

Fasce orarie: **Night mode** abbassa la luminosità, **Sleep mode** spegne il
display. Sleep ha la precedenza su Night.

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

Poi va riavviato il servizio `dmd_real`.

Verifica rapida dell'handshake:

```bash
curl http://dmdpi.local/handshake
```

Deve rispondere con 22 campi separati da `|`, i primi due sono larghezza e
altezza del display.

---

## Interfaccia web

**Impostazioni** — luminosità con applicazione immediata, server NTP, fuso
orario, ora legale automatica o scostamento UTC manuale, indirizzo IP locale e
stato della sincronizzazione oraria.

**Servizi** — attivazione dei quattro servizi, indicazione della sorgente
attualmente a schermo e possibilità di forzare manualmente una sorgente invece
di lasciar decidere l'arbitro.

---

## Come viene deciso chi va sul display

Un solo processo può pilotare i GPIO, quindi tutte le sorgenti convivono nello
stesso servizio e un arbitro sceglie chi vince:

| Priorità | Sorgente |
|---|---|
| 100 | ZeDMD |
| 60 | Air Radar |
| 58 | Now Playing |
| 55 | Rolling Banner |
| 50 | Media Player |
| 10 | Clock |

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
/opt/dmd/hass.py          entità di Home Assistant via MQTT Discovery
/etc/dmd/config.json      configurazione
/var/lib/dmd/spotify.json token di Spotify, permessi 0600, fuori dall'export
```

Aggiungere un servizio significa scrivere una nuova sorgente in `sources/`,
registrarla nel `Runtime` e aggiungere una voce alla pagina Servizi.

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

| Versione | Contenuto |
|---|---|
| 1.0 | Ricevitore ZeDMD-WiFi, orologio, web UI |
| 1.1 | Colori di ora e data separati, formato 12/24h, lingua dei giorni, Media Player separato con foto e video, Night mode e Sleep mode, condivisione SMB e upload da web |
| 1.1.1 | `update.sh` installa ffmpeg e samba in modo indipendente |
| 1.2 | Regolazione fine del driver S-PWM dalla web UI, riavvio del servizio dall'interfaccia |
| 1.3 | Air Radar: aerei in transito da coordinate GPS e raggio, via API pubbliche ADS-B |
| 1.3.1 | Nessuna coordinata preimpostata nel software distribuito |
| 1.4 | Air Radar: scelta dei parametri di volo mostrati e registro CSV scaricabile |
| 1.5 | Aggiornamento via rete da GitHub, con verifica preventiva e ripristino automatico |
| 1.5.1 | Corretta la ricerca della rotta: era subordinata a una seconda casella, ora rimossa |
| 1.5.2 | Rotte dal servizio routeset di adsb.lol, in blocco e con codici IATA; prova diagnostica |
| 1.6 | Elenco della libreria media tenuto in memoria invece di rileggere il disco a ogni contenuto |
| 1.7 | Interfaccia web in italiano e inglese, lingua rilevata dal browser, link al progetto |
| 1.7.1 | Un errore della web UI non ferma più il servizio: il pannello resta acceso |
| 1.7.2 | Impronte md5 di tutti i file e verifica automatica prima e dopo la copia |
| 1.8 | Esportazione e importazione della configurazione, con esclusione delle coordinate |
| 1.9 | Rolling banner (dieci testi scorrevoli) e controllo aggiornamenti della libreria matrice |
| 1.9.1 | L'aggiornamento installa i file dichiarati dall'archivio scaricato, non quelli del codice già installato |
| 1.9.2 | Controllo della libreria anche quando la cartella appartiene all'utente e il servizio gira come root |
| 1.9.3 | "Ora e sincronizzazione" spostato nella pagina Orologio |
| 1.9.4 | Durata del bit minimo e bit con dithering: alzano il refresh senza perdere profondità PWM |
| 1.10 | Now Playing: brano in ascolto da AirPlay 2, Spotify o MQTT; entità in Home Assistant |


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
con ricaduta sugli ICAO quando mancano. Se il servizio non risponde si ripiega
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

Dalla cartella del pacchetto scompattato:

```bash
sudo ./setup_nowplaying.sh
```

Chiede il nome della cassa e dove sta il broker, poi fa tutto: Mosquitto,
dipendenze, `nqptp`, `shairport-sync` compilato con AirPlay 2 e metadati,
scheda audio fittizia, file di configurazione, confinamento ai core 0-2 e
sezione MQTT del DMD. Ripetibile: salta i passi già fatti, compresa la
compilazione. `--verifica` controlla lo stato senza toccare niente.

Sta a parte da `install.sh` per la stessa ragione di `setup_share.sh`: è
facoltativo, e la sola compilazione porta via un quarto d'ora.

### Dipendenze

`python3-paho-mqtt`. Se manca, la pagina Musica lo dice e Now Playing resta
spento; il resto del DMD non se ne accorge.

Guida completa, anche per farlo a mano: `docs/now-playing.it.md`.
