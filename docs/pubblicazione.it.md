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
git commit -m "1.6: cache della libreria media, Air Radar, OTA, installazione da GitHub"
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

## 8. Aggiornare il Raspberry

Dopo la pubblicazione non serve più trasferire niente a mano.

**Dalla web UI** — pagina *Impostazioni*, sezione *Aggiornamento*: entro 24 ore
il controllo automatico trova la versione nuova, oppure premi *Controlla ora*.
Poi compare il pulsante di installazione.

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
```

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

Quest'ultima riga merita attenzione: un `git init` in `~/Downloads` trasforma
l'intera cartella Download in un repository, e un `git add -A` successivo
proverebbe a pubblicare tutto quello che hai scaricato. Se `git status` elenca
centinaia di file che non c'entrano nulla, **fermati** e cancella il `.git`
sbagliato.
