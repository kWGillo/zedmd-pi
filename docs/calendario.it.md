# Google Calendar sul DMD

Gli appuntamenti dei prossimi tre giorni compaiono sul pannello a giro, come
le scadenze. Il DMD legge il calendario e basta: non crea niente, non sposta
niente, non cancella niente. È una vetrina, non un'agenda.

---

## 1. Che cosa si vede, e che cosa non si vede

Il pannello mostra, ogni tanto e per pochi secondi, un appuntamento alla
volta:

- in alto a destra **quando** — giorno, mese e ora — nello stesso colore che
  l'orologio usa per la data, perché è lì che l'occhio va a cercare le date su
  questo pannello;
- al centro **che cosa**, grande, che scorre se il titolo non ci sta;
- sotto **dove** — o, se il posto non è indicato, la descrizione — piccolo e
  in grigio, che è un dettaglio e non deve rubare la scena.

**Niente semaforo.** È la differenza voluta rispetto alle scadenze. Il
semaforo dice *manca poco*, e ha senso per una bolletta, che si può pagare
prima; non ne ha per un appuntamento, che succede quando succede. La
lampadina non aggiungerebbe niente che la data non dica già.

### La finestra dei tre giorni

Un appuntamento compare **tre giorni prima** di succedere e sparisce quando è
passato. È la stessa regola del semaforo delle scadenze applicata agli
appuntamenti: senza una soglia, il pannello mostrerebbe la fine del mese, che
non è una notizia. Un pannello che segnala sempre qualcosa non segnala più
niente.

Si legge solo il **calendario principale** dell'account. Calendari secondari,
colori, promemoria, inviti da accettare, regole di visibilità: tutto ignorato
di proposito. Le ricorrenze le espande Google prima di mandarle: al pannello
arrivano occorrenze con una data ciascuna, non regole da interpretare.

---

## 2. Collegare l'account

Il DMD non ha né tastiera né schermo su cui digitare una password Google, e
non deve averne bisogno: si autorizza **dal browser del proprio computer**, e
al DMD arriva soltanto un token.

Serve un progetto su Google Cloud. È gratuito, e le credenziali restano tue:
non c'è un'applicazione del progetto a cui dare accesso al tuo calendario.

### 2.1 Su Google Cloud

1. Su **console.cloud.google.com** crea un progetto (un nome qualsiasi).
2. In *API e servizi → Libreria* abilita la **Google Calendar API**.
3. In *Schermata consenso OAuth*: tipo **Esterno**, poi aggiungi il permesso
   `https://www.googleapis.com/auth/calendar.readonly` e — questo conta —
   **pubblica l'app in produzione**.

   > Finché la schermata resta *in test*, Google fa scadere i refresh token
   > dopo **sette giorni**: il collegamento si romperebbe ogni settimana
   > senza che nessuno abbia toccato niente. È il motivo per cui questo passo
   > è in grassetto.

4. In *Credenziali* crea un **ID client OAuth** di tipo **Applicazione web**.
5. Fra gli *URI di reindirizzamento autorizzati* incolla
   `http://localhost:8080/api/google/callback` — identico, carattere per
   carattere, a quello che compare nella pagina Calendario del DMD.
6. Copia **Client ID** e **Client secret**.

### 2.2 Sul DMD

Nella pagina **Calendario**:

1. Incolla Client ID e Client secret, controlla l'indirizzo di ritorno, salva.
2. Premi **Autorizza**: compare un link.
3. Aprilo nel browser del tuo computer, scegli l'account, accetta.
4. Il browser finisce su un indirizzo che, quasi sempre, **non si apre**: a
   `localhost` del tuo computer non c'è niente in ascolto. Non è un errore. Il
   codice sta scritto nella barra degli indirizzi: copia l'indirizzo intero e
   incollalo nel campo in fondo alla pagina, poi premi *Completa il
   collegamento*.

È il percorso previsto per i dispositivi senza browser, non un aggiramento.

Fatto questo, la pagina dice *Collegato come...* e l'elenco **Prossimi
appuntamenti** mostra quello che il pannello vede in questo momento. Se è
vuoto e sai che ci sono appuntamenti, controlla di aver autorizzato l'account
giusto.

Infine, nella pagina **Servizi**, accendi **Google Calendar**: nasce spento,
perché un interruttore acceso su un servizio muto fa credere che qualcosa non
funzioni.

---

## 3. Dove finiscono i token

In `/var/lib/dmd/google.json`, con permessi `0600`: leggibile solo da root.

**Non stanno nella configurazione**, e nella configurazione esportata non c'è
nemmeno il *client secret* — viene tolto come la password del broker MQTT. Un
`config.json` gira: finisce in un backup, in un allegato, in una
segnalazione. Chi lo reimporta riscrive il segreto una volta sola; se invece
fosse dentro, basterebbe una disattenzione per regalarlo.

Il pulsante **Scollega l'account** fa due cose: cancella il file dei token (e
svuota quello che era già stato letto) e chiede a Google di **revocare** il
permesso. Sono due porte distinte — la seconda resterebbe aperta anche dopo
aver cancellato tutto da qui — e chiuderle insieme è il comportamento che ci si
aspetta.

Se la revoca non passa (rete assente, token già scaduto) il DMD si scollega
**lo stesso**: chi preme quel pulsante vuole prima di tutto che il pannello
smetta di leggere il suo calendario. Il messaggio lo dice, e in quel caso la
revoca si completa a mano su *myaccount.google.com → Sicurezza → App di terze
parti con accesso all'account* — la stessa pagina da usare se il DMD è
irraggiungibile e vuoi comunque tagliare l'accesso.

Restano invece in configurazione **Client ID e Client secret**: sono
credenziali della tua applicazione, non dell'account.

---

## 4. Quanto spesso si chiede a Google

Ogni **quindici minuti**, e mai più spesso: un calendario non cambia trenta
volte al secondo, e il pannello ridisegna trenta volte al secondo. Fra una
lettura e l'altra si usa quello che si è già letto.

Per la stessa ragione la riga di stato nella pagina Servizi non apre mai una
connessione: mostra la cache. La pagina Servizi è quella che si apre quando
qualcosa non funziona, e non deve poter restare appesa quindici secondi su una
chiamata a Google che non risponde.

Il pulsante **Rileggi da Google** nella pagina Calendario forza la lettura
subito, per quando si è appena aggiunto un appuntamento e lo si vuole vedere.

Se la rete manca, l'errore compare nella pagina e gli appuntamenti già noti
**restano**: un guasto momentaneo non deve cancellare quello che si sapeva.

---

## 5. Quando compare, e chi ha la precedenza

L'avviso compare ogni venti minuti e resta dieci secondi, come quello delle
scadenze. Se ci sono più appuntamenti nella finestra si alternano, invece di
mostrare sempre il primo e non far sapere degli altri.

Nella scala delle priorità sta a **59**: sopra le scadenze (57), perché una
scadenza ha un giorno e un appuntamento ha anche un'ora — chi passa davanti al
pannello dieci minuti prima di uscire di casa ha più bisogno del secondo — e
sotto Air Radar (60), che segnala un aereo che fra dieci secondi non c'è più.

Cinquantanove e non cinquantotto, che sarebbe stato il numero naturale, perché
58 è già di Now Playing: a parità l'arbitro tiene chi si è registrato per
primo — il player — e l'avviso non sarebbe mai comparso mentre suona musica. Un
pareggio di priorità non è un dettaglio estetico, è una sorgente che tace, e
c'è una prova che li rifiuta.

Durante una partita, un video o un flusso ZeDMD non si intromette: quelle
sorgenti tengono il pannello, e l'avviso aspetta il proprio turno.
