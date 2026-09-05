# -*- coding: utf-8 -*-
"""La webcam sul pannello, dal vivo.

Il lavoro vero — aprire la telecamera, tenerla accesa il meno possibile,
ridurre i colori — sta in `webcam.py`. Qui c'e' solo il pezzo che riguarda
l'arbitro: quando questa sorgente ha qualcosa da mostrare e con quanta
insistenza lo chiede.
"""

import webcam

from .base import Source


class TelecameraSource(Source):
    name = "webcam"
    label = "Funcam"

    # Sopra il Media Player (50), sotto il Rolling Banner (55).
    #
    # Il ragionamento: acceso il servizio, la ripresa dal vivo **e'** quello
    # che si vuole vedere, quindi deve stare sopra la rotazione di foto e
    # video, che altrimenti la interromperebbe a intervalli casuali. Ma resta
    # sotto tutto cio' che ha qualcosa da **dire** — scritte, compleanni,
    # scadenze, musica, aerei, e naturalmente ZeDMD: un avviso che non compare
    # perche' c'e' la telecamera accesa sarebbe un avviso perso.
    #
    # 51 e non 50: a parita' l'arbitro tiene chi ha registrato per primo, e un
    # pareggio qui vorrebbe dire una sorgente che tace per sempre.
    priority = 51

    def __init__(self, cfg, width, height):
        super().__init__(cfg, width, height)
        self._cattura = webcam.Cattura(cfg, width, height)
        self._ultimo_numero = 0
        self._immagine = None

    # --------------------------------------------------------- ciclo di vita

    def start(self):
        self._cattura.avvia()

    def stop(self):
        self._cattura.ferma()
        self._ultimo_numero = 0
        self._immagine = None

    @property
    def cattura(self):
        """La cattura condivisa: la pagina web scatta le foto da qui.

        La telecamera e' una sola e non si apre due volte: se la pagina
        aprisse una seconda cattura per fare uno scatto, il secondo `open`
        fallirebbe — o peggio, riuscirebbe, raddoppiando il carico che stiamo
        cercando di tenere basso.
        """
        return self._cattura

    # ------------------------------------------------------------- contenuto

    def active(self):
        """Vero finche' c'e' un fotogramma da mostrare.

        Chiedere qui il fotogramma ha un effetto voluto: segna che qualcuno
        sta guardando, e tiene sveglia la cattura. Quando questa sorgente
        perde il pannello, `active` smette di essere chiamata, nessuno segna
        piu' niente, e dopo venti secondi la telecamera si spegne da sola.
        """
        if not self.enabled:
            return False
        numero, _quadro = self._cattura.fotogramma()
        if self._cattura.in_pausa():
            # Si era spenta perche' il pannello era di qualcun altro, o
            # perche' un tentativo era andato male. In tutti e due i casi
            # adesso qualcuno guarda: si riprova. Nel secondo che ffmpeg
            # impiega a tornare si continua a mostrare l'ultimo fotogramma —
            # meglio di un buco nero — ma solo per `VALIDO_PER` secondi, dopo
            # i quali `fotogramma` smette di offrirlo e la sorgente sparisce.
            #
            # `attendi=False`: questo metodo lo chiama l'arbitro trenta volte
            # al secondo e non puo' restare fermo ad aspettare che un processo
            # chiuda. Se trova occupato riprova al giro dopo.
            self._cattura.avvia(attendi=False)
        return bool(numero)

    def frame(self):
        numero, quadro = self._cattura.fotogramma()
        if not numero or quadro is None:
            return None
        if numero == self._ultimo_numero and self._immagine is not None:
            # Stesso fotogramma di prima: il pannello disegna piu' in fretta
            # di quanto la telecamera produca, e rifare dithering e tavolozza
            # sugli stessi pixel sarebbe lavoro buttato — proprio quello che
            # si sta cercando di non fare.
            return None
        conf = self.cfg.get("webcam") or {}
        try:
            self._immagine = webcam.rendi(quadro, conf.get("stile", "colori"),
                                          conf.get("livelli_grigio", 4),
                                          conf.get("contrasto_auto", True),
                                          conf.get("livelli_colore", 2))
        except Exception as exc:                        # pragma: no cover
            print("[webcam] fotogramma non convertito: %s" % exc)
            return None
        self._ultimo_numero = numero
        return self._immagine

    # ----------------------------------------------------------------- stato

    def status(self, lang=None):
        if not self.enabled:
            return self.t("status.disabled", lang)
        stato = self._cattura.stato()
        if stato["errore"] and not stato["acceso"]:
            # L'errore si racconta solo se la telecamera e' davvero ferma: uno
            # inciampo passeggero, gia' superato da un nuovo tentativo
            # riuscito, non deve restare scritto in pagina a spaventare.
            return self.t("webcam.status.error", lang, error=stato["errore"])
        if not stato["acceso"]:
            return self.t("webcam.status.paused", lang)
        if stato["registrando"]:
            return self.t("webcam.status.recording", lang)
        return self.t("webcam.status.live", lang,
                      device=stato["device"] or "—")
