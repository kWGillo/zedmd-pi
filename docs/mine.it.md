---
title: "Mine vaganti"
subtitle: "Il gioco vettoriale: la posamine, le quattro specie di mine, il salto"
---

# 1. Il nome

Il gioco che il Vectrex aveva di serie, dentro la console, ha un nome suo e
resta suo. Lo schema — una posamine che semina un campo, mine che si
schiudono e si dividono, una nave che ruota, spinge e spara — non è di
nessuno. Questo è **Mine vaganti**, con grafica, regole e musica scritte per
il pannello.

# 2. Lo stile vettoriale

Il Vectrex non aveva pixel: un fascio di elettroni tracciava **linee luminose
su nero**, e il fosforo sbavava un poco attorno a ognuna. Qui ogni cosa è
fatta di segmenti sottili, con un bagliore tenue sotto: la nave, le mine, la
posamine, i colpi, le esplosioni.

Sul pannello è anche la scelta giusta per un motivo tecnico: niente aree
piene di colore, quindi niente righe di refresh (è la lezione di Squadriglia).

Il campo è tutto il pannello sotto una riga di tabellone, e **i bordi si
riattaccano**: quello che esce a destra rientra da sinistra, quello che esce
in basso rientra dall'alto. Anche le mine e i colpi.

# 3. I comandi

| Comando | Pad | Tastiera |
|---|---|---|
| ruotare | sinistra / destra (croce o levetta) | frecce, A D |
| spingere | su | freccia su, W |
| sparare | **X** (tenendo premuto spara a raffica) | spazio, Ctrl |
| **salto** | **cerchio** | **Alt** |

La nave ha inerzia: spingendo accelera nella direzione della punta, e
lasciata rallenta da sola. Fuoco serve anche a cominciare e a rigiocare. Al
massimo quattro colpi in volo.

**Il salto** fa sparire la nave per un attimo e la fa ricomparire in un altro
punto del campo. Dove non si sa: il gioco pesca due punti a caso e sceglie il
meno affollato, un aiuto e non una garanzia. Poi bisogna aspettare due
secondi e mezzo prima di poterlo rifare. Mentre la nave non c'è, niente la
può toccare.

# 4. Come va una partita

1. Passa la **posamine** da sinistra a destra e lascia i **semi**: i puntini
   fiochi sparsi nel campo, ventuno per livello.
2. Tre semi si schiudono in **mine grandi**. Una mina che si sta schiudendo
   cresce e si accende piano: in quel momento non fa male e i colpi le
   passano attraverso.
3. Ogni mina abbattuta fa schiudere **due mine più piccole** da altri due
   semi: grande, media, piccola. La piccola sparisce e basta.
4. Se il campo resta senza mine ma ci sono ancora semi, se ne schiudono altre
   tre grandi.
5. Finiti semi, mine e palle di fuoco: **livello nuovo**, 1000 punti, e la
   posamine ripassa. A ogni livello le mine vanno un po' più veloci.

Nessuna mina si schiude a meno di venti pixel dalla nave.

# 5. Le quattro specie

Una specie nuova per livello, fino al quarto; da lì ci sono tutte e quattro.
Si distinguono dalla forma, non solo dal colore:

| Specie | Aspetto | Cosa fa | Dal livello |
|---|---|---|---|
| **Galleggiante** | stella a tre punte, blu | va dritta | 1 |
| **Di fuoco** | stella a quattro punte, arancio | abbattuta, lancia una **palla di fuoco** verso di te | 2 |
| **Magnetica** | tre punte più piene, verde | ti insegue | 3 |
| **Magnetica di fuoco** | quattro punte più piene, magenta | ti insegue, e abbattuta lancia la palla | 4 |

Le mine nate da una mina abbattuta sono della sua stessa specie. La palla di
fuoco si può abbattere.

# 6. Punti e vite

| Cosa | Punti |
|---|---|
| mina grande | 100 galleggiante, 150 di fuoco, 200 magnetica, 250 magnetica di fuoco |
| mina media | una volta e mezza |
| mina piccola | il doppio: sono le più difficili da prendere |
| palla di fuoco | 110 |
| livello finito | 1000 |

Tre vite, e una in più ogni 10.000 punti. Toccare una mina o una palla costa
una vita, e la mina salta con te (senza punti). Si rinasce al centro, appena
lì intorno è libero, e per un momento si è protetti: la nave lampeggia.

Il tabellone in alto: punteggio, record, livello, e le vite come navette a
destra.

# 7. La musica

Un motivo originale in mi minore: un basso che pulsa sotto e una melodia rada
che sale e ricade, come un segnale lontano. Suona finché si gioca, sotto gli
effetti; la casella **Musica di sottofondo nei giochi** della pagina Giochi la
spegne.

# 8. Come è stato provato

La prova (`test_mine.py`, 72 controlli) verifica ogni regola da sola — la
posamine, la schiusa, la divisione, le specie, il salto, le vite, il livello,
i bordi che si riattaccano, il disegno — e poi fa giocare partite intere a
due piloti automatici:

- uno che **sbaglia come una persona**: vede in ritardo, mira con un errore,
  ogni tanto salta tardi. Arriva di solito fra il secondo e il quinto livello,
  e prima o poi perde sempre;
- uno che **preme tasti a caso**: non passa quasi mai il secondo livello.

Un fotogramma costa meno di un millisecondo sul computer di prova: sul
Raspberry, con 33 millisecondi a disposizione, c'è tutto il margine.
