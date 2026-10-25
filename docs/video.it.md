# Uscita video: il pannello, o un monitor

Dalla 17.0 il programma gira anche su un PC con un monitor collegato, invece
che su un Raspberry con il pannello LED. Questo documento spiega come sceglie,
che cosa cambia, e che cosa su un PC non c'è.

# 1. Che macchina è

La domanda si fa una volta sola, all'avvio, leggendo quello che la macchina
dice di sé: `/proc/device-tree/model`, con `/proc/cpuinfo` di riserva sui
kernel dove il device tree non è montato.

Non si guarda l'architettura. Un Pi 4 a 64 bit e un PC ARM rispondono la
stessa cosa a `uname -m`, e la domanda vera non è «che processore è» ma «c'è
un pannello LED che posso pilotare».

| Macchina | Pannello | Perché |
|---|---|---|
| Raspberry Pi 3, Pi 4, Compute Module 4 | sì | la libreria pilota il PWM del BCM, e lì c'è |
| Raspberry Pi 5 | no | il controller GPIO è l'RP1, e la libreria non lo supporta |
| Pi Zero, Pi 2, Pi 400 | no | funzionerebbero, ma con questo programma non li ha mai provati nessuno |
| PC, macchina virtuale, container | no | il modulo `rgbmatrix` non c'è nemmeno |

Dove il pannello non si offre, il disegno va sul monitor. Si può vedere a
schermo con:

```
python3 /opt/dmd/piattaforma.py
```

# 2. La tela e l'uscita sono due cose

È il cardine di tutta la 17.0, e vale la pena capirlo prima di toccare le
impostazioni.

La **tela** è la misura su cui disegnano le sorgenti: 256×64, come il
pannello. L'**uscita** è dove quel disegno finisce. Sul pannello coincidono.
Su un monitor no: la tela viene ingrandita per riempire lo schermo.

Non è una complicazione gratuita. La misura della tela viene passata a una
trentina di sorgenti all'avvio e congelata lì dentro, ed è **anche** il
protocollo ZeDMD: larghezza e altezza stanno nell'handshake, e Batocera le
usa per decidere che fotogrammi trasmettere. Farla diventare la risoluzione
del monitor romperebbe tre cose insieme.

Nella 17.0, su un monitor, si vedeva un DMD grande con due bande nere. Dalla
17.1 quelle bande sono fasce, e ci stanno dentro altre sorgenti (sezione 3).
Le informazioni riproporzionate al rapporto dello schermo — 4:3, 16:9, 16:10,
21:9 — restano un lavoro a parte.

# 3. Le due regioni

Dalla 17.2 la tela ingrandita non lascia piu' due bande nere: lo schermo si
divide in **due regioni**.

**Da solo l'orologio prende tutto.** A 1024x768 con scala 4 disegna su 256x192
pixel logici -- tre volte le righe del pannello -- e le cifre crescono con lui,
da corpo 38 a corpo 83. La data resta piccola in alto a destra, gli orari del
mondo e il valore dell'energia restano in fondo.

**L'orologio prende tutto solo se non puo' arrivare nient'altro**, cioe' se
tutti i servizi sono spenti o fuori dalla loro fascia oraria. Non basta che in
questo momento non ci sia niente da mostrare: altrimenti passerebbe un aereo e
l'orologio si rimpicciolirebbe, poi tornerebbe grande, dieci volte all'ora.

Attenzione: con la configurazione di serie **cinque servizi sono gia' accesi**
-- sveglia, zedmd, moon, inutili, scadenze -- perche' sono quelli che non
mostrano niente finche' non li configuri. La pagina Video li elenca sotto
«Tengono l'orologio a meta'»: spegni quelli che non usi dalla pagina Servizi.

**Quando un servizio e' acceso**, l'orologio sta nella meta' di sopra e la
meta' di sotto ospita una sorgente per volta:
il Media Player, un aereo, il meteo. La sceglie la priorita', come ha sempre
fatto l'arbitro -- finche' un aereo sta passando resta l'aereo.

Le sorgenti non si toccano: disegnano su 256x64 perche' quelle misure sono le
loro, e dentro la regione si centrano senza stirarsi.

**Perche' la tela logica e non la risoluzione.** Il filtro DMD funziona perche'
ogni pixel della tela diventa una cella di celle intere. Disegnando l'orologio
alla risoluzione vera le cifre diventerebbero lisce e i punti sparirebbero da
meta' schermo. Crescendo la tela logica i pixel ci sono ancora, sono solo di
piu'.

**Restano a schermo intero** Doom, il Game Boy, i giochi, l'anteprima della
gestione media e le notifiche di livello allarme. Le prime quattro perche'
sono interattive; l'allarme perche' e' il livello che non si puo' non vedere.

| a 1024x768 | righe logiche |
|---|---|
| orologio da solo | 184 |
| orologio con contenuto | 88 |
| contenuto | 96 |

# 4. La pagina Video

| Comando | Cosa fa |
|---|---|
| **Uscita** | «Decide la macchina» sceglie il pannello su Pi 3 e 4 e il monitor altrove. Si può forzare: su un Pi con un monitor sulla scrivania, «Monitor» è una scelta legittima |
| **Risoluzione** | vuota vale quella che c'è adesso, ed è quasi sempre la risposta giusta |
| **Finestra** | «Se c'è un desktop» apre una finestra quando trova una sessione grafica, altrimenti va a tutto schermo |
| **Filtro DMD** | ogni pixel diventa un punto con la sua intercapedine |
| **Punto %** | quanto della cella è acceso: 80 lascia l'intercapedine di un pannello da 3 mm |
| **Bagliore %** | l'alone intorno al punto. A zero il bordo è netto |
| **Fondo** | il colore fra i punti. Nero pieno è corretto per un DMD |
| **Giochi sullo schermo** | ingranditi di un intero, o stirati a tutto schermo |
| **Come disegnare** | a regioni dove ci sta piu' di una tela, o una tela sola al centro |

Le prime tre valgono dal **riavvio del servizio**: la superficie e la misura
della tela si creano una volta sola, all'avvio. È la stessa ragione per cui la
taratura del pannello riavvia. Il filtro e la scala dei giochi valgono subito.

La pagina dice anche che macchina è, dove sta andando il disegno, quanto è
grande la tela e di quanto viene ingrandita. Se il vetro è nero, è lì che si
guarda: il motivo è scritto in cima.

# 5. Il filtro DMD

Due cose fatte di proposito.

**Il bagliore sta nella maschera, non in una sfocatura.** La via ovvia sarebbe
sfocare il fotogramma ingrandito e sommarlo: su 1792×448 sono una ventina di
millisecondi, e un gioco a trenta fotogrammi al secondo li paga tutti. Invece
il punto si disegna una volta sola con il suo alone — centro pieno, bordo che
sfuma — e per fotogramma resta una moltiplicazione. Misurato: 8,2 ms a
1920×1080. E un punto di un pannello vero è fatto così davvero: un LED dietro
un diffusore, non un quadrato.

**Il moltiplicatore è intero.** Su 1920×1080 la tela ci sta sette volte
(1920/256 fa sette e mezzo, comanda il lato più stretto): 1792×448, con 64
colonne di banda ai lati e 316 righe sopra e sotto. Con un moltiplicatore non
intero i punti cadrebbero a cavallo dei pixel e il reticolo si vedrebbe
ondeggiare.

**La luminosità su un monitor è una moltiplicazione.** Sul pannello è un
registro della matrice. Su HDMI non esiste niente del genere, e senza
moltiplicare lo slider e la modalità notte fingerebbero di funzionare.

# 6. I giochi

Restano 256×64 e si ingrandiscono di un intero, centrati, con il nero intorno.
Le aree non usate sono una scelta, non una mancanza.

Il motivo sta nei giochi stessi: il campo prende i 200 pixel di sinistra e i
56 di destra sono il tabellone, la fisica di bongo è in pixel al secondo
quadrato, il labirinto di gnam è arte disegnata a mano su celle da quattro
pixel. Portarli a proporzioni qualsiasi non sarebbe una moltiplicazione:
sarebbe riprogettare tredici giochi — e per gnam vorrebbe dire un labirinto
nuovo, disegnato da una persona.

«Stirati a tutto schermo» esiste per chi preferisce comunque lo schermo pieno
alla nitidezza.

# 7. L'audio su un PC

Sul Raspberry le uscite HDMI e bcm2835 si scartano di proposito: non c'è
nessun cavo HDMI — il pannello è attaccato al bonnet, non a un monitor — e il
jack usa lo stesso blocco PWM della libreria matrice.

Su un PC sono quello che c'è. L'elenco diventa quindi due elenchi, e su PC si
rimanda in seconda fila il solo HDMI, che suona soltanto se il monitor ha gli
altoparlanti. Senza chiavette USB attaccate, il DMD parla dal codec integrato.

Su un desktop con PipeWire o PulseAudio c'è un problema in più: il server
audio tiene la scheda, e `plughw:` risponde «device busy». La strada è passare
dal mixer di sistema, scrivendo come dispositivo `default` o `pulse` nella
pagina Impostazioni. Non compaiono nell'elenco delle schede perché non sono
schede, ma si accettano scritti a mano.

# 8. Avvio automatico

Il servizio è lo stesso di sempre, `dmd.service`, e parte da solo
all'accensione. Gira come root — serve per `/dev/input`, per la porta 80
dell'handshake ZeDMD e, sul Raspberry, per i GPIO.

Il disegno esce da SDL: una finestra se c'è una sessione grafica, il KMS se
non c'è. Dal servizio, che gira come root e non appartiene alla sessione
dell'utente, si va a tutto schermo sul KMS: è il caso dell'apparecchio, che è
quello che si vuole. La modalità finestra serve a chi lancia `dmdd.py` a mano
per provare.

Se SDL non è installato si ripiega su `/dev/fb0`, che non ha bisogno di niente
ma nemmeno di una finestra.

# 9. Cosa su un PC non c'è

| | |
|---|---|
| **ZeDMD** | c'è. Resta 256×64 — la codifica a zone è 16×8, che quella misura la implica — e viene ingrandito all'uscita |
| Pulsante GPIO | solo Raspberry |
| Taratura del pannello, libreria matrice | non hanno senso, e le pagine non compaiono |
| Luminosità, modalità notte | emulate in software |
| Joystick, tastiera, webcam, MQTT, Home Assistant, AirPlay, Samba, servizi internet | funzionano |

# 10. Se il vetro resta nero

Il programma non muore più quando l'uscita non si accende: continua, stampa il
motivo nel giornale di bordo e lo scrive in cima alla pagina Video. Il radar
registra, le notifiche arrivano, la pagina risponde — è solo il vetro a non
esserci.

```
journalctl -u dmd -f
```

I motivi che si leggono più spesso: `No module named 'pygame'` con
`/dev/fb0` assente (manca l'uscita video: `apt install python3-pygame`), o,
dove il pannello è stato chiesto a mano su una macchina che non ce l'ha,
`No module named 'rgbmatrix'`.
