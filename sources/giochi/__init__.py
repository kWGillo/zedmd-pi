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
                       BTN_MODE, BTN_SOUTH, BTN_START, BTN_TR, BTN_TR2,
                       BTN_WEST, Lettore, joystick, tastiere)
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
    28: "avvia", 1: "esci",                                # invio, escape
}

PULSANTI = {
    BTN_SOUTH: "fuoco", BTN_TR2: "fuoco", BTN_TR: "fuoco",
    BTN_EAST: "esci", BTN_WEST: "fuoco",
    BTN_START: "avvia", BTN_MODE: "avvia",
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
                                tasti=TASTI, pulsanti=PULSANTI, assi=ASSI,
                                etichetta="giochi")

    # ------------------------------------------------------------ ciclo di vita

    def start(self):
        """Rende i giochi *disponibili*, non ne avvia nessuno."""
        self._stop.clear()
        if self.conf().get("keyboard", True):
            self._lettore.start()

    def stop(self):
        self._stop.set()
        self.chiudi_sessione()
        self._lettore.stop()

    def conf(self):
        return self.cfg.get("giochi") or {}

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
            self.chiudi_sessione()
            return True
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
        # Come per Doom: il pad puo' far cominciare una partita con Options,
        # la tastiera del cabinato solo se lo si e' chiesto. Un tasto sfiorato
        # per caso non deve portarsi via il pannello a meta' partita.
        if avvio:
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
