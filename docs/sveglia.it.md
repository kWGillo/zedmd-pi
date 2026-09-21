---
title: "La sveglia"
subtitle: "Quattro orari, un orologio che lampeggia, e il pulsante che c'era già"
---

# Perché esiste

Il DMD sta in soggiorno, è acceso tutta la notte, ha un orologio grande e una
scheda audio. Tutto quello che serve a una sveglia c'era già: mancava solo di
metterlo insieme.

# Come si usa

Pagina **Sveglia**. Quattro riquadri, uno per orario, e ciascuno ha:

| Campo | Cosa fa |
|---|---|
| **Attiva** | l'interruttore di quella sveglia |
| **Ora** | l'orario |
| **Giorni** | i giorni della settimana. Nessuno spuntato = tutti |
| **Suona per** | dopo quanti secondi si arrende da sola |
| **Suono** | un file della libreria media, o quello del programma |
| **Etichetta** | una parola che compare sul pannello sotto l'ora |

Il pulsante **Fai squillare adesso** la prova senza aspettare le sette. Vale la
stessa ragione del pulsante di prova delle notifiche: senza, l'unico modo di
sapere se funziona sarebbe metterla e andare a dormire.

# Il timer

Una sveglia si mette **a un'ora**; un timer **fra quanto**. La pasta non scade
alle 20:47, scade fra nove minuti, e nessuno vuole guardare l'orologio e fare
la somma con le mani bagnate.

In cima alla pagina c'è un conto alla rovescia con quattro durate pronte da
premere — i pulsanti vengono prima del campo libero apposta: in cucina si
preme, non si digita — e un campo per scriverne una qualsiasi. Si può dare un
nome («Pasta», «Forno»), che compare sul pannello quando squilla: serve a
sapere *perché* sta suonando, non solo che sta suonando.

Il timer è **uno solo**. Due che scadono insieme darebbero un unico squillo con
due motivi, cioè un'informazione persa. Finché ne sta andando uno i comandi per
avviarne un altro non compaiono: restano il conto alla rovescia e «Annulla il
timer», e per cambiarlo si annulla e si rifà. Prima i comandi restavano lì, e
premerli con il campo vuoto rispondeva «durata non valida» mentre il timer
stava andando benissimo — un errore inventato su un'azione che non andava
nemmeno offerta.

**Sul pannello si vede.** Mentre il timer scorre, l'orologio ha in fondo una
barra rossa spessa due pixel che **si accorcia** man mano che il conto scende:
a metà timer è larga mezzo pannello. Il timer si mette da una pagina web, ma la
pasta si guarda in cucina, e in cucina l'unica cosa che si guarda è il
pannello. Una riga fissa direbbe soltanto che un timer c'è; una che si accorcia
costa gli stessi due pixel e dice anche quanto manca, senza scrivere numeri
sopra un orologio che di numeri ne ha già.

**Il suono del timer** si sceglie nella stessa scheda, sotto i pulsanti. Se
non ne scegli uno, suona quello della prima sveglia attiva — che fino alla 10.0
era l'unico modo di cambiarlo, senza che nessuna pagina lo dicesse.

# Che cosa succede quando scatta

Il pannello diventa un orologio che **lampeggia**, in rosso, con l'etichetta
sotto se l'hai scritta. L'ora sta al centro dello spazio che ha: tutto il
pannello, o quello sopra l'etichetta. Fino alla 10.0 si centrava la *casella*
del carattere invece delle cifre accese, e l'interlinea che il font tiene sopra
le lettere spingeva tutto in basso: senza etichetta l'ora stava bassa, con
l'etichetta la scritta TIMER usciva dal fondo del pannello. La scheda audio suona, e continua a bussare ogni
secondo e mezzo finché non la fermi.

La si ferma in tre modi: il **pulsante fisico**, il pulsante nella pagina,
oppure Home Assistant. Se non la ferma nessuno si spegne da sola
dopo i secondi che hai indicato — una sveglia che suona per sempre in una casa
vuota è un dispetto ai vicini, non una funzione.

# Le tre eccezioni, e perché ci sono

Ogni altra sorgente di questo progetto è **educata**: chiede il pannello, e se
qualcun altro ha la precedenza aspetta il suo turno. Una sveglia educata non è
una sveglia. Questa ha tre eccezioni che nessun altro servizio ha.

**Vince sullo Sleep mode.** Il ciclo principale, quando dorme, si ferma *prima*
di chiedere all'arbitro chi debba comparire: una sorgente qualunque, per quanto
prioritaria, non verrebbe nemmeno interrogata. Una sveglia alle 7 con lo Sleep
fino alle 8 non suonerebbe mai — che è esattamente il caso in cui serve di più.

**Vince sul display spento a mano.** Discutibile, e la scelta è consapevole:
spegnere il pannello è una decisione sul *presente*, mettere una sveglia è una
promessa fatta prima per dopo. Fra le due vince la promessa. Chi non la vuole
spegne la sveglia, non il display.

**Non la tocca il volume notturno.** Il Night mode abbassa la voce del DMD
perché un aereo alle tre di notte non merita di svegliarti. Una sveglia si
mette apposta per svegliarti: sarebbe l'unico caso in cui quel silenzio fa
danno. Suona al volume di giorno, sempre. E la luminosità torna quella diurna:
una sveglia che si vede al quindici per cento è mezza sveglia.

Resta invece dentro **una** regola, e è giusto così: se l'interruttore generale
dell'audio è spento non suona, e il pannello lampeggia lo stesso. Chi ha spento
il suono non vuole sentire niente.

# Il pulsante

Non ne aggiunge uno nuovo: usa il pulsante fisico del DMD, quello che sta sul
GPIO 25. Mentre la sveglia squilla quel pulsante **è suo** — un clic la ferma e
non scatta nessuna foto.

Fino alla 9.1 quel pulsante non era del DMD ma della FunCAM: lo apriva `start()`
della telecamera, quindi esisteva solo mentre il servizio FunCAM era acceso. Con
la FunCAM spenta — il caso normale di chi la webcam non la usa — la sveglia
squillava, la pagina diceva di premere il pulsante, e premerlo non faceva
niente. Da fuori sembrava una saldatura sbagliata.

Adesso il pulsante è del DMD. Mentre la sveglia suona se lo prende lei: se
nessuno lo tiene lo apre da sola, e se ce l'ha già la FunCAM glielo lascia,
perché il clic le arriva e lei lo gira comunque alla sveglia. Lo rilascia il
ciclo principale e non `zittisci`, che viene chiamata dal callback del pulsante
stesso: chiudere un oggetto `gpiozero` da dentro il suo gestore di eventi è il
modo più rapido di piantare un thread.

Chi non lo vuole mette `sveglia.pulsante` a falso in configurazione.

# E i giochi?

Se la sveglia scatta durante una partita, il pannello è suo: priorità **120**,
sopra ZeDMD, che è la più alta del progetto.

**Le partite si fermano, tutte e tre.** Breakout e Invaders hanno un ciclo
nostro, e lo si congela con una variabile: la sessione resta aperta, il tempo
del gioco non passa, e al risveglio la palla riparte da dov'era. I tasti
premuti si dimenticano, così la racchetta non parte da sola verso il muro.

Doom e il Game Boy sono processi separati, con un thread che ne svuota la pipe
dei fotogrammi in continuazione: non si fermano da soli nemmeno quando il
pannello è di qualcun altro. Si sospendono con un segnale del sistema
operativo — `SIGSTOP` li congela con la memoria intatta, `SIGCONT` li fa
ripartire da dov'erano, senza che il programma debba saperne niente.

> **Questa parte è nata da un errore.** La prima stesura non congelava niente,
> con la motivazione che «le sveglie suonano al mattino, e chi sta giocando a
> Doom alle sette?». La risposta è arrivata in una frase — *metti che devo
> ricordarmi di scolare la pasta e mentre cucino decido di giocare a Doom* —
> e ha demolito la premessa: una sveglia serve soprattutto **mentre si è
> occupati a fare altro**. Peggio, la stessa stesura affermava che i giochi
> interni si congelassero da soli perché li disegna il ciclo principale: non è
> vero, hanno un thread loro come gli altri due. Si tornava e ci si trovava
> morti in tutti e tre i casi.

**Un limite che resta, ed è meglio saperlo.** Un processo sospeso non chiude i
file che teneva aperti, scheda audio compresa: se Doom sta suonando quando la
sveglia scatta, la scheda resta sua e la sveglia non può suonarci sopra. Il
pannello lampeggia, il suono no. Liberare quella scheda vorrebbe dire chiudere
la partita, e fra una sveglia muta e una partita persa vale di più la partita —
chi cucina il pannello lo guarda.

# In Home Assistant

Due entità, e la distinzione fra loro conta:

- un **interruttore «Sveglia»**, che dice se gli orari valgono. Spegnendolo non
  suonerà più niente, domani compreso;
- un'**azione «Ferma la sveglia»**, che si accende da sola quando la sveglia sta
  squillando e, spenta, la zittisce.

Sono due cose diverse apposta: fermare lo squillo di stamattina non deve
cancellare la sveglia di domani.

# Se non suona

| Cosa vedi | Cosa vuol dire |
|---|---|
| Niente, all'ora giusta | il servizio Sveglia è spento nella pagina Servizi |
| Lampeggia ma è muta | l'audio generale è spento in Impostazioni |
| Suona pianissimo | il livello hardware della scheda: vedi il manuale dell'audio |
| Si ferma troppo presto | «Suona per» è basso |
| Non si ferma col pulsante | `sveglia.pulsante` è a falso, oppure il pulsante non è saldato: si prova con `gpiozero` a servizio fermo |
