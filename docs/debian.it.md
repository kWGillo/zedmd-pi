# Installazione su Debian 13 «trixie» — senza pannello, con un monitor

Dalla 17.0 il programma gira anche su un PC con un monitor collegato, invece
che su un Raspberry con il pannello LED. Questo documento è la procedura
completa, dalla chiavetta al servizio avviato, con dentro le cose che si
scoprono solo provandole.

Vale per qualunque PC a 64 bit. I riferimenti a un mini PC con Atom
x5-Z8350 — la scatoletta tipo Z83 — sono lì perché è la macchina su cui è
stato provato, e perché su quella classe di hardware ci sono tre o quattro
trappole che altrove non esistono.

# 1. Perché Debian e non Ubuntu Desktop

Il vincolo vero del progetto sono **apt e systemd**: `install.sh` installa
pacchetti Debian, `dmd.service` è un'unità systemd, l'aggiornamento OTA fa
`systemctl restart dmd`. Tutto quello che toglie uno dei due — Alpine, Void,
Ubuntu Core — non è «più leggero», è «da riscrivere».

Ubuntu Server va benissimo. Debian netinst è un filo più piccola: niente
snapd, niente cloud-init, e `unattended-upgrades` non acceso di suo, che su
una eMMC è scrittura in meno.

**Ubuntu Desktop no**, e i numeri lo dicono da soli: Canonical chiede 6 GB di
RAM come minimo per Desktop e 1,5 GB per Server. Su una scatoletta da 2 GB il
desktop gira a meno di un terzo del suo minimo dichiarato: swappa sulla eMMC e
da lì in poi è tutto lento. Non è il processore, è la memoria che finisce.

# 2. L'immagine e l'installazione

`debian-13.x.0-amd64-netinst.iso`, circa 700 MB.

Da Debian 12 in poi il **firmware non libero sta dentro l'installatore
ufficiale**: il wifi Broadcom delle scatolette (AP6255, AP6212) viene
riconosciuto durante l'installazione invece che dopo, a mano, copiando file in
`/lib/firmware/brcm/`. È il pomeriggio che si rischiava di perdere.

**La trappola di Debian, l'unica vera.** Quando l'installatore chiede la
password di root, **lasciala vuota**: così il tuo utente finisce nel gruppo
`sudo`. Se la imposti, ti ritrovi senza `sudo` su una macchina che gestirai
via SSH. Se succede, si rimedia entrando come root:

```
usermod -aG sudo gillo
```

**A tasksel**, la schermata con le spunte: togli tutto tranne **standard
system utilities** e **SSH server**. Niente desktop, niente print server.

Disco intero sulla eMMC, senza LVM: su 32 GB non serve a niente e aggiunge uno
strato.

# 3. Le quattro cose da controllare prima di andare avanti

Su un PC qualunque si saltano. Su una scatoletta Atom valgono il minuto che
costano.

**La larghezza dell'UEFI.** Alcune macchine Atom hanno firmware UEFI a 32 bit
su CPU a 64 bit, e l'installatore amd64 non si avvia. Da un live:

```
cat /sys/firmware/efi/fw_platform_size
```

`64` e sei a posto; `32` e serve un `bootia32.efi` sulla chiavetta. Le
scatolette che montavano Windows 10 a 64 bit sono a 64 bit per forza.

**L'audio.** Il codec Cherry Trail (`bytcr-rt5640`, `bytcht-es8316`) su Linux è
capriccioso: ci sono bug aperti da anni su HDMI che non suona e sul jack che
funziona solo se la spina è inserita all'avvio. Provalo **prima** di installare
il DMD, così se non va sai che non è colpa sua:

```
aplay -l && speaker-test -c2 -t sine -l1
```

Se non esce suono, il piano B è una chiavetta USB audio da pochi euro: il DMD
la preferisce da sé alla scheda integrata, esattamente come fa sul Raspberry.

**Il dispositivo grafico.** Serve un DRM su cui disegnare:

```
ls /dev/dri/
```

`card0` e `renderD128` e il DMD ha dove disegnare. Se la cartella non c'è, il
programma parte lo stesso ma lo schermo resta nero, e il motivo lo scrivi
nella pagina Video.

**La memoria e la eMMC.** Su 2 GB:

```
sudo apt install zram-tools
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-dmd.conf
sudo mkdir -p /etc/systemd/journald.conf.d
printf '[Journal]\nSystemMaxUse=100M\n' | sudo tee /etc/systemd/journald.conf.d/dmd.conf
```

Il tetto al giornale di sistema non è pignoleria: il DMD scrive parecchio e la
eMMC si consuma a scritture.

# 4. L'installazione del DMD

Il programma si scarica **da GitHub, sulla macchina stessa**. Non serve
copiarci niente da un altro computer: il repository è pubblico, quindi non
servono né account né chiavi.

<https://github.com/kWGillo/zedmd-pi>

## Con git, ed è la strada consigliata

```
sudo apt install -y git
git clone https://github.com/kWGillo/zedmd-pi.git
cd zedmd-pi
```

È la strada consigliata per un motivo pratico: la cartella resta collegata al
repository, quindi per aggiornarla bastano due righe (sezione 10), e se un
giorno vuoi tornare a una versione precedente ce l'hai già tutta.

Il ramo `main` è sempre l'ultima versione pubblicata. Se preferisci fermarti a
una versione precisa, le versioni sono etichette:

```
git tag -l 'v*' | sort -V | tail -5
git checkout v17.4.2
```

## Senza git

Se non vuoi installare git, l'archivio del ramo si scarica con `curl`, che su
Debian c'è già:

```
curl -fsSL https://github.com/kWGillo/zedmd-pi/archive/refs/heads/main.tar.gz -o zedmd-pi.tar.gz
tar xzf zedmd-pi.tar.gz
cd zedmd-pi-main
```

La cartella si chiama `zedmd-pi-main` e non `zedmd-pi`: è GitHub che la nomina
così, con il nome del ramo attaccato. Dentro è identica.

## Poi, in tutti e due i casi

```
bash verify.sh
```

`verify.sh` deve dire **0 alterati, 0 mancanti**. Se dice altro, lo scaricamento
si è rovinato: rifallo, non installare.

Prima di installare, chiedi alla macchina chi è:

```
python3 piattaforma.py
```

Ti aspetti `famiglia: pc` e `pannello: no`. È la stessa risposta che userà
`install.sh` per decidere cosa fare, quindi se qui dice qualcosa di strano,
fermati.

```
sudo ./install.sh
```

Su un PC lo script **non** pretende la cartella della libreria matrice e
**non** compila i suoi binding — sul Raspberry sono obbligatori, qui
fallirebbero, perché quella libreria pilota il blocco PWM del BCM. Installa
invece SDL, scrive `video.uscita = schermo` e accende l'audio sulla scheda
integrata. Alla fine stampa *«Il disegno uscirà sul monitor collegato»*: se
invece ti parla di `slowdown` e di pannelli in cascata, il punto precedente ha
risposto male.

# 5. Il primo avvio

```
sudo systemctl start dmd
sudo journalctl -u dmd -f
```

Le righe che cerchi:

```
[display] macchina: ... (pc), pannello non disponibile
[display] schermo 1024x768, tela 256x64, scala 4, filtro acceso
[display] console: cursor_blink, consoleblank
```

Se invece leggi *«ATTENZIONE: uscita video non disponibile»*, il motivo è sulla
riga dopo — quasi sempre `No module named 'pygame'`, e si risolve con
`sudo apt install python3-pygame`. Il programma in quel caso **non muore**:
continua, e il motivo si legge anche nella pagina Video.

Se `journalctl` non ti mostra niente è perché il tuo utente non vede il
giornale di sistema. Una volta sola:

```
sudo usermod -aG adm gillo
```

# 6. La pagina web

`http://INDIRIZZO:8080/`, dal Mac o da qualunque cosa abbia un browser.

## Chiamarla per nome invece che per indirizzo

Su Raspberry Pi OS `nomemacchina.local` funziona da sempre, e non perché il
Raspberry abbia qualcosa di magico: ha **avahi** installato di serie. Una
Debian minimale no, e quindi `virtuadmd.local` non risponde finché non lo
installi.

Dalla 17.4.6 lo fa `install.sh`. A mano sono due pacchetti:

```
sudo apt install -y avahi-daemon libnss-mdns
```

Fanno due cose diverse, e vale la pena saperlo:

| | |
|---|---|
| `avahi-daemon` | **questa** macchina risponde al suo nome: è quello che ti serve per scrivere `virtuadmd.local` dal Mac |
| `libnss-mdns` | **questa** macchina sa chiamare le altre per nome: serve a lei, per raggiungere il broker MQTT o la cassa AirPlay senza IP |

Il nome è quello di sistema: `hostnamectl` lo dice, `sudo hostnamectl
set-hostname virtuadmd` lo cambia. Se in casa ci fossero due macchine con lo
stesso nome, avahi rinomina la seconda in `virtuadmd-2.local` da solo — e se
un giorno `.local` smette di rispondere senza motivo, è il primo sospetto.

Dal Mac si controlla così:

```
ping virtuadmd.local
```

La prima da aprire è **Video**: dice che macchina è, dove sta andando il
disegno, quanto è grande la tela logica e in quante regioni è divisa. Se lo
schermo è nero, il motivo è scritto lì in cima.

Non troverai la taratura del pannello né la libreria matrice: su un PC non
compaiono, perché parlerebbero di registri S-PWM e di profili di un chip che
non c'è.

# 7. Due cose che sorprendono, e non sono difetti

**L'orologio grande non si vede.** L'orologio prende tutto lo schermo solo
quando **nessun servizio è acceso e dentro la sua fascia oraria** — altrimenti
resterebbe a metà schermo in attesa, e si rimpicciolirebbe e ringrandirebbe a
ogni aereo che passa.

Con la configurazione di serie **cinque servizi sono già accesi**: sveglia,
zedmd, moon, inutili, scadenze. Nascono accesi perché non mostrano niente
finché non li configuri, ma bastano a tenere l'orologio a metà. La pagina Video
li elenca sotto *«Tengono l'orologio a metà»*: spegni dalla pagina Servizi
quelli che non usi.

**Il lampo del login all'avvio.** Per un istante compare il prompt di Debian,
poi torna l'orologio. È `getty` che scrive sul terminale virtuale sotto di
noi. Il cursore che restava a lampeggiare è corretto dalla 17.1.1. La manopola è
`video.console` e ha tre valori:

| | |
|---|---|
| `zitta` | predefinito: mette il terminale in modalità grafica — niente cursore, niente eco dei tasti, niente prompt di login — e spegne il risparmio schermo della console |
| `staccata` | stacca `fbcon` del tutto: sparisce anche il lampo del login, ma se il servizio muore lo schermo resta nero |
| `lascia` | non tocca niente: la via d'uscita se su questa macchina `fbcon` litiga con SDL |

**Se lo schermo è nero e il giornale è pieno di `Could not queue pageflip:
-22`**, è esattamente quel litigio: SDL ha impostato il modo video e `fbcon`
se l'è ripreso, quindi ogni fotogramma viene rifiutato. Dalla 17.3.1 la
console si mette a tacere *prima* di prendere la scheda, che è l'ordine
giusto; se su questa macchina non bastasse, `lascia` o `staccata`.

**Il cursore e i caratteri che compaiono premendo i tasti.** Sul framebuffer
— cioè dove si finisce quando SDL non riesce a prendere la scheda — il
terminale resta vivo sotto il disegno: il cursore lampeggia, e quello che
scrivi sulla tastiera durante una partita viene stampato in alto. Dalla
17.3.5 il terminale si mette in modalità grafica, che è quello che SDL fa da
sé sul KMS, e il kernel smette di disegnarci sopra. Il servizio lo rimette in
modalità testo quando si ferma.

Se il processo venisse ucciso in malo modo (`kill -9`), il terminale potrebbe
restare grafico, cioè nero e muto. Si rimette a posto così, da SSH o da un
altro terminale:

```
sudo python3 -c "import sys; sys.path.insert(0,'/opt/dmd'); import display; display._grafico_nostro = True; display.rianima_console()"
```

I tasti premuti nel frattempo restano nella coda del terminale: tornando in
modalità testo si vedono comparire sulla riga del `login:`. È l'eco che
riemerge, non un guasto.

# 8. L'audio su un PC

Sul Raspberry le uscite HDMI e `bcm2835` si scartano di proposito: non c'è
nessun cavo HDMI — il pannello è attaccato al bonnet — e il jack usa lo stesso
blocco PWM della libreria matrice.

Su un PC sono quello che c'è. Lo scarto quindi diventa un altro: si rimanda in
seconda fila il solo HDMI, che suona soltanto se il monitor ha gli
altoparlanti. Senza chiavette USB attaccate, il DMD parla dal codec integrato.

Su un **desktop** con PipeWire o PulseAudio c'è un problema in più: il server
audio tiene la scheda e `plughw:` risponde «device busy». La strada è passare
dal mixer di sistema, scrivendo come dispositivo `default` o `pulse` nella
pagina Impostazioni. Non compaiono nell'elenco delle schede perché non sono
schede, ma si accettano scritti a mano. Su una installazione senza desktop il
problema non esiste.

# 9. Quanto è veloce questa macchina

Il compositore — quello che ingrandisce la tela e ci mette i punti del DMD — si
misura senza installare niente, dalla cartella scompattata:

```
cd ~/zedmd-pi && python3 -c "
import time, display
from PIL import Image
im = Image.new('RGB',(256,64),(180,90,20))
for misura in ((1280,720), (1920,1080)):
    c = display.Compositore((256,64), misura, {'filtro_dmd': True})
    c.componi(im)
    t = time.time()
    for _ in range(60): c.componi(im)
    print(misura, 'scala x%d' % c.scala, '%.1f ms' % ((time.time()-t)/60*1000))
"
```

Non serve nemmeno la configurazione: il compositore non parla con nessun
dispositivo, ed è il motivo per cui è scritto staccato dal resto.

Il budget è 33 ms per fotogramma, che sono trenta al secondo. Sotto i 15 ms a
1080p stai largo; sopra i 25, metti **1280×720** nella pagina Video — l'area da
comporre quasi si dimezza e su un DMD ingrandito di cinque volte invece che di
sette non vedi la differenza.

Questo lavoro è legato alla **banda di memoria**, non al processore: `resize` e
la moltiplicazione della maschera leggono e scrivono megabyte, non fanno conti.
È il motivo per cui un Atom con LPDDR3 a canale singolo se la cava meglio di
quanto il suo nome faccia pensare.

# 10. Aggiornare

Tre strade, e la prima è quella che userai quasi sempre.

**Dalla pagina web.** Impostazioni → *Aggiornamenti* controlla questo stesso
repository, scarica, verifica l'archivio e riavvia il servizio da solo; se il
servizio non riparte, rimette la versione di prima. Non serve SSH e non serve
ricordarsi niente.

**Con git**, se hai installato così:

```
cd ~/zedmd-pi
git pull
sudo ./update.sh
```

`update.sh` copia i file in `/opt/dmd` e riavvia il servizio. Non tocca
`/etc/dmd/config.json`: le tue impostazioni restano.

**Senza git**, riscarichi l'archivio del ramo come nella sezione 4 e lanci
`sudo ./update.sh` dalla cartella nuova.

In tutti e tre i casi, prima di installare conviene guardare che cosa cambia:
il `CHANGELOG.md` nella cartella è lo stesso che sta su GitHub.

# 11. Cosa su un PC non c'è

| | |
|---|---|
| **ZeDMD** | c'è. Resta 256×64 — la codifica a zone è 16×8, che quella misura la implica — e viene ingrandito all'uscita |
| Pulsante GPIO | solo Raspberry |
| Taratura del pannello, libreria matrice | non hanno senso, e le pagine non compaiono |
| Luminosità, modalità notte | emulate in software, moltiplicando il fotogramma |
| Joystick, tastiera, webcam, MQTT, Home Assistant, AirPlay, Samba, servizi internet | funzionano |

# 12. Se qualcosa non torna

```
sudo journalctl -u dmd -f
bash /opt/dmd/verify.sh /opt/dmd
python3 /opt/dmd/piattaforma.py
```

Le prove del progetto stanno in `/opt/dmd/diagnostica/` e si lanciano a mano:
quelle dello schermo e delle regioni non hanno bisogno di un monitor, perché
provano i conti e non il dispositivo.

```
python3 /opt/dmd/diagnostica/prova_schermo.py
python3 /opt/dmd/diagnostica/prova_regioni.py
python3 /opt/dmd/diagnostica/prova_piattaforma.py
```

## Il font dell'orologio

Da Debian 13 le facce monospaziate di DejaVu non stanno più in
`fonts-dejavu-core` ma in `fonts-dejavu-mono`, e l'orologio è disegnato sulle
larghezze di `DejaVuSansMono-Bold`. Non serve ricordarselo: `install.sh` prova
il pacchetto e, se non basta, installa da sé la copia che viaggia nel progetto
(`font/`) in `/usr/local/share/fonts/dmd/`. Per vedere quale sta usando:

```
ls /usr/share/fonts/truetype/dejavu/ /usr/local/share/fonts/dmd/ 2>/dev/null
```

Con un font proporzionale il programma funziona lo stesso — dalla 17.3.3 le
cifre non si spostano più — ma l'ora centrata respira in modo diverso a ogni
minuto, perché le cifre non hanno tutte la stessa larghezza.

Quella che il monitor **lo vuole** è `schermo_dal_vivo.py`: dipinge sullo
schermo vero, una strada per volta, e dice quale disegna. Si lancia con il
servizio fermo, perché due programmi non possono tenere la stessa scheda:

```
sudo systemctl stop dmd
sudo python3 /opt/dmd/diagnostica/schermo_dal_vivo.py
sudo systemctl start dmd
```

Serve quando il servizio risulta `active (running)` e sullo schermo non c'è
niente — o c'è ancora il `login:` della console, che è lo stesso guasto
vestito da «non parte in automatico». Sulle macchine virtuali il colpevole è
quasi sempre SDL, che non riesce a prendere la scheda; dalla 17.3.2 il
programma ripiega da solo su `/dev/fb0`, e la pagina Video dice che l'ha
fatto.

Per il resto, la pagina **Video** è il primo posto dove guardare: è fatta
apposta per rispondere alla domanda «perché il vetro è nero».
