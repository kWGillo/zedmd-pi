# -*- coding: utf-8 -*-
"""I tre punteggi migliori, e le tre lettere di chi li ha fatti.

Perche' esiste
--------------
Fino alla 12.6 di una partita restava un numero solo: il record del gioco,
senza nome e senza storia. Va bene per un giocatore solo, non regge la
seconda persona che si siede davanti -- e un cabinato con due persone davanti
e' esattamente il punto.

Qui ci sono le due cose che nei bar c'erano nel 1989 e che nessuno ha mai
migliorato: la **classifica dei tre migliori**, e le **tre lettere** da
comporre a fine partita, una alla volta, con la leva e il pulsante. Tre
lettere e non un nome intero perche' con tre lettere si finisce prima di
cambiare idea, e perche' e' cosi' che si fa.

Chi disegna cosa
----------------
`Classifica` e' solo i dati: legge e scrive in configurazione, e non sa niente
di pannelli. `Epilogo` e' la macchina a stati che dopo il GAME OVER prende il
pannello per qualche secondo: mostra il punteggio, se serve fa comporre le
iniziali, e poi fa vedere la classifica. Non e' un gioco e non sta dentro
nessuno dei nove: appartiene al **cabinato**, come il record, e infatti e' la
sorgente dei giochi a metterlo in mezzo.

Il tempo non si ferma mai
-------------------------
Ogni schermata ha un tempo massimo, compreso l'inserimento delle iniziali:
chi si alza e se ne va lascerebbe il pannello fermo su una schermata di
attesa per sempre, e un pannello che aspetta e' un pannello rotto per chi
passa di li' e non sa cosa stava succedendo. Scaduto il tempo, quello che era
stato composto vale, e si va avanti.
"""

import time

from PIL import Image

from .base import ALTEZZA, LARGHEZZA, centra, scrivi

# Quante posizioni tiene la classifica. Tre come nei cabinati: cinque erano
# gia' troppi da leggere in piedi.
QUANTI = 3

# L'alfabeto da comporre, nell'ordine in cui scorre sotto la leva. Lo spazio
# in fondo serve a chi vuole due lettere sole.
ALFABETO = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "
INIZIALI = 3

# Le tre fasi, e quanto durano.
DURATA_FINE = 2.2          # GAME OVER, prima di tutto il resto
DURATA_NOME = 25.0         # per comporre le iniziali
DURATA_CLASSIFICA = 7.0    # la classifica, prima di tornare al gioco

# Ogni quanto scorre la lettera se tieni premuta la leva.
RIPETIZIONE = 0.22
PRIMA_RIPETIZIONE = 0.45

# I colori delle schermate, presi dai cabinati: le posizioni in verde, i
# punteggi in azzurro, i nomi in magenta, il titolo in giallo.
GIALLO = (255, 210, 40)
VERDE = (60, 220, 90)
AZZURRO = (90, 200, 255)
MAGENTA = (255, 80, 200)
GRIGIO = (120, 120, 130)
BIANCO = (235, 235, 245)


def _adesso():
    return time.time()


class Classifica:
    """I tre migliori di un gioco: leggere, confrontare, scrivere.

    I dati stanno in `cfg["giochi"]["classifica"][nome]`, una lista di
    dizionari `{punti, nome, livello, quando}` gia' in ordine. Il vecchio
    `record` resta scritto accanto e aggiornato: e' quello che la pagina web,
    Home Assistant e il tabellone del gioco leggono da versioni, e romperlo
    per un riordino interno sarebbe un dispetto.
    """

    def __init__(self, conf):
        self.conf = conf if conf is not None else {}

    def _tabella(self):
        return self.conf.setdefault("classifica", {})

    def elenco(self, gioco):
        voci = []
        for voce in (self._tabella().get(gioco) or [])[:QUANTI]:
            try:
                voci.append({"punti": int(voce.get("punti", 0)),
                             "nome": str(voce.get("nome", ""))[:INIZIALI].upper(),
                             "livello": int(voce.get("livello", 0) or 0),
                             "quando": float(voce.get("quando", 0) or 0)})
            except (TypeError, ValueError):
                continue
        return voci

    def record(self, gioco):
        voci = self.elenco(gioco)
        return voci[0]["punti"] if voci else int(
            (self.conf.get("record") or {}).get(gioco, 0) or 0)

    def posizione(self, gioco, punti):
        """In che posizione finirebbe questo punteggio, o 0 se non entra.

        A parita' di punti si resta **dietro** a chi c'era gia': il primo che
        ci arriva tiene il posto, ed e' la regola di tutti i cabinati.
        """
        if punti <= 0:
            return 0
        voci = self.elenco(gioco)
        for indice, voce in enumerate(voci):
            if punti > voce["punti"]:
                return indice + 1
        return len(voci) + 1 if len(voci) < QUANTI else 0

    def entra(self, gioco, punti):
        return self.posizione(gioco, punti) > 0

    def aggiungi(self, gioco, punti, nome, livello=0, quando=None):
        """Mette il punteggio al suo posto. Torna la posizione, o 0."""
        posto = self.posizione(gioco, punti)
        if not posto:
            return 0
        voci = self.elenco(gioco)
        voci.insert(posto - 1, {"punti": int(punti),
                                "nome": (nome or "")[:INIZIALI].upper(),
                                "livello": int(livello or 0),
                                "quando": float(quando or _adesso())})
        self._tabella()[gioco] = voci[:QUANTI]
        # Il record vecchio resta allineato: lo leggono la pagina web, Home
        # Assistant e il tabellone dentro la partita.
        record = self.conf.setdefault("record", {})
        record[gioco] = max(int(record.get(gioco, 0) or 0),
                            int(self._tabella()[gioco][0]["punti"]))
        return posto

    def migra(self):
        """Porta i vecchi record, senza nome, dentro la classifica nuova.

        Chi aggiorna non deve vedere le sue partite sparire: un record che
        c'era diventa il primo posto, con tre trattini al posto del nome --
        che e' anche il modo in cui un cabinato diceva «questo non l'ha
        firmato nessuno».
        """
        tabella = self._tabella()
        cambiato = False
        for gioco, punti in (self.conf.get("record") or {}).items():
            try:
                punti = int(punti)
            except (TypeError, ValueError):
                continue
            if punti > 0 and not tabella.get(gioco):
                tabella[gioco] = [{"punti": punti, "nome": "---",
                                   "livello": 0, "quando": 0.0}]
                cambiato = True
        return cambiato


class Epilogo:
    """Le schermate fra il GAME OVER e il ritorno al gioco.

    Tre fasi in fila: `fine`, `nome` (solo se il punteggio entra in
    classifica) e `classifica`. Quando `finito()` dice di si', la sorgente dei
    giochi smette di chiamarla e il pannello torna al gioco.
    """

    def __init__(self, gioco, punti, livello, classifica, lingua="it",
                 salva=None, adesso=None):
        self.gioco = gioco
        self.punti = int(punti)
        self.livello = int(livello or 0)
        self.classifica = classifica
        self.lingua = "en" if lingua == "en" else "it"
        self._salva = salva or (lambda: None)
        self.posizione = classifica.posizione(gioco, self.punti)
        self.fase = "fine"
        self.lettere = [0, 0, 0]          # indici dentro ALFABETO
        self.quale = 0
        self.nome_salvato = False
        # `adesso if adesso is not None`, non `adesso or`: l'istante zero e'
        # un istante valido, e nelle prove e' proprio quello da cui si parte.
        self._scadenza = (adesso if adesso is not None else _adesso()) + DURATA_FINE
        self._precedenti = set()
        self._ripeti_da = {}
        self.suona = lambda nome: None

    # ------------------------------------------------------------- il tempo

    def _passa_a(self, fase, durata, adesso):
        self.fase = fase
        self._scadenza = adesso + durata

    def finito(self):
        return self.fase == "fatto"

    # ------------------------------------------------------------ i comandi

    def _appena(self, premuti, adesso):
        """I comandi che contano in questo istante: appena premuti, o tenuti.

        Tenere la leva fa scorrere le lettere, come in ogni cabinato: la prima
        ripetizione dopo mezzo secondo, poi cinque al secondo. Senza, comporre
        una Z sono venticinque pressioni.
        """
        fuori = set()
        for azione in premuti:
            if azione not in self._precedenti:
                fuori.add(azione)
                self._ripeti_da[azione] = adesso + PRIMA_RIPETIZIONE
            elif adesso >= self._ripeti_da.get(azione, 0):
                fuori.add(azione)
                self._ripeti_da[azione] = adesso + RIPETIZIONE
        for azione in list(self._ripeti_da):
            if azione not in premuti:
                self._ripeti_da.pop(azione, None)
        self._precedenti = set(premuti)
        return fuori

    def passo(self, _dt, premuti, adesso=None):
        adesso = adesso if adesso is not None else _adesso()
        comandi = self._appena(premuti, adesso)

        if self.fase == "fine":
            # Il GAME OVER si puo' saltare, ma non con il tasto che si stava
            # gia' tenendo premuto: chi muore con il dito sul fuoco salterebbe
            # la schermata senza averla vista.
            if "fuoco" in comandi or adesso >= self._scadenza:
                self._apri_nome(adesso)
            return

        if self.fase == "nome":
            self._passo_nome(comandi, adesso)
            return

        if self.fase == "classifica":
            if "fuoco" in comandi or "avvia" in comandi or adesso >= self._scadenza:
                self.fase = "fatto"

    def _apri_nome(self, adesso):
        if self.posizione:
            self._passa_a("nome", DURATA_NOME, adesso)
        else:
            self._passa_a("classifica", DURATA_CLASSIFICA, adesso)

    def _passo_nome(self, comandi, adesso):
        if "su" in comandi:
            self.lettere[self.quale] = (self.lettere[self.quale] - 1) % len(ALFABETO)
            self.suona("ping")
        if "giu" in comandi:
            self.lettere[self.quale] = (self.lettere[self.quale] + 1) % len(ALFABETO)
            self.suona("ping")
        if "sinistra" in comandi and self.quale > 0:
            self.quale -= 1
            self.suona("ping")
        if "destra" in comandi and self.quale < INIZIALI - 1:
            self.quale += 1
            self.suona("ping")
        if "fuoco" in comandi or "avvia" in comandi:
            if self.quale < INIZIALI - 1:
                self.quale += 1
                self.suona("ping")
            else:
                self.conferma(adesso)
            return
        if adesso >= self._scadenza:
            # Tempo scaduto: quello che c'e' vale. Meglio un nome a meta' che
            # una classifica senza la partita appena giocata.
            self.conferma(adesso)

    def nome(self):
        return "".join(ALFABETO[i] for i in self.lettere).strip() or "---"

    def conferma(self, adesso=None):
        adesso = adesso if adesso is not None else _adesso()
        if not self.nome_salvato:
            self.classifica.aggiungi(self.gioco, self.punti, self.nome(),
                                     self.livello, adesso)
            self.nome_salvato = True
            self._salva()
            self.suona("record")
        self._passa_a("classifica", DURATA_CLASSIFICA, adesso)

    # ------------------------------------------------------------ il disegno

    T = {
        "fine": ("GAME OVER", "GAME OVER"),
        "punti": ("PUNTI", "SCORE"),
        "nuovo": ("NUOVO RECORD!", "NEW RECORD!"),
        "entrato": ("SEI FRA I MIGLIORI 3", "YOU MADE THE TOP 3"),
        "iniziali": ("SCRIVI LE TUE INIZIALI", "ENTER YOUR INITIALS"),
        "aiuto": ("SU/GIU LETTERA - FUOCO OK", "UP/DOWN LETTER - FIRE OK"),
        "migliori": ("I MIGLIORI 3", "BEST 3"),
        "vuota": ("NESSUN PUNTEGGIO", "NO SCORES YET"),
        "posti": ("1o", "1ST"),
        "riparti": ("FUOCO PER RIGIOCARE", "FIRE TO PLAY AGAIN"),
    }
    POSTI = {"it": ("1o", "2o", "3o"), "en": ("1ST", "2ND", "3RD")}

    def t(self, chiave):
        return self.T[chiave][0 if self.lingua == "it" else 1]

    def disegna(self):
        img = Image.new("RGB", (LARGHEZZA, ALTEZZA), (0, 0, 0))
        px = img.load()
        if self.fase == "fine":
            self._disegna_fine(px)
        elif self.fase == "nome":
            self._disegna_nome(px)
        else:
            self._disegna_classifica(px)
        return img

    def _disegna_fine(self, px):
        centra(px, self.t("fine"), 20, (255, 60, 60))
        centra(px, "%s %d" % (self.t("punti"), self.punti), 32, GIALLO)
        if self.posizione == 1:
            centra(px, self.t("nuovo"), 44, MAGENTA)
        elif self.posizione:
            centra(px, self.t("entrato"), 44, VERDE)

    def _disegna_nome(self, px):
        centra(px, self.t("nuovo") if self.posizione == 1 else self.t("entrato"),
               6, MAGENTA if self.posizione == 1 else VERDE)
        centra(px, "%s %d" % (self.t("punti"), self.punti), 16, GIALLO)
        # Le tre lettere, grandi e spaziate, con la sottolineatura su quella
        # che si sta componendo: e' il modo in cui si capisce dove si e'
        # senza leggere niente.
        passo = 22
        inizio = (LARGHEZZA - passo * INIZIALI) // 2 + 4
        for indice in range(INIZIALI):
            x = inizio + indice * passo
            lettera = ALFABETO[self.lettere[indice]]
            colore = BIANCO if indice == self.quale else AZZURRO
            self._lettera_grande(px, lettera, x, 28, colore)
            if indice == self.quale:
                for dx in range(10):
                    px[x - 1 + dx, 44] = MAGENTA
        centra(px, self.t("aiuto"), 52, GRIGIO)

    def _lettera_grande(self, px, lettera, x, y, colore):
        """Una lettera del font piccolo, raddoppiata. Sul pannello le tre
        iniziali devono leggersi da lontano: e' l'unico testo della serata che
        qualcuno guardera' da due metri."""
        campione = Image.new("RGB", (8, 8), (0, 0, 0))
        punti = campione.load()
        scrivi(punti, lettera, 0, 0, colore)
        for riga in range(7):
            for colonna in range(6):
                if campione.getpixel((colonna, riga)) != (0, 0, 0):
                    for dy in range(2):
                        for dx in range(2):
                            px[x + colonna * 2 + dx, y + riga * 2 + dy] = colore

    def _disegna_classifica(self, px):
        centra(px, self.t("migliori"), 4, GIALLO)
        voci = self.classifica.elenco(self.gioco)
        if not voci:
            centra(px, self.t("vuota"), 30, GRIGIO)
            return
        posti = self.POSTI["it" if self.lingua == "it" else "en"]
        for indice, voce in enumerate(voci[:QUANTI]):
            y = 16 + indice * 12
            mio = (self.nome_salvato and indice == self.posizione - 1)
            scrivi(px, posti[indice], 26, y, VERDE)
            scrivi(px, "%7d" % voce["punti"], 64, y,
                   BIANCO if mio else AZZURRO)
            scrivi(px, "%-3s" % (voce["nome"] or "---"), 150, y, MAGENTA)
            if voce["livello"]:
                scrivi(px, "LIV %d" % voce["livello"], 180, y, GRIGIO)
        centra(px, self.t("riparti"), 56, GRIGIO)
