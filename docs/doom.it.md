# Doom sul DMD — preparazione e attivazione

Guida rapida per la versione **3.2** del kWGillo DMD Server. Copre solo
Doom: preparazione, accensione, comandi e taratura. Per tutto il resto vale il
manuale completo.

---

## In breve

Tre passi, una volta sola. Il primo è facoltativo.

1. *(facoltativo)* Copia il **tuo WAD** nella cartella condivisa
   `\\<ip-del-pi>\dmd-doom`, se hai comprato Doom.
2. Apri la pagina **Doom** della web UI e premi **Prepara Doom**. Un paio di
   minuti.
3. Nella stessa pagina scegli il **WAD** da usare.

Da quel momento si gioca premendo **Gioca**. Non c'è nessun servizio da
accendere: Doom non gira in sottofondo.

---

## 1. Cosa serve

| | |
|---|---|
| **Versione** | DMD Server 3.2 o successiva |
| **Rete** | serve alla preparazione: scarica i sorgenti di Doom e, se non hai un WAD tuo, Freedoom (~55 MB) |
| **Spazio** | circa 150 MB fra `/var/lib/dmd/doom` e `/srv/dmd/doom` |
| **Tempo** | un paio di minuti di compilazione su un Raspberry 3B+ |
| **Tastiera** | facoltativa: una tastiera USB nel Raspberry è il modo più diretto di giocare |
| **WAD** | facoltativo: il tuo, se hai comprato Doom. Altrimenti si usa Freedoom, che è libero |

Non serve nessun collegamento nuovo: **i GPIO non si toccano**. I comandi
passano dalla tastiera USB e dalla pagina web.

---

## 2. (Facoltativo) Il tuo WAD, prima di tutto il resto

Il WAD è il file che contiene livelli, grafica e suoni. Il programma è una
cosa, il WAD è un'altra.

Il pacchetto scarica **Freedoom**, che è libero e si può ridistribuire. I WAD
di id Software no: chi ha comprato Doom usa il proprio.

I WAD hanno una **cartella condivisa in rete** tutta loro, accanto a quella
dei media:

| | |
|---|---|
| Dal tuo computer | `\\<ip-del-pi>\dmd-doom` |
| Sul Raspberry | `/srv/dmd/doom` |

Dentro ci sono solo i WAD. Il programma compilato e i salvataggi restano in
`/var/lib/dmd/doom`, dove non si possono cancellare per sbaglio.

Copia il tuo WAD lì **prima** di premere il pulsante, con uno di questi nomi:

```
doom.wad        Ultimate Doom
doom2.wad       Doom II
plutonia.wad    Final Doom: Plutonia
tnt.wad         Final Doom: TNT
doom1.wad       Doom shareware
```

Se ne trova uno, la preparazione **non scarica Freedoom** e la pagina ti
propone il tuo come predefinito. Se lo copi dopo, nessun problema: comparirà
comunque nell'elenco e potrai sceglierlo.

> **Se aggiorni dalla 3.0 o dalla 3.0.1**, i WAD stavano insieme al programma.
> La preparazione li sposta da sola nella cartella condivisa e la
> configurazione si riallinea: non devi fare niente.

> Il nome non basta e il DMD non si fida del nome. Un WAD si riconosce dai
> primi quattro byte del file: `IWAD` è un gioco completo, `PWAD` è
> un'estensione che da sola non parte. Un file scaricato a metà o rinominato
> per sbaglio viene scartato **dicendoti perché**, invece di far fermare Doom
> con un messaggio incomprensibile.

---

## 3. Prepara Doom

Apri la web UI del DMD e vai alla pagina **Doom** (nel menu, dopo Radar).
Nel riquadro **Preparazione** premi **Prepara Doom**.

Il pulsante fa tre cose:

- installa gli strumenti di compilazione, se mancano;
- scarica e compila **doomgeneric**, il motore di Doom;
- scarica **Freedoom**, a meno che non abbia trovato un WAD tuo.

La compilazione va in sottofondo e la pagina ne mostra il log mentre procede;
quando ha finito si aggiorna da sola. Su un Raspberry 3B+ ci vogliono circa
due minuti — è normale che per un po' sembri ferma.

Alla fine il log elenca i WAD trovati e dice quali sono utilizzabili:

```
==> Controllo dei WAD
    OK   doom1.wad  (5 MB)
    NO   appunti.wad: non e' un WAD
    NO   mod.wad: e' un'estensione, non un gioco completo

Fatto: 1 WAD utilizzabili.
```

**Dalla riga di comando**, se preferisci, lo stesso lavoro si fa con:

```
sudo /opt/dmd/doom/setup_doom.sh
```

Le due strade sono equivalenti: il pulsante lancia esattamente questo script.

> **Perché non è già pronto nel pacchetto.** I sorgenti di Doom sono sotto
> licenza GPL versione 2, questo progetto è GPLv3, e le due non si possono
> mescolare in un unico programma. Per questo Doom gira come **processo
> separato** che parla con il DMD attraverso una pipe — due programmi che si
> parlano non si "collegano" — e i suoi sorgenti si scaricano al momento
> invece di essere inclusi. È anche una comodità: se Doom cade, cade lui, e il
> pannello torna all'orologio.

---

## 4. Scegli il WAD

Nel riquadro **WAD trovati** compaiono tutti i file `.wad` della cartella, con
dimensione ed esito del controllo. Seleziona quello che vuoi usare e premi
**Usa questo**.

Quelli scartati restano visibili, con il motivo accanto: serve a capire cosa
correggere, non a nasconderlo.

---

## 5. Come funziona

**Doom non è un servizio: è una partita.** Non gira in sottofondo, non compare
fra gli interruttori, e finché non premi «Gioca» sul Raspberry non c'è nessun
processo di Doom in esecuzione.

### Quando premi «Gioca»

Tutti i servizi si fermano e il pannello diventa suo — **Batocera compreso** —
finché non esci o finché non lo lasci fermo abbastanza a lungo. Non è una
questione di priorità: è una *presa*, lo stesso meccanismo della Gestione
media, e non si discute.

La partita comincia avviando Doom direttamente dentro il livello. Ci vuole un
secondo di nero: è normale. È il modo affidabile di entrare in gioco, invece
di interrompere un demo e poi navigare il menu a colpi di frecce su un
pannello alto sessantaquattro pixel.

### Quando esci

Il processo si chiude e le sorgenti riprendono il loro giro senza essersi
accorte di niente: orologio, radar, banner, Media Player, Batocera.

> **Nelle versioni 3.0 e 3.1** c'era anche un *attract mode*: Doom che giocava
> da solo quando nessuno toccava niente. Non ha mai funzionato — prima non si
> vedeva mai perché Batocera non molla il pannello, poi restava a schermo dopo
> l'uscita da una partita, con il Media Player che spuntava ogni tanto. È
> stato tolto insieme ai due meccanismi che lo sostenevano.

### Come finisce

| | |
|---|---|
| **Esci dalla partita** | il pulsante nella pagina Doom, subito |
| **Inattività** | dopo 180 secondi senza comandi (modificabile) |

Finita la partita il processo si chiude e i servizi riprendono.

---

## 6. I comandi

Due strade, la stessa coda di tasti. Nessun GPIO.

### Tastiera collegata al Raspberry

È la via più diretta: non passa dalla rete. Va bene qualunque tastiera USB, e
viene riconosciuta da sola — l'elenco di quelle viste in questo momento è
scritto nella pagina Doom.

| Comando | Tasti |
|---|---|
| Avanti / indietro | ↑ ↓ oppure W S |
| Gira | ← → |
| Passo laterale | A D |
| Fuoco | Ctrl (destro o sinistro), Alt |
| Apri porte, usa interruttori | Spazio |
| Corri | Shift |
| Menu | Esc |
| Conferma | Invio |
| Mappa | Tab |
| Cambia arma | da 1 a 7 |

La tastiera **comanda** il gioco ma non lo fa *cominciare*: la partita si apre
da «Gioca». Se preferisci poterla cominciare premendo un tasto sul cabinato,
c'è la spunta *«Un tasto sulla tastiera può far cominciare una partita»* — è
spenta di proposito, perché il DMD sta in mezzo a un flipper e un tasto
sfiorato per caso non deve portarsi via il pannello a metà partita.

Se non vuoi che il DMD legga affatto la tastiera, togli la spunta a *«Leggi la
tastiera collegata al Raspberry»*.

### Pagina web

Nel riquadro **Comandi** ci sono i pulsanti. Si **tengono premuti**: tenendo
il dito su una freccia si cammina davvero, invece di fare un passo alla volta.

Funziona anche la **tastiera del computer** che sta guardando la pagina, con
gli stessi tasti della tabella qui sopra.

> Dal telefono c'è qualche decina di millisecondi di ritardo, che è la rete e
> non il DMD. Si gioca, ma per giocare bene la tastiera nel Raspberry è
> un'altra cosa.

---

## 7. Taratura dell'immagine

Doom disegna **320×200**, cioè 1,6:1. Il pannello è **256×64**, cioè 4:1.
Schiacciando il fotogramma intero su 64 righe un nemico diventa alto otto
pixel e non si distingue da un barile.

Quindi il fotogramma non si schiaccia: si **ritaglia una fascia** attorno
all'orizzonte e si butta via il resto. In Doom il pavimento e il soffitto sono
esattamente dove non succede niente, mentre i nemici stanno sulla linea dello
sguardo.

| Parametro | Predefinito | Cosa fa |
|---|---|---|
| **Prima riga della fascia** | 36 | dove comincia il ritaglio, contando dall'alto delle 200 righe di Doom |
| **Altezza della fascia** | 96 | quante righe prendere. Più alta = si vede più scena ma tutto è più schiacciato |
| **Gamma** | 0,70 | sotto 1 schiarisce. Doom è un gioco buio e un LED non ha il nero di un CRT |

Questi valori sono un punto di partenza ragionevole, non una verità: la
risposta vera si trova guardando **il tuo** pannello. Salvando, Doom riparte
da solo — fascia e gamma stanno nella riga di comando del programma, non in un
file che rilegge.

**Se vuoi provare a vedere tutto lo schermo**, non serve nessuna funzione
nuova: metti *prima riga* a **0** e *altezza* a **200**, e il ritaglio diventa
un riproporzionamento dell'intero fotogramma. Sappi però cosa aspettarti — la
compressione verticale è 2,5 volte quella orizzontale, quindi tutto diventa
basso e largo, e un terzo del pannello se ne va nella barra di stato. Una via
di mezzo utile è **0 per 168 righe**: tutta la scena senza la barra di stato.

E un numero che vale la pena conoscere: con la larghezza che passa da 320 a
256 il fattore è 0,8, quindi le proporzioni sono **esatte** con una fascia di
**80 righe** (0,8 × 80 = 64). Il valore predefinito, 96, schiaccia in verticale
del 17% — si vede più scena in cambio di una leggera deformazione. Più la
fascia è alta, più si vede e più si schiaccia.

---

## 8. Impostazioni della partita

| Parametro | Predefinito | Cosa fa |
|---|---|---|
| **Difficoltà** | 3 | da 1 a 5, la scala di Doom |
| **Livello iniziale** | `1 1` | episodio e mappa da cui parte una partita |
| **Fine partita dopo** | 180 s | secondi senza comandi prima che la partita si chiuda e i servizi riprendano. `0` = mai |

**Il suono è spento di proposito.** Sul cabinato l'audio è di Batocera, e un
secondo canale sonoro sarebbe soltanto rumore sopra al gioco vero.

I salvataggi e la configurazione di Doom finiscono in
`/var/lib/dmd/doom/stato`, fuori da `/opt/dmd`, che deve restare identico alle
proprie impronte per gli aggiornamenti.

---

## 9. Se qualcosa non va

| Sintomo | Causa probabile | Rimedio |
|---|---|---|
| Il log della preparazione resta vuoto | il servizio DMD non sta girando | `systemctl status dmd`, poi `journalctl -u dmd -n 50` |
| «non è un WAD» | file rinominato, o non è un WAD | usa un file che comincia per `IWAD` |
| «è un'estensione, non un gioco completo» | è un PWAD, cioè una modifica | serve un gioco completo: Freedoom o un WAD di id Software |
| «troppo piccolo, forse scaricato a metà» | scaricamento interrotto | ricopia il file e ricontrolla la dimensione |
| Doom non compare sul pannello | non hai premuto **Gioca** | Doom non gira in sottofondo: si vede solo durante una partita |
| Premo «Gioca» e non succede niente | il WAD o il programma non vanno | guarda l'avviso in cima alla pagina Doom, che dice quale dei due |
| Un secondo di nero entrando in partita | Doom sta ripartendo dentro il livello | è normale |
| La tastiera del Raspberry non risponde | l'opzione è spenta, o la tastiera non è vista | controlla la spunta e l'elenco dei dispositivi nella pagina Doom |
| Il pannello resta su Doom dopo che hai finito | la partita è ancora aperta | **Esci dalla partita**, oppure aspetta il tempo di inattività |
| «Il programma è stato compilato prima dell'ultimo aggiornamento» | un aggiornamento ha toccato il sorgente | premi **Ricompila** quando ti fa comodo |

Per guardare cosa succede davvero:

```
journalctl -u dmd -f | grep doom
```

---

## 10. Licenze, in due righe

- Il **DMD Server** è GPLv3.
- **doomgeneric** discende dai sorgenti di Doom, che sono GPL2. Per questo non
  sta nel repository, si scarica e si compila sul posto, e gira come processo
  separato: due programmi che si parlano da una pipe restano due programmi.
- **Freedoom** è libero (licenza BSD) e si può ridistribuire.
- I **WAD di id Software** non si possono ridistribuire. Se ne usi uno, è
  perché lo hai comprato tu.
