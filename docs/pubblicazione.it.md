# Pubblicare una nuova versione su GitHub

Procedura da seguire ogni volta che ricevi un nuovo `zedmd-pi.tar.gz` e vuoi
portarlo sul repository **https://github.com/kWGillo/zedmd-pi**.

Si esegue **sul Mac**, non sul Raspberry.

> **Regola d'oro:** incolla **un comando alla volta**. Quando in una sequenza
> incollata tutta insieme un `cd` fallisce, i comandi successivi vengono
> eseguiti nella cartella sbagliata. È così che era finito un `git init` dentro
> `~/Downloads`.

---

## 0. Preparazione, solo la prima volta

Serve `gh`, il client ufficiale di GitHub, per l'autenticazione:

```bash
brew install gh
```

```bash
gh auth login
```

Scegli *GitHub.com* → *HTTPS* → *Login with a web browser*, e incolla nel
browser il codice che compare nel terminale.

Da qui in poi `git push` non chiede più credenziali.

---

## 1. Scompattare il pacchetto

```bash
cd ~/Downloads
```

```bash
ls ~/Downloads/*.tar.gz
```

Guarda il nome esatto che compare e usalo nel comando successivo. In `zsh` —
la shell del Mac — un carattere jolly che non trova nulla fa fallire l'intero
comando con `zsh: no matches found`, quindi conviene leggere il nome vero
invece di indovinarlo.

```bash
tar xzf zedmd-pi.tar.gz
```

```bash
cd ~/Downloads/zedmd-pi
```

---

## 2. Verificare di essere nel posto giusto

**Questo passaggio non si salta.** Costa tre secondi ed evita l'errore più
frequente:

```bash
pwd && ls version.py && git remote -v
```

Devono comparire tre cose:

| Cosa | Valore atteso |
|---|---|
| percorso | `/Users/<tuonome>/Downloads/zedmd-pi` |
| file | `version.py` |
| remote | `origin  https://github.com/kWGillo/zedmd-pi.git` |

Se compaiono tutte e tre, salta al passo 4.

### Se `pwd` mostra `/Users/<tuonome>/Downloads`

Il `cd` del passo 1 non è andato a buon fine, quasi sempre perché il `tar` ha
fallito. Non proseguire: torna al passo 1.

---

## 3. Se manca il remote: `fatal: not a git repository`

È il caso **normale**, non un errore: il pacchetto contiene i file, non la
cronologia del progetto.

Qui la tentazione è fare `git init` nella cartella scompattata. **Non
funziona**: creerebbe una storia nuova, senza parentela con quella già
pubblicata su GitHub, e il push verrebbe rifiutato con
*"refusing to merge unrelated histories"*. Se ne esce solo cancellando la
cronologia remota.

La strada giusta è l'inversa: si parte dal repository vero e gli si sostituisce
il contenuto.

```bash
cd ~/Downloads
```

```bash
git clone https://github.com/kWGillo/zedmd-pi.git zedmd-pi-repo
```

```bash
cd ~/Downloads/zedmd-pi-repo
```

Svuota la cartella tenendo **solo** `.git`, che è la cronologia:

```bash
find . -mindepth 1 -maxdepth 1 -not -name .git -exec rm -rf {} +
```

Copia dentro i file nuovi (il punto finale dopo la barra è indispensabile:
significa "il contenuto della cartella", non la cartella stessa):

```bash
cp -R ~/Downloads/zedmd-pi/. .
```

Controlla che sia andata:

```bash
pwd && grep __version__ version.py && git remote -v
```

Da qui in avanti lavori in `~/Downloads/zedmd-pi-repo`. La cartella
`~/Downloads/zedmd-pi` scompattata dal pacchetto non serve più e puoi
cancellarla.

> Le volte successive puoi saltare tutto questo: `zedmd-pi-repo` resta sul Mac
> con il suo `.git`. Basta `git pull`, svuotare, ricopiare il contenuto del
> pacchetto nuovo e ripartire dal passo 4.

---

## 4. Controllare che cosa stai per pubblicare

```bash
grep __version__ version.py
```

```bash
git status
```

`git status` elenca i file nuovi e modificati. Dagli un'occhiata: non devono
comparire file personali, `.DS_Store`, o la cartella `__pycache__`.

---

## 5. Pubblicare

```bash
git add -A
```

```bash
git commit -m "7.0: il meteo, con bollettino, aggiornamenti e allerte; la posizione passa alle Impostazioni"
```

Cambia il messaggio a ogni versione: numero della versione e una riga su cosa
è cambiato. Il testo lo trovi già pronto in `CHANGELOG.md`, in cima.

```bash
git push -u origin main
```

Dalla seconda volta in poi basta `git push`.

---

## 6. Se il push viene rifiutato

Messaggio tipico: *"Updates were rejected because the remote contains work that
you do not have locally"*. Vuol dire che su GitHub c'è qualcosa che nella tua
cartella non c'è.

```bash
git pull --rebase origin main
```

```bash
git push -u origin main
```

Se il `pull --rebase` segnala conflitti e il contenuto locale è quello giusto
— cioè il pacchetto appena scompattato è la versione buona — puoi sovrascrivere
il remoto:

```bash
git push --force-with-lease origin main
```

`--force-with-lease` è la variante prudente: rifiuta di sovrascrivere se nel
frattempo qualcun altro ha pubblicato qualcosa.

---

## 7. Verifica finale

```bash
gh repo view kWGillo/zedmd-pi --web
```

Apre il repository nel browser. Controlla che in cima al file `version.py`
compaia il numero giusto.

Oppure da terminale, senza aprire nulla:

```bash
curl -s https://raw.githubusercontent.com/kWGillo/zedmd-pi/main/version.py | grep __version__
```

Questo è **esattamente** l'indirizzo che interroga l'aggiornamento automatico
del Raspberry: se qui vedi il numero nuovo, l'OTA lo vedrà.

---

## 7b. Quello che non sta dentro il pacchetto

Tre informazioni si vedono su GitHub ma **non** stanno in nessun file del
repository: vivono nelle impostazioni del progetto, quindi `git push` non le
tocca e nessun aggiornamento le allinea da solo. Sono quelle che restano
indietro di venti versioni senza che nessuno se ne accorga.

### La descrizione (*About*)

È la riga sotto il nome del repository, e la sola cosa che si legge nei
risultati di ricerca di GitHub. Deve dire che cosa fa il progetto e per chi,
non a che versione è. **In inglese**, anche se i manuali sono in italiano: chi
cerca «hub75 s-pwm raspberry» non scrive in italiano.

```bash
gh repo edit kWGillo/zedmd-pi --description "ZeDMD-compatible network DMD for Raspberry Pi — drives S-PWM HUB75 panels (FM6373 and similar) that ZeDMD cannot, and between games it stays a living-room display: clock, flight radar, ISS pass alerts, now playing, calendar, Doom and Game Boy, with two-way Home Assistant integration over MQTT"
```

Si cambia solo quando cambia **che cosa** è il progetto, non a ogni versione.
Quella di prima si fermava alla prima metà — i pannelli che ZeDMD non gestisce
— e taceva tutto quello che il DMD fa quando non si gioca, che è poi il motivo
per cui resta acceso.

La coda su Home Assistant è l'aggiunta della 6.8, ed è un cambio di **che
cosa**: fino alla 6.0 il DMD si limitava a raccontarsi: pubblicava i suoi
sensori e basta. Adesso Home Assistant può anche parlargli — tre entità
`notify` accanto al telefono — e il pannello pubblica quello che vede del
cielo. Non è una funzione in più nell'elenco: è la differenza fra un
dispositivo che si osserva e uno che si usa.

Con la 7.0 vale la pena nominare anche il **meteo**, per lo stesso motivo: un
oggetto da salotto che al mattino racconta la giornata e avvisa di un'allerta
non è più soltanto un DMD con delle funzioni in più.

```bash
gh repo edit kWGillo/zedmd-pi --description "ZeDMD-compatible network DMD for Raspberry Pi — drives S-PWM HUB75 panels (FM6373 and similar) that ZeDMD cannot, and between games it stays a living-room display: clock, weather and severe-weather alerts, flight radar, ISS pass alerts, now playing, calendar, Doom and Game Boy, with two-way Home Assistant integration over MQTT"
```

### Gli argomenti (*topics*)

Sono le etichette che decidono se qualcuno che cerca «hub75 raspberry pi» ti
trova. `--add-topic` **aggiunge**, non sostituisce: rielencare quelli che
c'erano già non fa danno, e per toglierne uno serve `--remove-topic`.

```bash
gh repo edit kWGillo/zedmd-pi --add-topic batocera,dmd,hub75,led-matrix,pinball,raspberry-pi,virtual-pinball,zedmd,fm6373,shairport-sync,pyboy,doomgeneric,home-assistant,airplay,iss,satellite-tracking,sgp4,mqtt,adsb
```

`mqtt` e `adsb` sono arrivati con la 6.8.1, `weather` e `meteoalarm` con la
7.0: sono le parole con cui si cerca davvero questa roba, e prima non
c'erano.

```bash
gh repo edit kWGillo/zedmd-pi --add-topic weather,meteoalarm,open-meteo
```

### La *Release*

Il tag è l'unico posto dove la versione compare in modo permanente e
scaricabile. Senza release, chi arriva sul repository può prendere solo lo
stato attuale di `main`: non esiste «la 5.7» da scaricare, esiste «com'era
oggi». Il testo delle note lo prendi da `CHANGELOG.md`, in cima.

**Va fatta dopo il push**, non prima: il tag punta a quello che c'è su GitHub
in quel momento.

```bash
gh release create v7.0 --title "7.0" --notes-file <(sed -n '/^## \[7.0\]/,/^## \[6.7\]/p' CHANGELOG.md | sed '$d')
```

Se il tag esiste già, `gh release edit v7.0 --notes-file ...`.

> L'intervallo arriva fino alla **6.7** e non alla 6.9, e non è un errore: su
> GitHub l'ultima pubblicata è la 6.7, quindi questo push porta 6.8, 6.8.1, 6.9
> e 7.0 tutte insieme. La regola è al paragrafo qui sotto; il numero da cui
> partire lo dice il comando `curl` di fine pagina, non la memoria.

### Quando si pubblicano più versioni insieme

Capita — e non è un problema: si lavora per giorni, ogni correzione alza il
numero di versione, e su GitHub si arriva quando si arriva. Il push è uno
solo, e contiene tutto.

Due decisioni, e una sola è ovvia.

**Il commit è uno.** Non ha senso inventarne uno per versione: non
ricostruirebbero la storia vera — i file sono quelli finali, non gli stadi
intermedi — e la falsificherebbero. Il messaggio porta il numero finale.

**I tag intermedi non si fanno.** Un tag punta a un commit, e qui il commit è
uno: le versioni di mezzo finirebbero tutte sullo stesso stato, quello
dell'ultima. Sarebbero bugie scaricabili. Si crea **una** release, quella
finale, con dentro le note di tutte le versioni che il push contiene — così
chi legge vede comunque ogni passaggio, in ordine e per esteso.

L'intervallo si prende dal `CHANGELOG.md`: dalla versione nuova **fino alla
prima già pubblicata**, esclusa. Per un push che porta dalla 6.4 alla 6.8:

```bash
gh release create v6.8 --title "6.8" --notes-file <(sed -n '/^## \[6.8\]/,/^## \[6.3\]/p' CHANGELOG.md | sed '$d')
```

Per sapere qual è l'ultima versione già su GitHub, senza andare a memoria:

```bash
curl -s https://raw.githubusercontent.com/kWGillo/zedmd-pi/main/version.py | grep __version__
```

È la stessa riga che legge l'OTA del Raspberry, e va letta **prima** del push:
dopo dice già il numero nuovo.

> **Controllo veloce, una riga.** Dopo la pubblicazione:
>
> ```bash
> gh repo view kWGillo/zedmd-pi --json description,repositoryTopics,latestRelease
> ```
>
> Se la descrizione parla di funzioni che non ci sono più, o l'ultima release
> è di quattro versioni fa, sai che cosa sistemare.

---

## 8. Aggiornare il Raspberry

Dopo la pubblicazione non serve più trasferire niente a mano.

**Dalla web UI** — pagina *Impostazioni*, sezione *Aggiornamento*: entro 24 ore
il controllo automatico trova la versione nuova, oppure premi *Controlla ora*.
Poi compare il pulsante di installazione.

> **Aspetta cinque minuti prima di premere *Controlla ora*.** Il Raspberry
> chiede la versione a `raw.githubusercontent.com`, che è una rete di cache:
> serve il file con `Cache-Control: max-age=300`, cioè può rispondere con la
> versione **vecchia** fino a cinque minuti dopo il push. Su GitHub, nel
> browser, il file nuovo si vede subito — ed è esattamente la trappola: sembra
> che il DMD non veda l'aggiornamento, e invece nessuno dei due ha torto.
>
> È già successo con la 6.1. Se hai fretta, il controllo è questo, e dice
> quello che vede il Raspberry, non quello che vedi tu:
>
> ```bash
> curl -s https://raw.githubusercontent.com/kWGillo/zedmd-pi/main/version.py | grep __version__
> ```
>
> Quando qui compare il numero nuovo, *Controlla ora* lo trova. Il pacchetto
> vero e proprio arriva invece da `codeload.github.com`, che non ha questo
> ritardo: una volta vista la versione, l'installazione parte subito.

**Da riga di comando**, in alternativa:

```bash
ssh gillo@dmdpi.local
```

```bash
cd ~/dmd && git pull && sudo ./update.sh
```

> **Riavvia sempre Batocera dopo un aggiornamento.** Il client ZeDMD tiene in
> memoria lo stato della connessione e la contabilità delle zone già inviate:
> dopo il riavvio del servizio sul Raspberry quello stato non è più valido.

---

## Riepilogo, per quando la procedura è già nota

Con `~/Downloads/zedmd-pi-repo` già presente sul Mac dalla volta precedente:

```bash
curl -s https://raw.githubusercontent.com/kWGillo/zedmd-pi/main/version.py | grep __version__   # ← qual è l'ultima pubblicata
cd ~/Downloads
ls ~/Downloads/*.tar.gz
tar xzf zedmd-pi.tar.gz
cd ~/Downloads/zedmd-pi-repo
git pull
find . -mindepth 1 -maxdepth 1 -not -name .git -exec rm -rf {} +
cp -R ~/Downloads/zedmd-pi/. .
pwd && grep __version__ version.py && git remote -v   # ← verifica, non saltare
git add -A
git commit -m "<versione>: <cosa è cambiato>"
git push
curl -s https://raw.githubusercontent.com/kWGillo/zedmd-pi/main/version.py | grep __version__
gh release create v<versione> --title "<versione>" --notes-file <(sed -n "/^## \[<versione>\]/,/^## \[<ultima già pubblicata>\]/p" CHANGELOG.md | sed '$d')
gh repo view kWGillo/zedmd-pi --json description,repositoryTopics,latestRelease   # ← passo 7b
```

Poi, sul Raspberry, *Controlla ora* — ma **dopo cinque minuti**: il passo 8
spiega perché.

---

## Errori già incontrati, e come si riconoscono

| Messaggio | Che cosa è successo | Rimedio |
|---|---|---|
| `zsh: no matches found: zedmd*pi*.tar.gz` | il jolly non trova nulla; in zsh questo blocca il comando | `ls ~/Downloads/*.tar.gz` e scrivi il nome reale |
| `tar: ... Cannot open: No such file or directory` | nome del pacchetto diverso da quello atteso | come sopra |
| `cd: no such file or directory: zedmd-pi` | il `tar` era fallito, la cartella non esiste | ripeti il passo 1 |
| `fatal: not a git repository` | la cartella scompattata non contiene la cronologia | passo 3, **non** `git init` |
| `refusing to merge unrelated histories` | è stato fatto `git init` invece del clone | rifai dal passo 3 partendo dal clone |
| `gh: command not found` | manca il client GitHub | `brew install gh` |
| `Updates were rejected` | il remoto è avanti | passo 6 |
| `git init` eseguito per sbaglio in `~/Downloads` | `cd` fallito e comandi incollati in blocco | `rm -rf ~/Downloads/.git` |
| il DMD dice «sei aggiornato» subito dopo il push | la cache di `raw.githubusercontent.com`, cinque minuti | aspetta e ripremi *Controlla ora*; passo 8 |

Quest'ultima riga merita attenzione: un `git init` in `~/Downloads` trasforma
l'intera cartella Download in un repository, e un `git add -A` successivo
proverebbe a pubblicare tutto quello che hai scaricato. Se `git status` elenca
centinaia di file che non c'entrano nulla, **fermati** e cancella il `.git`
sbagliato.
