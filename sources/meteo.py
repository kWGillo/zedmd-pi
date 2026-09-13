"""Meteo sul pannello: il bollettino del mattino e l'aggiornamento ogni tot ore.

Due finestre, non una, e la differenza non e' la quantita' di dati ma **a che
domanda rispondono**.

*Il bollettino del mattino* risponde a "come mi vesto, esco a piedi o prendo la
macchina". Si guarda una volta, a colazione, e deve dire la giornata intera:
massima, minima, umidita', che tempo fara'. E' il momento in cui il pannello
somiglia di piu' a un notiziario.

*L'aggiornamento* risponde a "adesso". Meno numeri, piu' grandi: quanti gradi
fa in questo istante, e l'icona. Il resto sta li' di contorno.

Perche' non e' una sorgente sempre accesa. Un pannello che mostra il meteo
tutto il giorno smette di essere guardato dopo due giorni: diventa sfondo. Una
finestra che compare quattro volte al giorno e poi se ne va, invece, la si
legge -- e' la stessa ragione per cui i Compleanni e le Scadenze parlano poco.

Perche' non prende il pannello a forza. Il meteo non e' mai urgente: nessuno
deve sapere la temperatura **adesso** al punto da interrompere una partita o
un passaggio della Stazione. Niente `hold_on`, e priorita' sotto tutto quello
che ha un orario.

Il lavoro di rete sta in un thread suo. Una chiamata HTTP puo' metterci dodici
secondi a fallire, e il ciclo che disegna gira a trenta fotogrammi al secondo:
chiedere il meteo da dentro `active()` vorrebbe dire dodici secondi di pannello
fermo, cioe' un guasto visibile causato da una funzione di contorno.
"""

import threading
import time
from datetime import datetime

from PIL import Image, ImageDraw

import icone
import meteo
from .base import Source
from .clock import _load_font

try:
    import allerte as _allerte
except ImportError:                 # pragma: no cover - solo su copia parziale
    _allerte = None

# --------------------------------------------------------------------- colori

# I due numeri che contano hanno due colori opposti, e si riconoscono senza
# leggere l'etichetta: il caldo e' ambra, il freddo e' azzurro. E' la stessa
# grammatica dell'orologio -- ora ambra, data azzurra -- quindi il pannello
# resta coerente con se stesso.
CALDO = (0xFF, 0x8C, 0x1A)
FREDDO = (0x40, 0xB8, 0xFF)
TESTO = (0xE0, 0xE4, 0xF0)
SPENTO = (0x78, 0x80, 0x90)
UMIDO = (0x60, 0xC8, 0xB0)
VECCHIO = (0xC0, 0x70, 0x40)


class MeteoSource(Source):
    name = "meteo"
    label = "Meteo"
    # Sopra il Media Player (50) e la Funcam (51), sotto il Rolling Banner
    # (55). Il banner e' un testo che qualcuno ha scritto apposta perche'
    # venisse mostrato; il meteo arriva da solo. Fra due cose non urgenti, ha
    # la precedenza quella voluta da una persona.
    #
    # Nessuna priorita' pareggia con un'altra, e una prova lo pretende.
    priority = 54

    def __init__(self, cfg, width, height):
        super().__init__(cfg, width, height)
        self._running = False
        self._lock = threading.Lock()
        self._image = None
        self._dirty = False
        self._fino_a = 0.0
        self._modo = ""
        self._errore = ""
        self._meteo = meteo.Meteo(cfg, self._cartella())
        # Il giorno in cui il bollettino del mattino e' gia' stato dato. Senza
        # questo, alle 7:00 la finestra si riaprirebbe a ogni giro del thread
        # per tutta l'ora.
        self._bollettino_dato = ""
        self._ultimo_aggiornamento = 0.0
        # L'identificativo dell'ultima allerta gia' mostrata. Serve a farla
        # comparire **quando arriva**, senza aspettare il prossimo giro delle
        # quattro ore, e senza ripeterla per tutta la sua durata: un avviso che
        # si ripresenta ogni minuto smette di essere un avviso in mezza
        # giornata.
        self._allerta_vista = ""
        self._wake = threading.Event()
        self._thread = None
        self._font_grande = _load_font(max(14, int(height * 0.42)))
        self._font_medio = _load_font(max(9, int(height * 0.22)))
        self._font_piccolo = _load_font(max(7, int(height * 0.17)))

    # ------------------------------------------------------- configurazione

    def _cartella(self):
        registro = (self.cfg.get("air_radar") or {}).get("log_path") or ""
        import os
        return os.path.dirname(registro) or "/var/lib/dmd"

    def conf(self):
        return self.cfg.get("meteo") or {}

    # ------------------------------------------------------------- ciclo vita

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._wake.set()
        with self._lock:
            self._image = None
            self._dirty = False
        self._fino_a = 0.0
        self._modo = ""

    def active(self):
        return self._running and time.time() < self._fino_a

    def frame(self):
        with self._lock:
            if not self._dirty or self._image is None:
                return None
            self._dirty = False
            return self._image

    # ------------------------------------------------------------------ ciclo

    def _loop(self):
        # Il primo giro non parte subito: all'avvio il servizio ha gia' abbastanza
        # da fare, e una chiamata di rete in quel momento ritarda l'accensione
        # del pannello senza motivo. Il meteo puo' aspettare venti secondi.
        self._wake.wait(20)
        while self._running:
            try:
                self._giro()
            except Exception as exc:      # noqa: BLE001
                # Una sorgente di contorno non deve poter fermare niente. Il
                # motivo finisce nel registro e nella riga di stato, e il giro
                # dopo si riprova.
                self._errore = str(exc)
                print("[meteo] giro fallito: %s" % exc)
            self._wake.wait(60)
            self._wake.clear()

    def _giro(self):
        conf = self.conf()
        adesso = datetime.now()
        ora_bollettino = int(conf.get("ora_bollettino", 7) or 7)
        ogni = max(1, int(conf.get("ogni_ore", 4) or 4))

        oggi = adesso.strftime("%Y-%m-%d")
        tocca_bollettino = (adesso.hour == ora_bollettino
                            and self._bollettino_dato != oggi)
        scaduto = (time.time() - self._ultimo_aggiornamento) >= ogni * 3600

        # Le allerte si guardano a ogni giro, non ogni quattro ore: il modulo
        # ha il suo freno di mezz'ora e non chiama piu' del dovuto, ma un
        # avviso che arriva alle 20:05 non puo' aspettare le 22 per comparire.
        nuova = self._allerta_nuova()
        if nuova is not None:
            self._apri("allerta", int(conf.get("durata_allerta", 25) or 25))
            return

        if not tocca_bollettino and not scaduto:
            return

        # I dati si chiedono **prima** di aprire la finestra: una finestra che
        # si apre e poi resta vuota per dieci secondi mentre la rete risponde
        # e' peggio di una finestra che si apre dieci secondi dopo.
        self._meteo.aggiorna()
        if self._meteo.dati() is None:
            self._errore = self._meteo.errore() or "nessuna previsione"
            # Si segna comunque il tentativo, altrimenti con la rete giu' il
            # giro riproverebbe ogni minuto per sempre.
            self._ultimo_aggiornamento = time.time()
            return

        if tocca_bollettino:
            self._bollettino_dato = oggi
            self._apri("bollettino",
                       int(conf.get("durata_bollettino", 22) or 22))
        else:
            self._apri("aggiornamento",
                       int(conf.get("durata_aggiornamento", 12) or 12))
        self._ultimo_aggiornamento = time.time()

    def _allerta_nuova(self):
        """L'allerta da mostrare adesso, se e' cambiata. Altrimenti None.

        «Cambiata» vuol dire identificativo diverso da quello gia' mostrato: la
        stessa allerta che dura due giorni si vede una volta quando arriva e
        poi vive nella striscia in cima alle altre finestre. Quando scade,
        l'identificativo si dimentica, cosi' se ne arriva un'altra uguale
        domani viene mostrata di nuovo.
        """
        self._meteo.aggiorna_allerte()
        voce = self._meteo.allerta()
        if voce is None:
            self._allerta_vista = ""
            return None
        chiave = voce.get("identificativo") or "%s|%s|%s" % (
            voce.get("zona"), voce.get("tipo"), voce.get("inizio"))
        if chiave == self._allerta_vista:
            return None
        self._allerta_vista = chiave
        return voce

    def _apri(self, modo, secondi):
        self._modo = modo
        self._errore = ""
        try:
            immagine = self._disegna(modo)
        except Exception as exc:          # noqa: BLE001
            # Stessa regola dei satelliti: un disegno che fallisce **molla il
            # pannello** invece di lasciarci sopra l'ultimo fotogramma. Un
            # pannello congelato sembra un guasto dell'hardware, ed e' costato
            # tre versioni per essere capito.
            self._modo = ""
            self._fino_a = 0.0
            self._errore = "disegno: %s" % exc
            print("[meteo] disegno fallito, pannello rilasciato: %s" % exc)
            return
        with self._lock:
            self._image = immagine
            self._dirty = True
        self._fino_a = time.time() + max(4, secondi)

    def mostra_adesso(self, modo="aggiornamento", secondi=12):
        """Apre la finestra subito. E' il pulsante di prova della pagina web."""
        self._meteo.aggiorna()
        if self._meteo.dati() is None:
            return False, self._meteo.errore() or "nessuna previsione"
        self._apri(modo, secondi)
        return bool(self._modo), self._errore or "mostrato"

    # ---------------------------------------------------------------- disegno

    def _disegna(self, modo):
        dati = self._meteo.dati()
        immagine = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        d = ImageDraw.Draw(immagine)
        if modo == "allerta":
            self._allerta(d)
        elif modo == "bollettino":
            self._bollettino(d, dati)
        else:
            self._aggiornamento(d, dati)
        return immagine

    def _allerta(self, d):
        """L'avviso prende tutto il pannello, e non e' una decisione grafica.

        Una striscia in cima al bollettino si legge come un'etichetta; un
        pannello intero si legge come un avviso. Chi passa in corridoio deve
        capire **che c'e' qualcosa** prima di aver letto una parola, e quello
        lo fa il colore su tutta la superficie, non un bordino.
        """
        voce = self._meteo.allerta()
        if voce is None:
            # Scaduta fra il momento in cui si e' deciso di mostrarla e questo:
            # succede, e non e' un errore. Si ripiega sull'aggiornamento.
            self._aggiornamento(d, self._meteo.dati() or {})
            return
        lang = self._lingua()
        colore = (_allerte.COLORI.get(voce.get("livello"), (0xF0, 0xD0, 0x20))
                  if _allerte else (0xF0, 0xD0, 0x20))

        # La barra verticale a sinistra: e' la parte che si vede da lontano.
        d.rectangle([0, 0, 4, self.height - 1], fill=colore)

        lato = int(self.height * 0.62)
        icone.allerta(d, 10, (self.height - lato) // 2, lato, colore)
        sinistra = 10 + lato + 8

        livello = voce.get("livello") or ""
        scritto = (_allerte.livello_scritto(livello, lang) if _allerte
                   else livello)
        titolo = ("ALLERTA %s" % scritto.upper() if str(lang).startswith("it")
                  else "%s ALERT" % livello.upper())
        d.text((sinistra, 1), titolo, font=self._font_piccolo, fill=colore)

        disponibile = self.width - sinistra - 2
        evento = (_allerte.descrizione_evento(voce, lang) if _allerte
                  else voce.get("evento") or "")
        d.text((sinistra, int(self.height * 0.24)),
               self._taglia(d, evento, self._font_medio, disponibile),
               font=self._font_medio, fill=TESTO)

        basso = self.height - int(self.height * 0.19) - 1
        d.text((sinistra, basso),
               self._quando_allerta(d, voce, lang, disponibile),
               font=self._font_piccolo, fill=SPENTO)

    def _taglia(self, d, testo, font, disponibile):
        """Il testo che ci sta, accorciato con i puntini se serve.

        Su un pannello non c'e' «a capo»: quello che eccede non va sulla riga
        dopo, esce dal vetro e sparisce a meta' parola. Meglio dirlo con i
        puntini, che almeno si vede che manca qualcosa.
        """
        if self._largo(d, testo, font) <= disponibile:
            return testo
        accorciato = testo
        while accorciato and self._largo(d, accorciato + "…", font) > disponibile:
            accorciato = accorciato[:-1]
        return (accorciato.rstrip() + "…") if accorciato else ""

    def _quando_allerta(self, d, voce, lang, disponibile):
        """«in corso fino alle 23:59» oppure «fra 10 ore (08:00)».

        Un'allerta senza un quando e' una notizia, non un avviso: la prima
        domanda di chiunque la legga e' se riguarda adesso o stanotte.

        Quando non ci sta tutto, la prima cosa che si toglie e' **il nome
        della regione**, ed e' la scelta giusta: questo pannello mostra solo le
        allerte della regione che hai scelto tu, quindi quel nome e' l'unica
        parte della riga che non aggiunge niente. Il quando resta sempre.
        """
        italiano = str(lang).startswith("it")
        zona = voce.get("zona") or ""
        if voce.get("in_corso"):
            fine = self._ore(voce.get("fine"))
            se_finisce = (("fino alle %s" % fine) if italiano
                          else ("until %s" % fine)) if fine else ""
            quando = " · ".join(p for p in
                                ("in corso" if italiano else "ongoing",
                                 se_finisce) if p)
        else:
            ore = voce.get("fra_ore") or 0.0
            inizio = self._ore(voce.get("inizio"))
            if ore >= 1:
                fra = (("fra %d ore" % int(round(ore))) if italiano
                       else ("in %d hours" % int(round(ore))))
            else:
                fra = ("a breve" if italiano else "shortly")
            quando = ("%s (%s)" % (fra, inizio)) if inizio else fra

        intera = " · ".join(p for p in (zona, quando) if p)
        if self._largo(d, intera, self._font_piccolo) <= disponibile:
            return intera
        return self._taglia(d, quando, self._font_piccolo, disponibile)

    def _tacca_allerta(self, d):
        """Un quadratino colorato in alto a destra durante le altre finestre.

        L'avviso intero e' gia' passato quando e' arrivato; questo serve a chi
        guarda il bollettino due ore dopo e non c'era. Sta accanto al puntino
        del dato vecchio e non ci si sovrappone.
        """
        voce = self._meteo.allerta()
        if voce is None or not _allerte:
            return
        colore = _allerte.COLORI.get(voce.get("livello"), (0xF0, 0xD0, 0x20))
        d.rectangle([self.width - 10, 1, self.width - 6, 5], fill=colore)

    def _lingua(self):
        return ((self.cfg.get("web") or {}).get("language")
                or (self.cfg.get("clock") or {}).get("language") or "it")

    @staticmethod
    def _gradi(valore):
        """Una temperatura come si scrive su un cartello, non come esce da un
        sensore: interi. Il mezzo grado non lo sente nessuno e ruba due
        caratteri ai numeri che contano."""
        if valore is None:
            return "--"
        return "%d°" % int(round(valore))

    def _largo(self, d, testo, font):
        try:
            riquadro = d.textbbox((0, 0), testo, font=font)
            return riquadro[2] - riquadro[0]
        except AttributeError:            # pragma: no cover - PIL molto vecchia
            return d.textsize(testo, font=font)[0]

    def _bollettino(self, d, dati):
        """La giornata intera: icona grande, massima, minima, umidita'."""
        lang = self._lingua()
        oggi = dati.get("oggi") or {}
        adesso = dati.get("adesso") or {}
        codice = oggi.get("codice")
        if codice is None:
            codice = adesso.get("codice")

        lato = int(self.height * 0.72)
        icone.disegna(d, meteo.icona(codice, notte=False),
                      4, (self.height - lato) // 2, lato)
        sinistra = 4 + lato + 6

        titolo = "OGGI" if str(lang).startswith("it") else "TODAY"
        d.text((sinistra, 1), titolo, font=self._font_piccolo, fill=SPENTO)
        largo_titolo = self._largo(d, titolo, self._font_piccolo)
        descrizione = meteo.descrizione(codice, lang)
        d.text((sinistra + largo_titolo + 6, 1), descrizione,
               font=self._font_piccolo, fill=TESTO)

        # I due numeri, grandi e affiancati. Non c'e' l'etichetta "MAX" e
        # "MIN": il colore la dice, e due parole in piu' ruberebbero lo spazio
        # ai numeri, che sono la ragione per cui si guarda.
        y = int(self.height * 0.26)
        massima = self._gradi(oggi.get("massima"))
        d.text((sinistra, y), massima, font=self._font_grande, fill=CALDO)
        x = sinistra + self._largo(d, massima, self._font_grande) + 10
        d.text((x, y), self._gradi(oggi.get("minima")),
               font=self._font_grande, fill=FREDDO)

        # Riga bassa: umidita', e la pioggia solo se ce n'e'. Una probabilita'
        # di pioggia dello zero per cento non e' un'informazione, e' rumore.
        basso = self.height - int(self.height * 0.19) - 1
        pezzi = []
        umidita = oggi.get("umidita")
        if umidita is None:
            umidita = adesso.get("umidita")
        if umidita is not None:
            pezzi.append(("UM %d%%" % umidita, UMIDO))
        pioggia = oggi.get("pioggia_probabile")
        if pioggia:
            pezzi.append(("%s %d%%" % ("PIOGGIA" if str(lang).startswith("it")
                                       else "RAIN", pioggia), FREDDO))
        alba, tramonto = self._ore(oggi.get("alba")), self._ore(oggi.get("tramonto"))
        if alba and tramonto:
            pezzi.append(("%s-%s" % (alba, tramonto), SPENTO))

        x = sinistra
        for testo, colore in pezzi:
            largo = self._largo(d, testo, self._font_piccolo)
            if x + largo > self.width - 2:
                # Non si scrive fuori dal pannello: si smette. Meglio tre
                # informazioni che quattro di cui una tagliata a meta'.
                break
            d.text((x, basso), testo, font=self._font_piccolo, fill=colore)
            x += largo + 8

        self._eta(d)
        self._tacca_allerta(d)

    def _aggiornamento(self, d, dati):
        """Adesso: pochi numeri, grandi."""
        lang = self._lingua()
        adesso = dati.get("adesso") or {}
        oggi = dati.get("oggi") or {}
        codice = adesso.get("codice")
        notte = not adesso.get("giorno", True)

        lato = int(self.height * 0.72)
        icone.disegna(d, meteo.icona(codice, notte=notte),
                      4, (self.height - lato) // 2, lato)
        sinistra = 4 + lato + 6

        d.text((sinistra, 1), meteo.descrizione(codice, lang),
               font=self._font_piccolo, fill=TESTO)

        y = int(self.height * 0.24)
        temperatura = self._gradi(adesso.get("temperatura"))
        d.text((sinistra, y), temperatura, font=self._font_grande, fill=CALDO)
        x = sinistra + self._largo(d, temperatura, self._font_grande) + 12

        umidita = adesso.get("umidita")
        if umidita is not None:
            d.text((x, y + int(self.height * 0.12)), "UM %d%%" % umidita,
                   font=self._font_medio, fill=UMIDO)

        # La massima e la minima anche qui, ma piccole e con i **loro** colori:
        # scritte tutte grigie come "24° / 12°" costringerebbero a ricordare
        # quale viene prima. Ambra e azzurro lo dicono senza etichette, ed e' la
        # stessa grammatica del bollettino: chi ha visto l'una capisce l'altra.
        basso = self.height - int(self.height * 0.19) - 1
        massima = self._gradi(oggi.get("massima"))
        d.text((sinistra, basso), massima, font=self._font_piccolo, fill=CALDO)
        x = sinistra + self._largo(d, massima, self._font_piccolo) + 6
        d.text((x, basso), self._gradi(oggi.get("minima")),
               font=self._font_piccolo, fill=FREDDO)

        self._eta(d)
        self._tacca_allerta(d)

    def _eta(self, d):
        """Un puntino in alto a destra quando la previsione e' vecchia.

        Serve a distinguere "fa diciotto gradi" da "faceva diciotto gradi
        stamattina, poi e' caduta la rete". Non si scrive una frase: chi guarda
        di sfuggita non la leggerebbe, e chi si accorge del puntino va a
        vedere la pagina web.
        """
        if self._meteo.fresca():
            return
        d.rectangle([self.width - 4, 1, self.width - 2, 3], fill=VECCHIO)

    @staticmethod
    def _ore(iso):
        """Da un istante ISO alla sola ora e minuto. None se non si capisce."""
        if not iso or not isinstance(iso, str):
            return ""
        pezzo = iso.split("T")[-1]
        return pezzo[:5] if len(pezzo) >= 5 else ""

    # ------------------------------------------------------------------ stato

    def status(self, lang=None):
        if not self._running:
            return self.t("status.disabled", lang)
        if self._meteo.posizione() is None:
            return self.t("meteo.status.nopos", lang)
        if self._errore:
            return self.t("meteo.status.error", lang, motivo=self._errore)
        dati = self._meteo.dati()
        if not dati:
            return self.t("meteo.status.waiting", lang)
        adesso = dati.get("adesso") or {}
        oggi = dati.get("oggi") or {}
        eta = self._meteo.eta_ore()
        # L'allerta va **davanti**, non in coda: e' l'unica cosa in questa riga
        # che possa richiedere di fare qualcosa.
        avviso = self._meteo.allerta()
        prefisso = ""
        if avviso is not None:
            prefisso = self.t(
                "meteo.status.alert", lang,
                livello=(_allerte.livello_scritto(avviso.get("livello"),
                                                  lang or self._lingua())
                         if _allerte else avviso.get("livello") or ""),
                evento=(_allerte.descrizione_evento(avviso,
                                                    lang or self._lingua())
                        if _allerte else avviso.get("evento") or "")) + " · "
        return prefisso + self.t(
            "meteo.status.ok", lang,
            temperatura=self._gradi(adesso.get("temperatura")),
            descrizione=meteo.descrizione(adesso.get("codice"),
                                          lang or self._lingua()),
            massima=self._gradi(oggi.get("massima")),
            minima=self._gradi(oggi.get("minima")),
            minuti=int((eta or 0) * 60))

    def riepilogo(self):
        """I numeri per Home Assistant. None se non c'e' ancora niente."""
        dati = self._meteo.dati()
        if not dati:
            return None
        adesso = dati.get("adesso") or {}
        oggi = dati.get("oggi") or {}
        return {
            "temperatura": adesso.get("temperatura"),
            "umidita": adesso.get("umidita"),
            "codice": adesso.get("codice"),
            "descrizione": meteo.descrizione(adesso.get("codice"),
                                             self._lingua()),
            "massima": oggi.get("massima"),
            "minima": oggi.get("minima"),
            "pioggia_probabile": oggi.get("pioggia_probabile"),
            "eta_ore": self._meteo.eta_ore(),
            "allerta": self._meteo.allerta(),
        }
