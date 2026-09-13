---
title: "DMD — Meteo"
subtitle: "Il bollettino del mattino, l'aggiornamento ogni poche ore, e perché l'allerta della Protezione Civile non c'è ancora"
---

# Meteo

Due finestre, non una, e la differenza non è la quantità di dati ma **a che
domanda rispondono**.

Il **bollettino del mattino** risponde a *come mi vesto, esco a piedi o prendo
la macchina*. Si guarda una volta, a colazione, e deve dire la giornata
intera: massima, minima, umidità, che tempo farà. È il momento in cui il
pannello somiglia di più a un notiziario.

L'**aggiornamento** risponde a *adesso*. Meno numeri, più grandi: quanti gradi
fa in questo istante e l'icona. Massima e minima restano, piccole, di contorno.

## Perché non è sempre acceso

Un pannello che mostra il meteo tutto il giorno smette di essere guardato dopo
due giorni: diventa sfondo. Una finestra che compare quattro volte al giorno e
poi se ne va, invece, la si legge. È la stessa ragione per cui i Compleanni e
le Scadenze parlano poco.

E non prende mai il pannello a forza. Il meteo non è urgente: nessuno deve
sapere la temperatura *adesso* al punto da interrompere una partita o il
passaggio della Stazione Spaziale. Priorità **54** — sopra il Media Player e
la Funcam, sotto il Rolling Banner, molto sotto il radar. Fra due cose non
urgenti ha la precedenza quella che una persona ha scritto apposta.

## Da dove arrivano i numeri

Da **Open-Meteo**, e la scelta non è casuale fra i tanti servizi possibili.

**Non vuole una chiave.** Non è una comodità, è una proprietà di sicurezza:
non c'è nessun segreto da custodire sul Raspberry, niente da togliere dalla
configurazione esportata, niente che possa finire in una schermata o in un
registro. Tutti gli altri problemi di riservatezza di questo progetto sono
stati risolti *togliendo* cose — le coordinate dal codice, la password dal
file esportato, i token in un file a parte con i permessi stretti. Qui non c'è
proprio niente da togliere.

**Diecimila chiamate al giorno** per uso non commerciale. Ne servono sette.

**Le coordinate sono già quelle del DMD.** Non se ne chiedono di nuove, e non
ne esistono di scritte nel codice: la posizione vera vive soltanto nella
configurazione locale, come per gli aerei e per i satelliti. Se non è stata
messa, il meteo non chiede niente a nessuno e lo dice.

Dalla 7.0 sta in **Impostazioni** e non più nella pagina Radar: la usano in
tre, e tenerla lì la faceva sembrare una preferenza del radar — chi accendeva i
satelliti la cercava nella pagina sbagliata.

Una nota su cosa si riceve: Open-Meteo lavora su una griglia, quindi la
risposta arriva con le coordinate del riquadro più vicino, non con le tue. Non
è un errore ed è giusto che si veda: la previsione è della zona, non del
giardino.

## Che cosa si vede

Le due finestre hanno lo stesso impianto, e non è pigrizia: la prima cosa che
si guarda è sempre la stessa — **quanti gradi fa** — e cambia il contorno, non
la risposta alla prima domanda.

| | Bollettino del mattino | Aggiornamento |
|---|---|---|
| a sinistra | icona | icona |
| in alto a sinistra | `OGGI` e che tempo farà | che tempo fa adesso |
| in alto a destra | ▲ **massima** ▼ **minima** | ▲ **massima** ▼ **minima** |
| **in mezzo, grande** | **temperatura adesso** e umidità | **temperatura adesso** e umidità |
| in basso | probabilità di pioggia, alba e tramonto | temperatura percepita, se diversa |

I due numeri della giornata hanno due colori opposti e si riconoscono senza
leggere l'etichetta: il caldo è ambra, il freddo azzurro. È la stessa grammatica
dell'orologio — ora ambra, data azzurra — quindi il pannello resta coerente con
se stesso. Le frecce sono **disegnate**, non scritte: i caratteri di freccia
esistono ma non tutti i font li hanno, e una freccia che diventa un rettangolo
vuoto è peggio di nessuna freccia.

L'unità si scrive **una volta sola**, sul numero grande: ripeterla accanto a
massima e minima riempirebbe la riga di lettere invece che di numeri, e nessuno
cambia scala fra una riga e l'altra.

L'umidità sta accanto alla temperatura e non in fondo, perché è un numero che
si legge *insieme* a quella: ventisei gradi con il settanta per cento sono
un'altra giornata rispetto a ventisei asciutti.

La probabilità di pioggia compare **solo se c'è**. Uno zero per cento non è
un'informazione, è rumore. Lo stesso vale per la temperatura percepita: si
scrive solo quando si discosta di almeno un grado e mezzo da quella vera —
«18 gradi, percepiti 18» è una riga sprecata, mentre con vento o afa quella
differenza è il motivo per cui uno si mette la giacca.

### Celsius o Fahrenheit

Si sceglie nella scheda del Meteo. Le previsioni si chiedono **sempre** in
Celsius e si convertono al momento di scrivere: così cambiare unità non
invalida la previsione già scaricata, e non costa una chiamata in più. Su MQTT
esce comunque Celsius, che è quello che Home Assistant sa riconvertire da solo
secondo le impostazioni di chi guarda.

### Il puntino in alto a destra

Se compare, la previsione è vecchia di più di tre ore: quasi sempre vuol dire
che è caduta la rete. Serve a distinguere *fa diciotto gradi* da *faceva
diciotto gradi stamattina*. Non c'è una frase perché chi guarda di sfuggita non
la leggerebbe; chi nota il puntino va a vedere la pagina Servizi, dove c'è
scritto per esteso da quanti minuti è fermo il dato.

## Le icone

Sono **disegnate**, non caricate da file. A una trentina di pixel un PNG
scalato diventa una poltiglia: le forme si riconoscono per i bordi, e i bordi a
trenta pixel sono due o tre pixel. Disegnarle con cerchi e linee vuol dire che
ogni pixel è dove volevamo, che la dimensione si cambia con un numero, e che il
pacchetto non pesa un byte in più.

Le icone sono **meno dei codici meteo**, ed è voluto: a quella dimensione la
differenza fra pioviggine moderata e pioviggine intensa non si può disegnare, e
due icone identiche con due nomi diversi sarebbero una bugia grafica. La
differenza la dice il testo, che di spazio ne ha.

Di notte cambia una cosa sola, ed è l'unica che cambi davvero: con il cielo
sereno si disegna la Luna invece del Sole. Una nuvola di notte resta una
nuvola.

## In Home Assistant

Cinque entità, e nessuna è un doppione di quello che Home Assistant sa già:
chi ha una stazione meteo in giardino ha il dato **misurato** in un punto,
questo è quello **previsto** per le prossime ore — la cosa su cui si
costruiscono le automazioni, come chiudere la tapparella prima del temporale e
non dopo.

| Entità | Contenuto |
|---|---|
| `sensor…meteo_temperatura` | la temperatura adesso |
| `sensor…meteo_umidita` | l'umidità adesso |
| `sensor…meteo_massima` | la massima prevista per oggi |
| `sensor…meteo_minima` | la minima prevista per oggi |
| `sensor…meteo_condizione` | che tempo fa, a parole, con tutto il resto negli attributi |

## Le allerte

### Come si è scelta la fonte

Merita due righe, perché è l'esempio più pulito di una regola di questo
progetto: **quando la documentazione non basta, si misura.**

Sulla carta le strade erano tre e tutte incerte. MeteoAlarm risultava aver
dismesso il feed RSS, lo standard di fatto per le allerte europee. Il suo
successore, MeteoGate di EUMETNET, non documentava se le allerte fossero
accessibili senza registrarsi. E il repository ufficiale del Dipartimento della
Protezione Civile — che pubblica ogni giorno entro le 16:00 il bollettino sulle
156 zone di allerta, con licenza CC-BY — dichiarava sé stesso *«Repository in
fase di caricamento»* con la sezione sul formato dei dati vuota.

La scelta era fra indovinare e chiedere. Si è chiesto: tre `curl` dal
Raspberry, che ha la rete libera.

| Sonda | Risposta |
|---|---|
| feed legacy MeteoAlarm per l'Italia | **200** — è vivo |
| API EDR interrogata per posizione | **Not Found** — quella strada è chiusa |
| Open-Meteo | risponde, e con un errore JSON pulito sulle coordinate finte |

Nessuna delle prime due cose si poteva sapere leggendo la documentazione.

### Che cosa arriva

Un feed Atom con dentro **CAP 1.2**, lo standard con cui le protezioni civili
di mezzo mondo pubblicano le allerte. Per l'Italia MeteoAlarm raccoglie quelle
della Protezione Civile. Ogni avviso porta il codice della zona (`IT018`), il
nome in chiaro (`Sicilia`), il tipo di evento, la **gravità** normalizzata
(`Moderate`, `Severe`, `Extreme` → giallo, arancione, rosso) e gli orari di
inizio e scadenza.

### Come si vede

L'avviso prende **tutto il pannello**: barra colorata a sinistra, triangolo di
pericolo, il tipo di evento e quando. Non è una scelta grafica: una striscia in
cima al bollettino si legge come un'etichetta, un pannello intero si legge come
un avviso, e chi passa in corridoio deve capire che c'è qualcosa *prima* di
aver letto una parola.

Compare **quando arriva**, non al prossimo giro delle quattro ore. Poi non si
ripete: vive in una tacca colorata nell'angolo delle altre finestre. Un avviso
che ricompare ogni minuto smette di essere un avviso in mezza giornata.

Quando la riga in basso non ci sta tutta, la prima cosa che si toglie è il nome
della regione — questo pannello mostra solo le allerte della regione che hai
scelto tu, quindi quel nome è l'unica parte che non aggiunge niente. Il
**quando** resta sempre.

### La regione si sceglie a mano

Il feed copre il paese intero e divide per regione. Per sapere qual è la tua
servirebbe trasformare le coordinate in una regione, cioè portarsi dietro i
confini amministrativi — megabyte di poligoni per rispondere a una domanda che
tu sai già.

Quindi si sceglie da una tendina, una volta. E **senza regione non si mostra
niente** — non tutto: far comparire l'allerta della Sicilia a chi sta in
Piemonte non è un'approssimazione, è un allarme falso.

Il confronto è sul nome ed è tollerante ad accenti, maiuscole e apostrofi,
perché `Valle d'Aosta`, `Valle d’Aosta` e `valle daosta` sono la stessa cosa
per chiunque tranne che per un confronto fra stringhe. Ma è tollerante **in un
verso solo**: la regione scelta dev'essere l'inizio del nome della zona. Così
`Piemonte` trova anche `Piemonte e Valle d'Aosta`, mentre `Aosta` da sola non
cattura `Valle d'Aosta` — che è esattamente il difetto che la prima versione
aveva, trovato dalla suite: una regione che riceve gli avvisi di un'altra.

### Quello che non si mostra

Conta quanto quello che si mostra:

- gli avvisi **scaduti**. Un avviso vecchio sul pannello è peggio di nessun
  avviso, perché insegna a non fidarsi — e dopo quello il pannello non serve
  più a niente;
- quelli **annullati** (`message_type: Cancel`);
- le **prove di sistema** (`Test`, `Exercise`), che esistono nello standard CAP
  proprio perché chi le riceve non le mostri. Mostrarle sarebbe il peggiore
  degli allarmi falsi: indistinguibile da uno vero.

C'è invece un **preavviso**: un avviso che comincia entro dodici ore si vede
già. Sapere stasera che domattina ci sarà un temporale è utile; saperlo mentre
grandina non lo è.

### In Home Assistant

`sensor…meteo_allerta` ha come stato il **livello** — `giallo`, `arancione`,
`rosso` — e non il testo, perché è la parola su cui si scrive una condizione in
un'automazione ed è normalizzata. Il testo, la zona e gli orari stanno negli
attributi, dove servono a chi legge e non a chi decide.

È l'unica entità meteo per cui valga davvero la pena scrivere un'automazione
che *fa* qualcosa invece di mostrare un numero: chiudere una tapparella,
spegnere l'irrigazione, mandare un messaggio a chi è fuori.

## Configurazione

Sta nella pagina **Servizi**, nella scheda del Meteo, e sono due numeri:

- **ora del bollettino del mattino** — sette è l'ora della colazione; chi si
  alza alle cinque la sposta;
- **aggiornamento ogni quante ore** — quattro vuol dire cinque o sei finestre
  al giorno.

Due pulsanti fanno comparire subito le due finestre sul pannello: vale la
stessa ragione del pulsante di prova delle notifiche, cioè che senza un modo di
chiamarla a comando l'unico modo di sapere se il bollettino funziona sarebbe
aspettare le sette del mattino.

## Quando qualcosa non va

| Cosa si vede | Che cosa vuol dire |
|---|---|
| «nessuna posizione» nella riga di stato | la pagina Radar è a zero: il meteo prende da lì le coordinate |
| il puntino in alto a destra | la previsione è vecchia di più di tre ore, quasi sempre rete giù |
| la finestra non compare mai | il servizio è spento nella pagina Servizi, oppure un'altra sorgente con priorità più alta sta occupando il pannello |
| «previsione non aggiornata» | il motivo è scritto per esteso di fianco |

Una risposta mutilata dal servizio — colonne mancanti, valori nulli, campi
rinominati — produce un bollettino con **meno numeri**, non un errore: il
giorno in cui Open-Meteo cambia il nome di una colonna deve sparire quella
riga, non il pannello.
