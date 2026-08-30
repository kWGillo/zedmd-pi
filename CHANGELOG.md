# Changelog

Tutte le modifiche rilevanti del progetto.

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
