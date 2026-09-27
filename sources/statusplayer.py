# -*- coding: utf-8 -*-
"""Status Player: chi sta giocando adesso, sul pannello.

Due modi di comparire, perche' rispondono a due domande diverse.

*La notifica* risponde a **"e' appena successo qualcosa"**: un amico ha
avviato un gioco. Compare subito, dura pochi secondi, e poi il pannello
torna a quello che stava facendo. E' un evento: se non lo dici adesso non
ha piu' senso dirlo.

*Il giro* risponde a **"chi c'e' in questo momento"**: ogni tanto, una
schermata per ciascuno di quelli che stanno giocando -- nome, gioco,
punteggio. Non e' urgente: e' il tabellone di una sala giochi.

Priorita' 62, appena sopra i satelliti e sotto le notifiche di Home
Assistant. Un amico che comincia a giocare e' un fatto del momento come il
passaggio di un aereo, ma non e' un allarme, e soprattutto non interrompe
una partita di chi sta al pannello: quello sta giocando davvero.

Il punteggio e' quello di RetroAchievements, e vale la pena dire perche':
e' l'unico numero confrontabile fra uno che gioca a Sonic e uno che gioca a
Metal Slug. Accanto, quando c'e', quanto ne ha guadagnati da quando ha
cominciato quella partita -- che e' il numero che rende viva una schermata
altrimenti ferma.
"""

import threading
import time

from PIL import Image, ImageDraw

import statusplayer
from .base import Source
from .clock import _load_font

PRIORITA = 62

# I colori, con la stessa grammatica del resto del pannello: ambra per la
# cosa che conta (il nome di chi gioca), bianco per il fatto (il gioco),
# grigio per il contorno, verde per i punti guadagnati adesso.
NOME = (0xFF, 0xB0, 0x30)
TITOLO = (0xF0, 0xF2, 0xF8)
SPENTO = (0x78, 0x80, 0x90)
PUNTI = (0xFF, 0xE0, 0x80)
GUADAGNO = (0x50, 0xE0, 0x80)
RIGA = (0x30, 0x38, 0x4C)

# Quanto dura una schermata del giro, e quanto ne passa fra un giro e
# l'altro. Sono i valori di serie: la pagina li cambia.
DURATA_SCHERMATA = 7
INTERVALLO_GIRO = 300
DURATA_NOTIFICA = 8


class StatusPlayerSource(Source):
    name = "status_player"
    label = "Status Player"
    priority = PRIORITA

    def __init__(self, cfg, width, height, registro=None, vigile=None):
        super().__init__(cfg, width, height)
        self._running = False
        self._lucchetto = threading.Lock()
        self._image = None
        self._dirty = False
        self._showing = False
        self._thread = None
        self._sveglia = threading.Event()
        self._mostrate = 0
        self._notificate = 0
        # Il registro e il giro delle richieste stanno fuori dalla sorgente:
        # cosi' la pagina web li puo' leggere e riempire anche a pannello
        # spento, e l'agente su Batocera puo' scrivere quando gli pare.
        self.registro = registro if registro is not None else statusplayer.Registro()
        self.vigile = vigile if vigile is not None else statusplayer.Vigile(
            cfg, self.registro)
        self._font_nome = _load_font(max(12, int(height * 0.34)))
        self._font_gioco = _load_font(max(9, int(height * 0.24)))
        self._font_piccolo = _load_font(max(7, int(height * 0.17)))

    # -------------------------------------------------------- ciclo di vita

    def start(self):
        if self._running:
            return
        self._running = True
        self._sveglia.clear()
        self.vigile.avvia()
        self._thread = threading.Thread(target=self._ciclo, name="status_player",
                                        daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._showing = False
        self.vigile.ferma()
        self._sveglia.set()

    def trigger_now(self):
        """Mostra subito il giro, senza aspettare l'intervallo."""
        self._sveglia.set()

    # ------------------------------------------------------------- arbitro

    def active(self):
        return self._running and self._showing

    def frame(self):
        with self._lucchetto:
            if not self._dirty or self._image is None:
                return None
            self._dirty = False
            return self._image

    def status(self, lang=None):
        if not self._running:
            return self.t("status.disabled", lang)
        conf = self.conf()
        if not (conf.get("chiave_ra") or "").strip() and not self.amici_agente():
            return self.t("status.player.vuoto", lang)
        vivi = self.registro.in_gioco(self.minuti_vivo())
        if self.registro.errore:
            return self.t("status.player.errore", lang,
                          error=self.registro.errore)
        if not vivi:
            return self.t("status.player.nessuno", lang, shown=self._mostrate)
        primo = vivi[0]
        return self.t("status.player.ok", lang, count=len(vivi),
                      name=primo["nome"], game=primo["gioco"] or "?",
                      shown=self._mostrate)

    # ----------------------------------------------------------- impostazioni

    def conf(self):
        return self.cfg.get("status_player") or {}

    def minuti_vivo(self):
        try:
            return max(1, min(180, int(self.conf().get("minuti_vivo",
                                                       statusplayer.VIVO_DEFAULT))))
        except (TypeError, ValueError):
            return statusplayer.VIVO_DEFAULT

    def amici_agente(self):
        """Vero se qualcuno puo' scrivere dall'agente: serve un segreto."""
        return bool((self.conf().get("token") or "").strip())

    def _intero(self, chiave, difetto, minimo, massimo):
        try:
            return max(minimo, min(massimo, int(self.conf().get(chiave, difetto))))
        except (TypeError, ValueError):
            return difetto

    # ---------------------------------------------------------------- ciclo

    def _ciclo(self):
        prossimo_giro = time.monotonic()
        while self._running:
            # Le partenze hanno sempre la precedenza sul giro: sono il
            # motivo per cui questo servizio esiste.
            for evento in self.registro.eventi():
                if not self._running:
                    break
                if self.conf().get("notifica", True):
                    self._mostra(self._disegna_notifica(evento),
                                 self._intero("durata_notifica",
                                              DURATA_NOTIFICA, 3, 30))
                    self._notificate += 1
            adesso = time.monotonic()
            if adesso >= prossimo_giro and self.conf().get("giro", True):
                vivi = self.registro.in_gioco(self.minuti_vivo())
                durata = self._intero("durata_schermata", DURATA_SCHERMATA, 3, 30)
                for posto, voce in enumerate(vivi):
                    if not self._running:
                        break
                    self._mostra(self._disegna_voce(voce, posto + 1, len(vivi)),
                                 durata)
                    self._mostrate += 1
                prossimo_giro = time.monotonic() + self._intero(
                    "intervallo_giro", INTERVALLO_GIRO, 30, 7200)
            # Un secondo di attesa: le partenze devono uscire in fretta, e un
            # secondo di ritardo su una notizia non lo nota nessuno.
            self._sveglia.wait(1.0)
            self._sveglia.clear()

    def _mostra(self, immagine, secondi):
        """Tiene una schermata per `secondi`, poi lascia il pannello."""
        self._pubblica(immagine)
        self._showing = True
        fine = time.monotonic() + max(1, int(secondi))
        while self._running and time.monotonic() < fine:
            time.sleep(0.1)
        self._showing = False

    def _pubblica(self, immagine):
        with self._lucchetto:
            self._image = immagine
            self._dirty = True

    # -------------------------------------------------------------- disegno

    def _tela(self):
        immagine = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        return immagine, ImageDraw.Draw(immagine)

    def _scrivi(self, disegno, xy, testo, font, colore, destra=False):
        if not testo:
            return 0
        larghezza = disegno.textlength(testo, font=font)
        x = xy[0] - larghezza if destra else xy[0]
        disegno.text((x, xy[1]), testo, font=font, fill=colore)
        return larghezza

    def _stringi(self, disegno, testo, font, disponibile):
        """Accorcia un titolo finche' entra, con i puntini alla fine."""
        testo = testo or ""
        if disegno.textlength(testo, font=font) <= disponibile:
            return testo
        while testo and disegno.textlength(testo + "…", font=font) > disponibile:
            testo = testo[:-1]
        return (testo.rstrip() + "…") if testo else ""

    def _disegna_voce(self, voce, posto, quanti):
        """Una persona: nome grande, gioco sotto, punti a destra.

        ```
        IN GIOCO                                2 DI 3
        GILLO                                   12.480
        Super Mario World   SNES                   +25
        ```
        """
        immagine, disegno = self._tela()
        alto = 1
        self._scrivi(disegno, (2, alto), self.t("player.panel.ingioco"),
                     self._font_piccolo, SPENTO)
        if quanti > 1:
            self._scrivi(disegno, (self.width - 2, alto),
                         "%d/%d" % (posto, quanti), self._font_piccolo,
                         SPENTO, destra=True)

        mezzo = int(self.height * 0.26)
        punti = _mille(voce.get("punti", 0))
        larghezza_punti = disegno.textlength(punti, font=self._font_nome) if punti else 0
        self._scrivi(disegno, (2, mezzo),
                     self._stringi(disegno, voce["nome"], self._font_nome,
                                   self.width - 8 - larghezza_punti),
                     self._font_nome, NOME)
        if punti:
            self._scrivi(disegno, (self.width - 2, mezzo), punti,
                         self._font_nome, PUNTI, destra=True)

        basso = int(self.height * 0.70)
        guadagno = voce.get("guadagnati", 0)
        coda = "+%s" % _mille(guadagno) if guadagno else voce.get("sistema", "")
        larghezza_coda = disegno.textlength(coda, font=self._font_gioco) if coda else 0
        titolo = voce.get("presenza") or voce.get("gioco", "")
        self._scrivi(disegno, (2, basso),
                     self._stringi(disegno, titolo, self._font_gioco,
                                   self.width - 8 - larghezza_coda),
                     self._font_gioco, TITOLO)
        if coda:
            self._scrivi(disegno, (self.width - 2, basso), coda,
                         self._font_gioco,
                         GUADAGNO if guadagno else SPENTO, destra=True)
        return immagine

    def _disegna_notifica(self, voce):
        """La partenza: il nome, quello che ha avviato, e da dove si sa.

        ```
        ------------------------------------------------
        GILLO ha avviato
        Super Mario World                    SNES  12.480
        ```
        """
        immagine, disegno = self._tela()
        disegno.line([(0, 0), (self.width - 1, 0)], fill=RIGA)
        alto = 2
        larghezza = self._scrivi(disegno, (2, alto), voce["nome"],
                                 self._font_gioco, NOME)
        self._scrivi(disegno, (2 + larghezza + 4, alto),
                     self.t("player.panel.avviato"), self._font_gioco, SPENTO)

        mezzo = int(self.height * 0.34)
        self._scrivi(disegno, (2, mezzo),
                     self._stringi(disegno, voce.get("gioco", ""),
                                   self._font_nome, self.width - 6),
                     self._font_nome, TITOLO)

        basso = int(self.height * 0.78)
        self._scrivi(disegno, (2, basso), voce.get("sistema", ""),
                     self._font_piccolo, SPENTO)
        punti = _mille(voce.get("punti", 0))
        if punti:
            self._scrivi(disegno, (self.width - 2, basso),
                         self.t("player.panel.punti", points=punti),
                         self._font_piccolo, PUNTI, destra=True)
        return immagine


def _mille(numero):
    """12480 -> "12.480". Un punteggio si legge a gruppi di tre."""
    try:
        numero = int(numero)
    except (TypeError, ValueError):
        return ""
    if numero <= 0:
        return ""
    return "{:,}".format(numero).replace(",", ".")
