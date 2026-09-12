# I satelliti sul pannello

Il DMD avvisa dieci minuti prima che la Stazione Spaziale passi sopra casa, lo
ricorda a cinque, e durante il passaggio mostra **dove guardare**.

Non è un secondo Air Radar. Il radar racconta quello che passa perché è
interessante saperlo; questa sorgente esiste per **farti uscire in terrazzo al
momento giusto**, e da lì discende ogni scelta che trovi in questa pagina.

---

## Che cosa serve

Una sola libreria, per il calcolo orbitale:

```bash
sudo pip3 install sgp4 --break-system-packages
```

Sui Raspberry a 64 bit arriva già compilata e si installa in pochi secondi. Se
manca, il servizio **non fa cadere niente**: lo dice nella riga di stato e
resta spento. L'installazione completa (`install.sh`) la mette da sola;
l'aggiornamento via rete no, perché non esegue lo script di installazione.

Servono anche le **coordinate**, e sono quelle dell'Air Radar: una casa sola,
un posto solo. Se hai già usato il radar sei a posto; altrimenti le imposti
nella pagina *Radar*.

> **Possono essere volutamente imprecise.** Spostare la posizione di 0,1 gradi
> — undici chilometri — cambia gli orari dei passaggi di **due secondi**. È
> misurato, e c'è una prova che lo verifica. Se preferisci non scrivere la tua
> posizione esatta da nessuna parte, arrotondala: non perdi nulla.

---

## Come funziona, in breve

Per gli aerei esiste un servizio che dice *dove sono*. Per i satelliti no: si
scaricano gli **elementi orbitali** — i TLE, due righe di numeri per satellite
— e la posizione **la calcola il Raspberry**, con l'algoritmo SGP4.

Tre conseguenze pratiche, tutte a favore:

- **nessuna chiamata di rete per funzionare.** Gli elementi si scaricano una
  volta ogni sei ore; fra un aggiornamento e l'altro il pannello lavora anche
  con internet giù;
- **gli elementi invecchiano in giorni**, non in minuti, quindi scaricarli di
  rado non peggiora niente;
- CelesTrak, che li pubblica, chiede di non interrogarlo più di una volta
  all'ora e di **fermarsi al primo errore**, pena il blocco dell'indirizzo. Il
  freno è scritto nel codice e non si può aggirare dalla pagina.

---

## Perché parla così poco

In cielo ci sono circa sedicimila oggetti attivi, e in ogni istante qualche
centinaio sta sopra l'orizzonte. Ma a occhio nudo se ne vedono pochissimi, e
solo quando il satellite è illuminato dal Sole **mentre qui è già buio**.

Quella condizione, più la tabella dei pochi oggetti di cui conosciamo davvero
la luminosità, porta sedicimila a **uno o due eventi al giorno**.

Misurato su ventotto giorni, alla latitudine di 45 gradi:

| | al giorno |
|---|---|
| passaggi sopra i 10 gradi | 5,4 |
| di cui **visibili a occhio nudo** | **1,1** |
| passaggi «belli», sopra i 40 gradi | uno ogni 2-3 giorni |

E non sono distribuiti in modo uniforme: ci sono settimane con uno o due
passaggi ogni sera e poi **quattro o cinque giorni di silenzio assoluto**,
quando l'orbita passa solo di giorno o in ombra. Nel 18% dei giorni non c'è
nessun passaggio visibile. Non è un guasto: è l'orbita.

### La magnitudine, e perché è una tabella scritta a mano

I TLE danno l'orbita, non la luminosità. E la fonte pubblica che dava le
magnitudini — i file di Mike McCants, lo standard per vent'anni — **è stata
ritirata e non si aggiorna più**.

Senza magnitudine, «visibile» può voler dire soltanto *illuminato dal Sole
mentre qui è buio* — condizione che un CubeSat da dieci centimetri soddisfa
esattamente come la Stazione Spaziale.

Per questo l'ultimo filtro non è un calcolo ma una **tabella di due righe**:
la Stazione Spaziale Internazionale e quella cinese. Sembra poco ed è il
contrario: lo scopo della sorgente è farti uscire in terrazzo, e annunciare
qualcosa di invisibile non è un'imprecisione — è una promessa mancata.

> Il gruppo *stations* di CelesTrak sembra contenere le stazioni spaziali. In
> realtà ne contiene venti oggetti, per lo più **CubeSat rilasciati dalla
> ISS**: GXIBA-1, KNACKSAT-2, HMU-SAT2. Senza la tabella il pannello avrebbe
> mandato qualcuno a cercare una scatoletta invisibile.

---

## I tre momenti, e i tre colori

Un passaggio visibile genera tre momenti. Il **colore** dice che genere di
evento è, il **lampeggio** dice che sta succedendo adesso: due canali
indipendenti, nessuna ridondanza.

| Quando | Che cosa si vede | Colore | Ora |
|---|---|---|---|
| **T−10 min** | nome, fra quanto, ora di sorgere, dove, quanto sale, per quanto | verde acceso | fissa |
| **T−5 min** | lo stesso, con il conto alla rovescia aggiornato | verde acceso | fissa |
| **dal sorgere al tramonto** | l'arco del cielo con il puntino che si muove | bianco | **lampeggia** |

Il lampeggio va a secondi pari, la stessa fase dei due punti dell'orologio:
due cose che lampeggiano insieme sembrano un battito, due sfasate sembrano un
guasto.

### Come è fatto il preavviso

```
ISS            FRA 5 MIN
SORGE 21:10  O 51° PER 5 MIN
```

Quattro informazioni, e ognuna risponde a una domanda diversa: **chi** passa,
**fra quanto**, **a che ora e dove** guardare, **per quanto** starà lì.

> **Perché il numero grande è il conto alla rovescia e non l'ora.** Fino alla
> 6.1 in alto a destra c'era `21:10`, l'ora di sorgere. Stessa posizione,
> stesso corpo e quasi stesso colore dell'orologio che quel pannello mostra
> tutto il resto del tempo: chi passava in soggiorno leggeva «sono le 21:10»
> e, insieme a «fra 5 min», concludeva che il passaggio fosse alle 21:15.
> Segnalato dal campo, ed era l'unica lettura ragionevole. Adesso il posto
> grande lo prende il conto alla rovescia — l'unica cosa che serva in quel
> momento — e l'ora scende sulla riga piccola con l'etichetta `SORGE`
> davanti, dove non può essere scambiata per altro.

**`PER 5 MIN` è la durata visibile, non quella del passaggio.** Sono due cose
diverse ogni volta che la Stazione entra nell'ombra della Terra prima di
tramontare, e succede spesso. Un caso vero, la sera del 12 settembre: il
passaggio delle 22:48 durava 5,9 minuti sopra l'orizzonte e **quaranta
secondi** prima di sparire. Il pannello scrive `PER 40 S`, perché scrivere
`6 MIN` sarebbe stato un invito a uscire per qualcosa che non c'era più.

### Perché dieci minuti prima

Un passaggio della Stazione dura **fra i due e i sette minuti** — misurati,
non stimati: il migliore possibile, quello che passa sopra la testa, non
arriva a sette. Annunciarlo mentre sta succedendo vuol dire alzarsi, cercare
le scarpe, aprire la portafinestra e trovarsi fuori con metà finestra già
bruciata.

Dieci minuti servono a uscire **prima che sorga**, prenderlo basso
all'orizzonte e seguirlo per tutto l'arco. E servono agli occhi, che dalla
luce di casa al buio ci mettono qualche minuto.

### L'arco

Durante il passaggio il pannello cambia mestiere: non serve più a ricordare,
serve a chi è fuori e sta cercando.

A sinistra il nome, l'ora che lampeggia e l'altezza in questo istante. A
destra **l'arco vero**: l'asse orizzontale è il tragitto da dove sorge a dove
tramonta, quello verticale l'altezza sull'orizzonte, e il puntino sta dove sta
adesso la Stazione. Alzi gli occhi e sai **quanto in alto** guardare — che è
l'informazione che manca sempre quando qualcuno ti dice «guarda, c'è la
Stazione».

### Quando si spegne

Nel **13%** dei passaggi visibili la Stazione non tramonta: entra nell'ombra
della Terra e **sparisce di colpo a metà cielo**, in tre o quattro secondi. È
la cosa più spettacolare che faccia, e chi non se l'aspetta pensa di aver perso
di vista un aereo.

Il pannello lo sa in anticipo. Sull'arco c'è un **taglio** che segna il punto,
e da lì in poi la curva è disegnata in tono minore: da quel momento non c'è più
niente da guardare. Negli ultimi quarantacinque secondi la riga in basso a
sinistra smette di dire quanto è alta e dice **`SPARISCE 21:14`**.

### Il terzo colore: c'è ma non si vede

I passaggi che non si vedono sono **quattro al giorno contro uno**. Mostrarli
cambia il servizio da «parla una volta al giorno» a «parla cinque volte» —
purché resti chiaro che non sono un invito a uscire.

Arrivano in **grigio-azzurro spento**, senza preavviso e senza lampeggio, per
una ventina di secondi attorno al culmine: il momento in cui il puntino sarebbe
più alto e l'arco più bello. La riga in basso dice perché non si vede:
`SOLE +21°` oppure `IN OMBRA`.

Si spegne dalla casella *«Mostra anche i passaggi che non si vedono»*.

---

## La pagina Satelliti

### Elevazione minima

Quanti gradi sopra l'orizzonte perché valga la pena annunciarlo. **Dieci
gradi** vuol dire «sopra i tetti»: più in basso ci sono case, alberi e
foschia.

**Non è un raggio in chilometri**, e non lo si può ragionare come quello del
radar. Per gli aerei, che volano a dieci chilometri, «entro 30 km» vuol dire
più o meno sopra casa. Un satellite sta a quattrocento chilometri:

| Elevazione | Distanza a terra (ISS) |
|---|---|
| orizzonte | 2250 km |
| 10° | 1390 km |
| 30° | 630 km |
| 45° | 383 km |
| 60° | 225 km |

Anche a 60 gradi, quasi allo zenit, la Stazione è a **225 chilometri** da
casa tua.

### Preavviso e cadenza

Con preavviso 10 e cadenza 5 compaiono due promemoria: a T−10 e a T−5. Ogni
promemoria resta a schermo una ventina di secondi e poi lascia lavorare le
altre sorgenti: non è una sorgente che occupa il pannello per un quarto d'ora.

### Famiglie

Le famiglie le pubblica CelesTrak e non le classifichiamo noi. Di
preimpostato c'è solo **stazioni**.

Gli altri gruppi sono selezionabili ma sconsigliati, e *«i cento più
luminosi»* è stato provato e scartato: due terzi di quel gruppo sono **stadi
di razzo esausti** — `SL-16 R/B`, `CZ-2C R/B`, `ARIANE 40+ R/B`. Il dato è
corretto, sono davvero fra gli oggetti più brillanti del cielo, ma quelle
sigle su un pannello in salotto non dicono niente a nessuno, e in una notte
sola riempivano l'elenco con 252 passaggi.

### Anche gli oggetti di luminosità sconosciuta

Sconsigliato, e sta nella pagina per chi vuole sperimentare. Acceso, il
pannello annuncia anche i CubeSat: passaggi veri, oggetti invisibili.

---

## Il registro

In `/var/lib/dmd/satelliti.csv`, scaricabile dalla pagina.

Ci finiscono **tutti** i passaggi a cose fatte, visibili e non, con l'altezza
del Sole accanto. È la colonna che trasforma un elenco in una risposta:

```
sorge,nome,norad,gruppo,durata_min,elevazione_massima,azimut_sorge,azimut_tramonta,magnitudine,visibile,sole_gradi
2024-01-03T11:46:55,ISS,25544,stazioni,6.7,82,OSO,ENE,-3.1,no,21.6
2024-01-03T16:38:23,ISS,25544,stazioni,6.7,83,ONO,ESE,-3.1,si,-8.3
```

Due passaggi quasi identici — 82 e 83 gradi, sei minuti e mezzo ciascuno. Il
primo non l'hai visto perché **il Sole era a 21 gradi**: mezzogiorno. Il
secondo sì, perché era a −8.

Si scrive **a passaggio concluso**, non al momento del calcolo: un passaggio
previsto non è un passaggio avvenuto, e un registro che mescola le due cose
non risponde più a nessuna domanda. È la stessa regola del registro dei voli.

---

## Verificare che gli orari siano giusti

Il modo più solido è confrontarli con una fonte indipendente — Heavens-Above,
o l'app che usi — e poi **uscire a guardare**.

Nella pagina trovi l'elenco dei prossimi passaggi con orario, durata,
elevazione massima e direzioni. Scegline uno sopra i 40 gradi, esci due minuti
prima e cerca dalla parte da cui sorge.

La riconosci subito perché **non lampeggia**: gli aerei hanno luci
intermittenti, la Stazione è un punto bianco fisso che scivola lento e
costante da un orizzonte all'altro.

---

## Priorità sul pannello

I satelliti stanno a **61**, appena sopra l'Air Radar. Il motivo è semplice:
un passaggio ha un **orario** — succede alle 21:10 o non succede più — mentre
un aereo no, ne passa un altro fra cinque minuti.

Sopra ci sono solo l'anteprima della libreria media e ZeDMD; sotto, tutto il
resto. Nessuna priorità pareggia con un'altra, e una prova lo pretende.

---

## Se qualcosa non va

| Sintomo | Causa | Rimedio |
|---|---|---|
| «manca la libreria sgp4» | dipendenza non installata | `sudo pip3 install sgp4 --break-system-packages` |
| «mancano le coordinate» | latitudine e longitudine a zero | si impostano nella pagina *Radar* |
| nessun passaggio in elenco | normale per giorni interi | guarda il registro: i passaggi ci sono, sono solo diurni |
| «nessun elemento orbitale» | il primo scaricamento non è riuscito | riprova fra un'ora: CelesTrak chiede di non insistere, e il servizio gli dà retta |
| il pannello non dice mai niente | la casella dei non visibili è spenta e il periodo è di quelli vuoti | accendi *«Mostra anche i passaggi che non si vedono»* |
