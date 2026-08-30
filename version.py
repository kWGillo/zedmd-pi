"""Versione del DMD Controller.

Storico:
  1.0  Prima versione: ricevitore ZeDMD-WiFi, orologio, web UI.
  1.1  Colori di ora e data separati, formato 12/24h, lingua dei giorni,
       Media Player separato dall'orologio con foto e video a rotazione,
       Night mode e Sleep mode, condivisione SMB e upload da web.
  1.1.1 update.sh: installa ffmpeg e samba in modo indipendente.
  1.2  Regolazioni fini del driver S-PWM dalla web UI, per eliminare i lampi
       orizzontali; riavvio del servizio dall'interfaccia.
  1.3  Air Radar: informazioni degli aerei in transito entro un raggio da una
       coordinata GPS, tramite le API pubbliche ADS-B della comunita'.
  1.3.1 Nessuna coordinata preimpostata: la posizione resta solo nella
        configurazione locale, mai nel codice distribuito.
  1.4  Air Radar: scelta dei parametri di volo da mostrare e registro CSV dei
       passaggi, scaricabile dalla web UI.
  1.5  Aggiornamento via rete dal repository GitHub, con verifica preventiva
       dell'archivio e ripristino automatico se il servizio non riparte.
  1.5.1 Air Radar: la rotta veniva cercata solo se era attiva una seconda
        casella, ora rimossa; ricerca su hexdb.io piu' robusta.
  1.5.2 Le rotte arrivano dal servizio routeset di adsb.lol, in blocco e con
        codici IATA; prova diagnostica nella pagina Radar; pulsanti separati
        nella pagina Media.
  1.6  L'elenco della libreria media viene tenuto in memoria invece di
       rileggere il disco a ogni contenuto e a ogni richiesta della web UI:
       con librerie molto grandi la scansione continua occupava CPU e scheda
       SD e si vedeva come righe bianche sul pannello.
  1.7  Interfaccia web in italiano e inglese, con la lingua rilevata dal
       browser e un selettore in ogni pagina; link al progetto su GitHub nel
       piede di pagina.
  1.7.1 Un errore dell'interfaccia web non ferma piu' il servizio: il pannello
        resta acceso e il motivo finisce nel log invece di far riavviare il
        processo all'infinito.
  1.7.2 Impronte md5 di tutti i file e verifica automatica prima e dopo la
        copia: un file arrivato corrotto viene riconosciuto subito, per nome,
        invece di far fallire l'avvio senza spiegazioni.
  1.8  Esportazione e importazione della configurazione dalla web UI, con
       esclusione facoltativa delle coordinate del radar. La taratura del
       pannello, trovata per tentativi, non dipende piu' dalla scheda SD.
  1.9  Rolling banner: dieci testi scorrevoli con colore, dimensione,
       velocita' e lampeggio propri, a comparsa periodica. Controllo degli
       aggiornamenti della libreria della matrice, senza installazione
       automatica.
  1.9.1 L'aggiornamento via rete installa i file dichiarati dall'archivio
        scaricato, non quelli elencati nel codice gia' installato: una
        versione che aggiunge un file non lo lasciava indietro. Controllo
        dei file mancanti prima del riavvio e ripristino anche quando a
        fallire e' la copia.
  1.9.2 Il controllo della libreria funziona anche quando la cartella
        appartiene all'utente e il servizio gira come root: git rifiutava il
        repository con "dubious ownership".
  1.9.3 Il riquadro "Ora e sincronizzazione" passa dalla pagina Impostazioni
        a quella dell'Orologio, sotto le impostazioni di aspetto: le due cose
        si regolano insieme.
  1.9.4 Due leve nuove nella regolazione fine: durata del bit meno
        significativo e bit resi con dithering temporale. Alzano il refresh
        reale senza abbassare la profondita' PWM, che era l'unico rimedio
        allo sfarfallio dei mezzi toni.
  1.10  Now Playing: il pannello mostra titolo, artista, album e avanzamento
        del brano in ascolto. I metadati arrivano da shairport-sync via MQTT
        (AirPlay 2: qualunque applicazione di iPhone, iPad o Mac, quindi
        anche Amazon Music e Apple Music), dall'API di Spotify per la musica
        che non passa da AirPlay, oppure da un topic MQTT libero per tutto il
        resto. Il DMD si presenta da solo a Home Assistant con MQTT
        Discovery, ma funziona anche senza. Il testo del player si disegna
        senza antialiasing e con soli colori pieni: le intensita' intermedie
        erano la causa dello sfarfallio, non il numero di colori.
  1.10.1 setup_nowplaying.sh viene installato in /opt/dmd insieme al resto.
        Nella 1.10 restava solo dentro il pacchetto scompattato, per analogia
        con setup_share.sh: ma quello lo chiamano install.sh e update.sh,
        mentre questo lo lancia l'utente. Dopo un aggiornamento via rete non
        c'e' nessuna cartella scompattata, e lo script non si trovava.
  1.10.2 setup_nowplaying.sh: mancava il pacchetto libplist-utils fra le
        dipendenze, e senza il programma plistutil la configurazione di
        shairport-sync per AirPlay 2 si ferma. Corretto anche il flag di
        systemd, che e' --with-systemd-startup. E quando qualcosa fallisce lo
        script stampa la riga del registro che spiega il motivo, invece di
        limitarsi a dire dove trovarla.
  1.10.3 setup_nowplaying.sh: aggiunto systemd-dev, che serve a configure per
        interrogare systemd e su Debian recenti e' un pacchetto a parte.
        Soprattutto: prima di compilare, lo script verifica in due secondi
        tutto quello che configure andra' a cercare, e se manca qualcosa lo
        elenca con il nome del pacchetto. Prima ogni dipendenza mancante si
        scopriva a compilazione avviata, una per volta, e ogni giro era un
        altro tentativo da capo.
  1.10.4 setup_nowplaying.sh riconosceva la compilazione riuscita solo se la
        stringa di versione diceva "AirPlay-2" col trattino, mentre
        shairport-sync scrive "AirPlay2" attaccato: il binario era a posto e
        lo script lo rifiutava. Ora la grafia viene normalizzata prima di
        confrontare, e se il controllo fallisce lo script stampa la stringa
        che ha letto invece di limitarsi a dire che qualcosa non va.
  1.10.5 setup_nowplaying.sh scriveva /etc/shairport-sync.conf a 640 root:root
        quando c'e' la password del broker: il demone non gira come root e
        non riusciva a leggerlo, fallendo l'avvio con "file I/O error". Ora
        il file passa al gruppo del servizio, e lo script verifica davvero
        che quell'utente riesca a leggerlo invece di darlo per scontato.
        Prima di riavviare i servizi azzera il contatore dei fallimenti, che
        altrimenti fa rifiutare il riavvio anche a causa corretta.
  1.10.6 La pausa dal telefono non veniva vista: il pannello continuava a far
        avanzare il tempo di un brano fermo, e dieci secondi dopo faceva
        sparire tutto. L'unico avviso e' il codice grezzo `paus`, che ora
        viene ascoltato, insieme allo stato esplicito sul topic `playing`.
        La fine della sessione non cancella piu' il brano di colpo: resta
        fermo per la finestra di permanenza. Le sottoscrizioni non prendono
        piu' l'intero ramo: le copertine non attraversano piu' la rete per
        essere buttate.
  1.10.7 L'applicazione si chiama kWGillo DMD Server. Il menu parte
        dall'Orologio e finisce con le Impostazioni, che restano comunque la
        pagina di ingresso.
  1.11  Air Radar: due tabelle CSV modificabili traducono i codici in nomi
        leggibili — designatori ICAO degli aeromobili e codici IATA degli
        aeroporti. Un codice che non e' in tabella viene mostrato com'e', e
        il sistema tiene il conto di quelli che incontra senza saper
        tradurre, cosi' la pagina Radar dice che cosa conviene aggiungere per
        primo. I file vivono in /var/lib/dmd e non vengono mai sovrascritti
        dagli aggiornamenti.
  1.11.1 Air Radar su tre fasce: identificativo, rotta al centro, dettagli in
        basso. Fra il numero di volo e la riga dei dettagli restava una banda
        vuota, e su una riga sola i nomi lunghi facevano scartare modello e
        quota per far entrare tutto. Se la rotta tradotta non ci sta si
        mostrano i codici, invece di tagliarla a meta'.
  1.11.2 Le due tabelle di conversione arrivano anche con l'aggiornamento via
        rete. Nella 1.11 erano in una sottocartella nuova, e l'aggiornamento
        lo esegue il codice della versione precedente, che l'elenco dei file
        lo legge dall'archivio ma le cartelle da copiare le ha cablate: la
        cartella non veniva creata e le tabelle sarebbero rimaste vuote. Ora i
        modelli stanno in cima all'installazione, dove il codice vecchio li
        vede, e la scelta delle cartelle e' dichiarata dall'archivio come gia'
        avviene per i file, cosi' la prossima cartella nuova non ripetera' la
        storia. I file gia' presenti in /var/lib/dmd non vengono toccati.
  1.11.3 Le rotte non venivano tradotte quasi mai: la tabella degli aeroporti
        conosceva solo i codici IATA di tre lettere, ma il servizio delle
        rotte quel campo spesso non ce l'ha e ripiega sui codici ICAO di
        quattro, che restavano sigle. Ora ogni riga puo' portare piu' codici
        separati da una barra e la tabella distribuita li ha gia' entrambi
        (MXP/LIMC): tutti e 326 gli scali rispondono a tutte e due le grafie.
  1.11.4 Air Radar: scegliendo molti parametri di volo la riga in basso non ci
        stava, e i campi in eccesso venivano buttati via senza dirlo. Ora la
        pagina Radar decide che cosa fare: accorciare la riga come prima,
        alternare gruppi di campi che ci stanno per intero — nessuno perso —
        oppure farla scorrere. Finche' i campi ci stanno tutti le tre scelte
        si comportano allo stesso modo, e il pannello resta fermo. Identifica-
        tivo e rotta non si muovono mai: cambia solo la fascia bassa.
  1.11.5 "Disposizione informazioni": l'etichetta della scelta nuova era
        lunga, andava a capo e sfalsava le tre caselle affiancate.
  1.11.6 Lo scorrimento veniva interrotto allo scadere del tempo dell'aereo,
        anche a meta' riga: spariva un testo che si stava ancora leggendo,
        cioe' proprio il difetto per cui lo scorrimento esiste. Ora la durata
        a schermo e' un minimo: la passata arriva in fondo e si cambia aereo
        quando l'ultimo carattere e' uscito da sinistra. Stessa regola per le
        pagine, che si vedono per tutto il loro turno.
  1.12  Air Radar: la compagnia aerea fra i parametri mostrabili. Non e' un
        campo che arriva dal servizio — sta nelle prime tre lettere del
        nominativo, e in AFR1732 la compagnia e' Air France — quindi serve
        una terza tabella di conversione, modificabile come le altre due e
        distribuita con 129 compagnie. Un volo che non ha compagnia, come
        l'aviazione generale che usa l'immatricolazione, non mostra nulla in
        quel campo invece di inventarsi una sigla. Il registro dei passaggi
        guadagna la colonna airline_name.
  1.12.1 Il colloquio HTTP che precede il flusso ZeDMD finisce nel registro,
        con l'indirizzo di chi lo ha chiesto, e compare nello stato del
        servizio. "Nessun client" confondeva due guasti diversi: il client che
        non ha mai raggiunto il Pi, e il client che si e' presentato ma non ha
        aperto il flusso. Ora si distinguono senza indovinare.
  1.12.2 Un client ZeDMD collegato non si prende piu' il pannello per sempre.
        Su Batocera dmdserver e' un servizio permanente: resta agganciato
        anche a menu fermo, mandando keep-alive ogni 100 ms, e la connessione
        da sola bastava a dare la precedenza a ZeDMD — che senza partita non
        manda niente. Il pannello sarebbe rimasto nero e orologio, radar e
        banner non sarebbero piu' ricomparsi. Ora contano i fotogrammi, non la
        connessione ne' il traffico. Lo stato del servizio distingue i tre
        casi che prima si somigliavano: nessuno collegato, collegato e muto,
        collegato e in trasmissione. Corretto anche un errore della 1.12.1,
        che inizializzava i contatori dell'handshake solo allo spegnimento:
        la pagina dei servizi andava in errore fino al primo handshake.
  1.12.3 Due difetti dello stesso tipo, entrambi sul pannello che non si
        aggiorna. Gli aggiornamenti a zone scrivevano i pixel ma non
        chiedevano di ridisegnare: aspettavano un comando RenderFrame che non
        sempre arriva, e l'immagine restava indietro finche' un aggiornamento
        successivo non la sbloccava per caso — si vedeva come "cambio gioco e
        il DMD resta fermo, ne cambio un altro e allora si aggiorna". Ora le
        zone rimaste in sospeso si mostrano comunque dopo 120 ms, che durante
        il gioco non scattano mai. E per la stessa ragione il pannello tornava
        all'orologio dopo un minuto di menu fermo: la 1.12.2 misurava la
        vitalita' sull'ultimo fotogramma, ma un client collegato che ha gia'
        mandato qualcosa tiene il pannello finche' resta collegato — l'immagine
        del tavolo selezionato deve poter restare ferma per minuti.
  1.12.4 Lo stato di ZeDMD conta i fotogrammi ricevuti al secondo e quelli
        finiti davvero sul pannello. Sono numeri di diagnosi, non una
        correzione: quando l'immagine arriva in ritardo dicono se il Pi ne
        riceve pochi — e allora il limite e' a monte, rete o client — oppure
        se ne riceve tanti e ne mostra pochi, che sarebbe un limite del ciclo
        di disegno. Senza questa distinzione ogni ottimizzazione sarebbe a
        occhio.
  1.12.5 Documentazione: attivare il servizio dmd_real su Batocera era una riga
        sola ("attiva DMD reale"), e nessuna spiegava come accorgersi che non
        fosse partito. Il config.ini da solo non avvia niente, e il sintomo —
        Raspberry in ascolto, nessun client — e' identico a quello di un
        indirizzo sbagliato. Ora le due cause si distinguono in un comando, e
        sono documentate le trappole viste sul campo: la chiave lasciata da
        Pixelcade, l'indirizzo rimasto al Raspberry precedente, e il fatto che
        tenendo premuto il tasto di scorrimento EmulationStation non pubblica
        nessuna immagine.
  2.0  Compleanni: un elenco di date e nomi, caricabile da CSV o scritto a
       mano, e il pannello ricorda chi compie gli anni con un messaggio
       scorrevole a partire da due giorni prima. Profili hardware del
       pannello: un menu applica in blocco i venti parametri di un tipo di
       pannello, e soprattutto permette di tornare indietro dopo una
       configurazione sbagliata — che non da' un errore, da' un display
       illeggibile. La taratura trovata sul campo diventa il valore
       predefinito dell'installazione, invece di essere qualcosa da
       reimpostare a ogni scheda nuova. Night mode e Sleep mode si accendono
       da Home Assistant come i servizi. Air Radar: unita' di misura
       scegliibili per quota, velocita' e distanza; identificativo del volo
       allineato a destra con i codici della rotta accanto; freccia spaziata
       fra origine e destinazione. Tabelle di aerei, aeroporti e compagnie
       aggiornate.
  2.0.1 Il servizio Compleanni non compariva nella pagina Servizi: la
        sorgente funzionava, ma senza interruttore non partiva mai e sul
        pannello non si vedeva niente. L'elenco dei servizi era cablato nel
        codice e me ne ero dimenticato. Aggiunto anche il tipo di ricorrenza,
        compleanno o anniversario, perche' di un anniversario non si dice che
        compie gli anni. Aggiornamenti del programma e della libreria in una
        pagina propria, dopo le Impostazioni: sono le uniche due cose che
        cambiano il software invece di regolarlo. Air Radar: numero di volo a
        sinistra e codici della rotta a destra, centrati sul suo asse. La
        libreria media si sfoglia a pagine da 200 invece di fermarsi ai primi
        400 file, e accanto a Elimina c'e' Vedi: prima di cancellare qualcosa
        bisogna poter guardare che cos'e'.
  2.0.2 Il pulsante "Vedi" della libreria media mostra il file **sul
        pannello**, non nel browser: quello che conta e' come viene li', con
        quella scala e quei colori. L'anteprima e' una sorgente a se', con
        priorita' 90: sotto ZeDMD e sopra tutto il resto, perche' chi ha
        appena premuto sta guardando il pannello adesso. Nella stessa pagina
        il pulsante non si sovrappone piu' al peso del file. Air Radar mostra
        i codici della rotta nella forma IATA di tre lettere anche quando il
        servizio ha risposto in ICAO: MXP invece di LIMC. La frase
        dell'anniversario dice "Domani e' l'anniversario di", non "Domani
        l'anniversario di". Tolte dalle tre tabelle dieci righe con codici
        ripetuti.
  2.0.3 Gestione media: una pagina propria per la libreria, e finche' resta
        aperta il pannello e' di chi guarda — tutte le sorgenti sospese,
        ZeDMD compreso. La priorita' alta della 2.0.2 non bastava: fra un file
        e l'altro restava sempre una finestra in cui qualcun altro si
        infilava. Corretti due difetti dell'anteprima, che erano lo stesso
        difetto: "Vedi" mostrava il file *precedente*, e una GIF in corso si
        bloccava. L'anteprima riusava il ciclo video del Media Player
        dirottandogli il buffer di uscita, e quel ciclo non si puo' fermare da
        fuori; ora ne ha uno suo, interrompibile a ogni fotogramma.
"""

__version__ = "2.0.3"
