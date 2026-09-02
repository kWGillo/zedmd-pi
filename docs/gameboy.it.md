# Game Boy sul DMD

Un emulatore Game Boy che usa il pannello come schermo. Gira come **processo
separato** — l'emulatore è PyBoy — e prende il pannello per il tempo della
partita, esattamente come Doom: o si sta giocando, o di Game Boy non esiste
niente in esecuzione.

---

## 1. Che cosa serve

- **PyBoy**, che si installa dal pulsante nella pagina Game Boy (o a mano con
  `sudo /opt/dmd/gb/setup_gb.sh`).
- **Le ROM**, che sono tue. In questo progetto non ce n'è nessuna e non ce ne
  saranno mai: si copiano nella condivisione di rete che lo script apre.

Lo stesso script crea la cartella `/srv/dmd/rom` e la condivide via SMB come
`dmd-rom`, accanto a quelle dei media e dei WAD di Doom. Dal computer si apre
come `\\<indirizzo-del-pi>\dmd-rom`.

Sono buoni i file `.gb` (Game Boy) e `.gbc` (Game Boy Color).

---

## 2. Come si vede sul pannello

Lo schermo del Game Boy è **160×144**, il pannello **256×64**. La proporzione
si tiene: portato a 64 righe, lo schermo occupa **71 pixel** al centro, e ai
lati il pannello resta spento.

### L'overscan

Settantuno pixel su duecentocinquantasei sono pochi. L'**overscan** toglie
righe sopra e sotto *alla sorgente*: si perde una fascia di cielo e una di
terreno, ma a parità di 64 righe la proporzione cambia e l'immagine sul
pannello diventa più larga.

| Overscan | Larghezza sul pannello | Cosa si perde |
|---|---|---|
| 0% | 71 px | niente |
| 20% | 88 px | 28 righe su 144 |
| 40% | 116 px | 56 righe su 144 |
| 60% | 178 px | 86 righe su 144 |

Il valore giusto dipende dal gioco: in un platform la parte alta è spesso
cielo e si può tagliare, in un gioco di ruolo il testo sta in basso e no.

### Lo spostamento verticale

L'overscan decide **quante** righe si perdono; lo spostamento decide **da che
parte**. Il taglio nasce simmetrico, ma i giochi non lo sono: il punteggio sta
in alto, il campo di gioco in basso.

Un numero **negativo** alza la finestra e mostra la parte alta dello schermo,
uno **positivo** la abbassa. La finestra non esce mai dallo schermo del Game
Boy: oltre il bordo il valore smette semplicemente di avere effetto, perché lì
non c'è altro da vedere. Senza overscan non c'è niente da spostare.

### Il gamma

Stessa convenzione di Doom: **sotto 1 schiarisce, sopra 1 scurisce**. Il
Game Boy originale ha quattro tonalità di verde, e su un pannello LED i due
toni intermedi tendono a confondersi: il gamma è la leva per separarli.

### I fotogrammi al secondo

Il Game Boy ne produce 59,7. Il valore predefinito è **30**, e non è una
rinuncia: il ciclo di rendering del DMD gira a 30, e ogni fotogramma in più
sarebbe traffico di memoria che compete con le letture del pannello — la
stessa contesa che produce le righe chiare. Trenta bastano all'occhio.

---

## 3. I comandi

### Sul pad

| Game Boy | Pad |
|---|---|
| Direzioni | croce direzionale e levetta sinistra |
| A | croce (X), R1, R2 |
| B | cerchio, quadrato, triangolo, L1, L2 |
| Start | **Start**, o L3 (levetta sinistra premuta) |
| Select | **Select**, o R3 (levetta destra premuta) |
| *Uscire* | **PS** |

Start e Select sono pulsanti globali del progetto — scorrono i giochi ed
escono da qualunque partita — ma **mentre il Game Boy gioca il lettore dei
giochi si fa da parte** e li lascia alla console. Devono: su Tetris il numero
di giocatori si sceglie con Start, e senza non si comincia.

Resta **PS** come via d'uscita, che è il significato che quel tasto ha sulla
console vera. Uscendo, il pannello torna al suo lavoro; premendo poi Start si
riprende il giro dei giochi da dove era rimasto.

**Dal pad non si apre mai una partita Game Boy**: si comincia dalla pagina, o
dal giro del tasto Start (vedi sotto).

### Nel giro del tasto Start

Il Game Boy fa parte del giro che il tasto Start scorre, insieme a Breakout,
Invaders e Doom. Ci entra **solo** se PyBoy è installato e la cartuccia scelta
è valida: una casella su cui Start non fa niente sarebbe peggio che non
averla. Si può togliere dal giro nella pagina Giochi.

### Sulla tastiera

Frecce o WASD per muoversi, **X** per A e **Z** per B, **Invio** per Start,
**Maiusc** o **Backspace** per Select, **Esc** per uscire.

Se si vuole, un tasto della tastiera può anche *far cominciare* una partita:
la casella sta nella pagina, ed è spenta di suo.

### Dalla pagina web

Ci sono gli otto pulsanti, utili dal telefono. Tengono conto del premuto e del
rilasciato separatamente, così tenendo il dito il personaggio cammina davvero.

---

## 4. Salvataggi

La memoria tampone della cartuccia (quella con la pila, dove i giochi salvano)
viene scritta accanto alla ROM quando la sessione si chiude. Si vede dalla
condivisione, e si può copiare o cancellare come qualunque file.

---

## 5. Quando la partita finisce

Tre modi: il pulsante *Esci* nella pagina, **PS** sul pad, oppure il tempo — dopo cinque minuti senza comandi la
sessione si chiude da sola e il pannello torna al suo lavoro. Il tempo si
cambia dalla pagina; zero vuol dire mai.

---

## 6. Perché un processo separato

PyBoy è una libreria Python: si potrebbe importare dentro il servizio. Non si
fa, per tre ragioni in ordine di importanza.

1. **Il GIL.** Un emulatore dentro il nostro processo si contenderebbe
   l'interprete con il ciclo che disegna il pannello. Su questo progetto la
   moneta è il microsecondo: è già misurato che basta la contesa sul bus di
   memoria per accendere una riga sbagliata.
2. **Isolamento.** Se l'emulatore cade, cade lui: il pannello torna
   all'orologio e il servizio non se ne accorge.
3. **Licenza.** PyBoy è LGPL-3.0 e con GPLv3 andrebbe d'accordo anche
   collegato — ma due processi che si parlano da una pipe restano due
   programmi distinti, e questo toglie ogni dubbio.

Il protocollo fra i due è volutamente stupido: fotogrammi grezzi di dimensione
fissa su `stdout`, coppie `[stato, tasto]` su `stdin`. È lo stesso di Doom.
