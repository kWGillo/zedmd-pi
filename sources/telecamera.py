# -*- coding: utf-8 -*-
"""La webcam sul pannello, dal vivo.

Il lavoro vero — aprire la telecamera, tenerla accesa il meno possibile,
ridurre i colori — sta in `webcam.py`; il pulsante fisico in `pulsante.py`.
Qui c'e' il pezzo che riguarda l'arbitro — quando questa sorgente ha
qualcosa da mostrare — e i tre stati in cui puo' trovarsi.

Il servizio arma, non accende
-----------------------------
Una regola sola, e vale sempre.

L'interruttore nella pagina Servizi **non accende la telecamera**: dice che
la si puo' accendere. La ripresa parte solo quando qualcuno la chiama — il
pulsante fisico, o i due comandi nella pagina Funcam. A servizio spento il
pulsante non fa niente, e il piedino non e' nemmeno aperto.

Nelle prime stesure questo valeva solo con il pulsante fisico attivo, e senza
pulsante il servizio accendeva la ripresa come una sorgente qualsiasi. Era un
errore di impostazione: legava il momento in cui una webcam in soggiorno si
accende a una casella che riguarda tutt'altro — se un pulsante e' stato
saldato o no. Su una telecamera, *quando si accende* e' la domanda
importante, e la risposta non puo' dipendere da un dettaglio di cablaggio.
"""

import time

import pulsante as pulsante_mod
import webcam

from .base import Source

# Quanti secondi di conto alla rovescia prima dello scatto. Tre: il tempo di
# togliere la mano dal pulsante e mettersi in posa.
ATTESA_SCATTO = 3.0

# Per quanto resta a schermo la foto appena scattata, prima di tornare alla
# ripresa dal vivo. Serve a vedere **cosa** si e' scattato: senza, lo scatto
# sparirebbe nell'istante in cui avviene e non si saprebbe se e' riuscito.
MOSTRA_SCATTO = 2.0


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
        self._ultimo_conto = 0
        self._immagine = None

        self._pulsante = None
        # Acceso o spento **secondo il pulsante**. Senza pulsante non conta:
        # comanda il servizio, come e' sempre stato.
        self._dal_vivo = False
        self._scatto_alle = 0.0     # quando scatta, 0 = nessun conto in corso
        self._mostra_fino = 0.0     # fin quando resta a schermo lo scatto
        self._scattata = None       # l'immagine appena scattata
        self._font = None

    # --------------------------------------------------------- ciclo di vita

    def _conf_pulsante(self):
        return (self.cfg.get("webcam") or {}).get("pulsante") or {}

    def con_pulsante(self):
        return bool(self._conf_pulsante().get("enabled"))

    def start(self):
        """Il servizio e' acceso: da adesso la telecamera **si puo'** accendere.

        Non si apre niente. Aprirla adesso vorrebbe dire tenerla accesa per
        ore in attesa di un dito, che e' esattamente cio' che si sta
        evitando.
        """
        self._dal_vivo = False
        if not self.con_pulsante():
            # Nessun pulsante saldato: si accende dai due comandi della
            # pagina. Il piedino non si apre, perche' non c'e' niente da
            # leggere.
            return
        gpio = self._conf_pulsante().get("gpio", pulsante_mod.GPIO_PREDEFINITO)
        self._pulsante = pulsante_mod.Pulsante(
            gpio, su_clic=self._clic, su_tenuta=self._tenuta)
        aperto, motivo = self._pulsante.avvia()
        if not aperto:
            # Il pulsante non si e' aperto: libreria assente, piedino gia'
            # occupato, un errore qualsiasi.
            #
            # La prima versione qui accendeva la telecamera "per non lasciarla
            # irraggiungibile". Era il rovescio esatto di cio' che l'utente ha
            # chiesto: chi accende il pulsante vuole una webcam **spenta**
            # finche' non la chiama, e rispondere a un guasto lasciandola
            # accesa in soggiorno per giorni e' la peggiore delle
            # interpretazioni possibili.
            #
            # Quindi resta spenta, e a non lasciarla irraggiungibile ci pensa
            # la pagina, che ha i suoi due pulsanti.
            print("[webcam] pulsante non disponibile: %s" % motivo)

    def stop(self):
        if self._pulsante is not None:
            self._pulsante.ferma()
            self._pulsante = None
        self._cattura.ferma()
        self._dal_vivo = False
        self._scatto_alle = 0.0
        self._mostra_fino = 0.0
        self._scattata = None
        self._ultimo_numero = 0
        self._ultimo_conto = 0
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

    # -------------------------------------------------------------- pulsante

    def _clic(self):
        """Un clic: accende, oppure scatta fra tre secondi."""
        if not self.enabled:
            return
        if not self._dal_vivo:
            self._dal_vivo = True
            self._cattura.avvia(attendi=False)
            return
        if self._scatto_alle:
            # Gia' in conto alla rovescia: un secondo clic non lo raddoppia e
            # non lo annulla. Sarebbe un gesto in piu' da ricordare, e questo
            # pulsante ne ha gia' tre.
            return
        self._scatto_alle = time.time() + ATTESA_SCATTO

    def _tenuta(self):
        """Tenuto premuto: spegne, e annulla un eventuale conto in corso."""
        if not self.enabled:
            return
        self._dal_vivo = False
        self._scatto_alle = 0.0
        self._mostra_fino = 0.0
        self._scattata = None
        self._cattura.ferma()

    def accendi(self):
        """Accende la ripresa. La chiama la pagina, come farebbe un clic."""
        self._clic()

    def spegni(self):
        """Spegne la ripresa. La chiama la pagina, come una pressione lunga."""
        self._tenuta()

    def riarma(self):
        """Richiude e riapre il pulsante, senza toccare la telecamera.

        Serve dopo aver installato `gpiozero` dalla pagina: la libreria adesso
        c'e', ma il piedino era stato dichiarato non apribile all'avvio del
        servizio. Senza questo si dovrebbe spegnere e riaccendere il servizio,
        che e' una spiegazione in piu' da dare e da ricordare.
        """
        if self._pulsante is not None:
            self._pulsante.ferma()
            self._pulsante = None
        if not self.con_pulsante() or not self.enabled:
            return False, "pulsante non richiesto"
        gpio = self._conf_pulsante().get("gpio", pulsante_mod.GPIO_PREDEFINITO)
        self._pulsante = pulsante_mod.Pulsante(
            gpio, su_clic=self._clic, su_tenuta=self._tenuta)
        return self._pulsante.avvia()

    def stato_pulsante(self):
        if self._pulsante is None:
            return {"aperto": False, "gpio": 0, "errore": "", "ultimo": 0}
        return self._pulsante.stato()

    def dal_vivo(self):
        return self._dal_vivo

    # ------------------------------------------------------------- contenuto

    def active(self):
        """Vero finche' c'e' qualcosa da mostrare.

        Chiedere qui il fotogramma ha un effetto voluto: segna che qualcuno
        sta guardando, e tiene sveglia la cattura. Quando questa sorgente
        perde il pannello, `active` smette di essere chiamata, nessuno segna
        piu' niente, e dopo venti secondi la telecamera si spegne da sola.
        """
        if not self.enabled:
            return False
        if not self._dal_vivo:
            # Nessuno l'ha accesa: il pannello e' di chi viene dopo.
            return False
        if self._mostra_fino and time.time() < self._mostra_fino:
            return True
        numero, _quadro = self._cattura.fotogramma()
        if self._cattura.in_pausa():
            # Si era spenta perche' il pannello era di qualcun altro, o
            # perche' un tentativo era andato male. In tutti e due i casi
            # adesso qualcuno guarda: si riprova. Nel secondo che ffmpeg
            # impiega a tornare si continua a mostrare l'ultimo fotogramma —
            # meglio di un buco nero — ma solo per `VALIDO_PER` secondi.
            #
            # `attendi=False`: questo metodo lo chiama l'arbitro trenta volte
            # al secondo e non puo' restare fermo ad aspettare che un processo
            # chiuda. Se trova occupato riprova al giro dopo.
            self._cattura.avvia(attendi=False)
        return bool(numero)

    def frame(self):
        adesso = time.time()

        # 1. La foto appena scattata resta a schermo qualche secondo.
        if self._mostra_fino:
            if adesso < self._mostra_fino:
                fresca, self._scattata = self._scattata, None
                return fresca          # una volta sola: poi non cambia piu'
            self._mostra_fino = 0.0
            self._ultimo_numero = 0    # la ripresa va ridisegnata da capo

        # 2. Il conto alla rovescia scade: si scatta.
        if self._scatto_alle and adesso >= self._scatto_alle:
            self._scatto_alle = 0.0
            self._scatta()
            return self._scattata if self._scattata is not None else None

        numero, quadro = self._cattura.fotogramma()
        if not numero or quadro is None:
            return None

        # 3. Durante il conto alla rovescia il numero cambia ogni secondo,
        # quindi il fotogramma va ridisegnato anche quando la telecamera non
        # ne ha prodotti di nuovi.
        conto = self._mancano()
        if numero == self._ultimo_numero and conto == self._ultimo_conto:
            # Stesso fotogramma e stesso numero: rifare dithering e tavolozza
            # sugli stessi pixel sarebbe lavoro buttato — proprio quello che
            # si sta cercando di non fare.
            return None

        immagine = self._rendi(quadro)
        if immagine is None:
            return None
        if conto:
            immagine = self._con_numero(immagine, conto)
        self._ultimo_numero = numero
        self._ultimo_conto = conto
        self._immagine = immagine
        return immagine

    def _mancano(self):
        """Secondi che restano al conto alla rovescia, 0 se non e' in corso."""
        if not self._scatto_alle:
            return 0
        return max(1, int(round(self._scatto_alle - time.time())))

    def _rendi(self, quadro):
        conf = self.cfg.get("webcam") or {}
        try:
            return webcam.rendi(quadro, conf.get("stile", "colori"),
                                conf.get("livelli_grigio", 4),
                                conf.get("contrasto_auto", True),
                                conf.get("livelli_colore", 2))
        except Exception as exc:                        # pragma: no cover
            print("[webcam] fotogramma non convertito: %s" % exc)
            return None

    def _con_numero(self, immagine, quanti):
        """Il numero del conto alla rovescia, grande, in mezzo al pannello."""
        from PIL import ImageDraw
        if self._font is None:
            from .clock import _load_font
            self._font = _load_font(max(12, int(self.height * 0.8)))
        penna = ImageDraw.Draw(immagine)
        testo = str(quanti)
        try:
            riquadro = penna.textbbox((0, 0), testo, font=self._font)
            largo, alto = riquadro[2] - riquadro[0], riquadro[3] - riquadro[1]
            x = (self.width - largo) // 2 - riquadro[0]
            y = (self.height - alto) // 2 - riquadro[1]
        except Exception:                               # pragma: no cover
            x, y = self.width // 2, 0
        # Contorno nero prima, numero bianco poi: sopra una ripresa qualsiasi
        # un numero bianco e basta sparirebbe su un fondo chiaro.
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    penna.text((x + dx, y + dy), testo, font=self._font,
                               fill=(0, 0, 0))
        penna.text((x, y), testo, font=self._font, fill=(255, 255, 255))
        return immagine

    def _scatta(self):
        percorso, motivo = self._cattura.scatta()
        if not percorso:
            print("[webcam] scatto non riuscito: %s" % motivo)
            return
        print("[webcam] scattata %s" % percorso)
        try:
            from PIL import Image
            with Image.open(percorso) as scatto:
                self._scattata = scatto.convert("RGB").copy()
        except Exception:                               # pragma: no cover
            self._scattata = None
        self._mostra_fino = time.time() + MOSTRA_SCATTO
        self._ultimo_numero = 0
        self._ultimo_conto = 0

    # ----------------------------------------------------------------- stato

    def status(self, lang=None):
        if not self.enabled:
            return self.t("status.disabled", lang)
        if self.con_pulsante() and self.stato_pulsante()["errore"]:
            return self.t("webcam.status.button.error", lang,
                          error=self.stato_pulsante()["errore"])
        if not self._dal_vivo:
            if self.con_pulsante() and self.stato_pulsante()["aperto"]:
                return self.t("webcam.status.armed", lang,
                              gpio=self.stato_pulsante()["gpio"])
            return self.t("webcam.status.armed.page", lang)
        if self._scatto_alle:
            return self.t("webcam.status.countdown", lang,
                          seconds=self._mancano())
        stato = self._cattura.stato()
        if stato["errore"] and not stato["acceso"]:
            # L'errore si racconta solo se la telecamera e' davvero ferma: un
            # inciampo passeggero, gia' superato da un nuovo tentativo
            # riuscito, non deve restare scritto in pagina a spaventare.
            return self.t("webcam.status.error", lang, error=stato["errore"])
        if not stato["acceso"]:
            return self.t("webcam.status.paused", lang)
        if stato["registrando"]:
            return self.t("webcam.status.recording", lang)
        return self.t("webcam.status.live", lang, device=stato["device"] or "—")
