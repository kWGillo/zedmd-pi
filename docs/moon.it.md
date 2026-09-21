---
title: "Moon"
subtitle: "La Luna di stasera, le lune con un nome, le stagioni, gli sciami e le serate da guardare"
---

# 1. Che cos'è

Un servizio che parla **solo di notte**, dal tramonto all'alba, e solo quando
tocca a lui: si dà il turno con il meteo, uno ogni due contenuti del Media
Player. Cinque schermate, e ognuna risponde a una domanda sola:

| Schermata | La domanda | Quando compare |
|---|---|---|
| **La Luna** | com'è stasera? | tutte le sere |
| **Una luna con un nome** | che luna è? | dal terzo giorno prima |
| **Una stagione** | quando cambia la stagione? | dal terzo giorno prima |
| **Uno sciame** | quante stelle cadenti, e la Luna disturba? | dal terzo giorno prima |
| **La serata buona** | vale la pena uscire a guardare? | solo quando è vero |

Le ultime quattro compaiono solo quando c'è qualcosa da dire. Un pannello che
annuncia cose rare si guarda; uno che annuncia sempre qualcosa diventa sfondo.

# 2. Il turno con il meteo

La regola è una sola: **ogni due media compare il meteo o la Luna, e si danno
il cambio.**

```
media · media · METEO · media · media · MOON · media · media · METEO …
```

- **Di giorno** la Luna non c'è, quindi lo spazio va sempre al meteo.
- **Senza media** — al mattino, o una sera con il Media Player spento — lo
  spazio si apre lo stesso dopo i minuti del giro del meteo (dieci di serie,
  nella scheda Meteo). Senza questo tetto, contare i media vorrebbe dire non
  mostrare mai niente proprio quando i media sono spenti.
- **La fascia del mattino** resta del meteo: dalle 6:30 alle 9:00 il
  bollettino ogni due minuti, e il turno sta fermo.
- **Un turno si consuma quando qualcuno lo vede.** Se in quel momento il
  pannello era di un aereo o di una notifica, la finestra si chiude senza
  essere vista, e dopo un minuto si riprova la stessa sorgente, senza passare
  all'altra.

Con il servizio Moon spento, lo spazio va tutto al meteo. Con il meteo spento,
di notte va tutto alla Luna.

# 3. Le schermate

## 3.1 La Luna di stasera

A sinistra il disco, **giallo panna**, con la fase vera calcolata pixel per
pixel: da noi, emisfero nord, la luna crescente è illuminata a destra. La parte
in ombra non è nera: è la **luce cinerea**, la Terra che illumina la Luna, che
si vede davvero a occhio nudo.

I puntini scuri sono le macchie grandi, messe dove stanno davvero: i mari
Imbrium e Serenitatis in alto, Tranquillitatis al centro, Crisium sul bordo
destro, Tycho verso il polo sud. Compaiono solo sulla parte in luce, come
quelli veri.

A destra: il nome della fase, la percentuale illuminata, **CRESCENTE** o
**CALANTE**, a che ora sorge e tramonta, e il giorno della prossima luna piena.

## 3.2 Le lune con un nome

Solo nomi che hanno una definizione:

- **Luna del Raccolto** — la luna piena più vicina all'equinozio d'autunno.
  Per diverse sere di fila sorge poco dopo il tramonto: in autunno l'eclittica
  è molto inclinata sull'orizzonte della sera, e chi raccoglieva aveva luce per
  lavorare dopo il buio. Nel 2026 cade **sabato 26 settembre**.
- **Superluna** — una luna piena a meno di 360.000 km dal centro della Terra.
  Le definizioni in giro sono diverse; questa è la più severa fra quelle
  comuni. Nel 2026 è una sola: la **vigilia di Natale**, a circa 356.700 km.
- **Luna blu** — la seconda luna piena dello stesso mese. Nel 2026 è stata il
  31 maggio.

## 3.3 Equinozi e solstizi

Il giorno, l'ora arrotondata — «VERSO LE 2» — e quanta luce dà quel giorno.
L'ora è arrotondata apposta: il calcolo del Sole è giusto entro una decina di
minuti, e il minuto esatto sarebbe una precisione che non abbiamo.

## 3.4 Gli sciami

Otto sciami, con il giorno del picco della lista dell'International Meteor
Organization: Quadrantidi, Liridi, Eta Aquaridi, Delta Aquaridi, **Perseidi**,
**Orionidi**, Leonidi, **Geminidi**.

Il numero è lo **ZHR**: quante meteore in un'ora sotto un cielo perfetto. Sotto
un cielo vero se ne vedono meno, spesso la metà: è un confronto fra sciami, non
una promessa.

E la Luna, che è la cosa che decide la serata. Tre risposte:

| Risposta | Che vuol dire |
|---|---|
| **La Luna non disturba** | illuminata meno di un terzo, o già sotto l'orizzonte |
| **Luna al 72%, giù alle 02:03 — poi cielo buio** | luminosa ma tramonta prima delle quattro |
| **Luna al 98%: ne copre molte** | resta su nelle ore buone |

Le ore buone sono quelle dopo mezzanotte, quando il nostro lato della Terra
guarda nella direzione in cui corre.

## 3.5 La serata buona

*«Stanotte cielo buio e sereno: Saturno a sud-est, 40°.»*

Tre condizioni, tutte necessarie, controllate dal crepuscolo nautico fino
all'una di notte:

- **buio senza Luna** per almeno un'ora e mezza: la Luna sotto l'orizzonte, o
  illuminata meno di un quarto;
- **poche nuvole**: in media non più del 25%, secondo la previsione che il
  meteo ha già scaricato;
- e il **pianeta più luminoso** visibile a metà della finestra buona, con la
  direzione e l'altezza in gradi. Un pugno a braccio teso è circa dieci gradi.

Senza la previsione delle nuvole la serata non si giudica: un cielo buio e
coperto non è una serata buona, e dirlo senza saperlo sarebbe una promessa a
vuoto.

# 4. Quanto sono giusti i conti

Tutto si calcola sul Raspberry, **senza rete e senza dipendenze nuove**,
partendo da `pianeti.py`. I risultati sono stati confrontati con gli orari
pubblicati e con PyEphem, un'effemeride indipendente:

| Cosa | Scarto massimo |
|---|---|
| Fasi lunari, 2025–2030 | 2,5 minuti |
| Sorgere e tramonto della Luna, 4 città | 0,5 minuti |
| Tramonto del Sole | meno di un minuto |
| Equinozi e solstizi, 2025–2030 | 9,5 minuti |

Per le stagioni c'è stata una correzione vera. Il Sole di `pianeti.py` è
calcolato nel riferimento dell'anno 2000: per dire da che parte guardare va
benissimo, per dire **quando** succede qualcosa no. In ventisei anni
l'equinozio si è spostato di un terzo di grado, e il primo calcolo dava
l'equinozio d'autunno con **nove ore** di scarto. Adesso il Sole si porta al
riferimento della data — precessione, nutazione e aberrazione — e lo scarto è
di minuti.

# 5. Semina e raccolto: perché no

Il calendario lunare agricolo è una tradizione, non un effetto misurabile, e
le tradizioni si contraddicono fra loro. Il pannello mette accanto numeri
verificati al minuto: non presenta una tradizione come un fatto.

L'unico legame vero fra Luna e raccolto è astronomico, ed è la Luna del
Raccolto.

# 6. Dove si imposta

Pagina **Servizi**, riga **Moon**: l'interruttore e il pulsante *Mostra la
Luna adesso*, che la mette sul pannello anche di giorno — per vederla senza
aspettare il tramonto.

Senza la posizione del DMD (pagina Impostazioni) la Luna si mostra lo stesso,
ma senza sorgere e tramonto, e la serata buona non si calcola. Il servizio non
sa dove sei, e non lo inventa.

| | |
|---|---|
| Quando | dal tramonto all'alba |
| Quanto spesso | a turno con il meteo, uno ogni due media |
| Senza media | dopo i minuti del giro del meteo (10) |
| Quanto dura | 15 secondi |
| Priorità | 53, fra OnAir e il meteo |
| Home Assistant | interruttore **Moon** |
