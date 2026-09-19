---
title: "OnAir — l'automazione in Home Assistant"
subtitle: "Collegare il sensore della porta al pannello, passo per passo, e i tre errori che ci sono costati una serata"
---

# 1. Chi fa cosa

Questa è la parte che non sta sul DMD, e conviene dirlo subito perché è il
malinteso da cui nasce tutto il resto.

**Il DMD non legge il tuo sensore.** Non sa nemmeno che esista una porta. Sa
una cosa sola: se è in onda o no, e te lo chiede con un interruttore.

**Il sensore lo guarda Home Assistant**, che lo guarda già per conto suo, e
riporta il risultato sull'interruttore del DMD con un'automazione di poche
righe. Quell'automazione la crei tu, una volta.

```
 sensore porta  ──►  automazione HA  ──►  switch «In onda»  ──►  pannello
   (Zigbee,           tre righe            (MQTT, creato         ON AIR
    Z-Wave,                                 dal DMD)
    quel che è)
```

Perché così e non col DMD che legge il sensore: il giorno che vorrai far
scattare l'ON AIR da un pulsante sulla scrivania, da un orario o dal mixer
audio, cambi l'automazione e il DMD non se ne accorge. E per leggere un
sensore Zigbee il DMD dovrebbe parlare con Home Assistant, cioè avere un
token, cioè una seconda password da custodire per fare una cosa che Home
Assistant fa già.

> **Prima di tutto**, accendi il servizio: pagina *Servizi* → **OnAir**. Nasce
> spento, come le notifiche. Finché è spento il pannello ignora l'interruttore,
> e passeresti la serata a cercare il guasto dalla parte sbagliata.

# 2. I due nomi da leggere

Questo capitolo è corto ed è il più importante del documento. **I due
identificativi non si indovinano: si leggono.**

## 2.1 L'interruttore del DMD

*Impostazioni → Dispositivi e servizi → Entità*, e nella casella di ricerca
scrivi **`onda`**.

Non scrivere «onair». Quella pagina cerca nel **nome** dell'entità, non
nell'identificativo, e il nome è «In onda». Cercando «onair» non esce niente e
sembra che l'entità non ci sia.

Clicca la riga, apri le impostazioni (icona a forma di ingranaggio) e copia
l'**ID entità**. Sarà qualcosa come:

```
switch.dmd_onair_diretta
```

oppure

```
switch.dmd_controller_in_onda
```

**Non è un refuso: possono essere diversi, e non lo decidi tu.** Il DMD
propone `dmd_onair_diretta`; Home Assistant a volte accetta la proposta e a
volte se lo costruisce da solo unendo il nome del dispositivo MQTT («DMD
Controller») al nome dell'entità («In onda»). Dipende da come e quando
l'entità è stata registrata la prima volta, ed è una decisione sua.

> **Il DMD non può dirtelo.** La sua pagina OnAir mostra il nome che
> *propone*, e lo dice chiaramente. Quello che Home Assistant ha poi deciso
> lo sa solo Home Assistant: non lo ripubblica da nessuna parte, quindi
> l'unico posto dove leggerlo è questa pagina.

## 2.2 Il tuo sensore porta

Stessa pagina, cerca il sensore per nome e apri le sue impostazioni. Sarà
qualcosa come `binary_sensor.contact_sensor_porta`.

Mentre sei lì, guarda anche **che valore ha con la porta chiusa**. Un sensore
con `device_class: door` segue questa convenzione:

| Stato | Porta |
|---|---|
| `on` | **aperta** |
| `off` | **chiusa** |

Sembra al contrario ed è al contrario di come uno se lo immagina: per Home
Assistant `on` vuol dire «il contatto segnala qualcosa», e quel qualcosa è
l'apertura. Quindi **in onda corrisponde a `off`**. Se il tuo sensore è
cablato al rovescio, nel file c'è una riga apposta da cambiare.

# 3. Creare l'automazione

1. *Impostazioni → Automazioni e scene → **Crea automazione***
2. *Crea una nuova automazione* (parti dal vuoto)
3. In alto a destra, i **tre puntini** → **Modifica in YAML**
4. Cancella quello che c'è e incolla il blocco del capitolo 4
5. Correggi le **tre righe marcate** `<<< DA CORREGGERE`
6. **Salva**, e dai un nome

Il file pronto, con tutti i commenti, è
[`ha/dmd_onair.yaml`](ha/dmd_onair.yaml).

# 4. Lo YAML

```yaml
alias: DMD - ON AIR dal sensore della porta
description: >-
  Rispecchia il sensore della porta sull'interruttore In onda del DMD.
  Porta chiusa = in onda.
mode: queued
max: 5

variables:
  sensore: binary_sensor.porta_studio            # <<< DA CORREGGERE (1 di 2)
  interruttore: switch.dmd_onair_diretta         # <<< DA CORREGGERE
  # Quale stato del sensore vuol dire «porta chiusa».
  chiusa: "off"

triggers:
  # Questo entity_id deve essere lo stesso di `sensore` qui sopra.
  - trigger: state
    entity_id: binary_sensor.porta_studio        # <<< DA CORREGGERE (2 di 2)
    not_from:
      - unknown

  - trigger: mqtt
    topic: dmd/availability
    payload: online
    id: riallinea

  - trigger: homeassistant
    event: start
    id: riallinea

conditions: []

actions:
  - delay: >-
      {{ 3 if (trigger.id | default('')) == 'riallinea' else 0 }}

  - choose:
      - conditions:
          - condition: template
            value_template: "{{ has_value(sensore) }}"
        sequence:
          - action: >-
              {{ 'switch.turn_on' if is_state(sensore, chiusa)
                 else 'switch.turn_off' }}
            target:
              entity_id: "{{ interruttore }}"
    default:
      - action: system_log.write
        data:
          level: warning
          logger: dmd.onair
          message: >-
            OnAir: il sensore {{ sensore }} non ha un valore leggibile
            (stato: {{ states(sensore) }}). Controlla che l'entity_id sia
            giusto e che sia lo stesso scritto nell'innesco.
```

## 4.1 Perché il sensore compare due volte

Perché un **innesco non accetta variabili**: Home Assistant deve sapere quale
entità sorvegliare prima ancora di eseguire l'automazione, quindi lì il nome
va scritto per esteso. È l'unica ripetizione del file, ed è marcata apposta.

È anche l'errore più facile da fare, e lo sappiamo perché l'abbiamo fatto:
vedi il capitolo 6.

## 4.2 Perché tre inneschi

**Il sensore**, ovviamente.

**Il DMD che torna disponibile.** Quando il Raspberry riparte, il DMD pubblica
`online` su `dmd/availability`. Quello è il momento esatto per ridirgli com'è
messa la porta: senza, un riavvio a metà diretta lascerebbe il pannello a
credere quello che sapeva prima. Non serve sorvegliare niente, lo annuncia lui.

**Il riavvio di Home Assistant**, per lo stesso motivo dall'altro lato.

L'azione **non guarda quale innesco è scattato**: rilegge sempre lo stato vero
del sensore e lo riafferma. Così è ripetibile senza danni e un innesco perso si
corregge al successivo. Il ritardo di tre secondi vale solo per il
riallineamento, perché lì il DMD ha appena detto «online» e deve finire di
iscriversi ai propri topic.

## 4.3 Perché un ramo scrive nel registro

Se il sensore non ha un valore leggibile, l'automazione **non spegne niente** e
lascia una riga nel registro di Home Assistant con il motivo.

Copre due casi che senza questo ramo finivano tutti e due nel silenzio:

- il sensore **scritto male**, quindi inesistente;
- il sensore **con la pila scarica**, quindi `unavailable`.

Prima, in tutti e due i casi `is_state()` restituiva falso e il template
sceglieva `switch.turn_off`: l'automazione spegneva, sempre, senza un errore.

# 5. Provare che funziona

Tre prove in ordine. Ognuna esclude un pezzo della catena, così quando
qualcosa non va sai subito dove guardare.

**1. Il pannello, senza nulla intorno.** Pagina *OnAir* del DMD → pulsante
**«Vai in onda»**. Se compare ON AIR, il DMD è a posto.

**2. L'interruttore, senza automazione.** In Home Assistant apri «In onda» e
premilo. Se il pannello reagisce, MQTT e discovery funzionano.

**3. La porta.** Chiudila. Se il pannello reagisce, hai finito.

Se la 2 funziona e la 3 no, il problema è nell'automazione — e allora
*Impostazioni → Automazioni*, apri la tua e guarda **«Ultima attivazione»**:

- dice **«Mai»** → l'automazione non scatta: l'innesco punta al sensore
  sbagliato, o è disattivata;
- dice **un orario recente** → scatta ma fa la cosa sbagliata: guarda il
  template (capitolo 6), e apri le **Tracce** in alto a destra, che mostrano
  passo per passo cosa ha deciso.

# 6. I tre errori che ci sono costati una serata

Non sono ipotesi: sono successi tutti e tre, in fila, la prima volta che
abbiamo collegato questa cosa.

## 6.1 Il sensore cambiato in un posto solo

Il più insidioso. L'automazione scattava — «ultima attivazione: 33 secondi fa»
— e non succedeva niente.

Il motivo: l'innesco era stato corretto con il sensore giusto, il **template**
no, ed era rimasto quello dell'esempio. `is_state()` su un'entità inesistente
è falso, il falso porta a `switch.turn_off`, e quindi ogni apertura **e** ogni
chiusura spegnevano. Nessun errore da nessuna parte.

Adesso il file lo dice in tre punti e, se ricapita, la riga nel registro lo
spiega. Ma resta il controllo da fare per primo: **il nome del sensore deve
comparire identico due volte.**

## 6.2 Cercare «onair» invece di «onda»

L'entità c'era dall'inizio. Cercandola per «onair» non usciva, perché quella
pagina cerca nel nome e il nome è «In onda». Abbiamo cancellato e ricreato
dichiarazioni MQTT per un'ora, inseguendo un'entità che non era mai mancata.

## 6.3 Dare per scontato l'identificativo

La prima versione di questa guida scriveva `switch.dmd_onair_diretta` come se
fosse una certezza. Su quell'impianto Home Assistant l'aveva chiamata
`switch.dmd_controller_in_onda`, e l'automazione puntava a un'entità che non
esisteva.

È il motivo per cui il capitolo 2 dice **leggere, non indovinare**, e per cui
la pagina OnAir del DMD adesso scrive accanto ai due nomi che sono quelli
*proposti*, e che quello buono va letto in Home Assistant.

# 7. Quando non funziona

| Sintomo | Dove guardare |
|---|---|
| La voce OnAir non c'è nel menu del DMD | Versione precedente alla 9.8 |
| «Vai in onda» non fa niente | Servizio OnAir spento: *Servizi* → OnAir |
| L'entità non si trova in HA | Cerca `onda`, non `onair` |
| L'entità non c'è davvero | Pagina *Rete* del DMD → ridichiara le entità |
| L'automazione dice «Mai» | Innesco sul sensore sbagliato, o disattivata |
| Scatta ma spegne sempre | Il sensore nel template (§ 6.1) |
| Funziona al contrario | Scambia `chiusa: "off"` con `"on"` |
| Resta accesa a porta aperta | Spegnila dalla pagina OnAir, poi guarda le Tracce |

Per una prova che salta del tutto Home Assistant, dal Raspberry:

```bash
sudo python3 -c "
import json, paho.mqtt.client as m
c = json.load(open('/etc/dmd/config.json'))['mqtt']
k = m.Client(m.CallbackAPIVersion.VERSION2, client_id='prova-onair')
if c.get('username'): k.username_pw_set(c['username'], c.get('password') or None)
k.connect(c['host'], int(c.get('port', 1883)), 10)
k.loop_start()
k.publish(c['base_topic'] + '/service/onair_diretta/set', 'ON', qos=1).wait_for_publish()
k.loop_stop(); print('pubblicato')
"
```

Legge indirizzo, utente e password dalla configurazione del DMD, così non
finiscono nella cronologia della shell. Con `'OFF'` si spegne. Se questo
funziona, broker e DMD sono a posto e il problema è tutto in Home Assistant.

# 8. Riassunto

| | |
|---|---|
| Chi legge il sensore | Home Assistant, non il DMD |
| Entità da comandare | quella chiamata **In onda** — leggi l'ID, non indovinarlo |
| Dove si cerca | *Entità*, cercando `onda` |
| Righe da correggere | tre, marcate `<<< DA CORREGGERE` |
| Il sensore compare | **due volte**, e devono combaciare |
| Porta chiusa | di norma `off` |
| File pronto | [`ha/dmd_onair.yaml`](ha/dmd_onair.yaml) |
| Il servizio | *Servizi* → OnAir, nasce spento |
