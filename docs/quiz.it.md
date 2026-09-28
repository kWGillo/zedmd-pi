---
title: "Super Quiz"
subtitle: "Quindici domande, quattro risposte, e una che vale: la accendiamo?"
---

# 1. Il gioco

Una domanda per volta, quattro risposte, un montepremi che raddoppia. Si
sceglie con la leva e si preme fuoco; poi il pannello chiede **«La
accendiamo?»**, e solo il secondo fuoco vale.

```
 CULTURA GENERALE                                        3/15  300
 Qual è il fiume più lungo d'Italia, con i suoi
 652 chilometri?
  A Po                        B Adige
  C Tevere                    D Arno
 ██████████████████████████████████
 SICURO 0
```

Quella domanda in mezzo non è un vezzo copiato dalla televisione. È l'unica
cosa che distingue «ho scelto» da «ho sfiorato il tasto», e su un pad tenuto
in mano mentre si discute di una risposta la differenza capita più spesso di
quanto si creda.

Dalla 14.1 la conferma è una **scelta fra SI e NO**, con le frecce, e il fuoco
conferma quella su cui sei. Si parte sempre da SI: chi ha premuto fuoco per
rispondere preme fuoco un'altra volta e ha risposto. Prima erano due tasti da
ricordare — fuoco sì, esci no — e una domanda con due caselle si capisce
senza istruzioni, che è il punto di una schermata.

Due **traguardi**, alla quinta e alla decima domanda: sbagliando si torna lì
invece che a zero. Senza, quindici domande di fila sarebbero una scommessa
sola e nessuno arriverebbe in fondo.

| | |
|---|---|
| Scelta | leva in tutte e quattro le direzioni |
| Risposta | fuoco, due volte |
| Ci ripenso | esci |
| Tempo | 60 secondi, regolabili da 5 a 180 — oppure nessuno |
| Scala | 100 → 1.000.000 in quindici gradini |
| Traguardi | quinta e decima domanda |

## Un tasto tenuto premuto vale una volta

Il quiz è un gioco di menu, non di riflessi: qui un tasto tenuto giù deve
contare una volta, non trenta al secondo. Dalla 14.1 conta il **momento in cui
si preme**, e il cabinato dice al gioco quali tasti erano già giù quando la
partita si è aperta — perché chi apre una partita lo fa premendo un tasto, e
quel tasto è ancora giù quando arriva il primo fotogramma.

Senza questo, succedeva quello che è stato segnalato: *rientro nel gioco e non
mi viene chiesto se giocare a tempo o meno; a seconda del tasto che premo
parte senza tempo o con tempo*. La schermata c'era: la attraversava da sola
nel primo fotogramma, scegliendo con il tasto che era ancora premuto.

## Con il tempo o senza

Prima della prima domanda il gioco chiede come si vuole giocare, e la leva
sceglie:

```
                       SUPER QUIZ
                  COME VUOI GIOCARE?
        ▶ CON IL TEMPO        SENZA TEMPO
              FUOCO PER COMINCIARE
```

Con il tempo, i secondi in fondo allo schermo sono **60** di serie invece dei
trenta della 13.0: trenta bastavano a leggere una domanda corta, non a
leggerne una lunga e discuterla in due. Si regolano dalla pagina Giochi, da 5
a 180. Il tempo che scade vale come una risposta sbagliata: in un quiz il
tempo è parte della domanda.

Senza tempo, il conto alla rovescia e la barra spariscono e la domanda resta
lì finché non si risponde. E — questa è la parte che si sarebbe notata solo
giocando — **il gioco non si chiude da solo**: l'inattività che dopo tre
minuti riporta il pannello all'orologio, e che negli altri nove giochi è
giusta, qui darebbe la partita per abbandonata mentre si sta ancora
pensando. Senza tempo il limite diventa mezz'ora, e torna a tre minuti appena
la partita finisce. Chi non sceglie entro venti secondi gioca con il tempo:
è il comportamento di sempre.

# 2. Le quattro musiche

È l'unico dei dieci giochi che non ha **un** brano. Ne ha quattro, uno per
momento, e si cambiano dalla pagina Giochi senza toccare il codice:

| Momento | Di serie | Perché |
|---|---|---|
| La domanda appare | `quiz_domanda` | due accordi che salgono, larghi: il sipario che si apre |
| Attesa della risposta | `quiz_attesa` | un pendolo, lento e uguale: è il silenzio a fare paura |
| Risposta giusta | `quiz_giusta` | quattro battute in maggiore, e basta |
| Risposta sbagliata | `quiz_sbagliata` | la stessa melodia che scende, e un basso che casca |

Nella tendina compaiono tre gruppi: i brani che stanno in `suoni/` — quindi
anche la musica di Pongo o quella di Kingo Bongo — i wav che metti in
`/var/lib/dmd/suoni`, che nessun aggiornamento tocca, e **i file audio della
libreria media**: quelli che carichi dalla pagina Media, wav o mp3,
sottocartelle comprese. L'elenco si legge dal disco, non da una lista scritta
nel programma.

**Il brano della risposta parte sempre dall'attacco e suona una volta sola.**
Dall'attacco anche se quello stesso brano stava già suonando un istante prima,
perché sentirne la coda, da fuori, vuol dire «non è partito». E una volta
sola perché non è un sottofondo: ha una fine, e la domanda dopo aspetta quella
fine. Con il giro continuo — come nella 14.1 — un brano corto si risentiva da
capo per il tempo che restava, e mezzo brano di troppo è un difetto: *«l'audio
c'è ma lo ripete una volta e mezza»*. Gli altri momenti, quelli sì, girano: il
pendolo dell'attesa è un sottofondo. E la domanda dopo aspetta che finisca per davvero — il
tetto è quello della conversione, quarantacinque secondi, non venti come
nella 13.1, perché fermarsi prima della fine era proprio la cosa da non fare.
Il fuoco salta l'attesa.

Nella pagina Giochi, sotto ogni tendina, c'è scritto se quel brano è **pronto
e quanto dura**, o perché non lo è; e quattro pulsanti lo fanno sentire subito.
Se si sente dalla pagina e non in partita, il guasto non è nel file.

**Se un brano non si può preparare, si torna al nostro.** Il file tolto dalla
libreria, un mp3 rotto, ffmpeg che manca: prima in quel caso il momento
restava muto, ed è il modo peggiore di dire che qualcosa non va — chi gioca
sente il silenzio e pensa che sia rotto il gioco. Il motivo vero, quello che
scrive ffmpeg, finisce nel log del servizio.

Un mp3 non entra nel mixer com'è: gli effetti dei giochi escono tutti da un
flusso solo, aperto una volta e tenuto aperto, e dentro quel flusso ci entrano
campioni — mono, 16 bit, 22050 Hz — non file. Il brano si converte quindi una
volta con ffmpeg, quando lo scegli e quando si apre il gioco, mai durante una
domanda: il risultato resta in `/var/lib/dmd/musiche` e si rifà solo se
cambi il file di partenza. Si convertono al massimo **45 secondi**, perché il
mixer tiene i campioni in memoria e un brano di quattro minuti sarebbero
duecento megabyte su un Raspberry.

## Finita la partita, fuoco ne comincia un'altra

Come negli altri nove giochi. Nella 13.0 e nella 13.1 non era così: a partita
finita il quiz non rispondeva più a niente, e rientrando sullo stesso gioco si
ritrovava la stessa partita finita — che dal pad è indistinguibile da un gioco
che ha smesso di leggere i tasti. Adesso la schermata finale lo dice, e c'è
mezzo secondo di margine perché il fuoco che ha dato l'ultima risposta non
faccia anche ripartire la partita dopo.

La stessa schermata non dice più «hai vinto» a chi ha perso alla prima
domanda: chi arriva in fondo ha vinto, chi si ferma a un traguardo si porta a
casa qualcosa, e chi sbaglia subito legge PARTITA FINITA.

## La risposta dura quanto la sua musica

La musica della risposta non fa da sottofondo: **è il tempo che passa**. La
domanda dopo arriva quando il brano finisce — sette secondi per la risposta
giusta e nove e mezzo per quella sbagliata, con i nostri, invece dei tre e
mezzo e quattro e mezzo della 13.0, che li tagliavano a metà. Chi ha fretta
preme fuoco e va avanti subito; chi mette un suo brano se lo sente tutto senza
dover regolare niente. Fra i 2 e i 20 secondi: sotto non si legge la risposta,
sopra il gioco sembrerebbe fermo. A musica spenta valgono i tempi di prima.

# 3. Da dove vengono le domande

Da **OpenQuizzDB** (`openquizzdb.org`), l'unico archivio di quiz a scelta
multipla che esista con l'italiano dentro e una licenza che ne permette la
ridistribuzione: **CC BY-SA 4.0**. È un progetto francese, ed è il motivo per
cui il lavoro vero non è stato scaricare, è stato **buttare via**.

Dei 3.323 quesiti ne sono rimasti **1.307 in italiano e 1.431 in inglese** —
numeri diversi, ed è il punto: ogni lingua paga solo i propri difetti. Cosa è
uscito dall'italiano, e perché:

| Scartate | Quante | Perché |
|---|---|---|
| pacchetti interi | ~1.100 | i dipartimenti della Bretagna, il gossip francese, i modi di dire intraducibili |
| nome proprio tradotto | 291 | «L'Humanité» diventato «Umanità»: non è una risposta imprecisa, è una risposta sbagliata |
| risposta non tradotta | 172 | il francese dice «Pomme», l'inglese «Apple», e l'italiano dice ancora «Apple» |
| troppo lunga | 76 | non ci sta sul pannello, quindi non si legge |
| francese rimasto | 49 | una parola con la cediglia in mezzo a una frase italiana |
| risposte ripetute | 9 | quattro risposte che sono tre |

La regola che ha lavorato di più è quella dei **nomi propri**, e usa il
francese come arbitro — una lingua per volta, dalla 15.0: se una risposta francese ha una maiuscola in mezzo —
`L'Humanité`, `Mega Mindy`, `PlayStation 2` — allora è un nome, e le altre due
lingue devono ripeterlo uguale. E se almeno due delle quattro sono nomi, lo
sono tutte e quattro: quando le alternative sono Mega Mindy, Gwen Tennyson e
Sif, anche «Blink» è un personaggio, e «Lampeggia» è una traduzione che
nessuno voleva.

**Quello che resta non è perfetto**, ed è giusto saperlo: su venti domande
prese a caso, quindici sono pulite e le altre hanno una formulazione goffa o
un sapore francese. Nessuna, per costruzione, ha la risposta giusta
sbagliata — quella è l'unica cosa che in un quiz non si perdona.

## Le tue domande

Un file `domande.it.csv` (o `domande.en.csv`) nella cartella dati,
`/var/lib/dmd`, si aggiunge alle nostre e **non viene mai toccato dagli
aggiornamenti**. Stesso formato:

```
id;categoria;difficolta;domanda;giusta;sbagliata1;sbagliata2;sbagliata3;curiosita
mie-1;Famiglia;1;In che anno ci siamo sposati?;1998;1997;1999;2001;
```

La prima risposta è quella giusta: sul pannello si mescolano. La difficoltà
va da 1 a 3, e decide a che punto della scala può uscire. Se ripeti un nostro
identificativo, vince la tua riga.

Sono le domande che rendono il gioco vostro invece che di chiunque: quelle di
famiglia, quelle che fanno ridere a Natale.

# 4. Due banche indipendenti

Fino alla 14.2 erano gemelle: la stessa domanda con lo stesso identificativo
nelle due lingue, così che il conto delle domande già uscite valesse per tutte
e due. Sembrava elegante, e costava carissimo. La segnalazione che l'ha
smontata è di una riga: *«le domande in inglese possono tranquillamente essere
diverse da quelle in italiano»*. È vero, e legandole si pagava un prezzo
assurdo: **ogni riga con la traduzione rotta in una sola delle due lingue
veniva buttata da tutte e due**. L'italiano pulito e l'inglese che aveva
tradotto un nome proprio? Persi tutti e due.

Dalla 15.0 ogni lingua ha la sua banca, le sue regole di pulizia e i suoi
identificativi, e il conto delle domande già uscite è **uno per lingua** — il
che è anche l'unica cosa sensata quando le domande non sono le stesse. La
memoria vecchia, se c'era, diventa quella italiana, e l'inglese riparte
pulito.

I numeri di adesso: **1.642 domande in italiano e 4.820 in inglese**. L'inglese
è così avanti perché ha due fonti (vedi sotto); l'italiano cresce a ondate, con
le traduzioni fatte a mano.

L'identificativo dice da dove viene la riga: `oq-` da OpenQuizzDB, `tdb-` da
Open Trivia DB, `otqa-` da OpenTriviaQA.

Il gioco segue la lingua dell'interfaccia: se la pagina è in inglese, il quiz
è in inglese. Le tue domande possono esistere in una lingua sola —
semplicemente non compaiono nell'altra, invece di comparire vuote.

## Le altre fonti, e perché l'italiano resta solo

Per l'inglese OpenQuizzDB non è l'unica: ce ne sono due più grandi, con la
stessa licenza.

| Archivio | Quante | Lingua | Come sta |
|---|---|---|---|
| [OpenQuizzDB](https://github.com/Zeuh/OpenQuizzDB) | ~3.300 per lingua | it, en, fr, es, de, nl | l'unico con l'italiano |
| [Open Trivia DB](https://opentdb.com/) | 5.298 verificate a mano | inglese | scaricato dall'API, o letto da una cartella con `--tdb-da` |
| [OpenTriviaQA](https://github.com/uberspot/OpenTriviaQA) | 49.192 uniche | inglese | si attiva con `--con-otqa <clone>`, spento di serie |

Per l'italiano non c'è altro di ridistribuibile: i siti di quiz per concorsi
non hanno una licenza che lo permetta, e gli unici dataset italiani di
«cultura generale» che girano sono generati da un modello, senza fonti citate.
Per un gioco in cui la risposta giusta deve essere *giusta*, non basta.

## Le domande tradotte a mano

Quello che manca all'italiano non si risolve con una traduzione automatica —
sarebbe rifare il difetto da cui veniamo. Si risolve traducendo a mano, una
riga per volta, e il lavoro sta in `diagnostica/traduzioni.tsv`:

```
tdb-1002 ~ La Terra si trova in quale galassia? ~ Via Lattea ~ Galassia di Marte ~ ...
tdb-345  ~ SALTA ~ chiede come si dice pomodoro in italiano
```

Le regole sono quattro, e la quarta è quella che conta: i nomi propri restano
come sono; le risposte stanno in venti caratteri e le domande in cento, perché
quello è lo spazio del pannello; sport e televisione straniera restano fuori,
perché tradotti resterebbero comunque di un'altra cultura; e **quello che in
italiano non ha senso si salta**, con il motivo scritto accanto, invece di
tradurlo lo stesso. «In inglese il pollice non è un dito, in italiano sì» è
un motivo valido per buttare una domanda.

Il file cresce a ondate: le domande già tradotte restano, e chi rigenera le
banche le ritrova. Sono anche loro CC BY-SA 4.0, come la fonte.

# 5. Niente rete

Le domande stanno in due file dentro il pacchetto, e non si scarica niente
mentre si gioca. Le ragioni sono tre e valgono tutte:

- una domanda deve arrivare in millesimi, e una chiamata HTTP dal Raspberry
  sono due o tre decimi quando va bene;
- l'archivio da cui vengono ammette **una richiesta ogni cinque secondi**:
  quindici domande sarebbero più di un minuto di attesa;
- un pannello che dipende da un sito per fare una domanda è un pannello che
  un giorno non la fa. È la stessa ragione per cui i cataloghi del radar
  stanno su disco.

Si rifanno con `python3 diagnostica/genera_domande.py`, **sul computer e non
sul Raspberry**.

# 6. Come è stato provato

`test_quiz.py`, 157 controlli, e `test_musica_media.py`, altri 35. Quelli che contano davvero:

- **un fuoco solo non risponde mai**: il primo apre la conferma, il secondo
  vale su SI o su NO — e un tasto tenuto premuto conta una volta, non trenta
  al secondo;
- **le due banche non sono più gemelle**, e dentro ciascuna nessun
  identificativo si ripete;
- **la risposta giusta non sta sempre nello stesso posto**: nel file è sempre
  la prima, e un quiz in cui la risposta è sempre la A si vince senza
  leggere;
- **senza tempo non scade niente**: né il conto alla rovescia, che non c'è,
  né l'inattività, verificata chiedendo al gioco il proprio limite — 1.800
  secondi mentre si gioca, 180 appena finito.
