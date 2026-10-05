---
title: "Energia"
subtitle: "Un numero da Home Assistant sotto l'orologio: la potenza di adesso o la carica dell'accumulo"
---

# 1. A cosa serve

Il pannello **non misura niente**. Misurare la casa è il mestiere di Home
Assistant, che ha già l'inverter, il contatore, il Shelly sul quadro e le
automazioni che leggono tutto. Qui arriva il numero **già fatto**, su un topic
MQTT, e il pannello fa l'unica cosa che Home Assistant non sa fare: tenerlo
sotto gli occhi di chi passa in corridoio, senza che nessuno tiri fuori il
telefono.

```
┌────────────────────────────────────────────────────────┐
│ LUN 05/10                                              │
│                                                        │
│                  14:22                                 │
│                                                        │
│ NY 08:22      CASA 1250 W           TOKYO 21:22+       │
└────────────────────────────────────────────────────────┘
      ↑              ↑                       ↑
   un fuso     il numero, al centro      l'altro fuso
```

Il numero sta **al centro della banda** sotto le cifre, quella del World Time.
Il centro è suo e non si sposta: un valore che cambia posto quando cambia una
città non si trova più con la coda dell'occhio, e il senso di averlo lì è
proprio quello — lo si guarda senza leggerlo.

# 2. Due tipi, e non sono la stessa cosa con un'unità diversa

| Tipo | Che cos'è | Come si colora |
|---|---|---|
| **Potenza** | watt, ampere, kW: un valore che deve stare **dentro un intervallo** | verde in mezzo, giallo nelle due fasce di preallarme, rosso e lampeggiante oltre i due estremi |
| **Accumulo** | la percentuale della batteria del fotovoltaico: un valore che **scende** | un semaforo che scende — verde, giallo, rosso — e lampeggia sotto una soglia sua |

Per questo le soglie **non sono le stesse e non si riusano**: la potenza ne ha
quattro, l'accumulo tre. Un solo insieme di soglie per tutti e due avrebbe
voluto dire, nella metà dei casi, campi che non vogliono dire niente — una
«soglia massima» su una batteria che non deve superare il 100%, o una «soglia
gialla in percento» su dei watt.

I numeri dei due tipi stanno in due blocchi separati e **restano dove sono**:
chi prova l'accumulo e torna alla potenza ritrova i suoi watt, non delle
caselle vuote. La pagina mostra solo quelli del tipo scelto.

## Le quattro soglie della potenza

```
   rosso      giallo        verde        giallo      rosso
 ─────────┬───────────┬───────────────┬───────────┬─────────
  lampeggia│          │               │           │lampeggia
         minima   preallarme     preallarme    massima
                   basso           alto
```

**Tutte facoltative**: una casella vuota è una soglia spenta. Chi guarda solo
il picco di consumo mette la massima e lascia il resto in bianco — e il
pannello non si inventa un minimo a zero, che sarebbe un allarme che suona in
casa di qualcuno senza che nessuno l'abbia chiesto.

Il **giallo non lampeggia**: è un avviso, non un allarme. Lampeggia solo il
rosso, perché se lampeggiasse anche il giallo il lampeggio smetterebbe di
voler dire qualcosa.

La soglia stessa è dentro l'allarme: a 3000 W con massima a 3000 il numero è
già rosso. *Al di sopra di questi valori* letto come *arrivato a questi
valori*, che è il modo in cui si guarda un contatore.

## Le tre soglie dell'accumulo

```
  100% ─────────── verde
   50% ─────────── soglia gialla   → da qui in giù giallo
   20% ─────────── soglia rossa    → da qui in giù rosso
   10% ─────────── soglia lampeggio → da qui in giù lampeggia
    0%
```

Il **lampeggio ha la sua soglia**, più in basso del rosso, ed è la differenza
che conta: un accumulo al 18% è rosso e si guarda, al 10% è rosso e *chiama*.
Se quella soglia si lascia vuota, si lampeggia da dove comincia il rosso:
meglio un lampeggio in più che un allarme che non scatta.

# 3. Il World Time si ferma a due località

Con il servizio Energia acceso la banda in fondo mostra **al massimo due**
località, una per lato, e il centro è del numero. Non è solo una questione di
spazio — la riga dell'energia a volte è corta e tre ci starebbero — è che il
centro deve restare suo.

Chi ne ha configurate di più **le vede comunque tutte**, due per volta, con la
rotazione di sempre: rifiutarle sarebbe stato peggio, perché una città
configurata che non compare mai sembra un guasto.

Se l'etichetta è lunga — *FOTOVOLTAICO 12500 W* — ai lati non ci sta nessuno e
la banda è tutta del numero. È una scelta fra un numero leggibile e due città
tagliate a metà.

Il servizio si può spegnere **da Home Assistant** (`switch.dmd_energia`) senza
fermare l'automazione: è il modo giusto per riavere i tre fusi a cena.

# 4. Che cosa si scrive sul topic

Un numero, e basta:

```
mosquitto_pub -t dmd/energia -m 1250
```

Si accettano anche le forme che Home Assistant produce da sé: `1250.4`,
`1250,4` (chi ha formattato il template per gli umani), `1250 W` (lo stato con
l'unità attaccata), e i valori negativi — l'energia che si immette in rete non
è un errore.

Per dire di più, un JSON:

```json
{"valore": 84, "unita": "%", "etichetta": "BATT"}
```

`unita` ed `etichetta` valgono **per quel messaggio**, non per sempre: servono
a chi ha due automazioni che pubblicano cose diverse sullo stesso topic — la
potenza di giorno, l'accumulo di sera — senza toccare la configurazione del
pannello. Il messaggio dopo, se è un numero nudo, torna all'unità configurata.

## Quello che si legge sul pannello

«etichetta valore unità»: **CASA 1250 W**, **BATT 84%**. L'etichetta può
restare vuota. La percentuale sta attaccata al numero e le parole staccate,
come si scrivono in italiano.

# 5. Il valore vecchio diventa due trattini

Passati i minuti della scadenza — cinque di serie — senza sentire niente, al
posto del valore compaiono **due trattini in grigio**:

```
 NY 08:22        CASA -- W          TOKYO 21:22+
```

Un numero fermo da mezz'ora è peggio di nessun numero: ci si fida di un dato
che non esiste più. E non si fa sparire la riga, perché il servizio è acceso e
il pannello deve dire *non mi sta arrivando niente* — che è una informazione,
non un buco. Il grigio spento non si confonde con una misura, e i due trattini
non lampeggiano: il dato non c'è, non c'è niente da allarmare.

Chi vuole il comportamento vecchio mette **zero minuti**: il valore resta per
sempre.

# 6. L'automazione di Home Assistant

Il file pronto è [`ha/dmd_energia.yaml`](ha/dmd_energia.yaml), con quattro
blocchi: la potenza, l'accumulo, i due a turno (giorno e sera) e uno script di
prova. Ne serve **uno**.

La cosa che conta, e che vale per qualunque automazione si scriva a mano:

> **Non pubblicare trenta volte al minuto.** Un sensore di potenza cambia a
> ogni lettura, cioè ogni due secondi. Un `platform: state` nudo
> pubblicherebbe ogni due secondi per sempre: traffico inutile sul broker e un
> numero che balla sul pannello, perché 1250 e 1248 sono lo stesso dato
> scritto due volte. I blocchi pronti usano `time_pattern` — mezzo minuto per
> la potenza, cinque minuti per l'accumulo — più una pubblicazione all'avvio di
> Home Assistant, altrimenti dopo un riavvio il pannello resta con i due
> trattini fino al prossimo giro.

L'altra: **un sensore non disponibile non si pubblica**. Meglio che il DMD
mostri i due trattini, che vogliono dire «non lo so», di uno zero inventato
dall'automazione.

# 7. Il pulsante di prova

Nella pagina Energia c'è una casella e un pulsante **Mostralo**: ci si scrive
un numero e compare sul pannello subito, come se fosse arrivato dal broker.

Serve davvero, e non è un lusso: fra «ho scritto le soglie» e «il numero
lampeggia come volevo» c'è di mezzo un'automazione che magari non esiste
ancora, e tarare la soglia del lampeggio aspettando che la batteria scenda
davvero al 10% è un'altra cosa che chiedere al pannello di farlo vedere
adesso.

# 8. Se il numero non compare

La riga di stato nella pagina Servizi dice **cosa è arrivato**, non «acceso»,
e basta a capire da che parte sta il problema:

| Dice | Vuol dire |
|---|---|
| *non è ancora arrivato niente sul topic* | il problema è in Home Assistant: prova lo script del blocco D |
| *ultimo valore di N minuti fa* | l'automazione ha pubblicato una volta e poi ha smesso: guarda le sue tracce |
| *Sul pannello: CASA 1250 W* | tutto funziona; se non lo vedi, il servizio è spento o il pannello mostra un'altra sorgente |

Le altre due cose da controllare sono sempre le stesse: il **topic** è lo
stesso nei due posti, e il servizio è **acceso** (pagina Servizi, o
`switch.dmd_energia`).

# 9. Come è stato provato

`test_energia.py`, 104 controlli. I cinque che contano davvero:

- **le soglie dei due tipi restano separate**: si scrive la potenza, si passa
  all'accumulo, si torna indietro, e i watt sono dove erano. È la metà del
  motivo per cui esistono due blocchi invece di uno;
- **una casella vuota resta vuota**, non diventa zero: con la minima non
  scritta un valore negativo resta verde invece di far lampeggiare il pannello
  di notte;
- **il numero è al centro del pannello entro tre pixel**, e le due località
  sono appoggiate ai due bordi senza uscire;
- **le cifre dell'ora si alzano anche con il solo servizio Energia acceso**, e
  si alzano esattamente di quanto si alzavano per il World Time: la banda
  esiste perché c'è qualcosa dentro, non perché c'è il World Time;
- **il lampeggio si vede**: si chiedono all'orologio il fotogramma del secondo
  pari e quello del dispari e devono essere diversi — e con un valore
  tranquillo devono essere identici, altrimenti si riscriverebbe la matrice
  trenta volte al secondo per niente.
