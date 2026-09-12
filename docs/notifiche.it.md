---
title: "Le notifiche da Home Assistant"
subtitle: "La porta che si apre, la lavatrice finita, l'allarme: la casa parla al pannello"
---

# 1. Il verso che mancava

Fino alla 6.0 il DMD parlava tanto e ascoltava pochissimo. Pubblicava una
trentina di topic verso Home Assistant — interruttori, luminosità, scadenze,
rifiuti, brano in ascolto — e si iscriveva soltanto ai comandi dei propri
interruttori.

Ma in casa la cosa che sa di più è Home Assistant: sa chi c'è, se la porta è
aperta, se l'allarme è inserito, se la lavatrice ha finito. Il DMD ha uno
schermo in soggiorno e non sa niente; Home Assistant sa tutto e non ha uno
schermo in soggiorno. Questa funzione mette in comunicazione le due cose nel
verso che mancava.

Il risultato pratico: apri la porta di casa e sul pannello scorre *Porta
d'ingresso aperta*. Finisce la lavatrice e te lo dice. Scatta l'allarme e il
pannello lo grida in rosso, interrompendo qualunque cosa stesse facendo.

> **Il contratto è piccolo di proposito.** Un topic, un JSON con tre campi,
> tre livelli. La politica — quando parlare, quando tacere, con che parole —
> sta in Home Assistant, dove stanno già le automazioni. Duplicarla anche sul
> DMD vorrebbe dire due verità che prima o poi divergono, e la seconda la
> scopri quando non funziona.

# 2. Che cosa serve

Niente di nuovo da installare. Servono due cose che probabilmente hai già:

1. **MQTT configurato e connesso** sul DMD. Pagina *Rete* → sezione *Broker
   MQTT*: indirizzo del broker, utente, password. Se la riga dice `non
   connesso`, è lì che si comincia — il resto di questa pagina non può
   funzionare.
2. **Il servizio Notifiche acceso.** Pagina *Servizi* → *Notifiche*. Nasce
   spento: senza qualcuno che pubblichi resterebbe muto per sempre, e un
   servizio acceso che non riceve niente non dà nessun errore, è solo muto.

In Home Assistant non serve installare niente: l'integrazione MQTT c'è già, ed
è la stessa che fa comparire il DMD fra i dispositivi.

# 3. Il contratto

Il DMD ascolta **un solo topic**:

```
dmd/notifica
```

Si cambia dalla pagina *Servizi* → *Notifiche*. Il messaggio può avere due
forme.

**Testo semplice.** Tutto quello che non comincia con `{` vale come notifica
al livello più basso:

```
mosquitto_pub -h 192.168.1.10 -u utente -P password \
              -t dmd/notifica -m "ciao dal salotto"
```

Serve per provare al volo, senza costruire nessun JSON.

**JSON**, per tutto il resto:

```json
{"testo": "Porta d'ingresso aperta", "livello": "avviso", "secondi": 6}
```

| Campo | Obbligatorio | Valore |
|---|---|---|
| `testo` | sì | Quello che scorre sul pannello |
| `livello` | no | `info`, `avviso`, `allarme`. Predefinito `info` |
| `secondi` | no | Da 2 a 120. Predefinito 8 |
| `colore` | no | Esadecimale, scavalca il colore del livello |
| `lampeggio` | no | `true` o `false`, scavalca quello del livello |

Se il testo è più largo del pannello scorre da destra a sinistra come il
banner, e se avanza tempo ripassa: meglio due giri di una frase che si legge
che uno solo perso mentre guardavi altrove.

> **Un messaggio che comincia con `{` deve essere JSON valido.** Se non lo è,
> viene scartato e contato, non mostrato com'è. È una scelta che nasce da una
> prova: con il ripiego a testo semplice, un'automazione con un errore di
> battitura faceva scorrere `{rotto` in soggiorno — e chi guarda il pannello
> non ha modo di capire che il guasto è in Home Assistant.

# 4. I tre livelli

Sul livello si regge tutto. Non è un'etichetta decorativa: decide il colore,
se lampeggia e — la cosa che conta davvero — **se può interrompere una
partita**.

| Livello | Colore | Lampeggia | Interrompe |
|---|---|---|---|
| `info` | azzurro | no | no |
| `avviso` | arancione | no | no |
| `allarme` | rosso | sì | **sì, qualunque cosa** |

`info` e `avviso` aspettano il loro turno come ogni altra sorgente: se stai
guardando l'orologio compaiono subito, se stai giocando a Doom aspettano che
tu abbia finito.

`allarme` si prende il pannello anche a metà partita, con lo stesso meccanismo
che usano Doom e il Game Boy per tenerselo. Se qualcuno entra in casa alle tre
di notte, il punteggio di Breakout non è la priorità.

> **`allarme` è scomodo da usare apposta.** Se diventa il livello di tutti, il
> pannello smette di essere un oggetto da soggiorno e diventa una sveglia che
> non si spegne. Tienilo per le tre o quattro cose per cui ti faresti
> svegliare: intrusione, fumo, acqua.

# 5. La via breve: il pannello nella tendina

Dalla 6.6 il DMD **si dichiara da solo** a Home Assistant come tre entità
`notify`, una per livello. Non devi installare niente: compaiono da sole
insieme alle altre entità del DMD.

| Entità | Che cosa fa |
|---|---|
| `notify.dmd_controller_notify_info` | azzurro, aspetta il suo turno |
| `notify.dmd_controller_notify_avviso` | arancione, aspetta il suo turno |
| `notify.dmd_controller_notify_allarme` | rosso, lampeggia, **interrompe tutto** |

In un'automazione: *Aggiungi azione* → **Notifiche: invia un messaggio** →
scegli **DMD - avviso** dalla tendina, scrivi il testo. Fine. Il pannello
compare nell'elenco dei bersagli accanto al telefono, e **il livello è la
scelta del bersaglio** invece di un campo da ricordare.

```yaml
action: notify.send_message
target:
  entity_id: notify.dmd_controller_notify_avviso
data:
  message: Porta di casa aperta
```

Sotto, ognuna pubblica su un topic per livello — `dmd/notifica/avviso` — e il
DMD tratta il testo nudo come una notifica di quel livello. Non c'è nessun
template da scrivere: è la ragione per cui i topic sono tre invece di uno con
un `command_template` che costruisca il JSON.

**Quando serve ancora lo script** (capitolo 6): se vuoi la durata diversa da
quella predefinita, un colore tuo, o il silenziatore che zittisce il pannello
lasciando passare gli allarmi. L'entità `notify` sa mandare solo un testo — ed
è esattamente per questo che è comoda.

# 6. Lo script in Home Assistant

Il file pronto è [`ha/dmd_notifica.yaml`](ha/dmd_notifica.yaml): contiene lo
script, cinque automazioni d'esempio e l'helper. Qui sotto c'è il perché e la
procedura.

## 6.1 Perché uno script e non quindici automazioni

Ogni automazione potrebbe pubblicare il suo JSON da sola. Ma il giorno che
cambi il topic, o vuoi che di notte non parli, o aggiungi il colore, con lo
script cambi **un posto solo**. Senza, cambi quindici automazioni e ne
dimentichi tre — e le tre dimenticate non danno errore, semplicemente non
compaiono più.

## 6.2 L'interruttore (facoltativo, consigliato)

*Impostazioni* → *Dispositivi e servizi* → *Helper* → *Crea helper* →
*Interruttore virtuale*, nome **DMD notifiche**. Deve venire
`input_boolean.dmd_notifiche`.

Serve a zittire il pannello senza spegnere niente sul DMD: lo accendi e lo
spegni dalle automazioni — ospiti, film, notte. Se non lo crei, lo script
funziona lo stesso e non zittisce mai.

Da non confondere con `switch.dmd_notifiche`, che il DMD pubblica da solo:
quello dice **se il servizio esiste**, questo dice **se la casa ha voglia di
parlare adesso**. Due cose diverse, e l'automazione ha senso che tocchi la
seconda.

## 6.3 Lo script

*Impostazioni* → *Automazioni e scene* → *Script* → *Crea script* → i tre
puntini in alto a destra → **Modifica in YAML** → incolla il blocco `SCRIPT`
del file, senza la riga `script:` e senza la chiave `dmd_notifica:`.

Salvalo con il nome **DMD - invia notifica**. Deve venire
`script.dmd_notifica`.

Dentro ci sono tre cose che vale la pena conoscere:

- **`mode: queued`.** Se due cose succedono insieme, la seconda aspetta invece
  di cancellare la prima. Con `single` — il valore predefinito — la porta che
  si apre mentre parte l'allarme farebbe sparire uno dei due messaggi.
- **La guardia del silenziatore**, scritta così che *un allarme passa
  comunque*: altrimenti basterebbe dimenticare l'interruttore spento per non
  sapere che è entrato qualcuno. Ed è scritta così che se l'helper non
  esiste lo script funziona lo stesso.
- **`retain: false`.** Con `true` il broker terrebbe l'ultimo messaggio e il
  DMD, a ogni riavvio, ti mostrerebbe di nuovo che la porta era aperta tre
  giorni fa.

## 6.4 La prova

*Strumenti per sviluppatori* → *Azioni* → `script.dmd_notifica`, campo
**testo**: `Ciao dal soggiorno` → *Esegui azione*.

Se non compare niente, vedi il [capitolo 9](#9-quando-non-funziona).

## 6.5 Il pulsante di prova sul DMD

Dalla 6.3, nel riquadro *Notifiche* della pagina **Servizi** del DMD c'è un
campo di testo, i tre livelli e un pulsante **Manda una prova**. Serve a
rispondere alla domanda «funziona?» senza aprire Home Assistant.

**Passa dal broker**, e non è un dettaglio: la notifica viene pubblicata sul
topic e torna indietro per la stessa strada che fanno quelle vere. Così la
prova copre quasi tutti gli anelli — broker raggiungibile, iscrizione viva,
payload interpretato, pannello che disegna. Fuori resta solo Home Assistant,
che da lì non si potrebbe provare comunque.

Le risposte sono tre, e ognuna dice una cosa diversa:

| Che cosa leggi | Che cosa vuol dire |
|---|---|
| *…pubblicata su `dmd/notifica` e tornata indietro dal broker* | Tutto a posto fino al pannello. Se le notifiche di Home Assistant non arrivano, il problema è di là |
| *Il broker non è raggiungibile: consegnata direttamente…* | Il pannello la mostra, ma niente che venga da fuori arriverà. Vai alla sezione MQTT nella pagina *Rete* |
| *Il servizio Notifiche è spento* | Accendilo, altrimenti la prova non ha niente da mostrare |

Due risposte diverse per i primi due casi sono voluto: dicono **quale metà
della catena funziona**, che è l'unica cosa che si voglia sapere premendo un
pulsante di prova. Una sola risposta buona per entrambi nasconderebbe proprio
il guasto che si sta cercando.

> Il livello `allarme` si può scegliere anche qui, apposta: è l'unico che
> interrompe una partita, ed è esattamente quello che vuoi verificare prima
> di affidargli l'allarme di casa.

# 7. Le automazioni

Nel file ce ne sono cinque: la porta, la lavatrice, il rientro, l'allarme
intrusione, il fumo. Si incollano da *Impostazioni* → *Automazioni e scene* →
*Crea automazione* → *Modifica in YAML*, cambiando gli `entity_id` con i tuoi.

Una riga merita di essere spiegata, perché sembra pedanteria e non lo è:

```yaml
not_from: ["unknown", "unavailable"]
not_to:   ["unknown", "unavailable"]
```

Senza, **ogni riavvio di Home Assistant** fa passare i sensori da
`unavailable` al loro stato vero, e il DMD annuncia in fila che si sono aperte
tutte le porte di casa. È il primo modo in cui una notifica in MQTT diventa
fastidiosa invece che utile.

Vale anche, e soprattutto, per l'allarme: se la centrale era in stato
`triggered` quando HA si è riavviato, senza quella riga il pannello urla
*INTRUSIONE* in rosso per un minuto mentre non sta succedendo niente.

Per i sensori numerici — la lavatrice — la trappola è la stessa in altra
forma, e si chiude con una condizione sullo stato di partenza:

```yaml
condition:
  - condition: template
    value_template: "{{ trigger.from_state.state | float(0) > 20 }}"
```

# 8. Il silenziatore notturno

L'ultima automazione del file spegne l'helper alle 23:30 e lo riaccende alle
7:00. Di notte il pannello è già quasi spento dalle fasce orarie, ma un
`avviso` arancione che scorre alle tre di notte sveglia lo stesso chi passa in
corridoio.

Gli allarmi passano comunque: è scritto nella condizione dello script, non
nell'automazione, così vale sempre e non dipende da chi chiama.

# 9. Quando non funziona

La riga di stato nella pagina *Servizi* dice quasi sempre dove si è rotto:

```
in ascolto su dmd/notifica — 12 mostrate, 0 scartate
```

| Cosa vedi | Cosa vuol dire |
|---|---|
| Il servizio è spento | Accendilo in *Servizi* → *Notifiche* |
| `non connesso` nella sezione MQTT (pagina *Rete*) | Il problema è prima: broker, indirizzo, password |
| `in ascolto`, `0 mostrate`, `0 scartate` | Il messaggio non arriva: topic diverso fra HA e DMD, oppure l'automazione non è partita |
| `0 mostrate`, **`n` scartate** | I messaggi arrivano ma sono malformati: la riga dice anche l'ultimo errore |
| `ultimo messaggio scartato: manca il testo` | Un template di HA ha reso una stringa vuota |
| `ultimo messaggio scartato: JSON non valido` | Un errore di battitura nel payload dello script |
| Le notifiche compaiono ma mai durante una partita | È giusto così: solo `allarme` interrompe |

Il primo posto dove guardare è il **pulsante di prova** nel riquadro
*Notifiche* (vedi [6.5](#65-il-pulsante-di-prova-sul-dmd)): in un clic dice se
la metà sul DMD funziona, e quindi se ha senso cercare il guasto in Home
Assistant.

La prova secca, che salta del tutto Home Assistant e dice se il guasto è di
qua o di là:

```
mosquitto_pub -h INDIRIZZO -u utente -P password -t dmd/notifica -m "prova"
```

Se questo si vede e le automazioni no, il guasto è in Home Assistant. Se non
si vede nemmeno questo, è sul DMD o sul broker.

# 10. Quello che non fa, e perché

**Niente immagini né icone.** Il pannello è 256×64 con pixel grossi come
lenticchie: un'icona leggibile mangerebbe un quarto della larghezza per dire
meno di una parola.

**Niente coda persistente.** Le notifiche non sopravvivono a un riavvio del
DMD, e la coda si ferma a venti: un'automazione impazzita che pubblica dieci
volte al secondo non deve riempire la memoria del Raspberry. Quando è piena si
butta la più vecchia — una notifica di mezz'ora fa non interessa più a
nessuno.

**Niente risposta verso Home Assistant.** Il DMD non dice se una notifica è
stata vista. Non saprebbe come: non c'è nessuno che prema un tasto.

**Niente regole sul DMD.** Nessun filtro, nessun orario, nessun «non
disturbare» configurabile di qua. Sta tutto nello script, di là, per la
ragione del capitolo 1.

# 11. Riassunto

| | |
|---|---|
| Topic | `dmd/notifica` |
| Payload | JSON con `testo`, `livello`, `secondi` — oppure testo semplice |
| Livelli | `info`, `avviso`, `allarme` |
| Interrompe una partita | solo `allarme` |
| Servizio | *Servizi* → *Notifiche*, nasce spento |
| File pronto | [`ha/dmd_notifica.yaml`](ha/dmd_notifica.yaml) |
| Entità in HA | `script.dmd_notifica`, `input_boolean.dmd_notifiche` |
