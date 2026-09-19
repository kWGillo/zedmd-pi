---
title: "OnAir"
subtitle: "Il pannello dice che si sta registrando, e lo dice a chi entra"
---

# 1. Perché esiste

Tutti gli altri servizi del DMD parlano a chi **guarda** il pannello: l'ora, gli
aerei, il brano, il compleanno. OnAir parla a chi **entra nella stanza**, e non
sta neanche guardando.

La luce rossa fuori dallo studio esiste da cent'anni per una ragione sola: chi
sta per aprire una porta deve sapere che dall'altra parte c'è un microfono
aperto. Un DMD in soggiorno può fare la stessa cosa senza aggiungere un
oggetto sulla parete, e può farla meglio, perché sa anche scrivere.

# 2. Come funziona, in quattro righe

1. La porta si chiude → sul pannello compare **ON AIR**, ferma, fondo rosso e
   lettere nere. Suona il campanello, una volta.
2. Per tutta la diretta l'orologio porta un **trattino rosso** in cima, largo
   32 pixel e alto 2.
3. La scritta **ricompare** ogni due contenuti del Media Player, così chi entra
   dopo la scopre lo stesso.
4. La porta si riapre → sparisce tutto.

# 3. Il DMD non sa che esiste una porta

Sa solo se è in onda, e lo chiede con un interruttore. La porta la guarda Home
Assistant.

Non è pigrizia: è il confine giusto. Il giorno che il segnale arriverà da un
pulsante sulla scrivania, da un orario, o dal mixer audio, qui non cambia
niente — cambia l'automazione, che sta dove stanno già tutte le altre
decisioni di casa.

In più l'interruttore si comanda **a mano**: dalla pagina OnAir, da Home
Assistant, e passando per HomeKit anche a voce. Il servizio è quindi usabile
subito, prima di aver saldato o comprato qualunque cosa.

## 3.1 Le due entità

| Entità (nome in HA) | Che cosa dice |
|---|---|
| **OnAir** | il **servizio** è acceso: il pannello se ne occupa |
| **In onda** | siamo **in onda**: è quello che comanda la porta |

Sono due apposta, come la sveglia e il suo squillo. Spegnere il servizio non
deve cancellare il fatto che stai registrando, e finire una diretta non deve
disattivare il servizio per domani.

## 3.2 L'automazione

La guida completa, passo per passo, è
[`onair-automazione.it.md`](onair-automazione.it.md); il file pronto è
[`ha/dmd_onair.yaml`](ha/dmd_onair.yaml).

> **I due identificativi si leggono, non si indovinano.** Il DMD *propone*
> `switch.dmd_onair_diretta`, ma Home Assistant può assegnarne un altro —
> per esempio `switch.dmd_controller_in_onda` — unendo il nome del
> dispositivo a quello dell'entità. Lo sa solo lui e non lo ripubblica: va
> letto in *Impostazioni → Dispositivi e servizi → Entità*, cercando
> **`onda`** e non «onair», perché quella pagina cerca nel nome.

> **Attenzione al verso.** Un sensore con `device_class: door` sta a `on` =
> porta **aperta**, `off` = **chiusa**. Quindi «in onda» corrisponde a `off`.

Tre inneschi e non uno. Il primo è il sensore. Il secondo è il DMD che torna
disponibile: pubblica `online` su `dmd/availability`, e quello è il momento
esatto per ridirgli com'è messa la porta — così un riavvio del Pi durante una
diretta non lascia il pannello a credere l'anno scorso. Il terzo è il riavvio
di Home Assistant.

L'azione non guarda **quale** innesco è scattato: rilegge sempre lo stato vero
del sensore e lo riafferma. È ripetibile senza danni, e un innesco perso si
corregge al successivo.

> Se il sensore non ha un valore leggibile — scritto male, oppure pila
> scarica — l'automazione **non spegne niente** e lascia una riga nel registro
> di Home Assistant con il motivo. Prima spegneva in silenzio, ed è il modo in
> cui un errore di battitura è riuscito a sembrare un guasto del pannello.

# 4. La scritta

Testo libero, fino a sessanta caratteri. Va a capo da solo sulle parole e
sceglie il carattere più grande in cui ci sta **davvero**: «ON AIR» riempie il
pannello, una frase lunga scende a tre o quattro righe con il corpo che cala
finché il blocco non entra. Solo quando non c'è più niente da rimpicciolire si
taglia, con i puntini a dirlo.

«Davvero» è la parola che conta, ed è una correzione della 9.8.1. Prima si
contavano le righe invece di misurarle, e bastavano due casi per farlo
sbordare: l'altezza vera di una riga è maggiore del corpo del carattere,
quindi quattro righe uscivano dal basso di un pixel; e una parola sola più
larga del pannello resta una riga sola, quindi «entrava» pur uscendo di lato
per mille pixel.

È la stessa impaginazione delle notifiche MQTT, e non per caso: dalla 9.8 la
regola vive in un posto solo, `sources/testo.py`. Una regola scritta due volte
prima o poi diverge.

Fondo e inchiostro si cambiano dalla pagina. Il predefinito è rosso su nero
perché è quello che chiunque riconosce senza leggere.

**Non lampeggia**, ed è una scelta. Il fondo pieno è già il segnale più forte
che questo pannello sappia fare, e una scritta che lampeggia mentre qualcuno
registra è esattamente la cosa che non vuoi vedere con la coda dell'occhio.

# 5. Quando ricompare

| Situazione | Cadenza |
|---|---|
| Media Player acceso | ogni **2 contenuti** (regolabile) |
| Media Player spento | con i tempi del Media Player, 20–30 s |
| In ogni caso | al massimo dopo **180 s** (regolabile) |

Il tetto di tempo non è un doppione: serve al caso in cui il Media Player è
acceso ma non passa niente — libreria vuota, fascia oraria, Night mode. Senza,
il contatore non avanzerebbe e la scritta non comparirebbe mai, proprio quando
servirebbe. Si può togliere mettendolo a zero.

I tempi dei media si prendono da quelli già configurati invece di inventarne di
nuovi: due manopole che dicono la stessa cosa sono una manopola di troppo.

# 6. Il campanello

Si sceglie in *Servizi → Suoni*, alla voce **OnAir — alla chiusura della
porta**. Il nome dice già la regola: suona **una volta sola**, quando si entra
in onda. Non a ogni ricomparsa della scritta.

Con la cadenza dei media, una diretta di un'ora vorrebbe dire trenta din-don, e
a quel punto il suono non annuncia più niente: è rumore. Una spia annuncia il
**cambio** di stato, non lo stato.

> Tienilo sopra il mezzo secondo, per lo stesso motivo delle notifiche: gli
> avvisi dei servizi non passano dal mixer degli effetti, e una scheda audio
> USB che dormiva si mangia l'attacco.

# 7. Quanto è educato

Priorità **52**: appena sopra il Media Player (50) e la telecamera (51), sotto
il meteo (54) e tutto il resto.

Quando tocca a lui vince la sua fetta di rotazione, ma un aereo di passaggio, un
compleanno o una notifica gli passano davanti. E soprattutto **non interrompe
mai una partita**: chi sta giocando la porta l'ha chiusa lui, e non ha bisogno
che glielo si ricordi a metà di un livello di Doom.

Per lo stesso motivo non riaccende un pannello spento e non scavalca lo Sleep
mode. La sveglia è l'unica che ha il diritto di svegliare.

# 8. Quando non funziona

**La voce OnAir non c'è nel menu.** Stai su una versione precedente alla 9.8.

**L'interruttore non compare in Home Assistant.** Il servizio è acceso? Pagina
*Servizi* → OnAir, nasce spento. E MQTT è connesso, con la discovery attiva?
Pagina *Rete*.

**La scritta non compare mai.** Vai in onda a mano dalla pagina OnAir: se così
compare, il problema è l'automazione, non il DMD. Guarda in Home Assistant se
è scattata, e controlla il verso del sensore.

**Compare una volta e poi più.** È il caso del tetto di tempo messo a zero con
il Media Player acceso e fermo. Rimettilo a 180.

**Resta accesa dopo che ho riaperto la porta.** L'automazione non ha parlato:
spegnila a mano dalla pagina, poi guarda il registro di Home Assistant.

# 9. Riassunto

| | |
|---|---|
| Servizio | *Servizi* → *OnAir*, nasce spento |
| Pagina | *OnAir*, nel menu dopo la sveglia |
| Entità in HA | «OnAir» e «In onda» — l'ID vero si legge in HA |
| Automazione | [`onair-automazione.it.md`](onair-automazione.it.md) |
| Priorità | 52 — non interrompe mai una partita |
| Suono | uno, alla chiusura della porta |
| Sull'orologio | trattino rosso 32×2 px, centrato in alto |
