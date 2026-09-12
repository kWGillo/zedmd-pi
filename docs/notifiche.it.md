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

1. **MQTT configurato e connesso** sul DMD. Pagina *Musica* → sezione MQTT:
   indirizzo del broker, utente, password. Se la riga dice `non connesso`, è
   lì che si comincia — il resto di questa pagina non può funzionare.
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

# 5. Lo script in Home Assistant

Il file pronto è [`ha/dmd_notifica.yaml`](ha/dmd_notifica.yaml): contiene lo
script, cinque automazioni d'esempio e l'helper. Qui sotto c'è il perché e la
procedura.

## 5.1 Perché uno script e non quindici automazioni

Ogni automazione potrebbe pubblicare il suo JSON da sola. Ma il giorno che
cambi il topic, o vuoi che di notte non parli, o aggiungi il colore, con lo
script cambi **un posto solo**. Senza, cambi quindici automazioni e ne
dimentichi tre — e le tre dimenticate non danno errore, semplicemente non
compaiono più.

## 5.2 L'interruttore (facoltativo, consigliato)

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

## 5.3 Lo script

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

## 5.4 La prova

*Strumenti per sviluppatori* → *Azioni* → `script.dmd_notifica`, campo
**testo**: `Ciao dal soggiorno` → *Esegui azione*.

Se non compare niente, vedi il [capitolo 8](#8-quando-non-funziona).

# 6. Le automazioni

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

# 7. Il silenziatore notturno

L'ultima automazione del file spegne l'helper alle 23:30 e lo riaccende alle
7:00. Di notte il pannello è già quasi spento dalle fasce orarie, ma un
`avviso` arancione che scorre alle tre di notte sveglia lo stesso chi passa in
corridoio.

Gli allarmi passano comunque: è scritto nella condizione dello script, non
nell'automazione, così vale sempre e non dipende da chi chiama.

# 8. Quando non funziona

La riga di stato nella pagina *Servizi* dice quasi sempre dove si è rotto:

```
in ascolto su dmd/notifica — 12 mostrate, 0 scartate
```

| Cosa vedi | Cosa vuol dire |
|---|---|
| Il servizio è spento | Accendilo in *Servizi* → *Notifiche* |
| `non connesso` nella sezione MQTT | Il problema è prima: broker, indirizzo, password |
| `in ascolto`, `0 mostrate`, `0 scartate` | Il messaggio non arriva: topic diverso fra HA e DMD, oppure l'automazione non è partita |
| `0 mostrate`, **`n` scartate** | I messaggi arrivano ma sono malformati: la riga dice anche l'ultimo errore |
| `ultimo messaggio scartato: manca il testo` | Un template di HA ha reso una stringa vuota |
| `ultimo messaggio scartato: JSON non valido` | Un errore di battitura nel payload dello script |
| Le notifiche compaiono ma mai durante una partita | È giusto così: solo `allarme` interrompe |

La prova secca, che salta del tutto Home Assistant e dice se il guasto è di
qua o di là:

```
mosquitto_pub -h INDIRIZZO -u utente -P password -t dmd/notifica -m "prova"
```

Se questo si vede e le automazioni no, il guasto è in Home Assistant. Se non
si vede nemmeno questo, è sul DMD o sul broker.

# 9. Quello che non fa, e perché

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

# 10. Riassunto

| | |
|---|---|
| Topic | `dmd/notifica` |
| Payload | JSON con `testo`, `livello`, `secondi` — oppure testo semplice |
| Livelli | `info`, `avviso`, `allarme` |
| Interrompe una partita | solo `allarme` |
| Servizio | *Servizi* → *Notifiche*, nasce spento |
| File pronto | [`ha/dmd_notifica.yaml`](ha/dmd_notifica.yaml) |
| Entità in HA | `script.dmd_notifica`, `input_boolean.dmd_notifiche` |
