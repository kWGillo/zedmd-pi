---
title: "La rete wifi dalla pagina web"
subtitle: "Vedere le reti, sceglierne una, e non restare chiusi fuori"
---

# 1. Il problema

Quando la wifi non va, per rimetterla a posto servivano un monitor, una
tastiera e un mouse attaccati al Raspberry. Per un oggetto che sta in
soggiorno è una procedura assurda: il pannello è lì acceso, il DMD funziona,
e l'unica cosa che manca è scrivere una password.

Questa è la prima metà della soluzione: la pagina **Rete**, da cui si vedono
le reti e se ne sceglie una. La seconda metà — l'hotspot di soccorso che si
alza da solo quando la connessione cade — arriverà dopo, e si appoggerà
proprio a questa pagina.

Con una precisazione che conviene fare subito: **questa pagina si raggiunge
via rete**. Se sei già chiuso fuori, oggi non ti tira fuori: serve il cavo
ethernet (il Pi lo prende in DHCP senza configurare niente) o il monitor. È
il soccorso automatico che chiuderà il cerchio.

# 2. Chi comanda la rete

`nmcli`, e nient'altro.

NetworkManager è il proprietario della rete sulle immagini recenti di
Raspberry Pi OS. Il DMD non scrive file di configurazione a mano e non tocca
`wpa_supplicant`: due proprietari della stessa cosa sono peggio di nessuno —
si sovrascrivono a vicenda e il risultato dipende da chi parte per ultimo.

Se `nmcli` non c'è, la pagina si apre lo stesso e lo dice: sei su
un'immagine più vecchia, e la rete si configura in
`/etc/wpa_supplicant/wpa_supplicant.conf`. In fondo alla pagina ci sono i
comandi da riga di comando, che restano validi sempre.

## Le password non le teniamo noi

La password della rete che scegli viene passata a NetworkManager, che le
credenziali le custodisce già per mestiere, in
`/etc/NetworkManager/system-connections` con i permessi giusti.

Nel `config.json` del DMD non finisce niente. È una scelta, non una
dimenticanza: non c'è una password da esportare per sbaglio quando salvi la
configurazione, e non c'è una password da perdere.

Il prezzo è che la password passa dalla riga di comando di `nmcli`, dove per
un paio di secondi è visibile a `ps`. Su una macchina con un utente solo è un
rischio remoto; l'alternativa — scrivere il file di NetworkManager a mano —
vorrebbe dire diventare il secondo proprietario della rete, che è esattamente
ciò che si sta evitando. Nel registro la password non compare: le righe di
log la sostituiscono con `***`.

# 3. La pagina

## Collegamento attuale

Rete a cui sei collegato, potenza del segnale, nome dell'interfaccia, e
**gli indirizzi a cui il DMD risponde** — wifi ed ethernet, perché con il
cavo attaccato sono due. Serve a sapere dove ritrovarlo dopo un cambio.

## Reti visibili

La scansione **non parte da sola**. Dura qualche secondo e muove traffico
sull'interfaccia proprio mentre il pannello sta disegnando: è lo stesso
disturbo che la taratura misura. Si fa quando la si chiede.

Ogni rete mostra segnale, tipo di cifratura, e se è già salvata. Due cose
non compaiono nell'elenco:

- le reti **nascoste**, che arrivano senza nome: non c'è niente su cui
  premere, e per quelle c'è il riquadro apposta più in basso;
- l'**hotspot del DMD stesso**, quando ci sarà: proporlo come rete a cui
  collegarsi sarebbe un invito a girare in tondo.

Lo stesso nome che compare più volte è un ripetitore, non due reti: si tiene
il segnale più forte, che è quello a cui ti collegheresti comunque.

## Reti salvate

Il DMD si ricollega a queste da solo. Si possono dimenticare, tranne una: **la
rete attraverso cui stai guardando la pagina**. Cancellarne il profilo
farebbe cadere la connessione all'istante, e per rimediare servirebbe di
nuovo il monitor — cioè esattamente la situazione da cui questa pagina deve
tirarti fuori. Se la vuoi togliere, collegati prima a un'altra.

## Wi-Fi sempre sveglio

Una casella sola, accesa di serie, e accanto lo stato letto dalla radio in
quel momento. Esiste per un guasto preciso: il DMD acceso, il pannello che
disegna, e **la macchina irraggiungibile** — né SSH né pagina web — finché non
la riavvii togliendo la corrente. Nel registro del kernel c'è una riga sola:

```
brcmfmac: brcmf_cfg80211_set_power_mgmt: power save enabled
```

La radio del Raspberry si addormenta per risparmiare qualche milliwatt, e
l'access point smette di tenerle da parte i pacchetti. Su un computer che usi
non te ne accorgi, perché sei tu a svegliarlo; su un oggetto che sta in un
angolo e a cui ti colleghi da fuori è la differenza fra acceso e sparito.

Il rimedio a mano (`iw dev wlan0 set power_save off`) dura fino al riavvio,
cioè fino al momento esatto in cui non c'è nessuno a rifarlo. Con la casella
accesa lo fa il programma, in due punti:

| Dove | Con cosa | Quanto dura |
|---|---|---|
| Sulla radio, adesso | `iw dev … set power_save off` | fino al riavvio |
| Nella connessione salvata | `nmcli connection modify … wifi.powersave 2` | per sempre |

Il nome della tua rete non serve saperlo: fra le connessioni attive si
riconosce quella wireless dal tipo. E si rifà **a ogni avvio del servizio**,
in un thread a parte che non trattiene l'accensione del pannello, perché una
reinstallazione o una connessione rifatta si riporterebbe dietro il difetto.

Togliendo la spunta si smette solo di **imporlo**: quello che NetworkManager
ha già salvato resta. Disfarlo da qui vorrebbe dire rimettere di nascosto il
guasto che la casella è nata per togliere; se lo vuoi davvero indietro, è una
riga di `nmcli` scritta da te.

Su una macchina senza `iw`, senza `nmcli` o senza wifi non succede niente e
non si rompe niente: la casella resta, e lo stato accanto dice che non si sa.

## Broker MQTT e Home Assistant

In fondo alla pagina, dalla 6.2, c'è il collegamento al **broker MQTT**:
indirizzo, porta, utente, password, topic di base, e le impostazioni di Home
Assistant (discovery, prefisso, nome del dispositivo).

Prima stava nella pagina *Musica*, perché all'inizio dal broker passavano solo
i metadati di AirPlay. Oggi ci passano gli interruttori dei servizi, la
luminosità, le scadenze, il calendario dei rifiuti e — dalla 6.1 — le
notifiche che Home Assistant manda al pannello. Cercare l'indirizzo del broker
sotto «Musica» era diventato un indovinello, e questa è comunque la pagina che
si apre quando qualcosa non si collega.

Nella pagina *Musica* restano i due topic da cui arriva il brano in ascolto —
quello di shairport-sync e quello libero — perché lì sono al posto giusto: non
dicono *come* ci si collega, dicono *da dove arriva la musica*.

I dettagli su come configurare il broker stanno in
[`now-playing.it.md`](now-playing.it.md); quelli sulle notifiche in arrivo in
[`notifiche.it.md`](notifiche.it.md).

# 4. Cosa succede quando premi «Collega»

Qui c'è una cosa che vale la pena capire, perché altrimenti sembra che il
pulsante non funzioni.

Il browser con cui stai premendo è collegato al DMD **attraverso la rete di
prima**. Se il cambio riesce, quella strada non c'è più: la risposta alla tua
richiesta non ti arriverà mai. Una pagina che aspettasse la fine del
collegamento resterebbe lì a girare finché non scade, senza dirti se è andata
bene o male.

Quindi il tentativo parte in un thread e la pagina risponde subito. L'esito
si legge riaprendo la pagina — sul nuovo indirizzo, quello che la pagina
stessa elencava prima del cambio.

Se il tentativo **fallisce** (password sbagliata, tipicamente) non si perde
niente: NetworkManager riattiva da solo il profilo di prima, il DMD torna
dov'era, e riaprendo la pagina trovi scritto cosa non è andato. Per questo il
profilo vecchio non si cancella mai prima di aver provato il nuovo.

# 5. Se la pagina non basta

Da SSH, o da tastiera attaccata al Raspberry, con `sudo`:

```
nmcli device wifi list
sudo nmcli device wifi connect "NOME_RETE" password "PASSWORD"
nmcli connection show
sudo nmcli connection delete "VECCHIA_RETE"
```

E per sapere se questo Raspberry può fare da access point — la domanda che
decide come sarà fatto il soccorso automatico:

```
iw list | grep -A 8 "Supported interface modes"
```

Se fra i modi elencati c'è `AP`, l'adattatore interno può alzare un hotspot.
Se non c'è, servirà una chiavetta USB che lo sappia fare.
