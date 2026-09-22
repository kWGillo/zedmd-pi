---
title: "Gnam Gnam"
subtitle: "Il labirinto, le palline e quattro fantasmi, ognuno con il suo modo di inseguire"
---

# 1. Il nome

Pac-Man è di Bandai Namco: nome, personaggio, labirinto e fantasmi. Il
meccanismo — mangiare le palline di un labirinto scappando da chi ti insegue,
e girare la caccia con una pillola — non è di nessuno. Questo è **Gnam Gnam**,
con un labirinto suo.

# 2. Il labirinto

L'originale è verticale, e schiacciarlo su 64 righe lo renderebbe
illeggibile. Qui c'è un labirinto disegnato per il pannello: **50 caselle per
16**, da quattro pixel l'una, nei 200 pixel di sinistra; a destra il
tabellone, come negli altri giochi.

- Corridoi larghi una casella, e **nessun vicolo cieco**: da ogni punto si
  può sempre scappare in almeno due direzioni.
- Un **tunnel** a metà altezza: esci da un lato e rientri dall'altro. I
  fantasmi lì dentro rallentano, tu no.
- La **casa dei fantasmi** al centro, con la porta rosa.
- **400 palline** e quattro **pillole** negli angoli.

I muri sono disegnati come contorni sottili, non come blocchi pieni: le aree
grandi di colore uniforme, sul pannello, mostrano le righe del refresh.

# 3. I comandi

Le quattro direzioni: croce direzionale, levette, frecce o WASD. Si può
premere la direzione **prima** di arrivare all'incrocio: la curva si fa appena
è possibile. Tornare indietro si può sempre, anche a metà corridoio.
**Fuoco** per cominciare e per rigiocare.

# 4. I fantasmi

Quattro, e ognuno insegue a modo suo:

| Fantasma | Come insegue |
|---|---|
| **Rosso** | punta dritto alla tua casella |
| **Rosa** | punta quattro caselle davanti a te: ti aspetta dove stai andando |
| **Azzurro** | punta al simmetrico del rosso rispetto a un punto davanti a te: da solo sembra girare a caso, insieme al rosso ti chiude in mezzo |
| **Arancio** | ti insegue da lontano, ma a otto caselle ci ripensa e torna nel suo angolo |

Non inseguono sempre. A fasi — sette secondi di tregua, venti di caccia — si
ritirano **ognuno nel suo angolo**, e ogni volta che la fase cambia invertono
la marcia: è il segnale che qualcosa sta cambiando.

Escono dalla casa uno alla volta: il rosso è già fuori, il rosa esce dopo un
secondo, l'azzurro dopo cinque, l'arancio dopo nove.

# 5. Le pillole

Una pillola fa diventare i fantasmi **blu**, lenti e confusi per sei secondi
(un po' meno a ogni livello). Negli ultimi due secondi lampeggiano. Mangiarli
vale **200, 400, 800 e 1600** punti, uno dopo l'altro; di loro restano gli
occhi, che corrono a casa e rinascono.

| Cosa | Punti |
|---|---|
| pallina | 10 |
| pillola | 50 |
| fantasmi, uno dopo l'altro | 200 · 400 · 800 · 1600 |

Tre vite. Finite le palline il labirinto lampeggia, si passa al livello dopo,
e tutto è un po' più veloce.

# 6. La musica

Mentre si gioca suona un **motivo scritto apposta** per Gnam Gnam — non la
musica di Pac-Man, che è protetta. Pentatonica maggiore, allegro, 132 battiti
al minuto: sedici battute, una prima parte e una seconda che sale, poi
ricomincia. Il giro dura mezzo minuto, abbastanza da non sembrare un disco
rotto. La melodia è un'onda quadra stretta, il timbro dei chip sonori delle
console, con un basso a triangolo e un charleston leggero sui controtempi.

- Sta **a un terzo** del volume degli effetti: palline e fantasmi si sentono
  sopra.
- **Tace** nella schermata iniziale, quando ti prendono, mentre il labirinto
  lampeggia a fine livello e a partita finita. Riparte da dov'era quando si
  torna a giocare.
- Segue il cursore **Volume dei giochi**, e la levetta **Effetti dei giochi**:
  spenti gli effetti, niente musica.
- Se la sveglia interrompe la partita, la musica si ferma con lei.

La ricetta — note, tempo, timbri — sta in `diagnostica/genera_suoni.py`:
cambiarla e rigenerare il file è un comando.

# 7. Come è stato provato

Una prova controlla il labirinto — simmetrico, chiuso, ogni pallina
raggiungibile, nessun vicolo cieco — e il carattere di ogni fantasma, casella
per casella. Poi un giocatore automatico semplice, che va verso la pallina più
vicina evitando i fantasmi, gioca partite intere: finisce il primo livello in
quattro partite su sei e poi viene preso. Premendo direzioni a caso si perde
sempre al primo livello.
