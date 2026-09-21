"""Il cielo di stasera, sul pannello.

Cinque schermate, e ognuna risponde a una domanda sola:

* **la Luna** -- com'e' stasera, quando sorge, se cresce o cala;
* **una luna con un nome** -- la Luna del Raccolto, una superluna, una luna
  blu: il giorno, e quello che la rende diversa dalle altre;
* **una stagione** -- equinozio o solstizio, il giorno e quanta luce da';
* **uno sciame** -- il nome, quante meteore, e se la Luna le disturba;
* **la serata buona** -- vale la pena uscire a guardare, stasera?

La Luna si mostra solo fra il tramonto e l'alba: di giorno non la guarda
nessuno, e quando c'e' sta gia' in cielo a dirlo da sola. Le altre quattro
compaiono **solo quando c'e' qualcosa da dire**, e si alternano con la Luna
nelle serate in cui c'e': un pannello che annuncia cose rare si guarda, uno
che annuncia sempre qualcosa diventa sfondo.

I calcoli stanno in `cielo.py`, e da li' non si esce: questa sorgente disegna
e basta.
"""

import math
import threading
import time
from datetime import datetime, timedelta, timezone

from PIL import Image, ImageDraw

import cielo
import pianeti
from .base import Source
from .clock import _load_font

# --------------------------------------------------------------------- colori

# Gli stessi della grammatica del meteo, perche' il pannello resti coerente
# con se stesso: testo chiaro, grigio per la cornice, ambra per quello che
# importa. In piu' il colore della Luna, che e' quello vero -- bianco appena
# freddo -- e il verde e il rosso del "si'" e del "no".
TESTO = (0xE0, 0xE4, 0xF0)
SPENTO = (0x78, 0x80, 0x90)
AMBRA = (0xFF, 0x8C, 0x1A)
AZZURRO = (0x40, 0xB8, 0xFF)
# La Luna e' giallo panna, non bianca: e' come la si vede alta in una sera
# d'estate, e sul pannello un bianco pieno accanto alle scritte si
# confondeva con il testo.
LUNA = (0xF4, 0xE6, 0xB0)
# I crateri: lo stesso giallo, piu' scuro. Si vedono solo sulla parte in
# luce, come quelli veri.
CRATERE = (0xB8, 0xA8, 0x70)
# Dove stanno, in coordinate del disco da -1 a +1, e quanto sono grandi.
# Non sono messi a caso: sono le macchie grandi che si vedono a occhio nudo
# dall'emisfero nord -- i mari Imbrium e Serenitatis in alto, Tranquillitatis
# al centro, Crisium sul bordo destro, Nubium in basso, Tycho quasi al polo
# sud. Una Luna con le macchie al posto giusto si riconosce anche a 44 pixel.
CRATERI = (
    (-0.35, -0.45, 2), (0.22, -0.40, 2), (0.35, -0.08, 2), (0.70, -0.28, 1),
    (0.52, 0.18, 1), (-0.25, 0.35, 2), (-0.62, -0.05, 1), (-0.08, 0.72, 1),
    (0.05, 0.20, 1), (-0.45, 0.62, 1),
)
# La parte in ombra della Luna. Non nera: la luce cinerea -- la Terra che
# illumina la Luna -- si vede davvero a occhio nudo, e senza un bordo il disco
# di una falce sottile sembrerebbe un'unghia appesa nel nulla.
CINEREA = (0x1C, 0x1C, 0x26)
SI = (0x40, 0xE0, 0x70)
NO = (0xFF, 0x60, 0x40)

NOMI_FASI = {
    "nuova": "LUNA NUOVA",
    "crescente": "FALCE CRESCENTE",
    "primo_quarto": "PRIMO QUARTO",
    "gibbosa_crescente": "GIBBOSA CRESCENTE",
    "piena": "LUNA PIENA",
    "gibbosa_calante": "GIBBOSA CALANTE",
    "ultimo_quarto": "ULTIMO QUARTO",
    "calante": "FALCE CALANTE",
}

GIORNI = ("LUNEDI'", "MARTEDI'", "MERCOLEDI'", "GIOVEDI'", "VENERDI'",
          "SABATO", "DOMENICA")
GIORNI_CORTI = ("LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM")

NOMI_LUNE = {
    "raccolto": ("LUNA DEL", "RACCOLTO"),
    "superluna": ("SUPER", "LUNA"),
    "blu": ("LUNA", "BLU"),
}

NOMI_STAGIONI = {
    "equinozio_primavera": ("EQUINOZIO", "DI PRIMAVERA"),
    "solstizio_estate": ("SOLSTIZIO", "D'ESTATE"),
    "equinozio_autunno": ("EQUINOZIO", "D'AUTUNNO"),
    "solstizio_inverno": ("SOLSTIZIO", "D'INVERNO"),
}


def quando_a_parole(locale, adesso):
    """STASERA, DOMANI, o il giorno della settimana con il numero."""
    giorni = (locale.date() - adesso.date()).days
    if giorni == 0:
        return "STASERA" if locale.hour >= 15 else "OGGI"
    if giorni == 1:
        return "DOMANI"
    return "%s %d" % (GIORNI[locale.weekday()], locale.day)


def ora_breve(istante, fuso=None):
    if istante is None:
        return "--:--"
    return istante.astimezone(fuso).strftime("%H:%M")


# ------------------------------------------------------------------- disegno


class Tela(object):
    """Gli attrezzi di disegno delle cinque schermate, senza stato del servizio.

    Separati dalla sorgente perche' la pagina web e le prove devono poter
    disegnare una schermata senza accendere un thread ne' aspettare la sera.
    """

    SINISTRA = 70      # dove comincia la colonna del testo, a destra del disegno
    DISCO = 22         # raggio della Luna disegnata

    def __init__(self, width=256, height=64):
        self.width = width
        self.height = height
        self.f_grande = _load_font(max(16, int(height * 0.40)))
        self.f_medio = _load_font(max(11, int(height * 0.25)))
        self.f_piccolo = _load_font(max(8, int(height * 0.16)))

    def nuova(self):
        immagine = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        return immagine, ImageDraw.Draw(immagine)

    # ---------------------------------------------------------- la Luna

    def luna(self, d, cx, cy, r, frazione, crescente):
        """Il disco della Luna con la sua fase vera, pixel per pixel.

        Il terminatore -- la linea fra luce e ombra -- visto da qui e' mezza
        ellisse: a luna piena coincide con il bordo di sinistra, a primo
        quarto e' una retta verticale, a luna nuova con il bordo di destra.
        Per ogni riga del disco lo si calcola e si accende quello che sta
        dalla parte del Sole. Da noi, emisfero nord, la luna crescente e'
        illuminata a destra.
        """
        accesi = set()
        for dy in range(-r, r + 1):
            meta = math.sqrt(max(0.0, r * r - dy * dy))
            # Dove passa il terminatore su questa riga, da -meta a +meta.
            confine = meta * (1 - 2 * frazione)
            for dx in range(-int(meta), int(meta) + 1):
                u = dx if crescente else -dx
                acceso = u > confine
                if acceso:
                    accesi.add((dx, dy))
                d.point((cx + dx, cy + dy), fill=LUNA if acceso else CINEREA)
        # I crateri dopo, e solo dove c'e' luce: nella parte in ombra non si
        # vedono, e un puntino scuro sul nero-blu della luce cinerea sarebbe
        # un pixel sporco.
        for u, v, lato in CRATERI:
            x0, y0 = int(round(u * r)), int(round(v * r))
            for ddx in range(lato):
                for ddy in range(lato):
                    if (x0 + ddx, y0 + ddy) in accesi:
                        d.point((cx + x0 + ddx, cy + y0 + ddy), fill=CRATERE)

    # ---------------------------------------------------------- pezzi di testo

    def scrivi(self, d, x, y, testo, font, colore):
        d.text((x, y), testo, font=font, fill=colore)
        return x + d.textlength(testo, font=font)

    def freccia(self, d, x, y, lato, su, colore):
        """Un triangolo pieno: in su se cresce, in giu' se cala."""
        if su:
            punti = [(x, y + lato), (x + lato, y + lato), (x + lato / 2.0, y)]
        else:
            punti = [(x, y), (x + lato, y), (x + lato / 2.0, y + lato)]
        d.polygon(punti, fill=colore)

    # ---------------------------------------------------------- le schermate

    def schermata_luna(self, dati, adesso, fuso=None):
        """La Luna di stasera."""
        img, d = self.nuova()
        self.luna(d, 32, 32, self.DISCO, dati["frazione"], dati["crescente"])
        x = self.SINISTRA
        self.scrivi(d, x, 1, NOMI_FASI.get(dati["fase"], "LUNA"),
                    self.f_piccolo, SPENTO)
        percento = "%d%%" % int(round(dati["frazione"] * 100))
        fine = self.scrivi(d, x - 1, 10, percento, self.f_grande, LUNA)
        # Cresce o cala: la freccia e la parola, accanto al numero.
        lato = 9
        self.freccia(d, fine + 8, 20, lato, dati["crescente"],
                     SI if dati["crescente"] else AMBRA)
        self.scrivi(d, fine + 8 + lato + 5, 18,
                    "CRESCENTE" if dati["crescente"] else "CALANTE",
                    self.f_medio, SI if dati["crescente"] else AMBRA)
        # Sorge e tramonta. Senza posizione non si sa, e non si inventa.
        riga = 40
        if dati.get("sorge") or dati.get("tramonta"):
            x2 = self.scrivi(d, x, riga, "SORGE ", self.f_piccolo, SPENTO)
            x2 = self.scrivi(d, x2, riga, ora_breve(dati.get("sorge"), fuso),
                             self.f_piccolo, TESTO)
            x2 = self.scrivi(d, x2, riga, "  TRAMONTA ", self.f_piccolo, SPENTO)
            self.scrivi(d, x2, riga, ora_breve(dati.get("tramonta"), fuso),
                        self.f_piccolo, TESTO)
        piena = dati.get("prossima_piena")
        if piena is not None:
            locale = piena.astimezone(fuso)
            if (locale.date() - adesso.date()).days >= 1:
                x2 = self.scrivi(d, x, 52, "PIENA ", self.f_piccolo, SPENTO)
                self.scrivi(d, x2, 52, "%s %d" % (GIORNI_CORTI[locale.weekday()],
                                                  locale.day),
                            self.f_piccolo, AZZURRO)
        return img

    def schermata_nome(self, evento, luna, adesso, fuso=None):
        """Una luna con un nome: il giorno, il nome, e il perche'."""
        img, d = self.nuova()
        quando = evento["quando"]
        frazione = pianeti.fase_luna(quando.astimezone(timezone.utc))["frazione"]
        self.luna(d, 32, 32, self.DISCO, max(frazione, 0.98), True)
        x = self.SINISTRA
        self.scrivi(d, x, 1, quando_a_parole(quando, adesso), self.f_piccolo, AMBRA)
        riga1, riga2 = NOMI_LUNE.get(evento["nome"], ("LUNA", ""))
        self.scrivi(d, x, 11, riga1, self.f_medio, LUNA)
        self.scrivi(d, x, 25, riga2, self.f_medio, LUNA)
        spiega = self._spiegazione_luna(evento, luna, fuso)
        for i, riga in enumerate(spiega[:2]):
            self.scrivi(d, x, 42 + i * 11, riga, self.f_piccolo, SPENTO)
        return img

    def _spiegazione_luna(self, evento, luna, fuso):
        nome = evento["nome"]
        if nome == "raccolto":
            sorge = (luna or {}).get("sorge_quel_giorno")
            righe = ["LA PIENA PIU' VICINA"]
            if sorge is not None:
                righe.append("SORGE %s, COL TRAMONTO" % ora_breve(sorge, fuso))
            else:
                righe.append("ALL'EQUINOZIO D'AUTUNNO")
            return righe
        if nome == "superluna":
            km = evento.get("distanza_km")
            testo = ("A %s KM DA NOI" % format(int(round(km, -2)), ",").replace(",", ".")
                     if km else "LA PIU' VICINA")
            return ["LA PIENA PIU' GRANDE", testo]
        if nome == "blu":
            return ["LA SECONDA PIENA", "DI QUESTO MESE"]
        return []

    def schermata_stagione(self, evento, adesso, luce_minuti=None, fuso=None):
        """Equinozio o solstizio."""
        img, d = self.nuova()
        nome = evento["nome"]
        self._icona_stagione(d, 32, 32, nome)
        x = self.SINISTRA
        quando = evento["quando"]
        self.scrivi(d, x, 1, quando_a_parole(quando, adesso), self.f_piccolo, AMBRA)
        riga1, riga2 = NOMI_STAGIONI.get(nome, ("", ""))
        self.scrivi(d, x, 11, riga1, self.f_medio, TESTO)
        self.scrivi(d, x, 25, riga2, self.f_medio, TESTO)
        # "Verso le": il calcolo del Sole e' giusto entro una decina di
        # minuti, quindi l'ora si da' arrotondata e con il suo "circa". Il
        # minuto esatto sarebbe una precisione che non abbiamo.
        locale = quando.astimezone(fuso)
        ora = (locale + timedelta(minutes=30)).hour
        x2 = self.scrivi(d, x, 42, "VERSO LE ", self.f_piccolo, SPENTO)
        self.scrivi(d, x2, 42, "%d" % ora, self.f_piccolo, TESTO)
        if luce_minuti:
            x2 = self.scrivi(d, x, 53, "LUCE ", self.f_piccolo, SPENTO)
            self.scrivi(d, x2, 53, "%dH %02dM" % divmod(int(round(luce_minuti)), 60),
                        self.f_piccolo, TESTO)
            coda = {"solstizio_estate": "  IL PIU' LUNGO",
                    "solstizio_inverno": "  IL PIU' CORTO"}.get(nome)
            if coda:
                x3 = x + d.textlength("LUCE %dH %02dM" % divmod(int(round(luce_minuti)), 60),
                                      font=self.f_piccolo)
                self.scrivi(d, x3, 53, coda, self.f_piccolo, SPENTO)
        return img

    def _icona_stagione(self, d, cx, cy, nome):
        """Un Sole sopra un orizzonte, alto o basso secondo la stagione.

        All'equinozio a meta', d'estate alto, d'inverno appena sopra la linea.
        E' la stessa cosa che fa il Sole vero a mezzogiorno, ed e' l'unica
        cosa che si capisce a colpo d'occhio di una stagione.
        """
        altezza = {"solstizio_estate": 22, "solstizio_inverno": 5}.get(nome, 13)
        orizzonte = cy + 14
        d.line((cx - 26, orizzonte, cx + 26, orizzonte), fill=SPENTO, width=1)
        # Prima l'arco, poi il Sole: al contrario i puntini dell'arco finivano
        # sopra il disco, e il Sole sembrava bucato.
        for k in range(0, 181, 12):
            ang = math.radians(k)
            px = cx - math.cos(ang) * 24
            py = orizzonte - math.sin(ang) * altezza
            if py < orizzonte:
                d.point((px, py), fill=SPENTO)
        sy = orizzonte - altezza
        r = 7
        d.ellipse((cx - r, sy - r, cx + r, sy + r), fill=AMBRA)
        for k in range(8):
            ang = math.radians(k * 45)
            x1, y1 = cx + math.cos(ang) * (r + 3), sy + math.sin(ang) * (r + 3)
            x2, y2 = cx + math.cos(ang) * (r + 6), sy + math.sin(ang) * (r + 6)
            if y1 < orizzonte and y2 < orizzonte:
                d.line((x1, y1, x2, y2), fill=AMBRA)

    def schermata_sciame(self, evento, adesso, fuso=None):
        """Uno sciame di meteore: quando, quante, e se la Luna disturba."""
        img, d = self.nuova()
        self._icona_meteore(d)
        x = self.SINISTRA
        picco = datetime.combine(evento["picco"], datetime.min.time())
        if evento["fra_giorni"] == 0:
            quando = "STANOTTE IL PICCO"
        elif evento["fra_giorni"] == 1:
            quando = "DOMANI NOTTE IL PICCO"
        else:
            quando = "PICCO %s %d" % (GIORNI[picco.weekday()], picco.day)
        self.scrivi(d, x, 1, quando, self.f_piccolo, AMBRA)
        self.scrivi(d, x - 1, 11, evento["nome"], self.f_medio, TESTO)
        x2 = self.scrivi(d, x, 29, "FINO A ", self.f_piccolo, SPENTO)
        x2 = self.scrivi(d, x2, 29, "%d" % evento["zhr"], self.f_piccolo, TESTO)
        self.scrivi(d, x2, 29, " L'ORA", self.f_piccolo, SPENTO)
        frazione = int(round(evento.get("frazione", 0) * 100))
        luna = evento.get("luna")
        if luna == "tramonta":
            x2 = self.scrivi(d, x, 43, "LUNA %d%%, GIU' ALLE " % frazione,
                             self.f_piccolo, SPENTO)
            self.scrivi(d, x2, 43, ora_breve(evento.get("luna_tramonta"), fuso),
                        self.f_piccolo, TESTO)
            self.scrivi(d, x, 53, "POI CIELO BUIO", self.f_piccolo, SI)
        elif luna == "copre":
            self.scrivi(d, x, 43, "LUNA AL %d%%:" % frazione, self.f_piccolo, NO)
            self.scrivi(d, x, 53, "NE COPRE MOLTE", self.f_piccolo, NO)
        else:
            self.scrivi(d, x, 43, "LA LUNA NON DISTURBA", self.f_piccolo, SI)
            self.scrivi(d, x, 53, "MEGLIO DOPO MEZZANOTTE", self.f_piccolo, SPENTO)
        return img

    def _icona_meteore(self, d):
        """Tre scie in diagonale, con la coda che sfuma.

        Le sfumature sono intensita' intermedie, quelle che su questo pannello
        possono sfarfallare. Qui sono sei pixel per scia e si vedono per pochi
        secondi: il rischio e' accettabile, e senza coda una meteora e' un
        trattino qualsiasi.
        """
        for (x0, y0, lung) in ((14, 8, 26), (34, 20, 20), (8, 34, 16)):
            for k in range(lung):
                forza = 1.0 - k / float(lung)
                c = tuple(int(v * (0.25 + 0.75 * forza)) for v in TESTO)
                d.point((x0 + lung - k, y0 + k * 0.6), fill=c)
            d.ellipse((x0 + lung - 1, y0 - 1, x0 + lung + 1, y0 + 1), fill=TESTO)
        for (sx, sy) in ((50, 6), (56, 30), (22, 50), (46, 48), (6, 16), (60, 54)):
            d.point((sx, sy), fill=SPENTO)

    def schermata_serata(self, serata, adesso, fuso=None):
        """Vale la pena uscire a guardare, stasera?"""
        img, d = self.nuova()
        pianeta = serata.get("pianeta")
        self._icona_cielo(d, pianeta)
        x = self.SINISTRA
        self.scrivi(d, x, 1, "STANOTTE CIELO", self.f_piccolo, SI)
        self.scrivi(d, x, 11, "BUIO E SERENO", self.f_medio, TESTO)
        if pianeta:
            # Nome, direzione e altezza in gradi. Le parole "alto", "a meta'
            # cielo" erano piu' calde ma non ci stavano: con NORD-OVEST la
            # riga usciva dal pannello. I gradi sono piu' corti e dicono di
            # piu' -- chi alza il braccio teso sa che un pugno e' dieci gradi.
            nome = pianeti.NOMI.get(pianeta["nome"], ("", "", pianeta["nome"]))[2]
            colore = _colore(pianeta.get("colore")) or TESTO
            x2 = self.scrivi(d, x, 29, nome, self.f_piccolo, colore)
            self.scrivi(d, x2, 29, " %s %d\u00b0" % (pianeta["direzione"],
                                                   int(round(pianeta["gradi"]))),
                        self.f_piccolo, TESTO)
        dalle = ora_breve(serata.get("dalle"), fuso)
        alle = ora_breve(serata.get("alle"), fuso)
        x2 = self.scrivi(d, x, 43, "DALLE ", self.f_piccolo, SPENTO)
        x2 = self.scrivi(d, x2, 43, dalle, self.f_piccolo, TESTO)
        x2 = self.scrivi(d, x2, 43, " ALLE ", self.f_piccolo, SPENTO)
        self.scrivi(d, x2, 43, alle, self.f_piccolo, TESTO)
        if serata.get("nuvole") is not None:
            x2 = self.scrivi(d, x, 53, "NUVOLE ", self.f_piccolo, SPENTO)
            self.scrivi(d, x2, 53, "%d%%" % serata["nuvole"], self.f_piccolo, TESTO)
        return img

    def _icona_cielo(self, d, pianeta):
        """Qualche stella e, se c'e', il pianeta nel suo colore."""
        for (sx, sy) in ((8, 10), (22, 4), (40, 12), (56, 6), (14, 30), (52, 26),
                         (30, 22), (6, 48), (44, 40), (58, 52), (24, 44), (36, 56)):
            d.point((sx, sy), fill=SPENTO)
        for (sx, sy) in ((20, 16), (48, 18), (12, 40)):
            d.point((sx, sy), fill=TESTO)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                d.point((sx + dx, sy + dy), fill=SPENTO)
        if pianeta:
            c = _colore(pianeta.get("colore")) or TESTO
            d.ellipse((30, 30, 38, 38), fill=c)
        # L'orizzonte, perche' si capisca che e' un cielo e non un rumore.
        d.line((0, 62, 64, 62), fill=SPENTO)


def _colore(testo):
    try:
        t = str(testo).lstrip("#")
        return (int(t[0:2], 16), int(t[2:4], 16), int(t[4:6], 16))
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ servizio

PRIORITA = 53


def conf_predefinita():
    return {
        # Quanti secondi sta a schermo una schermata del cielo. Quindici: la
        # Luna si legge in tre, ma le altre hanno quattro righe da leggere.
        "durata": 15,
    }


class CieloSource(Source):
    """Il cielo di stasera. Non decide da solo quando mostrarsi: glielo dice
    il turno (vedi `sources/turni.py`), che lo alterna con il meteo.

    Priorita' 53: sopra OnAir (52), sotto il meteo (54). Le due sorgenti non
    si pestano i piedi -- e' il turno a dare lo spazio all'una o all'altra --
    e la regola della casa vuole solo che nessuno pareggi.
    """

    # Il servizio si chiama Moon: e' il nome che si legge nella pagina e in
    # Home Assistant. Dentro il codice i moduli restano `cielo`, perche' il
    # cielo e' quello che calcolano -- la Luna e' la voce principale.
    name = "moon"
    label = "Moon"
    priority = PRIORITA

    def __init__(self, cfg, width, height):
        super().__init__(cfg, width, height)
        self.tela = Tela(width, height)
        self._running = False
        self._lock = threading.Lock()
        self._image = None
        self._dirty = False
        self._fino_a = 0.0
        self._durata = 0.0
        self._vista = False
        self._modo = ""
        self._comparse = 0
        self._perse = 0
        # Quale schermata tocca stasera: le si fa girare, cosi' in una serata
        # con un evento si vede l'evento, poi la Luna, poi di nuovo l'evento.
        self._giro = 0
        self._giro_giorno = ""
        # I calcoli della serata, uno al giorno: le stagioni e le lune con un
        # nome si cercano in un anno intero, e sul Raspberry ci vuole un
        # secondo. Non si rifa' a ogni comparsa.
        self._cache = {}
        # Il meteo, per le nuvole della serata buona. Lo attacca il runtime.
        self.meteo = None

    # ------------------------------------------------------------ conf

    def conf(self):
        base = conf_predefinita()
        base.update(self.cfg.get("moon") or {})
        return base

    def posizione(self):
        import dmdconf
        try:
            return dmdconf.posizione(self.cfg)
        except Exception:                        # pragma: no cover
            return None

    # ------------------------------------------------------------ sorgente

    def start(self):
        self._running = True

    def stop(self):
        self._running = False
        self._fino_a = 0.0

    def active(self):
        return self._running and time.time() < self._fino_a

    def frame(self):
        with self._lock:
            if not self._dirty or self._image is None:
                return None
            self._dirty = False
            return self._image

    def in_onda(self):
        """Come il meteo: la comparsa conta quando qualcuno la vede."""
        if self._vista:
            return
        self._vista = True
        self._comparse += 1
        if self._durata:
            self._fino_a = time.time() + self._durata

    def vista(self):
        return self._vista

    def status(self, lang=None):
        if not self._running:
            return self.t("status.disabled", lang)
        adesso = datetime.now().astimezone()
        if not self.e_notte(adesso):
            return self.t("cielo.status.giorno", lang, shown=self._comparse)
        return self.t("cielo.status.notte", lang, shown=self._comparse,
                      lost=self._perse)

    # ------------------------------------------------------------ la notte

    def e_notte(self, adesso):
        """Fra il tramonto e l'alba. Senza posizione, fra le 19 e le 7."""
        dove = self.posizione()
        if dove is None:
            return adesso.hour >= 19 or adesso.hour < 7
        return pianeti.altezza_sole(adesso.astimezone(timezone.utc),
                                    dove[0], dove[1]) < -0.833

    # ------------------------------------------------------------ cosa dire

    def _giorno(self, adesso):
        """La chiave della serata: da mezzogiorno a mezzogiorno.

        Le due di notte appartengono alla sera prima, non al giorno dopo: chi
        guarda la Luna all'una sta ancora guardando la stessa serata.
        """
        base = adesso - timedelta(hours=12)
        return base.strftime("%Y-%m-%d")

    def _calcoli(self, adesso):
        chiave = self._giorno(adesso)
        if chiave in self._cache:
            return self._cache[chiave]
        dove = self.posizione()
        lat, lon = (dove if dove else (None, None))
        sera = adesso if adesso.hour >= 12 else adesso - timedelta(days=1)
        sera = sera.replace(hour=21, minute=0, second=0, microsecond=0)
        try:
            evento = cielo.evento_di_stasera(sera, lat, lon)
        except Exception as exc:                 # pragma: no cover
            print("[cielo] eventi non calcolati: %s" % exc)
            evento = None
        self._cache = {chiave: {"evento": evento}}
        return self._cache[chiave]

    def _nuvole(self):
        """Le nuvole ora per ora dal meteo, come {datetime UTC: percentuale}."""
        try:
            dati = self.meteo._meteo.dati() if self.meteo is not None else None
        except Exception:                        # pragma: no cover
            dati = None
        grezze = (dati or {}).get("nuvole") or {}
        if not grezze:
            return None
        fuori = {}
        for chiave, valore in grezze.items():
            try:
                t = datetime.strptime(chiave, "%Y-%m-%dT%H:00Z").replace(
                    tzinfo=timezone.utc)
            except ValueError:
                continue
            fuori[t] = valore
        return fuori

    def schermate(self, adesso):
        """Le schermate di stasera, nell'ordine in cui girano."""
        dove = self.posizione()
        lat, lon = (dove if dove else (None, None))
        fuori = []
        evento = self._calcoli(adesso)["evento"]
        if evento is not None:
            fuori.append(("evento", evento))
        if lat is not None:
            try:
                s = cielo.serata(adesso, lat, lon, self._nuvole())
            except Exception as exc:             # pragma: no cover
                print("[cielo] serata non calcolata: %s" % exc)
                s = None
            if s and s.get("buona"):
                fuori.append(("serata", s))
        fuori.append(("luna", None))
        return fuori

    def disegna(self, tipo, dati, adesso):
        dove = self.posizione()
        lat, lon = (dove if dove else (None, None))
        fuso = adesso.tzinfo
        if tipo == "luna":
            return self.tela.schermata_luna(cielo.luna_stasera(adesso, lat, lon),
                                            adesso, fuso)
        if tipo == "serata":
            return self.tela.schermata_serata(dati, adesso, fuso)
        if dati["tipo"] == "stagione":
            luce = None
            if lat is not None:
                giorno = dati["quando"].replace(hour=12, minute=0, second=0,
                                                microsecond=0)
                alba = cielo.eventi_sole(giorno - timedelta(days=1), lat, lon)[1]
                tramonto = cielo.eventi_sole(giorno, lat, lon)[0]
                if alba and tramonto:
                    luce = (tramonto - alba).total_seconds() / 60.0
            return self.tela.schermata_stagione(dati, adesso, luce, fuso)
        if dati["tipo"] == "luna_nome":
            extra = {}
            if lat is not None:
                mezzodi = dati["quando"].replace(hour=12, minute=0, second=0,
                                                 microsecond=0)
                extra["sorge_quel_giorno"] = cielo.sorge_luna(
                    mezzodi.astimezone(timezone.utc), lat, lon, ore=18)
            return self.tela.schermata_nome(dati, extra, adesso, fuso)
        return self.tela.schermata_sciame(dati, adesso, fuso)

    # ------------------------------------------------------------ il turno

    def apri_turno(self, adesso=None):
        """Mostra la prossima schermata di stasera. Falso se non e' il caso."""
        if not self._running:
            return False
        adesso = adesso or datetime.now().astimezone()
        if not self.e_notte(adesso):
            return False
        giorno = self._giorno(adesso)
        if giorno != self._giro_giorno:
            self._giro_giorno = giorno
            self._giro = 0
        elenco = self.schermate(adesso)
        tipo, dati = elenco[self._giro % len(elenco)]
        self._giro += 1
        try:
            immagine = self.disegna(tipo, dati, adesso)
        except Exception as exc:
            # Stessa regola del meteo e dei satelliti: un disegno che fallisce
            # molla il pannello invece di lasciarci sopra l'ultimo fotogramma.
            print("[cielo] disegno fallito: %s" % exc)
            self._fino_a = 0.0
            return False
        return self.mostra(immagine, tipo)

    def mostra(self, immagine, modo="luna", secondi=None):
        with self._lock:
            self._image = immagine
            self._dirty = True
        if self._durata and not self._vista:
            self._perse += 1
        self._modo = modo
        self._durata = float(max(4, secondi or int(self.conf()["durata"] or 15)))
        self._vista = False
        self._fino_a = time.time() + self._durata
        return True

    def mostra_adesso(self, tipo="luna"):
        """Il pulsante della pagina: la schermata subito, anche di giorno."""
        adesso = datetime.now().astimezone()
        if tipo == "luna":
            dati = None
        else:
            elenco = [d for t, d in self.schermate(adesso) if t == tipo]
            if not elenco:
                return False
            dati = elenco[0]
        return self.mostra(self.disegna(tipo, dati, adesso), tipo)
