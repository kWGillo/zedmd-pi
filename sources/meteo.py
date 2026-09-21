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

import fasce
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
        # Il giorno per cui si sono gia' chiesti i dati del bollettino: vedi
        # `_giro`, i tentativi successivi usano quelli in mano.
        self._scaricato_per = ""
        # Vero quando il turno con il Cielo e' in funzione: vedi `_giro`.
        self.turni_attivi = False
        self._ultimo_aggiornamento = 0.0
        # Quando il meteo e' andato **a schermo** l'ultima volta. E' un
        # orologio diverso da quello qui sopra: uno conta le chiamate alla
        # rete, questo le comparse vere.
        #
        # Fino alla 8.2 lo segnava `_apri`, cioe' il momento in cui il meteo
        # *decideva* di mostrarsi. Ma fra la decisione e il pannello c'e'
        # l'arbitro, e il meteo ha priorita' 54: se in quell'istante c'era il
        # Rolling Banner, la finestra si apriva e si chiudeva senza che
        # nessuno vedesse niente -- e il turno era comunque speso, con il
        # prossimo fra venti minuti. Simulando una giornata: 48 comparse vere
        # e **460 turni bruciati a vuoto**. Adesso lo segna `in_onda()`, che
        # e' l'unico posto in cui si sa che il pannello e' davvero nostro.
        self._ultimo_mostrato = 0.0
        # La finestra aperta adesso: fino a quando, quanto doveva durare, e se
        # qualcuno l'ha vista. Serve a due cose: riprovare subito quando si
        # perde il turno, e dare la durata intera a chi arriva a schermo a
        # meta' finestra invece dei tre secondi avanzati.
        self._durata = 0.0
        self._vista = False
        # I numeri per la pagina web: quante volte ci si e' mostrati davvero e
        # quante si e' perso il turno. Senza, "non vedo mai il meteo" resta
        # un'impressione contro un'altra impressione.
        self._comparse = 0
        self._perse = 0
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

    def in_onda(self):
        """Adesso il pannello e' nostro: il turno si consuma qui.

        E si allunga la finestra. Il caso e' questo: il meteo apre i suoi
        dodici secondi, il banner ne occupa nove, e al meteo ne resterebbero
        tre -- il tempo di accorgersi che c'era qualcosa e vederlo sparire.
        Arrivando a schermo la finestra riparte per intero. Una volta sola:
        se il banner si intromette di nuovo a meta', non si ricomincia da
        capo all'infinito.
        """
        if self._vista:
            return
        self._vista = True
        self._comparse += 1
        adesso = time.time()
        self._ultimo_mostrato = adesso
        if self._durata:
            self._fino_a = adesso + self._durata
        # Il bollettino di oggi e' dato quando qualcuno l'ha **visto**, non
        # quando la finestra si e' aperta: e' la correzione della 9.13.
        if self._modo == "bollettino":
            self._bollettino_dato = datetime.now().strftime("%Y-%m-%d")

    # ------------------------------------------------------ la fascia del mattino

    # Per quante ore dopo l'ora del bollettino si continua a provare a
    # mostrarlo, se nessuno l'ha ancora visto. Tre: un bollettino delle sette
    # visto alle nove e mezza dice ancora la verita' sulla giornata; alle
    # undici e' meglio lasciarlo perdere.
    ORE_BOLLETTINO = 3

    @staticmethod
    def in_mattino(conf, adesso=None):
        """Vero se `adesso` cade nella fascia del mattino ed e' accesa."""
        if not conf.get("mattino", True):
            return False
        adesso = adesso or datetime.now()
        inizio = fasce.parse_hhmm(conf.get("mattino_inizio", "06:30"), 390)
        fine = fasce.parse_hhmm(conf.get("mattino_fine", "09:00"), 540)
        return fasce.in_window(adesso.hour * 60 + adesso.minute, inizio, fine)

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

        # Due orologi, e la distinzione e' il senso di questa parte.
        #
        #   `ogni_ore`     ogni quanto si **chiedono** i dati a Open-Meteo
        #   `ogni_minuti`  ogni quanto il meteo **prende il pannello**
        #
        # Fino alla 7.4 erano la stessa cosa, ed e' il motivo per cui il meteo
        # non si vedeva mai: un bollettino la mattina piu' un aggiornamento
        # ogni quattro ore fanno sei apparizioni al giorno, un minuto e mezzo
        # su ventiquattro ore. Ma la previsione non cambia ogni venti minuti,
        # e non c'e' nessun bisogno di chiederla di nuovo per rimostrarla:
        # quella in mano va benissimo, ed e' gia' marcata con la sua eta'.
        ogni_minuti = max(0, int(conf.get("ogni_minuti", 20) or 0))

        # La fascia del mattino. «Al mattino vedo poco le previsioni»: dalle
        # 6 alle 9, con la configurazione di serie, il meteo stava a schermo
        # 226 secondi su 10.800 -- il 2%, cioe' dodici secondi ogni dieci
        # minuti. Chi fa colazione davanti al pannello per un quarto d'ora ne
        # vedeva uno, se capitava. Nella fascia il giro si stringe e mostra il
        # **bollettino**, che e' la schermata che risponde alla domanda del
        # mattino: com'e' la giornata, non quanti gradi fa in questo istante.
        # Fuori dalla fascia tutto resta com'era: un meteo che c'e' sempre
        # smette di essere guardato.
        mattino = self.in_mattino(conf, adesso)
        if mattino:
            ogni_minuti = max(1, int(conf.get("mattino_ogni_minuti", 2) or 2))
        periodico = "bollettino" if mattino else "aggiornamento"
        durata_periodico = (int(conf.get("durata_bollettino", 22) or 22) if mattino
                            else int(conf.get("durata_aggiornamento", 12) or 12))

        oggi = adesso.strftime("%Y-%m-%d")
        # Il bollettino di oggi **finche' non e' stato visto**, dall'ora del
        # bollettino per le tre ore dopo. Fino alla 9.12 bastava averlo
        # *aperto*: se alle sette il pannello era del Calendario, di una
        # notifica o dello Sleep, la finestra da ventidue secondi si chiudeva
        # senza che nessuno la vedesse, e il bollettino era dato per fatto
        # fino al giorno dopo. La 8.2 aveva corretto lo stesso difetto per
        # l'aggiornamento periodico e non per questo.
        tocca_bollettino = (self._bollettino_dato != oggi
                            and ora_bollettino <= adesso.hour
                            < ora_bollettino + self.ORE_BOLLETTINO)
        scaduto = (time.time() - self._ultimo_aggiornamento) >= ogni * 3600
        # `_ultimo_mostrato` adesso vuol dire "l'ultima volta che ci hanno
        # visto". Quindi questa riga, senza cambiare una virgola, fa anche il
        # lavoro nuovo: se l'ultima finestra e' passata a vuoto il conto non
        # si e' azzerato, la condizione resta vera e al giro dopo -- un
        # minuto -- si riprova. Perdere il turno costa sessanta secondi
        # invece di venti minuti.
        tocca_giro = (ogni_minuti > 0
                      and not self.active()
                      and (time.time() - self._ultimo_mostrato)
                      >= ogni_minuti * 60)
        # Dalla 10.0 il giro di tutto il giorno lo decide il turno con il
        # Cielo -- uno ogni due media, a turno -- e non piu' questo orologio.
        # Resta suo solo dentro la fascia del mattino, dove la regola e'
        # un'altra: il bollettino ogni due minuti.
        if self.turni_attivi and not mattino:
            tocca_giro = False

        # Le allerte si guardano a ogni giro, non ogni quattro ore: il modulo
        # ha il suo freno di mezz'ora e non chiama piu' del dovuto, ma un
        # avviso che arriva alle 20:05 non puo' aspettare le 22 per comparire.
        nuova = self._allerta_nuova()
        if nuova is not None:
            self._apri("allerta", int(conf.get("durata_allerta", 25) or 25))
            return

        # La rete si interroga quando i dati sono vecchi, oppure una volta al
        # giorno per il bollettino. **Non** a ogni tentativo del bollettino:
        # con il pannello in Sleep fino alle otto, riprovare ogni minuto
        # vorrebbe dire sessanta chiamate a Open-Meteo per mostrare niente.
        # I tentativi usano i dati gia' in mano.
        serve_la_rete = scaduto or (tocca_bollettino
                                    and self._scaricato_per != oggi)
        fresco = False
        if serve_la_rete:
            # I dati si chiedono **prima** di aprire la finestra: una finestra
            # che si apre e poi resta vuota per dieci secondi mentre la rete
            # risponde e' peggio di una finestra che si apre dieci secondi dopo.
            self._meteo.aggiorna()
            # Si segna comunque il tentativo, altrimenti con la rete giu' il
            # giro riproverebbe ogni minuto per sempre.
            self._ultimo_aggiornamento = time.time()
            if tocca_bollettino:
                self._scaricato_per = oggi
            if self._meteo.dati() is None:
                self._errore = self._meteo.errore() or "nessuna previsione"
                return
            fresco = True

        if self._meteo.dati() is None:
            return

        if tocca_bollettino and not self.active():
            self._apri("bollettino",
                       int(conf.get("durata_bollettino", 22) or 22))
        elif tocca_giro or (fresco and (mattino or not self.turni_attivi)):
            # Il giro periodico, oppure dati appena arrivati: si mostra quello
            # che si ha, nella schermata giusta per quest'ora.
            self._apri(periodico, durata_periodico)

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
        # Se una finestra precedente non e' mai arrivata a schermo, adesso si
        # sa: la si conta come persa prima di sostituirla.
        if self._durata and not self._vista:
            self._perse += 1
        self._durata = float(max(4, secondi))
        self._vista = False
        self._fino_a = time.time() + self._durata
        # L'orologio del giro periodico **non** si tocca qui: lo tocca
        # `in_onda()`. Aprire una finestra non e' essersi mostrati.

    def apri_turno(self):
        """Lo spazio che il turno da' al meteo: la schermata di quest'ora.

        Con i dati gia' in mano, senza chiamare la rete: il turno arriva
        ogni due media, e la previsione non cambia ogni minuto.
        """
        if not self._running or self._meteo.dati() is None:
            return False
        conf = self.conf()
        mattino = self.in_mattino(conf, datetime.now())
        modo = "bollettino" if mattino else "aggiornamento"
        durata = (int(conf.get("durata_bollettino", 22) or 22) if mattino
                  else int(conf.get("durata_aggiornamento", 12) or 12))
        self._apri(modo, durata)
        return bool(self._modo)

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

    def unita(self):
        """"C" o "F". La previsione arriva sempre in Celsius: si converte qui."""
        scelta = str(self.conf().get("unita", "C") or "C").upper()
        return "F" if scelta.startswith("F") else "C"

    def _gradi(self, valore, unita=True):
        """Una temperatura come si scrive su un cartello, non come esce da un
        sensore: intera. Il mezzo grado non lo sente nessuno e ruba due
        caratteri ai numeri che contano.

        `unita` decide se aggiungere `C` o `F` dopo il grado. Si scrive **una
        volta sola** per schermata, sul numero grande: ripeterla accanto a
        massima e minima riempirebbe la riga di lettere invece che di numeri, e
        nessuno cambia scala fra una riga e l'altra.
        """
        if valore is None:
            return "--"
        gradi = float(valore)
        scala = self.unita()
        if scala == "F":
            gradi = gradi * 9.0 / 5.0 + 32.0
        return "%d°%s" % (int(round(gradi)), scala if unita else "")

    def _freccia(self, d, x, y, lato, su, colore):
        """Il triangolino prima di massima e minima.

        Disegnato invece che scritto: i caratteri di freccia esistono ma non
        tutti i font li hanno, e una freccia che diventa un rettangolo vuoto e'
        peggio di nessuna freccia. Un triangolo di cinque pixel non puo'
        mancare da nessun font, perche' non viene da un font.
        """
        meta = lato / 2.0
        if su:
            punti = [(x + meta, y), (x + lato, y + lato), (x, y + lato)]
        else:
            punti = [(x + meta, y + lato), (x + lato, y), (x, y)]
        d.polygon(punti, fill=colore)

    def _orizzonte(self, dati, adesso=None):
        """A quale giorno si riferiscono massima, minima e pioggia. E come si chiama.

        Nasce da una domanda che non aveva risposta guardando il pannello: *la
        mattina immagino che le previsioni siano della giornata, ma la sera non
        so se parlano delle prossime ore o del giorno dopo.* Aveva ragione, e il
        difetto era peggiore dell'ambiguita': di sera quei numeri erano
        **passati**. La massima di oggi alle dieci di sera l'hai gia' vissuta,
        e la minima quotidiana e' quella della notte scorsa. Erano cronaca
        presentata come previsione.

        La regola e' il tramonto, non un'ora fissa, e il tramonto il DMD ce
        l'ha gia' nei dati: cosi' d'estate il passaggio e' alle nove e mezza e
        d'inverno alle cinque, che e' quando cambia davvero la giornata di chi
        guarda. Se il dato manca si ripiega sulle diciannove, che e' una sera
        ragionevole a qualunque latitudine in cui questo pannello stia acceso.

        Torna (etichetta, giorno).
        """
        oggi = (dati or {}).get("oggi") or {}
        domani = (dati or {}).get("domani") or {}
        adesso = adesso or datetime.now()
        sera = False
        tramonto = self._ore(oggi.get("tramonto"))
        if tramonto:
            ore, minuti = int(tramonto[:2]), int(tramonto[3:5])
            sera = (adesso.hour, adesso.minute) >= (ore, minuti)
        else:
            sera = adesso.hour >= 19
        # Senza i dati di domani non si inventa niente: si resta su oggi e si
        # scrive OGGI, che e' ambiguo ma vero.
        if sera and domani.get("massima") is not None:
            return self.t("meteo.giorno.domani"), domani
        return self.t("meteo.giorno.oggi"), oggi

    def _estremi(self, d, destra, y, oggi, etichetta=""):
        """Massima e minima in alto a destra, ciascuna con la sua freccia.

        Sono la cornice della giornata, non il dato del momento: stanno
        piccole, in un angolo, e si leggono quando servono. Il numero grande al
        centro resta quello di adesso, che e' la domanda a cui il pannello deve
        rispondere per primo.
        """
        font = self._font_piccolo
        lato = max(3, int(self.height * 0.09))
        pezzi = []
        for su, valore, colore in ((True, oggi.get("massima"), CALDO),
                                   (False, oggi.get("minima"), FREDDO)):
            testo = self._gradi(valore, unita=False)
            pezzi.append((su, testo, colore,
                          lato + 3 + self._largo(d, testo, font)))
        largo_etichetta = (self._largo(d, etichetta, font) + 6) if etichetta else 0
        totale = sum(p[3] for p in pezzi) + 8 + largo_etichetta
        x = destra - totale
        if etichetta:
            # La parola sta **prima** delle frecce e nello stesso grigio del
            # resto della cornice: e' il soggetto della frase che segue, non un
            # dato in piu' da leggere. "DOMANI 24 15" si legge tutto insieme.
            d.text((x, y), etichetta, font=font, fill=SPENTO)
            x += largo_etichetta
        for su, testo, colore, largo in pezzi:
            self._freccia(d, x, y + 3, lato, su, colore)
            d.text((x + lato + 3, y), testo, font=font, fill=colore)
            x += largo + 8
        return totale

    def _centrato(self, d, centro, y, pezzi):
        """Scrive una fila di testi centrata su `centro`.

        `pezzi` e' una lista di (testo, font, colore, scarto_verticale). Il
        gruppo si misura intero e **poi** si posiziona: centrare ogni pezzo per
        conto suo li accavallerebbe.
        """
        larghezze = [self._largo(d, t, f) for t, f, _c, _dy in pezzi]
        totale = sum(larghezze) + 10 * (len(pezzi) - 1)
        x = centro - totale / 2.0
        for (testo, font, colore, dy), largo in zip(pezzi, larghezze):
            d.text((x, y + dy), testo, font=font, fill=colore)
            x += largo + 10

    def _largo(self, d, testo, font):
        try:
            riquadro = d.textbbox((0, 0), testo, font=font)
            return riquadro[2] - riquadro[0]
        except AttributeError:            # pragma: no cover - PIL molto vecchia
            return d.textsize(testo, font=font)[0]

    def _scheletro(self, d, codice, notte, oggi, etichetta=""):
        """La parte comune alle due finestre, e il motivo per cui e' comune.

        Le due schermate rispondono a domande diverse -- la giornata e
        l'adesso -- ma la prima cosa che si guarda e' la stessa: **quanti
        gradi fa**. Segnalato dal campo guardando il bollettino: massima e
        minima grandi al centro si leggevano come la temperatura di adesso, e
        quella vera non c'era da nessuna parte.

        Adesso l'impianto e' uno: icona a sinistra, la cornice della giornata
        piccola in alto a destra, e in mezzo -- grande e centrato -- il dato
        del momento. Cambia il contorno, non la risposta alla prima domanda.

        Torna (sinistra, centro, spazio) dell'area utile. `spazio` e' quanto
        resta alla riga in alto prima di incontrare massima e minima: si
        misura invece di stimarlo con una frazione della larghezza, perche'
        quel blocco cambia larghezza con l'etichetta del giorno e con la
        lingua -- TOMORROW e' piu' lungo di DOMANI -- e una frazione fissa o
        troncava troppo o faceva toccare le due parti.
        """
        lato = int(self.height * 0.62)
        icone.disegna(d, meteo.icona(codice, notte=notte),
                      3, (self.height - lato) // 2, lato)
        sinistra = 3 + lato + 5
        centro = sinistra + (self.width - 3 - sinistra) / 2.0
        largo = self._estremi(d, self.width - 3, 1, oggi, etichetta)
        spazio = max(20, self.width - 3 - largo - 6 - sinistra)
        return sinistra, centro, spazio

    def _bollettino(self, d, dati):
        """La giornata: cornice in alto, gradi di adesso in mezzo, ore sotto."""
        lang = self._lingua()
        adesso = dati.get("adesso") or {}
        # Il bollettino racconta **una giornata**, e quale sia lo decide il
        # tramonto: prima e' quella in corso, dopo e' quella che viene. Tutto
        # quello che sta sotto -- icona, descrizione, estremi, pioggia, alba e
        # tramonto -- viene da questo stesso giorno, altrimenti il pannello
        # mescolerebbe due giorni senza dirlo.
        etichetta, giorno = self._orizzonte(dati)
        codice_giorno = giorno.get("codice")
        if codice_giorno is None:
            codice_giorno = adesso.get("codice")

        sinistra, centro, spazio = self._scheletro(d, codice_giorno, False,
                                                   giorno, etichetta)

        # In alto a sinistra che tempo fa, accorciato se serve: lo spazio
        # finisce dove comincia l'etichetta del giorno. La parola OGGI stava
        # qui e se n'e' andata accanto a massima e minima: e' la' che serviva,
        # ed e' li' che adesso vale anche per la schermata di aggiornamento.
        d.text((sinistra, 1),
               self._taglia(d, meteo.descrizione(codice_giorno, lang),
                            self._font_piccolo, spazio),
               font=self._font_piccolo, fill=TESTO)

        self._centro_gradi(d, centro, adesso, giorno)

        # Riga bassa, centrata: la pioggia solo se ce n'e' -- uno zero per
        # cento non e' un'informazione, e' rumore -- poi alba e tramonto.
        basso = self.height - int(self.height * 0.19) - 1
        pezzi = []
        pioggia = giorno.get("pioggia_probabile")
        if pioggia:
            pezzi.append(("%s %d%%" % ("PIOGGIA" if str(lang).startswith("it")
                                       else "RAIN", pioggia),
                          self._font_piccolo, FREDDO, 0))
        alba, tramonto = (self._ore(giorno.get("alba")),
                          self._ore(giorno.get("tramonto")))
        if alba and tramonto:
            pezzi.append(("%s - %s" % (alba, tramonto),
                          self._font_piccolo, SPENTO, 0))
        if pezzi:
            self._centrato(d, centro, basso, pezzi)

        self._eta(d)
        self._tacca_allerta(d)

    def _aggiornamento(self, d, dati):
        """Adesso: gli stessi gradi grandi in mezzo, e che tempo fa in cima."""
        lang = self._lingua()
        adesso = dati.get("adesso") or {}
        # L'icona e la descrizione sono il cielo di **adesso** e non hanno
        # bisogno di etichette: si guarda fuori dalla finestra e si verifica.
        # Massima e minima invece sono una previsione, e fino alla 8.2 non
        # dicevano di quando: adesso lo dicono.
        etichetta, giorno = self._orizzonte(dati)
        codice = adesso.get("codice")
        notte = not adesso.get("giorno", True)

        sinistra, centro, spazio = self._scheletro(d, codice, notte, giorno,
                                                   etichetta)
        d.text((sinistra, 1),
               self._taglia(d, meteo.descrizione(codice, lang),
                            self._font_piccolo, spazio),
               font=self._font_piccolo, fill=TESTO)

        self._centro_gradi(d, centro, adesso, giorno)

        # Sotto, centrata, la temperatura percepita -- ma solo quando e'
        # diversa davvero. "18 gradi, percepiti 18" e' una riga sprecata; con
        # vento o afa quella differenza e' il motivo per cui uno si mette la
        # giacca.
        percepita = adesso.get("percepita")
        vera = adesso.get("temperatura")
        if (percepita is not None and vera is not None
                and abs(percepita - vera) >= 1.5):
            basso = self.height - int(self.height * 0.19) - 1
            etichetta = "PERCEPITI" if str(lang).startswith("it") else "FEELS"
            self._centrato(d, centro, basso,
                           [("%s %s" % (etichetta,
                                        self._gradi(percepita, unita=False)),
                             self._font_piccolo, SPENTO, 0)])

        self._eta(d)
        self._tacca_allerta(d)

    def _centro_gradi(self, d, centro, adesso, oggi):
        """Il blocco centrale: i gradi di adesso e l'umidita', affiancati.

        L'umidita' e' salita qui dalla riga in basso su segnalazione dal
        campo, e la segnalazione aveva ragione: e' un numero che si legge
        insieme alla temperatura -- ventisei gradi con il settanta per cento
        sono un'altra giornata rispetto a ventisei asciutti -- e in fondo alla
        schermata, piccola, non la guardava nessuno.

        I due numeri hanno corpi diversi e sono allineati sulla **linea di
        base**: con due corpi diversi il pareggio in alto si vede storto.
        """
        temperatura = adesso.get("temperatura")
        if temperatura is None:
            temperatura = oggi.get("massima")
        testo = self._gradi(temperatura)
        pezzi = [(testo, self._font_grande, CALDO, 0)]
        umidita = adesso.get("umidita")
        if umidita is None:
            umidita = oggi.get("umidita")
        if umidita is not None:
            # Lo scarto verticale allinea la base dell'umidita' con quella dei
            # gradi: e' la differenza fra le due altezze di carattere.
            scarto = (self._font_grande.getmetrics()[0]
                      - self._font_medio.getmetrics()[0])
            pezzi.append(("%d%%" % umidita, self._font_medio, UMIDO, scarto))
        self._centrato(d, centro, int(self.height * 0.26), pezzi)

    def _eta(self, d):
        """Un puntino in alto a destra quando la previsione e' vecchia.

        Serve a distinguere "fa diciotto gradi" da "faceva diciotto gradi
        stamattina, poi e' caduta la rete". Non si scrive una frase: chi guarda
        di sfuggita non la leggerebbe, e chi si accorge del puntino va a
        vedere la pagina web.
        """
        if self._meteo.fresca():
            return
        # In **basso** a destra, non in alto. In alto stava addosso al grado
        # della minima: due cose diverse nello stesso millimetro, e il puntino
        # sembrava un difetto del pannello invece di un avviso. L'angolo in
        # basso a destra e' l'unico sempre vuoto in tutte e tre le schermate.
        d.rectangle([self.width - 4, self.height - 4,
                     self.width - 2, self.height - 2], fill=VECCHIO)

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
        # Quando ci si e' fatti vedere l'ultima volta. E' l'unica riga che
        # risponde a "non vedo mai il meteo" con un numero invece che con
        # un'opinione, e vale quanto tutto il resto messo insieme.
        coda = ""
        if self._ultimo_mostrato:
            coda = " · " + self.t(
                "meteo.status.vista", lang,
                minuti=int((time.time() - self._ultimo_mostrato) / 60),
                comparse=self._comparse, perse=self._perse)
        return prefisso + self.t(
            "meteo.status.ok", lang,
            temperatura=self._gradi(adesso.get("temperatura")),
            descrizione=meteo.descrizione(adesso.get("codice"),
                                          lang or self._lingua()),
            massima=self._gradi(oggi.get("massima")),
            minima=self._gradi(oggi.get("minima")),
            minuti=int((eta or 0) * 60)) + coda

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
            # Le comparse vere e i turni persi: servono a Home Assistant
            # quanto alla pagina, e sono la misura di un difetto che e'
            # rimasto invisibile finche' nessuno li ha contati.
            "comparse": self._comparse,
            "turni_persi": self._perse,
            "vista_da_minuti": (int((time.time() - self._ultimo_mostrato) / 60)
                                if self._ultimo_mostrato else None),
        }
