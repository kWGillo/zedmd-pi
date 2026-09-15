# -*- coding: utf-8 -*-
"""La sveglia: l'unica cosa che questo pannello non sapeva ancora fare.

Che cosa fa
-----------
Fino a quattro orari, ciascuno con i suoi giorni della settimana. Quando uno
scatta, il pannello diventa un orologio che lampeggia e la scheda audio suona
finche' qualcuno non preme il pulsante della Funcam.

Perche' e' diversa da tutto il resto
------------------------------------
Ogni altra sorgente di questo progetto e' **educata**: chiede il pannello,
e se qualcun altro ha la precedenza aspetta il suo turno. Una sveglia
educata non e' una sveglia. Questa ha tre eccezioni che nessun altro
servizio ha, e ognuna e' stata necessaria:

**Vince su Sleep mode.** Il ciclo principale, quando dorme, si ferma *prima*
di chiedere all'arbitro chi debba comparire: una sorgente qualunque, per
quanto prioritaria, non verrebbe nemmeno interrogata. Una sveglia programmata
alle 7 con lo Sleep fino alle 8 non suonerebbe mai — che e' esattamente il
caso in cui serve di piu'.

**Vince sul display spento a mano.** Discutibile, e la scelta e' consapevole:
spegnere il pannello e' una decisione sul *presente*, mettere una sveglia e'
una promessa fatta al passato per il futuro. Fra le due vince la promessa, e
chi non la vuole la spegne.

**Non la tocca il volume notturno.** Il night mode abbassa la voce del DMD
perche' un aereo alle tre di notte non merita di svegliarti. Una sveglia si
mette apposta per svegliarti: sarebbe l'unico caso in cui quel silenzio fa
danno. Usa il volume di giorno, sempre.

Resta invece dentro una regola sola, che e' giusta: **se l'audio generale e'
spento, non suona.** Chi ha spento il suono non vuole sentire niente, e il
pannello lampeggia lo stesso.

Il pulsante
-----------
Non ne aggiunge uno nuovo: usa quello della Funcam, che sul cabinato c'e'
gia'. Mentre la sveglia suona quel pulsante appartiene a lei — un clic la
ferma e **non** scatta nessuna foto. La decisione sta in un punto solo: il
runtime da' alla telecamera un gancio da interrogare prima di agire, cosi'
nessuno dei due moduli deve sapere dell'altro.
"""

import time

from PIL import Image, ImageDraw

from .base import Source
from .clock import _load_font, parse_color

# Sopra tutto, ZeDMD compreso. Durante una partita a flipper una sveglia che
# aspetta educatamente il proprio turno non suona mai.
PRIORITA = 120

# Quante se ne possono impostare. Quattro: la sveglia dei giorni feriali,
# quella del fine settimana, e due per le eccezioni.
QUANTE = 4

# Ogni quanto si ritenta il suono mentre squilla. Non e' la durata del file:
# `suoni` scarta un avvio se ce n'e' gia' uno in corso, quindi questo e'
# semplicemente il ritmo con cui si bussa.
RITMO_SUONO = 1.5

# Il lampeggio: acceso per questo, spento per questo.
LAMPEGGIO = 0.45

COLORE = "#ff3b30"


def _hhmm(valore, predefinito=(7, 0)):
    """`07:30` -> (7, 30). Un valore storto vale il predefinito."""
    try:
        ore, minuti = str(valore).strip().split(":")[:2]
        ore, minuti = int(ore), int(minuti)
    except (TypeError, ValueError):
        return predefinito
    if not (0 <= ore <= 23 and 0 <= minuti <= 59):
        return predefinito
    return (ore, minuti)


def normalizza(voce):
    """Una sveglia con tutti i campi a posto, comunque sia scritta.

    Arriva dalla configurazione, che si puo' anche importare da un file: non
    si da' per scontato niente, e un campo storto non deve far cadere il
    servizio nel cuore della notte.
    """
    voce = voce if isinstance(voce, dict) else {}
    ore, minuti = _hhmm(voce.get("ora"), (7, 0))
    giorni = voce.get("giorni")
    if not isinstance(giorni, (list, tuple)) or not giorni:
        # Vuoto vuol dire tutti i giorni: e' la sveglia che si mette senza
        # pensarci, e deve essere quella che si ottiene senza scegliere.
        giorni = list(range(7))
    puliti = sorted({int(g) for g in giorni
                     if str(g).lstrip("-").isdigit() and 0 <= int(g) <= 6})
    try:
        durata = int(voce.get("durata", 120))
    except (TypeError, ValueError):
        durata = 120
    return {
        "enabled": bool(voce.get("enabled")),
        "ora": "%02d:%02d" % (ore, minuti),
        "minuto": ore * 60 + minuti,
        "giorni": puliti or list(range(7)),
        "suono": str(voce.get("suono") or "").strip(),
        "etichetta": str(voce.get("etichetta") or "").strip()[:24],
        # Dopo quanti secondi smette da sola. Una sveglia che suona per sempre
        # in una casa vuota e' un dispetto ai vicini, non una funzione.
        "durata": max(10, min(3600, durata)),
    }


class SvegliaSource(Source):
    name = "sveglia"
    label = "Sveglia"
    priority = PRIORITA

    def __init__(self, cfg, width, height):
        super().__init__(cfg, width, height)
        self._running = False
        # Quando ha cominciato a squillare, in tempo monotono. Zero = zitta.
        self._da = 0.0
        # Quale sveglia sta squillando, gia' normalizzata.
        self._voce = None
        # L'ultima occorrenza gia' servita: "2026-09-15 07:00|0". Serve a non
        # rifar scattare la stessa sveglia sessanta volte nel suo minuto.
        self._servita = ""
        self._prossimo_suono = 0.0
        self._ultimo_disegno = None
        # Il timer: una scadenza sola, in tempo di sistema, e la sua
        # etichetta. Zero = nessun timer in corso.
        #
        # Non e' una quinta sveglia, ed e' la distinzione che gli da' senso:
        # una sveglia si mette a un'ora, un timer **fra quanto**. La pasta non
        # scade alle 20:47, scade fra nove minuti -- e nessuno vuole guardare
        # l'orologio e fare la somma mentre ha le mani bagnate.
        self._timer_a = 0.0
        self._timer_nome = ""
        # Chi sa suonare un file. Lo attacca il runtime, come per tutti gli
        # altri ganci di questo progetto: una sorgente non deve sapere come
        # e' fatto l'audio, deve saper chiedere.
        self.suona = None

    # ------------------------------------------------------------ impostazioni

    def conf(self):
        return self.cfg.get("sveglia") or {}

    def voci(self):
        """Le sveglie impostate, normalizzate e in ordine di orario."""
        grezze = self.conf().get("voci")
        if not isinstance(grezze, (list, tuple)):
            grezze = []
        return [normalizza(v) for v in list(grezze)[:QUANTE]]

    # ------------------------------------------------------------------ ciclo

    def start(self):
        self._running = True

    def stop(self):
        self._running = False
        self.zittisci()

    # ------------------------------------------------------------- squillo

    def suonando(self):
        return self._da > 0.0

    def zittisci(self):
        """Ferma lo squillo. La chiamano il pulsante, la pagina e MQTT."""
        fermata = self.suonando()
        self._da = 0.0
        self._voce = None
        self._prossimo_suono = 0.0
        self._ultimo_disegno = None
        return fermata

    def rimanda(self):
        """Come `zittisci`, ma il nome dice cosa succede: torna domani."""
        return self.zittisci()

    # ------------------------------------------------------------------ timer

    def avvia_timer(self, minuti, nome=""):
        """Un conto alla rovescia. (ok, motivo).

        Sostituisce quello in corso invece di affiancarlo: un timer alla volta
        e' quello che serve in cucina, e due che scadono insieme darebbero un
        solo squillo con due motivi -- cioe' un'informazione persa.
        """
        try:
            minuti = float(minuti)
        except (TypeError, ValueError):
            return False, "durata non valida"
        if not 0 < minuti <= 24 * 60:
            return False, "durata non valida"
        self._timer_a = time.time() + minuti * 60
        self._timer_nome = str(nome or "").strip()[:24]
        return True, ""

    def ferma_timer(self):
        """Annulla il conto alla rovescia. True se ce n'era uno."""
        c_era = self._timer_a > 0
        self._timer_a = 0.0
        self._timer_nome = ""
        return c_era

    def timer_resta(self):
        """Secondi che mancano, o 0 se non c'e' nessun timer."""
        if not self._timer_a:
            return 0
        return max(0, int(round(self._timer_a - time.time())))

    def _timer_scaduto(self):
        return bool(self._timer_a) and time.time() >= self._timer_a

    def prova(self, secondi=15):
        """Fa squillare adesso. (ok, motivo). E' il pulsante della pagina.

        Non tocca `_servita`: una prova alle 06:59 non deve impedire alla
        sveglia vera di scattare un minuto dopo.
        """
        if not self._running or not self.enabled:
            return False, "servizio spento"
        voce = dict(normalizza({"enabled": True, "ora": time.strftime("%H:%M"),
                                "durata": secondi, "etichetta": ""}))
        voce["suono"] = next((v["suono"] for v in self.voci()
                              if v["enabled"] and v["suono"]), "")
        self._da = time.monotonic()
        self._voce = voce
        self._prossimo_suono = 0.0
        self._ultimo_disegno = None
        self._bussa()
        return True, ""

    def controlla(self, adesso=None):
        """Guarda l'orologio e fa partire una sveglia se e' il momento.

        Restituisce True se **in questo istante** la sveglia sta squillando.
        La chiama sia l'arbitro sia il ciclo principale — quest'ultimo perche'
        durante lo Sleep l'arbitro non viene nemmeno interpellato, e senza
        questa seconda chiamata una sveglia notturna non suonerebbe mai.
        """
        if not self._running or not self.enabled:
            if self.suonando():
                self.zittisci()
            return False

        adesso = adesso or time.localtime()
        minuto = adesso.tm_hour * 60 + adesso.tm_min
        giorno = adesso.tm_wday
        chiave_ora = time.strftime("%Y-%m-%d %H:%M", adesso)

        if not self.suonando() and self._timer_scaduto():
            # Il timer viene prima delle sveglie: e' stato messo pochi minuti
            # fa, quindi e' la cosa piu' recente che qualcuno abbia chiesto.
            nome = self._timer_nome
            self.ferma_timer()
            self._da = time.monotonic()
            self._voce = normalizza({
                "enabled": True, "ora": time.strftime("%H:%M", adesso),
                "etichetta": nome or "TIMER",
                "durata": int(self.conf().get("durata_timer", 120) or 120),
                "suono": next((v["suono"] for v in self.voci()
                               if v["enabled"] and v["suono"]), ""),
            })
            self._prossimo_suono = 0.0
            self._ultimo_disegno = None
            print("[sveglia] timer scaduto%s"
                  % (": %s" % nome if nome else ""))

        if not self.suonando():
            for indice, voce in enumerate(self.voci()):
                if not voce["enabled"] or giorno not in voce["giorni"]:
                    continue
                if voce["minuto"] != minuto:
                    continue
                chiave = "%s|%d" % (chiave_ora, indice)
                if chiave == self._servita:
                    continue
                self._servita = chiave
                self._da = time.monotonic()
                self._voce = voce
                self._prossimo_suono = 0.0
                self._ultimo_disegno = None
                print("[sveglia] scattata: %s%s" % (
                    voce["ora"],
                    " (%s)" % voce["etichetta"] if voce["etichetta"] else ""))
                break

        if self.suonando():
            # Si spegne da sola dopo la durata: una sveglia che suona per
            # sempre in una casa vuota e' un dispetto, non una funzione.
            if time.monotonic() - self._da >= self._voce["durata"]:
                print("[sveglia] nessuno ha risposto: mi fermo")
                self.zittisci()
            else:
                self._bussa()
        return self.suonando()

    def _bussa(self):
        """Ritenta il suono, se e' ora. Il ritmo lo detta `RITMO_SUONO`."""
        if self.suona is None:
            return
        adesso = time.monotonic()
        if adesso < self._prossimo_suono:
            return
        self._prossimo_suono = adesso + RITMO_SUONO
        try:
            self.suona(self._voce.get("suono") or "")
        except Exception as exc:          # pragma: no cover
            # Una sveglia che non riesce a suonare deve **continuare a
            # lampeggiare**, non cadere. Il pannello e' meta' della funzione.
            print("[sveglia] suono non riprodotto: %s" % exc)

    # ------------------------------------------------------------------ arbitro

    def active(self):
        return self.controlla()

    # --------------------------------------------------------------- disegno

    def frame(self):
        if not self.suonando():
            return None
        acceso = int((time.monotonic() - self._da) / LAMPEGGIO) % 2 == 0
        ora = time.strftime("%H:%M")
        firma = (acceso, ora)
        if firma == self._ultimo_disegno:
            return None
        self._ultimo_disegno = firma
        return self.disegna(acceso, ora)

    def disegna(self, acceso, ora):
        image = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        if not acceso:
            # Il nero fa parte del lampeggio: senza la meta' spenta non c'e'
            # nessun lampeggio, c'e' solo un orologio.
            return image

        draw = ImageDraw.Draw(image)
        colore = parse_color(self.conf().get("colore", COLORE),
                             parse_color(COLORE))
        etichetta = (self._voce or {}).get("etichetta") or ""

        # L'ora prende quasi tutta l'altezza quando non c'e' un'etichetta, e
        # le lascia spazio quando c'e'. Le misure si chiedono al font invece
        # di fissarle: e' la lezione del player, che con le frazioni fisse
        # faceva toccare le righe.
        alta = int(self.height * (0.62 if etichetta else 0.78))
        font = _load_font(max(10, alta))
        larghezza, altezza = self._misura(draw, ora, font)
        # Se il carattere scelto sfora in larghezza si stringe: su un pannello
        # 256x64 non succede, ma questo codice gira anche su pannelli diversi.
        while larghezza > self.width - 8 and alta > 10:
            alta = int(alta * 0.9)
            font = _load_font(max(10, alta))
            larghezza, altezza = self._misura(draw, ora, font)

        y = (self.height - altezza) // 2 if not etichetta else 0
        draw.text(((self.width - larghezza) // 2, y), ora,
                  font=font, fill=colore)

        if etichetta:
            font_e = _load_font(max(7, int(self.height * 0.20)))
            larghezza_e, altezza_e = self._misura(draw, etichetta, font_e)
            draw.text(((self.width - larghezza_e) // 2,
                       self.height - altezza_e - 1),
                      etichetta, font=font_e, fill=(255, 255, 255))
        return image

    @staticmethod
    def _misura(draw, testo, font):
        try:
            riquadro = draw.textbbox((0, 0), testo, font=font)
            return (riquadro[2] - riquadro[0], riquadro[3] - riquadro[1])
        except Exception:                 # pragma: no cover
            return (len(testo) * 6, 10)

    # ------------------------------------------------------------------ stato

    def prossima(self, adesso=None):
        """La prossima sveglia che scattera': (voce, quando). O (None, None).

        Serve alla pagina e a Home Assistant. Si guardano i sette giorni a
        venire invece di calcolare a mano i casi del fine settimana: sette
        giri di ciclo costano niente e non hanno casi particolari da sbagliare.
        """
        voci = [v for v in self.voci() if v["enabled"]]
        if not voci:
            return (None, None)
        adesso = adesso or time.localtime()
        ora_minuto = adesso.tm_hour * 60 + adesso.tm_min
        base = time.mktime((adesso.tm_year, adesso.tm_mon, adesso.tm_mday,
                            0, 0, 0, 0, 0, -1))
        migliore = (None, None)
        for salto in range(8):
            giorno = (adesso.tm_wday + salto) % 7
            for voce in voci:
                if giorno not in voce["giorni"]:
                    continue
                if salto == 0 and voce["minuto"] <= ora_minuto:
                    continue
                quando = base + salto * 86400 + voce["minuto"] * 60
                if migliore[1] is None or quando < migliore[1]:
                    migliore = (voce, quando)
            if migliore[1] is not None:
                break
        return migliore

    def status(self, lang=None):
        if not self._running or not self.enabled:
            return self.t("status.disabled", lang)
        if self.suonando():
            return self.t("status.sveglia.suona", lang,
                          ora=(self._voce or {}).get("ora", ""))
        resta = self.timer_resta()
        if resta:
            return self.t("status.sveglia.timer", lang,
                          minuti="%d:%02d" % (resta // 60, resta % 60))
        voce, quando = self.prossima()
        if voce is None:
            return self.t("status.sveglia.nessuna", lang)
        return self.t("status.sveglia.prossima", lang, ora=voce["ora"],
                      giorno=time.strftime("%a", time.localtime(quando)))

    def riepilogo(self):
        """Quel che serve alla pagina e a Home Assistant."""
        voce, quando = self.prossima()
        resta = self.timer_resta()
        return {
            "acceso": bool(self.enabled),
            "suona": self.suonando(),
            "adesso": (self._voce or {}).get("ora", ""),
            "etichetta": (self._voce or {}).get("etichetta", ""),
            "prossima": voce["ora"] if voce else "",
            "prossima_quando": quando or 0,
            "timer": resta,
            "timer_nome": self._timer_nome,
            "timer_testo": "%d:%02d" % (resta // 60, resta % 60) if resta else "",
            "voci": self.voci(),
        }
