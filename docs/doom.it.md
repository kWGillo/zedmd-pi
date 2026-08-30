# Doom sul DMD — preparazione e attivazione

Guida rapida per la versione **3.1** del kWGillo DMD Server. Copre solo
Doom: preparazione, accensione, comandi e taratura. Per tutto il resto vale il
manuale completo.

---

## In breve

Quattro passi, una volta sola. Il primo è facoltativo.

1. *(facoltativo)* Copia il **tuo WAD** nella cartella condivisa
   `\\<ip-del-pi>\dmd-doom`, se hai comprato Doom.
2. Apri la pagina **Doom** della web UI e premi **Prepara Doom**. Un paio di
   minuti.
3. Nella stessa pagina scegli il **WAD** da usare.
4. Nella pagina **Servizi** accendi **Doom**.

Da quel momento, quando il cabinato è fermo, Doom gioca da solo sul pannello.
Al primo comando comincia una partita.

---

## 1. Cosa serve

| | |
|---|---|
| **Versione** | DMD Server 3.1 o successiva |
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

## 5. Accendi il servizio

Vai nella pagina **Servizi** e accendi **Doom**. È l'ultimo passo: da qui in
poi il programma parte da solo a ogni avvio del DMD.

---

## 6. Come funziona

### Quando nessuno tocca niente

Doom **gioca da solo**, mandando in onda i demo che ha sempre avuto dentro. Non
è un video registrato: è il motore che gioca.

In questo stato Doom è una sorgente a **priorità bassa**: cede il pannello a
un aereo del radar, a un promemoria di compleanno, al Media Player. Se stai
giocando a flipper, sul DMD c'è il flipper.

Con Batocera però c'è una regola in più, e senza di quella Doom non lo vedresti
mai. Finché Batocera è collegato il pannello è suo, ed è giusto: l'immagine del
tavolo selezionato deve restare ferma per minuti mentre scorri il menu. Ma
**passata la soglia** — un minuto, regolabile — un gioco che si muove vale più
di un fermo immagine, e Doom subentra. Al **primo fotogramma nuovo** da
Batocera il pannello torna suo all'istante.

Due cose che questa regola *non* fa, di proposito:

- non promuove Doom sopra chi ha davvero qualcosa da dire: se intanto passa un
  aereo, si vede l'aereo;
- non esiste se Doom è spento. Senza un riempitivo pronto, l'immagine del
  tavolo resta dov'è invece di lasciare il campo all'orologio.

La soglia si regola nella pagina Doom, alla voce *«Doom subentra a Batocera
fermo da»*. **Zero** disattiva la deroga: Doom in attract mode non prenderà mai
il posto di Batocera.

### Quando qualcuno preme un comando

Comincia una **partita**, e il pannello diventa suo — **Batocera compreso** —
finché non esci o finché non lo lasci fermo abbastanza a lungo.

La partita comincia facendo ripartire Doom direttamente dentro il livello.
Ci vuole un secondo di nero: è normale. È il modo affidabile di entrare in
gioco, invece di interrompere un demo e poi navigare il menu a colpi di frecce
su un pannello alto sessantaquattro pixel.

### Come finisce

| | |
|---|---|
| **Esci dalla partita** | il pulsante nella pagina Doom, subito |
| **Inattività** | dopo 180 secondi senza comandi (modificabile) |
| **Servizio spento** | dalla pagina Servizi |

Finita la partita Doom riparte e torna ai suoi demo.

---

## 7. I comandi

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

Se non vuoi che il DMD legga la tastiera, togli la spunta a *«Leggi la
tastiera collegata al Raspberry»* nella pagina Doom.

### Pagina web

Nel riquadro **Comandi** ci sono i pulsanti. Si **tengono premuti**: tenendo
il dito su una freccia si cammina davvero, invece di fare un passo alla volta.

Funziona anche la **tastiera del computer** che sta guardando la pagina, con
gli stessi tasti della tabella qui sopra.

> Dal telefono c'è qualche decina di millisecondi di ritardo, che è la rete e
> non il DMD. Si gioca, ma per giocare bene la tastiera nel Raspberry è
> un'altra cosa.

---

## 8. Taratura dell'immagine

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

---

## 9. Impostazioni della partita

| Parametro | Predefinito | Cosa fa |
|---|---|---|
| **Difficoltà** | 3 | da 1 a 5, la scala di Doom |
| **Livello iniziale** | `1 1` | episodio e mappa da cui parte una partita |
| **Fine partita dopo** | 180 s | secondi senza comandi prima di tornare ai demo. `0` = mai |
| **Doom subentra a Batocera fermo da** | 60 s | quanto deve restare ferma l'immagine di Batocera prima che l'attract mode possa prendere il pannello. `0` = mai |

Difficoltà e livello valgono solo per le partite: l'attract mode fa i suoi
demo e non li guarda.

**Il suono è spento di proposito.** Sul cabinato l'audio è di Batocera, e un
secondo canale sonoro sarebbe soltanto rumore sopra al gioco vero.

I salvataggi e la configurazione di Doom finiscono in
`/var/lib/dmd/doom/stato`, fuori da `/opt/dmd`, che deve restare identico alle
proprie impronte per gli aggiornamenti.

---

## 10. Se qualcosa non va

| Sintomo | Causa probabile | Rimedio |
|---|---|---|
| Il log della preparazione resta vuoto | il servizio DMD non sta girando | `systemctl status dmd`, poi `journalctl -u dmd -n 50` |
| «non è un WAD» | file rinominato, o non è un WAD | usa un file che comincia per `IWAD` |
| «è un'estensione, non un gioco completo» | è un PWAD, cioè una modifica | serve un gioco completo: Freedoom o un WAD di id Software |
| «troppo piccolo, forse scaricato a metà» | scaricamento interrotto | ricopia il file e ricontrolla la dimensione |
| Doom non compare sul pannello | servizio spento | accendilo nella pagina Servizi |
| Doom non compare, ma il servizio è acceso | Batocera sta mandando fotogrammi *nuovi*: allora ha ragione lui | premi **Gioca** per prendere il pannello subito. Se il DMD di Batocera è fermo, controlla la soglia in *«Doom subentra a Batocera fermo da»*: se è a zero la deroga è disattivata |
| Un secondo di nero entrando in partita | Doom sta ripartendo dentro il livello | è normale |
| La tastiera del Raspberry non risponde | l'opzione è spenta, o la tastiera non è vista | controlla la spunta e l'elenco dei dispositivi nella pagina Doom |
| Il pannello resta su Doom dopo che hai finito | la partita è ancora aperta | **Esci dalla partita**, oppure aspetta il tempo di inattività |
| «Il programma è stato compilato prima dell'ultimo aggiornamento» | un aggiornamento ha toccato il sorgente | premi **Ricompila** quando ti fa comodo |

Per guardare cosa succede davvero:

```
journalctl -u dmd -f | grep doom
```

---

## 11. Licenze, in due righe

- Il **DMD Server** è GPLv3.
- **doomgeneric** discende dai sorgenti di Doom, che sono GPL2. Per questo non
  sta nel repository, si scarica e si compila sul posto, e gira come processo
  separato: due programmi che si parlano da una pipe restano due programmi.
- **Freedoom** è libero (licenza BSD) e si può ridistribuire.
- I **WAD di id Software** non si possono ridistribuire. Se ne usi uno, è
  perché lo hai comprato tu.
