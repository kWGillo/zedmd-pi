---
title: "Info inutili"
subtitle: "Il santo, chi festeggia, la giornata mondiale, e chi è nato o morto oggi"
---

# 1. A cosa serve

A niente, ed è il punto. Tutti gli altri servizi rispondono a una domanda —
che ore sono, che tempo fa, quando scade il bollo, quando passa la Stazione
Spaziale. Questo fa compagnia, ed è probabilmente quello che sul pannello di
una cucina verrà letto di più.

Compare **subito dopo il meteo**: appena la finestra del meteo si chiude, il
pannello passa a lui senza intervallo.

# 2. Tre schermate, due per volta

```
 oggi si festeggia                  accadde oggi
┌──────────────────────────────┐   ┌──────────────────────────────┐
│ 24 SETTEMBRE                 │   │ ACCADDE OGGI                 │
│ San Pacifico                 │   │      La Guinea-Bissau        │
│ Pacifico · Mercedes · Amata  │   │ 1973 dichiara l'indipendenza │
│ onomastico di Anna           │   │      dal Portogallo          │
└──────────────────────────────┘   └──────────────────────────────┘

 nati e morti
┌──────────────────────────────┐
│ NATI E MORTI                 │
│ * 1791  Michael Faraday      │
│ + 1989  Irving Berlin        │
└──────────────────────────────┘
```

La **prima** è tutta roba da calendario e sta dentro il programma: santo,
nomi che festeggiano, giornata mondiale. Non chiede niente a nessuno, e
funziona con il wifi staccato.

Le altre due arrivano da Wikipedia, e sono l'unica parte che dipende dalla
rete. Sono anche le uniche che possono sparire senza fare danno: se non c'è
niente da raccontare non si fanno, e il turno si accorcia. **Si accorcia, non
si rompe** — è il motivo vero della divisione, l'estetica viene dopo.

**Due schermate per volta, non tre.** Il calendario c'è sempre, e dietro di
lui si alternano i fatti storici e i personaggi: un passaggio l'uno, un
passaggio l'altro. Tre di fila sarebbero oltre venti secondi di pannello per
un servizio che non serve a niente, e due comparse di fila direbbero sempre la
stessa cosa. Sei secondi per le schermate brevi e **dieci per i fatti
storici**, che sono due righe da leggere: si regolano nella pagina Servizi.

> **Un difetto che si vedeva solo guardando il pannello per un pomeriggio.**
> Fino alla 16.1 quell'alternanza non c'era: usciva sempre *accadde oggi* e
> *nati e morti* mai. Chi sceglieva contava le **comparse**, che crescono di
> uno per ogni schermata che va in onda — cioè di **due** a ogni turno, il
> calendario più l'altra. Con due schermate possibili, due modulo due fa
> sempre lo stesso resto. Adesso il conto è sui turni, e *quale* fatto
> raccontare lo decide un terzo conto ancora: quante volte quella schermata si
> è aperta. Sono tre numeri diversi perché contano tre cose diverse, e
> confonderne due è esattamente come è nato il difetto.

## Le righe lunghe scorrono

Due righe della prima schermata le scrive qualcun altro, e sono lunghe quanto
vogliono: il **santo** — *San Basilio Magno e San Gregorio di Nazianzo* — e la
**giornata mondiale**, dove *Giornata contro lo sfruttamento dell'ambiente in
guerra* è un titolo vero, preso dal calendario delle Nazioni Unite.

Fino alla 15.1 finivano con i puntini, cioè mezza riga non si leggeva. Dalla
15.2 **scorrono**, e scorrono in un modo preciso:

1. restano ferme **un secondo**, il tempo di cominciare a leggere;
2. vanno verso sinistra a trenta pixel al secondo — velocità di lettura, non
   di corsa;
3. arrivate all'ultima parola **si fermano lì** e ci restano.

Niente giro infinito. Su una schermata che dura sei secondi un testo che
riparte da capo non si legge mai: ricomincia sempre e viene interrotto sempre
a metà. Fermarsi alla fine vuol dire che l'ultima parola resta sotto gli occhi.

E la schermata **si allunga quanto serve** a vedere lo scorrimento intero: una
riga che scorre per sei secondi dentro una schermata che dura sei secondi è
ancora una riga tagliata, solo in un altro modo. Il tetto resta venti secondi,
perché il servizio è quello che non serve a niente e non può tenersi il
pannello più di così.

Il santo prova prima a rimpicciolirsi — se nel corpo medio ci sta, sta fermo —
e scorre solo quando non basta.

## Quando una foto si prende il pannello a metà

Questo servizio ha **priorità 49** e il Media Player **50**: la foto
successiva gli porta via il pannello, ed è voluto — il turno glielo dà `Turni`
nella pausa fra due foto, non strappandolo a nessuno.

Fino alla 16.1 però l'orologio della schermata correva lo stesso, anche mentre
la schermata non si vedeva. Una schermata lunga interrotta da una foto tornava
indietro con mezzo secondo di vita: un lampo, con lo scorrimento già arrivato
in fondo. Dalla 16.2 **il tempo passato fuori dal pannello non conta**: la
scadenza e lo scorrimento si spostano in avanti dell'intervallo perso, e la
riga riprende da dove era rimasta.

Con un tetto, perché serve: si recupera al massimo un'altra volta la durata.
Senza, un Media Player molto attivo terrebbe viva la stessa schermata per
sempre.

## Il fatto storico invece sale

L'«accadde oggi» non è una riga lunga: è un **paragrafo**. Una frase di
Wikipedia va a capo da sola su quattro o cinque righe, e farla scorrere di
lato vorrebbe dire cinque strisce che si muovono insieme — illeggibile. Fino
alla 15.2 veniva impaginata su tre righe e il resto finiva con i puntini, e
quelle tre righe erano decise dall'altezza del pannello, non dal fatto.

Dalla 15.3 il testo si impagina **quanto è lungo** e la colonna **sale**, come
i titoli di coda. Chiesto così: *dovrebbe scorrere verso l'alto come la sigla
di Guerre Stellari, e dovrebbe esserci qualche secondo di pausa alla fine, per
permetterne la lettura.*

Due numeri diversi da quelli dello scorrimento di lato, e per forza:

- **dodici pixel al secondo** invece di trenta. Di lato si inseguono le
  lettere, in verticale si leggono righe intere: a questa velocità una riga
  alta quattordici pixel resta leggibile per più di un secondo mentre sale;
- **tre secondi di pausa in cima** invece di uno. Quando la salita si ferma,
  le ultime righe sono appena arrivate e sono proprio quelle che nessuno ha
  ancora letto.

Il titolo *ACCADDE OGGI* e l'anno grande a sinistra **non si muovono**: sono
il punto fermo da cui si legge, e sale soltanto la colonna del testo. Un
pannello in cui si muove tutto non si legge.

Si impaginano al massimo **dodici righe**. Non è un troncamento travestito —
un fatto storico di dodici righe non esiste — è che una pagina di Wikipedia
malformata non deve produrre una salita di tre minuti dentro un tetto di
venti secondi, che sarebbe di nuovo un testo tagliato.

# 3. La riga che fa fare una telefonata

In fondo alla prima schermata, quando capita, c'è **l'onomastico dei tuoi**:
i nomi del giorno confrontati con quelli della lista dei compleanni. Se oggi
è l'onomastico di qualcuno che conosci, il pannello scrive *onomastico di
Anna*, in verde, e quella riga prende il posto della giornata mondiale —
chi conosci viene prima del mondo.

Il confronto è **locale**: legge `compleanni.csv`, non manda niente in giro,
e funziona anche dentro una voce scritta come «Anna e Luca». Maiuscole e
accenti non contano.

Quando in fondo non c'è niente — capita circa un giorno su due — la schermata
respira: il santo e i nomi scendono al centro invece di lasciare mezzo
pannello vuoto.

# 4. Da dove vengono i dati

| Cosa | Dove sta | Rete |
|---|---|---|
| Santo del giorno | `santi.csv`, 366 giorni | no |
| Nomi che festeggiano | `santi.csv` | no |
| Giornata mondiale | `giornate.csv`, 390 voci in 360 giorni | no |
| Onomastico dei tuoi | `compleanni.csv` | no |
| Fatti storici di oggi | Wikipedia: feed *on this day*, o la pagina del giorno | sì |
| Nati e morti famosi | Wikipedia, API *on this day* | sì |

I due CSV sono stati compilati dalle pagine giorno per giorno di
[Cathopedia](https://it.cathopedia.org) per i santi, dagli elenchi degli
onomastici per i nomi, e dal calendario delle Giornate internazionali delle
Nazioni Unite per le giornate, con l'aggiunta delle ricorrenze civili
italiane. Sono calendari: non cambiano, quindi stanno nel programma invece di
essere chiesti a un servizio.

Quando un giorno ha **più** giornate mondiali — il 21 marzo ne ha cinque — il
pannello mostra la più corta. Nella pratica è quasi sempre anche la più nota:
*Giornata mondiale della poesia* contro *Giornata internazionale per
l'eliminazione della discriminazione razziale*.

## Perché la riga in fondo era quasi sempre vuota

Il calendario delle Nazioni Unite copre **179 giorni su 366**. Vuol dire che
più di un giorno su due non aveva niente da dire lì in fondo, e a guardare il
pannello sembrava un guasto: non lo era, era una tabella che finiva.

Dalla 12.3 ci sono anche le giornate **minori e goliardiche** — il gatto nero
il 17 agosto, la Nutella il 5 febbraio, il parlare come un pirata il 19
settembre, Festivus il 23 dicembre — e i giorni coperti passano a **360**. Le
sei date che restano vuote sono quelle in cui il santo dice già tutto: Natale,
Santo Stefano, San Nicola, Santa Cecilia, San Silvestro; più il 9 luglio e il
7 agosto, dove davvero non risulta niente a data fissa.

Le goliardiche portano `pop` in terza colonna e valgono **solo dove non c'è
niente di ufficiale**: il 21 marzo passa la poesia, non il panda. Vale anche
la regola di prima — a parità, la più corta.

Sono tutte a **data fissa**. Quelle che si spostano — la giornata del sonno,
il venerdì prima dell'equinozio; la giornata della neve, la terza domenica di
gennaio — sono state scartate: qui si guarda il calendario, non il giorno
della settimana.

**Le tue giornate.** Chi ne vuole aggiungere di sue — l'anniversario di
qualcosa, la giornata di qualcuno — mette un `giornate.csv` nella cartella
dati (`/var/lib/dmd`), con lo stesso formato `MM-GG;titolo`. Viene letto dopo
quello del programma e si aggiunge, non lo sostituisce. Scritte in due colonne
valgono **ufficiali**, quindi vincono sulle nostre goliardiche: è la stessa
regola delle tabelle del radar, le tue prima.

# 5. I fatti storici

Vengono dalla stessa API, sezione *selected* ed *events*, **in italiano**:
quella sezione su it.wikipedia esiste — è la stessa del riquadro «Accadde
oggi» della pagina principale — al contrario di nati e morti, che lì sono
vuoti.

Se il feed non rispondesse, si legge direttamente la **pagina del giorno** di
Wikipedia — «24 settembre» — e se ne prende la sezione *Eventi*. Quella pagina
c'è sempre, quindi i fatti arrivano in un modo o nell'altro. Il testo viene
ripulito di template, note e collegamenti, e si tiene la prima frase: sul
pannello la seconda non ci starebbe, e tagliata a metà farebbe peggio che non
esserci.

Si tengono gli otto fatti più recenti — sono quelli che uno ha sentito
nominare — e a ogni passaggio ne compare uno, a rotazione. L'anno sta grande a
sinistra, il fatto a destra: se ci sta è fermo, se è più lungo **sale**, come
spiegato nel capitolo 2.

# 6. I personaggi famosi

Vengono dall'API pubblica *on this day* di Wikipedia: gratuita, senza chiave,
come Open-Meteo per il meteo e le ADS-B per gli aerei.

**Il feed italiano non ha nati e morti.** Risponde regolarmente, ma con una
lista vuota, per tutti i giorni dell'anno: quelle due sezioni su it.wikipedia
non esistono. È il motivo per cui nella 11.4 la seconda schermata non
compariva mai — la chiamata riusciva, e non tornava niente. Dalla 11.6 si
chiede prima all'italiano (se un giorno lo riempiranno, è suo) e poi
all'inglese, e i nomi si **traducono**: i titoli inglesi passano da
`langlinks`, che dà il titolo italiano quando la voce c'è anche da noi —
*Charles the Bald* diventa *Carlo il Calvo* — e le descrizioni brevi si
prendono in italiano. In tutto sei richieste al giorno.

Si chiede **una volta al giorno** e si tiene in cache, quindi:

- se la rete cade dopo, il pannello continua a mostrare quelli di oggi;
- se la rete manca del tutto, la seconda schermata non compare e basta;
- se la rete torna, alla mezz'ora dopo c'è di nuovo tutto.

Si prendono i sei nati e i sei morti più recenti — sono quelli che uno
riconosce — e a ogni passaggio ne compare uno per tipo, a rotazione: due
passaggi di fila non dicono la stessa cosa.

I **morti** hanno la loro casella, e non è pro forma: su un pannello in cucina
possono essere lugubri. Spenti, la seconda schermata mostra due nati e resta
piena.

# 7. Nella pagina Servizi

Tre caselle e un numero:

| Comando | Cosa fa |
|---|---|
| **Santo, onomastici e giornata mondiale** | la prima schermata |
| **Fatti storici di oggi** | la schermata «Accadde oggi» |
| **Personaggi famosi nati e morti oggi** | la seconda; è quella che vuole internet |
| **Mostra anche i morti** | dentro la seconda |
| **Secondi per schermata** | da 3 a 30, sei di serie |
| **Secondi per i fatti storici** | da 3 a 30, dieci di serie: sono due righe da leggere |

E tre pulsanti di prova, uno per schermata, per vederle subito sul pannello.

# 8. In Home Assistant

Oltre all'interruttore del servizio (`switch.dmd_inutili`), sette sensori —
dalla 15.1 esce **tutto** quello che il pannello sa di oggi, non più metà:

| Entità | Contenuto |
|---|---|
| `sensor.dmd_inutili_santo` | il santo del giorno; negli attributi c'è tutto il resto |
| `sensor.dmd_inutili_onomastici` | **i tuoi**, se oggi ne festeggia uno; altrimenti i nomi del giorno |
| `sensor.dmd_inutili_tuoi` | solo i tuoi, su un sensore loro |
| `sensor.dmd_inutili_giornata` | la giornata mondiale, vuoto se non ce n'è |
| `sensor.dmd_inutili_giornate` | quante ne cadono oggi; l'elenco negli attributi |
| `sensor.dmd_inutili_accadde` | il primo «accadde oggi», già in forma di frase |
| `sensor.dmd_inutili_nati` | il primo nato di oggi; morti ed eventi negli attributi |

`sensor.dmd_inutili_tuoi` è quello su cui vale la pena scrivere
un'automazione che *fa* qualcosa: un promemoria per telefonare a chi
festeggia. Gli altri servono all'annuncio della mattina.

> **Perché lo stato è corto e l'elenco sta negli attributi.** Lo stato di un
> sensore di Home Assistant si ferma a 255 caratteri, e un «accadde oggi» di
> trecento non accorcia l'entità: la fa **sparire**. Quindi nello stato c'è la
> riga da leggere a voce, e in `attributes` ci sono eventi, nati, morti e
> giornate per intero.

# 9. Come è stato provato

`test_inutili.py`, 153 controlli. I sei che contano davvero:

- **il calendario è completo**: 366 giorni, 29 febbraio compreso, nessun
  giorno senza nomi, nessun santo oltre i 48 caratteri e nessuna giornata
  oltre i 60 — il CSV resta ragionevole anche ora che le righe lunghe
  scorrono;
- **la riga che scorre si muove davvero**: non basta provare il calcolo dello
  scorrimento, si chiede al servizio due fotogrammi di seguito e si verifica
  che siano diversi. Il servizio disegna una volta per turno e di solito
  risponde *niente di nuovo*: con quel «niente di nuovo» la riga più bella del
  mondo resterebbe ferma sul vetro;
- **mentre il fatto storico sale, il titolo e l'anno non si muovono**: si
  confrontano i pixel del primo fotogramma con quelli dell'ultimo nella fascia
  del titolo e nella colonna dell'anno, e devono essere identici. È la
  differenza fra una colonna che scorre e un pannello che trema;
- **le due schermate di coda si alternano davvero**: si fanno girare sei turni
  di fila e si pretende di vedere sia i fatti storici sia i personaggi, con
  fatti diversi ogni volta. È la prova che mancava, ed è il motivo per cui il
  difetto è sopravvissuto a tre versioni;
- **il tempo di una schermata conta quando si vede**: si simula il Media
  Player che porta via il pannello per sei secondi e si verifica che la
  scadenza e la salita si spostino dello stesso intervallo — e che oltre il
  tetto la schermata si chiuda invece di restare appesa;
- **senza rete il servizio si accorcia**: con la cache vuota resta una sola
  schermata, e quello che era già stato scaricato non viene cancellato da un
  errore di rete;
- **il turno arriva attaccato al meteo**: appena la finestra del meteo si
  chiude, il pannello passa a Info inutili, e le due schermate si fanno una
  dopo l'altra. Con il servizio spento, il meteo chiude e basta.

Una schermata costa poco più di un millisecondo, e **si disegna una volta per
turno**: non trenta volte al secondo come un gioco. Questo non è cambiato con
lo scorrimento — il disegno resta uno, e quello che si ripete trenta volte al
secondo è solo ricopiarlo e spostare la finestra della riga che scorre. Le
schermate senza righe lunghe continuano a rispondere *niente di nuovo* e a non
costare niente.
