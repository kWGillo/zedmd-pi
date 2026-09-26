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
quanto si creda. Fuoco conferma, **Esci** ci ripensa.

Due **traguardi**, alla quinta e alla decima domanda: sbagliando si torna lì
invece che a zero. Senza, quindici domande di fila sarebbero una scommessa
sola e nessuno arriverebbe in fondo.

| | |
|---|---|
| Scelta | leva in tutte e quattro le direzioni |
| Risposta | fuoco, due volte |
| Ci ripenso | esci |
| Tempo | 30 secondi, regolabili da 5 a 120 |
| Scala | 100 → 1.000.000 in quindici gradini |
| Traguardi | quinta e decima domanda |

Il tempo che scade vale come una risposta sbagliata: in un quiz il tempo è
parte della domanda.

# 2. Le quattro musiche

È l'unico dei dieci giochi che non ha **un** brano. Ne ha quattro, uno per
momento, e si cambiano dalla pagina Giochi senza toccare il codice:

| Momento | Di serie | Perché |
|---|---|---|
| La domanda appare | `quiz_domanda` | due accordi che salgono, larghi: il sipario che si apre |
| Attesa della risposta | `quiz_attesa` | un pendolo, lento e uguale: è il silenzio a fare paura |
| Risposta giusta | `quiz_giusta` | quattro battute in maggiore, e basta |
| Risposta sbagliata | `quiz_sbagliata` | la stessa melodia che scende, e un basso che casca |

Nella tendina compaiono tutti i brani che stanno in `suoni/`, quindi ci si
può mettere la musica di Pongo o quella di Kingo Bongo — o un file tuo, se lo
copi lì dentro: l'elenco si legge dal disco, non da una lista scritta nel
programma.

# 3. Da dove vengono le domande

Da **OpenQuizzDB** (`openquizzdb.org`), l'unico archivio di quiz a scelta
multipla che esista con l'italiano dentro e una licenza che ne permette la
ridistribuzione: **CC BY-SA 4.0**. È un progetto francese, ed è il motivo per
cui il lavoro vero non è stato scaricare, è stato **buttare via**.

Dei 3.323 quesiti italiani ne sono rimasti **1.301**, con altrettanti in
inglese. Cosa è uscito, e perché:

| Scartate | Quante | Perché |
|---|---|---|
| pacchetti interi | ~1.100 | i dipartimenti della Bretagna, il gossip francese, i modi di dire intraducibili |
| nome proprio tradotto | 291 | «L'Humanité» diventato «Umanità»: non è una risposta imprecisa, è una risposta sbagliata |
| risposta non tradotta | 172 | il francese dice «Pomme», l'inglese «Apple», e l'italiano dice ancora «Apple» |
| troppo lunga | 76 | non ci sta sul pannello, quindi non si legge |
| francese rimasto | 49 | una parola con la cediglia in mezzo a una frase italiana |
| risposte ripetute | 9 | quattro risposte che sono tre |

La regola che ha lavorato di più è quella dei **nomi propri**, e usa il
francese come arbitro: se una risposta francese ha una maiuscola in mezzo —
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

# 4. Lo stesso numero nelle due lingue

Le due banche non sono due archivi diversi: sono lo **stesso** archivio, e la
stessa domanda porta lo stesso identificativo in italiano e in inglese. Serve
a una cosa sola, e non è un dettaglio: il conto delle domande già uscite vale
per tutte e due le lingue. Chi gioca in inglese non si rivede in italiano
quello che ha visto un minuto prima.

Il gioco segue la lingua dell'interfaccia: se la pagina è in inglese, il quiz
è in inglese. Le tue domande possono esistere in una lingua sola —
semplicemente non compaiono nell'altra, invece di comparire vuote.

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

`test_quiz.py`, 90 controlli. I tre che contano davvero:

- **un fuoco solo non risponde mai**: il primo apre la conferma, e lo stesso
  fuoco non la può chiudere — un quarto di secondo di margine, altrimenti su
  un pad tenuto in mano si risponderebbe per sbaglio;
- **la stessa domanda ha lo stesso numero nelle due lingue**, verificato
  confrontando i 1.301 identificativi uno per uno;
- **la risposta giusta non sta sempre nello stesso posto**: nel file è sempre
  la prima, e un quiz in cui la risposta è sempre la A si vince senza
  leggere.
