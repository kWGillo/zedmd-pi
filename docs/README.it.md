# DMD Controller 1.1.1

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
- **Status Player** e **Air Radar** — presenti nell'interfaccia ma non ancora
  implementati.

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
/etc/dmd/config.json      configurazione
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
