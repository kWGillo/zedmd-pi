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
| **Città** | la tendina: sceglierla riempie il fuso |
| **Fuso** | l'identificativo IANA, anche scritto a mano |
| **Sul pannello** | l'etichetta che si vede, fino a 14 caratteri |
| **Adesso** | l'ora di laggiù, per controllare al volo |

La tendina ha un centinaio fra capitali e città che si nominano parlando, con
i nomi in italiano dove l'italiano un nome ce l'ha. Non pretende di essere
completa: per un posto che non c'è, il campo **Fuso** accetta qualunque nome
fra i quasi cinquecento che il sistema conosce.

> **L'etichetta è la cosa che conta di più**, e non è un dettaglio estetico:
> decide **quante** città si vedono insieme. Vedi il capitolo 5.

# 4. Dove sta, sul pannello

La banda occupa le righe da 51 a 61. Sotto c'è la barra del timer, che parte a
62; sopra, le cifre dell'orologio **salgono di cinque pixel** per fare posto —
spazio che sopra c'era già, e che sotto è la differenza fra un carattere da
otto e uno da dieci, cioè fra leggere e non leggere da tre metri.

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

Dipende da quanto sono lunghe le etichette, e il conto è questo:

| Etichette | Insieme |
|---|---|
| `NY` `TYO` `LDN` `SYD` | **quattro** |
| `NEW YORK` `TOKYO` `LONDRA` | **tre** |
| `LOS ANGELES` e simili | **due** |

Se le località attive sono più di quante ne stanno, si formano dei gruppi che
si alternano **ogni otto secondi**, con un cambio netto: niente scorrimento,
niente dissolvenza. Lo scorrimento obbliga ad aspettare l'inizio del giro, e
una dissolvenza su un pannello LED è una scala di grigi — e le intensità
intermedie su questo hardware sono la causa dello sfarfallio.

> **Il conto si fa sull'etichetta più larga di tutte, non sulle prime tre.**
> Sembra pignoleria e non lo è: «NEW YORK TOKYO LONDRA» stanno in tre, ma
> «SYDNEY LOS ANGELES NEW YORK» no, e con la rotazione capitano tutti e due i
> gruppi. Contando le prime, un giro su due l'ultima città usciva dal bordo.

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
| Sul pannello | banda alle righe 51–61; le cifre salgono di 5 px |
