"""Notifiche da Home Assistant: la casa parla al pannello.

Fino alla 6.0 il DMD parlava tanto e ascoltava pochissimo. Pubblicava una
trentina di topic -- interruttori, luminosita', scadenze, rifiuti -- e si
iscriveva soltanto ai comandi dei propri interruttori e al brano in
riproduzione.

Ma la cosa che sa di piu', in casa, e' Home Assistant: sa chi c'e', se la
porta e' aperta, se l'allarme e' inserito, se la lavatrice ha finito. Il DMD
ha lo schermo e non sa niente; Home Assistant sa tutto e non ha uno schermo in
salotto. Questa sorgente mette in comunicazione le due cose nel verso che
mancava.

**Il contratto e' volutamente piccolo.** Un topic, un JSON con tre campi, tre
livelli. La politica -- quando parlare, quando tacere, con che parole -- sta
in Home Assistant, dove stanno gia' le automazioni: duplicarla anche qui
vorrebbe dire due verita' che prima o poi divergono.

**Sul livello si regge tutto.** Non e' un'etichetta decorativa: decide il
colore, se lampeggia e -- la cosa che conta davvero -- se puo' interrompere
una partita. `info` e `avviso` aspettano il loro turno come ogni altra
sorgente; `allarme` si prende il pannello anche mentre giochi, perche' se
qualcuno entra in casa alle tre di notte il punteggio di Breakout non e' la
priorita'. Ed e' scomodo da usare apposta: se diventasse il livello di tutti,
il pannello smetterebbe di essere un oggetto da salotto e diventerebbe una
sveglia che non si spegne.
"""

import json
import threading
import time
from collections import deque

from PIL import Image

from . import testo as impaginazione
from .banner import BLINK_PERIOD
from .base import Source
from .clock import parse_color

# I tre livelli, con il colore di riserva e il carattere che li distingue.
# Chi pubblica puo' scavalcare il colore, ma non deve essere obbligato a
# saperne niente: un'automazione in Home Assistant deve restare di tre righe.
LIVELLI = {
    "info": {"colore": "#7ad7ff", "lampeggio": False, "interrompe": False},
    "avviso": {"colore": "#ffa000", "lampeggio": False, "interrompe": False},
    "allarme": {"colore": "#ff2a20", "lampeggio": True, "interrompe": True},
}
LIVELLO_PREDEFINITO = "info"

# Quanto sta a schermo una notifica se il messaggio non dice altro.
SECONDI_MINIMI = 2
SECONDI_MASSIMI = 120

# Il bordo che porta il livello, in pixel. Due e' il minimo che si vede da
# tre metri senza rubare spazio al testo: su 64 righe sono il 6% dell'altezza.
BORDO = 2

# Su quante righe si puo' spezzare un messaggio, e quanto spazio fra una e
# l'altra. Oltre le quattro il carattere scende sotto i tredici pixel e da
# lontano non si legge piu': a quel punto e' meglio tagliare che fingere.
#
# I numeri vivono in `sources.testo`, insieme alla regola che li usa: da
# quando c'e' OnAir sono due i servizi che impaginano cosi', e una regola
# scritta due volte prima o poi diverge.
RIGHE_MASSIME = impaginazione.RIGHE_MASSIME
INTERLINEA = impaginazione.INTERLINEA

# Il testo non porta piu' il colore del livello: lo porta il bordo. Bianco
# pieno perche' e' un "colore sicuro" -- componenti a 0 o 255 -- e su questo
# pannello le intensita' intermedie sono la causa dello sfarfallio.
COLORE_TESTO = (255, 255, 255)

# Cosa si scrive in fondo a un messaggio che non ci sta nemmeno a quattro
# righe. Il testo intero resta nella pagina web: sul pannello si taglia,
# perche' un messaggio che non entra in 256x64 non diventa leggibile
# scorrendo -- diventa lento, e ti obbliga ad aspettare l'inizio del giro.
PUNTINI = impaginazione.PUNTINI


class NotificheSource(Source):
    name = "notifiche"
    label = "Notifiche"
    # Sopra i satelliti (61) e tutto il resto, sotto l'anteprima (90) e ZeDMD
    # (100). Il criterio e' lo stesso di sempre: una notifica e' un **evento**
    # -- succede adesso o non succede piu' -- mentre un aereo, un satellite e
    # una foto tornano. Nessuna priorita' pareggia con un'altra.
    priority = 70

    def __init__(self, cfg, width, height):
        super().__init__(cfg, width, height)
        self._running = False
        self._lock = threading.Lock()
        self._image = None
        self._dirty = False
        self._showing = False
        self._coda = deque()
        self._thread = None
        self._sveglia = threading.Event()
        self._mostrate = 0
        self._scartate = 0
        self._ultima = ""
        self._ultimo_errore = ""
        # Lo mette il Runtime, come per Doom e il Game Boy: serve solo al
        # livello `allarme`, l'unico che ha diritto di interrompere.
        self.arbiter = None
        # Chi sa suonare il campanello di un livello. Lo attacca il runtime,
        # come per la sveglia: qui non si sa com'e' fatto l'audio, si sa solo
        # che a una notifica corrisponde un suono.
        self.suona = None

    # ------------------------------------------------------------- ciclo vita

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._sveglia.set()
        self._coda.clear()
        self._showing = False
        with self._lock:
            self._image = None
            self._dirty = False

    def active(self):
        return self._running and self._showing

    def frame(self):
        with self._lock:
            if not self._dirty or self._image is None:
                return None
            self._dirty = False
            return self._image

    def status(self, lang=None):
        if not self._running:
            return self.t("status.disabled", lang)
        if self._ultimo_errore:
            return self.t("status.notifiche.error", lang,
                          error=self._ultimo_errore[:60])
        if self._showing and self._ultima:
            return self.t("status.notifiche.showing", lang,
                          text=self._ultima[:40])
        return self.t("status.notifiche.waiting", lang,
                      topic=self._conf().get("topic", ""),
                      shown=self._mostrate, dropped=self._scartate)

    def _conf(self):
        return self.cfg.get("notifiche", {})

    # ------------------------------------------------------------- ricezione

    def handle_mqtt(self, topic, payload):
        """Arriva un messaggio dal broker. Non solleva mai.

        Accetta due forme. Un **JSON** con `testo`, `livello`, `secondi` e
        facoltativamente `colore` e `lampeggio`; oppure **testo semplice**,
        che vale come `info` con la durata predefinita -- cosi' una prova al
        volo si fa con `mosquitto_pub -t dmd/notifica -m "ciao"` senza
        costruire nessun JSON.

        Un messaggio malformato non deve spegnere niente: si conta fra gli
        scartati e si dice nella riga di stato, invece di finire in un
        registro che nessuno legge. E' la lezione del payload vuoto verso
        Home Assistant, applicata nel verso opposto.
        """
        # Il livello puo' arrivare dal **topic**: `dmd/notifica/avviso`. Serve
        # alle tre entita' notify di Home Assistant, che sanno mandare solo un
        # testo -- e cosi' il livello e' la scelta del bersaglio nella tendina
        # invece di un campo da ricordare. Un `livello` scritto dentro il JSON
        # vince comunque: chi si prende la briga di dirlo esplicitamente sa
        # quello che vuole.
        coda = str(topic or "").rstrip("/").rsplit("/", 1)[-1].lower()
        dal_topic = coda if coda in LIVELLI else ""
        try:
            voce = self._interpreta(payload, dal_topic)
        except Exception as exc:          # noqa: BLE001
            self._scartate += 1
            self._ultimo_errore = str(exc)
            print("[notifiche] messaggio scartato: %s" % exc)
            return
        if voce is None:
            return
        massimo = max(1, int(self._conf().get("massimo_in_coda", 20)))
        if len(self._coda) >= massimo:
            # Meglio perdere la piu' vecchia che accumulare: una notifica di
            # mezz'ora fa non interessa piu' a nessuno.
            self._coda.popleft()
            self._scartate += 1
        self._coda.append(voce)
        self._ultimo_errore = ""
        self._sveglia.set()

    def _interpreta(self, payload, livello_topic=""):
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8", "replace")
        testo_grezzo = (payload or "").strip()
        if not testo_grezzo:
            return None
        if testo_grezzo[0] in "{[":
            # Sembra JSON: allora **deve** esserlo. Se non lo e', il messaggio
            # si scarta invece di mostrarlo com'e'. Trovato da una prova: con
            # il ripiego a testo semplice, un'automazione con un errore di
            # battitura faceva scorrere `{rotto` in salotto -- e chi guarda il
            # pannello non ha modo di capire che il guasto e' in Home
            # Assistant. Meglio una notifica persa e contata fra gli scartati.
            try:
                dati = json.loads(testo_grezzo)
            except ValueError as exc:
                raise ValueError("JSON non valido: %s" % exc)
            if not isinstance(dati, dict):
                raise ValueError("il JSON non e' un oggetto")
        else:
            # Testo semplice: vale come notifica al livello piu' basso. Serve
            # per provare al volo, senza costruire nessun JSON.
            dati = {"testo": testo_grezzo}

        testo = str(dati.get("testo") or dati.get("message") or "").strip()
        if not testo:
            raise ValueError("manca il testo")
        livello = str(dati.get("livello") or dati.get("level")
                      or livello_topic or LIVELLO_PREDEFINITO).lower()
        if livello not in LIVELLI:
            # Un livello inventato non fa cadere la notifica: si mostra al
            # minimo grado. Perdere il messaggio sarebbe peggio.
            livello = LIVELLO_PREDEFINITO
        regole = LIVELLI[livello]
        colori = self._conf().get("colori") or {}
        try:
            secondi = float(dati.get("secondi", dati.get("seconds",
                                     self._conf().get("secondi", 8))))
        except (TypeError, ValueError):
            secondi = float(self._conf().get("secondi", 8))
        return {
            "testo": testo,
            "livello": livello,
            "secondi": max(SECONDI_MINIMI, min(SECONDI_MASSIMI, secondi)),
            "colore": str(dati.get("colore") or dati.get("color")
                          or colori.get(livello) or regole["colore"]),
            "lampeggio": bool(dati.get("lampeggio",
                                       dati.get("blink", regole["lampeggio"]))),
            "interrompe": bool(regole["interrompe"]),
        }

    # ------------------------------------------------------------------ ciclo

    def _loop(self):
        while self._running:
            if not self._coda:
                self._sveglia.wait(5.0)
                self._sveglia.clear()
                continue
            voce = self._coda.popleft()
            try:
                self._mostra(voce)
            except Exception as exc:      # noqa: BLE001
                print("[notifiche] %s" % exc)
            finally:
                self._showing = False
                self._ultima = ""

    def _mostra(self, voce):
        """La notifica sta ferma sul pannello per il tempo previsto.

        Fino alla 9.4 un messaggio che non ci stava in una riga **scorreva**,
        come il banner. Era il caso peggiore proprio dove contava di piu': un
        allarme lungo era rosso scuro *e* in movimento, cioe' da leggere
        aspettando che ripassasse l'inizio. Adesso il testo sta fermo sempre,
        spezzato su quante righe servono, e se non ci sta nemmeno cosi' si
        taglia.
        """
        righe, font = self._impagina(voce["testo"])
        self._ultima = voce["testo"]
        self._showing = True
        self._mostrate += 1

        # Il suono parte **qui**, insieme al primo fotogramma: e' il momento in
        # cui la notifica esiste. Il gancio lo attacca il runtime, come per la
        # sveglia -- una sorgente non deve sapere com'e' fatto l'audio, deve
        # saper chiedere. Un livello, un suono: chi sente dall'altra stanza
        # deve poter decidere se alzarsi senza girare la testa.
        if self.suona is not None:
            try:
                self.suona(voce["livello"])
            except Exception as exc:      # noqa: BLE001
                print("[notifiche] suono non riprodotto: %s" % exc)

        preso = False
        if voce["interrompe"] and self.arbiter is not None:
            # La presa del pannello, la stessa che usano Doom e il Game Boy.
            # E' l'unico modo per passare sopra a una partita: la priorita' da
            # sola non basta, perche' chi tiene il pannello lo tiene.
            self.arbiter.hold_on(self.name)
            preso = True
        try:
            scadenza = self._fine(voce)
            acceso_prima = None
            while self._running and time.time() < scadenza:
                acceso = self._acceso(voce)
                if acceso != acceso_prima:
                    self._pubblica(self._tela(voce, righe, font, acceso))
                    acceso_prima = acceso
                time.sleep(0.05)
        finally:
            if preso:
                self.arbiter.hold_off(self.name)

    def _fine(self, voce):
        return time.time() + voce["secondi"]

    def _acceso(self, voce):
        if not voce["lampeggio"]:
            return True
        return (time.time() % BLINK_PERIOD) < BLINK_PERIOD / 2

    def _pubblica(self, immagine):
        with self._lock:
            self._image = immagine
            self._dirty = True

    # ------------------------------------------------------------------ resa

    def _impagina(self, testo):
        """Righe e carattere: il piu' grande in cui il messaggio ci sta.

        Si provano una, due, tre, quattro righe e si tiene la prima
        impaginazione che entra: e' lo stesso criterio con cui l'orologio
        sceglie il carattere della colonna dei rifiuti, e ha il pregio che un
        messaggio corto resta grande invece di rimpicciolirsi per uniformita'.

        Se non entra nemmeno a quattro righe si taglia l'ultima e si mettono
        i puntini. Il testo intero resta nella pagina web.
        """
        # Il carattere non supera mai quello configurato: su una riga sola,
        # senza tetto, un "OK" riempirebbe il pannello da bordo a bordo.
        tetto = max(8, int(self.height * float(self._conf().get("altezza", 0.5))))
        return impaginazione.impagina(
            testo,
            larghezza=self.width - 2 * BORDO - 4,
            altezza=self.height - 2 * BORDO - 2,
            tetto=tetto)

    def _tela(self, voce, righe, font, bordo_acceso=True):
        """Il fotogramma: il bordo del livello e il testo fermo al centro.

        Lampeggia **solo il bordo**. Prima lampeggiava tutto, testo compreso,
        quindi meta' del tempo un allarme non si poteva leggere: l'urgenza si
        vede da lontano e le parole restano ferme.
        """
        from PIL import ImageDraw
        tela = Image.new("RGB", (self.width, self.height), (0, 0, 0))
        disegna = ImageDraw.Draw(tela)
        if bordo_acceso:
            disegna.rectangle((0, 0, self.width - 1, self.height - 1),
                              outline=parse_color(voce["colore"],
                                                  (0xFF, 0xFF, 0xFF)),
                              width=BORDO)
        impaginazione.scrivi_centrato(disegna, righe, font,
                                      self.width, self.height, COLORE_TESTO,
                                      margine=BORDO)
        return tela


# Restano come nomi locali perche' ci sono prove che li chiamano cosi', ma
# la regola vive in `sources.testo`, dove la usa anche OnAir.
_spezza = impaginazione.spezza
_accorcia = impaginazione.accorcia
