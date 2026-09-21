---
title: "World Time"
subtitle: "Che ore sono adesso dall'altra parte del mondo, in una riga sotto l'orologio"
---

# 1. Che cos'è

Fino a cinque località, con la loro ora vera, in una banda alta dieci pixel
sotto le cifre dell'orologio. Il nome nel colore della data, l'ora in grigio
chiaro, e un `+` o un `−` quando laggiù è un altro giorno.

Non è un servizio a sé: vive **dentro l'orologio**, e si accende dalla pagina
*Orologio*. Quando è spento il pannello è identico a prima.

# 2. Il fuso orario, non le coordinate

La domanda naturale è *«scrivo il nome della città o il GPS?»*, e la risposta
è **nessuna delle due**: si salva il **fuso orario IANA** — `America/New_York`,
`Asia/Tokyo` — e la città è solo il modo comodo di sceglierlo.

## 2.1 Perché non un'ora di scarto

Perché «New York = UTC−5» è sbagliato per metà dell'anno, e sbagliato in
silenzio. Nessuno se ne accorge finché non arriva in ritardo a una chiamata.

Il fuso invece porta con sé le regole dell'ora legale, comprese quelle che
cambiano: gli Stati che spostano le date, quelli che l'ora legale l'hanno
abolita. Quelle regole stanno già sul Raspberry, nel database dei fusi del
sistema, e si aggiornano con gli aggiornamenti di sistema.

La prova, fatta sul serio:

| Ora di Roma | Ora di New York | Sigla |
|---|---|---|
| 15 gennaio, 12:00 | 06:00 | `EST` |
| 15 luglio, 12:00 | 06:00 | `EDT` |

Stesso orario, sigla diversa. Uno scarto fisso ne avrebbe sbagliata una delle
due, e a nessuno sarebbe venuto in mente di controllare.

## 2.2 Perché non le coordinate GPS

Per un motivo pratico, non di principio. Tradurre latitudine e longitudine in
un fuso richiede un archivio di poligoni da cinquanta o cento megabyte, oppure
un servizio online con la sua chiave. Su un pacchetto che pesa tre megabyte il
primo è fuori scala; il secondo aggiunge una dipendenza di rete a una cosa che
funziona benissimo da sola, per sempre, anche con il router staccato.

# 3. Come si imposta

Pagina **Orologio**, sezione *World Time*. Cinque righe, ognuna con:

| Campo | A cosa serve |
|---|---|
| Spunta | se questa località si mostra |
| **Città** | una scorciatoia: sceglierla riempie il fuso |
| **Fuso** | l'identificativo IANA — **è questo che vale** |
| **Sul pannello** | l'etichetta che si vede, fino a 14 caratteri |
| **Adesso** | l'ora di laggiù, per controllare al volo |

La tendina ha un centinaio fra capitali e città che si nominano parlando, con
i nomi in italiano dove l'italiano un nome ce l'ha. Non pretende di essere
completa: per un posto che non c'è, il campo **Fuso** accetta qualunque nome
fra i quasi cinquecento che il sistema conosce.

## 3.1 La tendina non mostra cosa hai scelto, e non è una dimenticanza

Scegli una città e la casella **Fuso** si riempie mentre guardi. Dopo il
salvataggio la tendina torna su *— scegli —* e la casella resta piena.

Sembra un difetto ed è l'unica cosa onesta che può fare. Quello che si salva
è **il fuso**, e un fuso ha più città: Roma e Milano sono `Europe/Rome`, New
York e Miami sono `America/New_York`, Seattle e Los Angeles sono
`America/Los_Angeles`. Mostrare «la città del fuso salvato» vuol dire
sceglierne una a caso fra quelle — e infatti chi sceglieva Roma tornava sulla
pagina e trovava scritto **Milano**: stesso fuso, ma non quello che aveva
chiesto.

Quindi la tendina è un attrezzo per riempire, non una finestra su quello che
c'è dentro. Quello che vale sta nella casella accanto, che è anche l'unica
cosa che il pannello legge.

> `America/Seattle` non esiste. Il database dei fusi nomina ogni zona con la
> sua città più grande, e tutta la costa del Pacifico — Seattle, Portland,
> San Francisco, Las Vegas, Los Angeles — ha le stesse regole. Seattle, San
> Francisco e Las Vegas sono in tendina lo stesso: non trovarle fa credere
> che manchino.

> **L'etichetta è la cosa che conta di più**, e non è un dettaglio estetico:
> decide **quante** città si vedono insieme. Vedi il capitolo 5.

# 4. Dove sta, sul pannello

La banda occupa le righe da 51 a 61. Sotto c'è la barra del timer, che parte a
62; sopra, le cifre dell'orologio **salgono di tre pixel**.

## 4.1 Perché tre, e non cinque

Nella 9.9 erano cinque, e non servivano a evitare una collisione: senza alzata
le cifre finiscono alla riga 45 e la banda comincia a 51, lo spazio c'era già.
Servivano a **ribilanciare** — senza, le cifre hanno 17 righe sopra e 5 sotto,
e sembrano sedute sulla banda invece che centrate.

Cinque però ne creavano un'altra, e si è vista solo sul pannello vero:

| Alzata | Cifre | Righe in comune con la data |
|---|---|---|
| 0 | 17–45 | 0 |
| **3** | **14–42** | **1** |
| 5 | 12–40 | 3 |

Con il cursore sul suo `+2` di serie le cifre scendono a 16–44, e le righe in
comune diventano **zero**.

Le cifre e la data sono separate da **circa cinque pixel in orizzontale**,
uno in più o uno in meno secondo le cifre del minuto e il giorno della
settimana. L'alzata non c'entra, è una misura verticale. Ma finché i due
blocchi stanno ad altezze diverse nessuno li confronta; affiancati, a tre
metri e con cinque pixel in mezzo, il minuto e il giorno della settimana per
un istante si leggono come una cosa sola.

A tre la riga in comune è una, e sotto le cifre restano otto righe invece di
dieci. Uno squilibrio che non si nota, in cambio di una quasi collisione che
si notava.

## 4.2 E se tre non ti va

Pagina *Orologio*, sezione dell'aspetto: **Posizione verticale dell'ora**, un
cursore da −12 a +12 pixel. Lo zero è la posizione calcolata dal programma, il
cursore è uno scostamento da lì, e vale anche a World Time spento.

**A installazione appena fatta il cursore è su +2**, non su zero. Il centro
geometrico non è il centro che si vede: un pannello sta su una mensola e lo si
guarda dal basso, e da lì le cifre centrate sembrano alte. Due pixel misurati
sul pannello vero, non calcolati — e chi ha un'altra mensola muove il cursore.

Con il World Time acceso e il cursore di serie le cifre stanno alle righe
16–44: zero righe in comune con la data, sei righe di margine sopra la banda.

Il numero giusto non è lo stesso per tutti. Oltre il limite fisico — la banda,
il bordo — il cursore smette di muovere invece di spingere le cifre dove non
si leggono più.

Due cose si spostano da sole quando la banda è accesa:

**La colonna delle raccolte differenziate si stringe.** Con quattro raccolte
attive nello stesso giorno, l'ultima arrivava alla riga 59, cioè dentro la
banda. Adesso la colonna sa dove deve fermarsi e distribuisce le voci nello
spazio che le resta.

**Il semaforo delle scadenze non si tocca**, e qui c'è una sorpresa: le tre
lampade occupano **sette pixel** di larghezza, da 219 a 225. La fascia che gli
è riservata è larga 68, ma lui ne usa un ottavo. Non c'era niente da spostare
— bastava misurare invece di supporre.

# 5. Quante se ne vedono insieme

Dipende da quanto sono lunghe le etichette. Il carattere è a larghezza fissa,
sei pixel ogni lettera, e il conto si fa sulla somma:

| Città insieme | Etichette, in tutto | Per esempio |
|---|---|---|
| **2** | sempre — anche due da 14 | `LOS ANGELES` `BUENOS AIRES` |
| **3** | fino a **20** caratteri | `SEATTLE` `TOKYO` `NEW YORK` (20) |
| **4** | fino a 13 caratteri | `NY` `TYO` `LDN` `SYD` (11) |
| 5 | fino a 5 — in pratica mai | |

Con tre etichette più lunghe di venti caratteri in tutto se ne vedono due alla
volta. Niente esce mai dal bordo: un'etichetta arriva al massimo a 14
caratteri, e anche la più lunga sta da sola con molto spazio intorno.

## 5.1 Perché di notte se ne vedevano meno

Fino alla 9.11 il conto si faceva sulle scritte del momento, **segno del giorno
compreso**. Il segno è un carattere, sei pixel, e compare solo quando la città
è su un altro giorno: «SEATTLE TOKYO NEW YORK» stava in 245 pixel su 254 di
giorno, e di notte — con Seattle e New York ancora a ieri, due segni — arrivava
a 257. La banda passava da tre città insieme a due che si alternano, e al
mattino tornava a tre.

Dalla 9.12 il posto del segno si tiene sempre, e il nome sta a tre pixel dalla
sua ora invece che a uno spazio intero. Il conto dà lo stesso numero a
mezzogiorno e a mezzanotte, e lo stesso terzetto con tre segni occupa 250.

Se le località attive sono più di quante ne stanno, si formano dei gruppi che
si alternano **ogni otto secondi**, con un cambio netto: niente scorrimento,
niente dissolvenza. Lo scorrimento obbliga ad aspettare l'inizio del giro, e
una dissolvenza su un pannello LED è una scala di grigi — e le intensità
intermedie su questo hardware sono la causa dello sfarfallio.

> **Con più città di quante ne stanno, il conto si fa sulle più larghe.**
> Sembra pignoleria e non lo è: con la rotazione ogni gruppo deve starci, e
> non si sa quale capiterà. Contando le prime, un giro su due l'ultima città
> usciva dal bordo. Per questo quattro città attive — `SEATTLE` `TOKYO`
> `NEW YORK` `LONDRA` — girano a due a due, anche se tre di loro starebbero
> insieme.

Il momento del cambio si calcola dai secondi dell'ora corrente e non da un
contatore interno: due pannelli accesi nella stessa stanza girano insieme, e
un riavvio non fa ripartire il giro da capo.

# 6. Il segno del giorno

Guarda queste due righe:

```
NEW YORK 23:54-        TOKYO 06:30+
```

A Roma sono le 05:54 e a New York le 23:54 — ma di **ieri**. L'ora da sola
nasconde proprio l'informazione che uno cerca guardando un orologio del mondo,
ed è tanto più importante quanto più il fuso è lontano.

Il segno costa due pixel: `−` se laggiù è il giorno prima, `+` se è il giorno
dopo, niente se è lo stesso.

# 7. Quando non funziona

**La sezione dice che manca il database dei fusi.** Il Raspberry non ha
`tzdata`. Si installa con `sudo apt install tzdata`. È raro: Raspberry Pi OS
ce l'ha di serie.

**Una riga mostra `—` nella colonna «Adesso».** Quel fuso non esiste su questo
sistema. Controlla l'ortografia — sono sensibili alle maiuscole e usano il
trattino basso: `America/New_York`, non `america/new york`.

**Una località non compare sul pannello ma le altre sì.** Stesso motivo: un
fuso che non risponde viene saltato, e le altre restano. È voluto — una riga
sbagliata non deve portarsi via le altre quattro.

**Compaiono solo due città su cinque.** È la rotazione: aspetta otto secondi.
Se ne vuoi di più insieme, accorcia le etichette.

**Le ore sono tutte sbagliate della stessa quantità.** Non è il World Time: è
l'ora del Raspberry. Pagina *Orologio*, sezione dell'ora di sistema, controlla
che NTP sia sincronizzato.

# 8. Riassunto

| | |
|---|---|
| Dove si imposta | pagina *Orologio*, sezione *World Time* |
| Quante località | fino a 5 |
| Quante insieme | 2–4, secondo la lunghezza delle etichette |
| Rotazione | cambio netto ogni 8 secondi |
| Cosa si salva | il fuso IANA, non uno scarto di ore |
| Ora legale | automatica, dal database del sistema |
| Altro giorno | `+` o `−` dopo l'ora |
| Sul pannello | banda alle righe 51–61; le cifre salgono di 3 px |
| Se non ti torna | cursore *Posizione verticale dell'ora*, ±12 px, +2 di serie |
