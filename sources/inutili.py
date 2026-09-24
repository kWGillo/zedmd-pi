# -*- coding: utf-8 -*-
"""Info inutili: il santo, i nomi che festeggiano, la giornata mondiale, e
chi e' nato o morto oggi.

Perche' esiste
--------------
E' l'unico servizio del pannello che non serve a niente, ed e' probabilmente
quello che verra' letto di piu': gli altri rispondono a una domanda -- che ore
sono, che tempo fa, quando scade il bollo -- questo fa compagnia.

Due schermate, e non e' estetica
--------------------------------
1. **Oggi si festeggia**: santo del giorno, i nomi che festeggiano, la
   giornata mondiale. Tutto da due CSV dentro il programma: **non serve la
   rete**, mai.
2. **Accadde oggi**: un nato e un morto famosi, da Wikipedia. E' l'unica
   parte che dipende dalla rete, ed e' anche l'unica che puo' sparire senza
   fare danno: senza dati la seconda schermata non si fa e il servizio dura
   la meta'. Si accorcia, non si rompe.

La riga che fa fare una telefonata
----------------------------------
In fondo alla prima schermata, quando capita, c'e' **l'onomastico dei tuoi**:
i nomi del giorno confrontati con quelli di `compleanni.csv`. Le altre righe
si leggono; questa fa prendere il telefono. Il confronto e' locale: nessun
nome esce di casa.

Il turno
--------
Il servizio prende il pannello **subito dopo il meteo**, una volta per giro,
ed e' il motivo per cui non ha una finestra sua che si apre da sola: e'
`Turni` a chiamarlo quando e' la sua volta.
"""

import threading
import time
from datetime import datetime

from PIL import Image, ImageDraw

import inutili as dati

from .base import Source
from .clock import _load_font

# --------------------------------------------------------------------- colori

# La grammatica del pannello e' quella dell'orologio e del meteo: ambra per la
# cosa principale, azzurro per quella di contorno, grigio per le etichette.
FESTA = (0xFF, 0x8C, 0x1A)          # il santo
NOMI = (0xE0, 0xE4, 0xF0)           # i nomi che festeggiano
TUOI = (0x60, 0xC8, 0xB0)           # l'onomastico di uno dei tuoi: verde, salta all'occhio
GIORNATA = (0x40, 0xB8, 0xFF)       # la giornata mondiale
DATA = (0x78, 0x80, 0x90)
ANNO_EVENTO = (0xFF, 0x8C, 0x1A)    # l'anno del fatto storico: come il santo
NATO = (0x9A, 0xD8, 0x6A)
MORTO = (0xB0, 0x90, 0xD0)
ANNO = (0x78, 0x80, 0x90)
TITOLO = (0xC0, 0xC6, 0xD2)

MESI = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre")

# Ogni quanto si prova a chiedere a Wikipedia, e quando conviene farlo: poco
# dopo mezzanotte il giorno e' cambiato e la cache serve nuova.
OGNI_MINUTI = 30


class InutiliSource(Source):
    name = "inutili"
    label = "Info inutili"
    priority = 49                    # sotto il media, sopra niente: il turno lo da' Turni

    def __init__(self, cfg, width, height):
        Source.__init__(self, cfg, width, height)
        self._lock = threading.Lock()
        self._image = None
        self._dirty = False
        self._fino_a = 0.0
        self._durata = 0.0
        self._slide = ""
        self._running = False
        self._vista = False
        self._comparse = 0
        self._prossima = "festa"     # da quale delle due si comincia il giro
        self.storia = dati.Storia(self._cartella())
        self._thread = None
        self._wake = threading.Event()
        self._font_grande = _load_font(max(13, int(height * 0.33)))
        self._font_medio = _load_font(max(9, int(height * 0.22)))
        self._font_piccolo = _load_font(max(7, int(height * 0.17)))

    def _cartella(self):
        radar = self.cfg.get("air_radar") or {}
        return radar.get("log_path") or dati.DATA_DIR

    def conf(self):
        return self.cfg.get("inutili") or {}

    # ------------------------------------------------------------------ vita

    def start(self):
        if self._running:
            return
        self._running = True
        self._wake.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._wake.set()
        self._fino_a = 0.0
        with self._lock:
            self._image = None
            self._dirty = False

    def _loop(self):
        """Una sola cosa da fare: tenere fresca la cache di Wikipedia."""
        self._wake.wait(25)
        while self._running:
            try:
                if self.conf().get("personaggi", True):
                    self.storia.aggiorna()
            except Exception as exc:              # pragma: no cover - difensivo
                print("[inutili] aggiornamento fallito: %s" % exc)
            self._wake.wait(OGNI_MINUTI * 60)
            self._wake.clear()

    # --------------------------------------------------------------- pannello

    def active(self):
        return self._running and time.time() < self._fino_a

    def frame(self):
        with self._lock:
            if not self._dirty or self._image is None:
                return None
            self._dirty = False
            return self._image

    def in_onda(self):
        if self._vista:
            return
        self._vista = True
        self._comparse += 1
        if self._durata:
            self._fino_a = time.time() + self._durata

    # ----------------------------------------------------------------- turno

    def slide_disponibili(self, adesso=None):
        """Quali schermate si potrebbero fare adesso.

        La prima c'e' sempre: e' calendario, e il calendario ce l'abbiamo in
        casa. Le altre due ci sono solo se Wikipedia ha risposto almeno una
        volta -- e sono quelle che, senza rete, semplicemente non si fanno.
        """
        conf = self.conf()
        pronte = []
        if conf.get("calendario", True):
            pronte.append("festa")
        if conf.get("eventi", True) and self.storia.eventi(self._quando(adesso)):
            pronte.append("eventi")
        if conf.get("personaggi", True) and self._ha_personaggi(adesso):
            pronte.append("storia")
        return pronte

    @staticmethod
    def _quando(adesso=None):
        return (adesso or datetime.now()).timetuple()

    def coda_del_turno(self, adesso=None):
        """Le schermate di **questo** turno, in ordine.

        Non tutte insieme: tre schermate di fila sono oltre venti secondi, e
        un servizio che non serve a niente non puo' tenere il pannello per
        mezzo minuto. Il calendario c'e' sempre, e dietro di lui si alternano
        i fatti storici e i personaggi -- un passaggio l'uno, un passaggio
        l'altro. Cosi' due comparse di fila non dicono mai la stessa cosa.
        """
        pronte = self.slide_disponibili(adesso)
        dietro = [s for s in ("eventi", "storia") if s in pronte]
        coda = [s for s in pronte if s == "festa"]
        if dietro:
            coda.append(dietro[self._comparse % len(dietro)])
        return coda

    def durata_di(self, slide):
        """Quanti secondi sta su una schermata.

        I fatti storici hanno la loro durata, piu' lunga: sono due righe di
        testo da leggere, non tre parole da riconoscere.
        """
        conf = self.conf()
        if slide == "eventi":
            return max(3, int(conf.get("durata_eventi", 10) or 10))
        return max(3, int(conf.get("durata_slide", 6) or 6))

    def _ha_personaggi(self, adesso=None):
        quando = (adesso or datetime.now()).timetuple()
        if self.storia.nati(quando):
            return True
        return bool(self.conf().get("morti", True) and self.storia.morti(quando))

    def apri_turno(self, adesso=None):
        """Il turno: le schermate disponibili, una di fila all'altra.

        Torna True se il pannello e' stato preso. Le due schermate si fanno
        nello stesso turno, una dopo l'altra: e' il "si accorcia, non si
        rompe" -- se la seconda non c'e', il turno dura la meta'.
        """
        if not self._running:
            return False
        adesso = adesso or datetime.now()
        coda = self.coda_del_turno(adesso)
        if not coda:
            return False
        self._coda = coda[1:]
        self._apri(coda[0], self.durata_di(coda[0]))
        return bool(self._slide)

    def _apri(self, slide, secondi):
        try:
            immagine = self._disegna(slide)
        except Exception as exc:                  # pragma: no cover - difensivo
            print("[inutili] disegno fallito: %s" % exc)
            self._slide = ""
            self._fino_a = 0.0
            return
        with self._lock:
            self._image = immagine
            self._dirty = True
        self._slide = slide
        self._vista = False
        self._durata = float(secondi)
        self._fino_a = time.time() + self._durata

    def avanza(self):
        """La schermata dopo, se ce n'e' un'altra in coda. Torna True se ha
        aperto qualcosa: la chiama `Turni` quando la prima e' finita."""
        coda = getattr(self, "_coda", None)
        if not coda or not self._running:
            return False
        prossima = coda.pop(0)
        self._apri(prossima, self.durata_di(prossima))
        return bool(self._slide)

    def mostra_adesso(self, slide="festa", secondi=None):
        """Il pulsante di prova della pagina web."""
        if slide in ("storia", "eventi"):
            pronta = (self._ha_personaggi() if slide == "storia"
                      else bool(self.storia.eventi(self._quando())))
            if not pronta:
                _fatto, motivo = self.storia.aggiorna(forza=True)
                pronta = (self._ha_personaggi() if slide == "storia"
                          else bool(self.storia.eventi(self._quando())))
                if not pronta:
                    return False, motivo or "niente da mostrare"
        self._coda = []
        self._apri(slide, secondi or self.durata_di(slide))
        return bool(self._slide), ""

    # --------------------------------------------------------------- disegno

    def disegna_campo(self, img, px):             # pragma: no cover - non usata
        pass

    def _disegna(self, slide):
        img = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        d = ImageDraw.Draw(img)
        if slide == "storia":
            self._storia(d)
        elif slide == "eventi":
            self._eventi(d)
        else:
            self._festa(d)
        return img

    # ---- schermata 1: oggi si festeggia

    def _festa(self, d, adesso=None):
        adesso = adesso or datetime.now()
        quando = adesso.timetuple()
        margine = 3
        disponibile = self.width - margine * 2

        d.text((margine, 1), self._data(adesso), font=self._font_piccolo, fill=DATA)

        # In fondo: l'onomastico dei tuoi se c'e', altrimenti la giornata
        # mondiale. Chi conosci viene prima del mondo.
        tuoi = dati.onomastici_tuoi(quando)
        if tuoi:
            coda = ("onomastico di %s" % ", ".join(tuoi), TUOI)
        else:
            giornata = dati.giornata(quando)
            coda = (giornata, GIORNATA) if giornata else None

        santo = dati.santo(quando)
        font = self._font_grande
        if self._largo(d, santo, font) > disponibile:
            font = self._font_medio

        # Quando in fondo non c'e' niente -- capita un giorno su due -- la
        # schermata respira invece di lasciare mezzo pannello vuoto: il santo
        # e i nomi scendono al centro.
        alto_santo = int(self.height * 0.17) + 2
        if coda is None:
            alto_santo = int(self.height * 0.30)
        d.text((margine, alto_santo), self._taglia(d, santo, font, disponibile),
               font=font, fill=FESTA)

        riga = alto_santo + (self._alto(d, font) or int(self.height * 0.3)) + 3
        nomi = dati.nomi(quando)[:5]
        if nomi:
            testo = self._taglia(d, " · ".join(nomi), self._font_piccolo, disponibile)
            d.text((margine, riga), testo, font=self._font_piccolo, fill=NOMI)

        if coda is not None:
            basso = self.height - int(self.height * 0.17) - 2
            d.text((margine, basso), self._taglia(d, coda[0], self._font_piccolo, disponibile),
                   font=self._font_piccolo, fill=coda[1])

    def _data(self, adesso):
        return "%d %s" % (adesso.day, MESI[adesso.month - 1].upper())

    # ---- schermata 2: accadde oggi (i fatti)

    def _eventi(self, d, adesso=None):
        """L'anno grande a sinistra, il fatto a destra su due o tre righe.

        L'anno e' la cosa che si guarda per prima -- «1969» dice gia' mezza
        storia -- quindi sta da solo, grande, e il testo gli scorre accanto
        invece di andargli sotto.
        """
        adesso = adesso or datetime.now()
        quando = adesso.timetuple()
        margine = 3
        d.text((margine, 1), "ACCADDE OGGI", font=self._font_piccolo, fill=TITOLO)
        fatti = self.storia.eventi(quando)
        if not fatti:                              # pragma: no cover - difensivo
            d.text((margine, int(self.height * 0.4)), "niente da raccontare",
                   font=self._font_medio, fill=DATA)
            return
        anno, testo = fatti[self._comparse % len(fatti)]
        d.text((margine, int(self.height * 0.30)), str(anno),
               font=self._font_grande, fill=ANNO_EVENTO)
        sinistra = margine + self._largo(d, "0000", self._font_grande) + 6
        disponibile = self.width - sinistra - margine
        righe = self._a_capo(d, testo, self._font_piccolo, disponibile, 3)
        alto = int(self.height * 0.17) + 1
        passo = int(self.height * 0.22)
        for i, riga in enumerate(righe):
            d.text((sinistra, alto + i * passo), riga,
                   font=self._font_piccolo, fill=NOMI)

    def _a_capo(self, d, testo, font, disponibile, quante):
        """Il testo spezzato in righe che ci stanno, al massimo `quante`.

        Sul pannello non c'e' l'andare a capo automatico: se non si spezza a
        mano, la frase esce dal vetro. L'ultima riga, se il testo non finisce,
        prende i puntini.
        """
        parole = testo.split()
        righe, riga = [], ""
        for parola in parole:
            prova = (riga + " " + parola).strip()
            if riga and self._largo(d, prova, font) > disponibile:
                righe.append(riga)
                riga = parola
                if len(righe) == quante:
                    break
            else:
                riga = prova
        if len(righe) < quante and riga:
            righe.append(riga)
        if len(righe) == quante and parole:
            # E' rimasto fuori qualcosa?
            scritte = " ".join(righe)
            if len(scritte) < len(testo):
                righe[-1] = self._taglia(d, righe[-1] + "…", font, disponibile)
        return righe

    # ---- schermata 3: nati e morti

    def _storia(self, d, adesso=None):
        adesso = adesso or datetime.now()
        quando = adesso.timetuple()
        margine = 3
        disponibile = self.width - margine * 2
        d.text((margine, 1), "NATI E MORTI", font=self._font_piccolo, fill=TITOLO)

        conf = self.conf()
        righe = []
        nati = self.storia.nati(quando)
        morti = self.storia.morti(quando) if conf.get("morti", True) else []
        scelta = self._comparse
        if nati:
            righe.append(("nato", nati[scelta % len(nati)]))
        if morti:
            righe.append(("morto", morti[scelta % len(morti)]))
        if len(righe) == 1 and nati and len(nati) > 1:
            # Con i morti spenti si mostrano due nati: la schermata resta piena.
            righe.append(("nato", nati[(scelta + 1) % len(nati)]))

        y = int(self.height * 0.28)
        passo = int(self.height * 0.30)
        for tipo, (anno, nome, mestiere) in righe[:2]:
            colore = NATO if tipo == "nato" else MORTO
            segno = "*" if tipo == "nato" else "+"
            d.text((margine, y), segno, font=self._font_medio, fill=colore)
            x = margine + 8
            d.text((x, y), str(anno), font=self._font_medio, fill=ANNO)
            x += self._largo(d, str(anno), self._font_medio) + 5
            resto = self.width - margine - x
            testo = nome
            if mestiere and self._largo(d, "%s, %s" % (nome, mestiere),
                                        self._font_medio) <= resto:
                testo = "%s, %s" % (nome, mestiere)
            d.text((x, y), self._taglia(d, testo, self._font_medio, resto),
                   font=self._font_medio, fill=NOMI)
            y += passo

        if not righe:                             # pragma: no cover - difensivo
            d.text((margine, int(self.height * 0.4)), "niente da raccontare",
                   font=self._font_medio, fill=DATA)

    # ------------------------------------------------------------- utilita'

    def _largo(self, d, testo, font):
        try:
            riquadro = d.textbbox((0, 0), testo, font=font)
            return riquadro[2] - riquadro[0]
        except AttributeError:                    # pragma: no cover - PIL vecchia
            return d.textsize(testo, font=font)[0]

    def _alto(self, d, font):
        try:
            riquadro = d.textbbox((0, 0), "Ag", font=font)
            return riquadro[3] - riquadro[1]
        except AttributeError:                    # pragma: no cover - PIL vecchia
            return d.textsize("Ag", font=font)[1]

    def _taglia(self, d, testo, font, disponibile):
        """Quello che ci sta, con i puntini. Sul pannello non c'e' «a capo»."""
        if self._largo(d, testo, font) <= disponibile:
            return testo
        accorciato = testo
        while accorciato and self._largo(d, accorciato + "…", font) > disponibile:
            accorciato = accorciato[:-1]
        return (accorciato.rstrip(" ·,") + "…") if accorciato else ""

    # ------------------------------------------------------------------ stato

    def status(self, lang=None):
        if not self._running:
            return self.t("status.disabled", lang)
        quando = datetime.now().timetuple()
        santo = dati.santo(quando)
        if self._ha_personaggi():
            return self.t("inutili.status.ok", lang, santo=santo)
        if not self.conf().get("personaggi", True):
            return self.t("inutili.status.solo", lang, santo=santo)
        motivo = self.storia.errore()
        if motivo:
            # Se i personaggi non arrivano, la pagina deve dire **perche'**:
            # e' l'unica parte del servizio che puo' non funzionare, e una
            # riga che dice solo "non ancora scaricati" non aiuta nessuno.
            return self.t("inutili.status.errore", lang, santo=santo, motivo=motivo)
        return self.t("inutili.status.attesa", lang, santo=santo)

    def riepilogo(self):
        """Quello che il servizio sa di oggi: per la pagina e per MQTT."""
        quando = datetime.now().timetuple()
        riassunto = dati.riepilogo(quando, self.storia)
        riassunto["slide"] = self.slide_disponibili()
        riassunto["turno"] = self.coda_del_turno()
        riassunto["comparse"] = self._comparse
        return riassunto
