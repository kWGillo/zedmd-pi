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

Niente viene piu' tagliato (15.2, 15.3)
---------------------------------------
Tre testi di questo servizio li scrive qualcun altro -- i due CSV e Wikipedia
-- e sono lunghi quanto vogliono. Tagliati con i puntini volevano dire mezza
riga non letta, che su un servizio che fa solo compagnia e' l'unico modo di
sbagliare. Adesso si muovono, in due modi diversi perche' sono due cose
diverse:

- il **santo** e la **giornata mondiale** sono righe: scorrono di lato, ferme
  un secondo, poi trenta pixel al secondo, e all'ultima parola si fermano;
- l'**accadde oggi** e' un paragrafo: va a capo su quante righe serve e la
  colonna **sale**, come i titoli di coda, piu' piano e con tre secondi di
  pausa in cima. Di lato sarebbero cinque strisce in movimento insieme.

**Non a giro**, in nessuno dei due casi: un giro su una schermata di pochi
secondi viene interrotto sempre a meta'. E la schermata si allunga quanto
serve a vedere tutto, con un tetto a venti secondi.

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

# --------------------------------------------------- il testo che non ci sta

# Due righe della prima schermata le scrive qualcun altro, e sono lunghe
# quanto vogliono: il santo -- «SANTI CORNELIO E CIPRIANO» -- e la giornata
# mondiale, dove «Giornata mondiale per la riduzione del rischio di disastri»
# e' un titolo vero. Fino alla 15.1 finivano con i puntini, cioe' mezza riga
# non si leggeva: su un pannello che serve solo a far compagnia, tagliare la
# frase e' l'unico modo di sbagliare.
#
# Adesso **scorrono**, e scorrono in un modo preciso: partono ferme, vanno
# fino all'ultima parola, e la' si fermano. Non a giro. Un giro infinito su
# una schermata che dura sei secondi non si legge: ricomincia sempre da capo e
# viene interrotto sempre a meta'. Fermarsi alla fine vuol dire che l'ultima
# parola resta sotto gli occhi per il tempo di leggerla.
VELOCITA = 30.0          # pixel al secondo: velocita' di lettura, non di corsa
ATTESA_PRIMA = 1.0       # ferma all'inizio, il tempo di cominciare
ATTESA_DOPO = 1.3        # ferma alla fine, il tempo di finire

# L'«accadde oggi» e' un'altra cosa, e lo e' per una ragione geometrica: non e'
# una riga lunga, e' un **paragrafo**. Una frase di Wikipedia va a capo da
# sola su quattro o cinque righe, e farla scorrere di lato vorrebbe dire
# cinque strisce che si muovono insieme: illeggibile. Quelle righe stanno una
# sotto l'altra e scorrono **verso l'alto**, come i titoli di coda -- chiesto
# cosi': «come la sigla di Guerre Stellari».
#
# Due numeri diversi da quelli di sopra, e per forza:
#  - **piu' lento.** Di lato si inseguono le lettere, in verticale si leggono
#    righe intere: a dodici pixel al secondo una riga alta quattordici resta
#    leggibile per piu' di un secondo mentre sale.
#  - **la pausa in fondo e' piu' lunga.** Chiesta: «qualche secondo di pausa
#    alla fine, per permetterne la lettura». Quando la salita si ferma, le
#    ultime righe sono appena arrivate e sono quelle che nessuno ha ancora
#    letto -- un secondo non basta, tre si'.
VELOCITA_ALTO = 12.0
ATTESA_DOPO_ALTO = 3.0

# Quante righe al massimo si impaginano. Non e' un troncamento travestito: un
# fatto storico di dodici righe non esiste, e il numero sta qui perche' un
# giorno una pagina di Wikipedia malformata non faccia una salita di tre
# minuti dentro un tetto di venti secondi -- che sarebbe, di nuovo, un testo
# tagliato.
RIGHE_MASSIME = 12

# E la schermata si allunga quanto serve a vedere lo scorrimento intero: una
# riga che scorre per sei secondi dentro una schermata che dura sei secondi e'
# ancora una riga tagliata, solo in un altro modo. Il tetto c'e' perche' il
# servizio resta quello che non serve a niente: oltre venti secondi si tiene
# il pannello troppo, e a quel punto meglio perdere l'ultima parola.
TETTO_SLIDE = 20.0

# Quanto puo' passare fra due fotogrammi prima di dire «il pannello era di un
# altro». Il ciclo gira a trenta fotogrammi al secondo, cioe' trentatre'
# millisecondi: mezzo secondo e' quindici volte tanto, abbastanza da non
# confondere una pausa vera con un giro lento. Vedi `_recupera`.
PAUSA_FUORI = 0.5


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
        # Le righe che scorrono su questa schermata, e da quando: il disegno
        # resta uno -- si fa una volta per turno, non trenta volte al secondo
        # -- e sopra ci si appoggiano solo le finestre che si muovono.
        self._scorrevoli = []
        self._bande = []
        self._inizio = 0.0
        self._slide = ""
        self._running = False
        self._vista = False
        self._comparse = 0
        # **I turni, non le comparse.** Chi sceglie la seconda schermata e il
        # fatto da raccontare conta i *turni*, e per forza: `_comparse` cresce
        # di uno per ogni schermata che va in onda, cioe' di **due** a ogni
        # turno -- festa piu' l'altra. Con due schermate possibili, «due»
        # modulo due fa sempre lo stesso resto: la seconda schermata era
        # «accadde oggi» ogni volta e i nati di oggi non si vedevano mai,
        # mentre dei fatti storici ne uscivano solo quelli di posto pari.
        # Si vedeva solo guardando il pannello per un pomeriggio.
        self._turno = 0
        # E quante volte ciascuna schermata si e' aperta. Serve a scegliere
        # *quale* fatto raccontare, ed e' un conto diverso da quello dei
        # turni: «accadde oggi» compare un turno su due, quindi contando i
        # turni il resto sarebbe sempre lo stesso -- la stessa trappola di
        # `_comparse`, un piano piu' sotto.
        self._quante = {}
        self._ultimo_frame = 0.0
        self._recuperato = 0.0
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
            self._scorrevoli = []
            self._ultimo_frame = 0.0
            self._recuperato = 0.0

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

    def _recupera(self, adesso):
        """Il tempo passato fuori dal pannello non conta.

        `frame()` la chiama il ciclo del pannello **solo quando questa
        sorgente e' quella che si vede**: fra due chiamate passano trenta
        millisecondi, non di piu'. Se ne passano molti di piu', il pannello
        in mezzo era di qualcun altro -- il Media Player ha priorita' 50 e
        questo servizio 49, quindi la foto successiva se lo prende -- e quei
        secondi la schermata non li ha avuti.

        Fino alla 16.1 li contava lo stesso: una schermata lunga interrotta
        da una foto tornava indietro con mezzo secondo di vita e appariva per
        un lampo, con lo scorrimento gia' in fondo. Adesso l'orologio della
        schermata si sposta in avanti dell'intervallo perso, e lo scorrimento
        riprende da dove era rimasto.

        Il tetto esiste perche' un Media Player molto attivo, senza, terrebbe
        viva la stessa schermata per sempre: si recupera al massimo un'altra
        volta la durata, poi la schermata finisce comunque.
        """
        if not self._ultimo_frame:
            self._ultimo_frame = adesso
            return
        perso = adesso - self._ultimo_frame
        self._ultimo_frame = adesso
        if perso <= PAUSA_FUORI:
            return
        ancora = max(0.0, self._durata - self._recuperato)
        perso = min(perso, ancora)
        if perso <= 0:
            return
        self._recuperato += perso
        self._fino_a += perso
        self._inizio += perso

    def frame(self):
        with self._lock:
            if self._image is None:
                return None
            self._recupera(time.time())
            if not self._scorrevoli:
                if not self._dirty:
                    return None
                self._dirty = False
                return self._image
            # Con una riga che scorre il fotogramma e' nuovo ogni volta, e la
            # schermata sotto no: si ricopia quella e si cambia la finestra.
            # Quando lo scorrimento e' finito torna due volte la stessa
            # immagine, e il ciclo del pannello la butta via da solo.
            self._dirty = False
            return self._componi(self._image, self._scorrevoli,
                                 time.time() - (self._inizio or time.time()))

    def in_onda(self):
        if self._vista:
            return
        self._vista = True
        self._comparse += 1
        # Lo scorrimento parte da **adesso**: fra il disegno e il momento in
        # cui l'arbitro da' il pannello puo' passare del tempo, e una riga che
        # ha finito di scorrere prima di comparire non l'ha letta nessuno.
        self._inizio = time.time()
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

        Il conto e' sui **turni** e non sulle comparse: vedi `_turno`. E la
        funzione resta senza effetti collaterali, perche' la chiama anche la
        pagina web -- e una pagina aperta non deve far girare il pannello.
        """
        pronte = self.slide_disponibili(adesso)
        dietro = [s for s in ("eventi", "storia") if s in pronte]
        coda = [s for s in pronte if s == "festa"]
        if dietro:
            coda.append(dietro[self._turno % len(dietro)])
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
        # Il turno avanza **qui**, prima di comporre la coda: cosi' la pagina
        # web, che chiama `coda_del_turno` per far vedere cosa viene dopo,
        # legge la stessa cosa che sta per andare in onda.
        self._turno += 1
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
        bande = self._bande
        with self._lock:
            self._image = immagine
            self._dirty = True
            self._scorrevoli = bande
            # Schermata nuova, conto nuovo: il primo fotogramma non deve
            # vedere come «perso» il tempo passato dall'ultimo della
            # schermata di prima.
            self._ultimo_frame = 0.0
            self._recuperato = 0.0
        self._slide = slide
        self._quante[slide] = self._quante.get(slide, 0) + 1
        self._vista = False
        self._inizio = time.time()
        self._durata = self._quanto_dura(float(secondi), bande)
        self._fino_a = time.time() + self._durata

    @staticmethod
    def _quanto_dura(secondi, bande):
        """La durata della schermata, allungata se qualcosa deve scorrere.

        Ogni banda ha la sua velocita' e la sua pausa finale -- di lato si
        corre, in verticale si legge -- quindi il conto si fa su ciascuna e
        comanda la piu' lenta.
        """
        if not bande:
            return secondi
        serve = max(ATTESA_PRIMA + b["massimo"] / b["velocita"] + b["dopo"]
                    for b in bande)
        return max(secondi, min(TETTO_SLIDE, serve))

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
        # La prova non tocca il giro dei turni -- quello e' del pannello --
        # ma `_apri` conta comunque l'apertura, quindi premendo due volte il
        # pulsante si vede il fatto dopo e non due volte lo stesso.
        self._coda = []
        self._apri(slide, secondi or self.durata_di(slide))
        return bool(self._slide), ""

    # --------------------------------------------------------------- disegno

    def disegna_campo(self, img, px):             # pragma: no cover - non usata
        pass

    def _disegna(self, slide):
        img = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        d = ImageDraw.Draw(img)
        # Le righe che scorrono le mette da parte chi disegna: la schermata
        # resta un'immagine sola, come e' sempre stata, e `_apri` le prende da
        # qui. Le altre due schermate non ne hanno -- i fatti storici vanno a
        # capo su tre righe, che e' il modo giusto per un testo lungo quando
        # lo spazio in altezza c'e'.
        self._bande = []
        if slide == "storia":
            self._storia(d)
        elif slide == "eventi":
            self._eventi(d)
        else:
            self._festa(d)
        return img

    def _componi(self, base, bande, passato):
        """La schermata con le finestre di cio' che scorre al punto in cui e'
        adesso. `passato` sono i secondi da quando la schermata e' comparsa."""
        img = base.copy()
        for banda in bande:
            avanti = max(0.0, passato - ATTESA_PRIMA) * banda["velocita"]
            dove = int(min(banda["massimo"], avanti))
            larga, alta = banda["area"], banda["altezza"]
            if banda["verso"] == "alto":
                finestra = banda["striscia"].crop((0, dove, larga, dove + alta))
            else:
                finestra = banda["striscia"].crop((dove, 0, dove + larga, alta))
            img.paste(finestra, (banda["x"], banda["y"]))
        return img

    def _scorri(self, d, testo, font, colore, x, y, area):
        """Mette in coda una riga che scorre **di lato**, se non ci sta.

        La striscia e' il testo intero su una tela sua: quello che si vede e'
        un taglio largo `area`, e il taglio che si sposta e' lo scorrimento.
        Torna True quando la riga scorre -- cioe' quando chi chiama non deve
        aggiungere altro -- e False quando il testo ci stava.
        """
        larghezza, alta = self._riquadro(d, testo, font)
        if larghezza <= area:
            return False
        striscia = Image.new("RGB", (larghezza, alta), (0, 0, 0))
        ImageDraw.Draw(striscia).text((0, 0), testo, font=font, fill=colore)
        self._bande.append({"striscia": striscia, "x": x, "y": y,
                            "area": area, "altezza": alta, "verso": "lato",
                            "velocita": VELOCITA, "dopo": ATTESA_DOPO,
                            "massimo": larghezza - area})
        return True

    def _scorri_in_alto(self, d, righe, font, colore, x, y, area, altezza,
                        passo):
        """Mette in coda un paragrafo che sale, se non ci sta in `altezza`.

        Le righe sono gia' impaginate: qui si impilano su una tela alta quanto
        serve, e la finestra che si vede sale da sola. Torna le righe che chi
        chiama deve disegnare al posto suo -- tutte se non c'e' niente da far
        salire, le prime se invece sale -- cosi' la schermata ferma e' giusta
        anche nella pagina di prova.
        """
        quante = max(1, altezza // passo)
        if len(righe) <= quante:
            return righe
        # Due pixel in piu' dell'ultima riga: senza, la salita si ferma con la
        # coda della «g» appoggiata al bordo di sotto, cioe' tagliata di un
        # pixel proprio nell'unica riga che nessuno ha ancora letto.
        alta_riga = max(1, self._riquadro(d, "Ag", font)[1]) + 2
        striscia = Image.new("RGB", (max(1, area),
                                     (len(righe) - 1) * passo + alta_riga),
                             (0, 0, 0))
        dis = ImageDraw.Draw(striscia)
        for indice, riga in enumerate(righe):
            dis.text((0, indice * passo), riga, font=font, fill=colore)
        self._bande.append({"striscia": striscia, "x": x, "y": y,
                            "area": area, "altezza": altezza, "verso": "alto",
                            "velocita": VELOCITA_ALTO, "dopo": ATTESA_DOPO_ALTO,
                            "massimo": max(0, striscia.height - altezza)})
        return righe[:quante]

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
        # Il santo scorre se non ci sta nemmeno nel corpo piccolo. La riga
        # tagliata si disegna comunque sotto: e' quello che si vede nella
        # pagina di prova e nel primo fotogramma, e la finestra che scorre le
        # passa sopra appena il pannello e' suo.
        self._scorri(d, santo, font, FESTA, margine, alto_santo, disponibile)
        d.text((margine, alto_santo), self._taglia(d, santo, font, disponibile),
               font=font, fill=FESTA)

        riga = alto_santo + (self._alto(d, font) or int(self.height * 0.3)) + 3
        nomi = dati.nomi(quando)[:5]
        if nomi:
            testo = self._taglia(d, " · ".join(nomi), self._font_piccolo, disponibile)
            d.text((margine, riga), testo, font=self._font_piccolo, fill=NOMI)

        if coda is not None:
            basso = self.height - int(self.height * 0.17) - 2
            # La giornata mondiale e' la riga lunga per vocazione: «Giornata
            # internazionale per l'eliminazione della violenza contro le
            # donne» non ci sta in nessun corpo che si legga, e tagliata non
            # dice niente. Scorre anche l'onomastico dei tuoi, che sta nello
            # stesso posto e con cinque nomi arriva alla stessa lunghezza.
            self._scorri(d, coda[0], self._font_piccolo, coda[1], margine,
                         basso, disponibile)
            d.text((margine, basso), self._taglia(d, coda[0], self._font_piccolo, disponibile),
                   font=self._font_piccolo, fill=coda[1])

    def _data(self, adesso):
        return "%d %s" % (adesso.day, MESI[adesso.month - 1].upper())

    # ---- schermata 2: accadde oggi (i fatti)

    def _eventi(self, d, adesso=None):
        """L'anno grande a sinistra, il fatto a destra, e se e' lungo **sale**.

        L'anno e' la cosa che si guarda per prima -- «1969» dice gia' mezza
        storia -- quindi sta da solo, grande, e il testo gli scorre accanto
        invece di andargli sotto.

        Il testo e' l'unico paragrafo del servizio: quello che prima non ci
        stava in tre righe finiva con i puntini, e quelle tre righe erano
        decise dall'altezza del pannello, non dal fatto. Adesso si impagina
        **quanto e' lungo** e la colonna sale, che e' il modo in cui si legge
        un paragrafo -- di lato si inseguirebbero cinque righe insieme.
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
        # Il fatto scorre con le **aperture di questa schermata**: una per
        # volta, in fila. Contando le comparse se ne saltava uno su due --
        # ne passano due per turno -- e contando i turni pure, perche'
        # «accadde oggi» compare un turno su due.
        anno, testo = fatti[self._quante.get("eventi", 0) % len(fatti)]
        d.text((margine, int(self.height * 0.30)), str(anno),
               font=self._font_grande, fill=ANNO_EVENTO)
        sinistra = margine + self._largo(d, "0000", self._font_grande) + 6
        disponibile = self.width - sinistra - margine
        alto = int(self.height * 0.17) + 1
        passo = max(1, int(self.height * 0.22))
        righe = self._a_capo(d, testo, self._font_piccolo, disponibile,
                             RIGHE_MASSIME)
        # Le righe che si vedono ferme sono quelle che ci stanno: le altre
        # arrivano salendo. La colonna parte dove partiva prima e arriva in
        # fondo al pannello -- l'anno sta a sinistra e non le da' fastidio.
        ferme = self._scorri_in_alto(d, righe, self._font_piccolo, NOMI,
                                     sinistra, alto, disponibile,
                                     self.height - alto, passo)
        for i, riga in enumerate(ferme):
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
        scelta = self._quante.get("storia", 0)   # una apertura, un personaggio
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

    def _riquadro(self, d, testo, font):
        """Quanta tela serve a scrivere `testo` partendo da (0, 0).

        Non e' `_largo` piu' `_alto`: quelli misurano l'inchiostro, qui serve
        il posto che occupa **dal punto in cui si scrive**, perche' la striscia
        si incolla nello stesso punto dove sarebbe andata la riga. Un pixel in
        meno e la «g» resta senza la coda.
        """
        try:
            riquadro = d.textbbox((0, 0), testo, font=font)
            return max(1, riquadro[2] + 1), max(1, riquadro[3] + 1)
        except AttributeError:                    # pragma: no cover - PIL vecchia
            larga, alta = d.textsize(testo, font=font)
            return max(1, larga + 1), max(1, alta + 1)

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
        riassunto["giro"] = self._turno
        return riassunto
