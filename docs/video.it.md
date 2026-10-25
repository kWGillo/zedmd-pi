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

Dalla 17.3 «schermo intero» per **Doom e il Game Boy** vuol dire davvero tutto
lo schermo: disegnano alla misura della tela logica con le loro proporzioni --
Doom 320:200, il Game Boy 160:144 -- invece che in una fascia da pannello. Per
Doom serve ricompilare l'helper una volta sola:

```
sudo /opt/dmd/doom/setup_doom.sh
```

Dalla 17.4 i **giochi** si riproporzionano, uno per volta. Chi ha imparato a
disegnarsi su una tela qualunque prende tutto il campo: il tabellone passa da
colonna di destra a striscia in alto, e il gioco guadagna le 56 colonne e
tutte le righe in piu'. Chi non l'ha ancora imparato resta 256x64 ingrandito
di un intero e centrato, come prima.

Convertiti finora: **Snake** e **Breakout**. Gli altri undici seguono: la loro
geometria e' fatta di costanti di modulo, righe assolute, sprite che sono
maschere di collisione e fisica tarata su 64 righe, e riproporzionarla e' una
riprogettazione, non una moltiplicazione.

| a 1024x768 | righe logiche |
|---|---|
| orologio da solo | 184 |
| orologio con contenuto | 88 |
| contenuto | 96 |

**Su uno schermo molto largo le righe si spartiscono diversamente.** Dalla
17.4.11: su un 21:9 la tela logica è bassa — un 2560×1080 ingrandito dieci
volte dà 108 righe logiche — e la metà farebbe 54, meno delle 64 righe che una
sorgente disegna. Lì il contenuto prende **esattamente la sua tela**, 64 righe,
e l'orologio tutto quello che resta:

| | righe logiche | orologio | contenuto |
|---|---|---|---|
| 1024×768 | 192 | 88 | 96 |
| 1920×1080 | 154 | 69 | 77 |
| 2560×1080 | 108 | 36 | 64 |
| 3440×1440 | 110 | 38 | 64 |

Dove la metà basta resta la metà esatta. E la larghezza non si tocca mai: su un
21:9 il disegno si prende tutti i 2560 pixel.

**E in una regione più bassa del pannello l'orologio si riproporziona tutto**,
dalla 17.4.12. Trentasei righe logiche sono **meno** delle 64 del pannello, e
fino alla 17.4.11 due conti diversi davano per scontato il contrario: le cifre
prendevano il sessanta per cento dell'altezza (a 36 righe, 21 contro le 38 del
pannello) e i testi seguivano la sola larghezza, che su un 21:9 è quella del
pannello — quindi la data restava grande come sul pannello accanto a cifre più
piccole. Adesso i testi seguono il minore fra i due fattori e le cifre prendono
tutto lo spazio sopra la banda degli orari:

| tela dell'orologio | cifre | data | banda orari |
|---|---|---|---|
| 256×36 (2560×1080) | 27 | 7 | 6 |
| 256×64 (pannello) | 38 | 12 | 10 |
| 256×88 (1024×768 con contenuto) | 52 | 12 | 10 |
| 256×184 (1024×768 da solo) | 83 | 12 | 10 |

Sul pannello i due fattori valgono entrambi uno, quindi non si muove un pixel;
e sulle tele più alte, dove la regola della larghezza era quella giusta, non
cambia niente.

# 4. La pagina Video

Dalla 17.3.4 la voce **Video** non compare nel menu su un Raspberry che sta
pilotando il pannello: lì la pagina non ha niente da dire, perché la
risoluzione è 256×64, il filtro DMD su un DMD vero non vuol dire niente e le
due regioni nemmeno. La pagina resta: le Impostazioni mostrano un riquadro
«Uscita video» che porta lì, perché è lì dentro che si sceglie **Monitor** —
su un Pi con uno schermo sulla scrivania è una scelta legittima.

Servono tutte e due le condizioni. Su un PC dove qualcuno ha scritto
`uscita: pannello` a mano la voce resta, perché quel pannello non si accenderà
mai ed è proprio lì che si va a leggere perché.

| Comando | Cosa fa |
|---|---|
| **Uscita** | «Decide la macchina» sceglie il pannello su Pi 3 e 4 e il monitor altrove. Si può forzare: su un Pi con un monitor sulla scrivania, «Monitor» è una scelta legittima |
| **Risoluzione** | vuota vale quella che c'è adesso, ed è quasi sempre la risposta giusta. Dalla 17.3.3 la casella si apre sulle misure che il monitor dichiara, lette da `/sys/class/drm` |
| **Finestra** | «Se c'è un desktop» apre una finestra quando trova una sessione grafica, altrimenti va a tutto schermo |
| **Filtro DMD** | ogni pixel diventa un punto con la sua intercapedine |
| **Punto %** | quanto della cella è acceso: 80 lascia l'intercapedine di un pannello da 3 mm |
| **Bagliore %** | l'alone intorno al punto. A zero il bordo è netto |
| **Fondo** | il colore fra i punti. Nero pieno è corretto per un DMD |
| **Giochi sullo schermo** | ingranditi di un intero, o stirati a tutto schermo |
| **Come disegnare** | a regioni dove ci sta piu' di una tela, o una tela sola al centro |
| **Standby del monitor** | quando il DMD si spegne, il monitor riceve il segnale di spegnimento e va in standby davvero. Solo su monitor: sul pannello «spento» e' la matrice a zero |

Le prime tre valgono dal **riavvio del servizio**: la superficie e la misura
della tela si creano una volta sola, all'avvio. È la stessa ragione per cui la
taratura del pannello riavvia. Il filtro e la scala dei giochi valgono subito.

La pagina dice anche che macchina è, dove sta andando il disegno, quanto è
grande la tela e di quanto viene ingrandita. Se il vetro è nero, è lì che si
guarda: il motivo è scritto in cima.

# 4-bis. Lo standby del monitor

Spento vuol dire fotogramma nero, e un monitor che mostra nero **resta
acceso**: consuma, scalda, e di notte in una stanza buia si vede comunque il
rettangolo grigio del pannello.

Con **Standby del monitor** acceso — il predefinito su un monitor — quando il
DMD si spegne (il pulsante *Spegni*, la fascia notturna) il programma scrive
nel framebuffer il valore `4`, che e' `FB_BLANK_POWERDOWN`:

```
/sys/class/graphics/fb0/blank
```

Il driver lo traduce in DPMS verso il monitor, che va in standby vero: LED
arancione, pannello spento. Al risveglio si riscrive `0` **prima** di
disegnare, perche' un fotogramma mandato a uno schermo addormentato e' un
fotogramma perso.

Due cose da sapere, e sono tutte e due del monitor e non del programma:

* **puo' metterci una decina di secondi a decidersi.** Lo schermo intanto e'
  gia' nero, quindi l'attesa non si vede, ma se guardi il LED aspettando che
  cambi colore lo noti;
* **al risveglio ci mette un secondo o due** a risincronizzarsi. Se la cosa
  da' fastidio — per esempio perche' una notifica deve comparire subito — si
  spegne dalla pagina Video.

Dove il file non c'e' o non si lascia scrivere non succede niente: resta il
fotogramma nero di sempre.

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

Dalla 17.4 si riproporzionano, **uno per volta**.

Un gioco convertito riceve la misura della tela e si ridisegna addosso: il
tabellone passa da colonna di destra a striscia di sette righe in alto, e il
campo si riprende le 56 colonne e tutte le righe in più. Sul pannello resta
identico al pixel — il 4:1 impone la colonna a destra, ed è il ragionamento
che quella colonna l'ha inventata.

Convertiti finora: **Snake** (da 49×15 a 50×36 caselle), **Breakout**,
**Pongo**, **T-Rex**, **Mine vaganti**, **Kingo Bongo** e **Invasori**
(che su una tela alta ritrova le cinque file del cabinato) e
**Squadriglia**.

Un gioco che scorre di lato — T-Rex, e domani Squadriglia — ha un problema
in più: lo schermo è più alto ma non più largo, quindi ingrandire le figure
vuol dire vederle arrivare per meno tempo. Lì si ingrandisce di un fattore
intero (due, non di più) e il mondo resta quello: cambia solo quanta parte
se ne vede.

**Sono tutti e tredici**, dalla 17.4.9. Ciascuno a modo suo, perché la forma
del gioco decide la strada:

| | |
|---|---|
| campo chiuso (Snake, Breakout, Pongo, Invasori) | due fattori, uno per asse, applicati alle misure del gioco |
| scorre di lato (T-Rex, Squadriglia) | il mondo resta in unità e si guarda con uno zoom intero: le figure raddoppiano, e si vede metà mondo per volta |
| vettoriale (Mine vaganti) | uno zoom solo, isotropo: due fattori diversi farebbero di una mina un'ellisse che cambia misura mentre gira |
| schermo fisso (Kingo Bongo) | i palazzi si allungano verso il basso: in una parabola conta il dislivello fra i tetti, e quello non cambia |
| solo parole (Super Quiz) | il testo si scrive al doppio e le risposte tornano in colonna sola |
| arte disegnata a mano (Gnam) | cresce di un quarto e si centra: più in là serve un labirinto nuovo |

Sul pannello nessuno di loro è cambiato di un pixel, ed è la regola che ha reso
sicura una conversione fatta un gioco per volta.

«Stirati a tutto schermo» resta per chi preferisce comunque lo schermo pieno
alla nitidezza, e per i giochi non ancora convertiti.

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

**Il caso più insidioso è SDL che dice di disegnare e non disegna.** Sul KMS
SDL non solleva niente: se non riesce a prendere la CRTC lo scrive e tira
dritto, e il giornale si riempie di

```
ERROR: Could not set videomode on CRTC.
ERROR: Could not queue pageflip: -22
```

venti volte al secondo. Capita sulle macchine virtuali, dove la scheda video è
emulata. Dalla 17.3.2 il programma se ne accorge da solo: la superficie SDL si
rifiuta, si ripiega su `/dev/fb0` — che su quelle stesse macchine funziona — e
lo dice, all'avvio e in cima alla pagina Video:

```
[display] si ripiega su SuperficieFramebuffer -- SuperficieSDL: SDL non disegna sul KMS -- ERROR: Could not set videomode on CRTC.
```

Si perde il vsync, non il disegno.

Sul framebuffer il terminale resta vivo sotto al fotogramma, e fino alla
17.3.4 si vedevano il suo cursore e — premendo un tasto durante una partita —
i caratteri stampati in alto. Dalla 17.3.5 il terminale si mette in modalità
grafica, che è quello che SDL fa da sé sul KMS: il kernel smette di disegnarci
sopra, e torna in modalità testo quando il servizio si ferma.

Per vedere con i propri occhi quale strada funziona, con il servizio fermo:

```
sudo systemctl stop dmd
sudo python3 /opt/dmd/diagnostica/schermo_dal_vivo.py
```

Dipinge tre schermate piene — rossa dal framebuffer, verde da SDL, blu da SDL
con la console staccata prima — cinque secondi ciascuna. Se una compare, quella
strada disegna.

Gli altri motivi che si leggono più spesso: `No module named 'pygame'` con
`/dev/fb0` assente (manca l'uscita video: `apt install python3-pygame`), o,
dove il pannello è stato chiesto a mano su una macchina che non ce l'ha,
`No module named 'rgbmatrix'`.
