# -*- coding: utf-8 -*-
"""Il pulsante fisico della Funcam.

Perche'
-------
Accendere la telecamera dalla pagina Servizi vuol dire tirare fuori il
telefono, aprire il browser, trovare la voce. Per una cosa che si fa passando
davanti al pannello e' una procedura assurda — la stessa obiezione, e la
stessa risposta, della pagina Rete.

Un pulsante solo, tre gesti:

  clic con la telecamera spenta   ->  si accende
  clic con la telecamera accesa   ->  scatta una foto fra tre secondi
  tenuto premuto tre secondi      ->  si spegne

Se il servizio e' spento il pulsante non esiste: non si apre nemmeno il
piedino. Il servizio resta il padrone, il pulsante e' solo la scorciatoia.

Dove si collega, e perche' proprio li'
--------------------------------------
La Bonnet Adafruit occupa quasi tutti i piedini. Quelli davvero liberi, con
il pannello collegato, sono pochi — e vanno scelti sapendo cosa usa la
libreria della matrice, non a occhio:

  usati dalla matrice   4 (o 18 con la modifica PWM), 5, 6, 12, 13, 16, 17,
                        20, 21, 22, 23, 24, 26, 27
  liberi                2, 3, 7, 8, 9, 10, 11, 14, 15, 19, 25

**GPIO 25** e' il piedino consigliato, ed e' anche quello che Adafruit stessa
usa per un pulsante su questa identica scheda. Non ha funzioni alternative,
nessun driver del kernel se lo prende, ed e' libero sia sulla Bonnet sia
sulla HAT. GPIO 19 e' la seconda scelta, altrettanto buona.

Da evitare, anche se sembrano liberi:

  4    con la modifica PWM (GPIO 4 unito a GPIO 18 a saldare) resta legato
       all'uscita OE e la libreria lo tiene occupato di proposito
  24   e' la riga di indirizzo E: inutilizzata sui pannelli a 1/16 di scan,
       ma comunque cablata sul traslatore di livello della Bonnet
  14, 15  sono la console seriale, accesa di suo su quasi tutte le immagini
  2, 3    liberi sulla Bonnet, ma occupati dall'orologio sulla HAT
  7..11   liberi solo se SPI e' disattivato

Il collegamento e' la cosa piu' semplice del progetto: **un pulsante
normalmente aperto fra GPIO 25 e massa**. Nessuna resistenza, perche' si usa
quella di richiamo interna al Raspberry. Sul connettore a 40 piedini GPIO 25
e' il **piedino 22** e una massa e' il **piedino 20**: sono accanto, sulla
stessa fila, quindi si salda sui due fori del connettore della Bonnet — che
sono esposti sopra, perche' lo zoccolo sta sotto. E' il metodo che Adafruit
documenta per la sua stessa scheda.

La lettura
----------
Serve `gpiozero`, che su Raspberry Pi OS c'e' gia'. Il motivo per non fare
la lettura a mano e' che il rimbalzo dei contatti e la distinzione fra clic e
pressione lunga sono esattamente le due cose che sembrano banali e non lo
sono: un pulsante meccanico chiude e riapre decine di volte in pochi
millisecondi, e senza filtro un clic diventa cinque foto.

La macchina a stati sta pero' **fuori** dal pezzo che parla con il piedino,
in `_premuto`, `_tenuto` e `_rilasciato`. Cosi' si puo' provare senza un
Raspberry davanti: le prove chiamano quei tre metodi come farebbe un dito.
"""

import os
import subprocess
import threading
import time

import staccato

# Il piedino consigliato, e il perche' sta nella nota qui sopra.
GPIO_PREDEFINITO = 25

# I piedini che si possono davvero usare con la Bonnet montata. L'elenco e'
# corto di proposito: proporne uno occupato dalla matrice vorrebbe dire un
# pannello che smette di funzionare, e la causa sarebbe l'ultimo posto in cui
# si andrebbe a cercare.
GPIO_AMMESSI = (25, 19, 7, 8, 9, 10, 11, 2, 3)

# Quanto va tenuto premuto perche' conti come "spegni". Tre secondi: pochi
# per essere scomodo, tanti perche' nessun clic ci arrivi per sbaglio.
TENUTA = 3.0

# Filtro anti-rimbalzo, in secondi.
RIMBALZO = 0.05


def disponibile():
    try:
        import gpiozero          # noqa: F401
        return True
    except Exception:
        return False


# ------------------------------------------------------------ installazione

LOG_PATH = "/var/lib/dmd/gpiozero-setup.log"

# Il pacchetto da installare, e il perche' di un pulsante invece di una riga
# di istruzioni: chi ha appena saldato un pulsante sotto il pannello non ha
# un terminale aperto, e mandarlo a cercarne uno vanifica il pulsante stesso.
# Doom, il Game Boy e la condivisione SMB si preparano gia' cosi'.
PACCHETTO = "python3-gpiozero"

# Oltre questo tempo un'installazione senza esito si considera morta: senza,
# un processo ucciso a meta' lascerebbe la pagina a dire "in corso" per
# sempre, e il pulsante di installazione sparito.
SCADUTA = 900


def log(messaggio):
    riga = "%s  %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), messaggio)
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a") as handle:
            handle.write(riga + "\n")
    except OSError:
        pass


def tail_log(lines=30):
    try:
        with open(LOG_PATH) as handle:
            return "".join(handle.readlines()[-lines:])
    except OSError:
        return ""


def _righe():
    try:
        with open(LOG_PATH) as handle:
            return handle.read().splitlines()
    except OSError:
        return []


def in_corso():
    """Se un'installazione sta girando adesso.

    Non si guarda un processo figlio: quello vero gira **fuori** da questo
    servizio (vedi `staccato`), quindi da qui non lo si vede nemmeno. Si
    guarda il registro, che e' l'unica cosa che i due condividono: c'e' un
    avvio piu' recente dell'ultimo esito, e non e' cosi' vecchio da essere
    per forza morto.
    """
    avvio = esito = -1
    quando = 0.0
    for indice, riga in enumerate(_righe()):
        if "== avviata" in riga:
            avvio = indice
            try:
                quando = time.mktime(time.strptime(riga[:19], "%Y-%m-%d %H:%M:%S"))
            except ValueError:
                quando = 0.0
        elif "== esito" in riga:
            esito = indice
    if avvio <= esito:
        return False
    return not quando or (time.time() - quando) < SCADUTA


def ultimo_esito():
    """Il codice di uscita dell'ultima installazione finita, o None."""
    for riga in reversed(_righe()):
        if "== esito" in riga:
            try:
                return int(riga.rsplit(None, 1)[-1])
            except (ValueError, IndexError):
                return None
    return None


def installa():
    """Installa gpiozero in sottofondo. Restituisce un errore o ''.

    Due accortezze che non sono decorative.

    `DPkg::Lock::Timeout` perche' su un Raspberry appena acceso il lucchetto
    di apt e' spesso in mano agli aggiornamenti automatici, e senza attesa
    l'installazione fallirebbe con un errore che non spiega niente a chi ha
    solo premuto un pulsante.

    E gira **fuori dal servizio**: `apt` che viene ucciso a meta' lascia
    dpkg in uno stato da riparare a mano, e un riavvio del DMD durante
    l'installazione ammazzerebbe tutto cio' che sta nel suo cgroup.
    """
    if disponibile():
        return ""
    if in_corso():
        return "gia' in corso"
    log("== avviata installazione di %s" % PACCHETTO)
    comando = (
        "export DEBIAN_FRONTEND=noninteractive; "
        "apt-get -o DPkg::Lock::Timeout=120 update >> %(log)s 2>&1; "
        "apt-get -o DPkg::Lock::Timeout=120 install -y %(pkg)s >> %(log)s 2>&1; "
        "echo \"$(date '+%%Y-%%m-%%d %%H:%%M:%%S')  == esito $?\" >> %(log)s"
        % {"log": LOG_PATH, "pkg": PACCHETTO})
    try:
        staccato.lancia(["bash", "-c", comando], "dmd-gpiozero")
    except Exception as exc:
        log("== esito 1 (avvio fallito: %s)" % exc)
        return str(exc)
    return ""


def stato():
    """Quel che serve alla pagina per decidere cosa mostrare."""
    return {"pronto": disponibile(), "in_corso": in_corso(),
            "esito": ultimo_esito(), "log": tail_log(),
            "pacchetto": PACCHETTO}


def valido(gpio):
    try:
        return int(gpio) in GPIO_AMMESSI
    except (TypeError, ValueError):
        return False


class Pulsante:
    """Un pulsante fisico che chiama `su_clic` e `su_tenuta`.

    Le due funzioni le passa chi lo usa — qui non si sa cosa vogliano dire, e
    non e' un dettaglio: il pulsante non deve conoscere la telecamera, o
    domani non lo si potra' usare per nient'altro.
    """

    def __init__(self, gpio=GPIO_PREDEFINITO, su_clic=None, su_tenuta=None,
                 tenuta=TENUTA):
        self.gpio = int(gpio)
        self.tenuta = float(tenuta)
        self._su_clic = su_clic
        self._su_tenuta = su_tenuta
        self._lucchetto = threading.Lock()
        self._bottone = None
        self._errore = ""
        self._premuto_da = 0.0
        self._gia_tenuto = False
        self._ultimo = 0.0        # quando e' successo l'ultimo gesto

    # ------------------------------------------------------------ apertura

    def avvia(self):
        """Apre il piedino. Restituisce (aperto, motivo)."""
        with self._lucchetto:
            if self._bottone is not None:
                return True, ""
            if not valido(self.gpio):
                self._errore = "GPIO %s non utilizzabile con la Bonnet" % self.gpio
                return False, self._errore
            try:
                from gpiozero import Button
            except Exception as exc:
                self._errore = "gpiozero non installato (%s)" % exc
                return False, self._errore
            try:
                bottone = Button(self.gpio, pull_up=True,
                                 bounce_time=RIMBALZO, hold_time=self.tenuta)
            except Exception as exc:
                # Piedino gia' preso da qualcun altro, o kernel che non lo
                # concede: si racconta invece di far cadere il servizio.
                self._errore = str(exc)
                return False, self._errore
            bottone.when_pressed = self._premuto
            bottone.when_held = self._tenuto
            bottone.when_released = self._rilasciato
            self._bottone = bottone
            self._errore = ""
            return True, ""

    def ferma(self):
        with self._lucchetto:
            bottone, self._bottone = self._bottone, None
        if bottone is not None:
            try:
                bottone.close()
            except Exception:
                pass

    def aperto(self):
        with self._lucchetto:
            return self._bottone is not None

    def stato(self):
        with self._lucchetto:
            return {"aperto": self._bottone is not None, "gpio": self.gpio,
                    "errore": self._errore, "ultimo": self._ultimo}

    # ------------------------------------------------------ macchina a stati

    def _premuto(self):
        self._premuto_da = time.time()
        self._gia_tenuto = False

    def _tenuto(self):
        """Scattato a `tenuta` secondi, con il dito ancora sopra.

        Il gesto si compie **qui**, non al rilascio: chi tiene premuto per
        spegnere deve vedere il pannello spegnersi mentre tiene il dito, non
        quando lo alza. E' l'unico modo di sapere che ha tenuto abbastanza
        senza contare nella propria testa.
        """
        self._gia_tenuto = True
        self._ultimo = time.time()
        if self._su_tenuta:
            self._su_tenuta()

    def _rilasciato(self):
        """Alzato il dito: e' un clic solo se la tenuta non era gia' scattata.

        Senza questo controllo ogni pressione lunga varrebbe **due** gesti —
        lo spegnimento e poi un clic che riaccende — e il pulsante
        sembrerebbe non funzionare.
        """
        tenuto, self._gia_tenuto = self._gia_tenuto, False
        if tenuto:
            return
        self._ultimo = time.time()
        if self._su_clic:
            self._su_clic()
