"""Orologio.

Sorgente a priorita' piu' bassa: riempie il display quando nessun altro
servizio ha qualcosa da mostrare. Colori di ora e data indipendenti,
formato 12 o 24 ore, nomi dei giorni in italiano, francese o inglese.
"""

import colorsys
import datetime
import random
import time

from PIL import Image, ImageDraw, ImageFont

from .base import Source

# Il World Time e' facoltativo: senza il database dei fusi il modulo si
# importa lo stesso e la banda non compare. L'orologio non deve mai fermarsi
# per una cosa che sta sotto le cifre.
try:
    import fusi
except Exception:                                    # pragma: no cover
    fusi = None

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

# Indice 0 = lunedi', come time.struct_time.tm_wday
DAY_NAMES = {
    "it": ["LUN", "MAR", "MER", "GIO", "VEN", "SAB", "DOM"],
    "en": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
    "fr": ["LUN", "MAR", "MER", "JEU", "VEN", "SAM", "DIM"],
}

LANGUAGES = [("it", "Italiano"), ("fr", "Français"), ("en", "English")]


def parse_color(value, fallback=(255, 140, 26)):
    """Converte '#rrggbb' in una tupla RGB."""
    try:
        text = str(value).strip().lstrip("#")
        if len(text) == 3:
            text = "".join(ch * 2 for ch in text)
        if len(text) != 6:
            return fallback
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    except (TypeError, ValueError):
        return fallback


# ------------------------------------------------------ il colore casuale
#
# «Ad ogni cambio d'ora il colore dell'orario deve cambiare in modo casuale.
# I valori RGB non devono mai essere inferiori a 25~50, per evitare colori
# prossimi al nero.»
#
# Tre scelte, e ognuna viene da un modo in cui la versione ingenua sbaglia.
#
# **Si sceglie la tinta, non i tre canali.** Tre numeri a caso fra 50 e 255
# rispettano il limite e danno quasi sempre un grigio: la media di tre valori
# indipendenti sta vicino a meta' scala, e (140, 160, 150) e' un colore solo
# sulla carta. Qui la tinta e' libera, la luminosita' e' sempre piena -- un
# canale a 255, quindi mai scuro -- e la saturazione sta fra 0.55 e 0.80.
# Da quel tetto viene il limite chiesto: il canale piu' basso vale
# 255 * (1 - 0.80) = 51, cioe' **sopra 50 per costruzione**, non per un
# controllo fatto dopo.
#
# **Il colore dipende dall'ora, non da un dado lanciato allo scoccare.** E'
# lo stesso per tutta l'ora, e un riavvio a meta' non lo cambia: il seme e'
# il numero dell'ora nel calendario. Un orologio che cambia colore perche' e'
# ripartito il servizio sembra un orologio guasto.
#
# **Due ore di fila non si assomigliano mai.** Un dado vero ogni tanto
# ripete quasi la stessa tinta, e allora il cambio non si vede: l'ora e'
# cambiata e l'orologio no. Qui ogni ora avanza la tinta dell'angolo aureo --
# 137,5 gradi, il passo che distribuisce i punti su un cerchio senza mai
# farli ricadere vicini -- con una deviazione a caso di venti gradi. Fra due
# ore consecutive la distanza sta sempre fra 97 e 178 gradi, anche a
# cavallo della mezzanotte, e l'occhio ci vede lo stesso un'estrazione.
ANGOLO_AUREO = 137.50776
DEVIAZIONE = 20.0
SATURAZIONE = (0.55, 0.80)
MINIMO_CANALE = 50


def indice_ora(momento):
    """Il numero di quest'ora nel calendario: cresce di uno ogni ora."""
    giorno = datetime.date(momento.tm_year, momento.tm_mon, momento.tm_mday)
    return giorno.toordinal() * 24 + momento.tm_hour


def tinta_ora(indice):
    """La tinta di un'ora, in gradi."""
    dado = random.Random(indice)
    return (indice * ANGOLO_AUREO + dado.uniform(-DEVIAZIONE, DEVIAZIONE)) % 360.0


def colore_casuale(momento=None):
    """Il colore dell'ora `momento` (struct_time), come tupla RGB."""
    momento = momento or time.localtime()
    indice = indice_ora(momento)
    dado = random.Random(indice * 7919 + 1)
    saturazione = dado.uniform(*SATURAZIONE)
    r, g, b = colorsys.hsv_to_rgb(tinta_ora(indice) / 360.0, saturazione, 1.0)
    # Il tetto della saturazione basta gia' a tenere ogni canale sopra il
    # minimo. Il controllo resta lo stesso: se un giorno qualcuno allarga
    # l'intervallo, il limite chiesto non deve dipendere dal ricordarsene.
    return tuple(max(MINIMO_CANALE + 1, min(255, int(round(c * 255))))
                 for c in (r, g, b))


def colore_esadecimale(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


def _load_font(size):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def voce_mondo():
    return {"enabled": False, "etichetta": "", "fuso": ""}


def normalizza_mondo(voci):
    """Sempre `fusi.QUANTE` voci, comunque siano scritte.

    L'etichetta e' la parola che finisce sul pannello, ed e' **sua**: «NY» sta
    in meno spazio di «New York», e con tre citta' affiancate lo spazio e'
    l'unica cosa che conta. Se manca, si ripiega sull'ultimo pezzo del fuso --
    `America/New_York` diventa «New York» -- che e' meglio di una riga muta.
    """
    quante = fusi.QUANTE if fusi is not None else 5
    grezze = voci if isinstance(voci, (list, tuple)) else []
    fuori = []
    for indice in range(quante):
        voce = grezze[indice] if indice < len(grezze) else None
        base = voce_mondo()
        if isinstance(voce, dict):
            base["enabled"] = bool(voce.get("enabled"))
            base["fuso"] = str(voce.get("fuso") or "").strip()
            base["etichetta"] = str(voce.get("etichetta") or "").strip()[:14]
            if not base["etichetta"] and base["fuso"]:
                base["etichetta"] = base["fuso"].rsplit("/", 1)[-1] \
                    .replace("_", " ")
        fuori.append(base)
    return fuori


class ClockSource(Source):
    name = "clock"
    label = "Clock"
    priority = 10

    def __init__(self, cfg, width, height):
        super().__init__(cfg, width, height)
        self._running = False
        self._signature = None
        # Quanto resta del timer, come frazione da 1 a 0. Lo attacca il
        # runtime: vedi `_barra_timer`.
        self.timer = None
        # Se il servizio OnAir e' in diretta. Lo attacca il runtime, con la
        # stessa regola del timer: vedi `_tratto_onair`.
        self.onair = None
        # Se c'e' una versione nuova da installare. Stessa regola: il runtime
        # attacca qui una funzione, l'orologio non sa che esista GitHub.
        self.aggiornamento = None
        self._font = _load_font(max(12, int(height * 0.60)))
        self._font_small = _load_font(max(8, int(height * 0.20)))
        # Font della colonna dei rifiuti, dal piu' grande al piu' piccolo. Si
        # sceglie il primo in cui il nome piu' lungo sta nello spazio libero:
        # i nomi li scrive l'utente, e "Indifferenziato" non e' "Carta".
        self._font_rifiuti = [_load_font(max(6, int(height * f)))
                              for f in (0.170, 0.155, 0.140, 0.125, 0.110)]

    def start(self):
        self._running = True
        self._signature = None

    def stop(self):
        self._running = False

    def active(self):
        return self._running

    def status(self, lang=None):
        if not self._running:
            return self.t("status.disabled", lang)
        clock = self.cfg["clock"]
        return self.t("status.clock.active", lang,
                      format="24h" if clock["format_24h"] else "12h",
                      language=clock["language"].upper())

    def invalidate(self):
        """Forza il ridisegno, ad esempio dopo un cambio di impostazioni."""
        self._signature = None

    # ------------------------------------------------------------- rifiuti

    def _colonna(self):
        """Le voci da ricordare adesso. Mai un'eccezione fino al pannello.

        L'orologio e' la sorgente che si vede quasi sempre: un errore nel
        calendario dei rifiuti — un file scritto male, una data assurda — non
        deve portarsi via anche l'ora.
        """
        try:
            import rifiuti
            return rifiuti.attive(self.cfg)
        except Exception as exc:
            print("[clock] calendario rifiuti non leggibile: %s" % exc)
            return []

    # Il semaforo delle scadenze sta a destra dell'ora, sotto la data: sono i
    # 68 pixel che avanzano da quel lato, come i 68 di sinistra sono della
    # colonna dei rifiuti, e i 47 che restano sotto la data.
    #
    # Le lampade sono meta' di com'erano: cerchi da 7 con 2 di distacco, 25
    # pixel in tutto invece di 47. Avanzano 22 pixel, quindi la colonna non
    # parte piu' dal bordo alto della banda ma si centra dentro: SEM_BANDA e'
    # lo spazio disponibile, SEM_ALTEZZA quello che il semaforo occupa
    # davvero, e la differenza la fa il margine.
    SEM_RAGGIO = 3
    SEM_PASSO = 9
    SEM_CIMA = 17
    SEM_BANDA = 47

    @property
    def SEM_ALTEZZA(self):
        return 2 * self.SEM_RAGGIO + 2 * self.SEM_PASSO + 1

    def _scadenze_attive(self):
        """L'interruttore di pagina Servizi vale anche per il semaforo.

        Il semaforo lo disegna l'orologio, non la sorgente Scadenze: senza
        questo controllo spegnere il servizio farebbe sparire l'avviso ma
        lascerebbe le lampade accese, cioe' un interruttore che obbedisce a
        meta'.
        """
        return bool(self.cfg.get("services", {}).get("scadenze", False))

    def _semaforo(self):
        """Lo stato del semaforo, o 'spento' se qualcosa non va.

        Le scadenze stanno in un CSV che l'utente puo' modificare a mano: un
        file scritto male non deve portarsi via l'orologio.
        """
        if not self._scadenze_attive():
            return "spento"
        try:
            import scadenze
            return scadenze.semaforo(self.cfg)
        except Exception as exc:
            print("[clock] scadenze non leggibili: %s" % exc)
            return "spento"

    def _disegna_semaforo(self, draw, stato, sinistra, alto, acceso=True):
        """Tre lampade in colonna, come un semaforo vero: solo una accesa.

        Non un cerchio solo che cambia colore: con tre lampade la posizione
        dice gia' l'urgenza, e da lontano si legge prima il *dove* del *che
        colore* — che per chi non distingue bene i colori e' l'unica cosa che
        funziona.
        """
        import scadenze
        centro_x = sinistra + 34
        for indice, quale in enumerate((scadenze.ROSSO, scadenze.GIALLO,
                                        scadenze.VERDE)):
            centro_y = alto + self.SEM_RAGGIO + indice * self.SEM_PASSO
            colpita = (quale == stato
                       or (quale == scadenze.ROSSO and stato == scadenze.SCADUTA))
            if colpita and acceso:
                colore = scadenze.COLORI[quale]
                riempi = colore
            else:
                # Le lampade spente restano disegnate, fioche: un semaforo con
                # una lampada sola sembra un puntino, con tre si capisce che
                # cos'e' anche quando e' verde.
                riempi = None
                colore = tuple(max(6, c // 9) for c in scadenze.COLORI[quale])
            draw.ellipse([centro_x - self.SEM_RAGGIO, centro_y - self.SEM_RAGGIO,
                          centro_x + self.SEM_RAGGIO, centro_y + self.SEM_RAGGIO],
                         fill=riempi, outline=colore)

    def _disegna_colonna(self, draw, voci, limite, fondo=None):
        """Disegna le voci impilate a sinistra, dentro `limite` pixel.

        Impilate e non affiancate: i nomi hanno lunghezze diverse e in
        orizzontale si leggerebbero come una parola sola. In verticale ognuna
        ha la sua riga e il suo colore, che e' l'informazione vera — a colpo
        d'occhio si riconosce il colore prima ancora della parola.

        Lo spazio disponibile e' quello che l'ora lascia libero, e non e'
        negoziabile: se i nomi non ci stanno si rimpicciolisce il testo, e
        se non basta si taglia. Meglio "INDIFFERENZ" leggibile che una parola
        intera sopra le cifre dell'ora.
        """
        if not voci or limite < 12:
            return
        testi = [v["nome"].upper() for v in voci[:5]]
        larghezza_utile = limite - 2

        font = self._font_rifiuti[-1]
        for candidato in self._font_rifiuti:
            if all(draw.textlength(t, font=candidato) <= larghezza_utile
                   for t in testi):
                font = candidato
                break

        # In verticale la colonna arriva fin dove le si lascia arrivare. Di
        # norma e' tutto il pannello; con il World Time acceso e' la banda in
        # fondo a fermarla, e le voci si stringono per fare posto. Con quattro
        # raccolte insieme, senza questo, l'ultima finiva scritta sopra gli
        # orari del mondo -- un difetto che si vede solo con quattro, e che
        # infatti e' arrivato da chi ne ha quattro.
        alto_utile = self.height if fondo is None else max(24, fondo)
        passo = max(7, alto_utile // max(len(testi), 4))
        box = draw.textbbox((0, 0), "AG", font=font)
        alto = box[3] - box[1]
        for indice, (testo, voce) in enumerate(zip(testi, voci)):
            while testo and draw.textlength(testo, font=font) > larghezza_utile:
                testo = testo[:-1]
            y = indice * passo + max(0, (passo - alto) // 2)
            draw.text((2, y), testo, font=font,
                      fill=parse_color(voce.get("colore"), (255, 255, 255)))

    def frame(self):
        if not self._running:
            return None

        clock = self.cfg["clock"]
        now = time.localtime()

        if clock["format_24h"]:
            text = time.strftime("%H:%M", now)
            meridiem = ""
        else:
            hour = now.tm_hour % 12 or 12
            text = "%d:%02d" % (hour, now.tm_min)
            meridiem = "AM" if now.tm_hour < 12 else "PM"

        second_even = (now.tm_sec % 2 == 0)
        if clock["blink_colon"] and not second_even:
            shown = text.replace(":", " ")
        else:
            shown = text

        days = DAY_NAMES.get(clock["language"], DAY_NAMES["it"])
        date = "%s %02d/%02d" % (days[now.tm_wday], now.tm_mday, now.tm_mon)

        colonna = self._colonna()
        stato_sem = self._semaforo()
        # Una scadenza passata lampeggia. La fase e' quella del secondo pari,
        # la stessa dei due punti dell'ora: due cose che lampeggiano insieme
        # sembrano un battito, due che lampeggiano sfasate sembrano un guasto.
        import scadenze as _sc
        sem_acceso = second_even or stato_sem != _sc.SCADUTA

        # La barra del timer, in fondo al pannello. Si calcola prima della
        # firma e ci entra dentro: e' larga un pixel in meno ogni tanto, e se
        # restasse fuori dalla firma il pannello continuerebbe a mostrare
        # quella del momento in cui e' cambiato qualcos'altro.
        barra = self._barra_timer()
        diretta = self._tratto_onair()
        mondo = self._mondo(now)
        novita = self._segno_aggiornamento()
        time_color = self.colore_ora(now)

        # Ridisegna solo quando cambia qualcosa di visibile. Il colore entra
        # come **valore calcolato**, non come impostazione: con il colore
        # casuale l'impostazione resta ferma e il colore cambia ogni ora.
        signature = (shown, date if clock["show_date"] else "", meridiem,
                     time_color, clock["date_color"],
                     tuple((v["nome"], v["colore"]) for v in colonna),
                     stato_sem, sem_acceso, barra, diretta,
                     tuple(mondo), novita, self._offset())
        if signature == self._signature:
            return None
        self._signature = signature

        date_color = parse_color(clock["date_color"], (0, 160, 208))

        image = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        draw = ImageDraw.Draw(image)

        box = draw.textbbox((0, 0), shown, font=self._font)
        x = (self.width - (box[2] - box[0])) // 2 - box[0]
        y = (self.height - (box[3] - box[1])) // 2 - box[1]
        # Con il World Time acceso le cifre salgono di qualche pixel, per non
        # restare appoggiate alla banda degli orari del mondo. Poi si somma
        # l'offset scelto dall'utente, che vale sempre: vedi `_offset()`.
        if mondo:
            y -= self.MONDO_ALZATA
        y += self._offset()
        # Un limite fisico, non un ripensamento sul gusto di chi regola: le
        # cifre non devono finire dentro la banda degli orari del mondo ne'
        # sotto il bordo. Oltre quel punto il cursore smette di muovere, e la
        # pagina lo dice invece di lasciar credere che sia rotto.
        y = min(y, self._fondo_cifre(mondo) - box[3])
        y = max(y, -box[1])
        draw.text((x, y), shown, font=self._font, fill=time_color)
        ora_destra = x + box[2]
        ora_sotto = y + box[3]

        # L'ora resta al centro, sempre: la colonna vive nello spazio che
        # avanza alla sua sinistra e si adatta a quello. Un orologio che si
        # sposta quando arriva un promemoria e torna indietro quando se ne va
        # e' un orologio che si muove per conto suo.
        self._disegna_colonna(draw, colonna, limite=x - 3,
                              fondo=(self.MONDO_CIMA - 1) if mondo else None)

        if clock["show_date"]:
            box = draw.textbbox((0, 0), date, font=self._font_small)
            draw.text((self.width - (box[2] - box[0]) - 3, 2), date,
                      font=self._font_small, fill=date_color)

        # Il semaforo occupa quello che avanza a destra dell'ora, sotto la
        # data: dal bordo destro dell'ora al bordo del pannello.
        mostra_sem = stato_sem != "spento" or (
            self._scadenze_attive()
            and self.cfg.get("scadenze", {}).get("semaforo_sempre"))
        if mostra_sem:
            cima = self.SEM_CIMA + (self.SEM_BANDA - self.SEM_ALTEZZA) // 2
            self._disegna_semaforo(draw, stato_sem, ora_destra + 3, cima,
                                   acceso=sem_acceso)

        if meridiem:
            # Attaccato alle cifre, non nell'angolo in alto a sinistra: li'
            # ci va la colonna dei rifiuti, e in formato 12 ore "AM" finiva
            # scritto sopra la prima voce. Accanto all'ora, oltretutto, e'
            # dove un orologio se lo aspetta.
            riquadro = draw.textbbox((0, 0), meridiem, font=self._font_small)
            alto = riquadro[3] - riquadro[1]
            draw.text((min(ora_destra + 3, self.width - (riquadro[2] - riquadro[0]) - 1),
                       max(0, ora_sotto - alto - riquadro[1])),
                      meridiem, font=self._font_small, fill=date_color)

        if barra:
            draw.rectangle((0, self.height - self.TIMER_SPESSORE,
                            barra - 1, self.height - 1),
                           fill=parse_color(
                               (self.cfg.get("sveglia") or {}).get("colore"),
                               (255, 59, 48)))

        if mondo:
            self._disegna_mondo(draw, mondo)

        if diretta:
            # In cima e corto, dalla parte opposta della barra del timer, che
            # sta in fondo ed e' lunga: cosi' i due segnali non si possono
            # confondere nemmeno con la coda dell'occhio.
            meta = (self.width - self.ONAIR_LARGO) // 2
            draw.rectangle((meta, 0, meta + self.ONAIR_LARGO - 1,
                            self.ONAIR_ALTO - 1),
                           fill=parse_color(
                               (self.cfg.get("onair") or {}).get("colore_sfondo"),
                               (0xC0, 0, 0)))

        if novita:
            draw.rectangle((self.width - self.AGGIORNA_LARGO, 0,
                            self.width - 1, self.AGGIORNA_ALTO - 1),
                           fill=self.AGGIORNA_COLORE)

        return image

    # ------------------------------------------------------------ il timer

    TIMER_SPESSORE = 2

    def _barra_timer(self):
        """Quanti pixel di barra accendere in fondo, o 0 se non serve.

        Nasce da una cosa vista usando il DMD: *quando il timer è avviato non
        mi accorgo che c'è*. Il timer si mette da una pagina web, ma la pasta
        si guarda in cucina, e in cucina l'unica cosa che si guarda è il
        pannello -- che del timer non sapeva niente.

        Una riga fissa direbbe soltanto «c'è un timer». Una riga che si
        accorcia costa gli stessi due pixel e dice anche **quanto manca**,
        senza scrivere numeri sopra un orologio che di numeri ne ha già.

        Il gancio lo attacca il runtime: l'orologio non sa che esista una
        sveglia, sa solo che qualcuno ogni tanto gli dice una frazione.
        """
        if self.timer is None:
            return 0
        try:
            quota = self.timer()
        except Exception:                            # pragma: no cover
            return 0
        if not quota:
            # None (nessun timer) o 0.0 (appena scaduto: da li' in poi parla
            # la sveglia, che si prende il pannello tutto).
            return 0
        return max(1, int(round(quota * self.width)))

    # ----------------------------------------------------------- world time

    # Di quanto salgono le cifre quando la banda c'e'. Cinque: sopra le cifre
    # restano sedici righe libere, quindi si puo' -- e sotto sono i pixel che
    # portano il carattere da otto a dieci.
    # Quanto salgono le cifre quando il World Time e' acceso.
    #
    # Era 5, ed e' sceso a 3 guardando il pannello vero. A 5 le cifre e la
    # data condividevano **tre righe**: i due blocchi si ritrovavano
    # affiancati con cinque pixel in mezzo, e a tre metri il minuto e il
    # giorno della settimana per un istante si leggono come una cosa sola.
    # A 3 la riga in comune e' una, e i due blocchi tornano separati.
    #
    # Il prezzo sono due righe di respiro in meno sotto le cifre, otto invece
    # di dieci: uno squilibrio che non si nota, in cambio di una quasi
    # collisione che si notava. Chi la pensa diversamente ha il cursore.
    MONDO_ALZATA = 3

    # Dove comincia la banda e quanto e' alta. Da 51 a 61: sopra c'e' la
    # lampada piu' bassa del semaforo (finisce a 52, ma le cifre alzate le
    # lasciano spazio), sotto la barra del timer, che parte a 62.
    MONDO_CIMA = 51
    MONDO_CORPO = 10

    # Lo spazio minimo fra una citta' e l'altra, e quello fra un nome e la sua
    # ora.
    #
    # Erano 8 e uno spazio intero, 6 pixel, e con tre citta' bastavano **a
    # volte**. «SEATTLE TOKYO NEW YORK» stava in 245 pixel su 254 finche'
    # tutte e tre erano nello stesso giorno di Roma; ogni citta' su un altro
    # giorno aggiunge il suo `+` o `-`, sei pixel, e con due segni si arrivava
    # a 257. Di notte Seattle e New York sono ancora a ieri: la banda passava
    # da tre citta' insieme a due che si alternano, e al mattino tornava a
    # tre. Un orologio che cambia impaginazione a seconda dell'ora non e'
    # rotto, ma sembra.
    #
    # Adesso il nome e l'ora stanno a 3 pixel -- sono gia' di due colori
    # diversi, lo spazio pieno era una ridondanza -- e fra una citta' e
    # l'altra ne restano almeno 6, dove il cambio dal grigio dell'ora al blu
    # del nome fa il resto. Nove pixel guadagnati con i tre accosti, quattro
    # con i due stacchi: lo stesso terzetto con tre segni occupa 250.
    MONDO_STACCO = 6
    MONDO_ACCOSTO = 3
    # Il posto del segno del giorno si tiene **sempre**, anche quando il segno
    # non c'e'. Il conto di quante citta' entrano deve dare lo stesso numero
    # a mezzogiorno e a mezzanotte: e' la meta' della correzione, l'altra
    # meta' e' lo spazio guadagnato qui sopra.
    MONDO_SEGNO = "+"

    # Ogni quanti secondi cambia il gruppo, quando le localita' sono piu' di
    # quante ne stanno. Otto: il tempo di leggerle senza che chi passa debba
    # aspettare.
    MONDO_GIRO = 8

    def _conf_mondo(self):
        return (self.cfg.get("clock") or {}).get("world") or {}

    def _mondo(self, adesso=None):
        """Le righe del World Time da mostrare adesso. Lista vuota se spento.

        Ogni voce e' (etichetta, ora, segno), dove il segno e' `+` o `-`
        quando in quella citta' e' un altro giorno. E' l'informazione che
        l'ora da sola nasconde: a Roma le 05:54 sono l'una e cinquantaquattro
        di New York, ma di **ieri**, ed e' esattamente quello che uno vuole
        sapere guardando un orologio del mondo.

        La rotazione conta i secondi dell'ora corrente e non un contatore
        interno, cosi' due pannelli accesi nella stessa stanza girano insieme
        invece che sfasati, e un riavvio non fa ripartire il giro da capo.
        """
        if fusi is None:
            return []
        conf = self._conf_mondo()
        if not conf.get("enabled"):
            return []
        voci = [v for v in normalizza_mondo(conf.get("voci"))
                if v["enabled"] and v["fuso"]]
        if not voci:
            return []
        ore24 = bool((self.cfg.get("clock") or {}).get("format_24h", True))

        pronte = []
        for voce in voci:
            ora, scarto = fusi.orario(voce["fuso"], ore24)
            if not ora:
                # Un fuso che non esiste piu' -- o un database dei fusi
                # rimasto indietro -- non deve far sparire le altre citta'.
                continue
            pronte.append((voce["etichetta"], ora,
                           "+" if scarto > 0 else ("-" if scarto < 0 else "")))
        if not pronte:
            return []

        quante = self._quante_ci_stanno(pronte)
        if quante >= len(pronte):
            return pronte
        gruppi = (len(pronte) + quante - 1) // quante
        secondi = (adesso.tm_hour * 3600 + adesso.tm_min * 60 + adesso.tm_sec
                   if adesso else int(time.time()))
        quale = (secondi // self.MONDO_GIRO) % gruppi
        fetta = pronte[quale * quante:(quale + 1) * quante]
        # L'ultimo gruppo puo' essere spaiato: si completa dall'inizio invece
        # di lasciare mezza banda vuota.
        if len(fetta) < quante:
            fetta += pronte[:quante - len(fetta)]
        return fetta

    def _font_mondo(self):
        if not hasattr(self, "_mondo_font"):
            self._mondo_font = _load_font(self.MONDO_CORPO)
        return self._mondo_font

    def _quante_ci_stanno(self, pronte):
        """Quante voci entrano in una banda larga quanto il pannello.

        Si misurano le **piu' larghe**, non le prime. La differenza si vede
        solo con la rotazione: «NEW YORK TOKYO LONDRA» stanno in tre, ma
        «SYDNEY LOS ANGELES NEW YORK» no, e il numero deve valere per tutti i
        gruppi -- altrimenti un giro su due l'ultima citta' esce dal bordo.
        Contare le prime tre dava esattamente quel difetto.
        """
        misura = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        font = self._font_mondo()
        # Il segno si conta sempre, che ci sia o no: vedi MONDO_SEGNO.
        larghe = sorted((misura.textlength(e, font=font) + self.MONDO_ACCOSTO
                         + misura.textlength(o + self.MONDO_SEGNO, font=font)
                         for e, o, _s in pronte), reverse=True)
        quante, usati = 0, 0.0
        for largo in larghe:
            aggiunta = largo + (self.MONDO_STACCO if quante else 0)
            if usati + aggiunta > self.width - 2:
                break
            usati += aggiunta
            quante += 1
        # Almeno una: se una sola etichetta fosse piu' larga del pannello, la
        # banda resterebbe vuota per sempre invece di mostrare qualcosa.
        return max(1, quante)

    def _disegna_mondo(self, draw, voci):
        """La banda in fondo: nome nel colore della data, ora piu' chiara.

        Due colori e non uno: il nome e l'ora sono due informazioni diverse e
        con tre citta' affiancate, tutte dello stesso colore, la riga si
        legge come una frase sola.
        """
        font = self._font_mondo()
        conf = self._conf_mondo()
        colore_nome = parse_color(conf.get("colore_nome"),
                                  parse_color(self.cfg["clock"]["date_color"],
                                              (0, 160, 208)))
        colore_ora = parse_color(conf.get("colore_ora"), (200, 200, 200))

        pezzi = []
        for etichetta, ora, segno in voci:
            testo_ora = "%s%s" % (ora, segno)
            pezzi.append((etichetta, testo_ora,
                          draw.textlength(etichetta, font=font) + self.MONDO_ACCOSTO,
                          draw.textlength(testo_ora, font=font)))
        totale = sum(n + o for _e, _o, n, o in pezzi)
        if len(pezzi) > 1:
            stacco = max(self.MONDO_STACCO,
                         (self.width - 2 - totale) / (len(pezzi) - 1))
        else:
            stacco = 0
        # Una voce sola si centra; piu' voci si distribuiscono da bordo a
        # bordo, che e' l'unico modo perche' non sembrino ammucchiate.
        x = 1.0 if len(pezzi) > 1 else (self.width - totale) / 2
        for nome, ora, largo_nome, largo_ora in pezzi:
            draw.text((x, self.MONDO_CIMA), nome, font=font, fill=colore_nome)
            draw.text((x + largo_nome, self.MONDO_CIMA), ora, font=font,
                      fill=colore_ora)
            x += largo_nome + largo_ora + stacco

    # ------------------------------------------------------------ la diretta

    # Il trattino di OnAir: corto e in cima. Trentadue pixel su duecentocinquanta
    # sono un ottavo della larghezza -- abbastanza da vedersi dall'altra stanza,
    # poco da non sembrare un guasto della prima riga.
    ONAIR_LARGO = 32
    ONAIR_ALTO = 2

    def _tratto_onair(self):
        """Vero se va acceso il trattino della diretta.

        Stessa forma del timer, e per la stessa ragione: l'orologio non sa che
        esista un servizio OnAir ne' che esista una porta. Sa che qualcuno ogni
        tanto gli dice si' o no, e che quando e' si' accende due pixel.

        Il segnale serve perche' la scritta ON AIR passa e se ne va: per tutto
        il resto del tempo il pannello mostra l'orologio, e un orologio identico
        a quello di sempre non dice che si sta registrando.
        """
        if self.onair is None:
            return False
        try:
            return bool(self.onair())
        except Exception:                            # pragma: no cover
            return False

    # ------------------------------------------------- il colore dell'ora

    def colore_ora(self, momento=None):
        """Il colore delle cifre adesso: quello scelto, o quello di quest'ora.

        Pubblico perche' lo chiede anche la pagina web, per mostrare il colore
        dell'ora in corso accanto all'interruttore: dire «casuale» senza far
        vedere quale e' toccato adesso lascerebbe il dubbio che non funzioni.
        """
        clock = self.cfg.get("clock") or {}
        if clock.get("colore_casuale"):
            return colore_casuale(momento)
        return parse_color(clock.get("time_color"))

    # ------------------------------------------------ l'offset verticale

    # Di quanto si puo' spostare l'ora, in pixel, in su o in giu'. Dodici
    # righe su sessantaquattro sono gia' tanto: oltre, con il World Time
    # acceso, il limite fisico arriva prima del cursore e il comando
    # smetterebbe di rispondere per meta' della sua corsa.
    OFFSET_MASSIMO = 12

    def _offset(self):
        """Lo spostamento verticale scelto dall'utente. Positivo = piu' giu'.

        Vale **sempre**, non solo con il World Time acceso: un comando che
        non fa niente nel caso piu' comune e' un comando che fa aprire una
        pagina di aiuto. Con il World Time si somma all'alzata automatica,
        cosi' lo zero resta la posizione buona di serie e il cursore e' uno
        scostamento da quella, non un numero assoluto da indovinare.
        """
        try:
            valore = int((self.cfg.get("clock") or {}).get("offset_v", 0) or 0)
        except (TypeError, ValueError):
            return 0
        return max(-self.OFFSET_MASSIMO, min(self.OFFSET_MASSIMO, valore))

    def _fondo_cifre(self, mondo):
        """L'ultima riga su cui le cifre possono arrivare."""
        if mondo:
            return self.MONDO_CIMA - 1
        return self.height - 1

    # -------------------------------------------------- la versione nuova

    # Il segno dell'aggiornamento: quattro pixel per due, nell'angolo in alto
    # a destra. E' il posto piu' vuoto del pannello -- la data comincia alla
    # riga 2, il trattino della diretta sta al centro, la colonna dei rifiuti
    # sta a sinistra -- e soprattutto e' un posto dove non c'e' mai niente,
    # quindi quando qualcosa compare si nota anche senza guardarlo.
    #
    # Otto pixel su sedicimila. Non deve chiamare: deve essere li' la prossima
    # volta che passi davanti al pannello. Chi vuole sapere l'ora la legge lo
    # stesso, e chi si chiede cos'e' quel puntino apre la pagina Aggiornamenti.
    AGGIORNA_LARGO = 4
    AGGIORNA_ALTO = 2
    # Verde pieno, non una tinta intermedia: su questo pannello le intensita'
    # a meta' scala sono la causa dello sfarfallio, e su quattro pixel si
    # vedrebbe piu' il tremolio del segnale.
    AGGIORNA_COLORE = (0, 255, 0)

    def _segno_aggiornamento(self):
        """Vero se va acceso il puntino della versione nuova."""
        conf = self.cfg.get("ota") or {}
        if not conf.get("segnale", True):
            return False
        if self.aggiornamento is None:
            return False
        try:
            return bool(self.aggiornamento())
        except Exception:                            # pragma: no cover
            return False
