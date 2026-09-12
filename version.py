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
  3.0  Doom sul pannello. Gira come programma a se' — doomgeneric con l'uscita
       ritagliata a 256x64 — e parla con il servizio da una pipe: fotogrammi
       da una parte, tasti dall'altra. Due processi e non una libreria perche'
       i sorgenti di Doom sono GPL2 e questo progetto e' GPLv3, e perche' se
       cade cade lui.
       Il problema non era la potenza di calcolo — e' software del 1993 — ma
       la forma dello schermo: Doom disegna 1,6:1 e il pannello e' 4:1, quindi
       si ritaglia una fascia attorno all'orizzonte, dove stanno i nemici, e
       si buttano via pavimento e soffitto.
       Quando nessuno tocca niente Doom gioca da solo, con i demo che ha
       sempre avuto dentro, e cede il pannello a chiunque abbia qualcosa da
       dire. Al primo comando comincia una partita e il pannello e' suo,
       Batocera compreso, finche' non si esce o non lo si lascia fermo. La
       presa del pannello e' quella della gestione media, generalizzata: sono
       la stessa cosa.
       Si comanda dalla tastiera collegata al Raspberry, letta da /dev/input
       senza librerie in piu', e dalla pagina web — pulsanti e tastiera del
       browser, stessa coda di tasti. Niente GPIO: sui pannelli nuovi D ed E
       sono collegati e i pin liberi non ci sono piu'.
  3.0.1 Doom si prepara dalla pagina web invece che da SSH: un pulsante lancia
        la compilazione in sottofondo e ne mostra il log. Serviva sia
        all'installazione pulita sia dopo un aggiornamento via rete, dove non
        c'e' nessuna cartella scompattata da cui lanciare lo script. I WAD si
        controllano davvero: i primi quattro byte dicono se e' un gioco
        completo, un'estensione o un file scaricato a meta', e la pagina
        elenca quelli trovati. Un WAD proprio, se c'e', viene prima di
        Freedoom, e la preparazione non lo scarica per niente.
  3.1  Corretto il difetto che rendeva Doom in attract mode una funzione
       inesistente: su un cabinato acceso non compariva mai. La colpa non era
       di Doom ma di ZeDMD, che resta padrone del pannello finche' Batocera e'
       collegato — e su un cabinato acceso quella condizione e' sempre vera.
       Ora l'arbitro distingue *avere diritto al pannello* da *avere qualcosa
       da dire*: una sorgente ferma da oltre un minuto lascia il posto a un
       riempitivo, e se lo riprende al primo fotogramma nuovo. La deroga vale
       solo finche' un riempitivo c'e', quindi l'orologio non torna a rubare
       il posto all'immagine del tavolo — che era il guasto della 1.12.2 — e
       un aereo di passaggio vale comunque piu' di Doom che gioca da solo.
       I WAD hanno una cartella condivisa in rete tutta loro, /srv/dmd/doom,
       esposta come \\<ip>\dmd-doom accanto a quella dei media: sono l'unica
       cosa di Doom che si mette e si toglie a mano, e chiedere una sessione
       SSH per copiare un file non e' un modo di lavorare. Chi arriva dalla
       3.0.1 se li ritrova spostati li' dalla preparazione, e la
       configurazione si riallinea da sola.
  3.1.1 Tre difetti che insieme facevano sembrare Doom rotto.
        **Le migrazioni della configurazione non venivano eseguite.** Stavano
        in update.sh, e l'aggiornamento via rete non lo esegue: copia i file e
        riavvia. Le chiavi nuove sopravvivevano lo stesso, perche' i default
        si fondono a ogni caricamento, ma una *trasformazione di valore* no —
        e il percorso del WAD restava quello vecchio mentre la ricompilazione
        spostava i file. Doom si rifiutava di partire. Le trasformazioni ora
        stanno in dmdconf, l'unico punto attraversato da qualunque strada di
        aggiornamento.
        **Scegliere il WAD non faceva ripartire niente** se il processo era
        gia' morto — cioe' proprio nel caso in cui quel pulsante serve.
        **Una sorgente che non riesce ad avviarsi non ci riprovava mai**:
        `start()` si considerava gia' avviata. Ora il ciclo ritenta ogni 30 s,
        cosi' correggere un percorso sbagliato basta a rimettere in moto.
        Vietati sulle condivisioni SMB i file di servizio di macOS (`._*`,
        `.DS_Store`): il Finder non li crea piu', quelli gia' copiati vengono
        tolti, e non compaiono piu' fra i WAD. setup_share.sh ora viene
        installato in /opt/dmd, altrimenti setup_doom.sh non lo trovava e la
        condivisione dei WAD non nasceva.
  3.2  Doom non e' piu' un servizio: e' una partita. Si preme "Gioca", tutti i
       servizi si fermano, si gioca; si esce, e tutto riprende da dove stava.
       L'interruttore nella pagina Servizi non c'e' piu', e con lui se ne
       vanno l'attract mode della 3.0 e la deroga nell'arbitro della 3.1 —
       tre meccanismi per una funzione che nessuno aveva chiesto e che non ha
       mai funzionato: prima Doom non si vedeva mai, poi restava a schermo
       dopo l'uscita da una partita, con il Media Player che spuntava ogni
       tanto perche' aveva la priorita' piu' alta. Ora il processo esiste solo
       mentre si gioca, e il pannello e' suo per presa esclusiva.
       La tastiera del cabinato comanda il gioco ma non lo fa *cominciare*, a
       meno che non lo si chieda: il DMD sta in mezzo a un flipper, e un tasto
       sfiorato per caso non deve portarsi via il pannello a meta' partita.
  3.3  Joystick: pad PS4 e compatibili, e pad da PC. Sotto Linux sono
       dispositivi di /dev/input come le tastiere, quindi si leggono con lo
       stesso codice e senza librerie in piu'. Il lavoro vero e' negli assi:
       le levette non sono premute o rilasciate, hanno un valore dentro un
       intervallo che cambia da pad a pad — 0..255 su un DualShock 4,
       -32768..32767 su molti pad da PC — e l'intervallo si chiede al kernel
       invece di darlo per scontato. La conversione in premuto/rilasciato ha
       una zona morta al 40% e rilascia al 28%: senza due soglie diverse una
       levetta tenuta appena oltre il limite fa scattare il personaggio invece
       di farlo camminare. Options sul pad puo' far cominciare una partita, al
       contrario della tastiera: un pulsante preciso su un pad che si tiene in
       mano non si preme per sbaglio.
       Doom si accende e si spegne anche da Home Assistant, come interruttore
       MQTT. Lo stato non viene dalla configurazione — li' non c'e' — ma dalla
       partita in corso, cosi' una chiusura per inattivita' o un avvio fallito
       riportano l'interruttore a OFF da soli.
       Il gamma predefinito passa da 0.70 a 1.15. Lo 0.70 schiariva, ed era un
       ragionamento fatto a tavolino: sul pannello vero sbiancava e rendeva
       illeggibili i menu. Chi ha ancora il vecchio predefinito esatto viene
       corretto; chi ha tarato non viene toccato.
  3.4  Calendario della raccolta rifiuti nella colonna libera dell'orologio.
       Nessun portale da interrogare e nessuna credenziale da custodire: la
       raccolta ha una cadenza fissa, quindi si descrive una volta — quali
       giorni della settimana, con che cadenza (settimanale, quindicinale,
       prima e terza o seconda e quarta del mese) — e il calendario si
       calcola da solo, per sempre e senza rete. La cadenza quindicinale e'
       ancorata a una data di riferimento e non alla parita' della settimana
       ISO: un anno ha 52 o 53 settimane, e chi conta le settimane salta un
       turno a ogni Capodanno.
       Le eccezioni sono due tabelle separate, perche' sono due cose diverse:
       i giorni di mancato servizio e quelli di servizio straordinario. Una
       festivita' che sposta il giro si scrive come due righe, la soppressione
       e il recupero, e le due funzionano insieme.
       Accanto ai rifiuti stanno le attivita' comunali con una fascia oraria
       propria — il lavaggio strada che vieta la sosta dalle 00:00 alle 06:00
       vale finche' il divieto e' in vigore, non fino alle 8 come un bidone.
       Sul pannello i nomi compaiono a sinistra dell'orologio, che resta
       centrato: la colonna sceglie il carattere piu' grande in cui tutti i
       nomi ci stanno, invece di spostare l'ora per farsi posto. Il promemoria
       si accende alle 18 della sera prima e si spegne al passaggio.
       Home Assistant riceve l'evento, non il calendario: per ogni voce un
       binary_sensor che dice se stasera si espone e un sensore con la data
       della prossima raccolta. Con quei due si scrive un'automazione in tre
       righe.
       La voce "Gestione media" esce dal menu in alto: era un doppione del
       link che sta gia' nella pagina Media, ora un pulsante.
  3.4.1 La pagina Rifiuti rispondeva Internal Server Error. Dentro il ciclo dei
        sette giorni della settimana, "loop" e' quello interno, e in Jinja non
        esiste nessun modo di risalire a quello esterno: la casella non sapeva
        a quale voce apparteneva e la pagina cadeva prima di disegnarsi.
        L'indice della voce ora si lega una volta sola, all'inizio del blocco.
        Il difetto e' arrivato al browser perche' il giro di prova delle pagine
        web era rimasto fermo a otto indirizzi e non comprendeva ne' Rifiuti
        ne' Doom: ora le pagine provate sono dodici, e non basta piu' che
        rispondano — si controlla che i campi ci siano davvero, con i nomi che
        l'API rilegge, e che quello che si salva torni indietro intero.
  3.5  Fascia oraria del Media Player, con la stessa forma di Night mode: un
       flag, un'ora di inizio e una di fine, e il passaggio di mezzanotte
       gestito. Il flag viene prima di tutto — spento, che e' il predefinito,
       il Media Player lavora sempre e chi aggiorna non si accorge di niente.
       Fuori dalla fascia il servizio si ferma **davvero**: non e' una
       sorgente accesa che perde la gara, e' il thread che non gira, quindi
       niente decodifica e niente letture dalla scheda SD nelle ore in cui
       nessuno guarda. Riparte da solo quando la fascia si riapre.
       Lo Sleep resta prioritario, e lo resta perche' le due fasce non si
       parlano: il Media Player non sa niente dello Sleep e non puo' quindi
       svegliare un pannello che deve stare spento. Sommare le due condizioni
       dentro la regola della fascia avrebbe voluto dire scrivere la stessa
       precedenza in due posti, e prima o poi in due modi diversi.
       La regola delle fasce esce da dmdd e diventa un modulo suo: da dentro
       una sorgente dmdd non e' importabile, e senza quello il Media Player
       non poteva sapere perche' era fermo. Ora la riga di stato lo dice —
       "fuori dalla fascia 08:00-23:00" invece di "disabilitato", che e'
       un'altra cosa e ha un'altra soluzione.
  3.6  Due giochi scritti per il pannello, e una sezione Giochi che raccoglie
       anche Doom. Non sono emulatori: su 256x64 non calza nessuna piattaforma
       storica — la piu' vicina, il NES, andrebbe schiacciata di quasi quattro
       volte in verticale, e a quel punto un alieno alto otto pixel ne diventa
       due. Scriverli per il 4:1 costa meno che adattare qualcosa che 4:1 non
       e' mai stato, e permette di usare la forma invece di subirla: il campo
       prende i 200 pixel di sinistra, i 56 di destra diventano il tabellone
       con punteggio, record e vite.
       **Breakout** e' quello che soffre meno il pannello, perche' il muro e'
       largo per natura. Fra muro e racchetta pero' ci sono trenta pixel
       invece di duecento, quindi la palla parte lenta e accelera ogni quattro
       mattoni. **Invaders** ha tre file invece di cinque, un colpo per volta,
       ripari che si consumano dove vengono colpiti e la schiera che accelera
       man mano che si svuota.
       Come Doom dalla 3.2 sono una **partita, non un servizio**: si preme
       Gioca, i servizi si fermano, si esce e riprendono. La differenza e' che
       questi stanno dentro al processo — Doom sta fuori per la licenza GPL2 e
       ne paga il prezzo in pipe, compilazione e file che un aggiornamento puo'
       cancellare.
       La lettura di tastiere e pad esce da doom.py e diventa un modulo suo:
       una regola come la zona morta di una levetta non puo' esistere in due
       copie. Doom e i giochi ora leggono con lo stesso codice, e per la prima
       volta quel codice ha una prova che non richiede un pad in mano — gli
       eventi sono ventiquattro byte e si costruiscono a mano.
       Il menu andava a finire fuori dalla finestra: `nav` era un flex senza
       `flex-wrap`, e le voci che non ci stavano sparivano a destra senza che
       niente lo lasciasse intuire. Ora vanno a capo — su un telefono le undici
       voci stanno su tre righe, e non se ne nasconde nessuna.
  3.6.1 La pagina Giochi non aveva i campi per indicare tastiera e joystick a
        mano: la pagina Doom si', ed e' li' che si finisce quando il
        riconoscimento automatico sbaglia. Aggiunti, con lo stesso significato.
  3.7  I giochi si accendono e si spengono da Home Assistant, come Doom: un
       interruttore MQTT per gioco, costruito dall'elenco dei giochi invece
       che scritto a mano, cosi' aggiungerne uno domani basta a farlo comparire
       anche li'. Lo stato non viene dalla configurazione — una partita non e'
       un valore salvato, e' qualcosa che sta succedendo — ma dalla sessione:
       una chiusura per inattivita' riporta l'interruttore a OFF da sola.
       Gli interruttori sono mutuamente esclusivi perche' la presa del pannello
       e' una sola, e con essa e' emerso un difetto che c'era gia': aprire una
       partita mentre ne girava un'altra non dava errore, dava un processo Doom
       vivo dietro le quinte con Home Assistant convinto che si stesse ancora
       giocando a Doom mentre sul pannello c'era Breakout. Aprire una partita
       ora passa da un punto solo, il runtime, che e' l'unico a conoscerle
       entrambe — e ci passa anche la web UI, altrimenti la regola varrebbe
       solo per MQTT.
  3.7.1 In formato 12 ore "AM"/"PM" veniva scritto nell'angolo in alto a
        sinistra, che dalla 3.4 e' la prima riga della colonna dei rifiuti: le
        due scritte finivano una sopra l'altra. Ora sta attaccato alle cifre
        dell'ora, allineato in basso, che e' anche il posto in cui un orologio
        se lo aspetta. La colonna resta l'unica padrona dei suoi 68 pixel.
  3.8  Now Playing: le righe si impilano dalle **metriche dei font** invece
       che da frazioni fisse dell'altezza. Con le frazioni (0,33 e 0,56) su
       sessantaquattro righe l'artista finiva dove cominciava l'album — zero
       pixel di spazio — e la `g` di "D'Agostino" entrava nel titolo del
       disco. Non era un pixel da spostare a mano: era che nessuno aveva
       chiesto ai font quanto spazio volessero. Ora fra le righe ci sono tre
       pixel, uguali a qualunque altezza di pannello, e c'e' una prova che
       rende ogni riga da sola e verifica che l'inchiostro non tocchi quello
       della vicina — con i discendenti, che sono il caso peggiore.
       Il tasto **Start del pad scorre i giochi**: premuto una volta si gioca,
       premuto ancora si passa al successivo, e Select esce. Non c'e' un menu
       da attraversare, perche' su un pannello alto 64 pixel un menu costa
       piu' di quello che risolve. Doom entra nel giro solo se lo si chiede:
       parte in qualche secondo e vuole un WAD preparato, e finirci dentro per
       sbaglio cercando Breakout stona.
       Sulla tastiera del cabinato fanno lo stesso due tasti scelti, e non si
       cercano con evtest: si preme "Impara" nella pagina e poi il pulsante
       sul cabinato, e il codice arriva da solo. Le pulsantiere da flipper
       mandano codici che non stanno su nessuna tastiera da ufficio.
       Il tasto dedicato e' l'unico esente dalla casella "un tasto puo' far
       cominciare una partita", che resta spenta: quella protegge dai tasti
       sfiorati per caso, ma Start e' un gesto deliberato — se ci passasse
       sotto anche lui, la funzione nascerebbe spenta e sembrerebbe rotta.
  3.8.1 Il tasto Start apriva Doom una volta sola: dopo, il giro continuava
        fra gli altri giochi e Doom non tornava mai piu'. Tre difetti insieme,
        e nessuno dei tre si vedeva senza gli altri.
        **Il giro apriva i giochi senza passare dal runtime**, e quindi non
        chiudeva Doom: il processo restava vivo dietro le quinte, in sessione
        per sempre. La regola dell'esclusivita' era stata scritta nella 3.7 nel
        punto giusto, ma il giro le passava accanto.
        **Doom gia' in sessione usciva subito senza riprendere la presa del
        pannello.** "Sono in partita" e "ho il pannello" sono due fatti diversi,
        e un gioco apertosi sopra glielo aveva portato via: si rientrava in una
        partita che non si vedeva, e il pannello restava a nessuno.
        **La posizione nel giro si leggeva dalla partita in corso**, che con
        Doom acceso non e' dei giochi: la risposta era vecchia e il giro
        ripartiva da capo, saltando una casella per sempre.
        Ora la posizione si ricorda a parte, la prima pressione riprende
        l'ultimo gioco invece di saltare al successivo, e c'e' una prova per
        ciascuno dei tre: rimettendo uno qualsiasi dei difetti, fallisce.
        Tolte anche tre funzioni che esistevano in due copie identiche in
        doom.py e comandi.py — quella locale, definita dopo l'import, vinceva
        sull'originale. Erano proprio la duplicazione che lo spostamento della
        3.6 doveva togliere.
  3.8.2 Premendo Start o PS si vedeva un gioco per un attimo e poi Doom se lo
        mangiava. I lettori di Doom e dei giochi ricevono **lo stesso evento**,
        e quei due pulsanti erano di entrambi: "menu" per Doom, con il permesso
        di aprire una partita, e "ciclo" per i giochi. Una pressione sola
        faceva due cose, e vinceva l'ultima.
        Un pulsante deve avere un significato solo. Start, PS e Select ora sono
        **globali** e appartengono ai giochi: i primi due scorrono il giro,
        Select esce da qualunque partita, Doom compreso. Doom li perde, e in
        cambio menu e invio si spostano sulle levette premute (L3 e R3), che
        nessun altro usa: ci rimettono arma1 e arma2, che restano sui tasti
        numerici e sui pulsanti della pagina.
        **Nessun pulsante del pad puo' piu' far cominciare Doom**, e la regola
        e' scritta nel codice e non solo nella tabella dei pulsanti. A Doom ci
        si arriva dal giro — se lo si e' incluso — dalla sua pagina o da Home
        Assistant. La casella "il pad puo' far cominciare una partita" nella
        pagina Doom era diventata una promessa non mantenuta ed e' stata tolta.
        In piu' una guardia buona per il futuro: da un comando non si apre una
        partita **mentre il pannello e' di qualcun altro**. La presa e' l'unica
        cosa che sa chi sta lavorando, e adesso le si chiede.
  3.8.3 Doom non si avviava piu'. Colpa della correzione precedente: la 3.8.2
        ha tolto a Doom l'unica porta che aveva dal pad — Options, che ora
        scorre i giochi — senza accendere quella che doveva sostituirla. La
        casella "Doom nel giro" nasceva **spenta**, e dal cabinato Doom era
        diventato irraggiungibile.
        Ora e' accesa di serie, e chi aggiorna se la ritrova accesa una volta
        sola: da li' in poi la scelta e' sua e nessuno gliela sovrascrive.
        Due difetti trovati guardando, non segnalati.
        **Il giro non chiedeva se Doom fosse pronto**: controllava solo che
        qualcuno sapesse rispondere. Un Doom senza WAD sarebbe stato una
        casella su cui premere Start non fa niente. Ora si chiede davvero, e
        una domanda che solleva vale come un no.
        **Se una casella non parte, il giro passa alla successiva** invece di
        lasciare il pannello a nessuno. Premere Start e vedere il nero e'
        il peggio dei mondi; e se non parte proprio nessuno, dopo un giro
        completo si smette invece di provare all'infinito.
  4.0  Scadenze: appuntamenti e pagamenti, con un semaforo a destra
       dell'orologio. Assomiglia al calendario dei rifiuti, ma le differenze
       contano piu' delle somiglianze.
       **Le cadenze sono altre.** I rifiuti hanno un ritmo settimanale; una
       bolletta e' mensile, trimestrale, annuale — multipli di mesi, ancorati
       a una data di partenza. Il 31 gennaio piu' un mese e' il 28 febbraio e
       non il 3 marzo: una rata che scade il 31 non deve spostarsi di tre
       giorni ogni febbraio.
       **Una scadenza si chiude.** Un bidone si espone e basta; una bolletta
       si paga, e da quel momento quell'occorrenza e' storia. Chiudere una
       periodica apre da sola la successiva.
       **Il semaforo e' tre lampade, non un cerchio che cambia colore.** Con
       tre lampade la posizione dice gia' l'urgenza, e da lontano si legge
       prima il *dove* del *che colore* — che per chi non distingue bene i
       colori e' l'unica cosa che funziona. Spento oltre dieci giorni, verde
       da otto a dieci, giallo da quattro a sette, rosso da zero a tre, rosso
       lampeggiante quando la data e' passata. Le soglie si cambiano, e il
       lampeggio e' in fase con i due punti dell'ora: due cose che lampeggiano
       insieme sembrano un battito, sfasate sembrano un guasto.
       Ogni tanto il pannello mostra **che cosa**: titolo che scorre se e'
       lungo, data del colore del semaforo, descrizione. Scorre solo il
       titolo — far scorrere tre righe darebbe un pannello che si muove tutto
       e non si legge niente.
       **Il registro non si cancella mai.** Ogni occorrenza con l'ora in cui
       e' stata inserita e quella in cui e' stata completata, in un CSV a
       parte: e' l'unica parte del progetto in cui serve sapere *quando* e'
       successo qualcosa. Sopravvive alla cancellazione della scadenza, e se
       la riga aperta non c'e' piu' il completamento si scrive lo stesso —
       meglio una riga senza ora di inserimento che un pagamento senza traccia.
       Le scadenze si scrivono nella pagina, si incollano come CSV (separatore
       riconosciuto da solo), **e arrivano da Home Assistant**: cinque entita'
       fisse piu' l'elenco completo come attributi JSON, e due topic di
       comando per aggiungere e completare. Non un'entita' per scadenza: le
       scadenze nascono e muoiono, e ne resterebbero di orfane a ogni bolletta
       pagata. E' la prima parte del progetto in cui i dati viaggiano anche
       all'indietro.
  4.1  L'interruttore delle Scadenze c'era in configurazione ma non in
       pagina: la lista dei servizi era scritta a mano nel codice, quindi la
       chiave nuova non compariva. Ora c'e' anche in Home Assistant, e
       spegnere il servizio spegne pure il semaforo — lo disegna l'orologio,
       non la sorgente, e un interruttore che obbedisce a meta' e' peggio di
       nessun interruttore. Lampade del semaforo dimezzate: cerchi da 7 pixel
       invece di 13, centrati nella banda sotto la data.
  4.2  Il collegamento del pannello diventa una scelta della pagina
       Impostazioni: fili diretti sui GPIO, Adafruit RGB Matrix Bonnet, o
       Bonnet con la modifica PWM. Sta fuori dal profilo del pannello di
       proposito — che pannello e' e come e' collegato sono due fatti
       indipendenti, e tenerli insieme vorrebbe dire che riapplicare il
       profilo, con la Bonnet montata, riporta l'uscita sui piedini sbagliati
       e spegne il display. Nessun nome fuori elenco viene scritto: una
       mappatura inventata non da' un errore, da' un pannello nero, e la
       pagina per rimediare sta su quel pannello.
  4.3  Registri RGB forzati: un campo che scavalca il blocco di registro del
       profilo, per provare una parola alla volta quando nessun profilo del
       catalogo va bene del tutto. Campo vuoto = comanda il profilo, che
       resta sempre la via d'uscita. Il valore si convalida prima di salvarlo
       (parole esadecimali di quattro cifre, eventualmente per canale) perche'
       li' dentro un errore non da' un'eccezione, da' un pannello che si
       comporta male; e se la libreria installata non conosce l'opzione il
       servizio parte lo stesso col profilo, invece di lasciare il pannello
       nero per una funzione che nessuno ha chiesto.
  4.4  Il ciclo di rendering non riscrive piu' sul pannello un frame identico
       al precedente. Non e' pulizia: ogni scrittura rifa' l'intero buffer dei
       piani di bit, e quelle scritture contendono il bus di memoria alle
       letture del thread che aggiorna il pannello riga per riga — quando la
       lettura di una riga si ferma per qualche microsecondo, quella riga
       resta accesa piu' delle altre. E' la riga chiara che compare in un
       punto sempre diverso, misurata sul campo: peggiora sotto carico di
       memoria e di disco, non si vede nei contatori di interrupt, e non
       cambia con isolcpus. Con l'orologio fermo passiamo da trenta
       riscritture al secondo a una. Il conteggio dei frame mostrati e
       saltati e' in /api/status, per poterlo verificare invece di crederci.
  4.5  Game Boy sul pannello, con PyBoy. Come Doom: processo separato, pipe di
       fotogrammi grezzi, sessione che prende il pannello e lo restituisce.
       Lo schermo 160x144 sta in 71 pixel al centro tenendo le proporzioni, e
       l'**overscan** toglie righe sopra e sotto per allargarlo fino a
       riempire il pannello, perdendo cielo e terreno. Gamma regolabile come
       in Doom. Le ROM stanno in una condivisione SMB e sono di chi le
       possiede: qui dentro non ce n'e' nessuna. Dal pad non si apre mai una
       sessione, e Start e Select del Game Boy stanno sulle levette premute:
       i pulsanti con quel nome sono globali dalla 3.8.2, e un pulsante deve
       avere un significato solo.
  4.5.1 Doom e il Game Boy escono dalla scheda dei giochi scritti per il
       pannello e stanno in una scheda loro, "Emulatori esterni": sono
       programmi separati che fanno la stessa cosa — prendere il pannello per
       una partita — e mettere il Game Boy dentro Doom diceva una gerarchia
       che non esiste.
  4.5.2 La pagina Game Boy dice a che punto sta la preparazione: emulatore,
       cartella e **condivisione SMB**, ognuno con il suo stato, e il nome di
       rete scritto per esteso. Prima si poteva solo dedurlo, e la
       condivisione mancante sembrava un pezzo non implementato invece che un
       pulsante non ancora premuto. La condivisione ora si crea **prima**
       dell'emulatore: se pip fallisce, le ROM si possono copiare lo stesso.
  4.5.3 I pulsanti globali non rubano piu' i tasti al Game Boy. Premendo B
       (cerchio) si usciva dalla partita, e Start e Select — che su Tetris
       servono a scegliere i giocatori — scorrevano i giochi invece di
       arrivare alla console. Ora, a sessione aperta, il lettore dei giochi si
       fa da parte e lascia tutto all'emulatore: resta **PS** per uscire, che
       e' il significato che quel tasto ha sulla console vera. E il Game Boy
       entra nel giro del tasto Start, come Doom, se PyBoy c'e' e la cartuccia
       scelta e' valida.
  4.5.4 **Il servizio non partiva.** Il Runtime assegnava a `giochi.esclusiva`
       un metodo del Game Boy tre righe prima di costruirlo: AttributeError
       all'avvio, pannello nero. La correzione e' l'ordine giusto, piu' una
       lambda perche' il cablaggio non dipenda dall'ordine delle righe. La
       causa vera pero' e' che **nessuna prova costruiva il Runtime**: si
       provavano le sorgenti una per una e le pagine con un runtime finto,
       cioe' tutto tranne il punto in cui il programma si mette in piedi.
       Ora c'e' test_avvio.py: pannello finto, Runtime vero, e un giro di
       rendering completo.
  4.6  Spostamento verticale dell'immagine Game Boy. L'overscan taglia meta'
       sopra e meta' sotto, ma i giochi non sono simmetrici — il punteggio in
       alto, il campo di gioco in basso — e quale meta' interessa cambia da
       cartuccia a cartuccia. Un numero negativo alza la finestra, uno
       positivo la abbassa; oltre il bordo dello schermo il valore smette
       semplicemente di avere effetto, perche' li' non c'e' altro da vedere.
  4.6.1 **Colori dello schermo Game Boy**: verde DMG, grigio, ambra,
       arancione, blu notte o quattro colori scelti a mano. Il Game Boy non ha
       colori, ha quattro gradazioni, e su un pannello LED l'ambra si legge
       meglio del verde del 1989. Corretto anche un difetto della pagina: il
       log della preparazione la faceva ricaricare ogni tre secondi per
       sempre, e un valore appena scritto nei campi dell'immagine tornava
       indietro da solo se non si premeva Invio. E lo stato del WAD e' tornato
       nella pagina di Doom, dove appartiene.
  4.7  **Google Calendar** come servizio: gli appuntamenti dei prossimi tre
       giorni compaiono sul pannello a giro, come le scadenze — in alto a
       destra quando, al centro che cosa, sotto dove — ma **senza semaforo**,
       che e' la differenza chiesta: il semaforo dice "manca poco", e ha senso
       per una bolletta, non per un appuntamento, che succede quando succede.
       Sola lettura e solo il calendario principale: una vetrina, non
       un'agenda. L'autorizzazione si fa dal browser del proprio computer,
       perche' il DMD non ha tastiera; i token stanno in
       /var/lib/dmd/google.json a 0600, fuori dalla configurazione, e il
       segreto del client esce dall'export come la password del broker, e
       scollegando si chiede a Google di revocare il permesso invece di
       lasciare un consenso in piedi dal loro lato. README riscritto: era
       fermo alla 3.4.
  4.8  **Taratura automatica del pannello**, dalla pagina Taratura. Il
       pannello scrive nel log il refresh di ogni fotogramma: in regime sta
       fermo, e quando crolla vuol dire che la libreria ha aspettato la
       memoria mentre una riga restava accesa — che e' la riga chiara che si
       vede. La taratura prova un parametro alla volta, conta i fotogrammi
       rovinati e consiglia la configurazione migliore, che poi si applica e
       si salva come profilo. La soglia e' **relativa** al regime di ogni
       configurazione, altrimenti boccerebbe le piu' lente per il solo fatto
       di esserlo; e le finestre in cui qualcuno ha usato la web UI vengono
       **marcate e scartate**, perche' ogni richiesta e' esattamente il
       disturbo che si sta misurando.
  4.8.1 Quattro difetti trovati usando la 4.8 sul pannello vero. Scegliere un
       profilo non lo applicava, perche' il modulo del pannello era rimasto
       spezzato in due e il menu finiva nel pezzo senza pulsante. Il profilo
       tarato non compariva mai: `dmdconf` costruiva la configurazione
       scorrendo solo le chiavi dei valori predefiniti, e buttava via tutto il
       resto al caricamento — difetto vecchio quanto il progetto, che la
       taratura e' stata la prima a incontrare. La taratura moriva dopo pochi
       secondi, perche' `start_new_session` non la toglieva dal cgroup del
       servizio e il primo `systemctl restart` la ammazzava; lo stesso valeva
       per l'aggiornamento via rete lanciato dal pulsante web, dove sarebbe
       stato peggio. E una taratura interrotta da uno spegnimento continuava a
       dichiararsi in corso.
  4.8.2 La taratura esce dalla scheda del pannello e va in una scheda sua:
       «Salva» e «Avvia taratura» erano due pulsanti vicini che fanno cose
       incomparabili — uno scrive un campo, l'altro avvia tre quarti d'ora di
       riavvii. E l'avvio pretende un campo di conferma che solo quel modulo
       manda: una richiesta capitata su quell'indirizzo non fa piu' partire
       niente.
  4.8.3 Il menu dei profili tornava sempre su «Autotune» qualunque voce si
       scegliesse. Il profilo tarato contiene **un parametro solo**, e il
       riconoscimento automatico bastava quello: siccome lo `slowdown` scelto
       dalla taratura era lo stesso del profilo di fabbrica, ogni
       configurazione risultava "tarata". Ora il profilo tarato vale solo se
       e' stato scelto, non se i valori per caso coincidono.
  4.8.4 Il modulo del pannello tagliava lo `slowdown` a 6, mentre la taratura
       arriva a provare 7 e 8: un profilo tarato su 7 sarebbe stato riportato
       a 6 al primo salvataggio, in silenzio. Due pezzi dello stesso
       programma non possono avere due idee di cosa sia un valore ammesso, e
       ora una prova confronta i due elenchi.
  4.8.5 Il menu dei profili mostra la voce **scelta**, non quella a cui i
       numeri somigliano. Si sceglieva «Personalizzata», si salvava, si
       ricaricava e compariva «FM6373 & DP32020B»: i valori erano quelli —
       «Personalizzata» non li cambia, e' il suo mestiere — ma la scelta
       spariva dallo schermo.
       Non era estetica. Il profilo veniva riapplicato *dopo* i campi del
       modulo a ogni salvataggio, anche quando la voce del menu non era stata
       toccata: si portava il PWM da 10 a 11, si premeva Applica, e tornava
       10 senza dire niente. Ora il profilo si riapplica solo se la voce
       **cambia** — la pagina dichiara al modulo quale stava mostrando — e
       modificare un numero a mano porta il menu su «Personalizzata», che e'
       esattamente quello che e' successo.
  4.8.6 Il profilo tarato riporta anche i parametri che non ha misurato.
       Sequenza: «Personalizzata», PWM a 8, salva, ricarica, «Autotune»,
       salva — e il PWM restava 8. La taratura misura **un** parametro e nel
       profilo scriveva solo quello, quindi sceglierlo dal menu cambiava lo
       `slowdown` e lasciava gli altri diciannove com'erano: una voce di menu
       che non porta da nessuna parte precisa.
       Gli altri parametri sono quelli da cui la taratura e' partita, e ora
       il profilo se lo ricorda: salva il nome del profilo di partenza e
       applicarlo vuol dire «quel profilo, con questo parametro cambiato».
       Chi ha gia' una taratura fatta non deve rifarla: finche' di profili di
       pannello ne esiste uno solo non c'e' niente da indovinare. Se invece
       la taratura e' partita da una configurazione fatta a mano, resta
       scritto anche quello e si applica solo il parametro misurato: i numeri
       scelti dall'utente non si sovrascrivono per deduzione.
  4.8.7 Un interruttore per MQTT in cima alla pagina Servizi. Spegne e
       riaccende il collegamento al broker — e con esso il ponte verso Home
       Assistant — senza toccare nient'altro: indirizzo, utente, password e
       topic restano dove sono, quindi riaccendere e' un clic e non una
       ridigitazione. Prima l'unico modo era un campo in fondo alla pagina
       Musica, dentro un modulo di undici campi che vanno risalvati insieme.
       Spegnendo, il DMD saluta: il "offline" ritenuto fa comparire in Home
       Assistant le entita' come non disponibili invece di lasciarle ferme
       sull'ultimo valore, e il thread del ponte si ferma davvero — prima
       continuava a girare a vuoto, pubblicando su un client che non c'era
       piu'.
  4.9 La pagina Rete: le reti wifi si vedono e si scelgono dal browser.
       Prima, per cambiare rete, servivano un monitor, una tastiera e un
       mouse attaccati al Raspberry — per un oggetto che sta in soggiorno e'
       una procedura assurda.
       Si parla con `nmcli` e con nient'altro: NetworkManager e' il
       proprietario della rete, e due proprietari sono peggio di nessuno. Le
       password vanno a lui, che le custodisce gia' per mestiere; nel
       `config.json` non finisce niente, quindi non c'e' una credenziale da
       esportare per sbaglio ne' da perdere. Nel registro la password diventa
       `***`.
       Il collegamento non si fa dentro la richiesta web: chi ha premuto il
       pulsante e' collegato attraverso la rete di prima, e se il cambio
       riesce la risposta non gli arriva mai. Parte un thread, la pagina
       risponde subito, e l'esito si legge riaprendola sul nuovo indirizzo —
       che la pagina elenca. Se il tentativo fallisce non si perde niente:
       NetworkManager riattiva il profilo di prima, e per questo il vecchio
       non si cancella mai prima di aver provato il nuovo.
       Non si puo' dimenticare la rete attraverso cui si sta guardando la
       pagina: sarebbe staccarsi il filo sotto i piedi, e per rimediare
       servirebbe di nuovo il monitor.
       E' la prima meta'. La seconda — l'hotspot di soccorso che si alza da
       solo quando la connessione cade, e ogni tanto riprova le reti
       conosciute — si appoggera' a queste funzioni.
  4.10 La telecamera. Passi davanti alla webcam e ti vedi sul pannello,
       ridotto a quello che un computer di quarant'anni fa sapeva mostrare.
       Gli otto colori pieni non sono una scelta di stile: sono gli unici che
       su questo pannello non sfarfallano — sta scritto da tempo in
       `nowplaying.safe_colors` — ed e' anche la tavolozza dei primi computer
       a colori. Il vincolo hardware e l'estetica voluta sono la stessa cosa.
       Le sfumature che mancano le rimette il dithering ordinato di Bayer.
       Tre aspetti a scelta dalla pagina: otto colori, verde Game Boy, grigi.
       Il carico si tiene basso in tre modi, e il primo e' il piu' importante:
       i fotogrammi in piu' **non si scartano, non si chiedono**. Uno
       scartato dopo la cattura ha gia' attraversato l'USB e il bus, e il
       risparmio e' solo di CPU; uno mai prodotto non costa niente a nessuno.
       Poi si chiede YUYV e non MJPEG, cosi' non c'e' nessun JPEG da
       decodificare. E se il pannello e' di qualcun altro — ZeDMD, Doom — la
       cattura si ferma da sola dopo venti secondi e riparte quando serve.
       Foto e GIF da due pulsanti, salvate nella libreria media: il Media
       Player le rimette sul pannello da solo, piu' avanti. Se ci sono piu'
       telecamere si sceglie dal menu, e l'elenco mostra solo i nodi che
       catturano davvero — una webcam USB ne espone due o tre, e gli altri non
       danno un fotogramma nemmeno a insistere.
       Le immagini non escono dal Raspberry: niente rete, niente MQTT. Il
       servizio parte spento, perche' e' una telecamera in soggiorno.
  4.10.1 Tre cose sulla telecamera, che adesso si chiama **Funcam** e nel menu
       sta prima dei Servizi.
       **I colori si scelgono.** Da 2 a 8 livelli per canale: 2 sono gli otto
       pieni di prima, 6 ne danno 216 — in pratica la tavolozza da 256 colori
       dell\'epoca. Un 256 esatto con tre canali uniformi non esiste: quei 256
       erano una tavolozza scelta a mano. Salire non costa niente in CPU ne\'
       sul bus; costa solo il rischio che le tinte intermedie sfarfallino, e
       l\'unico modo di saperlo e\' guardare il pannello. La regola degli otto
       colori era nata disegnando **testo**, dove i pochi pixel sfumati di un
       bordo tremano contro uno sfondo fermo: un\'immagine di telecamera e\'
       fatta tutta di mezzi toni e potrebbe comportarsi diversamente. Il
       predefinito resta 2.
       **«Device or resource busy» corretto.** Il /dev/video si apre una volta
       sola, e la chiusura del processo precedente non veniva attesa fino in
       fondo: bastava che ffmpeg avesse chiuso lo stderr perche\' la cattura si
       dichiarasse spenta, mentre il dispositivo era ancora suo. Chi riapriva
       — un clic sull\'interruttore, o la ripartenza automatica dopo una pausa
       — trovava occupato, e restava spento con un errore che sembrava un
       guasto. Ora si aspetta l\'uscita vera del processo, accensioni e
       spegnimenti passano uno per volta, e chi non puo\' bloccarsi (il ciclo
       che disegna il pannello, trenta volte al secondo) se ne va e riprova.
       **E un errore non resta li\' per sempre.** Quasi tutti i motivi per cui
       una telecamera non si apre passano da soli: si riprova con attese che
       raddoppiano fino a mezzo minuto, invece di costringere a spegnere e
       riaccendere il servizio a mano.
  5.0  Il pulsante fisico della Funcam.
       Accendere la telecamera dalla pagina Servizi voleva dire tirare fuori
       il telefono, aprire il browser, trovare la voce: per una cosa che si
       fa passando davanti al pannello e' una procedura assurda — la stessa
       obiezione, e la stessa risposta, della pagina Rete.
       Un pulsante solo, tre gesti. Un clic a telecamera spenta la accende;
       un clic a telecamera accesa scatta una foto dopo tre secondi, con il
       conto alla rovescia grande sul pannello; tenuto premuto tre secondi la
       spegne — e lo fa **mentre** il dito e\' ancora sopra, che e\' l\'unico
       modo di sapere di aver tenuto abbastanza senza contare a mente. A
       servizio spento il pulsante non esiste: non si apre nemmeno il piedino.
       Con il pulsante acceso, il servizio cambia significato: non accende
       piu\' la telecamera, la **arma**. La webcam parte spenta e resta spenta
       finche\' non la si chiama, che su un oggetto con una telecamera in
       soggiorno non e\' una comodita\', e\' il punto. Senza pulsante tutto si
       comporta esattamente come prima.
       **Dove si collega.** GPIO 25, che sul connettore a 40 piedini e\' il
       piedino 22, con una massa accanto al piedino 20 — stessa fila. Un
       pulsante normalmente aperto fra i due e nient\'altro: la resistenza di
       richiamo e\' quella interna al Raspberry. Si salda sui fori del
       connettore della Bonnet, esposti sopra perche\' lo zoccolo sta sotto:
       e\' il metodo che Adafruit documenta per questa stessa scheda, e GPIO
       25 e\' anche il piedino che usa lei per un pulsante.
       La scelta non e\' libera e il programma non la lascia libera: con la
       Bonnet montata la matrice usa 4 (o 18 con la modifica PWM), 5, 6, 12,
       13, 16, 17, 20, 21, 22, 23, 24, 26 e 27, e prenderne uno vorrebbe dire
       un pannello che smette di funzionare con la causa nell\'ultimo posto in
       cui si andrebbe a cercare. Il menu propone solo i liberi, e un valore
       fuori elenco viene rifiutato.
       `gpiozero` si installa **da un pulsante nella pagina**, come Doom, il
       Game Boy e la condivisione SMB: chi ha appena saldato un pulsante
       sotto il pannello non ha un terminale aperto, e mandarlo a cercarne
       uno vanifica il pulsante stesso. L\'installazione gira fuori dal
       servizio — apt ucciso a meta\' lascia dpkg da riparare a mano — e
       aspetta il lucchetto di apt fino a due minuti, perche\' su un Raspberry
       appena acceso ce l\'hanno spesso gli aggiornamenti automatici.
       Se il pulsante non si apre, la telecamera **resta spenta**. La prima
       stesura la accendeva "per non lasciarla irraggiungibile", ed era il
       rovescio esatto di cio\' che serve: chi accende il pulsante vuole una
       webcam spenta finche\' non la chiama, e rispondere a un guasto
       lasciandola accesa in soggiorno per giorni e\' la peggiore delle
       interpretazioni. A non lasciarla irraggiungibile ci pensa la pagina,
       che adesso ha i suoi due comandi — accendi e spegni — utili comunque
       per quando non si e\' davanti al pannello.
  5.0.2 Il pulsante per installare `gpiozero` era nascosto dietro la spunta
       «Pulsante fisico»: per installare la libreria bisognava prima accendere
       una funzione che senza quella libreria non parte. Al contrario, e
       trovato usandolo — la 5.0.1 sembrava non avere affatto quel pulsante,
       e il servizio acceso faceva partire la webcam come sempre, che era il
       comportamento giusto per una spunta spenta ma sembrava un guasto.
       Adesso la scheda «Pulsante fisico» c'e\' sempre, e si legge nell'ordine
       in cui servono le cose: cosa fa, la libreria con il suo pulsante di
       installazione, dove si salda, e infine la spunta per accenderlo. Solo
       i comandi «accendi/spegni» restano nascosti finche\' il pulsante non e\'
       attivo, perche\' senza non farebbero niente.
       La spunta e il piedino hanno un modulo proprio, che scrive due chiavi e
       basta: `api_telecamera` riscrive tutti i campi che riceve, quindi una
       spunta dentro quel modulo avrebbe azzerato dispositivo, risoluzione e
       aspetto. E\' la stessa lezione del profilo del pannello nella 4.8.5.
  5.0.3 «non funziona: Error muxing a packet… Immediate exit requested» non
       era un guasto: era ffmpeg che **salutava**. Il codice -1414092869 e\'
       il suo AVERROR_EXIT, cioe\' "mi hanno chiesto di uscire subito" — e a
       chiederglielo eravamo noi.
       Il difetto stava nel giudizio: trattavo "c\'e\' del testo su stderr"
       come "e\' fallito". Ma ogni chiusura regolare ne stampa. Quindi ogni
       spegnimento del servizio, e soprattutto **ogni pausa automatica**
       — quella che ferma la cattura quando nessuno guarda, cioe\' il
       funzionamento normale — lasciava in pagina un errore mai avvenuto e
       faceva scattare l\'attesa prima di riprovare. Attesa che raddoppiava a
       ogni pausa, fino a mezzo minuto: la telecamera diventava sempre piu\'
       lenta a tornare, con scritto accanto un motivo falso.
       Adesso una chiusura chiesta da noi non viene nemmeno esaminata, e di
       quello che ffmpeg stampa si scartano i saluti noti: se non resta
       niente, non e\' successo niente. Se invece resta qualcosa, in pagina va
       **una riga sola** — quella che spiega — invece di quattrocento
       caratteri di chiacchiere del muxer.
  5.1  Il servizio arma, non accende. Sempre.
       L'interruttore nella pagina Servizi non fa piu\' partire la telecamera:
       dice che la si **puo\'** accendere. La ripresa parte solo quando
       qualcuno la chiama — il pulsante fisico, oppure i due comandi nella
       pagina Funcam, che adesso ci sono sempre. A servizio spento non
       succede niente: ne\' dal pulsante, ne\' dalla pagina.
       Fino alla 5.0.3 questo valeva **solo** con la spunta del pulsante
       fisico attiva; senza, il servizio accendeva la ripresa come una
       sorgente qualsiasi. Era un errore di impostazione, non un difetto di
       codice: legava il momento in cui una webcam in soggiorno si accende a
       una casella che riguarda tutt\'altro — se un pulsante e\' stato saldato
       o no. Su una telecamera *quando si accende* e\' la domanda importante,
       e la risposta non puo\' dipendere da un dettaglio di cablaggio.
       La spunta «Pulsante fisico» resta, ma adesso decide una cosa sola: se
       aprire il piedino per leggere un pulsante. Niente di piu\'.
  5.2  Audio: il pannello guadagna una voce.
       Serve una scheda audio USB, e non e\' un ripiego: la libreria della
       matrice si prende il blocco PWM del Raspberry, che e\' lo stesso che fa
       suonare l\'uscita jack. O si accende il pannello o si accende l\'audio
       interno — quindi l\'audio passa dall\'USB, sempre.
       Tre cose distinte, perche\' rispondono a domande distinte.
       *Le notifiche.* Quando una sorgente prende il pannello — e solo in quel
       momento, non finche\' ci resta — si sente il file scelto per lei nella
       pagina Servizi, preso dalla libreria media. Media, rolling banner e
       rifiuti non ne hanno: i primi due il pannello lo prendono di continuo, e
       un campanello a ogni foto sarebbe un tormento.
       *I giochi.* Invaders e Breakout hanno dodici effetti a onda quadra
       scritti per loro, che stanno in `suoni/` dentro il programma e non nella
       libreria media: sono parte del gioco, non roba da scegliere.
       *Doom.* Suona con la sua colonna sonora, dalla sua uscita ALSA. E\'
       l\'unico suono continuo del sistema, ed e\' anche l\'unico che pesa
       davvero sul bus: per questo ha una levetta tutta sua.
       Nessuna dipendenza nuova: a scrivere sulla scheda e\' ffmpeg, che c\'e\'
       gia\', col muxer `alsa` e il dispositivo `plughw` — che a differenza di
       `hw` converte frequenza e formato al volo, cosi\' un mp3 a 44,1 kHz esce
       anche da una chiavetta che sa fare solo 48 kHz.
       Un suono per volta: se ne arriva un secondo mentre il primo suona, viene
       **scartato**, non messo in coda. Una coda vorrebbe dire sentire il
       campanello di una notifica mezzo minuto dopo che e\' passata.
  5.3  Il DMD diventa una cassa. Un interruttore nella pagina Now Playing e la
       musica AirPlay esce davvero dalla scheda audio, invece di essere solo
       raccontata sul pannello.
       Fino a ieri `setup_nowplaying.sh` mandava l\'audio di shairport-sync
       nella scheda **fittizia** del kernel: dei brani si prendevano i
       metadati e il suono si buttava, perche\' non c\'era niente da cui farlo
       uscire. Con la scheda USB quella scelta non ha piu\' motivo di esistere,
       e cambiarla e\' una riga di `/etc/shairport-sync.conf`.
       Riguarda **solo AirPlay**, e va detto: Spotify racconta un brano che
       sta suonando su un altro dispositivo, e da un racconto non esce audio.
       Prima di scrivere si prova la scheda per davvero, in 44100 stereo e in
       accesso esclusivo, che e\' il formato di AirPlay: se non lo regge, non
       si tocca niente e il motivo si legge subito. Meglio un interruttore che
       non scatta di una cassa AirPlay che non suona piu\' e nessuno sa
       perche\'. La configurazione si modifica in un punto solo, perche\' nello
       stesso file c\'e\' la password del broker MQTT.
       A shairport si da\' `hw:`, ai nostri avvisi resta `plughw:`. Sembra
       un\'incoerenza: `plughw` mette un convertitore davanti alla scheda, ed
       e\' giusto per un mp3 qualunque, mentre shairport la frequenza la
       gestisce da se\' e la scheda vuole vederla com\'e\'.
       Mentre suona la musica gli avvisi dei servizi **tacciono**: la scheda e\'
       di shairport-sync, e comunque un campanello sopra il brano non lo vuole
       nessuno. Le notifiche sul pannello si vedono lo stesso. Doom, per la
       stessa ragione, parte muto — deciso da noi, invece di lasciare che SDL
       fallisca l\'apertura con qualche secondo di errori a inizio partita.
       Corretto un difetto della 5.2: la scelta automatica dell\'uscita
       prendeva l\'ultima scheda dell\'elenco, e su una macchina con Now Playing
       installato l\'ultima puo\' benissimo essere quella fittizia. Il risultato
       era silenzio perfetto senza un solo errore da leggere, che e\' il modo
       peggiore in cui una cosa possa non funzionare. Adesso la scelta
       automatica la salta, e nell\'elenco compare per quello che e\'.
       Degli errori di ffmpeg si mostra la **prima** riga e non l\'ultima: con
       `-v error` stampa prima la causa e poi la conseguenza, e l\'ultima riga
       — "Error opening output device" — e\' proprio quella che non dice
       niente.
       Due pulsanti di form diversi nella stessa scheda stavano attaccati: il
       margine che li stacca ce l\'ha il singolo tasto, e `form.inline` lo
       azzera. Adesso lo stacco lo mette la riga che li contiene. Succedeva in
       Impostazioni (Applica / Prova il suono) e in Funcam (foto / gif); nel
       Radar la coppia Aggiungi / Dimentica era incolonnata invece che
       affiancata, e passa nella stessa riga.
  5.4  **Cerchio spara, e non esce piu\'.** Era l\'ultimo posto in cui il tasto
       B del pad chiudeva una partita. La 4.5.3 aveva tolto quel significato
       al Game Boy, dove B appartiene al gioco; nei giochi interni era
       rimasto, con la motivazione — scritta nel codice — che "chi ce l\'ha
       nelle dita da Doom non deve reimpararla". La motivazione era **falsa**:
       in Doom cerchio e\' `usa`, non l\'uscita. Su un pad i quattro tasti
       frontali stanno sotto le stesse dita, e uno di loro non puo\' portare
       via la partita. Per uscire restano Select e PS, che si premono apposta.
       **Il pulsante di prova dell\'audio non inganna piu\'.** Suona anche a
       "Suono acceso" spento, ed e\' voluto — serve a decidere se accenderlo.
       Ma diceva solo "Suono inviato alla scheda": si provava, si sentiva il
       tono, e si concludeva che l\'audio funzionasse. Poi avvisi e giochi
       restavano muti, senza che il motivo fosse scritto da nessuna parte.
       Adesso, a interruttore spento, il riquadro lo dice **prima** di provare
       e il messaggio della prova lo ripete dopo.
       Le prove dei suoni montavano i giochi a mano, quindi non dicevano
       niente sul collegamento vero — quello che `apri_sessione` fa aprendo la
       partita, cioe\' esattamente il punto in cui il suono poteva mancare.
       Ora una partita vera gira dentro la prova e si controlla che gli
       effetti arrivino a ffmpeg.
  5.5  **Doom non poteva suonare, e l\'avevo scritto io nel Makefile.**
       La 5.2 ha aggiunto la levetta "Audio di Doom" e un manuale che
       spiegava come funzionava. Non funzionava: nel Makefile, in cima, c\'era
       scritto da anni "non vuole SDL e non fa suono", e infatti nessun modulo
       sonoro veniva compilato. `-nosound` era ininfluente, e le variabili
       `SDL_AUDIODRIVER`/`AUDIODEV` non le leggeva nessuno perche\' SDL non era
       collegato. Ho dichiarato una funzione senza verificarla.
       doomgeneric il modulo ce l\'ha — `i_sdlsound.c` e `i_sdlmusic.c`, quelli
       di chocolate-doom — e lo cerca sotto il nome `DG_sound_module` quando
       FEATURE_SOUND e\' definito. Adesso il Makefile lo compila se trova SDL2
       e SDL2_mixer, e se non li trova compila muto come prima invece di
       fallire: una libreria mancante non deve impedire di giocare.
       Serve una **ricompilazione** sul Raspberry, che l\'aggiornamento via
       rete non fa apposta. La pagina Doom se ne accorge da sola: guarda cosa
       ha collegato il binario, non cosa dice il sorgente, e lo dice a chi
       l\'audio di Doom l\'ha chiesto. E il controllo del binario vecchio
       adesso guarda anche il Makefile, non solo il `.c`: questa versione
       cambia **solo** il Makefile.
       **Breakout aveva pochi suoni**, e in parte era vero per costruzione —
       misurati 83 al minuto contro i 291 di Invaders. Ma mancava anche
       qualcosa: l\'effetto `livello` esisteva dalla 5.2 e non lo suonava
       nessuno (lo chiamava solo Invaders), quindi finire un muro passava in
       silenzio. Ora c\'e\', c\'e\' il lancio della palla, e soprattutto i
       mattoni hanno **una nota per fila** che sale scavando verso l\'alto:
       e\' il suono con cui il Breakout del 1976 diceva a che punto eri
       arrivato. Da 83 a 131 suoni al minuto, e non tutti uguali.
       **Il Game Boy suona.** Non con effetti nostri: con la sua APU, emulata
       da PyBoy, che con `sound_emulated=True` calcola i campioni senza aprire
       nessun dispositivo e ce li lascia leggere a ogni tick. Li mandiamo a
       ffmpeg come tutto il resto. Si raccolgono anche dai fotogrammi che non
       vengono disegnati: il video si puo\' saltare, l\'audio no. Segue la
       levetta degli effetti dei giochi, e tace quando la scheda e\' della
       musica AirPlay.
  5.5.1 **La ricompilazione di Doom falliva** con `multiple definition of
       I_InitTimidityConfig`, in fondo, dopo due minuti di attesa.
       Non era un difetto della libreria: era il Makefile che non ricompilava
       abbastanza. La 5.5 aggiunge `-DFEATURE_SOUND`, e quella flag cambia il
       **significato** dei sorgenti — `dummy.c` definisce uno stub di
       `I_InitTimidityConfig` proprio quando FEATURE_SOUND non c\'e\'. Ma
       nessun `.c` era cambiato, quindi make considerava tutti gli oggetti
       aggiornati e ricompilava solo i quattro file nuovi. Al collegamento si
       incontravano lo stub vecchio e la funzione vera.
       Adesso gli oggetti dipendono anche dalle **opzioni**: le opzioni in uso
       si scrivono in un\'impronta dentro la cartella di compilazione, e
       cambiarle rende vecchio tutto. Si ricompila una volta sola, e le
       compilazioni successive restano incrementali.
  5.6  Due difetti dell\'audio, con la stessa radice: **come il PCM arriva
       alla scheda**.
       *Il Game Boy suonava in ritardo.* Il muxer `alsa` di ffmpeg non accetta
       nessuna opzione e apre un buffer fisso di 32768 campioni: a 48 kHz sono
       **0,68 secondi**, piu\' i 340 ms del tubo. Per un avviso non conta
       niente, in una partita si sente eccome. Adesso si usa `aplay`, che il
       buffer lo prende come argomento — 80 ms — e il tubo si stringe a 16 KB.
       `aplay` sta in `alsa-utils`, lo stesso pacchetto di `alsamixer` che il
       manuale fa gia\' usare; se manca si ripiega su ffmpeg, perche\' in
       ritardo e\' meglio che muto.
       *Breakout aveva ancora suoni muti.* La causa era la regola "uno per
       volta": un processo per effetto, una scheda ALSA che sta in mano a un
       programma alla volta, e il secondo suono ravvicinato buttato via. Su
       Breakout se ne perdeva circa un quinto.
       Ora durante una partita c\'e\' un **mixer**: un riproduttore solo, aperto
       quanto dura la partita, e gli effetti sommati in memoria. Si
       sovrappongono invece di annullarsi, e partono nel blocco successivo —
       23 ms invece dei 150-300 ms che costava avviare un processo. Vive solo
       mentre si gioca: a pannello fermo non tiene occupata la scheda.
       Il ciclo che scrive ha un freno suo. Il ritmo lo detta la scheda audio,
       perche\' scrivere su un tubo pieno blocca; ma se il riproduttore
       consumasse piu\' in fretta del tempo reale il ciclo girerebbe a vuoto, e
       su un Pi la CPU bruciata sono righe chiare sul pannello. L\'ha trovato
       una prova, non il pannello.
  5.6.1 **Il mixer della 5.6 non e\' mai partito.** `sources/giochi` importava
       `suoni` dentro una funzione e non a livello di modulo: le due chiamate
       nuove — quella che apre il mixer con la partita e quella che lo chiude —
       riferivano un nome inesistente e sollevavano `NameError`. Il mio
       `except Exception` lo raccoglieva, stampava una riga nel registro e
       tirava dritto, quindi il gioco funzionava e gli effetti tornavano alla
       strada vecchia, quella che ne butta uno su due.
       Misurato sul percorso vero: **54% degli effetti perso** in nove secondi
       di Breakout. Adesso zero.
       Le prove non l\'avevano visto perche\' chiamavano `effetti_avvia`
       direttamente, mai passando da `apri_sessione`. Ora una partita vera si
       apre dentro la suite e si controlla che il mixer sia acceso — e che si
       spenga da solo quando la partita finisce.
       La lezione e\' sul `try/except`: avvolgere una chiamata nuova per non
       far cadere il servizio ha trasformato un errore rumoroso in una
       funzione che semplicemente non c\'era.
       **Il Game Boy spariva dal giro del tasto Start.** In `elenco_ciclo`
       c\'era un `return` anticipato quando "Doom nel giro" era spento, e si
       portava via anche il Game Boy: due caselle indipendenti nella pagina,
       una sola condizione nel codice. Chi toglieva Doom dal giro si ritrovava
       PyBoy fuori, senza nessun rapporto fra le due cose. Difetto vecchio, non
       della 5.6, ma il sintomo e\' identico.
  5.7  **L\'orologio compariva fra un gioco e l\'altro.** Nel giro del tasto
       Start, dopo Doom, il pannello tornava all\'orologio per qualche secondo
       e solo dopo partiva il Game Boy. Non era lentezza da sopportare: era
       l\'ordine di due righe. `apri_sessione` chiedeva la presa del pannello
       **dopo** aver avviato il processo, e avviare PyBoy vuol dire caricare
       Python, numpy e PIL piu\' la ROM — secondi, non millesimi. In quei
       secondi la partita precedente aveva gia\' mollato il pannello e la nuova
       non l\'aveva ancora preso: l\'arbitro lo dava a chi c\'era, cioe\'
       all\'orologio.
       Adesso la presa arriva **prima** dell\'avvio, e se l\'avvio fallisce si
       molla. Lo stesso schema c\'era in Doom, dove il binario parte in un
       attimo e non si vedeva: corretto anche li\', perche\' era sbagliato
       uguale.
       E il pannello non resta fermo sull\'ultimo fotogramma della partita
       precedente: durante il caricamento compare una schermata "GAME BOY" con
       il nome della cartuccia. Chi guarda sa che sta partendo qualcosa.
       **Documentazione allineata.** `docs/README.it.md` dichiarava ancora
       "DMD Controller 1.10" e ripeteva una descrizione del progetto ferma a
       quaranta versioni fa: adesso e\' soltanto l\'indice dei manuali. Nel
       manuale completo entrano la scheda audio USB, le pagine web aggiunte
       dalla 5.0 in poi e la tabella delle priorita\' completa di tutte e
       undici le sorgenti.
  5.8  **I satelliti.** Il pannello avvisa dieci minuti prima che la Stazione
       Spaziale passi sopra casa, lo ricorda a cinque, e durante il passaggio
       mostra dove guardare con l\'ora che lampeggia.
       Non e\' un secondo Air Radar. Il radar racconta quello che passa perche\'
       e\' interessante saperlo; questa sorgente esiste per **far uscire in
       terrazzo al momento giusto**, e da li\' discende ogni scelta.
       *Perche\' parla poco.* Di sedicimila oggetti attivi, a occhio nudo se ne
       vedono pochissimi: serve che il satellite sia al sole mentre qui e\'
       gia\' buio. Quella condizione, piu\' la tabella dei pochi di cui
       conosciamo davvero la luminosita\', porta sedicimila a **uno o due
       eventi al giorno**. La magnitudine nei TLE non c\'e\' e la fonte
       pubblica che la dava -- i file di Mike McCants -- e\' stata ritirata:
       senza quella tabella "visibile" vorrebbe dire soltanto "illuminato", e
       un CubeSat da dieci centimetri passerebbe il controllo come la
       Stazione. Il gruppo *stations* di CelesTrak, che credevo fossero le due
       stazioni, ne contiene venti: il pannello avrebbe mandato qualcuno a
       cercare una scatoletta invisibile.
       *Perche\' avvisa prima.* Un passaggio dura fra i due e i sette minuti,
       misurati. Annunciarlo mentre succede vuol dire arrivare a cose finite.
       *Perche\' durante il passaggio cambia mestiere.* Nei minuti in cui la
       Stazione e\' in cielo il pannello non serve piu\' a ricordare: serve a
       chi e\' fuori e sta cercando. Quindi disegna l\'arco vero del passaggio
       -- da dove sorge a dove tramonta, l\'altezza sull\'orizzonte -- con il
       puntino che ci scorre sopra. Il lampeggio va a secondi pari, la fase dei
       due punti dell\'orologio: due cose che lampeggiano insieme sembrano un
       battito, due sfasate sembrano un guasto.
       Niente rete per funzionare: gli elementi orbitali si scaricano una volta
       ogni sei ore e la posizione si calcola in casa, con SGP4. CelesTrak
       chiede di non interrogare piu\' di una volta all\'ora e di fermarsi al
       primo errore HTTP, pena il blocco dell\'indirizzo: il freno e\' scritto
       nel codice e una prova lo difende.
       Le coordinate sono quelle dell\'Air Radar -- una casa sola, un posto
       solo -- e possono anche essere volutamente imprecise: spostarsi di
       undici chilometri cambia gli orari di due secondi, misurati.
       Quattro difetti trovati provando sul campo, prima che una riga
       arrivasse al pannello: un passaggio gia\' in corso spacciato per appena
       sorto; uno a cavallo della finestra buttato via; la Stazione contata tre
       volte perche\' il catalogo numera a parte i moduli agganciati; e
       soprattutto **la bisezione del tramonto che andava dalla parte
       sbagliata**, scritta pensando solo al bordo che sale. Quest\'ultimo si
       vedeva solo lanciando due volte lo stesso comando: il sorgere restava
       identico al secondo, il tramonto ballava di decine di secondi.
       Manca ancora la pagina dedicata: elevazione minima, preavviso e cadenza
       si regolano da `config.json`. Arriva nella prossima.
  5.8.1 **Il radar non vedeva aerei che passavano davvero.** Segnalato dal
       campo: aerei sopra casa, pannello muto, e premendo "interroga adesso" i
       voli comparivano subito. La catena interrogazione-disegno funzionava:
       era la **cadenza**.
       Nel ciclo l\'intervallo si contava dalla **fine della sfilata** invece
       che dall\'inizio dell\'interrogazione. `_show_all` tiene ogni aereo a
       schermo per i suoi secondi, quindi tre aerei da quindici secondi
       aggiungevano tre quarti di minuto fra un\'interrogazione e la
       successiva: chi leggeva "ogni 40 secondi" ne otteneva ottantacinque. Ed
       era un circolo vizioso, perche\' peggiorava proprio quando il radar era
       piu\' utile: piu\' aerei trovava, meno spesso guardava.
       Misurato su un caso vero, raggio 3 km in un corridoio di atterraggio: la
       probabilita\' di vedere un aereo in avvicinamento passava dall\'89% al
       66% nei momenti di traffico. Con la correzione e venti secondi di
       intervallo si arriva al 99%, e all\'87% sui sorvoli alti e veloci.
       Nella stessa riga c\'era un secondo difetto: `int(cfg["poll_interval"])`
       stava **fuori** dal `try`. Un valore non numerico in configurazione
       avrebbe ucciso il thread del radar per sempre, senza una riga nel
       registro.
       E si e\' aggiunta la cosa che mancava di piu\': la riga di stato adesso
       riporta la cadenza **misurata**, non quella configurata. Il difetto e\'
       rimasto nascosto per versioni intere perche\' nessuno poteva
       accorgersene -- la pagina dichiarava trenta secondi e nessuno mostrava i
       novanta veri.
       L\'intervallo predefinito scende da 30 a 20 secondi: con un raggio di
       pochi chilometri un aereo di linea attraversa il cerchio in meno di
       mezzo minuto, e interrogare piu\' lentamente del transito vuol dire non
       vederlo mai. Sotto i 15 non si scende comunque: e\' un servizio gratuito
       della comunita\'.
  5.8.2 **Il registro dei passaggi.** Come quello dei voli, ma con una colonna
       che cambia il senso della cosa: dentro ci finiscono anche i passaggi
       **non visibili**, con l\'altezza del Sole accanto.
       Prima i non visibili non venivano nemmeno calcolati: si scartavano
       subito. Era il filtro al posto sbagliato. La visibilita\' e\' una scelta
       di cosa **mostrare**, non di cosa **sapere** -- e con due soli oggetti
       calcolarli tutti costa niente.
       Cosi\' il registro risponde alla domanda vera, quella che altrimenti
       resta senza risposta: *perche\' stasera il pannello non ha detto
       niente?* Perche\' la Stazione e\' passata a 82 gradi alle 11:46, con il
       Sole a 21 gradi. Su tre giorni: sedici passaggi, tre visibili.
       Si scrive **a cose fatte**, non al calcolo: un passaggio previsto non e\'
       un passaggio avvenuto, e un registro che mescola le due cose non
       risponde piu\' a niente. Stessa regola del registro dei voli.
  6.0  **I satelliti sono un servizio completo.** La pagina dedicata, il
       manuale, e le due cose che mancavano al pannello.
       *Il terzo colore.* I passaggi che non si vedono sono quattro al giorno
       contro uno: mostrarli cambia il servizio da "parla una volta al giorno"
       a "parla cinque volte". Arrivano in grigio-azzurro spento, senza
       preavviso e senza lampeggio, per venti secondi attorno al culmine --
       dove l\'arco e\' piu\' bello da guardare. La riga sotto dice perche\' non
       si vede: "SOLE +21" oppure "IN OMBRA". Il colore e l\'assenza di
       lampeggio dicono da soli che non e\' un invito a uscire, ed e\' la
       differenza fra un servizio piu\' vivo e un servizio che mente.
       *Lo spegnimento.* Nel 13% dei passaggi visibili la Stazione non
       tramonta: entra nell\'ombra della Terra e sparisce di colpo a meta\'
       cielo, in tre o quattro secondi. E\' la cosa piu\' spettacolare che
       faccia. Adesso l\'istante si calcola, sull\'arco c\'e\' un taglio che
       segna il punto, la curva oltre quel punto e\' in tono minore, e negli
       ultimi quarantacinque secondi il pannello scrive "SPARISCE 21:14".
       *La pagina.* Elevazione minima, preavviso, cadenza, famiglie, le due
       caselle, l\'eta\' degli elementi orbitali, l\'elenco dei prossimi
       passaggi -- con il motivo accanto a quelli invisibili -- e i pulsanti
       del registro. Con una regola scritta nel codice: togliendo tutte le
       spunte alle famiglie ne resta una, perche\' un servizio acceso che non
       guarda niente non da\' nessun errore, resta solo muto per sempre.
       *Il manuale*, `docs/satelliti.it.md`, con il PDF.
       Numero tondo perche\' il DMD fa una cosa che prima non faceva: non
       mostra piu\' soltanto quello che succede, **dice quando uscire a
       guardare**.
  6.0.1 **Un cane da guardia per il radar**, e tre etichette che mancavano.
       Il sintomo dal campo, tre volte in tre giorni: aerei sopra casa,
       pannello muto, e premendo "interroga adesso" i voli comparivano. Due
       spiegazioni possibili, e i dati raccolti non bastavano a separarle: il
       cerchio da 3 km troppo stretto per quello che si percepisce come
       "sopra casa", oppure il ciclo del radar fermo.
       Un ciclo fermo non puo' accorgersi da solo di essere fermo: serve
       qualcuno da fuori. Adesso il ciclo lascia un **battito** a ogni giro, e
       il giro principale del servizio -- che passa una volta al secondo -- lo
       guarda. Se il battito e' vecchio piu' di quattro intervalli (e mai meno
       di due minuti: una sfilata di aerei dura, e un cane da guardia nervoso
       sarebbe peggio del difetto) il ciclo viene riavviato.
       Non e' una cura, ed e' importante scriverlo: il difetto, se esiste,
       resta da trovare. Ma e' una **misura**: ogni rianimazione lascia una
       riga nel registro con un orario, e la riga di stato la conta. Se quel
       numero resta a zero per settimane, il blocco non c'era e la risposta
       era il raggio.
       Nella stessa passata, una prova di fumo sui template ha trovato **tre
       chiavi di traduzione inesistenti**, li' da versioni: sulla pagina Game
       Boy due etichette mostravano il nome grezzo della chiave, e su Now
       Playing il pulsante di salvataggio si chiamava "form.save".
  6.1  **Home Assistant parla al pannello**, e i sensori smettono di mandare
       il vuoto.
       Fino a qui il DMD parlava tanto e ascoltava pochissimo: una trentina
       di topic pubblicati, e in ascolto soltanto i comandi dei propri
       interruttori. Ma in casa la cosa che sa di piu\' e\' Home Assistant --
       chi c\'e\', se la porta e\' aperta, se l\'allarme e\' inserito -- e non ha
       uno schermo in soggiorno. Il DMD ha lo schermo e non sa niente.
       Il contratto e\' piccolo di proposito: un topic, un JSON con testo,
       livello e secondi, tre livelli. La politica sta di la\', dove stanno
       gia\' le automazioni.
       **Sul livello si regge tutto**: decide il colore, il lampeggio e --
       la cosa che conta -- se puo\' interrompere una partita. `info` e
       `avviso` aspettano il loro turno; `allarme` prende il pannello con la
       stessa presa degli emulatori. Ed e\' scomodo da usare apposta: se
       diventasse il livello di tutti, il pannello sarebbe una sveglia che
       non si spegne.
       Nella stessa passata, il difetto che si vedeva solo dall\'altra parte:
       cinquanta righe al giorno di `Invalid state message \'\'` nel registro
       di Home Assistant. Un sensore `device_class: date` riceveva la
       stringa vuota quando non c\'era nessuna scadenza. Il modo corretto di
       dire "non lo so" e\' la stringa `None`. La prova che lo copre non
       legge il codice: cattura i 71 messaggi veri e li valida contro la
       dichiarazione di discovery con cui li abbiamo annunciati.
       *Lo script pronto per Home Assistant*, `docs/ha/dmd_notifica.yaml`, e
       il manuale `docs/notifiche.it.md` con il PDF.
"""

__version__ = "6.1"
