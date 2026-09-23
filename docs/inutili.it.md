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

# 2. Due schermate, e non è estetica

```
 schermata 1                                schermata 2
┌──────────────────────────────┐   ┌──────────────────────────────┐
│ 22 SETTEMBRE                 │   │ ACCADDE OGGI                 │
│ San Maurizio                 │   │ * 1791  Michael Faraday      │
│ Maurizio · Silvano · Tazio   │   │ + 1989  Irving Berlin        │
│ onomastico di Anna           │   └──────────────────────────────┘
└──────────────────────────────┘
```

La **prima** è tutta roba da calendario e sta dentro il programma: santo,
nomi che festeggiano, giornata mondiale. Non chiede niente a nessuno, e
funziona con il wifi staccato.

La **seconda** arriva da Wikipedia, ed è l'unica parte che dipende dalla rete.
È anche l'unica che può sparire senza fare danno: se non c'è niente da
raccontare, la seconda schermata non si fa e il turno dura la metà. **Si
accorcia, non si rompe** — è il motivo vero della divisione, l'estetica viene
dopo.

Sei secondi per schermata di serie, regolabili nella pagina Servizi.

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
| Giornata mondiale | `giornate.csv`, 209 voci in 179 giorni | no |
| Onomastico dei tuoi | `compleanni.csv` | no |
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

**Le tue giornate.** Chi ne vuole aggiungere di sue — la giornata mondiale
del gatto, l'anniversario di qualcosa — mette un `giornate.csv` nella cartella
dati (`/var/lib/dmd`), con lo stesso formato `MM-GG;titolo`. Viene letto dopo
quello del programma e si aggiunge, non lo sostituisce.

# 5. I personaggi famosi

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

# 6. Nella pagina Servizi

Tre caselle e un numero:

| Comando | Cosa fa |
|---|---|
| **Santo, onomastici e giornata mondiale** | la prima schermata |
| **Personaggi famosi nati e morti oggi** | la seconda; è quella che vuole internet |
| **Mostra anche i morti** | dentro la seconda |
| **Secondi per schermata** | da 3 a 30, sei di serie |

E due pulsanti di prova, uno per schermata, per vederle subito sul pannello.

# 7. In Home Assistant

Oltre all'interruttore del servizio (`switch.dmd_inutili`), tre sensori:

| Entità | Contenuto |
|---|---|
| `sensor.dmd_inutili_santo` | il santo del giorno; negli attributi c'è tutto il resto, personaggi compresi |
| `sensor.dmd_inutili_onomastici` | **i tuoi**, se oggi ne festeggia uno; altrimenti i nomi del giorno |
| `sensor.dmd_inutili_giornata` | la giornata mondiale, vuoto se non ce n'è |

Il secondo è l'unico su cui valga la pena scrivere un'automazione che *fa*
qualcosa: un promemoria per telefonare a chi festeggia.

# 8. Come è stato provato

`test_inutili.py`, 84 controlli. I tre che contano davvero:

- **il calendario è completo**: 366 giorni, 29 febbraio compreso, nessun
  giorno senza nomi, nessun santo troppo lungo per il pannello;
- **senza rete il servizio si accorcia**: con la cache vuota resta una sola
  schermata, e quello che era già stato scaricato non viene cancellato da un
  errore di rete;
- **il turno arriva attaccato al meteo**: appena la finestra del meteo si
  chiude, il pannello passa a Info inutili, e le due schermate si fanno una
  dopo l'altra. Con il servizio spento, il meteo chiude e basta.

Una schermata costa poco più di un millisecondo, e si disegna una volta per
turno: non trenta volte al secondo come un gioco.
