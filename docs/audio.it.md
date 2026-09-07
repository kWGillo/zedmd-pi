---
title: "L'audio del DMD"
subtitle: "Una scheda USB, un avviso per servizio, gli effetti dei giochi e la colonna sonora di Doom"
---

# 1. Perché serve una scheda USB

Non è un ripiego, ed è la prima cosa da chiarire perché sembra una scelta
discutibile e invece non è una scelta.

La libreria che pilota la matrice si prende il **blocco PWM** del Raspberry.
L'audio analogico interno — il jack, e l'uscita `bcm2835` che compare come
scheda 0 — usa lo stesso blocco. Sono alternativi per costruzione: infatti
l'installazione del DMD spegne il modulo `snd_bcm2835`, e senza spegnerlo la
libreria della matrice si rifiuta di partire.

Quindi: o suona il jack, o si accende il pannello. Non entrambi.

Una scheda audio USB è un dispositivo completamente diverso. Parla con
`snd_usb_audio`, non tocca il PWM, e convive col pannello senza nemmeno
saperlo. È **l'unico** modo di avere suono su questa macchina.

Vanno bene le chiavette da pochi euro con chip C-Media o simili: quello che
serve è un'uscita stereo. Si infila e basta — il kernel la riconosce da sola,
e compare come scheda 1 (o 2, se ce n'è già una).

> Per verificarlo: `cat /proc/asound/cards`. Se la chiavetta c'è, è in
> quell'elenco. È lo stesso file che legge il DMD.

# 2. Chi suona

`ffmpeg`, che sul DMD c'è già dalla versione 1.1 — lo usa il Media Player per
i video.

Fra le sue uscite ha il muxer `alsa`, quindi:

```
ffmpeg -i suono.mp3 -filter:a volume=0.6 -f alsa plughw:1,0
```

riproduce wav e mp3 su una scheda scelta, col volume voluto, **senza
installare niente di nuovo**. `aplay` non legge gli mp3 e non regola il
volume; `ffplay` si tira dietro SDL. Il ferro del mestiere lo avevamo già in
casa.

## `plughw`, non `hw`

Dettaglio piccolo e decisivo. `hw:1,0` è la scheda nuda: accetta solo la
frequenza e il formato che sa fare. `plughw:1,0` è la stessa scheda con un
convertitore davanti.

Un wav a 44 100 Hz stereo su una chiavetta che vuole 48 000 Hz mono, con `hw`,
non parte e basta — e il motivo non si scopre in fretta. Con `plughw` esce, e
la conversione la fa ALSA. Il DMD usa sempre `plughw`.

# 3. Le tre cose, che sono davvero tre

Le impostazioni dell'audio sono divise in tre perché rispondono a tre domande
diverse, non per gusto della simmetria.

| | Cosa suona | Da dove viene il file |
|---|---|---|
| **Avvisi dei servizi** | quando una sorgente prende il pannello | libreria media, scelto da te |
| **Effetti dei giochi** | Invaders e Breakout | `suoni/`, dentro il programma |
| **Audio di Doom** | la colonna sonora del gioco | i WAD, come nel gioco vero |

## 3.1 Gli avvisi dei servizi

Il momento è **quello della notifica**: l'istante in cui una sorgente vince
l'arbitrato e prende il pannello. Non mentre ci resta, non a intervalli. Una
volta, quando compare.

Per ogni servizio, nella pagina **Servizi**, c'è un menu con i file `wav` e
`mp3` presenti nella libreria media, e un pulsante **Ascolta** per sentirlo
prima di sceglierlo. «Nessun suono» toglie l'assegnazione.

I servizi che possono avere un avviso sono otto:

`zedmd` · `nowplaying` · `birthdays` · `air_radar` · `clock` · `scadenze` ·
`calendario` · `webcam`

**Tre non ce l'hanno, e non è una dimenticanza.** Media Player e Rolling
Banner non annunciano niente: compaiono a intervalli per decorazione, e un
campanello a ogni foto sarebbe un metronomo in soggiorno. I rifiuti non
compaiono per un motivo diverso: non sono un servizio. Li disegna l'orologio,
dentro la sua colonna, e non prendono mai il pannello per conto proprio.

Un avviso viene **troncato a 15 secondi**. Un file lungo scelto per sbaglio
terrebbe muto tutto il resto per minuti.

### Un suono per volta

Se un avviso parte mentre un altro sta ancora suonando, il nuovo si
**scarta**. Non va in coda e non interrompe quello in corso.

È una decisione, non una limitazione tecnica. Un avviso in coda si farebbe
sentire tre secondi dopo, riferito a una cosa che dal pannello è già sparita:
peggio che non sentirlo. E interromperne uno a metà è un singhiozzo.

## 3.2 Gli effetti dei giochi

Invaders e Breakout hanno dodici effetti a onda quadra, 22 050 Hz mono, scritti
per loro. Stanno in `/opt/dmd/suoni/` — **dentro il programma, non nella
libreria media**.

La differenza conta: sono parte del gioco come lo sono i suoi colori.
Mescolarli ai tuoi contenuti vorrebbe dire che cancellandone uno per sbaglio
il gioco diventa muto, e che comparirebbero nel menu degli avvisi come se
fossero roba da scegliere.

| Effetto | Quando |
|---|---|
| `sparo` | Invaders: il colpo del cannone |
| `colpito` | Invaders: un alieno esplode |
| `passo1`…`passo4` | Invaders: le quattro note del passo della schiera |
| `livello` | Invaders: schiera ripulita, ne arriva un'altra |
| `mattone` | Breakout: un mattone si rompe |
| `racchetta` | Breakout: rimbalzo sulla racchetta |
| `muro` | Breakout: rimbalzo sulle pareti |
| `persa` | entrambi: vita persa |
| `record` | entrambi: primato personale battuto |

Le quattro note del passo sono la cosa più fedele all'originale del 1978: è il
battito del gioco, e accelera insieme alla schiera. Metà della tensione stava
lì.

Si spengono tutti insieme dalla levetta **Effetti dei giochi** in
Impostazioni.

## 3.3 Doom

Doom suona con la sua musica e i suoi suoni, presi dal WAD, esattamente come
nel gioco originale.

Fino alla 5.1 il DMD lo lanciava sempre con `-nosound -nomusic`. Ora quei due
argomenti compaiono solo se l'audio di Doom è spento.

La scheda gliela passiamo dall'ambiente, non dalla riga di comando:

```
SDL_AUDIODRIVER=alsa
AUDIODEV=plughw:1,0
```

SDL sceglie il dispositivo da `AUDIODEV`; senza `SDL_AUDIODRIVER=alsa`
proverebbe prima pulseaudio, che su un'immagine senza sessione grafica non
c'è, e Doom partirebbe muto senza spiegare perché.

### Perché ha una levetta tutta sua

Perché è l'unico suono **continuo** del sistema, e quindi l'unico che costa
qualcosa.

Riprodurre audio è CPU e traffico USB, cioè la stessa moneta con cui si pagano
le righe chiare sul pannello — il disturbo che la pagina Taratura misura. Un
avviso di mezzo secondo non si misura nemmeno. Una colonna sonora che va per
tutta la partita sì. Se durante Doom noti disturbi che senza non ci sono, la
levetta è lì per questo.

# 4. Il DMD come cassa AirPlay

Questo sta nella pagina **Now Playing**, non in Impostazioni, perché è una
proprietà della musica e non del suono in generale.

## Che cosa cambia

`setup_nowplaying.sh` configura shairport-sync per scrivere l'audio nella
scheda **fittizia** del kernel (`snd_dummy`). Non era un capriccio: senza una
scheda audio l'audio andava buttato da qualche parte, e serviva un dispositivo
con un orologio vero — `/dev/null` e il plugin `null` di ALSA non limitano il
ritmo, e shairport-sync perderebbe il riferimento temporale.

Dei brani il DMD prendeva quindi solo i metadati: titolo, artista,
avanzamento. Il suono lo buttava.

Con una scheda USB collegata quella scelta non ha più motivo di esistere. La
spunta **«La musica esce dalla scheda audio»** sposta l'uscita di
shairport-sync sulla scheda vera, e il pannello diventa una cassa AirPlay a
tutti gli effetti: qualunque cosa parta da un iPhone, un iPad o un Mac —
Apple Music, Spotify, YouTube, un video — suona qui.

Meccanicamente è **una riga** di `/etc/shairport-sync.conf` più un riavvio del
servizio.

## Solo AirPlay

Le tre sorgenti di Now Playing non sono la stessa cosa, e qui la differenza
diventa concreta:

| Sorgente | Che cos'è | Si può far uscire? |
|---|---|---|
| **airplay** | un flusso audio che arriva davvero qui | **sì** |
| **spotify** | l'API web dice cosa suona *su un altro dispositivo* | no |
| **external** | metadati di un'automazione | no |

Spotify sta raccontando una cosa che sta succedendo altrove: non c'è nessun
audio da dirottare. Per fare del DMD anche un altoparlante Spotify Connect
servirebbe `librespot`, che è un altro programma, un'altra installazione e
un'altra storia.

## La prova prima di scrivere

Accendendo l'interruttore senti un tono breve. Non è un vezzo: è la verifica.

shairport-sync riceve il dispositivo in forma **esclusiva** (`hw:1,0`), non
attraverso il convertitore (`plughw:1,0`) che usiamo per gli avvisi. Sembra
un'incoerenza e non lo è: `plughw` è quello che vogliamo per un mp3 qualunque,
mentre shairport-sync la frequenza la gestisce da sé e la scheda vuole vederla
com'è — con `plughw` gli si nasconde ciò che sa fare davvero, e la
sincronizzazione ne risente.

Ma `hw:` può rifiutare. Quindi prima di scrivere la configurazione il DMD
suona un tono nel formato esatto di AirPlay — **44 100 Hz, stereo, 16 bit** —
su quel dispositivo. Se la scheda non lo regge, **non si tocca niente** e il
motivo compare in pagina. Meglio un interruttore che non scatta di una cassa
AirPlay che non suona più e nessuno sa perché.

Della configurazione precedente resta sempre una copia `.bak` accanto, e viene
cambiata **una sola riga**: nello stesso file c'è la password del broker MQTT,
e riscriverlo da capo vorrebbe dire perderla o maneggiarla.

## Chi tiene la scheda mentre suona la musica

Una scheda ALSA aperta in `hw:` sta in mano a un programma alla volta. Mentre
c'è un brano in corso, quel programma è shairport-sync.

Quindi **durante la musica gli avvisi dei servizi tacciono**, e non ci provano
nemmeno: il DMD lo sa, perché è la stessa informazione che sta disegnando sul
pannello. Le notifiche si vedono lo stesso — compleanni, scadenze, aerei — solo
non si sentono.

È la scelta giusta anche a prescindere dal vincolo tecnico: un campanello
sopra la musica non lo vuole nessuno, e se stai ascoltando qualcosa, quella
cosa ha la precedenza.

**Doom**, per la stessa ragione, parte muto se lo si lancia mentre la musica
va. Deciso da noi, invece di lasciare che SDL fallisca l'apertura della scheda
con qualche secondo di errori proprio all'inizio della partita. Se vuoi
l'audio del gioco, ferma la musica e ricomincia la partita.

## Spegnendolo

Si torna alla scheda fittizia. Now Playing continua a mostrare i brani
esattamente come prima: semplicemente non li suona.

# 5. La pagina Impostazioni

Il riquadro **Audio** ha quattro comandi.

**Suono acceso** — l'interruttore generale. Spento, non suona niente: né
avvisi, né giochi, né Doom.

**Uscita audio** — le schede viste dal kernel, lette da `/proc/asound/cards`.
Lasciando *«L'ultima collegata»* il DMD prende l'ultima della lista: con una
chiavetta USB
appena infilata è quasi sempre quella giusta, visto che la scheda 0 è l'audio
interno che con questo pannello non si può usare comunque.

Se la scheda che avevi scelto viene staccata, il DMD **non ripiega su
un'altra**: resta muto e lo dice in pagina. Suonare dall'altoparlante
sbagliato senza avvisare è peggio che non suonare, perché non si capisce cosa
stia succedendo.

**Volume (0-100)** — non tocca il mixer di sistema: è un filtro `volume=`
applicato da ffmpeg al momento della riproduzione, quindi non cambia niente
per gli altri programmi e non ha bisogno di `alsamixer`.

**Prova il suono** — suona un effetto sulla scheda scelta. Funziona **anche a
suono spento**, apposta: serve proprio a capire se l'audio funziona *prima* di
accenderlo.

Accanto ci sono le due levette **Effetti dei giochi (Breakout, Invaders)** e
**Audio di Doom**, che sono i § 3.2 e § 3.3.

Se ffmpeg fallisce — scheda staccata a metà, file illeggibile — l'ultima riga
del suo errore compare sotto il riquadro. Il silenzio non resta mai senza
spiegazione.

# 6. Cosa non fa

Vale la pena elencarlo, perché sono assenze volute.

- **Non mixa.** Un suono per volta, il secondo si scarta (§ 3.1).
- **Non regola il volume di sistema.** Il filtro di ffmpeg vale per il DMD e
  basta.
- **Non tiene una libreria di suoni propria** per gli avvisi: i file sono i
  tuoi, nella cartella media, gestiti come le foto e i video — da SMB, o
  dall'upload della pagina Media.
- **Non annuncia i rifiuti, il Media Player e il Rolling Banner** (§ 3.1).
- **Non parla.** Nessuna sintesi vocale: sarebbe un'altra dipendenza e un'altra
  storia.

# 7. Se non si sente niente

In ordine, dal più probabile.

1. **La scheda c'è?** `cat /proc/asound/cards`. Se la chiavetta non compare,
   il problema è prima del DMD.
2. **È selezionata?** Impostazioni → Audio → Uscita. Se la voce scelta non
   esiste più, il riquadro lo dice.
3. **Il volume è a zero?** Sia quello del DMD, sia quello della scheda:
   `alsamixer -c 1` e alza il canale principale, che su molte chiavette parte
   basso o muto. È l'unico posto dove serve `alsa-utils`.
4. **La prova suona?** Se sì, il problema è nell'assegnazione dei file: guarda
   il menu del servizio nella pagina Servizi.
5. **Se ffmpeg si lamenta**, il motivo è sotto il riquadro Audio. `Device or
   resource busy` vuol dire che un altro programma tiene la scheda; su questa
   macchina l'unico candidato è Doom.

Da riga di comando, per escludere il DMD dal ragionamento:

```
ffmpeg -f lavfi -i "sine=frequency=440:duration=1" -f alsa plughw:1,0
```

Se questo non suona, non è il DMD.
