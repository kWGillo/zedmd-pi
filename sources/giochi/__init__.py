# -*- coding: utf-8 -*-
"""I giochi scritti per il pannello, e la sessione che li fa girare.

**Non sono un servizio: sono una partita**, esattamente come Doom dalla 3.2.
Si preme Gioca, i servizi si fermano, il pannello e' della partita per presa
esclusiva; si esce, e tutto riprende da dove stava. Il meccanismo e' quello
gia' collaudato — `arbiter.hold_on` senza scadenza — e non ne serviva un
secondo.

La differenza con Doom e' che qui non c'e' nessun processo separato. Doom sta
fuori per una ragione di licenza (GPL2 dentro GPLv3 non ci sta) e ne paga il
prezzo: una pipe, un binario da compilare al primo avvio, un file che
l'aggiornamento via rete ha gia' cancellato una volta. Questi giochi sono
nostri e stanno dentro, come l'orologio: nessuna pipe, niente da compilare,
niente che un aggiornamento possa portarsi via.
"""

import threading
import time

from PIL import Image

from ..base import Source
from ..comandi import (ABS_HAT0X, ABS_HAT0Y, ABS_RX, ABS_X, BTN_EAST,
                       BTN_MODE, BTN_SELECT, BTN_SOUTH, BTN_START, BTN_TR,
                       BTN_TR2, BTN_WEST, Lettore, joystick, tastiere)
from .base import ALTEZZA, CAMPO, LARGHEZZA, Gioco, centra, scrivi
from .invasori import Invasori
from .mattoni import Mattoni

GIOCHI = (Mattoni, Invasori)
NOMI = tuple(g.nome for g in GIOCHI)


def per_nome(nome):
    for gioco in GIOCHI:
        if gioco.nome == nome:
            return gioco
    return GIOCHI[0]


def elenco():
    """(nome, etichetta) per la pagina web."""
    return [(g.nome, g.etichetta) for g in GIOCHI]


# Tastiera del cabinato: frecce e WASD, piu' spazio/ctrl per sparare. Sono le
# stesse di Doom dove hanno lo stesso significato, cosi' chi ha imparato una
# pulsantiera non deve impararne due.
TASTI = {
    105: "sinistra", 106: "destra", 103: "su", 108: "giu",
    30: "sinistra", 32: "destra", 17: "su", 31: "giu",     # A D W S
    57: "fuoco", 29: "fuoco", 56: "fuoco",                 # spazio, ctrl, alt
}

# I due tasti "di servizio" della tastiera sono configurabili: su una
# pulsantiera da flipper i codici non sono quelli di una tastiera da ufficio,
# e indovinarli con evtest e' una serata persa. Questi sono solo i predefiniti.
TASTO_CICLO = 28        # invio
TASTO_ESCI = 1          # escape

PULSANTI = {
    BTN_SOUTH: "fuoco", BTN_TR2: "fuoco", BTN_TR: "fuoco",
    BTN_WEST: "fuoco",
    # Start scorre l'elenco dei giochi, Select esce. Cerchio resta una via
    # d'uscita: chi ce l'ha nelle dita da Doom non deve reimpararla.
    BTN_START: "ciclo", BTN_MODE: "ciclo",
    BTN_SELECT: "esci", BTN_EAST: "esci",
}

ASSI = {
    ABS_X: ("sinistra", "destra"),
    ABS_RX: ("sinistra", "destra"),
    ABS_HAT0X: ("sinistra", "destra"),
    ABS_HAT0Y: ("su", "giu"),
}

# Trenta come il ciclo di rendering del pannello: girare piu' veloce vuol dire
# calcolare fotogrammi che nessuno vedra' mai, e su un Pi e' CPU tolta al
# ricevitore ZeDMD, che se rallenta fa scartare fotogrammi al client.
FPS = 30


class GiochiSource(Source):
    """La sorgente che tiene il pannello mentre si gioca."""

    name = "giochi"
    label = "Giochi"
    # Come Doom: non partecipa alla gara di priorita'. O la partita e' aperta,
    # e allora il pannello e' preso, oppure non c'e' niente in esecuzione.
    priority = 0

    def __init__(self, cfg, width, height, arbiter=None):
        super().__init__(cfg, width, height)
        self.arbiter = arbiter
        self._lock = threading.Lock()
        self._image = None
        self._dirty = False

        self._gioco = None
        self._sessione = False
        self._thread = None
        self._stop = threading.Event()
        self._premuti = set()
        self._ultimo_comando = 0.0

        self._lettore = Lettore(self._dispositivi, self._da_comando,
                                tasti=self._tasti(), pulsanti=PULSANTI,
                                assi=ASSI, etichetta="giochi")
        # Il codice del tasto imparato dalla pagina web, quando si sta
        # imparando: il lettore lo consegna qui prima di tradurlo.
        self._impara = None
        self._imparato = 0
        # Dove siamo arrivati nel giro del tasto Start. Sopravvive alla
        # chiusura di una sessione, e a una partita di Doom.
        self._giro = ""

    # ------------------------------------------------------------ ciclo di vita

    def start(self):
        """Rende i giochi *disponibili*, non ne avvia nessuno."""
        self._stop.clear()
        if self.conf().get("keyboard", True) or self.conf().get("joystick", True):
            self.ricarica_comandi()

    def stop(self):
        self._stop.set()
        self.chiudi_sessione()
        self._lettore.stop()

    def conf(self):
        return self.cfg.get("giochi") or {}

    def _tasti(self):
        """La tabella della tastiera, con i due tasti di servizio scelti."""
        tabella = dict(TASTI)
        conf = self.conf()
        try:
            ciclo = int(conf.get("tasto_ciclo") or TASTO_CICLO)
        except (TypeError, ValueError):
            ciclo = TASTO_CICLO
        try:
            esci = int(conf.get("tasto_esci") or TASTO_ESCI)
        except (TypeError, ValueError):
            esci = TASTO_ESCI
        # Prima esci e poi ciclo: se per errore sono lo stesso codice, vince
        # far cominciare una partita, che e' l'azione che serve piu' spesso.
        tabella[esci] = "esci"
        tabella[ciclo] = "ciclo"
        return tabella

    def ricarica_comandi(self):
        """Rilegge i tasti scelti. La chiama la pagina dopo un salvataggio."""
        self._lettore.stop()
        self._lettore = Lettore(self._dispositivi, self._da_comando,
                                tasti=self._tasti(), pulsanti=PULSANTI,
                                assi=ASSI, etichetta="giochi",
                                su_codice=self._codice_grezzo)
        if self.conf().get("keyboard", True) or self.conf().get("joystick", True):
            self._lettore.start()

    # ------------------------------------------------------ imparare un tasto

    def impara_tasto(self, attesa=15.0):
        """Mette in ascolto: il prossimo tasto premuto viene registrato.

        Le pulsantiere da flipper mandano codici che non stanno su nessuna
        tastiera da ufficio. Farli indovinare all'utente con evtest e' una
        serata persa: si preme il pulsante e il sistema lo riconosce.
        """
        self._imparato = 0
        self._impara = time.time() + max(1.0, attesa)
        return True

    def stato_impara(self):
        if self._imparato:
            codice, self._imparato = self._imparato, 0
            self._impara = None
            return {"attivo": False, "codice": codice}
        attivo = bool(self._impara and time.time() < self._impara)
        if not attivo:
            self._impara = None
        return {"attivo": attivo, "codice": 0}

    def _codice_grezzo(self, codice, giu):
        """Il lettore consegna qui ogni tasto prima di tradurlo.

        Restituendo True l'evento viene ingoiato: mentre si impara un tasto
        non deve anche fare quello che farebbe normalmente.
        """
        if not (self._impara and giu):
            return False
        if time.time() >= self._impara:
            self._impara = None
            return False
        self._imparato = int(codice)
        self._impara = None
        return True

    def _dispositivi(self):
        conf = self.conf()
        elenco_dispositivi = []
        if conf.get("keyboard", True):
            scelto = str(conf.get("keyboard_device", "")).strip()
            elenco_dispositivi.extend([scelto] if scelto else tastiere())
        if conf.get("joystick", True):
            scelto = str(conf.get("joystick_device", "")).strip()
            elenco_dispositivi.extend([scelto] if scelto else joystick())
        senza_ripetizioni = []
        for percorso in elenco_dispositivi:
            if percorso not in senza_ripetizioni:
                senza_ripetizioni.append(percorso)
        return senza_ripetizioni

    # ------------------------------------------------------------- la sessione

    def in_sessione(self):
        return self._sessione

    def gioco_corrente(self):
        return self._gioco.nome if self._gioco else ""

    def elenco_ciclo(self):
        """I giochi che il tasto Start scorre, nell'ordine.

        Doom sta fuori a meno che non lo si chieda: parte in qualche secondo,
        vuole un WAD preparato, e finirci dentro per sbaglio mentre si cerca
        Breakout e' sgradevole. Gli altri due partono nell'istante in cui si
        preme.
        """
        giro = list(NOMI)
        if not self.conf().get("ciclo_doom"):
            return giro
        # Si **chiede** se Doom e' pronto, non ci si limita a controllare che
        # qualcuno sappia rispondere: un Doom senza WAD dentro al giro sarebbe
        # una casella su cui il tasto Start non fa niente.
        try:
            pronto = bool(self.doom_pronto and self.doom_pronto())
        except Exception:
            pronto = False
        if pronto:
            giro.append("doom")
        return giro

    # Chi sa dire se Doom e' preparato, e chi apre una partita. Le assegna il
    # runtime: la sorgente dei giochi non deve conoscere Doom, deve solo saper
    # chiedere. `apri_partita` in particolare **deve** passare dal runtime,
    # perche' Doom e i giochi si contendono la stessa presa del pannello e
    # l'unico che lo sa e' lui.
    doom_pronto = None
    apri_doom = None
    apri_partita = None
    chiudi_partita = None

    def ciclo(self):
        """Passa al gioco successivo. Da fermo, riprende da dove era rimasto.

        E' il tasto Start del cabinato: premuto una volta si gioca, premuto
        ancora si cambia gioco. Non c'e' un menu da attraversare, perche' su
        un pannello alto 64 pixel un menu costa piu' di quello che risolve.
        """
        giro = self.elenco_ciclo()
        if not giro:
            return False
        # La posizione nel giro si ricorda a parte e non si legge dalla
        # partita in corso: con Doom nel giro la partita in corso non e' dei
        # giochi, e chiedere "che gioco sta girando?" dava una risposta
        # vecchia. Il giro ripartiva sempre da capo e Doom compariva una volta
        # sola, poi mai piu'.
        if self._sessione:
            corrente = self.gioco_corrente()
        elif self._giro:
            corrente = self._giro
        else:
            # Prima pressione dopo un riavvio: si **riprende** l'ultimo gioco
            # giocato invece di saltare al successivo. Chi preme Start la
            # prima volta vuole giocare, non scegliere.
            ripresa = self.conf().get("ultimo") or ""
            self._giro = ripresa if ripresa in giro else giro[0]
            return self._apri(self._giro, giro)
        indice = giro.index(corrente) if corrente in giro else -1
        prossimo = giro[(indice + 1) % len(giro)] if indice >= 0 else giro[0]
        self._giro = prossimo
        return self._apri(prossimo, giro)

    def _apri(self, prossimo, giro):
        """Apre la casella scelta; se non ci riesce, passa alla successiva.

        Doom puo' non partire — WAD sbagliato, binario non compilato — e in
        quel caso lasciare il pannello a nessuno sarebbe il peggio dei mondi:
        si e' premuto Start e non succede niente. Meglio tirare dritto.
        """
        for _ in range(len(giro)):
            if prossimo == "doom":
                self.chiudi_sessione()
                fatto = bool(self.apri_doom()) if callable(self.apri_doom) else False
            elif callable(self.apri_partita):
                # Non `apri_sessione` diretta: aprire un gioco deve poter
                # **chiudere Doom**, e quella regola sta nel runtime.
                fatto = bool(self.apri_partita("giochi", prossimo))
            else:
                fatto = bool(self.apri_sessione(prossimo))
            if fatto:
                return True
            print("[giochi] %s non e' partito: passo al successivo" % prossimo)
            prossimo = giro[(giro.index(prossimo) + 1) % len(giro)]
            self._giro = prossimo
        return False

    def apri_sessione(self, nome=""):
        """Comincia una partita e prende il pannello."""
        nome = nome or self.conf().get("ultimo") or NOMI[0]
        self._ultimo_comando = time.time()
        if self._sessione and self._gioco and self._gioco.nome == nome:
            return True
        if self._sessione:
            # Cambiare gioco a partita aperta: si chiude quella e si apre
            # l'altra, senza mollare il pannello in mezzo.
            self._ferma_ciclo()
        record = self._gioco.record() if self._gioco else 0
        self._gioco = per_nome(nome)()
        self._gioco._record = max(record if self._gioco.nome == nome else 0,
                                  int(self.conf().get("record", {}).get(nome, 0)))
        self._premuti.clear()
        self._sessione = True
        self._stop.clear()
        self._thread = threading.Thread(target=self._ciclo, name="giochi",
                                        daemon=True)
        self._thread.start()
        if self.arbiter is not None:
            # Senza scadenza: chi gioca decide quando smettere. A chiudere
            # pensano il pulsante Esci o il tempo di inattivita'.
            self.arbiter.hold_on(self.name)
        return True

    def chiudi_sessione(self):
        aperta = self._sessione
        self._sessione = False
        self._ferma_ciclo()
        self._premuti.clear()
        self._lettore.dimentica()
        if self.arbiter is not None:
            self.arbiter.hold_off(self.name)
        with self._lock:
            self._image = None
            self._dirty = False
        return aperta

    def _ferma_ciclo(self):
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.5)
        self._salva_record()

    def _salva_record(self):
        """Il record sopravvive alla partita: e' l'unica cosa che ha senso
        ricordare, e sta in configurazione come tutto il resto."""
        if not self._gioco:
            return
        try:
            conf = self.cfg.setdefault("giochi", {})
            record = conf.setdefault("record", {})
            nome = self._gioco.nome
            if self._gioco.record() > int(record.get(nome, 0)):
                record[nome] = int(self._gioco.record())
                conf["ultimo"] = nome
                import dmdconf
                dmdconf.save()
        except Exception as exc:
            print("[giochi] record non salvato: %s" % exc)

    def inattivita(self):
        if not self._sessione:
            return 0.0
        return time.time() - self._ultimo_comando

    def controlla_inattivita(self):
        """Una partita lasciata a meta' non tiene il pannello per sempre."""
        limite = int(self.conf().get("session_timeout", 180) or 0)
        if limite and self._sessione and self.inattivita() > limite:
            print("[giochi] partita chiusa per inattivita'")
            self.chiudi_sessione()

    # ------------------------------------------------------------------ comandi

    def premi(self, azione, giu=True, apri=True):
        """Un comando, da qualunque parte arrivi: pagina web, tastiera o pad."""
        if azione == "esci" and giu:
            # Select esce da **qualunque** partita, anche da Doom: e' un
            # pulsante globale come Start, e chi lo preme vuole tornare
            # all'orologio, non sapere quale sorgente stesse girando.
            if callable(self.chiudi_partita):
                self.chiudi_partita()
            else:
                self.chiudi_sessione()
            return True
        if azione == "ciclo":
            # Solo alla pressione: sul rilascio si passerebbe al gioco dopo.
            if not giu:
                return True
            if not apri:
                return False
            return self.ciclo()
        if azione == "avvia" and giu and not self._sessione:
            if not apri:
                return False
            return self.apri_sessione()
        if not self._sessione:
            return False
        self._ultimo_comando = time.time()
        if giu:
            self._premuti.add(azione)
        else:
            self._premuti.discard(azione)
        return True

    def tocca(self, azione, durata=0.12):
        """Premuto e rilasciato: e' quello che serve a un pulsante web.

        Senza il rilascio automatico un dito che scivola fuori dal pulsante
        lascerebbe la racchetta a correre contro il bordo per sempre.
        """
        if not self.premi(azione, True):
            return False
        timer = threading.Timer(max(0.02, min(1.0, durata)),
                                lambda: self.premi(azione, False))
        timer.daemon = True
        timer.start()
        return True

    def _da_comando(self, azione, giu, avvio):
        """Un comando letto da tastiera o da pad.

        Il permesso di *far cominciare* una partita non e' lo stesso per
        tutti. Un tasto qualunque del cabinato non ce l'ha, perche' il DMD sta
        in mezzo a un flipper e un tasto sfiorato per caso non deve portarsi
        via il pannello. Ma il **tasto dedicato** — Start sul pad, o quello
        scelto sulla pulsantiera — ce l'ha sempre: e' un gesto deliberato, e
        se glielo si negasse la funzione nascerebbe spenta e sembrerebbe
        rotta.
        """
        if azione == "ciclo":
            apri = True
        elif avvio:
            apri = bool(self.conf().get("joystick_starts", True))
        else:
            apri = bool(self.conf().get("keyboard_starts", False))
        self.premi(azione, giu, apri=apri)

    def premuti(self):
        return sorted(self._premuti)

    # ------------------------------------------------------------------ il ciclo

    def _ciclo(self):
        periodo = 1.0 / FPS
        precedente = time.time()
        while not self._stop.is_set() and self._sessione:
            adesso = time.time()
            dt = min(0.1, adesso - precedente)      # una pausa lunga non
            precedente = adesso                     # teletrasporta la palla
            gioco = self._gioco
            if gioco is None:
                break
            try:
                gioco.passo(dt, set(self._premuti))
                immagine = gioco.disegna()
            except Exception as exc:
                print("[giochi] errore nel gioco: %s" % exc)
                self.chiudi_sessione()
                return
            with self._lock:
                self._image = immagine
                self._dirty = True
            resto = periodo - (time.time() - adesso)
            if resto > 0:
                self._stop.wait(resto)

    # ------------------------------------------------------------------ arbitro

    def active(self):
        return self._sessione

    def frame(self):
        with self._lock:
            if not self._dirty or self._image is None:
                return None
            self._dirty = False
            return self._image

    def stato(self):
        gioco = self._gioco
        base = {"session": self._sessione, "gioco": self.gioco_corrente(),
                "idle": int(self.inattivita()), "keys": self.premuti(),
                "giochi": elenco()}
        base.update(gioco.stato() if gioco else
                    {"punteggio": 0, "vite": 0, "livello": 0,
                     "record": 0, "finita": False})
        return base

    def status(self, lang=None):
        if not self._sessione or not self._gioco:
            return self.t("status.giochi.ferma", lang)
        return self.t("status.giochi.partita", lang,
                      gioco=self._gioco.etichetta,
                      punteggio=self._gioco.punteggio,
                      vite=self._gioco.vite)


__all__ = ["GIOCHI", "NOMI", "GiochiSource", "Gioco", "Invasori", "Mattoni",
           "elenco", "per_nome", "TASTI", "PULSANTI", "ASSI",
           "ALTEZZA", "CAMPO", "LARGHEZZA", "centra", "scrivi"]
