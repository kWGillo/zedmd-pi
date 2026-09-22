---
title: "Pongo"
subtitle: "Due racchette, una pallina: tu contro il pannello"
---

# 1. Il nome

Il gioco del 1972 si chiamava PONG, e **PONG è un marchio di Atari**. Il
meccanismo — due racchette, una pallina, un punto a chi non la prende — non è
di nessuno e si rifà liberamente; il nome invece è loro. Questo è **Pongo**.

# 2. Come si gioca

Tu a sinistra, in rosso. Il computer a destra, in azzurro. **Su e giù**
con la croce direzionale o con una delle due levette, **avanti e indietro**
con sinistra e destra; **fuoco** per cominciare. Il punteggio sta in alto, uno per parte della rete, e vince chi
arriva a **11** — come il cabinato, senza vantaggi.

- **Dove colpisci conta.** Al centro della racchetta la pallina esce dritta,
  sui bordi esce inclinata fino a 50 gradi. È l'unico modo di mirare.
- **Ogni colpo accelera** la pallina del 5%, fino a un tetto: oltre, su 64
  righe, non si seguirebbe più.
- **Dopo ogni punto** la pallina riparte dal centro dopo un secondo, verso chi
  ha perso il punto, da un'altezza a caso.

- **Puoi avanzare.** Con sinistra e destra la racchetta si muove anche in
  orizzontale, fino a **metà del tuo campo**. Da lì chiudi gli angoli
  all'avversario, e se colpisci **mentre avanzi schiacci**: la pallina riparte
  il 15% più veloce, oltre all'accelerazione di ogni colpo. In cambio hai meno
  tempo: a metà campo una pallina veloce arriva in un terzo di secondo. Una
  pallina che ti è già passata dietro non si rimanda — non si colpisce di
  spalle. Il computer resta sul fondo: è il tuo vantaggio, e lo paghi in
  tempo di reazione.

Il campo è **tutto il pannello**: gli altri giochi tengono la striscia di
destra per il tabellone, qui il punteggio sta dove lo si aspetta, sopra la
rete.

# 3. Il computer

Un avversario che non sbaglia mai non si batte, e uno che sbaglia a caso non
diverte. Questo ha **tre difetti umani**:

| Difetto | Facile | Normale | Difficile |
|---|---|---|---|
| si accorge che la pallina arriva dopo | 0,30 s | 0,18 s | 0,10 s |
| velocità della racchetta | 48 px/s | 62 px/s | 80 px/s |
| errore nello stimare dove arriva | ±7 px | ±4,5 px | ±2,5 px |

L'errore **cresce con la velocità della pallina**, che è esattamente quando
sbaglia anche una persona. E lo sceglie una volta per scambio: una stima
ricalcolata a ogni fotogramma farebbe tremare la racchetta, invece di mandarla
nel posto sbagliato con convinzione.

I livelli non sono stati tarati a occhio. Una prova tira trecento palle verso
il computer e conta quelle che rimanda — circa **60%** a facile, **75%** a
normale, **95%** a difficile — e fa giocare partite intere a un giocatore
automatico che reagisce in due decimi di secondo e sbaglia la mira di qualche
pixel: vince quasi sempre a facile, circa metà delle volte a normale, quasi
mai a difficile.

Il livello si sceglie nella scheda di Pongo, pagina **Giochi**. Cambiato a
partita aperta, vale dalla battuta successiva.

# 4. Il record

Il record di Pongo è lo **scambio più lungo**: quanti colpi di racchetta,
tuoi e del computer, senza che la pallina cada. È l'unico numero che cresce
con la bravura e non con il tempo passato a giocare.

# 5. Un giocatore solo, per adesso

Il secondo giocatore non c'è. Oggi pad e tastiera finiscono in un flusso di
comandi unico: il gioco non sa da quale dispositivo arriva un tasto, e per
due giocatori bisogna prima insegnarlo al lettore dei comandi. Il gioco però
ha già i due lati separati — la racchetta di destra si muove da una funzione
sua — quindi il secondo giocatore si aggiungerà senza riscriverlo.

# 6. I suoni

Tre, calcolati come quelli dello Snake (`diagnostica/genera_suoni.py`): il
**ping** della racchetta, la **sponda** un'ottava sotto, e il **punto**, la
stessa nota del ping che sale e dura di più. Il punto del computer usa il
suono della palla persa di Breakout.
