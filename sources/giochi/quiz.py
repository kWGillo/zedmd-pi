# -*- coding: utf-8 -*-
"""Super Quiz: quindici domande, quattro risposte, una scala di premi.

Il gioco
--------
Una domanda per volta, quattro risposte, e un montepremi che raddoppia. Si
sceglie con la leva e si preme fuoco; poi il pannello chiede **«La
accendiamo?»**, e solo il secondo fuoco vale. Quella domanda in mezzo non e'
un fronzolo preso dalla televisione: e' l'unica cosa che distingue «ho
scelto» da «ho sfiorato il tasto», e su un pad tenuto in mano mentre si
discute di una risposta capita piu' spesso di quanto si creda.

Due **traguardi**, alla quinta e alla decima domanda: sbagliando si torna li'
invece che a zero. Senza, quindici domande di fila sono una scommessa sola e
nessuno arriva in fondo.

Perche' non assomiglia agli altri otto
--------------------------------------
Non c'e' niente da schivare e non ci sono fotogrammi da far scorrere: qui
il pannello e' **tutto testo**, e il tempo passa solo nel momento in cui stai
decidendo. Per questo il gioco si prende anche i 56 pixel del tabellone --
una domanda su due righe da sessanta caratteri non ci sta altrimenti -- e
disegna il suo, piccolo, in cima.

La musica
---------
Quattro brani per quattro momenti: quando la domanda compare, mentre si
aspetta, quando si indovina e quando si sbaglia. Quali siano lo dice la
configurazione, cosi' si possono cambiare senza toccare il codice.

Le domande
----------
Stanno in `domande.it.csv` e `domande.en.csv` e le serve il modulo `domande`,
che sa anche non ripetersi fra una partita e l'altra. Il gioco segue la
lingua dell'interfaccia: se la pagina e' in inglese, il quiz e' in inglese.
"""

import time

from PIL import Image

import domande as banca

from .base import ALTEZZA, LARGHEZZA, Gioco, centra, larghezza_testo, scrivi

# La scala dei premi. Quindici gradini, con i due traguardi in grassetto
# nella testa di chi gioca: il quinto e il decimo.
SCALA = (100, 200, 300, 500, 1000,
         2000, 4000, 8000, 16000, 32000,
         64000, 125000, 250000, 500000, 1000000)
TRAGUARDI = (5, 10)

# Quanto dura ogni momento, in secondi.
DURATA_DOMANDA = 2.4       # la domanda compare, e si legge
TEMPO_RISPOSTA = 60.0      # il tempo per decidere

# Quanto resta ferma la schermata della scelta prima di partire da sola. Chi
# ha premuto Start e si e' allontanato non deve lasciare il pannello su un
# menu: dopo questo tempo si gioca con il tempo, che e' il modo normale.
DURATA_SCELTA = 20.0

# Senza tempo il gioco non si chiude per inattivita' come gli altri -- e' il
# punto di giocare senza tempo -- ma un limite lontano resta: una partita
# lasciata a meta' e dimenticata non puo' tenersi il pannello per sempre.
# Mezz'ora e' «te ne sei andato», non «ci sto pensando».
INATTIVITA_SENZA_TEMPO = 1800
# Quanto resta la risposta prima della domanda dopo. Sono i tempi di riserva:
# quando il brano del momento si sa quanto dura, comanda lui -- la musica
# della risposta non e' un sottofondo, e' il tempo che passa, e tagliarla a
# meta' per far comparire la domanda dopo si sente come un difetto. Questi
# numeri restano per quando la musica e' spenta o il file non si legge.
DURATA_GIUSTA = 3.6
DURATA_SBAGLIATA = 4.6
DURATA_FINALE = 5.0

# I due estremi entro cui la musica puo' comandare. Sotto, un brano di mezzo
# secondo farebbe sparire la risposta prima che si legga; sopra, un brano
# lungo messo li' per sbaglio terrebbe il gioco fermo -- e il fuoco, che
# salta l'attesa, e' comunque sempre buono.
MINIMA_RISPOSTA = 2.0
# Il tetto e' quello della conversione: chiesto cosi', «la domanda successiva
# deve apparire dopo che il file audio e' terminato». Venti secondi tagliavano
# un brano piu' lungo, cioe' facevano proprio la cosa che non si voleva. Il
# fuoco salta l'attesa, e oltre i quarantacinque secondi non si converte.
MASSIMA_RISPOSTA = 45.0

LETTERE = "ABCD"

# La riga delle risposte: due colonne, che e' l'unico modo di far stare
# quattro risposte su un pannello alto 64 pixel senza scriverle in fila.
COLONNA = (2, 130)
LARGHEZZA_COLONNA = 30     # caratteri per colonna, prefisso compreso

GIALLO = (255, 210, 40)
AMBRA = (255, 150, 30)
VERDE = (60, 220, 90)
ROSSO = (255, 70, 70)
AZZURRO = (90, 200, 255)
GRIGIO = (110, 110, 120)
BIANCO = (235, 235, 245)


def spezza(testo, quanti, righe=2):
    """Il testo a capo sulle parole, in al massimo `righe` righe."""
    parole = (testo or "").split()
    fuori, riga = [], ""
    for parola in parole:
        prova = (riga + " " + parola).strip()
        if len(prova) <= quanti:
            riga = prova
            continue
        if riga:
            fuori.append(riga)
        riga = parola
        if len(fuori) == righe:
            break
    if riga and len(fuori) < righe:
        fuori.append(riga)
    if len(fuori) == righe and len(" ".join(parole)) > sum(len(r) + 1 for r in fuori):
        # Non ci sta tutto: l'ultima riga finisce con i puntini, che dicono
        # «manca qualcosa» meglio di una frase tagliata netta.
        ultima = fuori[-1]
        while len(ultima) > quanti - 1:
            ultima = ultima[:ultima.rfind(" ")] if " " in ultima else ultima[:-1]
        fuori[-1] = ultima + "…"
    return fuori


def _viste_per_lingua(valore):
    """La memoria delle domande uscite, sempre nella forma nuova.

    Accetta anche quella vecchia -- una lista sola, di quando le due banche
    erano gemelle -- e la mette da parte come memoria italiana: e' la lingua
    in cui quasi tutti hanno giocato, e nel dubbio si dimentica qualcosa,
    non si finge di ricordare.
    """
    if isinstance(valore, dict):
        return {lingua: list(valore.get(lingua) or []) for lingua in ("it", "en")}
    if isinstance(valore, (list, tuple)):
        return {"it": list(valore), "en": []}
    return {"it": [], "en": []}


def soldi(valore):
    """1000 diventa 1.000: sul pannello i punti si leggono, le cifre no."""
    return "{:,}".format(int(valore)).replace(",", ".")


class Quiz(Gioco):
    nome = "quiz"
    etichetta = "Super Quiz"
    colore_hud = GIALLO
    COMANDI = ("sinistra", "destra", "su", "giu", "fuoco", "esci")

    # La musica di serie, una per momento. La configurazione puo' cambiarle
    # tutte e quattro: sono nomi di file dentro `suoni/`, senza estensione.
    MUSICHE = {
        "domanda": "quiz_domanda",
        "attesa": "quiz_attesa",
        "giusta": "quiz_giusta",
        "sbagliata": "quiz_sbagliata",
    }

    def __init__(self, seme=None):
        self.lingua = "it"
        self.musiche = dict(self.MUSICHE)
        self._tutte_viste = {}
        self.tempo_risposta = TEMPO_RISPOSTA
        self.musica_accesa = True
        self._viste = []
        self._mazzo = None
        super(Quiz, self).__init__(seme)

    # ----------------------------------------------------------- la partita

    def avvia_partita(self, seme=None):
        # I tasti tenuti premuti nell'istante in cui la partita comincia non
        # contano: si comincia da fermi, e il primo comando e' il primo tasto
        # **premuto** da qui in avanti. Quelli gia' giu' restano giu' -- non
        # si azzerano: e' proprio il fuoco che ha fatto ricominciare la
        # partita, e azzerarlo lo farebbe valere una seconda volta,
        # attraversando da solo la schermata della scelta.
        self._premuti_prima = getattr(self, "_premuti_prima", set())
        self.punteggio = 0
        self.vite = 1
        self.livello = 1
        self.finita = False
        self.gradino = 0              # quante domande gia' indovinate
        self.vinto = 0                # quello che si porta a casa adesso
        self.scelta = 0
        self.conferma = True          # SI o NO nella richiesta di conferma
        # Si comincia scegliendo **come** si gioca. Con il tempo e' una gara
        # con se stessi; senza, e' un gioco da tavolo in cui si discute la
        # risposta -- ed e' il modo in cui lo si usa in due.
        self.senza_tempo = False
        self.fase = "avvio"
        self.messaggio = ""
        self.domanda = None
        self.rimasto = self.tempo_risposta
        self._scadenza = DURATA_SCELTA
        self._orologio = 0.0
        self._mazzo = banca.Mazzo(self.lingua, self._viste, seme)
        self._prossima()

    def configura(self, conf):
        """Le impostazioni che stanno in configurazione, non nel codice."""
        conf = conf or {}
        musiche = conf.get("quiz_musica") or {}
        for momento in self.MUSICHE:
            nome = str(musiche.get(momento, "") or "").strip()
            self.musiche[momento] = nome or self.MUSICHE[momento]
        try:
            self.tempo_risposta = max(5.0, min(180.0, float(
                conf.get("quiz_tempo", TEMPO_RISPOSTA))))
        except (TypeError, ValueError):
            self.tempo_risposta = TEMPO_RISPOSTA
        # Con la musica spenta la risposta non puo' durare quanto un brano
        # che non parte: si torna ai tempi di riserva.
        self.musica_accesa = bool(conf.get("musica", True))
        self._tutte_viste = _viste_per_lingua(conf.get("quiz_viste"))
        self._viste = list(self._tutte_viste.get(self.lingua, []))
        self.rimasto = self.tempo_risposta
        self._mazzo = banca.Mazzo(self.lingua, self._viste)
        self._prossima()

    def configura_lingua(self, lingua):
        """Il quiz parla la lingua dell'interfaccia: la sceglie chi lo apre."""
        self.lingua = "en" if lingua == "en" else "it"
        # Ogni lingua ha la sua memoria: le due banche non fanno le stesse
        # domande, e un identificativo italiano dentro il conto inglese non
        # vuol dire niente.
        self._viste = list(self._tutte_viste.get(self.lingua, []))
        self._mazzo = banca.Mazzo(self.lingua, self._viste)
        self._prossima()

    def memoria_domande(self):
        """Gli identificativi usciti, per lingua: {"it": [...], "en": [...]}."""
        fuori = dict(self._tutte_viste)
        if self._mazzo is not None:
            fuori[self.lingua] = self._mazzo.memoria()
        return fuori

    def difficolta_del_gradino(self):
        """Le prime cinque facili, le ultime cinque da esperti."""
        if self.gradino < 5:
            return 1
        return 2 if self.gradino < 10 else 3

    def _prossima(self):
        if self._mazzo is None:
            return
        self.domanda = self._mazzo.pesca(self.difficolta_del_gradino())
        self.scelta = 0
        self.livello = self.gradino + 1
        self.rimasto = self.tempo_risposta
        if self.domanda is None:
            # Nessuna domanda: non e' un guasto del gioco, e' un file che
            # manca. Si dice e si chiude, invece di mostrare un pannello vuoto.
            self.finita = True
            self.fase = "finale"
            self.messaggio = ("NESSUNA DOMANDA" if self.lingua == "it"
                              else "NO QUESTIONS")

    def traguardo(self):
        """Quello che resta in mano sbagliando adesso."""
        vinto = 0
        for quanti in TRAGUARDI:
            if self.gradino >= quanti:
                vinto = SCALA[quanti - 1]
        return vinto

    # ------------------------------------------------------------- il passo

    def ignora_tasti(self, premuti):
        """Quello che e' gia' premuto quando la partita si apre non conta."""
        self._premuti_prima = set(premuti)

    def _appena(self, tasti):
        """I tasti **appena premuti**: quelli di adesso meno quelli di prima.

        Il quiz e' un gioco di menu, non di riflessi: qui un tasto tenuto giu'
        deve valere una volta, non trenta al secondo. Senza questa riga
        succedeva quello che e' stato segnalato dal campo -- si rientra nel
        gioco tenendo premuto il fuoco, e la schermata "con il tempo o senza"
        passa in un fotogramma scegliendo da sola; e se il tasto tenuto era
        una freccia, partiva nell'altro modo. Dal pad e' indistinguibile da
        un gioco che decide per conto suo.
        """
        tasti = set(tasti)
        nuovi = tasti - self._premuti_prima
        self._premuti_prima = tasti
        return nuovi

    def passo(self, dt, tasti):
        tasti = self._appena(tasti)
        if self.finita and self.fase == "finale":
            self._orologio += dt
            # Fuoco ricomincia, come in tutti gli altri nove giochi. Mancava,
            # ed era un difetto vero: finita una partita il quiz non
            # rispondeva piu' a niente, e l'unico modo di rigiocare era
            # uscire dal cabinato e rientrare -- quando andava bene, perche'
            # rientrando sullo stesso gioco si ritrovava la stessa partita
            # finita, e sembrava che il pad avesse smesso di funzionare.
            #
            # Il mezzo secondo di margine e' lo stesso ragionamento della
            # conferma: il fuoco che ha dato l'ultima risposta non deve
            # anche far ripartire la partita dopo.
            if "fuoco" in tasti:
                self.avvia_partita()
            return
        self._orologio += dt
        if self.fase == "avvio":
            self._scelta_del_tempo(tasti)
            return
        if self.fase == "domanda":
            if self._orologio >= DURATA_DOMANDA or "fuoco" in tasti:
                self.fase = "attesa"
                self._orologio = 0.0
            return
        if self.fase == "attesa":
            self._attesa(dt, tasti)
            return
        if self.fase == "conferma":
            self._conferma(tasti)
            return
        if self.fase in ("giusta", "sbagliata"):
            if self._orologio >= self.durata_della_risposta() or "fuoco" in tasti:
                self._avanti()

    def durata_della_risposta(self):
        """Quanto dura il momento della risposta: **il suo brano**.

        La domanda dopo arriva quando la musica finisce. Con i brani di serie
        vuol dire sette secondi per la risposta giusta e nove e mezzo per
        quella sbagliata, invece dei tre e mezzo e quattro e mezzo di prima,
        che li tagliavano a meta'. Chi ha fretta preme fuoco e va avanti; chi
        mette un suo brano al posto del nostro se lo sente tutto, senza dover
        toccare niente.

        Se la musica e' spenta, o il file non si legge, valgono i tempi di
        riserva: un gioco muto non deve aspettare una musica che non parte.
        """
        riserva = (DURATA_GIUSTA if self.fase == "giusta"
                   else DURATA_SBAGLIATA)
        if not self.musica_accesa:
            return riserva
        try:
            quanto = float(self.durata_musica(self.musica_di_adesso()))
        except Exception:
            quanto = 0.0
        if quanto <= 0.0:
            return riserva
        # Mezzo secondo di margine sulla musica: il mixer scrive a blocchi
        # di 23 ms e la domanda dopo non deve comparire sull'ultima nota.
        return max(MINIMA_RISPOSTA, min(MASSIMA_RISPOSTA, quanto + 0.5))

    def _scelta_del_tempo(self, tasti):
        """Con il tempo o senza: la leva sceglie, il fuoco comincia."""
        if "sinistra" in tasti and self.senza_tempo:
            self.senza_tempo = False
            self.suona("ping")
        if "destra" in tasti and not self.senza_tempo:
            self.senza_tempo = True
            self.suona("ping")
        if "fuoco" in tasti or self._orologio >= DURATA_SCELTA:
            self.fase = "domanda"
            self._orologio = 0.0
            self.rimasto = self.tempo_risposta
            self.suona("lancio")

    def limite_inattivita(self, limite):
        """Quanto puo' restare fermo il pannello prima che la partita si chiuda.

        Senza tempo la partita non si chiude al limite degli altri giochi: e'
        esattamente il motivo per cui si sceglie di giocare senza tempo, e una
        domanda su cui si sta discutendo da tre minuti non e' una partita
        abbandonata. Un limite lontano resta comunque, perche' un pannello
        tenuto per sempre da una partita dimenticata e' un pannello rotto per
        chi passa di li' e non sa cosa stava succedendo.
        """
        if self.senza_tempo and not self.finita:
            return max(limite, INATTIVITA_SENZA_TEMPO)
        return limite

    def _attesa(self, dt, tasti):
        if self.senza_tempo:
            # Il tempo non passa: la barra non c'e' e non scade niente.
            self.rimasto = self.tempo_risposta
        else:
            self.rimasto = max(0.0, self.rimasto - dt)
        if not self.senza_tempo and self.rimasto <= 0:
            # Tempo scaduto: vale come una risposta sbagliata, ed e' giusto
            # cosi' -- in un quiz il tempo e' parte della domanda.
            self._sbagliato(scaduto=True)
            return
        if "sinistra" in tasti and self.scelta % 2 == 1:
            self.scelta -= 1
            self.suona("ping")
        if "destra" in tasti and self.scelta % 2 == 0:
            self.scelta += 1
            self.suona("ping")
        if "su" in tasti and self.scelta >= 2:
            self.scelta -= 2
            self.suona("ping")
        if "giu" in tasti and self.scelta < 2:
            self.scelta += 2
            self.suona("ping")
        if "fuoco" in tasti:
            self.fase = "conferma"
            self._orologio = 0.0
            # Si riparte sempre da SI: la conferma e' un fermo, non un dubbio.
            self.conferma = True
            self.suona("lancio")

    def _conferma(self, tasti):
        """«La accendiamo?» -- SI o NO con le frecce, il fuoco conferma.

        Dalla 14.1 e' una scelta vera fra due caselle invece di due tasti da
        ricordare: chiesto cosi', ed e' anche il modo in cui la domanda si
        capisce senza istruzioni. Si parte da SI, che e' la risposta che si
        vuole dare nove volte su dieci: chi ha premuto fuoco per rispondere
        preme fuoco un'altra volta e ha risposto.
        """
        if "sinistra" in tasti and not self.conferma:
            self.conferma = True
            self.suona("ping")
        if "destra" in tasti and self.conferma:
            self.conferma = False
            self.suona("ping")
        if "esci" in tasti or "speciale" in tasti:
            self.fase = "attesa"
            self.suona("ping")
            return
        if "fuoco" in tasti:
            if self.conferma:
                if self.scelta == self.domanda["giusta"]:
                    self._giusto()
                else:
                    self._sbagliato()
            else:
                # NO: si torna a scegliere la risposta, senza rispondere.
                self.fase = "attesa"
                self.suona("ping")

    def _giusto(self):
        self.gradino += 1
        self.vinto = SCALA[self.gradino - 1]
        self.punteggio = self.vinto
        self.fase = "giusta"
        self._orologio = 0.0
        self.suona("punto")
        self._aggiorna_record()
        if self.gradino >= len(SCALA):
            self.messaggio = "MILIONE!" if self.lingua == "it" else "MILLION!"

    def _sbagliato(self, scaduto=False):
        self.vinto = self.traguardo()
        self.punteggio = self.vinto
        self.fase = "sbagliata"
        self._orologio = 0.0
        self.messaggio = ("TEMPO SCADUTO" if self.lingua == "it" else "TIME UP") \
            if scaduto else ""
        self.suona("persa")
        self._aggiorna_record()

    def _avanti(self):
        if self.fase == "sbagliata" or self.gradino >= len(SCALA):
            self.finita = True
            self.fase = "finale"
            self._orologio = 0.0
            return
        self.fase = "domanda"
        self._orologio = 0.0
        self._prossima()

    # ------------------------------------------------------------- la musica

    def musica_di_adesso(self):
        if self.fase in ("avvio", "domanda"):
            # La schermata della scelta ha la stessa musica della domanda che
            # compare: e' lo stesso momento, il sipario che si apre.
            return self.musiche["domanda"]
        if self.fase in ("attesa", "conferma"):
            return self.musiche["attesa"]
        if self.fase == "giusta":
            return self.musiche["giusta"]
        if self.fase == "sbagliata":
            return self.musiche["sbagliata"]
        return None

    def musica_da_capo(self):
        """Nelle due schermate della risposta, sempre: il brano **e'** il
        momento, e la domanda dopo aspetta che finisca. Sentirne la coda
        perche' stava gia' suonando vuol dire, da fuori, che non e' partito.
        """
        return self.fase in ("giusta", "sbagliata")

    def musica_a_giro(self):
        """Nelle due schermate della risposta il brano suona **una volta**.

        La domanda dopo aspetta che finisca: se finito ricominciasse, si
        sentirebbe un pezzo di attacco in piu' prima di andare avanti. Con un
        brano corto e' la meta' del brano, e dal divano si sente come un
        difetto -- perche' lo e'.
        """
        return self.fase not in ("giusta", "sbagliata")

    # ------------------------------------------------------------- il disegno

    def disegna(self):
        """Tutto il pannello, tabellone compreso.

        E' l'unico dei nove a farlo: una domanda da sessanta caratteri per due
        righe ha bisogno di tutti i 256 pixel, e un gioco fatto di parole non
        ha niente da mettere in una colonna laterale.
        """
        img = Image.new("RGB", (LARGHEZZA, ALTEZZA), (0, 0, 0))
        px = img.load()
        if self.fase == "avvio":
            self._disegna_avvio(px)
            return img
        if self.fase == "finale":
            self._disegna_finale(px)
            return img
        self._disegna_testa(px)
        self._disegna_domanda(px)
        self._disegna_risposte(px)
        self._disegna_piede(px)
        return img

    def _disegna_avvio(self, px):
        centra(px, "SUPER QUIZ", 6, GIALLO, 0, LARGHEZZA)
        domanda = ("COME VUOI GIOCARE?" if self.lingua == "it"
                   else "HOW DO YOU WANT TO PLAY?")
        centra(px, domanda, 18, GRIGIO, 0, LARGHEZZA)
        voci = (("CON IL TEMPO", "TIMED"), ("SENZA TEMPO", "NO TIMER"))
        for indice, voce in enumerate(voci):
            testo = voce[0] if self.lingua == "it" else voce[1]
            scelta = (indice == 1) == self.senza_tempo
            x = 20 + indice * 122
            scrivi(px, testo, x + 6, 32, BIANCO if scelta else GRIGIO)
            if scelta:
                for dy in range(6):
                    px[x, 31 + dy] = GIALLO
                    px[x + 1, 31 + dy] = GIALLO
        secondi = ("%d SECONDI PER RISPONDERE" if self.lingua == "it"
                   else "%d SECONDS TO ANSWER") % int(self.tempo_risposta)
        centra(px, secondi if not self.senza_tempo else
               ("TUTTO IL TEMPO CHE VUOI" if self.lingua == "it"
                else "ALL THE TIME YOU WANT"), 44, AZZURRO, 0, LARGHEZZA)
        aiuto = ("LEVA SCEGLIE - FUOCO COMINCIA" if self.lingua == "it"
                 else "STICK CHOOSES - FIRE STARTS")
        centra(px, aiuto, 55, GRIGIO, 0, LARGHEZZA)

    def _disegna_testa(self, px):
        domanda = self.domanda or {}
        scrivi(px, domanda.get("categoria", "")[:28].upper(), 2, 1, GRIGIO)
        premio = SCALA[min(self.gradino, len(SCALA) - 1)]
        testo = "%d/%d  %s" % (self.gradino + 1, len(SCALA), soldi(premio))
        scrivi(px, testo, LARGHEZZA - larghezza_testo(testo) - 2, 1, GIALLO)

    def _disegna_domanda(self, px):
        domanda = self.domanda or {}
        righe = spezza(domanda.get("domanda", ""), 62, 2)
        for indice, riga in enumerate(righe):
            centra(px, riga, 10 + indice * 8, BIANCO, 0, LARGHEZZA)

    def _disegna_risposte(self, px):
        domanda = self.domanda or {}
        risposte = domanda.get("risposte", [])
        mostra = self.fase in ("giusta", "sbagliata")
        for indice, risposta in enumerate(risposte[:4]):
            x = COLONNA[indice % 2]
            y = 28 + (indice // 2) * 9
            colore = AZZURRO
            if mostra and indice == domanda.get("giusta"):
                colore = VERDE
            elif mostra and indice == self.scelta:
                colore = ROSSO
            elif not mostra and indice == self.scelta:
                colore = BIANCO
            testo = "%s %s" % (LETTERE[indice],
                               risposta[:LARGHEZZA_COLONNA - 2])
            scrivi(px, testo, x + 4, y, colore)
            if indice == self.scelta and not mostra:
                # La scelta si vede da un lato, non da una cornice: una
                # cornice su un pannello cosi' fitto toglie una riga di testo.
                for dy in range(6):
                    px[x, y - 1 + dy] = (AMBRA if self.fase == "conferma"
                                         else GIALLO)
                    px[x + 1, y - 1 + dy] = (AMBRA if self.fase == "conferma"
                                             else GIALLO)

    def _disegna_piede(self, px):
        domanda = self.domanda or {}
        if self.fase == "conferma":
            testo = "LA ACCENDIAMO?" if self.lingua == "it" else "IS THAT YOUR ANSWER?"
            centra(px, testo, 45, AMBRA, 0, LARGHEZZA)
            self._disegna_si_no(px, 55)
            return
        if self.fase == "giusta":
            testo = self.messaggio or ("GIUSTA!" if self.lingua == "it" else "RIGHT!")
            centra(px, testo, 46, VERDE, 0, LARGHEZZA)
            curiosita = spezza(domanda.get("curiosita", ""), 62, 1)
            if curiosita:
                centra(px, curiosita[0], 55, GRIGIO, 0, LARGHEZZA)
            return
        if self.fase == "sbagliata":
            testo = self.messaggio or ("SBAGLIATA" if self.lingua == "it"
                                       else "WRONG")
            centra(px, testo, 46, ROSSO, 0, LARGHEZZA)
            resta = ("RESTI CON %s" if self.lingua == "it" else "YOU KEEP %s")
            centra(px, resta % soldi(self.vinto), 55, GIALLO, 0, LARGHEZZA)
            return
        # Attesa: la barra del tempo, che e' l'unica cosa che si muove.
        self._disegna_tempo(px)

    def _disegna_si_no(self, px, y):
        """SI e NO affiancati, con la barretta su quello scelto.

        La barretta e non il solo colore: e' la stessa grammatica della
        schermata di avvio e di quella delle risposte, e a tre metri due
        parole di colore diverso si distinguono peggio di un segno.
        """
        voci = ((("SI" if self.lingua == "it" else "YES"), True, VERDE),
                ("NO", False, ROSSO))
        for indice, (testo, quale, colore) in enumerate(voci):
            scelto = (quale == self.conferma)
            x = LARGHEZZA // 2 - 40 + indice * 56
            scrivi(px, testo, x + 6, y, colore if scelto else GRIGIO)
            if scelto:
                for dy in range(6):
                    px[x, y - 1 + dy] = colore
                    px[x + 1, y - 1 + dy] = colore

    def _disegna_tempo(self, px):
        if self.senza_tempo:
            traguardo = self.traguardo()
            if traguardo:
                testo = ("SICURO %s" if self.lingua == "it" else "SAFE %s") % soldi(traguardo)
                centra(px, testo, 52, GRIGIO, 0, LARGHEZZA)
            return
        quota = max(0.0, min(1.0, self.rimasto / max(1.0, self.tempo_risposta)))
        larghezza = int((LARGHEZZA - 8) * quota)
        colore = VERDE if quota > 0.5 else (GIALLO if quota > 0.2 else ROSSO)
        for x in range(larghezza):
            for y in range(50, 53):
                px[4 + x, y] = colore
        traguardo = self.traguardo()
        if traguardo:
            testo = ("SICURO %s" if self.lingua == "it" else "SAFE %s") % soldi(traguardo)
            centra(px, testo, 56, GRIGIO, 0, LARGHEZZA)

    def _disegna_finale(self, px):
        # Tre finali diversi, e dirli uguali sarebbe una presa in giro: chi
        # e' arrivato in fondo ha vinto, chi si ferma a un traguardo si
        # porta a casa qualcosa, chi sbaglia la prima non si porta niente.
        if self.gradino >= len(SCALA):
            titolo = "HAI VINTO" if self.lingua == "it" else "YOU WON"
        elif self.vinto > 0:
            titolo = "TI PORTI A CASA" if self.lingua == "it" else "YOU TAKE HOME"
        else:
            titolo = "PARTITA FINITA" if self.lingua == "it" else "GAME OVER"
        if self.messaggio.startswith("NESSUNA") or self.messaggio.startswith("NO "):
            centra(px, self.messaggio, 24, ROSSO, 0, LARGHEZZA)
            centra(px, "FUOCO PER RIPROVARE" if self.lingua == "it"
                   else "FIRE TO TRY AGAIN", 44, GRIGIO, 0, LARGHEZZA)
            return
        centra(px, titolo, 16, GRIGIO, 0, LARGHEZZA)
        centra(px, soldi(self.vinto), 28, GIALLO, 0, LARGHEZZA)
        quante = ("%d RISPOSTE GIUSTE" if self.lingua == "it"
                  else "%d RIGHT ANSWERS") % self.gradino
        centra(px, quante, 40, VERDE, 0, LARGHEZZA)
        # E come si rigioca. Una schermata finale che non dice cosa fare e'
        # una schermata da cui si esce spegnendo.
        centra(px, "FUOCO PER RIGIOCARE" if self.lingua == "it"
               else "FIRE TO PLAY AGAIN", 52, GRIGIO, 0, LARGHEZZA)

    # Il campo non esiste: qui si disegna tutto a mano, e `disegna` non
    # chiama mai questo metodo. Sta qui perche' la classe base lo pretende.
    def disegna_campo(self, img, px):     # pragma: no cover
        pass

    def stato(self):
        base = Gioco.stato(self)
        base.update({"gradino": self.gradino, "fase": self.fase,
                     "vinto": self.vinto, "lingua": self.lingua,
                     "senza_tempo": self.senza_tempo})
        return base
