---
title: "Aggiornamenti"
subtitle: "Perché il pannello non si aggiorna da solo, e come fa a dirti che dovrebbe"
---

# 1. La domanda, e la risposta

*«Aggiungiamo un aggiornamento quotidiano automatico?»*

No. E il motivo è che **il controllo quotidiano esisteva già**: dalla 1.5, ogni
ventiquattro ore, acceso di serie. Interrogava GitHub, trovava la versione
nuova, scriveva una riga in `ota.log` — e si fermava lì.

Il buco non era il controllo. Era l'annuncio.

## 1.1 Perché no all'installazione automatica

Tre motivi, tutti di questo progetto e nessuno teorico.

**L'aggiornamento via rete non esegue `install.sh`.** Sostituisce i file e
riavvia. Una versione che introduce una dipendenza nuova non si installa male:
si installa, e il servizio non riparte. Il ripristino automatico lo rimette in
piedi — ed è la ragione per cui questa discussione si può fare — ma ti riporta
alla versione di prima. Il pannello la mattina funziona, e tu credi di essere
aggiornato.

**Il riavvio cade quando capita.** In mezzo a una partita, con la sveglia che
sta per suonare, con l'ON AIR acceso e la porta dello studio chiusa.

**E soprattutto: questo pannello ha un utente solo, ed è coinvolto.** Il
software che si aggiorna da solo esiste per l'utente assente — mille
dispositivi, gente che non aprirà mai una pagina di configurazione. Chi apre
la pagina quasi ogni giorno non ha quel problema. Ha il problema opposto: che
nessuno gli dica che c'è qualcosa di nuovo.

> Il costo di restare indietro di una versione è qualche giorno senza una
> funzione. Il costo di un'installazione notturna andata storta è un pannello
> spento su una mensola e una mattina passata in SSH. Non sono due rischi
> paragonabili.

# 2. Dove si vede che c'è una versione nuova

Tre posti, e nessuno dei tre interrompe quello che stai facendo.

## 2.1 In Home Assistant

Il pannello si dichiara come **entità `update`**, che è il tipo che Home
Assistant ha fatto apposta:

| | |
|---|---|
| Nome | **Aggiornamento** |
| Mostra | installata `9.9` → disponibile `9.10` |
| Porta con sé | le note di rilascio e il link alla release |
| Ha | un pulsante **Installa** |

Finisce nella stessa lista in cui Home Assistant mette gli aggiornamenti del
sistema operativo e degli add-on, cioè in un posto dove uno *già guarda*. Un
`binary_sensor` chiamato «Aggiornamento disponibile» avrebbe detto la stessa
identica cosa in un posto dove nessuno la cerca.

> **Il pulsante non è un aggiornamento automatico.** È una pressione, come
> quella sulla pagina web, solo fatta dal divano. Che poi ci si possa scrivere
> sopra un'automazione è vero, ed è una scelta da prendere con gli occhi
> aperti — non una che il pannello prende di nascosto ogni notte.

Il pulsante **rifiuta di partire** in due casi: se il controllo non ha trovato
niente di nuovo, e se un'installazione è già in corso.

## 2.2 Sul pannello

Quattro pixel verdi nell'**angolo in alto a destra** dell'orologio.

Sono otto pixel su sedicimila, e la posizione non è casuale: è il punto più
vuoto del pannello. La data comincia alla riga 2, il trattino rosso della
diretta sta al centro, la colonna delle raccolte differenziate sta a sinistra,
la barra del timer sta in fondo. Lì non c'è mai niente — e proprio per questo,
quando qualcosa compare, si nota senza guardarlo apposta.

Non lampeggia, non suona, non interrompe. Chi vuole sapere l'ora la legge lo
stesso; chi si chiede cos'è quel puntino apre la pagina *Aggiornamenti*.

Si spegne dalla pagina *Aggiornamenti*, con la spunta **Segnala la versione
nuova sul pannello**. Da spento il pannello è identico a prima.

## 2.3 Nella pagina web

Un pallino accanto alla voce **Aggiornamenti** del menu, visibile da qualunque
pagina. Verde quando c'è una versione nuova, **rosso** quando l'ultimo
aggiornamento è finito male.

# 3. Il controllo guarda la release, non il ramo

Fino alla 9.9 il controllo leggeva `version.py` dal ramo `main`. Adesso chiede
a GitHub **l'ultima release pubblicata**.

La differenza conta più di quanto sembri. `version.py` sul ramo cambia nel
momento in cui si fa push, cioè anche a metà di un lavoro; la release esiste
solo quando qualcuno ha deciso che quella versione si può installare. Fra i
due c'è la distanza che separa *«il codice è cambiato»* da *«la versione è
pronta»*, ed è esattamente la distanza che un pannello su una mensola deve
rispettare.

In più la release porta con sé due cose che il ramo non ha: **quando** è stata
pubblicata e **cosa** contiene. Le note di rilascio si leggono nella pagina
prima di premere Installa.

## 3.1 Se l'API non risponde

Si ricade su `version.py` del ramo, come funzionava fino alla 9.9. L'API di
GitHub ha un limite di chiamate per indirizzo e un giorno può semplicemente
non rispondere: un controllo meno preciso è meglio di un controllo che smette
di funzionare.

La pagina dice sempre quale delle due strade ha preso, alla voce **Il
controllo guarda**.

## 3.2 Si installa quello che la pagina ha promesso

L'archivio si scarica dal **tag** della release, non dalla punta del ramo.
Senza questo la pagina prometterebbe la 9.10 e potrebbe installare qualunque
cosa fosse stata spinta su `main` nel frattempo.

Quando il controllo è ripiegato sul ramo non c'è nessun tag, e allora si
scarica il ramo — come prima.

# 4. Quando un aggiornamento va storto

La catena di sicurezza è la stessa dalla 1.5, e funziona:

1. scarica in una cartella temporanea
2. verifica che ci siano i file attesi e che tutto il Python compili
3. salva una copia dell'installazione corrente
4. sostituisce i file e riavvia il servizio
5. interroga la pagina web per capire se il servizio è davvero ripartito
6. se non risponde, **ripristina la copia** e riavvia di nuovo

Il passo 6 è il motivo per cui l'installazione gira in un processo separato e
staccato: deve sopravvivere al riavvio del servizio che l'ha avviata.

## 4.1 Il difetto che il passo 6 aveva creato

Il ripristino funzionava, e proprio per questo era diventato invisibile.
Rimetteva in piedi la versione precedente e l'unica traccia era una riga in
fondo a `ota.log`.

Dal punto di vista di chi guarda il pannello, la mattina dopo, **un
aggiornamento fallito e uno mai tentato sono la stessa identica cosa** — salvo
che nel primo caso continui a premere Installa e continua a non succedere
niente.

Dalla 9.10 l'esito finisce in `/var/lib/dmd/ota-esito.json`, che sopravvive al
riavvio del servizio, e da lì in tre posti:

| Dove | Cosa si vede |
|---|---|
| Pagina *Aggiornamenti* | un banner con la versione tentata, quella rimasta attiva, il motivo e l'ora |
| Menu | il pallino diventa **rosso** |
| Home Assistant | il sensore **Ultimo aggiornamento** |

Il banner resta finché non premi **Ho letto**. Non sparisce da solo, perché
sparire da solo è esattamente il difetto di prima.

## 4.2 Il sensore di Home Assistant

`sensor.…_ultimo_aggiornamento` — il nome esatto lo assegna Home Assistant, e
va letto lì.

Lo stato è una parola: `riuscito`, `ripristinato`, `fallito`, `ripristino
fallito`, oppure sconosciuto se non è mai stato tentato niente. Gli attributi
portano `atteso` (la versione che si voleva), `attiva` (quella rimasta),
`motivo` e `quando`.

È la cosa su cui si scrive un'automazione che **ti manda una notifica sul
telefono** quando un aggiornamento non è andato a buon fine.

# 5. Le impostazioni

Pagina **Aggiornamenti**:

| Campo | Predefinito | A cosa serve |
|---|---|---|
| Repository | `kWGillo/zedmd-pi` | da dove si aggiorna |
| Ramo | `main` | usato solo quando si ripiega sul ramo |
| Controllo ogni (ore) | `24` | ogni quanto si chiede a GitHub |
| Controlla automaticamente | acceso | il giro quotidiano |
| Segnala sul pannello | acceso | i quattro pixel verdi |

# 6. Quando non funziona

**Il pallino verde c'è ma la pagina dice che è tutto aggiornato.** Premi
*Controlla ora*: il pallino segue l'ultimo controllo riuscito, e se è passata
un'installazione nel frattempo il controllo è più vecchio di lei.

**La pagina dice «il ramo (l'API delle release non ha risposto)».** Il limite
di chiamate di GitHub, o la rete. Non è un guasto: il controllo ha funzionato
lo stesso, solo con meno informazioni. Riprova più tardi.

**In Home Assistant l'entità Aggiornamento non compare.** Controlla che
l'integrazione MQTT sia accesa nella pagina *Impostazioni* del DMD e premi
*Ridichiara le entità*. Le entità nuove di una versione compaiono solo dopo
che il pannello si è ridichiarato.

**Il controllo non riesce e in Home Assistant l'entità dice «aggiornato».** È
voluto: quando il controllo non riesce si dice che l'ultima versione
disponibile *è quella installata*. Un'entità update senza `latest_version` in
Home Assistant compare come guasta, e una notizia che non è arrivata non è un
guasto del pannello.

**Ho premuto Installa e non succede niente.** Guarda il diario in fondo alla
pagina. Se l'installazione è partita, lì ci sono le righe; se il servizio non
è ripartito, il banner rosso te lo dice al ritorno della pagina.

**Il banner rosso dice «`/opt/dmd/.lgd-nfy0` is a named pipe».** È successo
installando la 10.1 da una 10.0 o precedente. Quella è la pipe con cui lgpio,
la libreria del pulsante fisico, riceve i suoi avvisi: la apre nella cartella
del servizio, e la copia di sicurezza delle versioni fino alla 10.1 non sapeva
saltarla. Toglila e premi di nuovo *Installa*:

```
sudo rm /opt/dmd/.lgd-nfy0
```

Il pulsante continua a funzionare: la pipe è già aperta, e alla ripartenza la
libreria ne apre una nuova. Dalla 10.2 la copia di sicurezza la salta da sola.

# 7. Riassunto

| | |
|---|---|
| Si aggiorna da solo | **no**, mai |
| Controlla da solo | sì, ogni 24 ore |
| Cosa guarda | l'ultima release pubblicata, con ripiego sul ramo |
| Cosa installa | il tag della release, non la punta del ramo |
| Avviso in Home Assistant | entità `update` nativa, con pulsante |
| Avviso sul pannello | 4×2 pixel verdi in alto a destra |
| Avviso nella pagina | pallino sul menu, verde o rosso |
| Se va storto | ripristino automatico **più** un banner che resta |
