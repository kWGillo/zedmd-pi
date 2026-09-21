# I manuali

Questa cartella contiene la documentazione del progetto, in Markdown e in PDF
già impaginato. I `.md` si leggono direttamente su GitHub; i `.pdf` sono
pensati per essere stampati o letti offline.

La descrizione del progetto e le istruzioni di installazione stanno nel
[README principale](../README.md), un livello sopra.

> **Perché questo file è soltanto un indice.** Fino alla 5.6.1 qui c'era una
> copia della descrizione del progetto, ferma alla versione **1.10**: quaranta
> versioni indietro, con un elenco di servizi in cui mancava metà di quello che
> il DMD sa fare, e una lunga sezione sul radar nel frattempo cambiata altrove.
> Un documento che ripete un altro documento invecchia, e invecchia in
> silenzio. Qui adesso c'è solo l'elenco di cosa leggere.

## Per cominciare

| Documento | Di cosa parla |
|---|---|
| [`manuale-completo.it.md`](manuale-completo.it.md) · [PDF](DMD_manuale_completo.pdf) | Dal Raspberry nudo al pannello acceso: hardware, cablaggio, alimentazione, installazione, diagnostica, risoluzione problemi |
| [`taratura.it.md`](taratura.it.md) · [PDF](DMD_taratura.pdf) | Far sparire righe chiare e sfarfallio: profili del pannello, taratura automatica, registri del driver |
| [`rete.it.md`](rete.it.md) · [PDF](DMD_rete.pdf) | Configurare il wifi dalla pagina web invece che con monitor e tastiera |
| [`aggiornamenti.it.md`](aggiornamenti.it.md) · [PDF](DMD_aggiornamenti.pdf) | Perché il pannello non si aggiorna da solo, come avvisa che dovrebbe, e cosa succede quando un aggiornamento va storto |

## Le funzioni

| Documento | Di cosa parla |
|---|---|
| [`zedmd-wifi.it.md`](zedmd-wifi.it.md) · [PDF](DMD_zedmd_wifi.pdf) | Il protocollo ZeDMD-WiFi e come collegare Batocera, VPX, dmd-extensions |
| [`now-playing.it.md`](now-playing.it.md) · [PDF](DMD_now_playing.pdf) | Il brano in ascolto sul pannello: AirPlay 2, Spotify, MQTT, Home Assistant |
| [`audio.it.md`](audio.it.md) · [PDF](DMD_audio.pdf) | La scheda audio USB, gli avvisi dei servizi, gli effetti dei giochi, l'audio di Doom e del Game Boy, il DMD come cassa AirPlay |
| [`calendario.it.md`](calendario.it.md) · [PDF](DMD_calendario.pdf) | Google Calendar: collegamento, permessi, cosa finisce sul pannello |
| [`telecamera.it.md`](telecamera.it.md) · [PDF](DMD_telecamera.pdf) | FunCAM: la webcam sul pannello con pochi colori, e il pulsante fisico sulla Bonnet |
| [`satelliti.it.md`](satelliti.it.md) · [PDF](DMD_satelliti.pdf) | I passaggi della Stazione Spaziale: preavviso, l'arco del cielo, lo spegnimento in ombra, il registro |
| [`notifiche.it.md`](notifiche.it.md) · [PDF](DMD_notifiche.pdf) | Le notifiche da Home Assistant: il topic, i tre livelli, lo script e le automazioni pronte |
| [`worldtime.it.md`](worldtime.it.md) · [PDF](DMD_worldtime.pdf) | World Time: fino a cinque orari del mondo sotto l'orologio, perché il fuso e non le coordinate, e quante se ne vedono insieme |
| [`onair-automazione.it.md`](onair-automazione.it.md) · [PDF](DMD_onair_automazione.pdf) | L'automazione di Home Assistant che collega il sensore della porta al pannello: i due nomi da leggere, lo YAML, e i tre errori facili |
| [`onair.it.md`](onair.it.md) · [PDF](DMD_onair.pdf) | OnAir: il pannello dice che si sta registrando — la scritta, il trattino sull'orologio, l'automazione dalla porta |
| [`meteo.it.md`](meteo.it.md) · [PDF](DMD_meteo.pdf) | Il bollettino del mattino e l'aggiornamento ogni poche ore, le icone disegnate, e perché l'allerta della Protezione Civile non c'è ancora |
| [`moon.it.md`](moon.it.md) · [PDF](DMD_moon.pdf) | Moon: la Luna di stasera, le lune con un nome, equinozi e solstizi, gli sciami e le serate buone da guardare — e il turno con il meteo |

## I giochi

| Documento | Di cosa parla |
|---|---|
| [`doom.it.md`](doom.it.md) · [PDF](DMD_doom.pdf) | Doom sul pannello: compilazione, WAD, comandi, audio |
| [`gameboy.it.md`](gameboy.it.md) · [PDF](DMD_gameboy.pdf) | Game Boy con PyBoy: ROM, overscan, tavolozze, audio |
| [`pongo.it.md`](pongo.it.md) · [PDF](DMD_pongo.pdf) | Pongo: tu contro il computer, i tre livelli e come sono stati tarati |
| [`joypad.it.md`](joypad.it.md) · [PDF](DMD_joypad.pdf) | Mappatura dei comandi: pad, tastiera collegata al DMD, chi può far cominciare una partita |

---

I PDF si rigenerano dai `.md` con [`mkpdf.sh`](mkpdf.sh), che usa `pandoc` e
`wkhtmltopdf`. Lo script sta qui perché una volta è andato perso e ricostruirlo
ha richiesto di dedurre lo stile misurando i colori e la larghezza del testo
dentro un PDF già pubblicato: una mattinata per qualcosa che occupa due
schermate. **Non** vengono
installati in `/opt/dmd`: sul Raspberry non servono, e l'aggiornamento via rete
copia soltanto ciò che il servizio esegue.

Lo storico versione per versione sta in [`CHANGELOG.md`](../CHANGELOG.md) e,
con più dettaglio sul perché di ogni scelta, nell'intestazione di `version.py`.
