# Changelog

Tutte le modifiche rilevanti del progetto.

## [9.12]

### Un colore diverso a ogni ora

Nella pagina **Orologio**, accanto al colore dell'ora: *Colore casuale,
diverso a ogni ora*. Spento di serie. Accanto compare il colore toccato
all'ora in corso, e l'anteprima lo usa.

Tre scelte, e ognuna viene da un modo in cui la versione ingenua sbaglia:

- **si sceglie la tinta, non i tre canali.** Tre numeri a caso fra 50 e 255
  rispettano il limite e danno quasi sempre un grigio. Qui la luminosità è
  sempre piena — un canale a 255, quindi mai scuro — e la saturazione sta fra
  0,55 e 0,80: il canale più basso vale almeno 51, **sopra 50 per
  costruzione**. Provato su tutte le 8784 ore di un anno: il più basso uscito
  è 51, e i grigi sono zero;
- **il colore dipende dall'ora, non da un dado lanciato allo scoccare.** È lo
  stesso per tutta l'ora, e un riavvio a metà non lo cambia;
- **due ore di fila non si assomigliano mai.** Ogni ora la tinta avanza
  dell'angolo aureo, 137,5 gradi, con una deviazione a caso: fra un'ora e la
  successiva il salto sta sempre fra 98 e 177 gradi, anche a mezzanotte.

Il colore scelto a mano non si perde: spegnendo il casuale si ritrova.

### Tre fusi insieme, anche di notte

«SEATTLE TOKYO NEW YORK» stava in 245 pixel su 254 **finché le tre città
erano nello stesso giorno di Roma**. Ogni città su un altro giorno aggiunge il
suo `+` o `−`, sei pixel, e con due segni si arrivava a 257. Di notte Seattle
e New York sono ancora a ieri: la banda passava da tre città insieme a due
che si alternano, e al mattino tornava a tre.

Due correzioni. Il nome e l'ora stanno a **3 pixel** invece di uno spazio
intero — sono già di due colori diversi — e fra una città e l'altra ne
restano almeno **6** invece di 8. E il posto del segno si tiene **sempre**,
anche quando il segno non c'è, così il conto di quante città entrano dà lo
stesso numero a mezzogiorno e a mezzanotte.

Quante ne stanno insieme, con le etichette:

| Città insieme | Etichette, in tutto |
|---|---|
| 2 | sempre (fino a 14 caratteri l'una) |
| 3 | fino a **20** caratteri |
| 4 | fino a 13 caratteri |

Oltre, si alternano a gruppi ogni otto secondi. Niente esce mai dal bordo.

### Il cursore dell'ora parte da +2

**A installazione appena fatta** il cursore della posizione verticale è su
+2, non su zero: il centro geometrico non è il centro che si vede. Un pannello
sta su una mensola e lo si guarda dal basso, e da lì le cifre centrate
sembrano alte. Con il World Time acceso le cifre stanno alle righe 16–44:
zero righe in comune con la data.

Chi aveva già mosso il cursore se lo tiene: il valore nuovo vale per le
installazioni nuove, non riscrive le configurazioni già scritte.

## [9.11]

### L'ora si sposta a gusto

Un cursore nella pagina **Orologio**, da −12 a +12 pixel. Vale sempre, non
solo con il World Time acceso: lo zero è la posizione calcolata dal programma
e il cursore è uno scostamento da quella, non un numero assoluto da
indovinare.

Esiste perché la posizione giusta non è la stessa per tutti — la decidono
l'altezza a cui sta il pannello e il punto da cui lo si guarda, due cose che
da qui non si possono sapere.

Oltre il limite fisico — la banda degli orari del mondo, il bordo — il cursore
smette di muovere invece di spingere le cifre dove non si leggono.

### Due pixel più in basso

L'alzata del World Time scende da **cinque a tre**, e il motivo si è visto
solo sul pannello vero: a cinque le cifre e la data condividevano **tre
righe**.

Lo stacco orizzontale fra il minuto e il giorno della settimana è di circa
cinque pixel, uno in più o uno in meno secondo le cifre e il giorno, e
l'alzata non lo cambia. Ma finché i due blocchi stanno ad altezze
diverse nessuno li confronta; affiancati, a tre metri, per un istante si
leggono come una cosa sola. A tre righe di alzata la riga in comune è una.

Il prezzo sono due righe di respiro in meno sotto le cifre, otto invece di
dieci: uno squilibrio che non si nota, in cambio di una quasi collisione che
si notava.

### La tendina delle città non dice più il falso

È venuto fuori cercando Seattle. Il valore salvato è il **fuso**, e un fuso
ha più città: Roma e Milano, New York e Miami, Toronto e Montreal. Marcando
tutte le opzioni che corrispondono si ottiene un menu con due `selected`, e il
browser tiene l'ultima — chi sceglieva Roma tornava sulla pagina e trovava
scritto **Milano**.

Adesso la tendina non mostra niente: è una scorciatoia che riempie la casella
del fuso **mentre guardi**, e la casella è l'unica cosa che il pannello legge.

Questo chiude anche il secondo equivoco: il campo *Fuso* sembrava da compilare
a mano, e la colonna *Adesso* rispondeva con un trattino finché non si
salvava. Due cose che insieme sembrano un errore.

In tendina entrano **Seattle**, **San Francisco** e **Las Vegas**.
`America/Seattle` non esiste — tutta la costa del Pacifico ha le stesse regole
e il database dei fusi nomina ogni zona con la sua città più grande — ma non
trovarle fa credere che manchino.

## [9.10]

### No all'aggiornamento automatico, sì a farsi sapere

La domanda era se aggiungere un aggiornamento quotidiano **automatico**. La
risposta è no, e il motivo è che il controllo quotidiano esisteva già dalla
1.5 — ogni ventiquattro ore, acceso di serie — e scriveva una riga in
`ota.log`, cioè parlava a nessuno.

Il buco non era il controllo: era l'annuncio.

### L'entità update di Home Assistant

Il pannello si dichiara come `update`, il tipo che Home Assistant ha fatto
apposta: «installata 9.9 → disponibile 9.10», le note di rilascio e il
pulsante Installa, nella stessa lista in cui HA mette gli aggiornamenti del
sistema e degli add-on. Un `binary_sensor` chiamato «Aggiornamento
disponibile» avrebbe detto la stessa cosa in un posto dove nessuno la cerca.

Il pulsante funziona e **non è un aggiornamento automatico**: è una pressione,
come quella sulla pagina web, fatta dal divano. Rifiuta di partire se il
controllo non ha trovato niente di nuovo e se un'installazione è già in corso.

### Quattro pixel verdi

Nell'angolo in alto a destra dell'orologio, quando c'è una versione nuova. È
il punto più vuoto del pannello — la data comincia alla riga 2, il trattino
della diretta sta al centro, la colonna dei rifiuti sta a sinistra — e per
questo si nota anche senza guardarlo. Si spegne dalla pagina Aggiornamenti.

Nel menu della pagina web compare un pallino sulla voce *Aggiornamenti*, che
è l'ultima pagina che qualcuno apre per caso.

### Il controllo guarda la release, non il ramo

`version.py` sul ramo cambia nel momento in cui si fa push, cioè anche a metà
di un lavoro; la release esiste solo quando qualcuno ha deciso che quella
versione si può installare. Fra i due c'è la distanza fra «il codice è
cambiato» e «la versione è pronta».

Se l'API delle release non risponde — ha un limite di chiamate per indirizzo —
si ricade su `version.py` del ramo, come funzionava fino alla 9.9: un
controllo meno preciso è meglio di un controllo che smette di funzionare.

E adesso **quello che la pagina promette è quello che si installa**:
l'archivio si scarica dal tag della release, non dalla punta del ramo.

### Il ripristino non è più muto

Il ripristino automatico funziona dalla 1.5, e proprio per questo era
diventato invisibile: rimetteva in piedi la versione precedente e l'unica
traccia era una riga in fondo a un log. Dal pannello, la mattina dopo, un
aggiornamento fallito e uno mai tentato erano identici — salvo che nel primo
caso continui a premere Installa e continua a non succedere niente.

L'esito finisce in `/var/lib/dmd/ota-esito.json`, che sopravvive al riavvio
del servizio, e da lì in un banner nella pagina, in un pallino rosso nel menu
e in un sensore di Home Assistant a cui si può attaccare un'automazione.

## [9.9]

### World Time

Fino a cinque località con la loro ora vera, in una banda alta dieci pixel
sotto le cifre dell'orologio. Nome nel colore della data, ora in grigio
chiaro, e un `+` o un `−` quando laggiù è un altro giorno.

Quest'ultimo è il dettaglio che sembra un vezzo e non lo è: a Roma le 05:54
sono l'una e cinquantaquattro di New York, ma di **ieri**, ed è esattamente
quello che uno vuole sapere guardando un orologio del mondo.

### Il fuso, non le coordinate

Si salva l'identificativo IANA — `America/New_York` — e non un'ora di scarto,
perché «New York = UTC−5» è sbagliato per metà dell'anno **e sbagliato in
silenzio**. Le regole dell'ora legale stanno già nel database dei fusi del
Raspberry, si aggiornano con gli aggiornamenti di sistema e non chiedono rete.

Le coordinate GPS sono state scartate per aritmetica, non per principio:
tradurre latitudine e longitudine in un fuso richiede un archivio di poligoni
da cinquanta megabyte, su un pacchetto che ne pesa tre. Una tendina con un
centinaio di città riempie il campo, e chi sta altrove scrive a mano il fuso
fra i quasi cinquecento che il sistema conosce.

### Le due preoccupazioni sull'ingombro erano infondate

Ed è bastato misurare. Il semaforo delle scadenze occupa **sette pixel** di
larghezza, da 219 a 225 — non i 68 della fascia che gli è riservata. E da
`y=53` in giù il pannello era già completamente vuoto, per tutti i 256 pixel.
Non serviva né confinare la banda nella larghezza dell'orologio né spostare le
lampade.

Le cifre salgono di cinque pixel, spazio che sopra c'era già, e che sotto è la
differenza fra un carattere da otto e uno da dieci: cioè fra leggere e no.

### Quello che invece dava fastidio davvero

Con **quattro** raccolte differenziate nello stesso giorno, l'ultima finiva
alla riga 59, dentro la banda. La segnalazione è arrivata da chi ne ha quattro,
guardando le anteprime.

Adesso la colonna sa dove deve fermarsi e distribuisce le voci nello spazio che
le resta. Con una, due o tre non cambia niente — ed è il motivo per cui il
difetto non si sarebbe visto provando in casa.

### Quante se ne vedono insieme

Quattro con le sigle corte (`NY`, `TYO`), tre con i nomi interi, due con
«LOS ANGELES». Le altre ruotano a gruppi ogni otto secondi, con un cambio
netto: niente scorrimento, che obbliga ad aspettare il giro, e niente
dissolvenza, che su un pannello LED è una scala di grigi.

Il conto delle città per gruppo si fa sulla **più larga** e non sulle prime.
Altrimenti un giro su due l'ultima usciva dal bordo — e questa l'hanno presa le
prove, prima del pannello.

Manuale nuovo: [`docs/worldtime.it.md`](docs/worldtime.it.md).

## [9.8.1]

### Il testo che sbordava

*«Se il testo è troppo lungo sborda e non lo ridimensiona.»* Quattro parole, e
dentro c'erano due difetti, tutti e due nati dalla stessa scorciatoia:
**contare le righe invece di misurarle**.

L'altezza vera di una riga non è il corpo del carattere: un DejaVu da 13 px
disegna un blocco alto quindici o sedici quando ci sono accenti e lettere che
scendono. Quattro righe così fanno 59 pixel su 58, e la quarta esce dal basso.

La larghezza è peggio. `spezza` non taglia mai una parola a metà — apposta,
perché una parola spezzata a caso rende illeggibili tutte e due le metà —
quindi una parola sola più larga del pannello resta **una riga sola**, e una
riga sola «entra» in qualunque impaginazione se ci si limita a contarle. Usciva
di lato per mille pixel e niente la rimpiccioliva.

Adesso si misura. Se non entra si scende di corpo un pixel per volta, e si
taglia solo quando non c'è più niente da rimpicciolire. In regalo: frasi che
prima venivano troncate a 13 px adesso ci stanno **intere** a 12. Vale per
OnAir e per le notifiche, che condividono l'impaginatore.

### I nomi delle entità non si indovinano

Un'automazione che non funzionava è costata una serata, per tre errori in fila,
e vale la pena elencarli perché nessuno dei tre era nel codice.

Il DMD propone `switch.dmd_onair_diretta`, ma Home Assistant può assegnare
altro — `switch.dmd_controller_in_onda` — unendo il nome del dispositivo a
quello dell'entità. La documentazione dava per certo il primo.

La pagina *Entità* cerca nel **nome**, non nell'identificativo: cercando
«onair» l'entità sembrava mancare mentre c'era. Si cerca «onda».

E il nome del sensore compariva in **due** punti del file YAML. Correggendone
uno solo, l'automazione scattava regolarmente e **spegneva sempre**, perché
`is_state()` su un'entità inesistente è falso. Nessun errore, nessun avviso.

L'automazione nel pacchetto adesso tiene i nomi in `variables`, marca tutte e
tre le righe da correggere, e se il sensore non ha un valore leggibile non
spegne niente e scrive il motivo nel registro di Home Assistant. Un errore di
battitura deve farsi sentire.

### Un manuale per la parte Home Assistant

`docs/onair-automazione.it.md`: chi legge il sensore, i due nomi da leggere e
dove, lo YAML commentato, le tre prove che isolano i tre anelli della catena, e
i tre errori qui sopra raccontati per nome.

### Due frasi che mancavano

Nella pagina Servizi, sotto «OnAir», si leggeva `services.desc.onair` invece
della descrizione. Cercandola è saltato fuori che mancava **anche quella della
sveglia**, da versioni.

Una prova nuova controlla adesso le 897 chiavi scritte nei modelli, in italiano
e in inglese. È il tipo di difetto che non si vede provando il codice, perché
il codice funziona: si vede solo guardando la pagina, e chi la guarda è chi la
usa.

## [9.8]

### OnAir

Tutti gli altri servizi parlano a chi **guarda** il pannello: l'ora, gli aerei,
il brano, il compleanno. Questo parla a chi **entra nella stanza**, e non sta
neanche guardando. È la ragione per cui la luce rossa fuori dagli studi esiste
da cent'anni — e un DMD in soggiorno può farla senza aggiungere un oggetto alla
parete, e può farla meglio, perché sa anche scrivere.

Quando la porta si chiude compare **ON AIR**: fondo rosso, lettere nere, ferma,
nel carattere più grande in cui ci sta. Suona il campanello. Per tutta la
diretta l'orologio porta un trattino rosso di 32×2 pixel centrato in cima —
dalla parte opposta della barra del timer, che è in fondo ed è lunga, così i
due segnali non si possono confondere. La scritta ricompare ogni due contenuti
del Media Player, perché chi entra dopo deve scoprirlo lo stesso. Alla
riapertura sparisce tutto.

**Il DMD non sa che esiste una porta.** Sa solo se è in onda, e lo chiede con un
interruttore: il sensore lo scegli in Home Assistant, con un'automazione di tre
righe che trovi pronta in [`docs/ha/dmd_onair.yaml`](docs/ha/dmd_onair.yaml). Il
giorno che il segnale verrà da un pulsante, da un orario o da un mixer, qui non
cambia niente. E l'interruttore si comanda anche a mano, dalla pagina e a voce,
quindi il servizio si prova prima di aver saldato qualunque cosa.

Priorità **52**: sopra il Media Player, sotto il meteo, e mai sopra una partita.
Chi gioca la porta l'ha chiusa lui.

### Due casi che la richiesta non nominava

**Il campanello suona una volta sola**, alla chiusura. Il rischio era concreto:
il runtime ha un gancio che suona l'avviso di *qualunque* sorgente prenda il
pannello, e con la cadenza dei media una diretta di un'ora avrebbe voluto dire
trenta din-don. Una spia annuncia il cambio di stato, non lo stato.

**«Ogni due media» da solo non bastava.** Se il Media Player è acceso ma non
passa niente — libreria vuota, fascia oraria, Night mode — il contatore non
avanza e la scritta non comparirebbe mai, proprio quando serve. C'è anche un
tetto di tempo, centottanta secondi, che si toglie mettendolo a zero.

### L'impaginazione del testo vive in un posto solo

La regola — prova una riga, poi due, poi tre, tieni la prima che entra, e se non
entra taglia con i puntini — era stata scritta per le notifiche nella 9.5.
Copiarla in OnAir sarebbe stato più veloce oggi e più caro ogni volta dopo: ora
sta in `sources/testo.py`, e i due servizi la chiamano.

### Ventisei sigle nuove

Tutte viste una volta sola: è la coda lunga vera, quella che si è potuta leggere
solo dopo che la 9.7 aveva sbloccato le tabelle. Venti compagnie — quasi tutte
operatori d'affari e air taxi — due aeroporti e tre modelli, fra cui il Tecnam
P2010 e l'Aura Aero Integral R.

## [9.7]

### Le tabelle si fondono

La 9.6 ha rimesso le impronte in elenco, e sul pannello non è cambiato niente:
le stesse sigle di prima, comprese quelle aggiunte mesi fa. Il difetto era più
a monte, e più brutto.

La regola vecchia aveva due sole uscite:

```
file identico a un modello nostro  ->  lo sostituisco tutto
file diverso da tutti i modelli    ->  non lo tocco mai più
```

Bastava **una riga in più** per cadere per sempre nel secondo caso. E a
scriverla non eri tu: era il nostro pulsante «Aggiungi in coda al file», che
mette un `CODICE,,` come promemoria da completare. Da quel momento il pacchetto
portava tabelle nuove e il pannello continuava a mostrare sigle — senza un
errore, senza una riga di log. Il pulsante che aiuta era lo stesso che tagliava
fuori.

Adesso non si sceglie più fra tutto e niente: **si fonde**. Le tue traduzioni
vincono sempre, anche quando contraddicono le nostre. Del modello entra solo
quello che nel tuo file non traduce nessuno. I promemoria vuoti che finalmente
hanno una risposta se ne vanno, che è la ragione per cui erano stati scritti.
Accanto resta una copia di sicurezza con il suffisso `.bak`, e un file già a
posto non viene riscritto.

### Due cose viste strada facendo

Il confronto con il modello si fa **una volta per avvio**. Prima `ensure`
rileggeva il file intero e ne calcolava l'md5 a *ogni singola traduzione* — un
costo che nessuno aveva notato perché non si vedeva da fuori. Il pulsante
«Rileggi le tabelle» lo fa rifare su richiesta.

Il pulsante dei promemoria scrive con **il separatore del tuo file**. Chi aveva
un CSV esportato da un foglio di calcolo italiano, con i punti e virgola, si
ritrovava due righe scritte con la virgola, quindi illeggibili. La fusione
rispetta la stessa regola.

### Cinque sigle nuove

L'aeroporto di Almaty, e tre modelli che raccontano da soli dove vive questo
pannello: il **Magni M-24 Orion**, autogiro costruito a Besnate, il **CSA
SportCruiser** e il **Pitts S-2**.

Brasov, che l'elenco dava per ignota, era invece già in tabella dalla 9.4:
un'altra vittima del file congelato, non una sigla mancante.

## [9.6]

### Le tabelle nuove non arrivavano

Dalla pagina Radar è arrivato un elenco di quaranta sigle mai tradotte. La
maggior parte **c'erano già**: tutti e sei gli aeroporti — Paderborn, Marsa
Alam, Baku, Hahn, Chengdu Tianfu, Zhengzhou — cinque modelli su sette e nove
compagnie su ventisette stavano nel pacchetto dalla 9.4, e sul pannello
continuavano a comparire come codici.

Il motivo sta in una riga. `lookup.DISTRIBUITI` tiene le impronte delle tabelle
che abbiamo distribuito: una copia dell'utente che corrisponde a una di quelle
non è mai stata aperta e si può sostituire; una che non corrisponde a nessuna
vale come lavoro suo e si lascia stare. Nella 9.4 le tabelle sono cambiate ma la
loro impronta non è entrata in elenco, e da quel momento si sono comportate come
se le avesse scritte lui.

Adesso in elenco ci sono anche le tabelle della 9.4–9.5.1, e una prova nuova
confronta ogni tabella con quella distribuita prima: se è cambiata pretende
l'impronta vecchia in elenco, se è rimasta uguale pretende che non ci sia —
perché dichiarare vecchio il modello attuale vorrebbe dire sostituirlo con sé
stesso a ogni avvio.

È la dimenticanza che si fa in silenzio: il pacchetto è giusto, e ad arrivare
storto è solo quello che si vede.

### Ventitré sigle nuove

Venti compagnie — Aeroitalia, flynas, Air Cairo, Corsair, BA CityFlyer, Dan
Air, Electra Airways, Cargo Air, Norwegian Air Sweden, 2Excel, Arcus Air, Air
Horizont, più otto operatori d'affari fra Italia, Germania, Francia, Malta e
Stati Uniti — due modelli, il Tecnam P92 Echo e l'Alpi Pioneer 300, due
ultraleggeri italiani che spiegano da soli perché passassero di lì, e un
aeroporto, Long Island MacArthur, entrato da una rotta e non da un aereo di
passaggio.

Ognuna verificata su due fonti indipendenti che dicono la stessa cosa. Non sulle
liste di Wikipedia, che su questo sono vecchie: danno `AEZ` a un operatore
statunitense chiuso da anni invece che ad Aeroitalia, e `CFE` al nome che BA
CityFlyer aveva prima del 2007.

### L'elenco da tradurre dice quante ne sta nascondendo

La pagina Radar ne mostra quaranta; in memoria ne stanno cinquecento. Oltre la
quarantesima sparivano senza dirlo — e lo si è visto dal vivo: fra due elenchi
letti a un giorno di distanza, tre codici nuovi ne hanno spinti fuori tre vecchi
dal fondo, che sembravano risolti e non lo erano.

Adesso sotto la tabella c'è scritto quante sono in tutto. Il pulsante che le
aggiunge al file le ha sempre prese tutte, anche quelle non mostrate: era il
numero a mentire, non il comando.

## [9.5.1]

### I suoni delle notifiche dicono da dove vengono

I tre selettori si chiamano adesso *Notifica · info — MQTT / Home Assistant*,
e così avviso e allarme.

Nell'elenco dei suoni tutte le altre righe sono servizi del pannello, e si sa
già che cosa fanno. Queste tre sono le uniche che arrivano da fuori: senza
dirlo, chi apre la pagina fa presto a chiedersi che cosa siano.

## [9.5]

### Le notifiche stanno ferme

Un messaggio che non stava in una riga scorreva da destra a sinistra come il
banner, e il colore del livello era quello delle lettere. I due difetti si
sommavano dove contava di più: un allarme lungo era scritto in rosso scuro, in
movimento e lampeggiante, cioè da leggere aspettando che ripassasse l'inizio.

Adesso il testo sta fermo, spezzato su quante righe servono e nel carattere più
grande in cui ci sta — una riga a 32 px, due a 29, tre a 18, quattro a 13. Si
parte dal grande e si scende, così un messaggio corto resta grande invece di
rimpicciolirsi per uniformità, e le parole non si spezzano mai a metà.

Quello che non ci sta nemmeno a quattro righe viene **tagliato con i puntini**,
e per intero resta nella pagina web.

### Il livello è la cornice, non le lettere

La gravità la porta una cornice di due pixel; il testo resta bianco. Sono due
lavori diversi — farsi vedere da lontano e farsi leggere da vicino — e prima li
faceva un colore solo, male tutti e due.

Dell'allarme lampeggia solo la cornice. Prima lampeggiava tutto, e metà del
tempo il messaggio non c'era.

### Tre campanelli, uno per livello

Le notifiche erano l'unico servizio a cui non si poteva assegnare un suono, ed
è l'unica cosa del pannello che succede mentre non lo stai guardando: il
compleanno lo scopri passando in soggiorno, l'allagamento in cantina no.

In *Servizi → Suoni* ci sono adesso tre righe — *Notifica · info*, *Notifica ·
avviso*, *Notifica · allarme* — che si scelgono dalla libreria media come
quelle di tutti gli altri servizi. Tre e non uno: un campanello solo direbbe
«è successo qualcosa» e obbligherebbe ad alzarsi per sapere che cosa.

In elenco entrano i tre livelli e non la voce generica «notifiche»: se ci fosse
anche quella, il gancio del runtime suonerebbe una seconda volta a ogni
messaggio. E un suono che non parte — scheda occupata, file sparito — non si
porta via la notifica: il pannello la mostra lo stesso.

> I campanelli delle notifiche conviene sceglierli sopra il mezzo secondo. Gli
> avvisi dei servizi non passano dal mixer degli effetti, e il fruscio che
> tiene sveglio il convertitore USB vale solo durante le partite: una notifica
> che arriva dopo ore di silenzio trova la scheda addormentata.

## [9.4]

### Le pagine dicono meno

Venti spiegazioni tolte da Musica, Radar, FunCAM e Impostazioni, dove il titolo
diceva già quello che diceva il paragrafo. Qualche etichetta riscritta con le
parole di chi la usa invece che con quelle di chi l'ha scritta: «Uscita musicale
(solo AirPlay)», «Usa cassa integrata», «Altoparlante attivo», «Volume effetti
sonori servizi».

La Funcam si chiama **FunCAM**, ovunque. Della sua pagina resta una riga sola
sul cablaggio, che è l'unica che serve avere sotto gli occhi mentre si salda:
il pulsante va fra GPIO 25 e massa.

### Il radar dimenticava la propria lista della spesa

L'elenco delle sigle mai tradotte — quello che dice quali aeroporti, modelli e
compagnie conviene aggiungere in tabella per primi — viveva solo in memoria. A
ogni riavvio del servizio la pagina tornava vuota, mentre nel registro dei voli
c'erano centinaia di passaggi senza nome.

Adesso all'avvio il registro si rilegge e l'elenco si ricostruisce, con i
conteggi veri e l'ora vera dell'ultimo avvistamento invece di quella del
riavvio. La ricostruzione non introduce una seconda verità: ripassa il registro
**dalle stesse funzioni** che traducono un aereo mentre passa, così la regola
che distingue una compagnia da un'immatricolazione, e quella che spacca
`LOWW → LIMC` nei due aeroporti, restano scritte in un posto solo.

### Le tabelle imparano da quello che è passato davvero

Da 846 passaggi registrati sul campo sono usciti 22 aeroporti, 9 modelli di
aereo e 12 compagnie che il pannello mostrava come sigle.

Gli aeroporti sono stati verificati uno per uno sull'elenco ICAO invece che a
memoria. Dei modelli e delle compagnie sono stati aggiunti solo quelli
confermati da una fonte: gli altri restano nell'elenco delle sigle da tradurre,
che è più onesto di un nome inventato — cinque modelli e trentatré compagnie,
tutti visti una o due volte.

Dopo l'aggiunta, degli aeroporti presenti nel registro non ne resta ignoto
nessuno.

Le impronte delle tabelle precedenti entrano in `lookup.DISTRIBUITI`: è la riga
senza la quale chi aggiorna si terrebbe le tabelle vecchie e non vedrebbe
niente di tutto questo.

### I manuali dicono di nuovo la verità

Dieci manuali su diciassette erano rimasti indietro, e in un paio di punti
mentivano. Adesso raccontano Snake e il suo sterzo a quattro direzioni, il
volume separato dei giochi e il fruscio che tiene sveglia la scheda, la sveglia
che si prende il pulsante quando la FunCAM è spenta, la barra del timer in
fondo all'orologio, i trenta gradi dei satelliti, la correzione della pioggia
sul meteo, e le tabelle delle sigle del radar.

Due errori veri: la tabella delle priorità nel manuale completo ne elencava
undici su quindici — mancavano sveglia, notifiche, satelliti e meteo, cioè
proprio quelle aggiunte dopo che la tabella era stata scritta — e la riga sul
pulsante della sveglia mandava a cercare una casella della FunCAM che non
c'entra più niente.

Di «cabinato» e «flipper» resta una sola occorrenza in tutti i manuali, ed è
voluta: racconta perché Snake ha smesso di sterzare in relativo.

I PDF sono stati rigenerati.

## [9.3]

### Le spiegazioni nelle pagine diventano una riga

Un giudizio dal campo: *l'interfaccia è ottima, ma la quantità di testo
descrittivo potrebbe non essere gradevole.* Era vero, e si misurava: due terzi
di tutto il testo dell'interfaccia — 41.000 caratteri su 65.000 — erano
spiegazioni, con una media di 203 caratteri l'una. Chi apre una pagina per
spuntare una casella non legge un paragrafo: lo salta, e saltandolo perde anche
la riga che gli serviva.

Riscritti **183 testi**: media da 203 a 80 caratteri, il 61% in meno su quelli
descrittivi e il 34% su tutto il testo dell'interfaccia. Ognuno dice adesso che
cosa fa il comando, in una riga. Il perché non è sparito: è nei commenti del
codice, dove serve a chi lo cambia e non pesa a chi lo usa.

Restano lunghe poche cose, ed è una scelta dichiarata: la taratura del pannello,
la libreria della matrice, il cablaggio del pulsante e la preparazione di Doom e
PyBoy. Sono le cose che si fanno una volta sola, con il saldatore o il terminale
in mano, e lì una parola in meno costa un pomeriggio.

Una prova nuova tiene il tetto a novantacinque caratteri e l'elenco delle
eccezioni scritto una per una, con il motivo accanto: allungare un testo si
potrà ancora, ma diventa una decisione presa e non un'abitudine che torna.

## [9.2]

Cinque cose della sveglia e del timer, tutte trovate montando la macchina e
usandola, non leggendo il codice.

### Il pulsante non era di nessuno

Il piedino GPIO lo apriva `start()` della **telecamera**. Esisteva quindi solo
mentre il servizio Funcam era acceso — e con la Funcam spenta, che è il caso
normale di chi la webcam non la usa, nessuno leggeva quel piedino. La sveglia
squillava, il testo della pagina diceva di premere il pulsante, e premerlo non
faceva niente. Da fuori sembrava una saldatura sbagliata; il pulsante invece
era perfetto, tredici pressioni su tredici lette da `gpiozero` a servizio
fermo.

Adesso il pulsante è del DMD, non della telecamera. Mentre la sveglia squilla è
suo: se nessuno lo tiene se lo apre da sola, e se ce l'ha la telecamera glielo
lascia, perché il clic le arriva e lei lo gira comunque alla sveglia. Lo
rilascia il ciclo principale e non `zittisci`, che viene chiamata dal callback
del pulsante stesso: chiudere un oggetto `gpiozero` da dentro il suo gestore di
eventi è il modo più rapido di piantare un thread.

Chi non lo vuole mette `sveglia.pulsante` a falso.

### Il timer non si vedeva

Si mette da una pagina web, ma la pasta si guarda in cucina, e in cucina
l'unica cosa che si guarda è il pannello — che del timer non sapeva niente.

L'orologio adesso ha in fondo una barra rossa spessa due pixel che **si
accorcia** man mano che il conto scende. Una riga fissa direbbe soltanto che un
timer c'è; una che si accorcia costa gli stessi due pixel e dice anche quanto
manca, senza scrivere numeri sopra un orologio che di numeri ne ha già.

### Il timer inventava un errore

Con un conto alla rovescia in corso la pagina lasciava sotto i comandi per
avviarne un altro. Premerne uno con il campo dei minuti vuoto rispondeva «Timer
non avviato: durata non valida» mentre il timer stava andando benissimo: un
errore inventato su un'azione che non andava nemmeno offerta.

Adesso, con un timer in corso, ci sono solo il conto alla rovescia e «Annulla il
timer». Un timer alla volta era già la regola, ma la si applicava sostituendo
quello in corso; adesso ci si rifiuta e si spiega perché.

### E due cose storte nella pagina

Il campo dei minuti e il pulsante Avvia stavano in una griglia metà e metà, che
per un numero di quattro cifre dava un campo largo mezza scheda con il pulsante
spaiato di fianco. Adesso hanno una riga fatta per loro: campo largo quanto
serve, e i due allineati in mezzo.

## [9.1]

I suoni dei giochi che mancavano. Due difetti, e nessuno dei due stava dentro i
giochi — dove invece la caccia è andata avanti per settimane, al punto che
Breakout è stato riscritto da capo per colpa loro.

A chiudere la questione è stata una registrazione byte per byte di quello che il
DMD manda alla scheda durante una partita vera: **gli effetti c'erano tutti.**
Venticinque sbuffi in 129 secondi, i contatori a 26 chiesti e 26 resi, zero
underrun, e fra un suono e l'altro zero digitale perfetto. Da lì la domanda non
è più stata «perché si perdono» ma «perché non si sentono», che è una domanda
diversa e ha due risposte.

### Il volume: i giochi usavano quello degli avvisi

Il volume generale lo si abbassa pensando al pannello che parla da solo, magari
di sera. Sul DMD dove il problema si vedeva era a 0,05. Nella registrazione ogni
sbuffo aveva il picco **esattamente** 0,05 volte quello del suo file — 800 su
32767 dove il file ne ha 16000 — senza una sola eccezione, e i tre valori fuori
dal conto erano due suoni sovrapposti.

Intanto Doom, il Game Boy e la musica AirPlay si sono sempre sentiti benissimo,
ed è l'indizio che mancava: scrivono sulla scheda per conto loro, a fondo scala,
cioè 26 dB più forte dei nostri effetti.

Ora i giochi hanno la loro manopola in Impostazioni, predefinita a 0,90, e chi
aggiorna non eredita il volume degli avvisi. Non è una comodità: un effetto dura
cinquanta millesimi e l'orecchio integra il volume su due decimi di secondo, così
un suono tanto corto si sente molto più piano di uno lungo con la stessa
ampiezza. Con una manopola sola, o gli avvisi urlano o i giochi spariscono.

### Il silenzio: la scheda si addormentava

Fra un effetto e l'altro il mixer scriveva zero digitale esatto — il 98% dei
campioni della registrazione. Molti convertitori USB si automutano su zero e
riaprono l'uscita con una rampa di qualche decina di millesimi per non fare il
«plop»: un effetto da settanta millesimi ci sparisce dentro quasi intero.

È da qui che veniva il sintomo che sembrava impossibile — «quando lo sento, lo
sento bene» — e la differenza fra Snake, che suona ogni cinque secondi e ne
perdeva nove su dieci, e Breakout, che suona a raffica e ne salvava la maggior
parte. La prova che lo ha inchiodato è stata la più semplice di tutte: lo stesso
beep, dieci volte di fila, con in mezzo silenzio digitale oppure un fruscio
inudibile. Col silenzio non si sentiva; col fruscio sì.

Adesso, durante una partita, il mixer non scrive mai zero: scrive rumore bianco
a −60 dBFS, sotto il fondo di qualunque stanza e abbastanza perché la scheda non
vada a dormire. Si spegne con `audio.sottofondo` a zero.

### E due numeri che mentivano

La pagina Giochi diceva `buffer_ms: 544` dove il cuscino vero è 250: si divideva
il `buffer_size` della scheda — in fotogrammi a 48000 — per 22050. Con `plughw`
aplay stampa un blocco di riepilogo per ogni anello della catena, e tenendone
solo quaranta righe si perdeva proprio il primo, l'unico che parla del flusso
che scriviamo noi. Quel numero sbagliato rassicurava nel momento peggiore,
mentre si cercava un difetto di cuscino.

E quattro righe di riepilogo (`tstamp_mode`, `tstamp_type`, `period_event`,
`hw_ptr`) finivano nel cestino degli errori: l'ultima diventava la riga rossa
della pagina, e un flusso negoziato alla perfezione si presentava come un
guasto.

## [9.0]

Quattro cose sostanziali, tutte nate da una segnalazione di chi il DMD ce l'ha
acceso in casa. Le versioni intermedie con cui ci si è arrivati non sono state
pubblicate: quello che segue è il punto di arrivo, non il percorso.

### Breakout rifatto da capo, per il suono

Per settimane è stato l'unico gioco a cui mancavano degli effetti. Le misure
dicevano che la logica li chiedeva tutti — 510 contatti rilevati dalla fisica,
510 chiamate — ma quelle misure le avevo scritte io, e a un certo punto
difendere il proprio codice vale meno che rifare la parte che ha qualcosa di
unico.

E qualcosa di unico ce l'aveva: **da dove** usciva il suono. Il passo di
Breakout si spezza in micro-passi più corti di un pixel — altrimenti una palla
veloce attraversa un mattone senza accorgersene — e i suoni partivano da
*dentro* quel ciclo. Era l'unico gioco del progetto in cui una sola chiamata a
`passo()` poteva emetterne tre o quattro, in un ordine deciso dalla fisica
invece che dal fotogramma. Invaders, che i suoi li emette una volta per
fotogramma, non ha mai avuto il problema.

Adesso la fisica non suona: **registra**. Gli eventi finiscono in una lista e a
fine `passo()` escono insieme, ordinati per importanza e senza ripetizioni, al
massimo due per fotogramma. In tutto il file c'è **una sola riga** che chiama
`suona`, e una prova lo verifica leggendo il sorgente. È diventata la regola del
progetto, e Snake nasce già così.

Rifacendolo è saltato fuori un difetto vecchio: rompere l'ultimo mattone e
perdere la palla nello stesso fotogramma lasciava il livello a metà fino al
lancio successivo.

### Snake

Quello dei Nokia, su una griglia di **49x15**: larghissima e bassa, il contrario
degli undici quadrati per lato del 3310. Un serpente che cresce qui riempie
prima l'altezza che la larghezza, quindi la partita è fatta di corridoi
orizzontali — e per questo il cibo non compare **mai** nella riga in cui il
serpente sta già viaggiando: su quindici righe sarebbe mezzo regalo.

Si gioca con le quattro direzioni del pad, delle frecce o di WASD. Il
dietrofront si ignora, e si scarta **al momento di muoversi** e non alla
pressione: altrimenti due tasti sfiorati dentro lo stesso trentesimo di secondo
farebbero un mezzo giro, e il serpente si morderebbe da solo senza aver percorso
una casella. La pagina Giochi guadagna i pulsanti su e giù, perché con due
frecce sole dal telefono non era giocabile.

Quattro effetti nuovi — `mangia1/2/3` e `tonfo` — e la nota del boccone **sale
con il livello**: è il modo in cui il gioco dice «stai andando bene» senza
scrivere niente sul pannello. Hanno una **ricetta** invece di essere wav
opachi: `diagnostica/genera_suoni.py` li rifà da frequenze, durate e inviluppi.
Non tocca quelli di Breakout e Invaders, che sono stati fatti in un altro modo e
rigenerarli vorrebbe dire cambiarli.

### I satelliti: trenta gradi invece di dieci

Una sera il pannello annuncia un passaggio e il satellite risulta sopra la
Spagna. **Quella parte non era un difetto**: il preavviso è di dieci minuti, e in
dieci minuti un oggetto in orbita bassa percorre 4600 km di traccia al suolo — è
esattamente da lì che si arriva sopra l'Italia.

Ma la soglia era sbagliata lo stesso. Dieci gradi è la regola dei radioamatori,
sotto cui l'atmosfera attenua il segnale **radio**; qui il ricevitore sono gli
occhi di chi sta in terrazzo, e davanti a quegli occhi ci sono i tetti. A dieci
gradi un oggetto a 420 km sta a 1390 km di distanza al suolo ed è **2,8
magnitudini più fioco**: tredici volte. A trenta gradi ne perde 1,3, e bisogna
alzare il naso invece di guardare fra i comignoli.

Costa circa **metà** degli annunci — la frazione di passaggi che sopravvive a
una soglia è la larghezza della fascia di tracce al suolo che la produce. Più su
non si poteva andare: a sessanta gradi resterebbe il 16%, e con due soli oggetti
noti il servizio smetterebbe di esistere. La levetta c'era già, da 0 a 80 gradi:
mancava un predefinito pensato per gli occhi invece che per un'antenna. Chi ha
scritto un numero suo se lo tiene.

### Il meteo diceva «nuvolo» mentre pioveva

Il codice del cielo fra i valori correnti viene da un modello, e un modello che
dice «coperto» mentre cade pioviggine non sbaglia di molto — ma sul pannello
sbaglia del tutto, perché chi lo guarda sta decidendo se prendere l'ombrello.

I millimetri d'acqua caduti nell'ultima ora il servizio li dà, come numero a
parte, e non li chiedevamo nemmeno. Adesso si chiedono, e quando i due si
contraddicono **si crede al millimetro**: l'acqua è una misura, il codice è
un'interpretazione. Al contrario non si corregge niente — un codice che dice
pioggia con zero millimetri può essere un rovescio appena finito. Sotto un
decimo di millimetro non si tocca nulla: è un velo che non bagna.

Chiedere un campo in più però non deve poter spegnere il meteo: se il servizio
lo rifiutasse, la richiesta ripiega sull'elenco di prima.

### E i testi smettono di parlare di un cabinato

Le righe che si leggono nelle pagine dicevano «la tastiera del cabinato», «il
pulsante sul cabinato», «una pulsantiera da flipper». Era il mio modello
mentale, non la macchina di chi lo usa: un pannello su una mensola e un
controller in mano. Adesso dicono il pad, o la tastiera collegata al DMD, o
semplicemente *il tasto che vuoi usare*. Nei commenti del codice qualche
riferimento resta, ed è lì che spiega **perché** certi codici siano
configurabili — quel ragionamento vale ancora.

## [8.6]

- **Il video lo dimostra: un mattone rotto, e nessun suono.** Quaranta secondi
  di filmato del pannello, con l'audio. Il punteggio sullo HUD è un testimone
  che non si può contestare: fra 34,0 e 34,5 secondi passa da `001130` a
  `001140` — **un mattone rotto**, provato dai dieci punti. Nello spettro
  dell'audio, in quella finestra, tutte e sette le note del gioco stanno al
  livello del rumore di fondo: rapporto banda/fondo fra 9 e 20. Nelle finestre
  in cui i suoni si sentono, lo stesso rapporto vale fra 60 e 500. Quel mattone
  non ha suonato.

- **E non è un caso isolato.** Riconoscendo i suoni dalla loro nota — ogni
  effetto ha una frequenza sua — e tarando la soglia sulla parte buona del
  filmato: **racchetta 1,56 al secondo prima della palla persa, 0,16 dopo;
  muro 2,78 prima, 0,32 dopo.** Sette secondi e mezzo di silenzio totale dal
  rilancio, poi i suoni tornano. La segnalazione dal campo era esatta in ogni
  dettaglio, compreso il «dopo aver perso la palla».

- **Una delle cause l'ha introdotta la 8.5, cioè io.** Il regolatore nuovo
  tiene nell'anello della scheda un cuscino di `CUSCINO_ANELLO` millisecondi, e
  quel valore era calcolato come *cuscino meno tubo*: con il tubo al minimo
  faceva **30 ms**. La chiavetta del DMD lavora con periodi da 1200 fotogrammi
  a 48000 Hz, cioè 25 ms, e `delay` comprende anche quello che è già stato
  consegnato al ferro: un bersaglio di 30 ms è poco più di **un solo periodo** e
  non si raggiunge mai. Il regolatore restava in attesa fino a mezzo secondo e
  scriveva un blocco ogni tanto invece di trenta al secondo — la scheda a
  secco, il gioco muto.

  Adesso il bersaglio è il cuscino intero, 120 ms, quasi cinque periodi. Il
  tubo resta al minimo per non nascondere ritardo, ma non si sottrae più: il
  ritardo peggiore possibile è 213 ms. E l'attesa massima del regolatore scende
  da mezzo secondo a 150 ms, così un errore dello stesso tipo può rallentare,
  non ammutolire.

- Una prova nuova rifiuta qualunque bersaglio più basso di tre periodi: questa
  lezione sta in un controllo, non in un commento.

## [8.5]

- **La scheda audio non ha mai fatto un buco.** Leggendo `/proc/asound` sul DMD
  mentre si giocava: `state: RUNNING` per 58 secondi di fila, **nessun XRUN**, e
  `buffer_size 12003` frame a 48000 Hz — i 250 ms richiesti, concessi per
  intero. Nessun suono è mai stato tagliato dalla scheda.

- **Ma la coda era piena al 99%.** `delay` stava fra 229 e 263 ms su 250 di
  capienza, per tutto il tempo, più i 372 ms che poteva tenere il tubo verso
  `aplay`: fino a **sei decimi di secondo** fra il colpo e il suono.

  La causa è una riga della 8.2, mia. Il mixer si dava il ritmo con
  `time.monotonic()` — scrivo un blocco ogni 23 ms, quindi dopo un minuto avrò
  scritto un minuto di audio. Sembra ovvio e non lo è: **la scheda non va al
  ritmo del nostro orologio.** Gli effetti sono a 22050 Hz mono e la chiavetta
  suona a 48000 stereo; la conversione più il quarzo fanno un errore piccolo e
  sempre nello stesso verso. Un errore piccolo che si accumula riempie
  qualunque coda, e da lì in poi il ritardo è il massimo possibile per
  costruzione.

- **Adesso il ritmo lo detta l'orologio della scheda.** ALSA pubblica in
  `/proc` quanti fotogrammi le restano da suonare: il mixer lo legge a ogni
  blocco e smette di scrivere finché non sono scesi sotto il cuscino. La
  frequenza si legge una volta sola per flusso, perché quella non cambia e il
  file costa. Il tubo passa al minimo che Linux concede — 4096 byte, 93 ms —
  perché quello che sta nel tubo è ritardo che `/proc` non racconta, e il
  cuscino vero è anello più tubo.

  Misurato al banco con una scheda che deriva dello 0,4%: senza regolatore la
  coda cresce e si assesta al **90% dell'anello**; con il regolatore la mediana
  cala del 31% e a fine corsa resta molto più in basso.

- **E una registrazione, per chiudere la questione.** Accendendo
  `audio.registra_effetti` in configurazione, il mixer scrive in
  `/tmp/dmd-effetti.raw` una copia esatta di quello che manda alla scheda — PCM
  grezzo 22050 mono. I contatori dicono quello che il programma *crede* di aver
  fatto; il file dice quello che ha fatto. È l'unico modo di rispondere a
  «questi suoni sono usciti dal DMD o no?» quando i contatori dicono di sì e
  l'orecchio dice di no.

## [8.4]

Versione di **strumenti, non di rimedi**: i suoni di Breakout continuano a
mancare sul campo, e invece di spedire una correzione a indovinare si sono
scagionati i sospettati uno per uno.

- **Il gioco è innocente, e la prova è quella che hai chiesto tu.** «Possiamo
  contare i contatti della palla con gli oggetti o il cursore e il numero di
  suoni emessi?» Sì — a patto di non contare i contatti dalle stesse righe che
  suonano, che sarebbe verificare che il codice è uguale a sé stesso. Qui i
  contatti si rilevano dalla **fisica**: un mattone in meno, la velocità che
  cambia segno, la palla riportata esattamente sul bordo. Quattro partite
  intere, tutte le vite: **510 contatti, 510 suoni**. Nessun contatto muto, e
  mai più di un suono per fotogramma — il che manda in soffitta anche
  l'ipotesi dei suoni a grappolo schiacciati dal limitatore.

- **Il mixer è innocente.** Campionando i contatori durante una partita vera:
  90 suoni chiesti, 90 resi, zero morti del riproduttore, zero riavvii, mixer
  sempre acceso — mentre chi stava giocando sentiva sparire i suoni.

- **E il contatore dei buchi era cieco.** Leggeva gli `underrun!!!` che stampa
  `aplay`, ma `aplay` quei messaggi li stampa **solo in modalità prolissa**, e
  gli si passava `-q`. Quello `vuoti 0` non poteva accendersi nemmeno con la
  scheda che restava a secco ogni tre secondi: era un contatore cieco
  spacciato per una prova, ed era mio. Adesso `aplay` va in prolisso e i buchi
  si contano per davvero.

- **E si vede quanto buffer ha concesso la scheda.** Se ne chiedono 250 ms, ma
  ALSA dà quello che può e non lo dice a nessuno. Dal riepilogo di `aplay -v`
  si legge il `buffer_size` reale, e la pagina Giochi lo mostra in
  millisecondi accanto al cuscino richiesto. Se i due numeri non si somigliano,
  il cuscino su cui conta il mixer non esiste — ed è la prima cosa da guardare
  la prossima volta.

- Le righe di `aplay` vengono ora divise in tre categorie: buchi, riepilogo
  della negoziazione, errori veri. Senza, un innocuo `buffer_size: 5512`
  sarebbe finito nella riga rossa della pagina come se fosse un guasto.

## [8.3]

- **Il meteo adesso dice di quando parla.** Accanto a massima e minima c'è una
  parola — **OGGI** o **DOMANI** — e dopo il tramonto l'intera schermata passa
  al giorno dopo: icona, descrizione, estremi, probabilità di pioggia, alba e
  tramonto vengono tutti dallo stesso giorno.

  Non era solo ambiguità. Di sera quei due numeri erano **passati**: la massima
  di oggi alle dieci di sera l'hai già vissuta, e la minima quotidiana è quella
  della notte scorsa. Era cronaca presentata come previsione.

  La soglia è il tramonto vero, che il DMD ha già nei dati, non un orario
  fisso: d'estate il passaggio è alle nove e mezza, d'inverno alle cinque —
  cioè quando cambia davvero la giornata di chi guarda. Senza la previsione del
  giorno dopo non si inventa niente: si resta su oggi e si scrive OGGI.

- **E si fa vedere davvero.** «Sono dieci minuti che guardo il DMD e non ho mai
  visto le previsioni.» Dieci minuti con un giro da venti non provano niente da
  soli, quindi si è contato — e sotto c'era un difetto vero.

  Il meteo ha priorità 54, il Rolling Banner 55, e il banner con i valori
  predefiniti occupa il **38% della giornata**. Il meteo segnava il turno come
  speso *nell'istante in cui apriva la finestra*, non quando il pannello era
  davvero suo: se in quel momento c'era il banner, la finestra si apriva e si
  chiudeva senza che nessuno vedesse niente, e il turno successivo era fra venti
  minuti. Simulando una giornata: **48 comparse vere e 460 turni bruciati a
  vuoto**.

  Adesso il turno lo consuma `in_onda()`, un aggancio nuovo su tutte le sorgenti
  che il ciclo di rendering chiama quando l'arbitro assegna il pannello — l'unico
  istante in cui si sa che qualcuno sta guardando. Perdere il turno costa
  sessanta secondi invece di venti minuti. E chi arriva a schermo a metà finestra
  la ottiene intera, invece dei tre secondi avanzati dal banner.

- **Il giro passa da venti a dieci minuti**, con migrazione automatica per chi
  ha ancora il vecchio predefinito esatto — chi ha scritto un numero suo lo
  tiene. Misurato su una giornata simulata: da 48 a **139 comparse al giorno**,
  il 2% del tempo del pannello.

- **Quello che invece non si è fatto, ed è la parte che vale.** La proposta era
  di alzare anche la priorità del meteo. Con il turno bruciato corretto, passare
  davanti al banner vale **quattro comparse al giorno su 139** — e costa banner
  tagliati a metà frase, perché l'arbitro rivaluta a ogni fotogramma. La
  priorità non era la leva: era il turno.

- Minore, ma si vedeva: il puntino che segnala una previsione vecchia stava in
  alto a destra, addosso al grado della minima. Due cose diverse nello stesso
  millimetro, e sembrava un difetto del pannello. Adesso sta in basso. E la
  descrizione del cielo non si tronca più prima del necessario: lo spazio
  disponibile si misura invece di stimarlo con una frazione fissa, perché quel
  blocco cambia larghezza con l'etichetta del giorno e con la lingua.

## [8.2]

- **I suoni di Breakout, rifatti dalla parte che li faceva sparire.** La
  richiesta era di ripartire da capo. Il punto di partenza però non poteva
  essere il gioco: misurando una partita vera, la logica di Breakout chiede i
  suoi suoni, e li chiede una volta sola. Sparivano **dopo**, lungo la strada
  fra il gioco e l'altoparlante — e quella strada aveva tre buche.

- **Il riproduttore poteva morire senza che nessuno lo sapesse.** È la buca
  grossa, ed è anche la risposta alla domanda rimasta aperta per settimane:
  *perché solo Breakout?* La scheda audio del DMD è una sola. Se quando si
  preme Start c'è un avviso di un servizio che la sta usando, `aplay` parte,
  non riesce ad aprirla ed esce subito. Ma `Popen` riesce sempre, quindi
  `avvia()` rispondeva «tutto bene», e il motivo vero — *Device or resource
  busy* — finiva in `/dev/null`, perché lo stderr veniva buttato via.

  Da quel momento, e per tutta la partita, ogni effetto ripiegava sulla
  vecchia strada del processo per volta: ne suona uno e **scarta tutti quelli
  che si sovrappongono**. Breakout i suoi suoni li fa a grappoli — muro,
  mattone e racchetta possono capitare dentro lo stesso frame, perché la palla
  avanza a micro-passi — e ne perdeva a manciate. Invaders, che li fa
  spaziati, quasi no. È esattamente la differenza che si sentiva.

  Adesso la morte del riproduttore si vede, si conta e **si ripara**: la
  scheda si riapre finché non torna libera, per un minuto, e i suoni chiesti
  nel frattempo aspettano in coda invece di prendere la strada che li
  scartava. Quelli che aspettano più di mezzo secondo si buttano: una
  racchetta che arriva in ritardo non è un suono recuperato, è un suono
  sbagliato.

- **Il cuscino era di venti millesimi di secondo.** Fra il mixer e
  l'altoparlante c'è una coda di audio già scritto, ed è l'unica difesa contro
  un ritardo del thread: quando la coda finisce, la scheda mette silenzio. In
  ALSA si chiama underrun; per chi gioca è «il suono è saltato». La misura
  diceva 20–60 ms. Sul Raspberry il GIL è uno solo, Pillow lo tiene per tutta
  la durata di ogni operazione e il pannello ridisegna 256×64 trenta volte al
  secondo: una pausa di cinquanta millesimi non è un caso di scuola.

  Il cuscino adesso è dichiarato e vale **120 ms** — misurati al banco, 133 ms
  fra il mattone colpito e il suono. Si paga un ritardo che non si distingue
  da «subito» (una cassa Bluetooth ne aggiunge di più) e si compra un audio
  che una pausa di ottanta millesimi non buca più.

- **Il tetto di otto voci buttava la più vecchia.** Otto voci insieme vogliono
  dire otto suoni dentro 55 ms, cioè 145 al secondo: non succede mai. Quel
  tetto non ha mai protetto niente e poteva solo far sparire un suono. Adesso
  è 24 ed è un freno di sicurezza, non una regola di funzionamento. Quando più
  suoni coincidono il blocco si abbassa quel tanto che basta invece di
  tagliare i picchi: cinque mattoni insieme si sentono come cinque mattoni e
  non come uno schiocco.

- **E l'ultimo suono della partita esce davvero.** Il primato suona mentre la
  partita si sta già chiudendo, e la riga dopo spegneva il riproduttore. Con
  un cuscino davanti, «la riga dopo» vuol dire *sempre prima che si senta*.
  Adesso si aspetta che la coda sia uscita.

- **I numeri, finalmente.** Durante la partita la pagina Giochi mostra quanti
  effetti ha chiesto il gioco, quanti ne sono usciti davvero, la resa in
  percentuale, i buchi della scheda, le cadute e le riaperture del
  riproduttore, e le sue ultime righe di errore. «Ne salta troppi» adesso è
  una domanda con una risposta.

- **Due correzioni a cose che avevo scritto e che erano false.** Nella guida
  alla pubblicazione c'era scritto che l'URL lungo di `raw.githubusercontent`
  (`refs/heads/main`) salta la cache: misurato, **rispondono entrambi**
  `cache-control: max-age=300`. E accanto al pulsante *Controlla ora* adesso
  c'è scritto che la risposta di GitHub può essere vecchia di cinque minuti.

## [8.1]

- **La pagina Servizi diventa tre schede: Servizi · Timing · Suoni.** Non tre
  voci di menu — che su un telefono sta già su tre righe — e non tre
  sottopagine di Impostazioni, che le avrebbe separate dai servizi a cui si
  riferiscono. Sono **tre colonne della stessa tabella**: se un servizio è
  acceso, quando è acceso, che suono fa.

- **Timing.** Ogni servizio ha la sua fascia oraria, con «sempre attivo» acceso
  di suo: finché non ne accendi una, tutto si comporta come si è sempre
  comportato. Si porta dentro anche Night mode, Sleep mode e la fascia del
  Media Player, che stavano in tre pagine diverse.

  La regola è rimasta **una sola**: `Arbiter.consentito` era già il cancello
  unico attraversato da tutti — la pagina web, Home Assistant, l'avvio — e
  bastava generalizzare `fasce` invece di aggiungere un secondo meccanismo. La
  fascia del Media Player resta scritta dov'era, sotto `mediaplayer.timer_*`:
  spostarla avrebbe voluto dire o perdere l'impostazione di chi aggiorna, o
  tenerne due copie che prima o poi divergono.

  **La colonna che conta non sono gli orari.** È quella a destra, che dice se
  il servizio sta lavorando *adesso* e, se no, chi lo sta fermando. Aggiungere
  una fascia a quindici servizi moltiplica per quindici i modi in cui qualcosa
  può non comparire: senza una risposta scritta si finisce a indovinare, ed è
  già successo col meteo — dove la colpa è stata data a una fascia che non
  c'entrava niente.

- **Suoni.** Le scelte dei suoni erano sparse nelle schede dei singoli servizi,
  una per riquadro, in mezzo a tutto il resto. Adesso stanno in un posto solo,
  ciascuna con il nome del file assegnato in evidenza.

- **Il volume è uno slider.** Un volume si cerca a orecchio, e il numero esatto
  non lo sa nessuno prima di averlo sentito. Accanto compare il **livello
  hardware della scheda** — quello che a −20 dB aveva zittito musica, avvisi e
  giochi insieme per una serata intera senza che nessuna pagina lo mostrasse —
  e sotto il 70% la pagina dice anche come alzarlo.

- Casella nuova: **risvegliare il display se qualcuno apre una partita durante
  lo Sleep**. Era già il comportamento, ma cablato nel codice. Sono due cose
  diverse da quella dei frame da Batocera: quelli arrivano da soli, una partita
  la apre qualcuno che è lì davanti.

## [8.0]

- **Il timer.** Una sveglia si mette *a un'ora*; un timer *fra quanto*. La
  pasta non scade alle 20:47, scade fra nove minuti, e nessuno vuole guardare
  l'orologio e fare la somma con le mani bagnate.

  Quattro durate pronte da premere — i pulsanti vengono prima del campo libero
  apposta: in cucina si preme, non si digita — più un campo per scriverne una
  qualsiasi, e un nome facoltativo («Pasta», «Forno») che compare sul pannello
  quando squilla: serve a sapere *perché* sta suonando, non solo che sta
  suonando. Uno solo per volta: due che scadono insieme darebbero un unico
  squillo con due motivi, cioè un'informazione persa.

- **Le partite si congelano davvero, e questa è la correzione di un errore
  mio.** La 7.7 non congelava niente, con la motivazione che «le sveglie
  suonano al mattino, e chi sta giocando a Doom alle sette?». La risposta è
  arrivata in una frase — *metti che devo ricordarmi di scolare la pasta e
  mentre cucino decido di giocare a Doom* — e ha demolito la premessa: una
  sveglia serve soprattutto **mentre si è occupati a fare altro**.

  Peggio: la stessa stesura affermava che i giochi scritti per il pannello si
  fermassero da soli, perché li disegna il ciclo principale. **Non è vero.**
  Hanno un thread loro, esattamente come Doom e il Game Boy, e continuano a
  giocare anche a pannello altrui. Si tornava e ci si trovava morti in tutti e
  tre i casi.

  Ora Breakout e Invaders si congelano con una variabile — la sessione resta
  aperta, il tempo del gioco non passa, e al risveglio la palla riparte da
  dov'era, con i tasti premuti dimenticati perché la racchetta non parta da
  sola verso il muro. Doom e il Game Boy si sospendono con `SIGSTOP` e
  ripartono con `SIGCONT`, senza sapere niente di quello che è successo.

  **Un limite resta, ed è scritto invece che risolto:** un processo sospeso non
  chiude i file che teneva aperti, scheda audio compresa. Se Doom sta suonando
  quando la sveglia scatta, la scheda resta sua e la sveglia lampeggia ma non
  si sente. Liberarla vorrebbe dire chiudere la partita, e fra una sveglia muta
  e una partita persa vale di più la partita.

- **Le caselle degli orari uscivano dal bordo destro delle schede su iPhone.**
  Segnalato con una foto, e la causa sono due regole che si sommano.
  `input[type=time]` ha una **larghezza minima propria** — quella del selettore
  nativo di iOS — e nessuna percentuale lo fa scendere sotto il suo min-content;
  e una colonna di grid nasce con `min-width: auto`, che vuol dire «non
  stringerti sotto il tuo contenuto». Il campo allargava la colonna, la colonna
  allargava la griglia, e la griglia usciva dalla scheda. `width: 100%`, che
  c'era già, non poteva farci niente.

## [7.7]

- **La sveglia.** Il DMD sta in soggiorno, è acceso tutta la notte, ha un
  orologio grande e una scheda audio. Tutto quello che serve a una sveglia
  c'era già: mancava di metterlo insieme.

  Quattro orari, ciascuno con i suoi giorni della settimana, il suo suono e
  la sua durata. Quando uno scatta il pannello diventa un orologio che
  lampeggia e la scheda audio suona, finché non si preme il **pulsante della
  Funcam** — che sul cabinato c'era già, e che mentre la sveglia squilla
  appartiene a lei: un clic la ferma e non scatta nessuna foto. La decisione
  sta in un punto solo, con la telecamera che non sa nemmeno che esista una
  sveglia.

- **Tre eccezioni che nessun altro servizio ha**, e ognuna è stata necessaria.

  *Vince sullo Sleep mode.* Il ciclo principale, quando dorme, si ferma
  **prima** di chiedere all'arbitro chi debba comparire: una sorgente
  qualunque, per quanto prioritaria, non verrebbe nemmeno interrogata. Una
  sveglia alle 7 con lo Sleep fino alle 8 non suonerebbe mai — cioè proprio
  nel caso in cui serve di più.

  *Vince sul display spento a mano.* Spegnere il pannello è una decisione sul
  presente; mettere una sveglia è una promessa fatta prima per dopo. Fra le
  due vince la promessa, e chi non la vuole spegne la sveglia.

  *Non la tocca il volume notturno.* Quel silenzio esiste perché un aereo alle
  tre di notte non merita di svegliarti. Una sveglia si mette apposta per
  farlo: sarebbe l'unico caso in cui quella regola fa danno. Anche la
  luminosità torna quella di giorno — una sveglia che si vede al quindici per
  cento è mezza sveglia.

  Resta dentro **una** regola, ed è giusto: ad audio generale spento non
  suona, e il pannello lampeggia lo stesso. Chi ha spento il suono vuole
  silenzio.

- **La regola delle tre eccezioni sta in una funzione a sé**, fuori dal calcolo
  delle fasce. Non è pignoleria: lì dentro sarebbe rimasta in mezzo alla
  lettura dell'orologio e al calcolo della luminosità, e l'unico modo di
  verificarla sarebbe stato mettere una sveglia vera e aspettare le sette. Una
  regola che si può chiamare si può anche provare.

- Le prove fanno scorrere **una settimana intera** davanti alla sorgente vera,
  un minuto per giro, con un orologio finto, e contano gli squilli: cinque per
  una sveglia feriale, non trentacinque né uno. Più il caso in cui si parte
  sessanta volte nello stesso minuto, quello in cui nessuno risponde, il ritmo
  con cui bussa il suono, il lampeggio che deve avere anche la metà spenta, e
  cinque configurazioni storte che non devono far cadere il servizio alle 7 del
  mattino.

- In Home Assistant arrivano due entità distinte: l'**interruttore** del
  servizio, che dice se gli orari valgono, e l'**azione «Ferma la sveglia»**,
  che si accende da sola mentre squilla. Fermare lo squillo di stamattina non
  deve cancellare la sveglia di domani.

## [7.6]

- **La musica AirPlay esce davvero da una scheda che non fa 44100 Hz.** La
  7.4.1 ripiegava sul convertitore di ALSA (`plughw:`), e sul campo il
  risultato è stato il peggiore possibile: dispositivo aperto, nessun errore,
  nessuna musica.

  Il motivo è che shairport-sync non si limita a scrivere campioni: legge dal
  dispositivo il **ritardo** e con quello tiene la sincronia. Attraverso il
  plugin `plug` quel numero non è più quello vero, e shairport-sync insegue un
  bersaglio che si muove. La strada giusta era dire la verità alla scheda
  invece di nascondergliela — accesso esclusivo `hw:` più `output_rate` alla
  frequenza che la scheda sa fare davvero, lasciando il ricampionamento a
  shairport-sync, che ha soxr compilato dentro.

  **Provato a mano sul Raspberry prima di scriverlo nel codice.** Con
  `output_device = "hw:1,0"` e `output_rate = 48000` la musica esce.

  Ordine dei tentativi: 44100 in accesso esclusivo; poi 48000, 96000 e 88200
  sempre in esclusivo con ricampionamento; e solo come terza spiaggia il
  convertitore. Le due righe si sanno anche **togliere**: collegando poi una
  scheda che i 44100 li fa, un `output_rate` dimenticato la inchioderebbe a
  una frequenza che non le serve più. Una configurazione va saputa disfare,
  non solo fare.

- **I dieci minuti per vedere la cassa fra i device AirPlay non erano un
  guasto.** Interrogando l'mDNS direttamente dal Raspberry, il DMD si annuncia
  **subito**, insieme alle altre otto casse di casa. È la cache Bonjour
  dell'iPhone, che dopo un riavvio di shairport-sync tiene la voce vecchia
  finché non scade. Sul telefono si risolve in cinque secondi di modalità
  aereo; e il DMD riavvia shairport-sync solo quando la sua configurazione
  cambia davvero, quindi a regime non succede.

## [7.5]

- **Il meteo si vede.** La segnalazione era «è veramente raro vedere il
  meteo», e non era un'impressione da discutere: facendo scorrere una
  giornata intera davanti alla sorgente vera e contando, erano **sette
  apparizioni in ventiquattro ore — 94 secondi su 86400, cioè lo 0,11% del
  tempo.** Praticamente mai.

  La causa era che un solo numero faceva due mestieri. `ogni_ore` decideva
  insieme quando **chiedere** i dati a Open-Meteo e quando **mostrarli**, e le
  due cose non hanno lo stesso ritmo: una previsione non cambia ogni venti
  minuti, ma per rimostrarla non c'è nessun bisogno di richiederla — quella
  che si ha in mano va benissimo, ed è già marcata con la sua età.

  I due orologi adesso sono separati:

  | | | |
  |---|---|---|
  | **Dati richiesti ogni** | 4 ore | quante volte si interroga Open-Meteo |
  | **Compare ogni** | 20 minuti | quante volte il meteo prende il pannello |

  Misurato dopo la correzione: **72 apparizioni al giorno, l'1% del tempo, e
  le chiamate alla rete restano sette** — identiche a prima. Gli intervalli
  sono regolari al minuto, non a raffica. Il bollettino del mattino resta uno
  solo e alle sette, e le allerte mantengono la precedenza su tutto: qualunque
  finestra rimette a zero l'orologio del giro, perché ripresentarsi venti
  secondi dopo un'allerta con lo stesso meteo sarebbe insistenza, non
  informazione.

  Scrivendo **0** nel campo nuovo si torna esattamente al comportamento della
  7.4, per chi il meteo lo preferiva raro.

## [7.4.1]

- **Una scheda audio che non sa fare 44100 Hz adesso suona lo stesso.**
  Correggendo la scelta automatica, la 7.4 ha finalmente puntato la chiavetta
  USB invece dell'uscita HDMI — e ha scoperto che quella chiavetta dichiara:

  ```
  Playback:  Rates: 8000, 48000
  ```

  AirPlay trasmette a 44100 e a nient'altro. In accesso esclusivo ffmpeg
  rispondeva `sample rate 44100 not available, nearest is 48000`, e
  l'interruttore dell'uscita musicale si ridisattivava da solo a ogni
  salvataggio. **Non era un difetto nuovo**: era quello vecchio che diventava
  visibile, perché prima si provava l'HDMI — che si apre senza protestare e
  non suona niente.

  Ora, se la prova in accesso esclusivo fallisce, si riprova la stessa scheda
  con il convertitore di ALSA davanti. La preferenza per `hw:` resta giusta —
  con `plughw:` shairport-sync non vede più che cosa la scheda sappia fare
  davvero — ma quel dettaglio conta per la sincronizzazione fra più casse, che
  con una cassa sola non esiste, e l'alternativa qui era il silenzio. La
  pagina lo scrive quando succede: un compromesso taciuto è una sorpresa
  rimandata.

  La trappola di questa correzione stava nel riallineamento introdotto dalla
  7.4: dopo il ripiego in configurazione c'è `plughw:1,0`, e un confronto che
  si aspettasse `hw:1,0` avrebbe riscritto e riavviato shairport-sync **a ogni
  avvio del DMD, per sempre**. Una prova lo verifica su tre avvii di fila.

- **La riga dell'uscita musicale dice finalmente la cosa giusta.** Era già
  stata riscritta una volta, e mostrava ancora il dispositivo di
  shairport-sync: a interruttore spento si leggeva `hw:CARD=Dummy` e sembrava
  che il DMD avesse scelto la scheda finta. Ora nomina la scheda scelta in
  Impostazioni — «USB Audio», non `plughw:1,0` — in tutti e due gli stati, dice
  da quale scheda *uscirebbe* la musica quando l'interruttore è spento, e se le
  due configurazioni divergono lo segnala invece di lasciarlo indovinare.

## [7.4]

- **Now Playing non partiva, e la causa era un indirizzo scritto in due
  posti.** Il telefono vedeva la cassa, la musica usciva, e sul pannello non
  compariva niente — senza un errore da nessuna parte, perché dal punto di
  vista di ognuno dei due programmi andava tutto bene. Il broker di casa aveva
  cambiato indirizzo, la pagina web aveva aggiornato la configurazione del
  DMD, e `/etc/shairport-sync.conf` era rimasto a puntare a quello vecchio.
  Due file che devono dire la stessa cosa, e nessuno incaricato di tenerli
  allineati.

- **La domanda giusta però era un'altra: perché due programmi sulla stessa
  macchina si parlano attraverso un server di rete?** shairport-sync sa già
  scrivere i metadati in una pipe locale, e i codici a quattro lettere che ne
  escono — `minm`, `asar`, `asal`, `prgr`, `pfls` — sono *gli stessi* che il
  DMD gestisce da sempre. Nessun indirizzo, nessuna porta, nessuna password,
  niente da tenere allineato. Il DMD configura shairport-sync da solo al primo
  avvio: è una scrittura nel suo file e un riavvio, e la volta dopo non serve
  più. È anche l'unico modo perché una macchina già installata riceva la
  funzione, visto che l'aggiornamento via rete non esegue nessuno script.

  **MQTT resta e continua a funzionare esattamente come prima.** Chi ha già
  tutto configurato non deve toccare niente: le due strade finiscono nella
  stessa funzione. Ma chi non usa Home Assistant adesso può spegnere MQTT
  senza perdere la musica, e prima non era vero.

  Il parser ha una prova che parte dai casi cattivi e non da quelli buoni:
  l'elemento che arriva spezzato fra due letture, il base64 che va a capo, la
  copertina binaria che non deve essere rovinata da una decodifica in utf-8,
  la spazzatura prima del primo elemento, il tetto alla memoria. L'ultima non
  simula niente: crea una FIFO vera, ci scrive dentro come farebbe
  shairport-sync, e guarda che dall'altra parte esca il brano.

- **Breakout perdeva i suoi suoni, e i due sintomi erano un bug solo.** Con la
  palla ferma appoggiata alla racchetta, prima del lancio, quel ramo viene
  attraversato a ogni fotogramma — e ci suonava dentro: trenta `racchetta.wav`
  al secondo, da 50 ms l'uno. Era il ronzio continuo e sovrapposto prima di
  premere fuoco. Ed era anche il motivo per cui i mattoni non si sentivano: il
  mixer tiene otto voci insieme e restava perennemente pieno di copie dello
  stesso colpo, sommate fino a saturare — i mattoni li suonava, ma dentro un
  segnale già clippato non si sentivano.

  Misurato prima e dopo, su una partita vera di venti secondi: **438 chiamate,
  di cui 433 di troppo; adesso 7.** Invaders, che non si era mai lamentato,
  stava a 2 al secondo da sempre. La prova gioca davvero una partita — la
  logica del gioco non legge niente da sola — e conta le chiamate invece di
  ascoltarle: se un domani un gioco supera la soglia di sovrapposizione, lo
  dice una misura e non un orecchio.

- **La scelta automatica della scheda audio mandava tutto in un'uscita HDMI
  scollegata.** La regola diceva "l'ultima scheda non fittizia", ed era stata
  scritta quando in elenco c'erano solo la scheda finta e la chiavetta USB. Su
  un Pi 4 l'elenco vero è `0 Dummy, 1 USB Audio, 2 vc4hdmi0, 3 vc4hdmi1`: le
  due uscite HDMI si registrano **dopo** la USB e le passavano davanti.
  Silenzio perfetto, senza un errore da leggere. Ora le uscite interne del
  Raspberry — l'HDMI e il jack, che con questo pannello non può funzionare
  perché la libreria della matrice si prende lo stesso blocco PWM — sono
  l'ultima risorsa e non la prima scelta. Chi ne sceglie una a mano viene
  accontentato lo stesso.

- **Di notte il DMD abbassa la voce.** Sleep mode e display spento erano già
  silenziosi, ma non per una regola sull'audio: lì il ciclo si ferma prima di
  scegliere una sorgente, e il suono nasce proprio da quel momento. Il night
  mode invece lascia il pannello al lavoro, solo più fioco — e alle tre di
  notte un aereo di passaggio suonava l'avviso a volume pieno.

  C'è un **volume notturno**, con la stessa forma della luminosità notturna e
  predefinito **0, cioè muto**. Vale per quello che il pannello dice di sua
  iniziativa: un aereo, un compleanno, una notifica. Non per una partita, che
  è una cosa che stai facendo tu adesso — la stessa eccezione che lo Sleep
  mode fa già per chi tiene il pannello occupato.

  E lo slider della pagina continua a mostrare il volume di giorno. Non è un
  dettaglio: se mostrasse quello in vigore, aprire la pagina di notte e
  premere Salva scriverebbe zero in configurazione per sempre. È lo stesso
  inganno dello slider della luminosità durante il night mode, che questo
  progetto ha già pagato una volta.

- **L'uscita musicale segue la scheda scelta in Impostazioni.** L'interruttore
  la fotografava una volta sola, nell'istante in cui lo si premeva: cambiando
  scheda dopo, shairport-sync restava sulla vecchia e nessuno lo diceva.
  Stessa malattia dell'indirizzo del broker, stessa cura — comanda
  Impostazioni, e il riallineamento avviene al salvataggio e a ogni avvio.

- La riga in gergo ALSA sotto l'uscita musicale — `hw:3,0` e basta — è
  riscritta in italiano. Sembrava un campo da compilare, ed è stata letta come
  una seconda scelta della scheda audio: la scheda si sceglie in un posto
  solo, che è Impostazioni.

## [7.3]

- **La copertina del brano sul pannello — e una decisione ribaltata, con
  cautela.** Fino alla 7.2 la copertina *non* si mostrava, e nel progetto
  c'era scritto perché: è fatta quasi solo di mezzi toni, cioè il contenuto
  peggiore possibile per un pannello S-PWM. Non era una svista: metà della
  storia di questo progetto è una caccia allo sfarfallio causato dai mezzi
  toni, e `safe_colors` esiste esattamente per quello.

  Quella decisione non è stata cancellata ma **aggirata con uno strumento già
  in casa**: la Funcam mostra una telecamera su questo stesso vetro riducendo
  i livelli di colore per canale, e funziona. La copertina passa dalla stessa
  riduzione. A quattro livelli — il valore di partenza — resta riconoscibile
  con la maggior parte dei mezzi toni tolti; a due restano gli otto colori
  pieni, quelli che non sfarfallano mai; a zero si lascia com'è, da provare e
  non da dare per buono.

  Il disordine di Floyd-Steinberg non è un abbellimento: senza, una faccia in
  otto colori diventa una macchia di campiture piatte. Con, l'occhio rimette
  insieme le sfumature da solo.

- **L'altezza è fissa, la larghezza no.** Una copertina di un disco è quadrata,
  una locandina di Apple TV no. Forzare il quadrato vorrebbe dire tagliare o
  mettere le bande nere — una decisione da prendere, e sbagliata in tutti e due
  i modi. Fissando l'altezza al pannello e lasciando libera la larghezza non
  serve nessuna decisione, con un tetto a metà pannello perché una panoramica
  alta 64 sarebbe larga centoquaranta e lascerebbe i titoli senza spazio.

- **Non si scarica mai dove si disegna.** Il ciclo gira a trenta fotogrammi al
  secondo; una richiesta HTTP può metterci dieci secondi a fallire. Chiedere
  una copertina non scarica e non aspetta: guarda in cache, mette in coda e
  torna subito. Una prova misura i millisecondi di cinquanta richieste invece
  di fidarsi del commento.

  Due difetti trovati dalle prove, non dal ragionamento. Il primo: con un
  server lento la stessa copertina veniva chiesta più volte, perché fra
  l'uscita dalla coda e l'arrivo in cache l'indirizzo non stava in nessuno dei
  due posti. Il secondo, più istruttivo: il limite dei livelli era stato
  copiato dalla Funcam a otto, ma la Funcam quantizza con l'aritmetica mentre
  qui si usa una tavolozza — e PIL ne tiene **256 colori**, mentre otto livelli
  ne vorrebbero 512. La tavolozza veniva troncata, le combinazioni con molto
  rosso sparivano, e **una faccia color pelle diventava verde**. Il limite è
  sei.

- **Nessuna credenziale, ed è il motivo della strada scelta.** L'indirizzo
  delle copertine di Home Assistant porta *dentro di sé* un token firmato: si
  scarica senza intestazione di autenticazione, quindi sul Raspberry non resta
  nessun segreto. Se un giorno servisse un token a vita lunga, questa strada
  andrebbe riprogettata invece che allargata.

- **La rotazione: una volta ogni N foto.** Modalità nuova per Now Playing:
  `sempre` come è sempre stato, oppure `rotazione`, in cui il brano prende il
  pannello una volta ogni tot media invece di tenerlo per tutto il tempo in cui
  suona.

  Il conto è sui **media mostrati**, non sui minuti, e il contatore non è stato
  inventato per l'occasione: il Media Player lo teneva già per la sua riga di
  stato. Era la strada più corta e per una volta era anche quella giusta —
  «uno ogni cinque foto» è una frase sulle foto, e misurarla in minuti avrebbe
  dato un numero diverso a ogni cambio di durata.

  Senza Media Player acceso la rotazione **decade a `sempre`**: la rotazione
  esiste per dividere il pannello con le foto, e senza foto non c'è niente da
  dividere. La priorità resta 58: è una modalità della sorgente, non un
  rimescolamento dell'arbitro.

- **E senza copertina il pannello è esattamente quello di prima.** Non tutte
  le sorgenti la espongono — un ingresso HDMI non ce l'ha proprio — quindi
  metà della suite non prova la funzione nuova: prova che senza di essa
  l'impaginazione sia identica a quella di ieri, e non una versione ristretta.

## [7.2]

- **I satelliti diventano un servizio notturno, e lo dicono.** La segnalazione
  era *«non ha senso che venga mostrato di giorno»*, e aveva ragione — ma la
  causa era più stretta di così, e vale la pena scriverla perché è il motivo
  per cui il rimedio è questo e non un altro.

  I passaggi **visibili** non potevano già comparire di giorno: «visibile»
  significa satellite illuminato dal Sole mentre qui è buio, con il buio
  fissato a −6° di altezza solare. Quello che compariva era la **cartolina**
  grigio-azzurra dei passaggi che ci sono e non si vedono, che non aveva
  nessuna condizione di buio: la ISS che passa a 70° alle 14:20 finiva sul
  vetro. Di notte quella cartolina serve — risponde a «perché stasera il DMD
  non ha detto niente?» — di giorno è rumore che ruba il pannello al meteo e
  alle foto.

  Ora c'è un cancello sull'altezza del Sole, regolabile nella pagina
  Satelliti: a **3°** sopra l'orizzonte il servizio si apre un quarto d'ora
  prima del tramonto e si chiude poco dopo l'alba; a `0` esattamente al
  tramonto; a `90` non si chiude mai, che è com'era prima.

- **La soglia non è −6°, e questa è la scelta di progetto che conta.**
  Verrebbe naturale riusare quella della visibilità, e sarebbe un difetto: il
  preavviso scatta **dieci minuti prima** che il satellite sorga, e in dieci
  minuti il Sole scende di due o tre gradi. Con il cancello a −6° un passaggio
  che diventa visibile appena sotto quella soglia avrebbe il suo preavviso
  soppresso, perché dieci minuti prima il Sole stava a −3° — cioè sparirebbe
  proprio l'avviso della prima sera, quello più comodo, e nessuno saprebbe
  dire perché.

  Una prova misura quanto scende davvero il Sole in dieci minuti attorno al
  tramonto e pretende che il margine sia più largo di quella discesa. Così
  resta vera anche se un giorno si cambiasse il preavviso: diventerebbe rossa
  qui, invece di far scoprire l'avviso mancante sul terrazzo.

- **Il cancello ferma il vetro, non il resto.** I passaggi si continuano a
  calcolare, il registro a scrivere, i sensori MQTT a pubblicare, e la pagina
  Satelliti risponde alle nove del mattino alla domanda «quando passa
  stasera». È la regola che il modulo aveva già scritta e che qui si applica
  al Sole: il filtro è una scelta di cosa **mostrare**, non di cosa **sapere**.
  Se al tramonto il servizio si svegliasse senza sapere niente, perderebbe il
  primo passaggio della sera — cioè proprio quello per cui esiste. Una prova
  legge l'albero sintattico del modulo e verifica che `e_notte` compaia nel
  disegno e **non** negli altri tre.

- **E la riga di stato lo dice.** *«in attesa del tramonto (Sole a 45°, soglia
  3°)»*, accanto al prossimo passaggio che resta scritto. Un servizio acceso
  che non mostra niente e non spiega perché sembra rotto.

## [7.1]

Tre segnalazioni arrivate guardando la 7.0 **accesa**, che è l'unico collaudo
che conta davvero. Nessuna delle tre l'avrebbe trovata una suite: due si vedono
solo su un vetro da 256×64 in un salotto, e la terza è una frase che aveva
smesso di dire la verità.

- **La finestra del meteo, ridisegnata dopo la prima sera sul vetro.** Sette
  segnalazioni dal campo, e la più importante è: *«non si capisce la
  temperatura attuale»*. Aveva ragione, ed era un difetto di impostazione: il
  bollettino mostrava massima e minima grandi al centro, che si leggevano come
  il dato di adesso — e quello vero non c'era da nessuna parte.

  Adesso le due finestre hanno lo stesso impianto, e non è pigrizia: la prima
  cosa che si guarda è sempre la stessa. In mezzo, grande e centrata, la
  **temperatura di adesso** con accanto l'**umidità** — che è salita lì dalla
  riga in fondo, dove non la guardava nessuno, e ci sta bene perché è un numero
  che si legge insieme alla temperatura: ventisei gradi con il settanta per
  cento sono un'altra giornata rispetto a ventisei asciutti. In alto a destra,
  piccole, massima e minima con una **freccia** ciascuna.

  Le frecce sono disegnate, non scritte: i caratteri di freccia esistono ma non
  tutti i font li hanno, e una freccia che diventa un rettangolo vuoto è peggio
  di nessuna freccia.

  E c'è l'**unità**, che prima mancava del tutto — scritta una volta sola, sul
  numero grande: ripeterla accanto a massima e minima riempirebbe la riga di
  lettere invece che di numeri. Si sceglie fra Celsius e Fahrenheit nella
  scheda del Meteo; le previsioni si chiedono sempre in Celsius e si convertono
  al momento di scrivere, così cambiare unità non invalida la previsione già
  scaricata e non costa una chiamata.

  In basso, la temperatura percepita — ma solo quando differisce di almeno un
  grado e mezzo. «18 gradi, percepiti 18» è una riga sprecata; con vento o afa
  quella differenza è il motivo per cui uno si mette la giacca.

  La prova di tutto questo non guarda il testo: conta i **pixel accesi** per
  fascia orizzontale e pretende che la centrale sia la più luminosa, perché è
  lì che sta il numero che deve rispondere per primo.

- **Tre pulsanti che si toccavano.** Nella scheda del Meteo i tasti di prova
  stavano a dodici pixel l'uno dall'altro e si leggevano come un blocco unico.
  Su due pulsanti corti non si era mai notato; su tre lunghi, sì. Lo stacco
  passa a sedici.

- **Un testo che era diventato falso.** La scheda del Meteo diceva ancora che
  la posizione «è quella della pagina Radar», dove non sta più dalla 7.0. È il
  prezzo tipico di uno spostamento: il codice si aggiorna perché altrimenti non
  funziona, le frasi no — nessuno le compila. L'ha trovato una schermata, non
  una prova: nessuna suite controlla che quello che c'è scritto sia ancora
  vero.

## [7.0]

- **Il meteo.** Due finestre, e la differenza non è la quantità di dati ma a
  che domanda rispondono. Al mattino il **bollettino della giornata** —
  massima, minima, umidità, probabilità di pioggia, alba e tramonto — che
  risponde a *come mi vesto*. Poi ogni poche ore un **aggiornamento** con la
  temperatura di adesso, grande, che risponde a *adesso*.

  Non è sempre acceso, ed è la scelta che conta di più. Un pannello che mostra
  il meteo tutto il giorno smette di essere guardato dopo due giorni: diventa
  sfondo. Quattro o cinque finestre al giorno, invece, si leggono — la stessa
  ragione per cui i Compleanni e le Scadenze parlano poco.

  E non prende mai il pannello a forza: priorità 54, sotto il Rolling Banner e
  molto sotto il radar. Il meteo non è mai urgente al punto da interrompere una
  partita o il passaggio della Stazione. Una prova legge l'albero sintattico
  del modulo per verificare che `hold_on` non ci sia — e che la sorgente non
  conosca nemmeno l'arbitro, quindi non potrebbe prenderlo neanche volendo.

- **Le previsioni arrivano da Open-Meteo, che non chiede nessuna chiave.** Non
  è una comodità, è una proprietà di sicurezza: non c'è nessun segreto da
  custodire sul Raspberry, niente da togliere dalla configurazione esportata,
  niente che possa finire in una schermata o in un registro. Tutti gli altri
  problemi di riservatezza di questo progetto si sono risolti *togliendo* cose
  — le coordinate dal codice, la password dal file esportato, i token in un
  file a parte. Qui non c'è proprio niente da togliere.

  La posizione è quella già configurata nella pagina Radar. Se è a zero, il
  meteo non chiede niente a nessuno e lo dice: zero-zero sta in mezzo
  all'Atlantico, e il meteo del golfo di Guinea non aiuterebbe nessuno a capire
  che manca una configurazione.

- **Le icone sono disegnate, non caricate.** A una trentina di pixel un PNG
  scalato diventa una poltiglia: le forme si riconoscono per i bordi, e i bordi
  a trenta pixel sono due o tre pixel. Tredici icone fatte di cerchi, linee e
  poligoni — e sono **meno dei codici meteo**, perché a quella dimensione la
  differenza fra pioviggine moderata e intensa non si può disegnare, e due
  icone identiche con due nomi diversi sarebbero una bugia grafica.

  Di notte cambia una cosa sola: con il cielo sereno si disegna la Luna. Una
  nuvola di notte resta una nuvola.

- **Un puntino quando la previsione è vecchia.** Distingue *fa diciotto gradi*
  da *faceva diciotto gradi stamattina, poi è caduta la rete*. Non una frase:
  chi guarda di sfuggita non la leggerebbe, e chi nota il puntino va a vedere
  la pagina Servizi, dove c'è scritto per esteso.

- **Cinque entità in Home Assistant**, e nessuna è un doppione di una stazione
  meteo in giardino: quella misura un punto, questa prevede le prossime ore. È
  su una previsione che si costruisce un'automazione come chiudere la
  tapparella *prima* del temporale.

- **Le allerte meteo, e come si è deciso da dove prenderle.** Sulla carta le
  fonti erano tre e tutte incerte: MeteoAlarm risultava aver dismesso il feed
  RSS; il successore MeteoGate non documentava l'accesso libero; il repository
  del Dipartimento della Protezione Civile — che pubblica ogni giorno il
  bollettino sulle 156 zone di allerta — dichiarava sé stesso *«in fase di
  caricamento»* con la sezione sul formato dei dati vuota.

  La scelta era fra indovinare e chiedere. Si è chiesto: tre `curl` dal
  Raspberry, che ha la rete libera. Il feed dato per morto risponde **200**;
  l'API per posizione risponde **Not Found**. Nessuna delle due cose si poteva
  sapere leggendo la documentazione — ed è il motivo per cui questa versione ha
  le allerte invece di una funzione vuota con una spiegazione.

  Il feed è Atom con dentro **CAP 1.2**: ogni avviso porta il codice della zona
  (`IT018`), il nome in chiaro (`Sicilia`), il tipo di evento, la gravità
  normalizzata e gli orari di inizio e scadenza. L'avviso prende **tutto il
  pannello**, con la barra colorata a sinistra e il triangolo: una striscia in
  cima al bollettino si legge come un'etichetta, un pannello intero si legge
  come un avviso, e chi passa in corridoio deve capire che c'è qualcosa prima
  di aver letto una parola.

  Compare **quando arriva**, non al prossimo giro delle quattro ore, e poi non
  si ripete: vive in una tacca colorata nell'angolo delle altre finestre. Un
  avviso che ricompare ogni minuto smette di essere un avviso in mezza
  giornata.

  **La regione si sceglie a mano**, da una tendina. Il feed copre il paese
  intero, e senza regione non si mostra *niente* — non tutto: far comparire
  l'allerta della Sicilia a chi sta in Piemonte non è un'approssimazione, è un
  allarme falso. Il confronto è sul nome e tollerante ad accenti, maiuscole e
  apostrofi, perché `Valle d'Aosta`, `Valle d’Aosta` e `valle daosta` sono la
  stessa cosa per chiunque tranne che per un confronto fra stringhe.

  Due difetti li ha trovati la suite, non il ragionamento. Il primo: con gli
  apostrofi trasformati in spazi, `valle daosta` non trovava più la Valle
  d'Aosta. Il secondo, peggiore: la regola di tolleranza accettava qualunque
  parola contenuta nel nome, e così **«Aosta» prendeva gli allarmi della Valle
  d'Aosta** — una regione che riceve gli avvisi di un'altra, che in un impianto
  di allerte è il difetto più grave possibile. Ora la regione scelta dev'essere
  l'*inizio* del nome della zona.

  E quello che non si mostra conta quanto quello che si mostra: gli avvisi
  scaduti, quelli annullati, e le prove di sistema (`Test`, `Exercise`) — che
  esistono nello standard CAP proprio perché chi li riceve non li mostri.

- **I nomi lunghi dei satelliti finivano sopra l'arco.** Segnalato dal campo
  con una foto: `OKEAN-O` scritto a corpo pieno si sovrapponeva alla curva del
  passaggio. Il difetto era vecchio quanto la funzione e non si era mai visto,
  perché l'unico nome mai comparso era `ISS` — tre caratteri, che ci stanno
  ovunque. È bastato accendere «tutti gli oggetti» perché saltasse fuori.

  Il troncamento a otto caratteri che c'era prima non era una misura, era una
  speranza: otto caratteri stretti e otto larghi occupano larghezze diverse.
  Adesso si misura davvero, e si rimpicciolisce il corpo prima di tagliare —
  un nome piccolo si legge ancora, un nome tagliato non si riconosce. Quando
  proprio si taglia, si dice con i puntini: `SPACEMOBILE-00` è un nome
  plausibile e sbagliato, `SPACEMOBILE-0…` è un nome incompleto e si vede.

  Nel preavviso è cambiata anche la priorità dello spazio: prima il nome
  prendeva il corpo pieno e il conto alla rovescia si rimpiccioliva per stargli
  dietro. Adesso è il contrario, perché il conto è la cosa che serve in quel
  momento e il nome è il contorno.

  La prova non guarda il testo, guarda i **pixel**: nella colonna dove comincia
  l'arco non ci dev'essere niente acceso, con cinque nomi da tre a venti
  caratteri. E verifica anche il contrario, che `ISS` resti grande:
  rimpicciolire tutto per prudenza renderebbe illeggibile da tre metri anche il
  caso normale.

- **Una posizione sola per tre servizi.** Le coordinate stavano nella pagina
  Radar, e finché il radar era l'unico a usarle andava bene. Poi sono arrivati
  i satelliti, e adesso il meteo: la stessa informazione serve a tre servizi, e
  chi accendeva i satelliti andava a cercarla nella pagina sbagliata — o non la
  trovava e concludeva che il servizio fosse rotto.

  Adesso sta in **Impostazioni**, e le pagine che la usavano ci rimandano. La
  migrazione copia il valore vecchio e **non lo cancella**: se qualcuno
  ripristina un backup su una versione precedente, quella deve ancora trovarlo
  dov'era. Una posizione persa in un aggiornamento vuol dire tre servizi muti e
  nessun messaggio che spieghi perché.

  E l'esportazione senza posizione azzera **tutti e due** i posti in cui può
  trovarsi: azzerarne uno solo darebbe un file che *sembra* ripulito e non lo
  è, che è peggio di uno che non lo è e si vede.

- **Quello che la suite prova, e quello che non prova.** Non prova che diciotto
  gradi siano diciotto gradi: quello lo dice Open-Meteo e non abbiamo modo di
  contraddirlo. Prova che una risposta **mutilata** — colonne mancanti, valori
  nulli, tipi sbagliati, liste più corte del previsto — produca un bollettino
  con meno numeri invece di un'eccezione; che la rete giù non cancelli la
  previsione di stamattina; che non si richieda **specialmente quando
  fallisce**, che è il caso in cui il codice ingenuo martella un servizio
  gratuito fino a farsi bloccare; e che il disegno non scriva mai fuori dal
  pannello, nemmeno con una descrizione lunga e temperature a due cifre sotto
  zero.

## [6.9]

- **Il cursore della luminosità non mente più durante il Night mode.** Con
  Night mode attivo il pannello usa la luminosità notturna, ma il cursore
  principale restava manovrabile: si muoveva, non cambiava niente, e faceva
  pensare che il pannello fosse guasto. Un comando che accetta e non agisce è
  peggio di un comando assente, perché non dà nemmeno un errore da cercare.

  Adesso nella pagina è disabilitato per la durata della fascia notturna, e
  dice il perché e quanto vale la luminosità in uso. In Home Assistant
  l'entità si dichiara **non disponibile**, con due condizioni invece di una
  (`availability_mode: all`): il DMD acceso *e* il Night mode spento. E un
  comando che arrivasse lo stesso — un'automazione che pubblica sul topic —
  viene rifiutato con una riga nel registro, invece di essere accettato e
  ignorato.

- **Un interruttore per spegnere il pannello.** Mancava del tutto: chi voleva
  il buio doveva staccare la spina a un Raspberry acceso, che è il modo
  classico di rovinare la scheda SD. Spegne **solo il vetro**: il radar
  continua a registrare, le notifiche arrivano, la pagina web risponde.

  Vince su tutte le eccezioni di Sleep mode. Una partita aperta impedisce a
  Sleep mode di spegnere il pannello in faccia a chi sta giocando — giusto —
  ma se sono io ad aver premuto «spegni», quella cortesia diventerebbe un
  pannello che non si spegne e non si capisce perché. E resta spento anche
  dopo un riavvio del servizio: uno spegnimento che si annulla da solo
  aggiornando il DMD non sarebbe uno spegnimento.

  In Home Assistant è un interruttore che si chiama **Display**, e ON vuol
  dire acceso. La configurazione dentro dice `off`, perché le impostazioni si
  scrivono come eccezioni, ma nessuno accetterebbe un interruttore chiamato
  «Display spento» da tenere OFF.

- **Il Game Boy compare in Home Assistant.** Doom e i giochi scritti per il
  pannello avevano il loro interruttore, PyBoy no — ed era rimasto fuori per
  una ragione che si vede solo guardando da dove arrivano gli altri: i giochi
  del pannello si costruiscono dall'elenco di `sources.giochi`, e PyBoy non è
  in quell'elenco, è un runtime a sé con il suo processo e le sue cartucce.
  Acceso da Home Assistant parte con la ROM già configurata, come premere il
  tasto della console senza cambiare cartuccia.

- **Il totale dei voli registrati esce su MQTT.** `Aerei oggi` risponde a «che
  giornata è stata», questo a «quanti ne ho visti da quando l'ho acceso». Si
  conta il registro una volta sola e poi si tiene il numero a mente: il ponte
  pubblica ogni due secondi, e rileggere migliaia di righe per un valore che
  cambia due volte all'ora sarebbe stato lo stesso spreco silenzioso già
  evitato per il conteggio di oggi.

- **`pianeti.py`: dove sono i pianeti e la Luna, senza rete.** Non fa ancora
  niente di visibile — è la base della finestra del cielo — ma è completo e
  verificato. Posizioni dalla tabella JPL degli elementi approssimati, Luna
  con la serie di Meeus, magnitudini con le formule classiche. Nessuna
  dipendenza nuova: solo `math`, perché l'aggiornamento via rete non esegue
  `install.sh`.

  Verificato contro `pyephem` — effemeridi complete, scritte da altri — su
  quattro anni, quattro posti della Terra e quattro ore del giorno: lo scarto
  massimo è di **2,8 primi d'arco** per i pianeti e **1,4** per la Luna, un
  ventesimo del diametro della Luna piena.

  E il confronto ha trovato subito un difetto che il ragionamento non aveva
  visto: gli elementi dei pianeti sono riferiti all'equinozio J2000, la serie
  lunare a quello **della data**. Applicare la precessione a entrambi sembra
  coerente ed è sbagliato per la Luna di mezzo grado — una luna piena intera,
  scritta sul pannello con la stessa sicurezza. Nella suite il difetto viene
  rimesso apposta, per vedere la prova diventare rossa.

## [6.8.1]

- **La procedura di pubblicazione, con dentro anche gli inciampi.**
  [`docs/pubblicazione.it.md`](docs/pubblicazione.it.md) descriveva bene il
  caso normale e taceva le due cose che erano costate tempo davvero.

  La prima: **dopo il push il DMD può dire «sei aggiornato» ancora per cinque
  minuti.** Chiede la versione a `raw.githubusercontent.com`, che è una rete
  di cache e serve il file con `max-age=300`. Su GitHub, nel browser, il file
  nuovo si vede subito — ed è la trappola: sembra che l'aggiornamento
  automatico sia rotto, e invece nessuno dei due ha torto. È successo con la
  6.1. Ora c'è il comando che dice quello che vede il Raspberry, e non quello
  che vede il browser.

  La seconda: **che fare quando un push porta più versioni insieme.** Capita
  sempre: si lavora per giorni, ogni correzione alza il numero, e su GitHub si
  arriva quando si arriva. Un commit solo — uno per versione non
  ricostruirebbe gli stadi intermedi, li falsificherebbe — e **nessun tag
  intermedio**: un tag punta a un commit, e il commit è uno, quindi le
  versioni di mezzo finirebbero tutte sullo stato dell'ultima. Una release
  sola, con dentro le note di tutte le versioni che il push contiene.

  E due etichette nuove sul repository, `mqtt` e `adsb`: sono le parole con
  cui questa roba si cerca davvero, e non c'erano. La descrizione del progetto
  dice adesso che Home Assistant parla **in due direzioni**, che dalla 6.6 non
  è una funzione in più ma la differenza fra un dispositivo che si osserva e
  uno che si usa.

## [6.8]

- **Aerei e satelliti escono dal pannello e vanno in Home Assistant.** Il DMD
  sapeva già queste cose e se le teneva: il radar scrive un registro da
  millesettecento voli, i satelliti calcolano ventiquattro ore di passaggi, e
  tutto questo si vedeva solo sul vetro o nella pagina web — cioè solo se eri
  lì a guardare nell'istante giusto.

  Cinque entità nuove: **aerei registrati oggi** (azzerato da solo a
  mezzanotte), **aerei nel raggio** in questo istante, **l'ultimo passato**
  con rotta, quota e distanza negli attributi, **l'orario del prossimo
  passaggio** della Stazione e **quanti ne restano nelle 24 ore**.

  Due scelte che contano. Lo stato del passaggio è un **istante vero**
  (`device_class: timestamp`) e non una scritta: Home Assistant ci scrive
  «fra due ore» da solo, e un'automazione ci si aggancia con un trigger
  sull'ora — con una stringa qualunque il sensore sarebbe inutile senza dare
  errore. E negli attributi c'è **l'elenco completo delle ventiquattro ore**,
  che era poi la richiesta: sapere dei passaggi con un giorno di anticipo, non
  dieci minuti prima.

  Nell'elenco ci sono anche i passaggi che non si vedono, dichiarati come
  tali. Sul pannello non vanno — manderebbero qualcuno a cercare un puntino
  che non c'è — ma chi costruisce un'automazione decide da sé.

  Il conteggio degli aerei si tiene in memoria e non si rilegge dal CSV: il
  ponte MQTT pubblica ogni due secondi, e contare millesettecento righe di
  file a ogni giro per un numero che cambia due volte all'ora sarebbe stato
  uno spreco silenzioso.

## [6.7]

- **Il raggio del radar era un terzo di quello scritto nella pagina.** La
  distanza si chiedeva al provider in miglia nautiche con la virgola — 3 km
  sono 1,62 NM — e il provider la tronca all'intero. Un miglio: **1,85 km
  invece di 3**, cioè due terzi di cielo in meno in area. Da sempre.

  Non l'ha trovato una rilettura del codice: l'hanno trovato i dati. Nel
  registro di nove giorni la distanza massima è 1,82–1,85 km **ogni singolo
  giorno**, con il taglio esattamente su un miglio nautico; e le posizioni
  registrate formano un disco pieno (assi 0,96 e 0,66 km) e non il corridoio
  stretto che avrebbe spiegato la stessa cosa con la geometria del traffico.

  Adesso si chiede il numero intero arrotondato per eccesso, e il taglio fine
  lo fa la distanza calcolata qui: chiedere di più non costa niente, chiedere
  di meno fa perdere aerei in silenzio.

- **Il margine di cortesia.** Il radar guarda due chilometri più in là di
  quanto mostra, e gli aerei che cadono in quella fascia restano in memoria:
  la pagina Radar li elenca con la loro distanza vera. Non vanno sul pannello
  e non vanno nel registro.

  Nasce da una domanda tornata tre volte — *«è passato vicino e non l'ha
  visto»* — a cui finora si poteva rispondere solo misurando i pixel di una
  schermata di FlightRadar. Che è un pessimo modo di rispondere: la prima
  volta che ci ho provato ho sbagliato di due chilometri, e ho accusato le
  coordinate configurate che erano giuste a ottanta metri.

- **Now Playing dice «non lo so» come tutti gli altri.** Quando non suona
  niente il sensore mandava una stringa vuota, e in Home Assistant compariva
  bianco come se fosse rotto. Adesso dice `None`, che HA traduce in
  *sconosciuto*. È l'ultimo pezzo della correzione della 6.1, che allora si
  era fermata ai topic e non aveva guardato i template della discovery.

## [6.6]

- **Il pannello compare in Home Assistant accanto al telefono.** Il DMD si
  dichiara da solo come tre entità `notify`, una per livello. In
  un'automazione: *Aggiungi azione* → *Notifiche: invia un messaggio* →
  **DMD - avviso** dalla tendina, e il testo. Niente script da chiamare,
  niente campo da ricordare, e **il livello diventa la scelta del bersaglio**.

  Sotto, ogni entità pubblica su un topic per livello — `dmd/notifica/avviso`
  — e il DMD tratta il testo nudo come una notifica di quel livello. Tre topic
  invece di un `command_template` che costruisca il JSON, perché il DMD
  accetta già testo semplice: una cosa in meno che possa avere un errore di
  battitura, e una prova in meno da scrivere.

  Due dettagli che sembrano pedanteria e non lo sono. Le iscrizioni sono tre,
  esplicite: `dmd/notifica/#` coprirebbe **anche il topic padre**, per come è
  scritta la specifica MQTT, e ogni messaggio arriverebbe due volte. E un
  `livello` scritto dentro il JSON vince su quello del topic, altrimenti uno
  script che pubblica sul topic generico non potrebbe più mandare un allarme.

  Lo script resta, e serve ancora per la durata, il colore e il silenziatore:
  un'entità `notify` sa mandare solo un testo — ed è esattamente per questo
  che è comoda.

  La prova che conta verifica l'errore classico delle discovery: che il topic
  **dichiarato** sia lo stesso a cui il DMD **si iscrive**. Annunciarne uno e
  ascoltarne un altro non dà nessun errore — il messaggio parte, il broker lo
  accetta, e il pannello resta muto per sempre.

## [6.5]

- **L'arco del passaggio non è mai stato disegnato**, e mentre non lo
  disegnava teneva il pannello congelato.

  Trovato grazie a una fotografia con dentro l'ora esatta. Alle **22:49:17**
  il pannello mostrava `ISS → FRA 5 MIN / SORGE 22:48`: un promemoria «fra
  cinque minuti» per un passaggio sorto alle 22:48:06, un minuto prima. Il
  conto alla rovescia non era sbagliato — era un **fotogramma di sei minuti
  prima**, rimasto lì.

  Il meccanismo, una volta visto, è semplice e brutto: `_componi` costruiva il
  record del passaggio senza l'oggetto orbitale, e `_adesso` — la schermata
  dell'arco, quella che serve a chi è in terrazzo e sta cercando — faceva
  `passaggio["sat"]` e sollevava `KeyError: 'sat'`. Ma `_stato` era già stato
  scritto a `"adesso"` **prima** del disegno: la sorgente continuava a
  dichiararsi attiva, nessun'altra poteva prendere il posto, e l'ultimo
  fotogramma buono restava sul vetro finché il passaggio non finiva.

  Conseguenza: **l'arco non è mai comparso**, in nessun passaggio, da quando
  esiste. E il segnale c'era, scritto nella riga di stato della pagina
  Servizi: diceva `'sat'`, con le virgolette, che è come Python scrive un
  KeyError.

  Tre correzioni, una per anello:

  1. il record del passaggio si porta dietro il satellite che l'ha generato;
  2. **un disegno che fallisce molla il pannello** — chi non riesce a
     disegnare non ha diritto di occupare lo schermo. È la rete che copre la
     *classe* del difetto e non il singolo caso, la stessa idea del cane da
     guardia del radar;
  3. i tre passi del ciclo hanno tre reti separate: prima un errore nello
     scaricamento dei TLE o nella scrittura del registro — due cose che non
     riguardano il vetro — saltava anche il disegno.

  La prova costruisce un passaggio vero con la catena vera, usando un
  satellite sintetico invece di un TLE scaricato, e disegna l'arco. Togliendo
  la correzione torna rossa.

## [6.4]

- **Una freccia al posto di «FRA»** sul preavviso dei satelliti. Segnalato
  guardando il vetro, e con ragione: su un pannello a LED le parole corte in
  stampatello si leggono come sigle, e una sigla accanto a un numero sembra
  un'unità di misura. `→ 5 MIN` non si può leggere male, ed è pure due
  caratteri più corto.

- **Una cintura di sicurezza sul conto alla rovescia.** Se il passaggio è già
  sorto, l'avviso non si disegna. Non dovrebbe mai capitare — ci pensa la
  macchina a stati — ma «fra 5 min» accanto a «sorge 22:48» quando sono le
  22:49 è una bugia, e sul vetro una bugia non si distingue da un guasto.

- **Le briciole dei Mac nelle condivisioni.** Ogni volta che un Mac copia
  qualcosa su una condivisione SMB lascia un `.DS_Store` e, per **ogni
  singolo file copiato**, un gemello invisibile che comincia con `._` con
  dentro il resource fork. Su una libreria di migliaia di foto raddoppiano le
  voci che il Raspberry deve elencare a ogni giro. Adesso un giro dentro il
  servizio, ogni dodici ore, le toglie.

  Due scelte che contano. **Si cancellano nomi conosciuti**, non «tutto quello
  che comincia con un punto»: una cartella condivisa è di chi la usa, e una
  regola cieca si mangerebbe un `.stfolder` di Syncthing o un `.git` senza che
  nessuno capisca perché quella cosa ha smesso di funzionare. E c'è un
  pulsante **Guarda e basta**, perché questo è l'unico punto del programma che
  cancella file dell'utente, e chi vuole sapere cosa succederebbe prima che
  succeda deve poterlo fare in un clic.

  Sta dentro il servizio e non in un timer di systemd per la solita ragione:
  l'aggiornamento via rete non esegue `install.sh`, e un'unità nuova non
  arriverebbe mai sulle macchine già installate.

  Le prove hanno trovato **due difetti veri** prima che il codice girasse: il
  giro di prova cancellava lo stesso le cartelle di Spotlight e del cestino —
  cioè il pulsante che serve a non fare danni ne faceva — e la libreria non
  sarebbe stata pulita mai, perché il percorso veniva letto dalla sezione di
  configurazione sbagliata. Nessuno dei due dava errore: semplicemente non
  succedeva la cosa giusta.

## [6.3]

- **Un pulsante per provare le notifiche**, nel riquadro *Notifiche* della
  pagina Servizi: un campo di testo, i tre livelli, e via. Nasce da una sera
  di prove a vuoto — le notifiche arrivavano davvero, ma duravano dodici
  secondi e chi guardava il pannello arrivava sempre tardi; e per rimandarne
  una bisognava passare da Home Assistant, aprire *Strumenti per
  sviluppatori*, cercare l'azione. Un servizio che non si può provare da solo
  sembra rotto ogni volta che non lo guardi nell'istante giusto.

  **Passa dal broker**, e questa è la scelta che conta: consegnare la
  notifica dritta alla sorgente avrebbe provato soltanto il disegno, mentre
  così si provano quasi tutti gli anelli — broker raggiungibile, iscrizione
  viva, payload interpretato, pannello che disegna. Fuori resta solo Home
  Assistant, che da lì non si potrebbe provare comunque.

  Se il broker non risponde la notifica viene consegnata lo stesso, ma il
  messaggio lo dice: **due risposte diverse dicono quale metà funziona**, che
  è l'unica cosa che si voglia sapere premendo un pulsante di prova. Una sola
  risposta buona per entrambi i casi nasconderebbe proprio il guasto che si
  sta cercando. E a servizio spento il pulsante non finge: dice che è spento,
  invece di non far succedere niente e sembrare rotto.

## [6.2]

- **L'ora nel posto dell'orologio.** Il difetto è arrivato con una fotografia
  del pannello: il preavviso di un passaggio della Stazione diceva `ISS 21:10`
  in alto a destra e `FRA 5 MIN` sotto, e chi l'ha guardato ha capito «sono le
  21:10, allora passa alle 21:15». Lettura sbagliata e inevitabile: quel
  numero stava nella stessa posizione, con lo stesso corpo e quasi lo stesso
  colore dell'orologio che il pannello mostra tutto il resto del tempo. Non
  era un'ora scritta male, era **un orario di evento nel posto
  dell'orologio**.

  Adesso il posto grande lo prende il **conto alla rovescia** — anche perché è
  l'unica cosa che serva in quel momento — e l'ora scende sulla riga piccola
  con l'etichetta `SORGE` davanti, dove non può essere scambiata per altro.
  Con due corpi diversi sulla stessa riga le scritte si allineano sulla linea
  di base, e se il nome e il conto arrivassero a toccarsi il conto scende di
  corpo invece di sovrapporsi: misurato a ogni disegno, non stimato.

- **La durata, e quella giusta.** Sul preavviso mancava apposta, per non
  affollare una riga che si legge da tre metri. Ci torna perché è quella che
  decide se vale la pena infilarsi le scarpe — ed è la durata **visibile**,
  non quella geometrica. Il passaggio delle 22:48 del 12 settembre durava 5,9
  minuti sopra l'orizzonte e quaranta secondi prima di entrare nell'ombra
  della Terra: il pannello scrive `PER 40 S`, perché `6 MIN` sarebbe stato un
  invito a uscire per qualcosa che non c'era più.

- **MQTT trasloca da Musica a Rete.** Il modulo del broker era nato dentro
  *Musica* perché all'inizio dal broker passavano solo i metadati di AirPlay.
  Oggi ci passano gli interruttori dei servizi, la luminosità, le scadenze, i
  rifiuti e le notifiche in arrivo. Cercare l'indirizzo del broker sotto
  «Musica» era diventato un indovinello, e la domanda è arrivata dal campo in
  questi termini: *«dove cavolo si cambiano i dati di connessione mqtt?»*.
  Rete è comunque la pagina che si apre quando qualcosa non si collega.

  Nella pagina Musica restano i due topic da cui arriva il brano in ascolto:
  lì sono al posto giusto, perché non dicono *come* ci si collega ma *da dove
  arriva la musica*.

  Spostare un modulo di configurazione ha esattamente una trappola: i due
  moduli scrivono nella stessa sezione della configurazione, e un campo
  assente da una richiesta vale il suo valore predefinito — salvare il broker
  avrebbe azzerato in silenzio il topic di shairport, e salvare i topic
  avrebbe spento il broker. Due rotte separate, e due prove che partono da una
  configurazione riconoscibile e verificano che ognuna salvi la sua parte
  senza toccare l'altra.

- **Il riquadro MQTT della pagina Servizi ha un collegamento**, non più
  soltanto il nome della pagina scritto in una frase. Era l'altra metà della
  stessa domanda.

## [6.1]

Il verso che mancava. Fino a qui il DMD parlava tanto e ascoltava pochissimo:
pubblicava una trentina di topic verso Home Assistant e si iscriveva soltanto
ai comandi dei propri interruttori. Ma in casa la cosa che sa di più è Home
Assistant — sa chi c'è, se la porta è aperta, se l'allarme è inserito — e non
ha uno schermo in soggiorno. Il DMD ha lo schermo e non sa niente.

- **La casa parla al pannello.** Un solo topic (`dmd/notifica`), un JSON con
  tre campi, tre livelli. La politica — quando parlare, quando tacere, con
  che parole — sta in Home Assistant, dove stanno già le automazioni:
  duplicarla anche qui vorrebbe dire due verità che prima o poi divergono.

  **Sul livello si regge tutto.** Non è un'etichetta decorativa: decide il
  colore, se lampeggia e — la cosa che conta — se può interrompere una
  partita. `info` e `avviso` aspettano il loro turno come ogni altra
  sorgente; `allarme` si prende il pannello anche mentre giochi a Doom, con
  la stessa presa che usano gli emulatori. Ed è scomodo da usare apposta: se
  diventasse il livello di tutti, il pannello smetterebbe di essere un
  oggetto da soggiorno e diventerebbe una sveglia che non si spegne.

  Un messaggio malformato non spegne niente: si conta fra gli scartati e si
  dice nella riga di stato, invece di finire in un registro che nessuno
  legge. E un payload che comincia con `{` **deve** essere JSON valido — con
  il ripiego a testo semplice, un'automazione con un errore di battitura
  faceva scorrere `{rotto` in soggiorno, e chi guarda il pannello non ha modo
  di capire che il guasto è dall'altra parte.

- **Lo script pronto per Home Assistant**, in `docs/ha/dmd_notifica.yaml`:
  lo script `dmd_notifica`, cinque automazioni d'esempio e l'interruttore per
  zittire il pannello senza spegnere niente — con gli allarmi che passano
  comunque, perché altrimenti basterebbe dimenticare l'interruttore spento
  per non sapere che è entrato qualcuno. *Il manuale*,
  `docs/notifiche.it.md`, con il PDF.

- **I sensori che mandavano il vuoto.** Dal registro di Home Assistant,
  cinquanta righe al giorno di `Invalid state message '' from
  'dmd/scadenze/prossima'`. Un sensore dichiarato `device_class: date`
  riceveva una stringa vuota quando non c'era nessuna scadenza; HA prova a
  leggerla come data e protesta. Il modo corretto di dire «non lo so» a Home
  Assistant è la stringa `None`, che porta il sensore a *sconosciuto*.
  Corretto nei quattro punti che lo facevano: scadenze (data, titolo,
  giorni) e rifiuti.

  Il difetto **non si vedeva da questa parte**: il DMD pubblicava senza
  errori, il broker accettava, e solo il terzo anello della catena si
  lamentava. Quindi la prova che lo copre non legge il codice: cattura i 71
  messaggi veri e li valida contro la dichiarazione di discovery con cui li
  abbiamo annunciati. Se dichiariamo un sensore come data, deve arrivargli
  una data.

- **Lo script che rigenera i PDF** ora sta nel repository
  (`docs/mkpdf.sh`) invece che sulla macchina di chi pubblica. Era andato
  perso, e ricostruirlo ha richiesto di dedurre lo stile misurando colori e
  larghezza del testo dentro un PDF già pubblicato.

## [6.0.1]

- **Un cane da guardia per il radar.** Sintomo dal campo, tre volte in tre
  giorni: aerei sopra casa, pannello muto, e premendo *«interroga adesso»* i
  voli comparivano. Due spiegazioni possibili, e i dati non bastavano a
  separarle: il cerchio da 3 km troppo stretto per quello che si percepisce
  come «sopra casa», oppure il ciclo del radar fermo.

  Un ciclo fermo non può accorgersi da solo di essere fermo: serve qualcuno da
  fuori. Ora il ciclo lascia un **battito** a ogni giro, e il giro principale
  del servizio — che passa una volta al secondo — lo guarda. Se il battito è
  vecchio più di quattro intervalli (e mai meno di due minuti: una sfilata di
  aerei dura, e un cane da guardia nervoso sarebbe peggio del difetto
  sorvegliato) il ciclo viene riavviato.

  **Non è una cura**, ed è importante scriverlo: il difetto, se esiste, resta
  da trovare. È una **misura**: ogni rianimazione lascia una riga nel registro
  con un orario sopra, e la riga di stato la conta. Se quel numero resta a zero
  per settimane, il blocco non c'era e la risposta era il raggio.

- **Tre etichette che mancavano da versioni.** Una prova di fumo sui template
  ha trovato tre chiavi di traduzione inesistenti: sulla pagina *Game Boy* due
  etichette mostravano il nome grezzo della chiave (`doom.keyboard.device`,
  `doom.keyboard.read`) e su *Now Playing* il pulsante di salvataggio si
  chiamava `form.save`.

## [6.0]

Numero tondo perché il DMD fa una cosa che prima non faceva: non mostra più
soltanto quello che succede, **dice quando uscire a guardare**.

- **Il terzo colore.** I passaggi che non si vedono sono **quattro al giorno
  contro uno**: mostrarli cambia il servizio da «parla una volta al giorno» a
  «parla cinque volte». Arrivano in **grigio-azzurro spento**, senza preavviso
  e senza lampeggio, per venti secondi attorno al culmine — dove l'arco è più
  bello da guardare. La riga sotto dice perché non si vede: `SOLE +21°` oppure
  `IN OMBRA`.

  Il colore e l'assenza di lampeggio dicono da soli che non è un invito a
  uscire, ed è tutta la differenza fra un servizio più vivo e un servizio che
  mente. Si spegne da una casella.

- **Lo spegnimento in ombra.** Nel **13%** dei passaggi visibili la Stazione
  non tramonta: entra nell'ombra della Terra e **sparisce di colpo a metà
  cielo**, in tre o quattro secondi. È la cosa più spettacolare che faccia, e
  chi non se l'aspetta pensa di aver perso di vista un aereo.

  Adesso l'istante si calcola. Sull'arco c'è un **taglio** che segna il punto,
  la curva oltre quel punto è in tono minore, e negli ultimi quarantacinque
  secondi il pannello scrive **`SPARISCE 21:14`**.

- **La pagina Satelliti.** Elevazione minima, preavviso, cadenza, famiglie, le
  due caselle, l'età degli elementi orbitali, l'elenco dei prossimi passaggi
  — con il motivo accanto a quelli invisibili — e i pulsanti del registro.

  Con una regola scritta nel codice e difesa da una prova: togliendo tutte le
  spunte alle famiglie ne resta una. Un servizio acceso che non guarda niente
  non dà nessun errore: resta muto per sempre, e chi lo ha acceso pensa che
  sia rotto.

- **Il manuale** `docs/satelliti.it.md`, con il PDF: perché il servizio parla
  poco, perché avvisa dieci minuti prima, perché la magnitudine è una tabella
  scritta a mano, e la tabella che traduce l'elevazione in distanza (anche a
  60 gradi la Stazione è a 225 km).

## [5.8.2]

- **Il registro dei passaggi dei satelliti**, in `/var/lib/dmd/satelliti.csv`.
  Come quello dei voli, ma con una colonna che cambia il senso della cosa:
  dentro ci finiscono anche i passaggi **non visibili**, con l'altezza del Sole
  accanto.

  Prima i non visibili non venivano nemmeno calcolati, si scartavano subito:
  era il filtro al posto sbagliato. La visibilità è una scelta di cosa
  **mostrare**, non di cosa **sapere** — e con due soli oggetti calcolarli
  tutti costa niente.

  Così il registro risponde alla domanda che altrimenti resta senza risposta:
  *perché stasera il pannello non ha detto niente?* Perché la Stazione è
  passata a 82 gradi alle 11:46, con il Sole a 21 gradi. Su tre giorni:
  sedici passaggi, tre visibili.

  Si scrive **a cose fatte**, non al calcolo: un passaggio previsto non è un
  passaggio avvenuto. Stessa regola del registro dei voli.

  Colonne: `sorge, nome, norad, gruppo, durata_min, elevazione_massima,
  azimut_sorge, azimut_tramonta, magnitudine, visibile, sole_gradi`.

## [5.8.1]

- **Il radar non vedeva aerei che passavano davvero.** Segnalato dal campo:
  aerei sopra casa, pannello muto, e premendo *«interroga adesso»* i voli
  comparivano subito. La catena interrogazione → disegno funzionava: era la
  **cadenza**.

  Nel ciclo l'intervallo si contava dalla **fine della sfilata** invece che
  dall'inizio dell'interrogazione. `_show_all` tiene ogni aereo a schermo per i
  suoi secondi, quindi tre aerei da quindici secondi aggiungevano tre quarti di
  minuto fra un'interrogazione e la successiva: chi leggeva *«ogni 40 secondi»*
  ne otteneva ottantacinque.

  Ed era un circolo vizioso, perché peggiorava proprio quando il radar era più
  utile: **più aerei trovava, meno spesso guardava.**

  Misurato su un caso vero — raggio 3 km in un corridoio di atterraggio — la
  probabilità di vedere un aereo in avvicinamento passava dall'89% al **66%**
  nei momenti di traffico. Con la correzione e venti secondi di intervallo si
  arriva al 99%, e all'87% sui sorvoli alti e veloci.

- **Un valore sbagliato non uccide più il radar.** `int(cfg["poll_interval"])`
  stava fuori dal `try`: un numero scritto male in configurazione avrebbe fatto
  morire il thread per sempre, senza una riga nel registro.

- **La cadenza vera adesso si legge.** La riga di stato riporta i secondi
  **misurati** fra due interrogazioni, non quelli configurati. È la ragione per
  cui il difetto è rimasto nascosto per versioni intere: la pagina dichiarava
  trenta secondi e nessuno mostrava i novanta veri.

- **Intervallo predefinito da 30 a 20 secondi.** Con un raggio di pochi
  chilometri un aereo di linea attraversa il cerchio in meno di mezzo minuto, e
  interrogare più lentamente del transito vuol dire non vederlo mai. Sotto i 15
  non si scende comunque: è un servizio gratuito della comunità.

## [5.8]

- **I satelliti.** Una sorgente nuova: il pannello avvisa **dieci minuti
  prima** che la Stazione Spaziale passi sopra casa, lo ricorda a cinque, e
  durante il passaggio mostra **dove guardare** — l'arco vero da dove sorge a
  dove tramonta, con il puntino che ci scorre sopra — mentre l'ora lampeggia.

  Non è un secondo Air Radar. Il radar racconta quello che passa perché è
  interessante saperlo; questa sorgente esiste per **far uscire in terrazzo al
  momento giusto**, e da lì discende ogni scelta.

- **Parla poco, per costruzione.** Di sedicimila oggetti attivi a occhio nudo
  se ne vedono pochissimi: serve che il satellite sia al sole mentre qui è già
  buio. Quella condizione, più una tabella scritta a mano dei pochi di cui
  conosciamo davvero la luminosità, porta sedicimila a **uno o due eventi al
  giorno**.

  La tabella non è un abbellimento, è *il filtro*: la magnitudine nei TLE non
  c'è, e la fonte pubblica che la dava — i file di Mike McCants, lo standard
  per vent'anni — è stata ritirata. Il gruppo *stations* di CelesTrak, che
  sembrava contenere le due stazioni spaziali, ne contiene venti: per lo più
  CubeSat rilasciati dalla ISS, invisibili a occhio nudo.

- **Funziona senza rete.** Gli elementi orbitali si scaricano una volta ogni
  sei ore, la posizione si calcola in casa con SGP4. CelesTrak chiede di non
  interrogare più di una volta all'ora e di fermarsi al primo errore HTTP,
  pena il blocco dell'indirizzo: il freno è nel codice e una prova lo difende.

- **Le coordinate restano dove stanno.** Sono quelle dell'Air Radar — una casa
  sola, un posto solo — e possono essere volutamente imprecise: spostarsi di
  undici chilometri cambia gli orari di due secondi.

- **Quattro difetti trovati sul campo**, prima che una riga arrivasse al
  pannello: un passaggio già in corso spacciato per appena sorto; uno a
  cavallo della finestra buttato via in silenzio; la Stazione contata tre
  volte perché il catalogo numera a parte i moduli agganciati; e la
  **bisezione del tramonto che andava dalla parte sbagliata**, scritta
  pensando solo al bordo che sale. Quest'ultimo si vedeva solo lanciando due
  volte lo stesso comando: il sorgere restava identico al secondo, il tramonto
  ballava di decine di secondi.

- Manca la pagina dedicata: elevazione minima, preavviso e cadenza si regolano
  da `config.json`. Arriva nella prossima.

## [5.7]

- **L'orologio compariva fra un gioco e l'altro.** Nel giro del tasto Start,
  dopo Doom, il pannello tornava all'orologio per qualche secondo e solo dopo
  partiva il Game Boy.

  Non era lentezza da sopportare: era l'ordine di due righe. `apri_sessione`
  chiedeva la presa del pannello **dopo** aver avviato il processo, e avviare
  PyBoy vuol dire caricare Python, numpy e PIL più la ROM — secondi, non
  millesimi. In quei secondi la partita precedente aveva già mollato il
  pannello e la nuova non l'aveva ancora preso: l'arbitro lo dava a chi c'era,
  cioè all'orologio.

  Adesso la presa arriva **prima** dell'avvio, e se l'avvio fallisce si molla.
  Lo stesso schema c'era in `sources/doom.py`, dove il binario parte in un
  attimo e non si vedeva: corretto anche lì, perché era sbagliato uguale.

- **Una schermata di attesa per il Game Boy.** Il pannello non resta fermo
  sull'ultimo fotogramma della partita precedente: durante il caricamento
  compare «GAME BOY» con il nome della cartuccia, nei verdi del DMG.

- **Documentazione allineata.** `docs/README.it.md` dichiarava ancora *«DMD
  Controller 1.10»* e ripeteva una descrizione del progetto ferma a quaranta
  versioni fa: adesso è soltanto l'indice dei manuali, perché un documento che
  ne ripete un altro invecchia in silenzio. Nel manuale completo entrano la
  scheda audio USB (§1.2b), le pagine web aggiunte dalla 5.0 in poi (§10.2) e
  la tabella delle priorità completa di tutte e undici le sorgenti (§10.4).

## [5.6.1]

- **Il mixer della 5.6 non è mai partito.** `sources/giochi` importava `suoni`
  *dentro una funzione* e non a livello di modulo: le due chiamate nuove —
  quella che apre il mixer con la partita e quella che lo chiude — riferivano
  un nome inesistente e sollevavano `NameError`. Il `try/except` che avevo
  messo per non far cadere il servizio lo raccoglieva, stampava una riga nel
  registro e tirava dritto. Il gioco funzionava, e gli effetti tornavano alla
  strada vecchia: quella che ne butta uno su due.

  Misurato sul percorso vero: **54% degli effetti perso** in nove secondi di
  Breakout. Ora zero.

  Le prove non l'avevano visto perché chiamavano `effetti_avvia` direttamente,
  senza mai passare da `apri_sessione`. Ora una partita vera si apre dentro la
  suite, e si controlla che il mixer sia acceso e che si spenga da solo quando
  la partita finisce.

- **Il Game Boy spariva dal giro del tasto Start.** In `elenco_ciclo` c'era un
  `return` anticipato quando *«Doom nel giro»* era spento, e si portava via
  anche il Game Boy: due caselle indipendenti nella pagina, una sola condizione
  nel codice. Chi toglieva Doom si ritrovava PyBoy fuori dal carosello senza
  nessun rapporto fra le due cose. È un difetto vecchio, non della 5.6, ma il
  sintomo è lo stesso.

## [5.6]

Due difetti dell'audio con la stessa radice: **come il PCM arriva alla
scheda**.

- **Il Game Boy suonava in ritardo.** Il muxer `alsa` di ffmpeg non accetta
  nessuna opzione e apre un buffer fisso di 32768 campioni: a 48 kHz sono
  **0,68 secondi**, più i 340 ms del tubo. Per un avviso di mezzo secondo non
  conta niente; in una partita è la distanza fra quello che si vede e quello
  che si sente.

  Ora si usa `aplay`, che il buffer lo prende come argomento — **80 ms** — e il
  tubo si stringe da 64 a 16 KB. `aplay` sta in `alsa-utils`, lo stesso
  pacchetto di `alsamixer` che il manuale dell'audio fa già usare per alzare il
  volume della chiavetta. Se manca si ripiega su ffmpeg: in ritardo è meglio
  che muto.

- **Breakout aveva ancora suoni muti.** La causa era la regola «uno per
  volta»: un processo per effetto, e una scheda ALSA aperta in `plughw` sta in
  mano a un programma alla volta, quindi il secondo suono ravvicinato veniva
  buttato. Su Breakout se ne perdeva circa un quinto.

  Durante una partita ora c'è un **mixer**: un riproduttore solo, aperto quanto
  dura la partita, e gli effetti sommati in memoria. Si sovrappongono invece di
  annullarsi, e partono nel blocco successivo — 23 ms, contro i 150-300 ms che
  costava avviare un processo su un Pi. Vive solo mentre si gioca: a pannello
  fermo non tiene occupata la scheda e non consuma niente.

- **Il ciclo che scrive ha un freno.** In produzione il ritmo lo detta la
  scheda audio, perché scrivere su un tubo pieno blocca. Ma se il riproduttore
  consumasse più in fretta del tempo reale il ciclo girerebbe a vuoto, e su un
  Pi la CPU bruciata sono righe chiare sul pannello. L'ha trovato una prova con
  un riproduttore finto che consuma all'istante — 26 milioni di campioni in
  0,8 secondi — non il pannello.

## [5.5.1]

- **La ricompilazione di Doom falliva** con `multiple definition of
  'I_InitTimidityConfig'` — in fondo, dopo due minuti di attesa, con l'aria di
  essere un difetto della libreria.

  Non lo era: era il Makefile che non ricompilava abbastanza. La 5.5 aggiunge
  `-DFEATURE_SOUND`, e quella flag cambia il **significato** dei sorgenti già
  compilati — `dummy.c` definisce uno stub di `I_InitTimidityConfig` proprio
  quando `FEATURE_SOUND` **non** c'è. Ma nessun `.c` era cambiato, quindi make
  considerava aggiornati tutti gli oggetti e ricompilava solo i quattro file
  nuovi. Al collegamento si incontravano lo stub vecchio e la funzione vera.

  Ora gli oggetti dipendono anche dalle **opzioni**: quelle in uso finiscono in
  un'impronta dentro la cartella di compilazione, e cambiarle rende vecchio
  tutto. Si ricompila una volta sola; le compilazioni successive restano
  incrementali.

## [5.5]

- **Doom non poteva suonare, e l'avevo scritto io nel Makefile.** La 5.2 ha
  aggiunto la levetta *«Audio di Doom»*, il changelog che la annunciava e un
  manuale che spiegava come funzionava. Non funzionava: in cima al Makefile
  c'era scritto da anni *«non vuole SDL e non fa suono»*, e infatti nessun
  modulo sonoro veniva compilato. `-nosound` era ininfluente, e
  `SDL_AUDIODRIVER`/`AUDIODEV` non li leggeva nessuno perché SDL non era
  collegato. Ho dichiarato una funzione senza verificarla.

  doomgeneric il modulo ce l'ha — `i_sdlsound.c` e `i_sdlmusic.c`, quelli di
  chocolate-doom — e lo cerca sotto il nome `DG_sound_module` quando
  `FEATURE_SOUND` è definito. Ora il Makefile lo compila se trova SDL2 e
  SDL2_mixer, e se non li trova compila **muto come prima** invece di fallire:
  una libreria mancante non deve impedire di giocare.

- **Serve una ricompilazione sul Raspberry**, che l'aggiornamento via rete non
  fa apposta (ricompilare a ogni update vorrebbe dire due minuti di attesa per
  niente). La pagina Doom se ne accorge da sola: guarda che cosa ha *collegato*
  il binario, non che cosa dice il sorgente, e lo segnala a chi l'audio di Doom
  l'ha chiesto. Il controllo del «binario vecchio» ora guarda anche il
  Makefile, non solo il `.c` — questa versione cambia **solo** il Makefile, e
  senza quel controllo l'aggiornamento sarebbe passato in silenzio.

- **Breakout aveva pochi suoni.** In parte è vero per costruzione: misurati 83
  al minuto contro i 291 di Invaders. Ma mancava anche qualcosa. L'effetto
  `livello` esisteva dalla 5.2 e non lo suonava nessuno — lo chiamava solo
  Invaders — quindi finire un muro passava in silenzio. Ora c'è, c'è il lancio
  della palla, e soprattutto i mattoni hanno **una nota per fila**, che sale
  scavando verso l'alto: è il suono con cui il Breakout del 1976 diceva, senza
  scriverlo, a che punto eri arrivato. Da 83 a 131 suoni al minuto, e non
  tutti uguali.

- **Il Game Boy suona.** Non con effetti nostri: con la sua APU, emulata da
  PyBoy, che con `sound_emulated=True` calcola i campioni senza aprire nessun
  dispositivo e ce li lascia leggere a ogni tick. Li mandiamo a ffmpeg come
  tutto il resto, quindi nessuna dipendenza nuova. Si raccolgono anche dai
  fotogrammi che **non** vengono disegnati: il video si può saltare, l'audio
  no — prenderli solo dai fotogrammi mostrati vorrebbe dire buttare via due
  terzi del suono. Segue la levetta *«Effetti dei giochi»*, e tace quando la
  scheda è della musica AirPlay.

## [5.4]

- **Cerchio spara, e non esce più.** Era l'ultimo posto in cui il tasto **B**
  del pad chiudeva una partita. La 4.5.3 aveva già tolto quel significato al
  Game Boy, dove B appartiene al gioco; nei giochi interni era rimasto, con la
  motivazione — scritta nel codice — che *«chi ce l'ha nelle dita da Doom non
  deve reimpararla»*. La motivazione era **falsa**: in Doom cerchio è `usa`,
  non l'uscita. Su un pad i quattro tasti frontali stanno sotto le stesse dita
  mentre si gioca, e uno di loro non può portare via la partita. Per uscire
  restano **Select** e **PS**, che si premono apposta.

- **Il pulsante di prova dell'audio non inganna più.** Suona anche a «Suono
  acceso» spento, ed è voluto: serve proprio a decidere se accenderlo. Ma
  diceva soltanto *«Suono inviato alla scheda»* — si provava, si sentiva il
  tono, e si concludeva che l'audio funzionasse. Poi avvisi dei servizi ed
  effetti dei giochi restavano muti, e il motivo non era scritto da nessuna
  parte. Ora, a interruttore spento, il riquadro lo dice **prima** di provare
  e il messaggio della prova lo ripete dopo.

- **Le prove dei suoni non toccavano il collegamento vero.** Montavano i
  giochi a mano, quindi non dicevano niente su quello che `apri_sessione` fa
  aprendo la partita — cioè esattamente il punto in cui il suono dei giochi
  poteva mancare senza che nessuno se ne accorgesse. Ora una partita vera gira
  dentro la prova e si controlla che gli effetti arrivino a ffmpeg.

## [5.3]

- **Il DMD diventa una cassa.** Un interruttore nella pagina Now Playing e la
  musica AirPlay esce davvero dalla scheda audio, invece di essere soltanto
  raccontata sul pannello. Fino a ieri `setup_nowplaying.sh` mandava l'audio
  di shairport-sync nella scheda **fittizia** del kernel: dei brani si
  prendevano i metadati e il suono si buttava, perché non c'era niente da cui
  farlo uscire. Con la scheda USB quella scelta non ha più motivo di esistere,
  e cambiarla è una riga di `/etc/shairport-sync.conf`.

- **Riguarda solo AirPlay, e va detto.** Spotify racconta che cosa sta
  suonando su un *altro* dispositivo: da un racconto non esce audio. Per fare
  del DMD anche un altoparlante Spotify Connect servirebbe `librespot`, che è
  un altro programma e un'altra storia.

- **Prima di scrivere, la scheda si prova per davvero:** 44 100 Hz stereo in
  accesso esclusivo, cioè il formato di AirPlay. Se non lo regge non si tocca
  niente e il motivo si legge subito — meglio un interruttore che non scatta
  di una cassa AirPlay che non suona più e nessuno sa perché. Il tono che si
  sente è la prova stessa. La configurazione si modifica in un punto solo:
  nello stesso file c'è la password del broker MQTT, e riscriverlo da capo
  vorrebbe dire perderla o maneggiarla.

- **A shairport si dà `hw:`, ai nostri avvisi resta `plughw:`.** Sembra
  un'incoerenza: `plughw` mette un convertitore davanti alla scheda, ed è
  giusto per un mp3 qualunque; shairport-sync la frequenza la gestisce da sé e
  la scheda vuole vederla com'è.

- **Mentre suona la musica gli avvisi tacciono.** La scheda è di
  shairport-sync finché dura il brano, e comunque un campanello sopra la
  musica non lo vuole nessuno: le notifiche sul pannello si vedono lo stesso.
  Doom, per la stessa ragione, parte muto — deciso da noi, invece di lasciare
  che SDL fallisca l'apertura con qualche secondo di errori proprio a inizio
  partita.

- **Corretto un difetto della 5.2.** La scelta automatica dell'uscita audio
  prendeva l'ultima scheda dell'elenco, e su una macchina con Now Playing
  installato l'ultima può benissimo essere quella **fittizia**. Il risultato
  era silenzio perfetto senza un solo errore da leggere, che è il modo
  peggiore in cui una cosa possa non funzionare. Ora la scelta automatica la
  salta, e nell'elenco compare per quello che è.

- **Degli errori di ffmpeg si mostra la prima riga, non l'ultima.** Con
  `-v error` stampa prima la causa (`cannot set sample rate`) e poi la
  conseguenza (`Error opening output device`), ed è la seconda quella che non
  dice niente.

- **Due pulsanti di form diversi nella stessa scheda stavano attaccati.** Il
  margine che li stacca ce l'ha il singolo tasto, e `form.inline` lo azzera:
  ora lo stacco lo mette la riga che li contiene. Succedeva in Impostazioni
  (*Applica* / *Prova il suono*) e in Funcam (foto / gif); nel Radar la coppia
  *Aggiungi* / *Dimentica* era incolonnata invece che affiancata, e passa
  nella stessa riga.

- **README aggiornato**, fermo alla 4.8: mancavano la Funcam, la pagina Rete,
  il pulsante fisico, l'audio e l'uscita musicale, la priorità 51 nella
  tabella dell'arbitro, i moduli nuovi nella struttura dei file e otto righe
  di storico. Aggiunta anche una tabella su **che cosa entra nel backup della
  configurazione e che cosa no**.

## [5.2]

- **Il pannello guadagna una voce.** Serve una scheda audio USB, e non è un
  ripiego: la libreria della matrice si prende il blocco PWM del Raspberry,
  che è lo stesso che fa suonare l'uscita jack. O si accende il pannello o si
  accende l'audio interno — infatti l'installazione spegne `snd_bcm2835`.
  L'USB è l'unica strada, non un compromesso.

- **Un avviso per servizio, al momento della notifica.** Quando una sorgente
  vince l'arbitrato e prende il pannello — e solo in quell'istante, non finché
  ci resta — suona il file scelto per lei nella pagina Servizi, preso dalla
  libreria media. Otto servizi possono averlo. **Media Player e Rolling Banner
  no:** non annunciano niente, compaiono a intervalli per decorazione, e un
  campanello a ogni foto sarebbe un metronomo. **I rifiuti nemmeno**, per un
  motivo diverso: non sono un servizio, li disegna l'orologio dentro la sua
  colonna.

- **Un suono per volta.** Se ne parte uno mentre un altro suona, il nuovo si
  **scarta**: non va in coda e non interrompe. Un avviso in coda si sentirebbe
  tre secondi dopo, riferito a qualcosa che dal pannello è già sparito. Gli
  avvisi si troncano a 15 secondi, così un file lungo scelto per sbaglio non
  tiene muto tutto il resto per minuti.

- **Dodici effetti per Invaders e Breakout**, a onda quadra, scritti per loro.
  Stanno in `suoni/` dentro il programma e **non** nella libreria media: sono
  parte del gioco come i suoi colori, e mescolarli ai contenuti dell'utente
  vorrebbe dire che cancellandone uno per sbaglio il gioco diventa muto. Fra
  questi le quattro note del passo della schiera, che accelerano con lei: metà
  della tensione dell'originale stava lì. E `record`, che è dei due giochi
  insieme, quando il primato personale viene battuto.

- **Doom suona.** Con la sua colonna sonora, dai suoi WAD: `-nosound -nomusic`
  ora compaiono solo se l'audio di Doom è spento. La scheda gli arriva
  dall'ambiente (`SDL_AUDIODRIVER=alsa`, `AUDIODEV`), perché senza il primo SDL
  proverebbe pulseaudio — che su un'immagine senza sessione grafica non c'è, e
  Doom partirebbe muto senza dire perché. Ha una levetta tutta sua: è l'unico
  suono continuo del sistema, quindi l'unico che pesa davvero sul bus.

- **Nessuna dipendenza nuova:** a scrivere sulla scheda è `ffmpeg`, che c'è
  già, col muxer `alsa`. Con `plughw` e non `hw` — il primo converte frequenza
  e formato al volo, così un mp3 a 44 100 Hz esce anche da una chiavetta che
  sa fare solo 48 000. Il volume è un filtro di ffmpeg, non il mixer di
  sistema: non cambia niente per gli altri programmi.

- **Una scheda staccata non fa ripiegare in silenzio su un'altra.** Il DMD
  resta muto e lo scrive in pagina: suonare dall'altoparlante sbagliato senza
  avvisare è peggio che non suonare, perché non si capisce cosa stia
  succedendo. Il pulsante di prova funziona anche a suono spento — serve
  proprio a decidere se accenderlo.

- Manuale nuovo: `docs/DMD_audio.pdf`.

## [5.1]

- **Il servizio arma, non accende. Sempre.** L'interruttore nella pagina
  Servizi non fa più partire la telecamera: dice che la si **può** accendere.
  La ripresa parte solo quando qualcuno la chiama — il pulsante fisico, oppure
  i due comandi nella pagina Funcam, che ora ci sono sempre. A servizio spento
  non succede niente: né dal pulsante, né dalla pagina.

  Fino alla 5.0.3 questo valeva *solo* con la spunta «Pulsante fisico» attiva;
  senza, il servizio accendeva la ripresa come una sorgente qualsiasi. Era un
  errore di impostazione, non un difetto di codice: legava il momento in cui
  una webcam in soggiorno si accende a una casella che riguarda tutt'altro —
  se un pulsante è stato saldato o no. Su una telecamera *quando si accende* è
  la domanda importante, e la risposta non può dipendere da un dettaglio di
  cablaggio.

- **La spunta «Pulsante fisico» decide ora una cosa sola:** se aprire il
  piedino per leggere un pulsante. Niente di più.

## [5.0.3]

- **«non funziona: Error muxing a packet… Immediate exit requested» non era un
  guasto: era ffmpeg che salutava.** Il codice `-1414092869` è il suo
  `AVERROR_EXIT` — *«mi hanno chiesto di uscire subito»* — e a chiederglielo
  eravamo noi.

  Il difetto stava nel giudizio: trattavo «c'è del testo su stderr» come «è
  fallito». Ma ogni chiusura regolare ne stampa. Quindi ogni spegnimento del
  servizio, e soprattutto **ogni pausa automatica** — quella che ferma la
  cattura quando nessuno guarda, cioè il funzionamento normale — lasciava in
  pagina un errore mai avvenuto e faceva scattare l'attesa prima di
  riprovare. Attesa che raddoppiava a ogni pausa, fino a mezzo minuto: la
  telecamera diventava sempre più lenta a tornare, con scritto accanto un
  motivo falso.

  Ora una chiusura chiesta da noi non viene nemmeno esaminata, e di quello che
  ffmpeg stampa si scartano i saluti noti: se non resta niente, non è successo
  niente.

- **E se resta qualcosa, in pagina va una riga sola** — quella che spiega —
  invece di quattrocento caratteri di chiacchiere del muxer.

## [5.0.2]

- **Il pulsante per installare `gpiozero` era nascosto dietro la spunta
  «Pulsante fisico».** Cioè: per installare la libreria bisognava prima
  accendere una funzione che senza quella libreria non parte. Al contrario.

  Trovato usandolo, non provandolo: la 5.0.1 sembrava semplicemente non avere
  quel pulsante, e con il servizio acceso partiva subito la webcam — che era
  il comportamento corretto per una spunta spenta, ma da fuori sembrava un
  guasto.

  Adesso la scheda «Pulsante fisico» c'è **sempre**, e si legge nell'ordine in
  cui servono le cose: cosa fa, la libreria con il suo pulsante di
  installazione, dove si salda, e infine la spunta per accenderlo. Solo i
  comandi *accendi/spegni* restano nascosti finché il pulsante non è attivo,
  perché senza non farebbero niente.

- **La spunta e il piedino hanno un modulo proprio**, che scrive due chiavi e
  basta. `api_telecamera` riscrive *tutti* i campi che riceve: una spunta
  dentro quel modulo avrebbe azzerato dispositivo, risoluzione e aspetto a
  ogni salvataggio parziale. È la stessa lezione del profilo del pannello
  nella 4.8.5.

## [5.0.1]

- **Il pulsante fisico della Funcam.** Accendere la telecamera dalla pagina
  Servizi voleva dire tirare fuori il telefono, aprire il browser, trovare la
  voce — per una cosa che si fa passando davanti al pannello è una procedura
  assurda. La stessa obiezione, e la stessa risposta, della pagina Rete.

  Un pulsante solo, tre gesti:

  | Gesto | Cosa fa |
  |---|---|
  | Un clic, telecamera spenta | si accende |
  | Un clic, telecamera accesa | scatta una foto dopo tre secondi, con il conto alla rovescia grande sul pannello |
  | Tenuto premuto tre secondi | si spegne, **mentre** il dito è ancora sopra |

  Lo spegnimento avviene al terzo secondo e non al rilascio: è l'unico modo di
  sapere di aver tenuto abbastanza senza contare a mente. E una pressione
  lunga vale *un* gesto, non due — senza quel controllo ogni spegnimento
  sarebbe seguito da un clic che riaccende.

  A servizio spento il pulsante non esiste: non si apre nemmeno il piedino.

- **Con il pulsante, il servizio cambia significato:** non accende più la
  telecamera, la **arma**. La webcam parte spenta e resta spenta finché non la
  si chiama — che su un oggetto con una telecamera in soggiorno non è una
  comodità, è il punto. Senza pulsante tutto si comporta esattamente come
  prima.

- **Dove si collega.** GPIO 25: sul connettore a 40 piedini è il **piedino
  22**, e una massa è il **piedino 20** — accanto, stessa fila. Un pulsante
  normalmente aperto fra i due, e nient'altro: la resistenza di richiamo è
  quella interna al Raspberry. Si salda sui fori del connettore della Bonnet,
  esposti sopra perché lo zoccolo sta sotto. È il metodo che Adafruit
  documenta per questa stessa scheda, e GPIO 25 è anche il piedino che usa lei
  per un pulsante.

  La scelta non è libera, e il programma non la lascia libera. Con la Bonnet
  montata la matrice usa 4 (o 18 con la modifica PWM), 5, 6, 12, 13, 16, 17,
  20, 21, 22, 23, 24, 26 e 27: prenderne uno vorrebbe dire un pannello che
  smette di funzionare, con la causa nell'ultimo posto in cui si andrebbe a
  cercare. Il menu propone solo i liberi, e un valore fuori elenco viene
  rifiutato.

- **`gpiozero` si installa da un pulsante nella pagina**, come Doom, il Game
  Boy e la condivisione SMB. Chi ha appena saldato un pulsante sotto il
  pannello non ha un terminale aperto, e mandarlo a cercarne uno vanifica il
  pulsante stesso. L'installazione gira fuori dal servizio — `apt` ucciso a
  metà lascia dpkg da riparare a mano — e aspetta il lucchetto di apt fino a
  due minuti, perché su un Raspberry appena acceso ce l'hanno spesso gli
  aggiornamenti automatici. Se la libreria arriva dopo l'avvio del servizio,
  un pulsante riapre il piedino senza spegnere e riaccendere niente.

- **Se il pulsante non si apre, la telecamera resta spenta.** La prima stesura
  la accendeva «per non lasciarla irraggiungibile», ed era il rovescio esatto
  di ciò che serve: chi accende il pulsante vuole una webcam spenta finché non
  la chiama, e rispondere a un guasto lasciandola accesa in soggiorno per
  giorni è la peggiore delle interpretazioni possibili.

  A non lasciarla irraggiungibile ci pensa la pagina, che ora ha i suoi due
  comandi — *accendi* e *spegni* — comodi comunque per quando non si è davanti
  al pannello.

## [4.10.1]

- **La telecamera si chiama Funcam**, e nel menu sta prima dei Servizi.

- **Quanti colori lo scegli tu.** Da 2 a 8 livelli per canale: 2 sono gli otto
  pieni di prima, 6 ne danno 216 — in pratica la tavolozza da 256 colori
  dell'epoca. Un 256 esatto con tre canali uniformi non esiste: quei 256 erano
  una tavolozza scelta a mano, non tre canali indipendenti.

  Salire **non costa niente**: gli stessi byte, lo stesso conto vettoriale,
  nessun traffico in più sul bus. Costa solo il rischio che le tinte
  intermedie sfarfallino — e l'unico modo di saperlo è guardare il pannello.
  Vale la pena provare, perché la regola degli otto colori era nata disegnando
  **testo**, dove i pochi pixel sfumati di un bordo tremano contro uno sfondo
  fermo; un'immagine di telecamera è fatta tutta di mezzi toni e potrebbe
  comportarsi diversamente. Il predefinito resta 2.

- **Corretto «Device or resource busy».** Il `/dev/video` si apre una volta
  sola, e la chiusura del processo precedente non veniva attesa fino in fondo:
  bastava che ffmpeg avesse chiuso il proprio stderr perché la cattura si
  dichiarasse spenta, mentre il dispositivo era ancora suo. Chi riapriva — un
  clic sull'interruttore del servizio, o la ripartenza automatica dopo una
  pausa — trovava occupato, e restava spento con un errore che sembrava un
  guasto.

  Ora si aspetta l'uscita vera del processo, accensioni e spegnimenti passano
  uno per volta, e chi non può bloccarsi (il ciclo che disegna il pannello,
  trenta volte al secondo) se ne va e riprova al giro dopo. Il banco di prova
  è stato rifatto perché il finto ffmpeg **tenesse** il dispositivo e lo
  rilasciasse *dopo* aver chiuso lo stderr, come quello vero: senza, la prova
  passava anche con il difetto in piedi.

- **E un errore non resta lì per sempre.** Quasi tutti i motivi per cui una
  telecamera non si apre passano da soli: si riprova con attese che
  raddoppiano fino a mezzo minuto, invece di costringere a spegnere e
  riaccendere il servizio a mano.

## [4.10]

- **La telecamera.** Una webcam USB attaccata al Raspberry, e sul pannello
  compare quello che vede — ridotto a quello che un computer di quarant'anni
  fa sapeva mostrare.

  Gli otto colori pieni non sono una scelta di stile: sono gli unici che su
  questo pannello non sfarfallano (lo sapevamo già, sta in
  `nowplaying.safe_colors`), ed è anche la tavolozza dei primi computer a
  colori. Il vincolo hardware e l'estetica voluta sono la stessa cosa. Le
  sfumature che mancano le rimette il dithering ordinato di Bayer. Tre aspetti
  a scelta dalla pagina: otto colori, verde Game Boy, grigi.

  **I fotogrammi in più non si scartano: non si chiedono.** Uno scartato dopo
  la cattura ha già attraversato l'USB e il bus, e il risparmio è solo di CPU;
  uno mai prodotto non costa niente a nessuno. Quindi il numero di fotogrammi
  al secondo è `-framerate` sull'ingresso v4l2, non un filtro a valle. Si
  chiede YUYV e non MJPEG, così non c'è nessun JPEG da decodificare. E se il
  pannello è di qualcun altro — ZeDMD, Doom — la cattura si ferma da sola dopo
  venti secondi e riparte quando serve.

  Foto e GIF da due pulsanti, salvate nella libreria media: il Media Player le
  rimette sul pannello da solo, più avanti. Con più telecamere collegate si
  sceglie dal menu, e l'elenco mostra solo i nodi che catturano davvero — una
  webcam USB ne espone due o tre, e gli altri non danno un fotogramma nemmeno
  a insistere.

  Priorità 51: sopra il Media Player, sotto tutto ciò che ha qualcosa da
  *dire*. Un avviso che non compare perché c'è la telecamera accesa sarebbe un
  avviso perso.

  Le immagini non escono dal Raspberry: niente rete, niente MQTT, nessun
  servizio esterno. Il servizio parte spento, perché è una telecamera in
  soggiorno.

## [4.9]

- **Pagina Rete.** Le reti wifi si vedono e si scelgono dal browser: elenco
  con segnale e cifratura, reti già salvate, reti nascoste da scrivere a
  mano, e il pulsante per dimenticarne una. Prima, per cambiare rete,
  servivano un monitor, una tastiera e un mouse attaccati al Raspberry.

  Si parla con `nmcli` e con nient'altro: NetworkManager è il proprietario
  della rete su Raspberry Pi OS, e due proprietari della stessa cosa sono
  peggio di nessuno. Se `nmcli` non c'è la pagina si apre lo stesso e spiega
  dove guardare — è la pagina che si apre quando le cose non vanno, cadere
  proprio lì sarebbe il difetto peggiore.

  **Le password non le custodisce il DMD.** Vanno a NetworkManager, che le
  tiene già per mestiere: nel `config.json` non finisce niente, quindi non
  c'è una credenziale da esportare per sbaglio né da perdere. Nel registro
  la password diventa `***`.

  **Il collegamento non blocca la pagina.** Chi preme il pulsante è collegato
  attraverso la rete di prima: se il cambio riesce, la risposta non gli
  arriva mai. Parte un thread, la pagina risponde subito, e l'esito si legge
  riaprendola sul nuovo indirizzo — che la pagina elenca prima del cambio. Se
  il tentativo fallisce non si perde niente: NetworkManager riattiva il
  profilo di prima, ed è il motivo per cui il vecchio non si cancella mai
  prima di aver provato il nuovo.

  Non si può dimenticare la rete attraverso cui si sta guardando la pagina:
  sarebbe staccarsi il filo sotto i piedi, e per rimediare servirebbe di
  nuovo il monitor.

  È la prima metà. La seconda — l'hotspot di soccorso che si alza da solo
  quando la connessione cade, e ogni tanto riprova le reti conosciute — si
  appoggerà a queste funzioni.

## [4.8.7]

- **Interruttore MQTT nella pagina Servizi.** In cima, sopra l'elenco delle
  sorgenti: spegne e riaccende il collegamento al broker, e con esso il ponte
  verso Home Assistant. Le impostazioni non le tocca — indirizzo, utente,
  password e topic restano dove sono — quindi riaccendere è un clic e non una
  ridigitazione. Prima l'unico modo era una casella in fondo alla pagina
  Musica, dentro un modulo di undici campi che vanno risalvati tutti insieme:
  per staccare il broker si rischiava di perderne l'indirizzo.

  Spegnendo, il DMD **saluta**: pubblica l'`offline` ritenuto sul topic di
  disponibilità, così in Home Assistant le entità diventano *non disponibili*
  invece di restare congelate sull'ultimo valore. Sul pannello non cambia
  niente, i servizi continuano per conto loro.

- Il ponte verso Home Assistant ora si **ferma** davvero quando MQTT viene
  spento. Prima il suo thread continuava a girare, pubblicando su un client
  che non c'era più: non si vedeva — le pubblicazioni cadevano in silenzio —
  ma «spegnere» deve fermare qualcosa, non solo smettere di collegarsi.

## [4.8.6]

- **Il profilo tarato non riportava i parametri che non aveva misurato.**
  Sequenza: «Personalizzata», PWM a 8, salva, ricarica la pagina, scegli
  «Autotune», salva — e il PWM restava 8. La taratura misura *un* parametro e
  nel profilo scriveva solo quello: sceglierlo dal menu cambiava lo `slowdown`
  e lasciava gli altri diciannove com'erano capitati. Una voce di menu che non
  porta da nessuna parte precisa non è un profilo.

  Gli altri parametri sono quelli da cui la taratura è partita, e ora il
  profilo se lo ricorda: salva il nome del profilo di partenza, e applicarlo
  significa «quel profilo, con questo parametro cambiato».

  Non serve rifare la taratura già fatta: un profilo scritto dalle versioni
  precedenti il campo non ce l'ha, e finché di profili di pannello ne esiste
  uno solo non c'è niente da indovinare. Se invece la taratura è partita da
  una configurazione fatta a mano resta scritto anche quello, e si applica
  solo il parametro misurato — i numeri scelti a mano non si sovrascrivono
  per deduzione.

## [4.8.5]

- **Scegliendo «Personalizzata» il menu tornava sul profilo di fabbrica.**
  Si sceglieva la voce, si salvava, si ricaricava la pagina e compariva
  *FM6373 & DP32020B*. I numeri erano davvero quelli — «Personalizzata» non
  li cambia, è il suo mestiere — ma il menu rispondeva alla domanda sbagliata:
  diceva *a chi somigliano i valori* invece di *cosa ho scelto*. Ora la voce
  scelta resta mostrata finché i valori le corrispondono; quando non
  corrispondono più si passa a «Personalizzata».

- **Modificare un numero a mano non veniva salvato.** È la stessa cosa vista
  dall'altra parte, ed è il difetto serio dei due. Il profilo si riapplica
  *dopo* i campi del modulo — ed è giusto, perché cambiare voce nel menu vuol
  dire «riportami a quei valori» — ma lo faceva a **ogni** salvataggio, anche
  quando la voce non era stata toccata. Risultato: PWM da 10 a 11, Applica, e
  tornava 10 in silenzio. Ora la pagina dichiara al modulo quale voce stava
  mostrando, e il profilo si riapplica **solo se la voce cambia**.

## [4.8.4]

- **Il modulo del pannello tagliava lo `slowdown` a 6**, mentre la taratura
  arriva a provare 7 e 8. Un profilo tarato su 7 sarebbe stato riportato a 6
  al primo salvataggio successivo, senza dire niente. Due pezzi dello stesso
  programma non possono avere due idee di cosa sia un valore ammesso: ora una
  prova confronta i due elenchi e fallisce se divergono.

## [4.8.3]

- **Il menu dei profili tornava sempre su «Autotune».** Il profilo tarato
  contiene un parametro solo — lo `slowdown` — e veniva riconosciuto dai
  valori come tutti gli altri. Ma un parametro solo coincide con mezzo mondo,
  a cominciare dal profilo di fabbrica, che quel valore ce l'ha uguale:
  qualunque configurazione risultava «tarata», e scegliendo *FM6373 &
  DP32020B* la voce saltava su *Autotune* appena la pagina si ridisegnava.
  Ora il profilo tarato vale **solo se è stato scelto**, non se i valori per
  caso coincidono; gli altri profili, che di parametri ne hanno venti, si
  continuano a riconoscere dai valori.

  È anche la spiegazione del «parte da sola la taratura»: la taratura non è
  mai partita — il registro del server non ha mai visto una richiesta di
  avvio — era il menu che si riposizionava da solo su quella voce.

## [4.8.2]

- **La taratura esce dalla scheda del pannello** e va in una scheda sua.
  «Salva e riavvia il servizio» e «Avvia taratura» erano due pulsanti vicini
  che fanno cose incomparabili: uno scrive un campo, l'altro avvia tre quarti
  d'ora di riavvii del pannello. Separarli non è estetica.
- **L'avvio pretende un campo di conferma** che manda solo quel modulo: una
  richiesta capitata su `/api/autotune/start` non fa più partire niente.

## [4.8.1]

Quattro difetti trovati usando la 4.8 sul pannello vero, in un paio d'ore.
Tre erano miei e nuovi; il quarto — quello di `dmdconf` — stava lì da sempre,
e la taratura ha solo avuto la sfortuna di essere la prima funzione a
scrivere una chiave fuori dai valori predefiniti.

- **Scegliere un profilo non lo applicava.** Per infilare il pulsante della
  taratura nella scheda del pannello avevo **spezzato in due il modulo**: il
  menu dei profili finiva nel pezzo senza pulsante, quindi premendo Salva non
  veniva inviato affatto. Si sceglieva un profilo, si salvava, e la voce
  tornava su «Personalizzata» con i parametri invariati — mentre modificare un
  campo a mano funzionava, perché quei campi stavano nell'altro pezzo. E il
  pulsante più vicino al menu era diventato *Avvia taratura*, che infatti
  partiva da sola quando si cercava di cambiare i parametri. Il modulo è di
  nuovo uno solo e la taratura sta sotto, dov'è un'altra azione. Una prova
  nuova pretende che il modulo del pannello sia unico e contenga sia il menu
  sia il pulsante.
- **Il profilo tarato non compariva mai nel menu.** La taratura finiva, il
  risultato veniva scritto in `/etc/dmd/config.json`, il servizio ripartiva —
  e il profilo spariva. `dmdconf._merge` costruiva la configurazione
  scorrendo **solo le chiavi dei default**: tutto quello che stava nel file e
  non nei default veniva buttato al caricamento, e il primo salvataggio lo
  cancellava anche dal disco. Nessun errore, nessun messaggio. Ora le chiavi
  sconosciute vengono tenute: di roba scritta da una versione più nuova, o da
  una funzione che scrive fuori dai default, non si sa niente — e non sapere
  niente non autorizza a cancellare.

  Le prove non l'avevano visto perché leggevano il file di configurazione a
  mano, cioè da una porta diversa da quella che usa la web UI. Ora ce n'è una
  che fa il giro intero: carica con `dmdconf`, guarda il menu, salva,
  ricarica.
- **La taratura moriva dopo pochi secondi.** Il processo veniva staccato con
  `start_new_session`, che lo toglie dal terminale ma **non dal cgroup** del
  servizio: e `systemctl restart dmd` — che la taratura stessa fa a ogni
  configurazione — con il `KillMode` predefinito ammazza tutto quello che sta
  nel cgroup. Da fuori sembrava che stesse lavorando: il file di stato restava
  fermo a «0 su 10» e il pannello sul primo valore di prova. Ora parte come
  unità transitoria di systemd, in un cgroup suo (`staccato.py`).
- **Lo stesso difetto era nell'aggiornamento via rete**, e lì sarebbe stato
  peggio: l'OTA riavvia il servizio a lavoro fatto a metà, con `/opt/dmd` già
  riscritto, e morire in quel punto vuol dire restare a metà **senza nemmeno
  il ripristino automatico**. Non era mai emerso perché l'aggiornamento lo si
  è sempre lanciato da SSH, dove il processo nasce nel cgroup della sessione e
  sopravvive; dal pulsante nella pagina web sarebbe morto. Corretto insieme.
- **La taratura fantasma.** Spegnendo il Raspberry a metà taratura, il
  processo moriva e il file di stato restava a dire «in corso». Alla
  riaccensione le Impostazioni offrivano *Ferma la taratura* per una taratura
  che non esisteva, e il pulsante per avviarne una non tornava più — per sei
  ore. Un flag su disco dice cosa è successo, non cosa sta succedendo: ora si
  controlla che il processo esista **e sia davvero il nostro**, confrontando
  il nome del comando e non una sottostringa (dopo un riavvio i numeri di
  processo ricominciano da capo, e il 1234 di ieri oggi può essere il server
  web). Lo stato si ripulisce da solo alla prima occhiata. Verificato
  rimettendo il difetto: la prova fallisce.


## [4.8]

### Aggiunto
- **Taratura automatica del pannello**: un pulsante *Avvia taratura* nelle
  Impostazioni, sotto il menu dei profili. Misura il pannello a diversi
  rallentamenti, rimette tutto com'era, e aggiunge al menu una voce
  *Autotune — Rallentamento GPIO 5* con la configurazione trovata. Nient'altro:
  la taratura **propone**, non decide, e il profilo si applica come qualunque
  altro. Nasce da una campagna di prove durata settimane fatta a occhio, che
  con un difetto casuale non distingueva un miglioramento vero da una serie
  fortunata.
- **I fotogrammi contaminati si marcano e si scartano.** Ogni richiesta alla
  web UI è Python che lavora e rete che si muove, cioè esattamente il disturbo
  che si sta misurando. Spegnere l'interfaccia durante la misura non si può —
  servirebbe per far partire la taratura e per leggerne i risultati — quindi
  si fa l'altra cosa: si conta il traffico durante ogni finestra e le finestre
  sporcate si dichiarano. Una misura sporca dichiarata vale più di una che
  credi pulita. Per la stessa ragione **la pagina non si aggiorna da sola**, e
  lo dice: un auto-refresh genererebbe da solo il disturbo da contare.
- **Profilo «Autotune»** fra i profili del pannello, salvato con la sua misura
  così ci si può tornare. Contiene **solo il parametro tarato**: una taratura
  non ha misurato la geometria del pannello e non deve riscriverla. Se non
  esce nessun consiglio — tutte le finestre contaminate, per dire — non
  compare nessuna voce: meglio nessun profilo che uno costruito su misure
  sporche.
- **Quattro parametri tarabili**: rallentamento GPIO, profondità PWM, durata
  del bit minimo, bit con dithering. La geometria e il tipo di chip no: quelli
  non sono taratura, sono dire che pannello si ha, e stanno nei profili.

### Misurato
- **`slowdown` è la leva del refresh, e va verso il basso.** Da 4 a 8 il
  pannello passa da 38,2 a 23,4 Hz. Il valore consigliato dalla misura è **5**:
  33,3 Hz contro i 29,4 di prima, con disturbi più bassi *e* più costanti fra i
  giri.
- **Il refresh nominale più alto non vince.** A `slowdown` 4 il ciclo gira al
  limite e non ha margine: il refresh oscilla fra 34 e 38 Hz e un terzo dei
  fotogrammi è fuori regime. Il primo valore con abbastanza gioco per
  assorbire i disturbi è 5, e costa cinque Hz.
- **La contesa sul bus, con un numero.** Stessa configurazione, due finestre:
  0,95% di fotogrammi disturbati a riposo, **8,90%** con la scheda SD sotto
  carico, e il refresh minimo che crolla da 25,9 a 18,5 Hz.

## [4.7]

### Aggiunto
- **Google Calendar come servizio.** Gli appuntamenti dei prossimi **tre
  giorni** compaiono sul pannello a giro, come le scadenze: in alto a destra
  *quando* — nel colore che l'orologio usa per la data — al centro *che cosa*,
  grande e scorrevole se il titolo non ci sta, e sotto *dove*, in grigio.
  Un appuntamento compare tre giorni prima e sparisce quando è passato.
- **Niente semaforo, e di proposito.** È la differenza chiesta rispetto alle
  scadenze: il semaforo dice *manca poco*, e ha senso per una bolletta, che si
  può pagare prima; non ne ha per un appuntamento, che succede quando succede.
  Una prova legge il fotogramma disegnato e fallisce se compare anche solo una
  delle tinte del semaforo.
- **Una vetrina, non un'agenda.** Sola lettura
  (`calendar.readonly`), solo il calendario principale: calendari secondari,
  colori, promemoria e regole di visibilità sono ignorati. Le ricorrenze le
  espande Google, così al pannello arrivano occorrenze con una data ciascuna
  invece di regole da interpretare.
- **Pagina Calendario**: il collegamento dell'account e nient'altro, più
  l'elenco in sola lettura di quello che il pannello vede in questo momento —
  che non è un'impostazione, è la prova che il collegamento funziona.
- **Autorizzazione dal browser del proprio computer.** OAuth 2.0 con codice di
  autorizzazione e PKCE, `access_type=offline` e `prompt=consent` perché serve
  un refresh token. Il DMD non ha tastiera: si apre il link altrove, si
  accetta, e si incolla l'indirizzo su cui si è finiti. Funziona anche il
  ritorno vero, se il browser raggiunge il DMD a quell'indirizzo.
- Documento **`docs/calendario.it.md`** e relativo PDF, con la procedura su
  Google Cloud passo per passo — compreso il passo che si dimentica:
  **pubblicare la schermata di consenso in produzione**, perché finché resta
  in test Google scollega tutto dopo sette giorni.
- **Interruttore in Home Assistant**, come ogni altro servizio, e una prova
  nuova che pretende la regola per tutti: ogni chiave di `services` deve avere
  la riga nella pagina Servizi *e* la sua entità MQTT. Era la terza faccia
  dello stesso difetto — chiave in configurazione, nessun interruttore — visto
  con i Compleanni nella 2.0 e con le Scadenze nella 4.1. Verificata togliendo
  la voce: fallisce.

### Sicurezza
- **Scollegando si revoca.** Il pulsante *Scollega l'account* non si limita a
  cancellare i token: chiede a Google di buttare via il permesso. Sono due
  porte distinte — il consenso resterebbe registrato nell'account anche dopo
  aver cancellato tutto dal DMD — e chiuderle insieme è quello che ci si
  aspetta da un pulsante che dice «scollega». Se la revoca non passa (rete
  assente, token già scaduto) il DMD si scollega **lo stesso** e il messaggio
  spiega dove completarla a mano: chi preme quel pulsante vuole prima di tutto
  che il pannello smetta di leggere il suo calendario.
- I token Google stanno in **`/var/lib/dmd/google.json`**, permessi `0600`,
  **fuori dalla configurazione**. E il *client secret* viene tolto dalla
  configurazione esportata come la password del broker MQTT: un `config.json`
  gira — backup, allegati, segnalazioni — e chi lo reimporta riscrive il
  segreto una volta sola.

### Corretto
- **Priorità del Calendario da 58 a 59.** Cinquantotto era il numero naturale,
  ed è già di Now Playing: a parità l'arbitro tiene chi si è registrato per
  primo — il player — e l'avviso non sarebbe mai comparso mentre suona musica.
  Trovato prima del rilascio scrivendo la riga delle priorità nel README. Una
  prova nuova rifiuta qualunque pareggio fra sorgenti: un pareggio non è un
  dettaglio estetico, è una sorgente che tace.

### Diagnostica
- **`diagnostica/misura_refresh.sh`: contare invece di guardare.** La caccia
  alle righe chiare è andata avanti per settimane a occhio — cambia un
  parametro, guarda il pannello, decidi se sembra meglio — e con un difetto
  casuale quel metodo non distingue un miglioramento vero da una serie
  fortunata. Ma la libreria scrive il refresh di **ogni fotogramma** nel log:
  in regime sta fermo a 29,3 Hz, e ogni tanto crolla. Un tuffo a 18,9 vuol
  dire un fotogramma durato 53 ms invece di 34, cioè diciannove millisecondi
  passati ad aspettare la memoria mentre una riga restava accesa. **Quello è
  il difetto**, e adesso si conta.

  Lo script campiona una finestra e stampa quanti fotogrammi sono stati
  disturbati; con `--sweep` cambia il parametro da solo, riavvia, aspetta
  l'assestamento, misura e passa al valore dopo, restituendo una tabella. La
  configurazione torna com'era anche se lo si interrompe — due trap distinte,
  perché una trap su INT/TERM che si limita a ripulire non ferma lo script e
  lo sweep proseguirebbe dopo il Ctrl+C. Verificato togliendola: la prova
  fallisce, e il pannello resterebbe a `pwm_bits` 9 senza che nessuno lo
  sappia.
- **`--confronto`: l'esperimento della contesa in un comando.** Misura a
  riposo, poi sotto carico generando lei la zavorra su disco con
  `oflag=direct`. Nasce da un errore fatto sul campo: coordinare due terminali
  a mano aveva prodotto due istanze che leggevano lo stesso journal e
  stampavano lo stesso numero, con l'illusione di un confronto.
- **`--chiave`: si sweepa qualunque parametro, non solo `pwm_bits`.** Sul
  primo sweep vero è emerso che su questo pannello **`pwm_bits` non muove il
  refresh**: 11, 10 e 9 danno 29,0 / 29,2 / 29,6 Hz, cioè il 2% su due
  dimezzamenti. Su un pannello normale ogni bit varrebbe un raddoppio; qui la
  modulazione la fa il chip S-PWM e i piani di bit non vengono usati. Buona
  notizia travestita da vicolo cieco: gli 11 bit di profondità sono gratis. La
  leva vera è `slowdown`, e ora si può provare.
- **`--giri`: le configurazioni si alternano invece di misurarle in fila.**
  Due misure identiche a distanza di quattro minuti avevano dato 20 e 0
  fotogrammi disturbati: la prima era partita un secondo dopo un
  aggiornamento OTA, con la scheda SD ancora occupata a smaltire le
  scritture. Misurate in fila, ogni configurazione si prende il rumore del
  proprio momento; a giro, il rumore si spalma su tutte.
- **Soglia relativa al regime di ogni configurazione, non fissa in Hz.** Il
  primo sweep su `slowdown` l'ha smascherata subito: a 7 il pannello gira a
  25,9 Hz e la soglia fissa a 28 dichiarava il **100%** dei fotogrammi
  disturbati. Non misurava i tuffi, misurava «la media sta sotto 28?». Ora un
  fotogramma è disturbato se sta più del 5% sotto il regime della *sua*
  configurazione — il massimo della finestra, cioè il valore che il pannello
  tiene quando nessuno lo disturba — e le righe tornano confrontabili anche
  quando lo sweep muove il refresh nominale. `--soglia` resta per forzarne una
  assoluta, `--calo` regola la percentuale.
- **Il riepilogo non conta più i giri vuoti.** Una configurazione senza
  campioni veniva sommata come uno zero e usciva con «minimo 0.0», cioè
  catastrofica invece che non misurata. Ora viene dichiarata per quello che è.
- **Un lucchetto contro le istanze doppie**, preso con `mkdir` perché è
  atomico: con un file, fra il controllo e la creazione due processi
  passerebbero entrambi.
- **Il refresh nel log si può finalmente leggere.** La libreria lo riscrive
  sulla stessa riga con un ritorno a capo, come una barra di avanzamento:
  journald riceve un messaggio senza fine riga, decide che è binario e mostra
  solo `[29.8K blob data]`. Serve `journalctl -a` e un `tr '\r\b' '\n\n'`.
  Documentato, perché è il genere di cosa che fa credere per mesi che
  un'opzione non funzioni.

### Corretto
- **Scegliere un profilo non lo applicava.** Per infilare il pulsante della
  taratura nella scheda del pannello avevo **spezzato in due il modulo**: il
  menu dei profili finiva nel pezzo senza pulsante, quindi premendo Salva non
  veniva inviato affatto. Si sceglieva un profilo, si salvava, e la voce
  tornava su «Personalizzata» con i parametri invariati — mentre modificare un
  campo a mano funzionava, perché quei campi stavano nell'altro pezzo. E il
  pulsante più vicino al menu era diventato *Avvia taratura*, che infatti
  partiva da sola quando si cercava di cambiare i parametri. Il modulo è di
  nuovo uno solo e la taratura sta sotto, dov'è un'altra azione. Una prova
  nuova pretende che il modulo del pannello sia unico e contenga sia il menu
  sia il pulsante.
- **Il profilo tarato non compariva mai nel menu.** La taratura finiva, il
  risultato veniva scritto in `/etc/dmd/config.json`, il servizio ripartiva —
  e il profilo spariva. `dmdconf._merge` costruiva la configurazione
  scorrendo **solo le chiavi dei default**: tutto quello che stava nel file e
  non nei default veniva buttato al caricamento, e il primo salvataggio lo
  cancellava anche dal disco. Nessun errore, nessun messaggio. Ora le chiavi
  sconosciute vengono tenute: di roba scritta da una versione più nuova, o da
  una funzione che scrive fuori dai default, non si sa niente — e non sapere
  niente non autorizza a cancellare.

  Le prove non l'avevano visto perché leggevano il file di configurazione a
  mano, cioè da una porta diversa da quella che usa la web UI. Ora ce n'è una
  che fa il giro intero: carica con `dmdconf`, guarda il menu, salva,
  ricarica.
- **La taratura moriva dopo pochi secondi.** Il processo veniva staccato con
  `start_new_session`, che lo toglie dal terminale ma **non dal cgroup** del
  servizio: e `systemctl restart dmd` — che la taratura stessa fa a ogni
  configurazione — con il `KillMode` predefinito ammazza tutto quello che sta
  nel cgroup. Da fuori sembrava che stesse lavorando: il file di stato restava
  fermo a «0 su 10» e il pannello sul primo valore di prova. Ora parte come
  unità transitoria di systemd, in un cgroup suo (`staccato.py`).
- **Lo stesso difetto era nell'aggiornamento via rete**, e lì sarebbe stato
  peggio: l'OTA riavvia il servizio a lavoro fatto a metà, con `/opt/dmd` già
  riscritto, e morire in quel punto vuol dire restare a metà **senza nemmeno
  il ripristino automatico**. Non era mai emerso perché l'aggiornamento lo si
  è sempre lanciato da SSH, dove il processo nasce nel cgroup della sessione e
  sopravvive; dal pulsante nella pagina web sarebbe morto. Corretto insieme.
- **La taratura fantasma.** Spegnendo il Raspberry a metà taratura, il
  processo moriva e il file di stato restava a dire «in corso». Alla
  riaccensione le Impostazioni offrivano *Ferma la taratura* per una taratura
  che non esisteva, e il pulsante per avviarne una non tornava più — per sei
  ore. Un flag su disco dice cosa è successo, non cosa sta succedendo: ora si
  controlla che il processo esista **e sia davvero il nostro**, confrontando
  il nome del comando e non una sottostringa (dopo un riavvio i numeri di
  processo ricominciano da capo, e il 1234 di ieri oggi può essere il server
  web). Lo stato si ripulisce da solo alla prima occhiata. Verificato
  rimettendo il difetto: la prova fallisce.

### Misurato
- **La contesa sul bus è dimostrata con un numero.** Stessa configurazione,
  due finestre da due minuti: **0** fotogrammi disturbati a riposo, **80**
  (40 al minuto) con la scheda SD sotto carico, e il refresh minimo che crolla
  da 28,3 a 18,6 Hz — fotogrammi da 53 ms invece di 34. La catena carico →
  tuffi nel refresh → righe chiare sul pannello smette di essere una
  ricostruzione e diventa una misura.
- **Il refresh reale è 29 Hz**, non i 38 citati in un paio di punti della
  documentazione, ora corretti. È basso: ogni fotogramma dura 34 ms, e un
  inciampo di venti millisecondi dentro quella finestra è una riga ben
  visibile. A refresh più alto lo stesso inciampo peserebbe molto meno.

### Documentazione
- **README riscritto.** Era fermo alla 3.4 e dichiarava nove servizi su
  dodici: mancavano Scadenze, Google Calendar, il Game Boy, Breakout e
  Invaders, e la tabella delle priorità ne elencava sei su dieci. Ora c'è
  anche l'indice dei PDF in `docs/`, e la regola per aggiungere un servizio
  dice tutte e quattro le cose da fare invece di tre.

### Prestazioni
- Si chiede a Google **ogni quindici minuti**, e mai più spesso: il pannello
  ridisegna trenta volte al secondo, un calendario no. La riga di stato della
  pagina Servizi legge **solo la cache** e non apre mai una connessione: è la
  pagina che si apre quando qualcosa non funziona, e non deve poter restare
  appesa su una chiamata che non risponde. Un errore di rete non cancella gli
  appuntamenti già noti.

## [4.6.1]

### Aggiunto
- **Colori dello schermo Game Boy**: verde DMG, grigio, ambra, arancione, blu
  notte, o quattro colori scelti a mano. Il Game Boy non ha colori — ha
  quattro gradazioni — e su un pannello LED l'ambra e l'arancione si leggono
  spesso meglio del verde del 1989. Le cartucce Game Boy Color portano i
  colori loro e ignorano la scelta.

### Corretto
- **I campi dell'immagine tornavano indietro da soli.** Il log della
  preparazione faceva ricaricare la pagina ogni tre secondi *per sempre*, e
  un valore appena scritto spariva se non si premeva subito Invio. Ora la
  pagina guarda il log solo mentre la preparazione gira davvero.
- Lo stato del WAD è tornato nella pagina di Doom, dove appartiene: nella
  scheda degli emulatori esterni parlava di uno dei due soltanto.

## [4.6]

### Aggiunto
- **Spostamento verticale dell'immagine Game Boy.** L'overscan taglia metà
  sopra e metà sotto, ma i giochi non sono simmetrici: il punteggio sta in
  alto, il campo di gioco in basso, e quale metà interessa cambia da cartuccia
  a cartuccia. Un numero negativo alza la finestra, uno positivo la abbassa.
  La finestra non esce mai dallo schermo del Game Boy — oltre il bordo il
  valore smette di avere effetto — e senza overscan non c'è niente da
  spostare.

## [4.5.4]

### Corretto
- **Il servizio non partiva.** Il Runtime assegnava a `giochi.esclusiva` un
  metodo del Game Boy **tre righe prima** di costruire la sorgente:
  `AttributeError` all'avvio, processo morto, pannello nero. L'oggetto ora si
  costruisce prima del cablaggio, e l'assegnazione è una lambda, così il
  collegamento non dipende dall'ordine delle righe.

### Aggiunto
- **`test_avvio.py`: il servizio si avvia.** È la prova che mancava, ed è la
  ragione per cui quarantasei suite verdi non hanno visto un guasto totale:
  provavano le sorgenti una per una e le pagine web con un runtime finto,
  cioè tutto tranne il punto in cui il programma si mette in piedi. Ora il
  pannello è finto ma il Runtime è quello vero, con le sue sorgenti, il suo
  cablaggio e un giro di rendering completo. Verificata rimettendo il difetto:
  fallisce.

## [4.5.3]

### Corretto
- **I pulsanti globali rubavano i tasti al Game Boy.** Premendo B (cerchio) si
  usciva dalla partita — cerchio è l'uscita globale — e Start e Select, che su
  Tetris servono a scegliere i giocatori, scorrevano i giochi invece di
  arrivare alla console. È la stessa classe di difetto della 3.8.2: due
  lettori ricevono lo stesso evento e gli danno significati diversi.
  Ora, mentre il Game Boy gioca, il lettore dei giochi **si fa da parte**:
  croce, cerchio, Start e Select sono della console. Resta **PS** per uscire,
  che è il significato che quel tasto ha sulla console vera.

### Aggiunto
- **Il Game Boy entra nel giro del tasto Start**, come Doom, se PyBoy è
  installato e la cartuccia scelta è valida — così non può esistere una
  casella su cui Start non fa niente. Si può escludere dalla pagina Giochi.
- Il tasto PS ha ora un'azione propria (`home`) distinta da Start: fuori da
  una sessione esclusiva fa quello che ha sempre fatto, scorrere i giochi.

## [4.5.2]

### Corretto
- **La condivisione SMB delle ROM sembrava non esistere.** Il codice per
  crearla c'era, ma la pagina non diceva se fosse stata fatta: la cartella la
  crea anche un `mkdir`, mentre dal computer non si vede niente finché in
  `smb.conf` non c'è la sezione. Ora la pagina Game Boy elenca i tre passi —
  emulatore, cartella, condivisione — ognuno con il suo stato e il nome di
  rete scritto per esteso, e il pulsante resta disponibile per ripetere la
  preparazione.
- La condivisione si crea **prima** dell'emulatore: con `set -e` un `pip` che
  fallisce fermava lo script, e la cartella condivisa in fondo non veniva mai
  creata.

## [4.5.1]

### Modificato
- Doom e il Game Boy escono dalla scheda dei giochi scritti per il pannello e
  stanno in una scheda loro, **Emulatori esterni**: sono due programmi
  separati che fanno la stessa cosa — prendere il pannello per una partita — e
  mettere il Game Boy dentro Doom dichiarava una gerarchia che non esiste.

## [4.5]

### Aggiunto
- **Game Boy sul pannello**, con l'emulatore PyBoy. Stessa forma di Doom:
  processo separato, fotogrammi grezzi su una pipe, sessione che prende il
  pannello per presa esclusiva e lo restituisce uscendo.
  - **Condivisione SMB `dmd-rom`** per le ROM, aperta da `gb/setup_gb.sh`
    insieme all'installazione di PyBoy — dal pulsante nella pagina, perché
    dopo un aggiornamento via rete non c'è nemmeno una sessione SSH aperta.
  - **Overscan regolabile**: toglie righe sopra e sotto allo schermo del Game
    Boy, quindi a parità di 64 righe l'immagine sul pannello diventa più
    larga (71 px a zero, 88 al 20%, 116 al 40%).
  - **Gamma** con la stessa convenzione di Doom, e fotogrammi al secondo
    regolabili (30 di suo: il ciclo di rendering gira a 30, e ogni fotogramma
    in più è traffico di memoria che compete con il pannello).
  - Le ROM si controllano prima di aprirle: estensione, dimensione, **logo
    Nintendo** e somma di controllo dell'intestazione. Un file copiato a metà
    lo dice la pagina, non uno schermo nero.
- Documento **`docs/gameboy.it.md`** e relativo PDF.

### Note
- **Dal pad non si apre mai una sessione Game Boy**, e Start e Select del
  Game Boy stanno sulle levette premute (L3 e R3): i pulsanti fisici con quel
  nome sono globali dalla 3.8.2. Un pulsante deve avere un significato solo.
- Le ROM sono di chi le possiede: questo progetto non ne contiene nessuna.

### Corretto
- `mkpdf.sh` cercava le immagini dei documenti nella cartella da cui veniva
  lanciato: le figure del capitolo 6.4 sparivano dal PDF a seconda di dove si
  eseguiva lo script.

## [4.4]

### Corretto
- **Il ciclo non riscrive più sul pannello un frame identico al precedente.**
  Ogni scrittura rifà l'intero buffer dei piani di bit, e quelle scritture
  contendono il bus di memoria alle letture del thread che aggiorna il
  pannello riga per riga: quando la lettura di una riga si ferma per qualche
  microsecondo, quella riga resta accesa più delle altre. È la riga chiara
  che compare in un punto sempre diverso — misurata sul campo: peggiora
  sotto carico di memoria, diventa sfarfallio sotto carico di disco, non si
  vede nei contatori di interrupt e non cambia con `isolcpus`. Con
  l'orologio fermo si passa da trenta riscritture al secondo a una.

### Aggiunto
- `/api/status` riporta i frame **mostrati** e **saltati**, così il
  risparmio si verifica invece di crederci.

## [4.3]

### Aggiunto
- **Registri RGB forzati** nella regolazione fine del pannello. Scavalca il
  blocco di registro del profilo, per provare **una parola alla volta**
  quando nessun profilo del catalogo va bene del tutto — ghosting, fondo non
  nero, colori impuri sono tutti decisi lì dentro. Campo vuoto = comanda il
  profilo, che resta sempre la via d'uscita.
- Il valore si convalida prima di salvarlo (parole esadecimali di quattro
  cifre, eventualmente per canale con `R:…;G:…;B:…`) e si normalizza:
  in quel campo un errore non dà un'eccezione, dà un pannello che si comporta
  male, e la pagina per capirlo sta su quel pannello.
- Se la libreria installata non conosce l'opzione, il servizio parte lo stesso
  con il profilo invece di morire all'avvio: chi aggiorna il DMD senza
  aggiornare il fork non deve ritrovarsi il pannello nero per una funzione che
  non ha chiesto.

### Corretto
- Due prove di Now Playing fallivano a giorni alterni: davano per scontato che
  fra il messaggio di nascita di Home Assistant e la verifica non passasse
  nient'altro, mentre il giro periodico del ponte pubblica rifiuti, scadenze e
  luminosità per conto suo. Ora aspettano i topic che gli interessano e
  ignorano gli altri.

## [4.2]

### Aggiunto
- **Collegamento del pannello scegliibile dalla pagina Impostazioni**: fili
  diretti sui GPIO, Adafruit RGB Matrix Bonnet, o Bonnet con la modifica PWM.
  Erano già tre mappature della libreria, ma per cambiarle bisognava scrivere
  nel file di configurazione.
- **Il manuale completo ha un §6.4 sulla Bonnet**: foto della scheda di
  riferimento, foto del ponticello 4–18 da saldare, e il perché le piazzole
  “E” restano vergini sui pannelli FM6373 di questo progetto.

### Modificato
- **Il cablaggio esce dal profilo del pannello.** Che pannello è e come è
  collegato sono due fatti indipendenti: tenerli insieme avrebbe significato
  che riapplicare il profilo, con la Bonnet montata, riporta l'uscita sui
  piedini del cablaggio a fili e spegne il display. Ora il profilo non tocca
  la mappatura, e viceversa.
- Una mappatura fuori elenco non viene scritta: un nome inventato non dà un
  errore, dà un pannello nero, e la pagina da cui rimediare sta su quel
  pannello.

## [4.1]

### Corretto
- **Le Scadenze non si potevano accendere o spegnere dalla pagina Servizi.**
  La chiave c'era in configurazione, ma l'elenco dei servizi della pagina è
  scritto a mano nel codice: una chiave nuova non compare da sola. Ora c'è
  anche l'interruttore, e una prova nuova chiede la regola invece del caso —
  ogni chiave di `services` deve avere il suo interruttore in pagina.

### Aggiunto
- **Interruttore delle Scadenze anche in Home Assistant**, come gli altri
  servizi.
- **Spegnere il servizio spegne anche il semaforo.** Il semaforo lo disegna
  l'orologio, non la sorgente Scadenze: senza un controllo esplicito
  l'interruttore avrebbe fermato l'avviso lasciando le lampade accese, cioè
  un interruttore che obbedisce a metà.

### Modificato
- **Lampade del semaforo dimezzate**: cerchi da 7 pixel invece di 13, con 2
  di distacco, centrati nella banda sotto la data invece che appoggiati in
  alto.
- Aggiornando dalla 4.0 il servizio Scadenze resta **acceso**: era attivo di
  fatto, e un aggiornamento non deve spegnere una cosa che si sta guardando.
  Da lì in poi vale quello che si sceglie in pagina.

## [4.0]

### Aggiunto
- **Scadenze: appuntamenti e pagamenti, con un semaforo a destra dell'orologio.**
  Assomiglia al calendario dei rifiuti, ma le differenze contano più delle
  somiglianze.

  **Le cadenze sono altre.** I rifiuti hanno un ritmo settimanale — quali giorni,
  ogni quante settimane. Una bolletta no: è mensile, trimestrale, annuale.
  Multipli di mesi, ancorati a una data di partenza. Il 31 gennaio più un mese è
  il 28 febbraio e non il 3 marzo: una rata che scade il 31 non deve spostarsi di
  tre giorni ogni febbraio.

  **Una scadenza si chiude.** Un bidone si espone e basta; una bolletta si paga,
  e da quel momento quell'occorrenza è storia. Chiudere una periodica apre da
  sola la successiva; una una tantum sparisce dall'elenco ma la voce resta, così
  la si può riaprire se si è spuntata per sbaglio.

- **Il semaforo è tre lampade, non un cerchio che cambia colore.** Con tre
  lampade la posizione dice già l'urgenza, e da lontano si legge prima il *dove*
  del *che colore* — che per chi non distingue bene i colori è l'unica cosa che
  funziona. Occupa i 68 pixel che avanzano a destra dell'ora, sotto la data,
  come i 68 di sinistra sono della colonna dei rifiuti.

  | Giorni | Lampada |
  |---|---|
  | oltre 10 | spento |
  | da 8 a 10 | verde |
  | da 4 a 7 | giallo |
  | da 0 a 3 | rosso |
  | data passata | rosso lampeggiante |

  Le soglie si cambiano dalla pagina. Il 7 sta nel giallo e non nel verde: fra
  due letture possibili si è scelta la più prudente. Il lampeggio è **in fase con
  i due punti dell'ora**: due cose che lampeggiano insieme sembrano un battito,
  sfasate sembrano un guasto.

- **Un avviso periodico sul pannello**, con la forma di quello del radar: titolo
  in alto che scorre se è lungo, data del colore del semaforo, descrizione sotto.
  Scorre solo il titolo — far scorrere tre righe darebbe un pannello che si muove
  tutto e non si legge niente. Sul pannello vanno solo le scadenze su cui il
  semaforo si è già acceso; le altre restano nella pagina, dove c'è spazio per
  leggerle.

- **Un registro che non si cancella mai.** Ogni occorrenza con l'ora in cui è
  stata inserita e quella in cui è stata completata, in un CSV a parte. È l'unica
  parte del progetto in cui serve sapere *quando* è successo qualcosa e non solo
  che cosa succede adesso. Sopravvive alla cancellazione della scadenza, e se la
  riga aperta non c'è più il completamento si scrive lo stesso: meglio una riga
  senza ora di inserimento che un pagamento senza traccia.

- **Le scadenze arrivano anche da Home Assistant, e ci tornano.** Cinque entità
  fisse — prossima data (`device_class: date`), titolo, giorni mancanti, stato
  del semaforo, numero di aperte — più **l'elenco completo come attributi JSON**
  su un topic solo. Non un'entità per scadenza: nascono e muoiono, e ne
  resterebbero di orfane a ogni bolletta pagata.

  Due topic di comando (`dmd/scadenze/aggiungi` con un payload JSON,
  `dmd/scadenze/completa` con un id) permettono di **creare e chiudere scadenze
  da un'automazione**. È la prima parte del progetto in cui i dati viaggiano
  anche all'indietro; un payload sbagliato viene rifiutato senza fermare il
  ponte.

- **Inserimento a mano, o incollando un CSV.** Il separatore — punto e virgola o
  virgola — viene riconosciuto da solo, e le righe senza una data valida si
  saltano dicendo quante sono, invece di far fallire tutto il file.

## [3.8.3]

### Corretto
- **Doom non si avviava più.** Colpa della correzione precedente: la 3.8.2 ha
  tolto a Doom l'unica porta che aveva dal pad — Options, che ora scorre i
  giochi — senza accendere quella che doveva sostituirla. La casella «Doom nel
  giro» nasceva **spenta**, e dal cabinato Doom era diventato irraggiungibile.

  Ora è accesa di serie, e chi aggiorna se la ritrova accesa **una volta sola**:
  da lì in poi la scelta è sua e la migrazione non ci rimette le mani.

### Corretto (trovati guardando, non segnalati)
- **Il giro non chiedeva se Doom fosse pronto**: controllava solo che qualcuno
  *sapesse rispondere*. Un Doom senza WAD valido sarebbe rimasto nel giro come
  una casella su cui premere Start non fa niente. Ora si chiede davvero, e una
  domanda che solleva vale come un no — meglio un giro corto che uno con un
  buco.
- **Se una casella non parte, il giro passa alla successiva** invece di lasciare
  il pannello a nessuno. Premere Start e vedere il nero è il peggio dei mondi. E
  se non parte proprio nessuno, dopo un giro completo si smette invece di
  provare all'infinito.

## [3.8.2]

### Corretto
- **Premendo Start o PS si vedeva un gioco per un attimo, poi Doom se lo
  mangiava.** I lettori di Doom e dei giochi ricevono **lo stesso evento**, e
  quei due pulsanti erano di entrambi: `menu` per Doom — con il permesso di
  aprire una partita — e `ciclo` per i giochi. Una pressione sola faceva due
  cose, e vinceva l'ultima. Da qui anche le sequenze che sembravano casuali:
  dipendevano da chi arrivava per primo.

  **Un pulsante deve avere un significato solo.** Start, PS e Select sono ora
  *globali* e appartengono ai giochi: i primi due scorrono il giro, Select esce
  da qualunque partita — Doom compreso, che prima non si chiudeva così.

  Doom li perde. In cambio `menu` e `invio` si spostano sulle levette premute
  (L3 e R3), che nessun altro usa: ci rimettono `arma1` e `arma2`, che restano
  sui tasti numerici della tastiera e sui pulsanti della pagina. Cambiare arma
  si può fare in altri modi; uscire da un menu con il pad no.

- **Nessun pulsante del pad può più far cominciare Doom**, e la regola è scritta
  nel codice, non solo nella tabella dei pulsanti: resta vera anche se domani
  qualcuno rimettesse Options fra quelli di avvio. A Doom ci si arriva dal giro
  dei giochi (se lo si è incluso), dalla sua pagina, o da Home Assistant. La
  casella «il pad può far cominciare una partita» nella pagina Doom era
  diventata una promessa non mantenuta ed è stata tolta.

- **Una guardia buona anche per il futuro:** da un comando non si apre una
  partita **mentre il pannello è di qualcun altro**. La presa è l'unica cosa che
  sappia chi sta lavorando in questo momento, e adesso le si chiede prima di
  aprire. Vale per qualunque sorgente, non solo per queste due.

## [3.8.1]

### Corretto
- **Il tasto Start apriva Doom una volta sola.** Dopo, il giro proseguiva fra
  gli altri giochi e Doom non tornava mai più — nemmeno uscendo e ricominciando.
  Erano **tre** difetti insieme, e nessuno dei tre si vedeva senza gli altri.

  **Il giro apriva i giochi senza passare dal runtime**, quindi non chiudeva
  Doom: il processo restava vivo dietro le quinte, in sessione per sempre. La
  regola dell'esclusività era stata scritta nella 3.7 nel punto giusto — è il
  giro che le passava accanto.

  **Doom già in sessione usciva subito senza riprendere la presa del pannello.**
  «Sono in partita» e «ho il pannello» sono due fatti diversi, e un gioco
  apertosi sopra gliel'aveva portata via: si rientrava in una partita che non si
  vedeva, e il pannello restava a *nessuno* — l'arbitro ripiegava sull'orologio.
  È questo che rendeva il difetto definitivo invece che passeggero.

  **La posizione nel giro si leggeva dalla partita in corso**, che con Doom
  acceso non è dei giochi: la risposta era vecchia, il giro ripartiva da capo e
  una casella spariva per sempre.

  Ora la posizione si ricorda a parte e sopravvive a una partita di Doom, la
  prima pressione **riprende** l'ultimo gioco invece di saltare al successivo, e
  c'è una prova per ciascuno dei tre difetti: rimettendone uno qualsiasi, la
  suite fallisce.

- **Tre funzioni esistevano in due copie identiche.** `_dispositivi_input`,
  `tastiere` e `joystick` erano sia in `comandi.py` sia in `doom.py`, e la copia
  locale — definita dopo l'import — vinceva sull'originale. Era esattamente la
  duplicazione che lo spostamento della 3.6 doveva togliere, sopravvissuta
  perché nessuno l'aveva guardata: due copie identiche non danno mai errore.

## [3.8]

### Corretto
- **In Now Playing l'artista e l'album si toccavano.** Le righe nascevano da
  frazioni fisse dell'altezza (0,33 e 0,56): su sessantaquattro righe l'artista
  finiva esattamente dove cominciava l'album — zero pixel di spazio — e la `g`
  di «D'Agostino» entrava nel titolo del disco.

  Non era un pixel da spostare a mano. Era che nessuno aveva chiesto ai font
  quanto spazio volessero: ora le righe si impilano dalle **metriche** —
  ascendente più discendente, che non dipendono dal testo — con uno spazio
  garantito fra l'una e l'altra. Su 64 righe sono tre pixel, e restano tre a
  qualunque altezza di pannello.

  La prova rende ogni riga da sola e verifica che il suo inchiostro non tocchi
  quello della vicina, usando stringhe piene di discendenti, che sono il caso
  peggiore. Rimettendo il layout vecchio la prova fallisce, come deve.

### Aggiunto
- **Il tasto Start del pad scorre i giochi.** Premuto una volta si gioca,
  premuto ancora si passa al successivo; **Select** esce (e cerchio resta una
  via d'uscita, per chi ce l'ha nelle dita da Doom). Non c'è un menu da
  attraversare: su un pannello alto 64 pixel un menu costa più di quello che
  risolve.

  **Doom entra nel giro solo se lo si chiede** — parte in qualche secondo e
  vuole un WAD preparato, e finirci dentro per sbaglio mentre si cerca Breakout
  stona. La sorgente dei giochi però non conosce Doom: il runtime le passa due
  funzioni, «è pronto?» e «aprilo», e tanto le basta.

- **I due tasti del cabinato si imparano, non si indovinano.** Una pulsantiera
  da flipper manda codici che non stanno su nessuna tastiera da ufficio, e
  cercarli con `evtest` è una serata persa: si preme **Impara** nella pagina e
  poi il pulsante sul cabinato, e il codice arriva da solo. Il lettore di
  `/dev/input` ha ora un aggancio che consegna i codici grezzi prima di
  tradurli, e mentre si impara l'evento viene ingoiato invece di fare anche il
  suo mestiere.

### Modificato
- **Il tasto dedicato è l'unico esente dalla casella «un tasto può far
  cominciare una partita»**, che resta spenta di serie. Quella casella protegge
  dal tasto sfiorato per caso, ed è giusta; ma Start è un gesto deliberato, e se
  ci passasse sotto anche lui la funzione nascerebbe spenta e sembrerebbe rotta.
  È la stessa distinzione che vale da sempre per Options sul pad.

## [3.7]

### Aggiunto
- **I giochi si accendono e si spengono da Home Assistant**, come Doom: un
  interruttore MQTT per gioco (`switch.dmd_gioco_breakout`,
  `switch.dmd_gioco_invaders`), che compare da solo con MQTT Discovery.
  L'elenco degli interruttori è **costruito dall'elenco dei giochi**, non
  scritto a mano: aggiungerne uno domani basta a farlo comparire anche lì.

  Lo stato non viene dalla configurazione — una partita non è un valore
  salvato, è qualcosa che sta succedendo — ma dalla sessione in corso: se si
  chiude per inattività, l'interruttore in Home Assistant torna a OFF da solo.

- **Un manuale PDF per i controller** (`docs/DMD_joypad.pdf`): collegamento del
  DualShock 4 via USB e via Bluetooth, verifica, mappa dei comandi per i giochi
  e per Doom, e la tabella dei guasti tipici — cavo di sola ricarica, `trust`
  dimenticato, modulo `joydev` non caricato.

### Corretto
- **Aprire una partita mentre ne girava un'altra non dava errore: dava un
  processo Doom vivo dietro le quinte.** Doom e i giochi si contendono la stessa
  presa del pannello, e chi la prende per ultimo vince — ma l'altro resta
  convinto di essere in partita, con il suo processo che si tiene in piedi da
  solo e Home Assistant che mostra Doom acceso mentre sul pannello c'è Breakout.

  Aprire una partita ora passa da un punto solo, il runtime, che è l'unico a
  conoscerle entrambe. Ci passa anche la web UI, non solo MQTT: altrimenti la
  regola varrebbe per Home Assistant e non per il pulsante Gioca.

- **La pagina Giochi non aveva i campi per indicare tastiera e joystick a
  mano** (3.6.1). La pagina Doom sì, ed è lì che si finisce quando il
  riconoscimento automatico sbaglia — il caso reale è il modulo `joydev` non
  caricato, che lascia il pad senza gestore `js` e quindi invisibile.

## [3.6]

### Aggiunto
- **Due giochi scritti per il pannello: Breakout e Invaders.** Non sono
  emulatori, ed è una scelta misurata: su 256×64 non calza nessuna piattaforma
  storica. La più vicina — il NES, che almeno è largo 256 — andrebbe schiacciata
  di 3,75 volte in verticale, e a quel punto un alieno alto otto pixel ne
  diventa due e il testo di stato è poltiglia. Scriverli *per* il 4:1 costa meno
  che adattare qualcosa che 4:1 non è mai stato.

  E permette di **usare** la forma invece di subirla: il campo di gioco prende i
  200 pixel di sinistra, i 56 di destra diventano un tabellone con punteggio,
  record e vite — spazio che su uno schermo 4:3 non ci sarebbe e che qui
  resterebbe vuoto.

  **Breakout** è quello che soffre meno il pannello, perché il muro è largo per
  natura. Fra muro e racchetta però ci sono trenta pixel invece di duecento: la
  palla parte lenta e accelera ogni quattro mattoni, altrimenti non si capisce
  cosa è successo. L'angolo dipende da dove si colpisce, così la racchetta è uno
  strumento di mira e non un muro.

  **Invaders** ha tre file invece di cinque — la discesa originale in
  sessantaquattro righe non ci sta — un colpo per volta come nell'originale,
  ripari che si consumano dove vengono colpiti, e la schiera che accelera man
  mano che si svuota.

- **Una sezione «Giochi» nel menu, che raccoglie anche Doom.** Doom mantiene la
  sua pagina, raggiungibile da lì, perché ha impostazioni che gli altri non
  hanno: preparazione, scelta del WAD, taratura della fascia.

### Modificato
- **Come Doom dalla 3.2, i giochi sono una partita e non un servizio**: si preme
  Gioca, i servizi si fermano, il pannello è della partita per presa esclusiva;
  si esce e tutto riprende. È lo stesso meccanismo già collaudato, non un
  secondo. La differenza è che questi girano **dentro** il processo: Doom sta
  fuori per una ragione di licenza (GPL2 dentro GPLv3 non ci sta) e ne paga il
  prezzo in pipe, compilazione al primo avvio e un binario che l'aggiornamento
  via rete ha già cancellato una volta.
- **La lettura di tastiere e pad esce da `doom.py` e diventa un modulo suo.**
  Una regola come la zona morta di una levetta, o l'intervallo di un asse chiesto
  al kernel, non può esistere in due copie. Doom e i giochi ora leggono con lo
  stesso codice — e per la prima volta quel codice ha una prova che non richiede
  un pad in mano: un evento di `/dev/input` è una struttura di ventiquattro
  byte, e si costruisce a mano.

### Corretto
- **Il menu in alto usciva dalla finestra.** `nav` era un flex senza
  `flex-wrap`: le voci che non ci stavano sparivano a destra, senza che niente
  lo lasciasse intuire. Ora vanno a capo — verificato con un browser vero a
  quattro larghezze: su un telefono da 390 px le undici voci stanno su tre
  righe, nessuna tagliata e nessuno scorrimento orizzontale. Da desktop resta
  una riga sola, come prima.
- **A Breakout la palla poteva restare incastrata in verticale.** Colpita
  esattamente al centro della racchetta ripartiva a novanta gradi, saliva e
  scendeva sulla stessa colonna all'infinito, e finita quella colonna il muro non
  si poteva più completare. Non è un caso di scuola — un giocatore che insegue
  bene la palla la centra quasi sempre — ed è stata la prova automatica a
  trovarlo, non una partita a mano. Ora l'angolo ha anche un minimo, con un filo
  di caso che impedisce alla traiettoria di diventare periodica.

## [3.5]

### Aggiunto
- **Fascia oraria del Media Player**, con la stessa forma di Night mode: un
  flag, un'ora di inizio e una di fine, passaggio di mezzanotte compreso. Sta
  nella pagina Media, sopra l'anteprima.

  **Il flag viene prima di tutto.** Spento — che è il predefinito — il Media
  Player lavora sempre, esattamente come ha sempre fatto: chi aggiorna non si
  accorge di niente finché non lo accende lui.

  Fuori dalla fascia il servizio si ferma **davvero**. Non è una sorgente
  accesa che perde la gara con l'orologio: è il thread che non gira. Niente
  decodifica, niente letture dalla scheda SD nelle ore in cui nessuno guarda
  il pannello — che è lo stesso motivo per cui nella 1.6 la libreria è passata
  in memoria. Riparte da solo quando la fascia si riapre, senza toccare
  l'interruttore nella pagina Servizi, che resta acceso perché è una scelta
  dell'utente e non della fascia.

- **La riga di stato distingue i due motivi.** «fuori dalla fascia
  08:00–23:00» invece di «disabilitato»: sono due cose diverse e hanno due
  soluzioni diverse, e senza dirlo l'unica spiegazione visibile sarebbe un
  interruttore acceso accanto a un servizio che non fa niente.

### Modificato
- **Lo Sleep mode resta prioritario, e lo resta per costruzione.** Le due
  fasce non si parlano: il Media Player non sa niente dello Sleep, quindi non
  ha alcun modo di svegliare un pannello che deve stare spento. Sommare le due
  condizioni dentro la regola della fascia avrebbe voluto dire scrivere la
  stessa precedenza in due posti — e prima o poi in due modi diversi. La
  precedenza resta dov'era: nel ciclo di rendering, a valle di chi ha vinto.
- **La regola delle fasce esce da `dmdd` e diventa un modulo suo** (`fasce.py`).
  Da dentro una sorgente `dmdd` non è importabile — è un ciclo di import — e
  senza quello il Media Player non aveva modo di sapere perché era fermo: la
  scelta era fra duplicare la regola e non spiegare niente.

## [3.4.1]

### Corretto
- **La pagina Rifiuti rispondeva Internal Server Error.** Dentro il ciclo dei
  sette giorni della settimana `loop` è quello **interno**, e in Jinja non
  esiste nessun modo di risalire a quello esterno: la casella del giorno non
  sapeva a quale voce apparteneva, e la pagina cadeva prima ancora di
  disegnarsi. L'indice della voce ora si lega una volta sola, all'inizio del
  blocco, e vale in tutto il blocco — annidato o no.
- **Il giro di prova delle pagine web era rimasto fermo a otto indirizzi** e
  non comprendeva né Rifiuti né Doom: è per questo che un errore di template è
  arrivato fino al browser invece di fermarsi qui. Ora le pagine provate sono
  dodici, e non basta più che rispondano: si controlla che i campi ci siano
  davvero — 6 voci per 7 giorni, con gli indici giusti — che i loro nomi siano
  quelli che l'API rilegge, e che giorni, cadenza, data di riferimento e fascia
  oraria tornino indietro interi dopo un salvataggio.

## [3.4]

### Aggiunto
- **Calendario della raccolta rifiuti, nella colonna libera dell'orologio.**
  A sinistra dell'ora c'è sempre stato uno spazio vuoto; ora ci compaiono i
  nomi di quello che va esposto stasera, uno sotto l'altro, ciascuno con il
  proprio colore.

  Non c'è nessun portale da interrogare e nessuna credenziale da custodire.
  La raccolta ha una cadenza fissa: la si descrive **una volta** — quali
  giorni della settimana, con che cadenza — e il calendario si calcola da sé,
  per sempre, senza rete e senza dipendere da un servizio che domani cambia
  l'API o chiude. Le cadenze previste sono quattro: settimanale, quindicinale,
  prima e terza occorrenza del mese, seconda e quarta.

  La quindicinale è ancorata a una **data di riferimento**, non alla parità
  della settimana ISO. Sembra un dettaglio ed è invece la differenza fra un
  calendario che funziona e uno che sbaglia: un anno ha 52 o 53 settimane, e
  chi conta la parità salta silenziosamente un turno a ogni Capodanno. Con la
  data di riferimento l'intervallo resta di 14 giorni esatti attraverso il
  cambio d'anno — verificato su tre Capodanni consecutivi.

- **Due tabelle di eccezioni, perché sono due cose diverse**: i giorni di
  **mancato servizio** e quelli di **servizio straordinario**. Ogni comune fa
  storia a sé, e la festività che sposta il giro si scrive come due righe — la
  soppressione del giorno saltato e il recupero del giorno aggiunto — che
  funzionano insieme. Una riga scritta male viene scartata da sola, con il
  numero di riga nel log, senza portarsi via il resto del calendario.

- **Attività comunali accanto ai rifiuti, con una fascia oraria propria.** Il
  lavaggio strada che vieta la sosta dalle 00:00 alle 06:00 non è un bidone da
  esporre: l'avviso resta finché il divieto è in vigore, non fino alle 8. Il
  tipo di voce si sceglie per voce, e le due caselle dell'orario compaiono
  solo dove hanno senso.

- **L'evento su Home Assistant, non il calendario.** Per ogni voce un
  `binary_sensor` che dice se in questo momento va esposta e un `sensor` con
  la data della prossima raccolta (`device_class: date`). Con quei due si
  scrive un'automazione in tre righe, senza integrazioni aggiuntive e senza un
  secondo posto in cui i dati possano divergere da quello che si legge sul
  pannello. Una voce rinominata o tolta si porta via le proprie entità, invece
  di lasciarne in giro una che non si aggiorna più e che nessuno sa da dove
  venga.

### Modificato
- **L'orologio resta centrato.** La colonna non sposta l'ora per farsi posto:
  sceglie il carattere più grande fra cinque in cui *tutti* i nomi stanno
  nello spazio libero, e solo se nemmeno il più piccolo basta accorcia i nomi.
  Il promemoria si accende alle 18 della sera prima e si spegne al passaggio,
  con gli orari regolabili.
- **«Gestione media» esce dal menu in alto.** Era un doppione del collegamento
  già presente nella pagina Media, che diventa un pulsante.

## [3.3]

### Aggiunto
- **Joystick: pad PS4 e compatibili, e pad da PC.** Sotto Linux sono
  dispositivi di `/dev/input` come le tastiere, quindi si leggono con lo stesso
  codice e senza librerie in più. Il lavoro vero è negli assi: le levette non
  sono premute o rilasciate, hanno un valore dentro un intervallo che cambia da
  pad a pad — 0..255 su un DualShock 4, -32768..32767 su molti pad da PC — e
  l'intervallo **si chiede al kernel** invece di darlo per scontato.

  La conversione in premuto/rilasciato ha una zona morta al 40% e rilascia al
  28%: senza due soglie diverse una levetta tenuta appena oltre il limite fa
  scattare il personaggio invece di farlo camminare.

  Il tasto Options può far **cominciare** una partita, al contrario della
  tastiera: un pulsante preciso su un pad che si tiene in mano non si preme per
  sbaglio, mentre un tasto del cabinato sfiorato per caso sì.

- **Doom si accende e si spegne da Home Assistant**, come interruttore MQTT. Lo
  stato non viene dalla configurazione — lì non c'è — ma dalla partita in
  corso, così una chiusura per inattività o un avvio fallito riportano
  l'interruttore a OFF da soli.

### Modificato
- **Il gamma predefinito passa da 0.70 a 1.15.** Lo 0.70 schiariva, ed era un
  ragionamento fatto a tavolino: sul pannello vero sbiancava e rendeva
  illeggibili i menu. Chi ha ancora il vecchio predefinito **esatto** viene
  corretto dalla migrazione; chi ha tarato a mano non viene toccato.

## [3.2]

### Modificato
- **Doom non è più un servizio: è una partita.** Si preme «Gioca», tutti i
  servizi si fermano, si gioca; si esce, e tutto riprende da dove stava.

  L'interruttore nella pagina Servizi non c'è più, e con lui se ne vanno
  l'attract mode della 3.0 e la deroga nell'arbitro della 3.1 — tre meccanismi
  per una funzione che nessuno aveva chiesto e che non ha mai funzionato:
  prima Doom non si vedeva mai, poi restava a schermo dopo l'uscita da una
  partita, con il Media Player che spuntava ogni tanto perché aveva la
  priorità più alta.

  Ora il processo esiste **solo mentre si gioca**, e per tutta la partita il
  pannello è suo per presa esclusiva. La tastiera del cabinato comanda il gioco
  ma non lo fa *cominciare*, a meno che non lo si chieda esplicitamente: il DMD
  sta in mezzo a un flipper, e un tasto sfiorato per caso non deve portarsi via
  il pannello a metà partita.

## [3.1.1]

### Corretto
- **Le migrazioni della configurazione non venivano eseguite.** Stavano in
  `update.sh`, e l'aggiornamento via rete non lo esegue: copia i file e riavvia.
  Le chiavi nuove sopravvivevano lo stesso, perché i valori predefiniti si
  fondono a ogni caricamento, ma una **trasformazione di valore** no — e il
  percorso del WAD restava quello vecchio mentre la preparazione spostava i
  file. Doom si rifiutava di partire. Le trasformazioni ora stanno in
  `dmdconf`, l'unico punto attraversato da qualunque strada di aggiornamento.
- **Scegliere il WAD non faceva ripartire niente** se il processo era già
  morto — cioè proprio nel caso in cui quel pulsante serve.
- **Una sorgente che non riesce ad avviarsi non ci riprovava mai**: `start()`
  si considerava già avviata. Ora il ciclo ritenta ogni 30 s, così correggere
  un percorso sbagliato basta a rimettere in moto.
- **I file di servizio di macOS** (`._*`, `.DS_Store`) sono vietati sulle
  condivisioni SMB: il Finder non li crea più, quelli già copiati vengono
  tolti, e non compaiono più fra i WAD.
- **`setup_share.sh` ora viene installato in `/opt/dmd`**, altrimenti
  `setup_doom.sh` non lo trovava e la condivisione dei WAD non nasceva.

## [3.1]

### Corretto
- **L'attract mode di Doom non compariva mai su un cabinato acceso.** La
  funzione era descritta come «quando nessuno tocca niente Doom gioca da solo»
  e nella pratica non esisteva: Doom girava benissimo, non arrivava mai a
  schermo. La colpa non era sua ma di ZeDMD — finché Batocera è collegato e ha
  mandato almeno un fotogramma il pannello è suo, e su un cabinato acceso
  quella condizione è sempre vera.

  Il rimedio non è alzare la priorità di Doom, che così vincerebbe anche
  durante una partita, e non è tornare alla regola della 1.12.2, che faceva
  sparire l'immagine del tavolo dopo un minuto per lasciare il posto
  all'**orologio** — quello era un guasto ed era stato corretto apposta.

  La distinzione giusta è fra **avere diritto al pannello** e **avere qualcosa
  da dire**. L'arbitro conosce ora i *riempitivi*: sorgenti che possono
  subentrare a chi è rimasto fermo oltre una soglia (60 s, regolabile, zero
  per disattivare) e che restituiscono il pannello al primo fotogramma nuovo.
  Tre guardie perché il rimedio non diventi peggiore del male:
  - la deroga esiste **solo finché un riempitivo è pronto**, quindi senza Doom
    acceso nulla cambia rispetto a prima e la 1.12.2 non torna;
  - si esclude **solo** il vincitore fermo e si rifà la scelta, invece di
    promuovere d'ufficio il riempitivo: un aereo di passaggio vale più di Doom
    che gioca da solo;
  - durante una **partita** non c'entra nulla: lì il pannello è preso, non
    vinto ai punti.

### Aggiunto
- **Condivisione di rete per i WAD.** `/srv/dmd/doom`, esposta come
  `\\<ip-del-pi>\dmd-doom` accanto a `dmd-media`. I WAD sono l'unica cosa di
  Doom che si mette e si toglie a mano, e chiedere una sessione SSH per
  copiare un file non è un modo di lavorare. La cartella contiene **solo** i
  WAD: il binario e i salvataggi restano in `/var/lib/dmd/doom`, dove non si
  possono cancellare per sbaglio.
- Chi arriva dalla 3.0.1 se li ritrova spostati lì dalla preparazione, e la
  configurazione si riallinea da sola — nel processo che possiede la
  configurazione, non riscrivendo il file JSON sotto il naso del servizio.
- I WAD si cercano ora in **due** posti, la cartella condivisa e quella del
  file configurato, così un percorso personale continua a comparire
  nell'elenco. L'ordine di preferenza è quello dei nomi, non quello delle
  cartelle: un `doom2.wad` tuo viene prima di un `freedoom1.wad` condiviso.
- `setup_share.sh` accetta percorso, nome e descrizione della condivisione:
  era cablato su `dmd-media`.

## [3.0.1]

### Aggiunto
- **«Prepara Doom» dalla pagina web.** Nella 3.0 la compilazione andava
  lanciata a mano da SSH, sempre, anche partendo da un'installazione pulita —
  e dopo un aggiornamento via rete non c'è nemmeno una cartella scompattata da
  cui lanciare lo script. Ora un pulsante fa partire la stessa preparazione in
  sottofondo e la pagina ne mostra il log mentre va, come già fa
  l'aggiornamento OTA; quando finisce si aggiorna da sola. Lo script a riga di
  comando resta, per chi lo preferisce.
- **Controllo vero dei WAD.** Che il file esista non basta: i primi quattro
  byte dicono se è un gioco completo (`IWAD`), un'estensione che da sola non
  parte (`PWAD`) o tutt'altro, e la dimensione dice se è stato scaricato a
  metà. Prima un file rinominato per sbaglio faceva fermare Doom con un
  messaggio che non aiutava nessuno. Il controllo c'è in tre posti: nello
  script, nella pagina e nella sorgente prima di avviare il processo.
- **La pagina elenca i WAD trovati** nella cartella, con nome, dimensione e
  motivo per cui uno non va bene, e permette di sceglierlo. Il WAD si sceglie
  fra quelli trovati, non scrivendo un percorso a mano.
- **Un WAD tuo viene prima di Freedoom.** Chi ha comprato Doom copia il suo
  (`doom.wad`, `doom1.wad`, `doom2.wad`, `plutonia.wad`, `tnt.wad`) nella
  cartella: la preparazione lo riconosce, non scarica Freedoom per niente, e
  la pagina lo propone come predefinito.
- La pagina avvisa se il programma è stato compilato **prima** dell'ultimo
  aggiornamento del sorgente C: funziona, ma non è quello che dice il sorgente
  installato, e cercare una modifica che non si vede fa perdere un pomeriggio.

## [3.0]

### Aggiunto
- **Doom sul pannello.** Gira come programma a sé — doomgeneric con l'uscita
  ritagliata a 256×64 — e parla con il servizio da una pipe: fotogrammi da una
  parte, tasti dall'altra. Due processi e non una libreria per tre ragioni, in
  ordine: i sorgenti di Doom sono GPL2 e questo progetto è GPLv3, e due
  programmi che si parlano da una pipe non si collegano; se cade, cade lui e
  il pannello torna all'orologio; e non serve nessun binding.
- Il problema non era la potenza di calcolo — è software del 1993 — ma **la
  forma dello schermo**: Doom disegna 320×200, cioè 1,6:1, e il pannello è
  256×64, cioè 4:1. Schiacciando tutto un nemico sarebbe alto otto pixel. Si
  ritaglia invece una **fascia attorno all'orizzonte**, che è dove stanno i
  nemici, e si buttano via pavimento e soffitto, che è dove non succede
  niente. Fascia e gamma si tarano dalla pagina Doom guardando il pannello.
- **Attract mode gratis.** Quando nessuno tocca niente Doom gioca da solo, con
  i demo che ha sempre avuto dentro. Lì è una sorgente come le altre, con
  priorità bassa: cede a un aereo, a un compleanno e soprattutto a Batocera.
- **Partita.** Al primo comando il pannello diventa suo — Batocera compreso —
  finché non si esce o non lo si lascia fermo abbastanza a lungo. La partita
  comincia facendo ripartire Doom dentro il livello invece di navigare il menu
  a colpi di frecce su un pannello alto sessantaquattro pixel.
- **Due modi di comandarlo, una sola coda di tasti.** La tastiera collegata al
  Raspberry, letta direttamente da `/dev/input` senza librerie in più — è la
  via più diretta, non passa dalla rete — e la pagina web, con i pulsanti e
  con la tastiera del browser. Niente GPIO: sui pannelli SM16380SC D ed E sono
  collegati e i pin che si sarebbero usati non ci sono più.
- `doom/setup_doom.sh` prepara tutto una volta sola: scarica doomgeneric, lo
  compila e prende Freedoom, che è libero. I WAD commerciali non si
  ridistribuiscono: chi ne ha uno suo cambia il percorso nella pagina.

### Modificato
- **La presa del pannello è ora un meccanismo generale.** Era nata nella 2.0.3
  per la gestione media; una sessione di Doom è la stessa cosa — «questo qui
  tiene il pannello finché non ha finito» — quindi invece di scriverla due
  volte se ne è fatta una sola, con due sapori: *a scadenza* per la libreria,
  dove il battito del browser la tiene viva e una scheda chiusa la lascia
  cadere, e *senza scadenza* per il gioco, dove chi gioca può fermarsi a
  guardare una porta senza che il pannello torni all'orologio. Una pagina non
  può chiudere la presa di un'altra.
- Il binario compilato di Doom sta in `/var/lib/dmd/doom`, non in `/opt/dmd`:
  l'aggiornamento OTA cancella e ricopia le sottocartelle del programma, e un
  binario lì dentro sparirebbe a ogni aggiornamento.

## [2.0.3]

### Aggiunto
- **Gestione media**, voce propria del menu accanto a Media. Ci vivono
  l'elenco della libreria, il caricamento dei file e il pulsante «Vedi».
  Entrandoci il pannello passa a chi sta guardando: **tutte le sorgenti sono
  sospese, ZeDMD compreso**. Non è una priorità più alta — quella c'era già
  nella 2.0.2 e non bastava — è una modalità: finché la pagina resta aperta
  nessuno può prendere il posto del file che stai guardando, e fra un file e
  l'altro non subentra nessuno.
- La pagina manda un battito ogni dieci secondi. Se la scheda viene chiusa il
  pannello torna al suo lavoro entro trenta secondi, senza che nessuno debba
  ricordarsi di uscire; il pulsante «Esci dalla gestione» lo restituisce
  subito. Le sorgenti non vengono fermate davvero, solo tenute lontane dal
  pannello: ZeDMD non si disconnette e il radar non riparte da zero.
- Sul pannello, entrando in gestione, compare la scritta «Gestione media». Un
  pannello nero e muto sembrerebbe guasto, e si andrebbe a cercare il problema
  dove non c'è.

### Corretto
- **«Vedi» mostrava il file precedente**, e una **GIF in corso si bloccava**.
  Era lo stesso difetto. L'anteprima riusava `media._show_video` dirottando il
  buffer di uscita del Media Player, e quel ciclo guarda solo i flag del Media
  Player: da fuori non lo si poteva fermare. La richiesta nuova aspettava tre
  secondi, si arrendeva, e il thread vecchio continuava a pubblicare sopra al
  file appena scelto; con due dirottamenti annidati il ripristino finale
  lasciava per sempre il Media Player a disegnare dentro l'anteprima. Ora
  l'anteprima ha il suo ffmpeg e controlla la richiesta di stop a ogni
  fotogramma: l'interruzione avviene in centesimi di secondo invece che mai.
- Premendo «Vedi» il pannello si svuota subito, invece di tenere a schermo il
  file precedente per tutto il tempo del caricamento: quel buco si legge come
  «non ha funzionato».
- Cancellare il file che si sta guardando toglie l'anteprima dal pannello.

## [2.0.2]

### Modificato
- **«Vedi» mostra il file sul pannello, non nel browser.** Guardarlo sul
  computer non risponde alla domanda vera — come viene su *quel* pannello, con
  quella scala e quei colori — ed è per rispondere a quella che si preme il
  pulsante prima di cancellare. L'anteprima è una sorgente a sé con priorità
  **90**: sotto ZeDMD, sopra tutto il resto. Chi ha appena premuto sta
  guardando il pannello adesso, e un aereo di passaggio non ha motivo di
  scavalcarlo; una partita in corso sì.
- **Air Radar: codici della rotta nella forma IATA di tre lettere** anche
  quando il servizio ha risposto in ICAO — `MXP` invece di `LIMC`. Sono le
  sigle stampate sul biglietto, e occupano un carattere in meno.
- **La frase dell'anniversario**: «Domani **è** l'anniversario di …».

### Corretto
- Nella libreria media il pulsante Elimina si sovrapponeva al peso del file:
  `display:flex` su una cella toglie la cella dal calcolo della tabella.
- **Tolte dieci righe con codici ripetuti** dalle tre tabelle di conversione:
  due negli aerei, due negli aeroporti, sei nelle compagnie. Erano innocue —
  vinceva la prima occorrenza — ma facevano un avviso nel log a ogni lettura.

## [2.0.1]

### Corretto
- **Il servizio Compleanni non compariva nella pagina Servizi.** La sorgente
  funzionava, ma l'elenco dei servizi è cablato nel codice e me n'ero
  dimenticato: senza interruttore il servizio non partiva mai, e sul pannello
  non si vedeva niente per quanto si abbassasse l'intervallo.

### Aggiunto
- **Tipo di ricorrenza: compleanno o anniversario.** Terza colonna facoltativa
  del CSV e menu nella pagina; senza tipo vale compleanno, così gli elenchi
  scritti prima continuano a funzionare. La frase cambia di conseguenza — di
  un anniversario non si dice che *compie gli anni*.
- **Pagina Aggiornamenti**, dopo Impostazioni: aggiornamento del programma e
  controllo della libreria della matrice. Sono le uniche due cose che
  cambiano il software installato invece di regolarlo, ed è la ragione per
  cui non stanno più insieme ai colori e agli orari.
- **Libreria media sfogliabile** a pagine da 200: prima si vedevano i primi
  400 file e gli altri non si potevano nemmeno cancellare.
- **Pulsante Vedi** accanto a Elimina: apre il PNG o la GIF in una scheda
  nuova. Prima di cancellare qualcosa bisogna poter guardare che cos'è, e il
  nome del file raramente basta.

### Modificato
- **Air Radar, fascia alta**: numero di volo tutto a sinistra e codici della
  rotta a destra, centrati sull'asse del numero invece che appoggiati alla
  sua base.

## [2.0]

### Aggiunto
- **Compleanni.** Un elenco di date e nomi — importabile da CSV, scrivibile a
  mano dalla pagina, modificabile come testo — e il pannello ricorda chi
  compie gli anni con un messaggio scorrevole, a partire da **48 ore prima**
  di default. L'anticipo, l'intervallo di ricomparsa, durata, colore e
  dimensione si regolano; l'età compare quando l'anno di nascita c'è.
  Priorità 56: sopra il Rolling banner, sotto Now Playing, Radar e ZeDMD —
  un compleanno è un evento datato, non del momento, e può aspettare il giro
  successivo. L'importazione **aggiunge** invece di sostituire: cancellare
  senza avviso quello che c'è già sarebbe la cosa peggiore che possa fare.
- **Profili hardware del pannello.** Un menu nella pagina Impostazioni
  applica in blocco tutti i parametri di un tipo di pannello — geometria,
  driver, indirizzamento, taratura fine. Serve soprattutto a **tornare
  indietro**: un parametro sbagliato non dà un errore, dà un display
  illeggibile, e da lì la memoria non aiuta. Per ora c'è
  `FM6373 & DP32020B` e la voce `Personalizzata`, che lascia i valori come
  sono; quando i pannelli SM16380 funzioneranno si aggiungerà una voce.
- **Night mode e Sleep mode comandabili da Home Assistant**, con gli stessi
  topic e la stessa forma degli altri interruttori.
- **Unità di misura del radar**: quota in piedi o metri, velocità in nodi,
  km/h o mph, distanza in km, miglia o miglia nautiche. Il registro CSV resta
  nelle unità originali, così i passaggi vecchi e nuovi restano confrontabili.

### Modificato
- **La taratura del pannello trovata sul campo diventa il valore predefinito
  dell'installazione**: profondità PWM 10, bit minimo 200 ns, un bit di
  dithering, rallentamento GPIO 5, refresh senza tetto, un ciclo extra a fine
  frame e 300 µs di pausa. Chi installa da zero parte da lì invece di
  ripercorrere la campagna di prove.
- **Air Radar, fascia alta**: l'identificativo del volo è allineato a
  **destra** e alla sua sinistra compaiono i codici della rotta in caratteri
  piccoli. Il numero di volo ha lunghezza variabile: centrato ballava da un
  aereo all'altro, allineato a destra resta fermo.
- **Freccia della rotta con uno spazio per lato** (`Malpensa → Fiumicino`):
  due nomi attaccati alla freccia si leggevano come una parola sola.
- Tabelle di **aerei, aeroporti e compagnie aggiornate** con le versioni
  fornite dall'utente. Chi non ha mai modificato le proprie le riceve
  automaticamente; chi le ha modificate se le tiene.

## [1.12.5]

### Modificato
- **Documentazione del collegamento a Batocera.** Attivare il servizio
  `dmd_real` era una riga sola, e non c'era modo di accorgersi che non fosse
  partito: il `config.ini` da solo non avvia niente, e il sintomo — Raspberry
  in ascolto, nessun client — e' identico a quello di un indirizzo sbagliato.
  Ora i due casi si distinguono con un comando, e la verifica (`ps aux | grep
  dmdserver`, che deve mostrare l'argomento `-c ...`) e' scritta accanto.
- Documentate le trappole incontrate sul campo: la chiave
  `dmd.pixelcade.dmdserver` lasciata da Pixelcade, che non e' l'interruttore di
  `dmd_real`; l'indirizzo rimasto a un Raspberry precedente; e il fatto che
  tenendo premuto il tasto di scorrimento EmulationStation non pubblica nessuna
  immagine, nemmeno al rilascio — comportamento suo, non del collegamento.

## [1.12.4]

### Aggiunto
- Lo stato di ZeDMD riporta i **fotogrammi ricevuti al secondo** e quanti ne
  sono finiti davvero sul pannello: *"connesso da 192.168.0.112 via TCP, 1240
  frame ricevuti (28.4/s), 980 mostrati, ultimo 0 s fa"*.
- Servono a separare due cause che dall'esterno si somigliano. Se durante uno
  scorrimento veloce il Pi riceve pochi fotogrammi al secondo, il limite e' a
  monte — rete o client — e ottimizzare la decodifica non servirebbe a nulla.
  Se ne riceve molti e ne mostra pochi, il limite e' il ciclo di disegno.
  Misurato qui, digerire un fotogramma costa 1,6 ms: il decodificatore regge
  centinaia di fotogrammi al secondo, quindi il sospetto e' altrove.

## [1.12.3]

### Corretto
- **Gli aggiornamenti a zone non facevano ridisegnare il pannello.** Il
  protocollo prevede che sia il comando `RenderFrame` a dire "adesso
  l'immagine e' completa", e le zone si limitavano a scrivere i pixel. Quel
  comando pero' non arriva sempre: l'immagine restava nel buffer, invisibile,
  finche' un aggiornamento successivo non la sbloccava per caso. Si vedeva
  come "cambio gioco selezionato e il DMD resta fermo, ne cambio un altro e
  allora si aggiorna". Ora le zone rimaste in sospeso vengono mostrate
  comunque dopo 120 ms — durante il gioco `RenderFrame` arriva a ogni
  fotogramma e questa rete di sicurezza non scatta mai.
- **Il pannello tornava all'orologio dopo un minuto a menu fermo.** E' una
  regressione della 1.12.2, che misurava la vitalita' sull'ultimo fotogramma
  ricevuto. Sul cabinato l'immagine del tavolo selezionato resta ferma per
  minuti: farla sparire non e' un risparmio, e' un guasto. La regola ora e'
  in due parti: un client collegato che non ha **mai** mandato un fotogramma
  cede il pannello dopo la finestra di cortesia — cosi' dmdserver, che si
  aggancia all'avvio, non lo tiene nero per sempre — mentre uno che ha gia'
  mandato qualcosa lo tiene finche' resta collegato. A connessione caduta
  vale la cortesia sull'ultimo fotogramma, che copre le riconnessioni brevi.

## [1.12.2]

### Corretto
- **Un client ZeDMD collegato non si prende piu' il pannello per sempre.** Su
  Batocera dmdserver e' un servizio permanente: si aggancia all'avvio e resta
  li' anche a menu fermo, mandando keep-alive ogni 100 ms. La sola
  connessione bastava a dare la precedenza a ZeDMD, che senza partita non
  manda niente: il pannello sarebbe rimasto nero e orologio, radar e banner
  non sarebbero piu' ricomparsi. Ora conta l'arrivo dei **fotogrammi**, non
  la connessione e nemmeno il traffico — i keep-alive non sono contenuto.
- La connessione appena aperta vale come segnale di vita per la stessa
  finestra di cortesia (60 s), cosi' il primo fotogramma di una partita non
  arriva su un pannello che ha appena ceduto il posto all'orologio.
- Lo stato del servizio distingue i tre casi che prima si somigliavano:
  nessuno collegato, collegato ma senza un solo fotogramma, in trasmissione.
- Corretto un errore della 1.12.1: i contatori dell'handshake venivano
  inizializzati solo allo spegnimento, quindi la pagina dei servizi andava in
  errore fino al primo handshake. Un test nuovo legge lo stato di **tutte** le
  sorgenti appena costruite, che e' la prova che mancava.

## [1.12.1]

### Aggiunto
- **Il colloquio HTTP che precede il flusso ZeDMD finisce nel registro**, con
  l'indirizzo di chi lo ha chiesto (`[zedmd-http] 192.168.0.112 /handshake`),
  e l'ultimo contatto compare nello stato del servizio.
- Lo stato "in ascolto, nessun client" confondeva due guasti che da fuori si
  somigliano: il client che non ha mai raggiunto il Pi — indirizzo sbagliato,
  rete diversa — e il client che si e' presentato ma non ha aperto il flusso
  sulla 3333. Ora lo stato dice quale dei due.

## [1.12]

### Aggiunto
- **Compagnia aerea** fra i parametri di volo mostrabili sul pannello.
- Non e' un campo che arriva dal servizio: sta nelle **prime tre lettere del
  nominativo**. In `AFR1732` la compagnia e' `AFR`, Air France — il
  designatore ICAO, non la sigla IATA di due lettere del biglietto.
- Terza tabella di conversione, `/var/lib/dmd/compagnie.csv`, modificabile
  dalla pagina Radar e dal file come le altre due. Distribuita con **129
  compagnie**: le europee, le principali intercontinentali, i corrieri merci
  e l'aviazione d'affari.
- Un nominativo che non ha quella forma non ha una compagnia da mostrare:
  l'aviazione generale usa l'immatricolazione (`I-ABCD`), e il campo resta
  vuoto invece di inventarsi una sigla dalle prime tre lettere della targa.
- Il registro dei passaggi guadagna la colonna `airline_name`. Il registro
  esistente viene messo da parte con la data, come sempre quando cambiano le
  colonne, invece di continuare con righe disallineate.

## [1.11.6]

### Corretto
- **Lo scorrimento veniva tagliato allo scadere del tempo dell'aereo**, anche
  a meta' riga: spariva un testo che si stava ancora leggendo, cioe' proprio
  il difetto per cui lo scorrimento esiste. La durata a schermo diventa un
  **minimo**: la passata arriva in fondo e si cambia aereo quando l'ultimo
  carattere e' uscito da sinistra.
- Stessa regola per le pagine: una pagina cominciata si vede per tutto il suo
  turno, invece di essere accorciata dalla scadenza.

## [1.11.5]

### Modificato
- L'etichetta della scelta nuova diventa **"Disposizione informazioni"**:
  quella precedente andava a capo e sfalsava le tre caselle affiancate.

## [1.11.4]

### Aggiunto
- **Che fare quando i parametri di volo non stanno su una riga.** Con nove
  campi selezionati la riga in basso misura circa 400 pixel su 252
  disponibili, e fino a ieri il pannello ne buttava via quattro senza
  segnalarlo. La pagina Radar ora offre tre comportamenti:
  - **a pagine** (predefinito): i campi si dividono in gruppi che ci stanno
    per intero e si alternano ogni tre secondi, regolabili. Non se ne perde
    nemmeno uno e il testo resta fermo;
  - **scorrevole**: la riga passa da destra a sinistra, con velocità
    regolabile. Si legge senza attese, ma è l'unica parte del pannello in
    movimento continuo;
  - **accorcia la riga**: il comportamento storico, per chi lo preferisce.
- Identificativo e rotta **non si muovono mai**: cambia solo la fascia bassa,
  così l'aereo non salta mentre lo stai leggendo.
- Finché i campi ci stanno tutti le tre scelte si comportano allo stesso
  modo: chi ne seleziona quattro non vede cambiare niente.

## [1.11.3]

### Corretto
- **Le rotte non venivano quasi mai tradotte.** La tabella degli aeroporti
  conosceva solo i codici IATA di tre lettere, perche' il servizio routeset
  di adsb.lol e' documentato per restituire quelli. In pratica quel campo
  spesso non c'e', e sia routeset sia hexdb.io ripiegano sui codici ICAO di
  quattro lettere: `LFPG→LIML` invece di `MXP→FCO`. Nessuna riga
  corrispondeva, e sul pannello restavano le sigle.
- La prima colonna dei due file ora accetta **piu' codici separati da `/`**,
  e la riga risponde a tutti: `MXP/LIMC,Malpensa,Milano Malpensa`.
- La tabella distribuita porta gia' **entrambe le grafie per tutti e 326 gli
  scali**, quindi non c'e' niente da fare a mano.
- Un file gia' presente in `/var/lib/dmd` non viene toccato: chi vuole le
  nuove sigle puo' aggiungerle a mano, oppure rinominare il proprio file e
  lasciare che venga ricreato dal modello.

## [1.11.2]

### Corretto
- **Le due tabelle di conversione arrivano anche con l'aggiornamento via
  rete.** Nella 1.11 stavano in una sottocartella nuova, `data/`.
  L'aggiornamento pero' lo esegue il codice della versione *precedente*, che
  l'elenco dei file da installare lo legge dall'archivio scaricato — e
  quindi conosce anche i file nuovi — ma l'elenco delle *cartelle* ce l'ha
  cablato dentro. Quella cartella non veniva creata, le tabelle non
  arrivavano e il controllo finale dell'aggiornamento le dichiarava mancanti,
  facendo tornare indietro tutto. Chi installa dal pacchetto scompattato non
  ha mai visto il problema.
- I due modelli ora stanno **in cima all'installazione**, dove anche il
  codice vecchio li vede: `/opt/dmd/aerei.csv` e `/opt/dmd/aeroporti.csv`.
- Anche la scelta delle **cartelle** e' ora dichiarata dall'archivio, come
  gia' avveniva per i file: la prossima cartella nuova non ripetera' la
  storia. L'elenco cablato resta come rete di sicurezza per un archivio
  senza manifest.
- Una tabella **vuota** in `/var/lib/dmd` viene ricreata dal modello. Non c'e'
  niente da salvare in un file senza nemmeno una riga valida, e lasciarlo li'
  avrebbe significato non tradurre piu' nulla per sempre. Una tabella con
  anche una sola voce dell'utente non viene toccata, come prima.

## [1.11.1]

### Modificato
- **Air Radar disegnato su tre fasce**: identificativo in alto, rotta al
  centro, dettagli in basso. Fra il numero di volo e la riga dei dettagli
  restava una banda vuota di una ventina di pixel, mentre in basso i nomi
  lunghi delle rotte facevano scartare modello e quota per far entrare la
  riga. Ora ci stanno tutti e cinque i campi.
- Se la rotta tradotta e' comunque piu' larga del pannello si tornano a
  mostrare i codici IATA, che ci stanno sempre: meglio un'informazione
  completa e stringata che una tagliata a meta'.
- Senza rotta il disegno resta a due fasce, come prima.
- Nuovo colore facoltativo per la rotta. Lasciato vuoto segue quello dei
  dettagli: chi non tocca nulla non vede cambiare niente.
- Le posizioni delle tre fasce si ricavano dall'altezza del pannello, non da
  numeri fissi.

## [1.11]

### Aggiunto
- **Conversioni dei codici del radar.** Due file CSV modificabili traducono
  le sigle in nomi leggibili: `/var/lib/dmd/aerei.csv` (designatori ICAO dei
  tipi di aeromobile) e `/var/lib/dmd/aeroporti.csv` (codici **IATA** degli
  aeroporti — non ICAO: le rotte arrivano dal routeset di adsb.lol, che
  restituisce IATA, quindi una riga scritta `LIMC` non verrebbe mai usata).
  Distribuiti gia' pieni: 177 tipi e 326 scali.
- Ogni voce ha **due forme**, breve e completa. Il pannello e' largo 256 px e
  la riga del radar porta gia' rotta, quota, velocita' e distanza: `737-800`
  ci sta, `Boeing 737-800` no. Il nome esteso va nella web UI e nelle due
  colonne nuove del registro, `type_name` e `route_name`.
- **Elenco dei codici incontrati e non tradotti**, nella pagina Radar,
  ordinato per quante volte sono passati davvero: e' la lista di cosa
  conviene aggiungere per primo invece di doverlo indovinare. Un pulsante li
  aggiunge in coda al file come righe da completare.
- Le tabelle si modificano **dalla pagina Radar**, con indicazione della riga
  quando qualcosa non va, oppure a mano: una modifica fatta via SSH o SMB
  viene raccolta senza riavviare il servizio.

### Note di progetto
- I file vivono in `/var/lib/dmd` e **non vengono mai sovrascritti dagli
  aggiornamenti**. `/opt/dmd` viene riscritto a ogni installazione: tenerli
  li' avrebbe fatto sparire le aggiunte a mano al primo aggiornamento via
  rete, senza che l'utente se ne accorgesse. Al primo avvio si creano da un
  modello contenuto nel pacchetto.
- Il formato e' CSV e non XML di proposito: una riga sbagliata si perde da
  sola, mentre in un XML un tag non chiuso porta via l'intero file.
- Il registro dei passaggi con l'intestazione vecchia viene messo da parte
  con la data nel nome invece di ricevere righe con un numero di colonne
  diverso, che sarebbero disallineate e illeggibili.

## [1.10.7]

### Modificato
- L'applicazione si chiama **kWGillo DMD Server**. Cambia il titolo
  nell'intestazione della web UI, la riga di avvio nel log e il nome
  predefinito del dispositivo in Home Assistant. Chi ha gia' una
  configurazione salvata tiene il nome che aveva: in Home Assistant
  l'identita' sta in `node_id`, quindi anche cambiandolo a mano non nasce un
  dispositivo nuovo.
- Il menu parte dall'**Orologio** e finisce con le **Impostazioni**. La
  pagina di ingresso resta quella delle impostazioni.

## [1.10.6]

### Corretto
- **La pausa dal telefono non veniva vista.** Mettendo in pausa, il pannello
  continuava a mostrare "in riproduzione" e a far avanzare il tempo di un
  brano fermo; una decina di secondi dopo faceva sparire tutto. Da una
  cattura del traffico reale risulta che l'unico avviso e' il codice grezzo
  `shairport/ssnc/paus`, che arriva nell'istante esatto della pausa: non
  veniva ascoltato. Lo stato leggibile `shairport/playing` resta invece a
  "1" fino alla chiusura della sessione, quindi aspettare quello significava
  mentire per dieci secondi. Ora si ascoltano entrambi.
- **La fine della sessione cancellava il brano di colpo.** `play_end` faceva
  piazza pulita: ecco perche' dopo la pausa il player spariva da solo. Ora
  la sessione che si chiude mette in pausa, e il brano resta fermo a schermo
  per la finestra di permanenza prima di lasciare il posto.

### Modificato
- **Il fondo di sicurezza era tarato male.** La stessa cattura mostra
  ventuno secondi di riproduzione normale senza un solo messaggio: il limite
  di venti secondi entro cui l'orologio poteva avanzare senza conferme
  avrebbe prodotto pause finte a meta' di ogni brano. Ora e' di dieci
  minuti, e serve solo per sorgenti che non annunciano la pausa affatto.
  Regolabile con `nowplaying.advance_timeout`.
- **Le sottoscrizioni non prendono piu' l'intero ramo.** Con `publish_raw`
  attivo, `shairport/#` porta anche le copertine: centinaia di kilobyte di
  JPEG per ogni brano, che attraversavano broker e rete per essere poi
  buttati. Ora si chiede il solo livello leggibile piu' i due codici grezzi
  che servono, `prgr` e `paus`.

### Note
Il test `test_pausa.py` riproduce la sessione catturata topic per topic —
avvio, silenzio, pausa, chiusura, ripresa — e verifica lo stato del pannello
a ogni passaggio. Sarebbe bastato a intercettare tutti e tre i difetti.

## [1.10.5]

### Corretto
- **shairport-sync non partiva quando il broker ha una password.** Lo script
  scriveva `/etc/shairport-sync.conf` a `640 root:root` per non lasciare la
  password leggibile da chiunque, ma il demone gira come utente
  `shairport-sync` e cosi' non riusciva ad aprirlo. L'errore che ne usciva —
  *"Error reading configuration file: file I/O error"* — non nomina i
  permessi e manda a cercare tutt'altro. Ora il file passa al gruppo
  dichiarato dall'unita' di servizio, e lo script **verifica davvero** che
  quell'utente riesca a leggerlo, provandoci; se non ci riesce allenta i
  permessi e lo dice, perche' un file leggibile con un avviso e' meglio di un
  servizio morto in silenzio.
- **`systemctl reset-failed` prima di ogni riavvio.** Dopo qualche tentativo
  fallito systemd blocca il servizio con *"start request repeated too
  quickly"* e da quel momento rifiuta di riavviarlo anche a causa corretta:
  si corregge il problema vero e sembra che la correzione non abbia
  funzionato.

### Modificato
- Se shairport-sync non parte, lo script stampa le ultime righe del suo
  journal. Era l'unico posto dove si leggeva il motivo, e costava un altro
  giro di comandi.
- Il messaggio sul confinamento ai core non dice piu' "sarebbe
  controproducente" quando i core contati sono meno di quattro: con
  `isolcpus` il core riservato non viene contato e non e' comunque
  raggiungibile, quindi il lavoro e' gia' fatto.

## [1.10.4]

### Corretto
- **La compilazione riuscita veniva scambiata per fallita.** Lo script
  verificava il binario cercando `AirPlay-2` nella stringa di versione, ma
  shairport-sync scrive `AirPlay2` attaccato. Risultato: `configure`, `make`
  e `make install` andavano a buon fine, e lo script si fermava un attimo
  dopo dicendo che mancava AirPlay 2. Ora la stringa viene normalizzata
  prima del confronto, quindi vanno bene tutte le grafie.
- Il primo tentativo di normalizzazione aveva a sua volta un difetto:
  `tr -d ' -_'` interpreta l'argomento come **intervallo** da spazio a
  underscore, cifre comprese, e "airplay2" diventava "airplay". Il trattino
  ora sta in fondo all'insieme, dove tr lo tratta come carattere.

### Modificato
- Se il controllo del binario fallisce, lo script stampa la stringa di
  versione che ha letto e l'elenco dei binari trovati. Senza quel dato non
  si distingue una compilazione incompleta da un confronto sbagliato — ed
  era un confronto sbagliato.
- La guida avverte della differenza di grafia fra le versioni.

## [1.10.3]

### Aggiunto
- **Verifica delle dipendenze prima di compilare.** Lo script controlla in due
  secondi, con `pkg-config` e `command -v`, tutto quello che il `configure` di
  shairport-sync andra' a cercare, e se manca qualcosa lo elenca con accanto
  il nome del pacchetto da installare. Prima ogni dipendenza mancante si
  scopriva a compilazione avviata, una per volta, e ogni giro era un altro
  tentativo da capo.

### Corretto
- Manca(va) **`systemd-dev`**: `configure` interroga pkg-config sul pacchetto
  systemd per sapere dove installare l'unita' di servizio, e su Debian recenti
  quel file e' in un pacchetto separato. Su quelle precedenti sta in
  `libsystemd-dev`, quindi si tentano entrambi senza pretendere che esistano
  tutti e due.
- Aggiunto anche `libswresample-dev`, che le versioni recenti di
  shairport-sync cercano per AirPlay 2.

## [1.10.2]

### Corretto
- **`setup_nowplaying.sh`: mancava `libplist-utils`.** Il `configure` di
  shairport-sync per AirPlay 2 cerca il programma `plistutil` e si ferma se
  non lo trova: *"plistutil can not be found. Please install plistutil for
  building for AirPlay 2."* L'elenco delle dipendenze ora coincide con quello
  del BUILD.md ufficiale, con in piu' `pkg-config` e `libmosquitto-dev` che
  servono a noi.
- **Flag di systemd sbagliato**: era `--with-systemd`, ma nella versione
  attuale si chiama `--with-systemd-startup`. Autoconf un flag sconosciuto lo
  segnala solo come avviso, quindi la compilazione sarebbe riuscita e
  l'errore sarebbe saltato fuori dopo, con l'unita' di servizio assente.

### Modificato
- Quando un passo fallisce, lo script **stampa la riga del registro che
  spiega il motivo** invece di limitarsi a dire dove trovarla. Citare un file
  di log senza mostrarlo costringe a un secondo giro di comandi proprio
  quando si e' gia' fermi.
- `nqptp` non viene ricompilato se e' gia' installato e attivo: dopo un
  errore si rilancia lo script, e non ha senso rifare ogni volta una
  compilazione riuscita.
- La guida riporta i due dettagli corretti, con la spiegazione del perche'
  sbagliarli costa tempo.

## [1.10.1]

### Corretto
- **`setup_nowplaying.sh` non arrivava sul Raspberry.** Nella 1.10 restava
  solo dentro il pacchetto scompattato, escluso da `/opt/dmd` per analogia
  con `setup_share.sh`. Ma l'analogia era sbagliata: `setup_share.sh` lo
  chiamano `install.sh` e `update.sh`, quindi e' sempre presente quando
  serve, mentre `setup_nowplaying.sh` lo lancia l'utente — e dopo un
  aggiornamento via rete non esiste nessuna cartella scompattata in cui
  cercarlo. Ora viene installato con il resto ed e' in `/opt/dmd`.

### Modificato
- La documentazione indica `sudo /opt/dmd/setup_nowplaying.sh` invece del
  percorso relativo.
- La pagina Musica suggerisce il comando finche' il broker non e'
  configurato, invece di lasciar compilare le caselle a mano.
- Lo script e' elencato anche in `PAYLOAD_FILES`, cosi' arriva anche a chi
  aggiorna da una versione il cui manifest non lo prevedeva.

## [1.10]

### Aggiunto
- **Now Playing**: il pannello mostra titolo, artista, album, stato e
  avanzamento del brano in ascolto. Nuova pagina **Musica** nella web UI e
  nuovo servizio attivabile dalla pagina Servizi.
- **Ingresso AirPlay 2** tramite `shairport-sync`: il Raspberry si presenta in
  rete come una cassa AirPlay, scarta l'audio e tiene i metadati. Al ricevitore
  non importa quale applicazione stia suonando, quindi Apple Music, Spotify,
  Amazon Music e YouTube funzionano tutte senza configurazioni per ciascuna.
- **Ingresso Spotify** tramite l'API web, per la musica che non passa da
  AirPlay: Spotify Connect verso casse vere, computer, Echo. Autenticazione
  OAuth con PKCE, senza segreto dell'applicazione.
- **Ingresso MQTT libero**: qualsiasi cosa può pubblicare un JSON con titolo,
  artista, album, durata, posizione e stato. Sono accettati anche i nomi usati
  da Home Assistant. Serve a coprire un HomePod avviato a voce o un Echo.
- **Entità in Home Assistant** via MQTT Discovery: sensore del brano corrente,
  un interruttore per ogni servizio e la luminosità come `number`, tutti
  comandabili. Disponibilità legata al testamento MQTT.
- `mqttbus.py`, `nowplaying.py`, `spotifyapi.py`, `hass.py`,
  `sources/nowplaying.py`, `templates/nowplaying.html`.
- **`setup_nowplaying.sh`**: prepara il sistema da solo — Mosquitto,
  dipendenze, `nqptp`, `shairport-sync` compilato con AirPlay 2 e metadati,
  scheda audio fittizia, configurazione e confinamento ai core 0-2. La guida
  richiedeva 132 righe di comandi digitati a mano, di cui i dieci flag di
  `./configure` e le venti righe di `shairport-sync.conf` erano anche le più
  fragili: un refuso lì non dà errore, dà un sistema che non funziona senza
  dire perché. Sta a parte da `install.sh` come `setup_share.sh`, perché è
  facoltativo e la compilazione porta via un quarto d'ora. È ripetibile,
  salta i passi già fatti, riconosce il pacchetto della distribuzione che
  altrimenti si sovrapporrebbe alla compilazione, e in chiusura resta in
  ascolto del broker per dire se i metadati arrivano davvero.
- Il DMD si ridichiara a Home Assistant quando questa riparta: HA pubblica
  `online` su `homeassistant/status` e il DMD è iscritto a quel topic. Con un
  ritardo casuale, come raccomanda la loro documentazione, per non sommare la
  propria risposta a quella di tutti gli altri dispositivi della casa. Due
  pulsanti nella pagina Musica per ridichiarare e per rimuovere le entità.
- Guida completa in `docs/now-playing.it.md` (e PDF).

### Modificato
- La **password del broker MQTT** viene tolta da ogni configurazione
  esportata, senza opzione. Un file di configurazione gira: finisce in un
  backup, in un allegato, in una segnalazione.
- Nuova priorità nell'arbitro: Now Playing sta a **58**, sopra Rolling Banner
  e Media Player, sotto Air Radar e ZeDMD. Mentre suona musica il player resta
  a schermo al posto delle foto, ma un aereo di passaggio può interromperlo e
  durante una partita comanda il flipper.
- `install.sh` e `update.sh` installano `python3-paho-mqtt`.
- Il manuale completo ha una nuova sezione 12, fra Batocera e Aggiornamenti,
  che rimanda allo script e al documento dedicato. Le sezioni successive
  scalano di uno. Il rimando dentro `verify.sh` puntava alla sezione
  sbagliata già da prima: corretto.

### Corretto
- Il ponte verso Home Assistant dichiarava le entità solo *alla* connessione
  MQTT. Se il bus era già connesso quando il ponte partiva, quell'evento era
  passato e non sarebbe tornato: Home Assistant non vedeva mai il
  dispositivo. Capitava di più proprio con il broker predefinito, quello
  locale, perché è il più veloce a connettersi.
- Salvare le impostazioni MQTT ricostruiva il bus azzerando le sottoscrizioni,
  ma `hass.start()` usciva subito perché il thread era già in corsa e non le
  rimetteva: da quel momento gli interruttori di Home Assistant smettevano di
  rispondere fino al riavvio del servizio.

### Perché il player si disegna così
Il testo del player si compone **senza antialiasing** e, di serie, con soli
colori pieni. Non è una scelta estetica: PIL sfuma i bordi delle lettere, e
ogni sfumatura è un pixel a intensità intermedia — esattamente ciò che su un
pannello S-PWM a refresh basso produce lo sfarfallio, mentre i colori saturi
restano fermi. La maschera del testo viene quindi ridotta a due soli livelli,
e con `safe_colors` ogni componente va a 0 o 255.

Per la stessa ragione **non c'è la copertina dell'album**: a 64 pixel sarebbe
illeggibile, ed essendo fatta quasi solo di mezzi toni significherebbe tenere
in permanenza sullo schermo il contenuto peggiore possibile per questo
pannello.

Il font a larghezza fissa della riga dei tempi è quello di Liberation e non
quello di DejaVu: ridotto a due livelli a quella dimensione, il monospace di
DejaVu disegna la cifra `1` come una parentesi quadra e `13:31` si legge
`]3:3]`.

### Note tecniche
- La posizione nel brano non arriva di continuo: AirPlay manda `prgr` al
  cambio di traccia e dopo un salto, Spotify risponde solo quando lo si
  interroga. Fra un aggiornamento e l'altro il tempo lo conta il DMD, con
  `time.monotonic()` e non con l'orologio di sistema — una correzione NTP non
  deve far saltare la barra di avanzamento.
- L'audio di `shairport-sync` va indirizzato alla scheda fittizia del kernel
  (`snd_dummy`) e **non** a `/dev/null` né al plugin `null` di ALSA: quelli
  non limitano il ritmo e farebbero perdere il riferimento temporale, che in
  un gruppo multi-room fa singhiozzare tutte le casse, non solo quella finta.
- `paho-mqtt` è una dipendenza facoltativa: se manca, la pagina Musica lo dice
  e il servizio resta spento, senza impedire l'avvio del resto.
- I token di Spotify vivono in `/var/lib/dmd/spotify.json` con permessi
  `0600`, fuori dalla configurazione.

## [1.9.4]

### Aggiunto
- Due campi nella **regolazione fine del pannello**, entrambi già presenti
  nella libreria ma non esposti finora:
  - **Durata bit minimo (ns)** — `pwm_lsb_nanoseconds`, predefinito 130.
    Accorcia ogni sotto-frame, quindi accorcia il frame intero: a 100 ns si
    guadagna circa un terzo di refresh. Sotto gli 80 ns gli impulsi più brevi
    diventano troppo corti perché il pannello li renda con precisione, e i
    toni scuri sbagliano.
  - **Bit con dithering** — `pwm_dither_bits`, predefinito 0. Rende i bit più
    bassi alternandoli nel tempo invece che con la durata di accensione: 1 bit
    raddoppia il refresh a parità di profondità dichiarata, al prezzo di un
    lieve brulichio sulle sfumature più fini.

### Perché
Su un pannello S-PWM le immagini con mezzi toni tremolavano mentre i colori
pieni restavano fermi: un pixel a intensità intermedia viene acceso e spento a
ciclo, e se il refresh reale è basso l'occhio lo segue. L'unico rimedio
disponibile era abbassare la profondità PWM da 11 a 10 bit — che dimezza il
tempo di frame e quindi raddoppia il refresh, ma costa metà delle sfumature.
Queste due leve ottengono lo stesso guadagno di refresh **tenendo** la
profondità.

I valori predefiniti coincidono con quelli della libreria: chi non li tocca non
vede alcun cambiamento.

## [1.9.3]

### Modificato
- Il riquadro **Ora e sincronizzazione** si sposta dalla pagina Impostazioni a
  quella dell'Orologio, sotto le impostazioni di aspetto. Formato dell'ora,
  colori, lingua dei giorni, fuso orario e server NTP sono aspetti della stessa
  cosa e si regolano nello stesso posto. Dopo il salvataggio si torna alla
  pagina Orologio.

## [1.9.2]

### Corretto
- Il controllo della libreria falliva con `fatal: detected dubious ownership in
  repository`. Il servizio gira come `root` — necessario per i GPIO — mentre la
  libreria sta nella home dell'utente, e dalla versione 2.35.2 git rifiuta i
  repository di un altro proprietario. Ora l'eccezione viene passata alla
  singola invocazione con `-c safe.directory=<percorso>`, senza modificare la
  configurazione globale del sistema.

## [1.9.1]

### Corretto
- **L'aggiornamento via rete non installava i file nuovi.** L'elenco dei file
  da copiare (`PAYLOAD_FILES`) è cablato nel codice, quindi appartiene alla
  versione *già installata*: un file introdotto da una versione successiva non
  poteva comparirvi. Aggiornando dalla 1.8 alla 1.9, `libcheck.py` non è stato
  copiato e il nuovo `dmdd.py` è morto su `ModuleNotFoundError` con il display
  spento. Ora l'elenco si legge da `manifest-install.md5`, che l'archivio
  scaricato porta con sé: è la versione nuova a dichiarare cosa contiene.
- Controllo dei file mancanti **prima** del riavvio del servizio: un'anomalia
  viene intercettata mentre il sistema è ancora in piedi, non dopo.
- Il ripristino della copia di sicurezza scatta anche quando a fallire è la
  copia dei file, non solo l'avvio del servizio. Prima, un errore a metà
  installazione lasciava `/opt/dmd` con un misto di vecchio e nuovo.

### Nota per chi aggiorna dalla 1.9
La correzione riguarda il codice che *esegue* l'aggiornamento, quindi ha
effetto dal passaggio successivo. Se il servizio non riparte dopo un
aggiornamento e il log riporta `ModuleNotFoundError`, il file mancante si
recupera così:

    sudo curl -fsSL https://raw.githubusercontent.com/kWGillo/zedmd-pi/main/<file>.py -o /opt/dmd/<file>.py
    sudo systemctl restart dmd

## [1.9]

### Aggiunto
- **Rolling banner**, nuovo servizio con pagina propria. Fino a dieci testi
  scorrevoli, ciascuno con testo, colore, dimensione (piccola/media/grande),
  velocità in pixel al secondo e lampeggio indipendenti. Compaiono a intervalli
  casuali come i contenuti del Media Player: il testo entra da destra,
  attraversa il pannello ed esce a sinistra, poi il display torna a chi lo
  aveva. Ordine sequenziale o casuale, e un pulsante di anteprima immediata.
- **Controllo aggiornamenti della libreria della matrice.** Il fork
  `kingdo9/rpi-rgb-led-matrix_pwm_experiment` non usa numeri di versione, si
  aggiorna a commit: il confronto è fra il commit installato in locale, letto
  con git, e quello in cima al ramo remoto, letto dall'API di GitHub. La scheda
  mostra entrambi, l'oggetto del commit remoto e il collegamento a `spwm.md`.

### Scelte di progetto
- Il banner sta a priorità **55**: sopra il Media Player (50), sotto Air Radar
  (60) e ZeDMD (100). Un testo scorre una volta sola e dura pochi secondi,
  mentre una foto può restare a schermo a lungo: sotto al Media Player non
  comparirebbe quasi mai. Sopra a ZeDMD interromperebbe le partite.
- L'aggiornamento della libreria **non è automatico, di proposito**.
  Ricompilarla e reinstallare i binding richiede una decina di minuti su una Pi
  Zero 2 W, con il pannello fermo, e può cambiare il comportamento di una
  taratura funzionante. La pagina mostra i comandi da dare a mano, nell'ordine.
- La cartella della libreria viene dedotta da `panel.profile_dir`, che ne è una
  sottocartella: nessuna configurazione in più da compilare. Resta la chiave
  `panel.library_dir` per i casi fuori standard.

## [1.8]

### Aggiunto
- **Esportazione della configurazione** dalla pagina Impostazioni: un file
  JSON con tutta la taratura del pannello, i colori, le fasce orarie e le
  impostazioni dei servizi. Il nome contiene hostname, versione e data.
- Casella **Includi le coordinate del radar**: togliendola, il file esportato
  ha la posizione azzerata e si può allegare a una segnalazione o passare a
  qualcun altro senza portarsi dietro l'indirizzo di casa.
- **Importazione** dallo stesso riquadro. Il file viene fatto passare dalle
  stesse migrazioni del caricamento normale, quindi va bene anche se salvato
  da una versione precedente; le chiavi sconosciute vengono ignorate. La
  configurazione in uso viene copiata in `/var/lib/dmd/` prima di essere
  sostituita, e il servizio si riavvia perché le impostazioni del pannello si
  applicano solo alla creazione della matrice.

### Perché
Una scheda SD guasta ha reso irraggiungibile l'unica copia di una taratura
trovata per tentativi in più giorni. Il codice era al sicuro su GitHub, la
configurazione no.

### Nota tecnica
L'importazione aggiorna i dizionari **in luogo** invece di sostituirli: le
sorgenti tengono un riferimento a `cfg` e ai suoi rami, e rimpiazzare
l'oggetto lascerebbe metà del programma a leggere quello vecchio.

## [1.7.2]

### Aggiunto
- **Impronte md5 di tutti i file** (`manifest.md5`, `manifest-install.md5`) e
  script `verify.sh`. `install.sh` e `update.sh` verificano il pacchetto prima
  di toccare l'installazione funzionante, e i file copiati prima di riavviare
  il servizio. Un file arrivato corrotto viene riconosciuto per nome, con
  l'avviso esplicito quando contiene byte nulli.
- L'aggiornamento via rete confronta le impronte oltre a compilare il Python:
  un template o un foglio di stile corrotto non è codice Python e passava
  inosservato.

### Perché
Su una scheda SD in sofferenza un file era arrivato della lunghezza esatta ma
con duemila byte nulli al centro. Nessun passaggio aveva segnalato niente:
`scp` contento, `tar` contento, `cp` contento, `md5` identico fra origine e
destinazione — perché a corrompersi era stata l'origine. Il servizio non
partiva e l'unico indizio era `ValueError: source code string cannot contain
null bytes`. Ora il guasto viene nominato al primo passaggio utile.

## [1.7.1]

### Corretto
- Un errore dell'interfaccia web non ferma più il servizio. Prima l'avvio della
  web UI stava fuori da qualsiasi protezione: una sua eccezione faceva uscire
  l'intero processo e con esso spegneva il pannello, lasciando systemd a
  riavviare all'infinito senza che il motivo comparisse da nessuna parte. Ora
  il pannello si accende comunque e il traceback finisce nel log.
- `current_language()` non interroga più `request` fuori da una richiesta HTTP.

## [1.7]

### Aggiunto
- **Interfaccia web in italiano e inglese.** La lingua viene rilevata dal
  browser (`Accept-Language`) alla prima apertura; un selettore in alto a
  destra la cambia in qualsiasi momento e la scelta viene salvata. Riportando
  il selettore su *predefinito* si torna a seguire il browser.
- Link al repository del progetto nel piede di ogni pagina e nella sezione
  Aggiornamenti.
- Modulo `i18n.py`: dizionario a due lingue, senza gettext e senza dipendenze
  da installare.

### Modificato
- Le righe di stato dei servizi seguono la lingua dell'interfaccia. I messaggi
  di `journalctl` restano in italiano: sono per chi legge i log, non per
  l'interfaccia.
- La lingua dei nomi dei giorni sul pannello resta un'impostazione separata,
  nella pagina Orologio: chi guarda il cabinato non è necessariamente chi
  configura il sistema.

## [1.6]

### Modificato
- L'elenco della libreria media viene tenuto in memoria per cinque minuti
  invece di essere riletto dal disco a ogni cambio di contenuto e a ogni
  richiesta della web UI. Con una raccolta Pixelcade completa — decine di
  migliaia di file — quella scansione continua occupava CPU e scheda SD, e sul
  pannello si vedeva come righe bianche orizzontali.
- `status()` del Media Player non fa più accessi al disco: riporta solo il
  numero di file già noto.

### Aggiunto
- Pulsante **Rileggi la libreria** nella pagina Media, per i file copiati
  dalla condivisione di rete senza passare dall'upload.
- Manuale di installazione riscritto sull'installazione da GitHub, con una
  sezione dedicata a righe bianche, blocchi ed errori di I/O.

## [1.5.2]

### Corretto
- Le rotte dei voli arrivano dal servizio `routeset` di adsb.lol: una sola
  richiesta per tutti i voli visibili, con codici IATA quando disponibili.
  hexdb.io resta come ripiego. Prima la rotta non compariva quasi mai.

### Aggiunto
- Prova diagnostica di una singola rotta nella pagina Radar.

### Modificato
- Nella pagina Media il caricamento dei file e l'anteprima immediata sono in
  due riquadri distinti.

## [1.5.1]

### Corretto
- La rotta veniva cercata solo se era attiva una seconda casella, che
  duplicava il campo *Rotta* nell'elenco dei parametri. La casella è stata
  rimossa.
- Ricerca su hexdb.io più robusta, con memoria anche degli esiti negativi.

## [1.5]

### Aggiunto
- **Aggiornamento via rete** dal repository GitHub. L'archivio viene scaricato
  in una cartella temporanea, verificato (file attesi presenti, tutto il Python
  compila) e solo allora installato, dopo una copia di sicurezza. Se il
  servizio non risponde al riavvio, la copia viene ripristinata da sola.
- Pagina Impostazioni: stato dell'aggiornamento, repository e ramo, controllo
  automatico e registro delle operazioni.

## [1.4]

### Aggiunto
- Air Radar: scelta dei parametri di volo da mostrare sul pannello.
- Registro CSV di tutti i passaggi, scaricabile dalla web UI, con possibilità
  di svuotarlo.

## [1.3.1]

### Corretto
- Nessuna coordinata preimpostata nel codice: la posizione resta soltanto
  nella configurazione locale e non entra mai nel pacchetto distribuito.

## [1.3]

### Aggiunto
- Servizio **Air Radar**: aerei in transito entro un raggio da una coordinata
  GPS, tramite le API pubbliche ADS-B della comunità (adsb.fi, adsb.one,
  adsb.lol), senza chiavi di accesso.
- Priorità 60: sta sopra a Media Player e orologio, sotto a ZeDMD.

## [1.2]

### Aggiunto
- Regolazioni fini del driver S-PWM dalla web UI
  (`SPWM_END_OF_FRAME_EXTRA_ROW_CYCLES`, `SPWM_FRAME_END_SLEEP_US`,
  `limit_refresh`, `pwm_bits`), per intervenire sui lampi orizzontali.
- Riavvio del servizio dall'interfaccia web.

## [1.1.1]

### Corretto
- `update.sh` verifica e installa ffmpeg e Samba in modo indipendente: su un
  sistema con ffmpeg già presente ma senza Samba la condivisione di rete non
  veniva creata.

## [1.1]

### Aggiunto
- Colori indipendenti per ora e data, con anteprima nella web UI.
- Formato 12 o 24 ore, con indicatore AM/PM.
- Nomi dei giorni in italiano, francese o inglese.
- Servizio **Media Player**, separato dall'orologio: foto e video estratti a
  caso da una libreria, a intervalli casuali configurabili.
- Libreria media condivisa via SMB e caricabile dalla web UI.
- Supporto al materiale Pixelcade, utilizzabile anche senza Batocera.
- **Night mode** (luminosità ridotta) e **Sleep mode** (display spento) su
  fasce orarie, con Sleep prioritario e risveglio opzionale sui frame ZeDMD.
- Numero di versione mostrato nella web UI e in `/api/status`.

### Modificato
- Il servizio `mediaplayer_clock` è stato diviso in `clock` e `mediaplayer`.
  La configurazione esistente viene migrata automaticamente.
- Ciclo di rendering a 30 fps invece di 60, per lasciare CPU al ricevitore.

## [1.0.2]

### Corretto
- Rilevamento del client sparito: dopo uno spegnimento brusco di Batocera la
  connessione TCP restava aperta e il display non tornava mai all'orologio.
  Ora un silenzio prolungato viene trattato come disconnessione.

## [1.0.1]

### Corretto
- L'handshake ZeDMD è servito da un socket server dedicato che scrive header e
  corpo in un'unica operazione. Con Flask il client leggeva un corpo vuoto, non
  riconosceva il trasporto TCP e ripiegava su UDP.
- Aggiunto l'ascolto UDP come rete di sicurezza.
- Ridotte le copie di memoria nel percorso di ricezione dei frame.

### Modificato
- La web UI si sposta sulla porta 8080; la porta 80 redirige.

## [1.0]

### Aggiunto
- Ricevitore del protocollo ZeDMD-WiFi.
- Orologio come contenuto di riserva.
- Interfaccia web: luminosità, NTP, fuso orario, gestione dei servizi.
- Arbitro con priorità, prelazione e tempo di grazia.
