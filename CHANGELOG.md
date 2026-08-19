# Changelog

Tutte le modifiche rilevanti del progetto.

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
