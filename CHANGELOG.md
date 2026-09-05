# Changelog

Tutte le modifiche rilevanti del progetto.

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
