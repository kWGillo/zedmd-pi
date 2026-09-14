"""Le copertine dei brani: prenderle, ridurle, e non farlo mai nel posto sbagliato.

Il modulo fa una cosa sola: dato un indirizzo, prima o poi restituisce
un'immagine pronta per il pannello. **Prima o poi** e' la parte importante.

## Perche' non si scarica dove si disegna

Il ciclo che disegna gira a trenta fotogrammi al secondo. Una richiesta HTTP
puo' metterci dieci secondi a fallire -- un server lento, una rete che non
risponde, un indirizzo cambiato -- e dieci secondi di pannello fermo sono un
guasto visibile causato da una decorazione. E' la stessa lezione gia' pagata
col meteo, e qui si applica prima di sbagliarla di nuovo.

Quindi `per()` non scarica: guarda in cache, e se non c'e' niente **mette in
coda** e torna `None`. Il pannello disegna senza copertina, e quando
l'immagine arriva il fotogramma dopo la mostra. Nessuna attesa, mai.

## Perche' non c'e' nessuna credenziale

L'indirizzo delle copertine di Home Assistant (`entity_picture`) porta **dentro
di se'** un token firmato, valido per quell'entita' e per poco tempo. Si
scarica senza intestazione di autenticazione, quindi sul Raspberry non c'e'
nessun segreto da custodire -- che e' la regola che regge tutto questo
progetto, e l'unico motivo per cui questa strada e' stata scelta fra le tante.

Se un giorno servisse un token vero, andrebbe riprogettata: un token a vita
lunga in un file di configurazione che si esporta e si condivide e' esattamente
la cosa che qui non si fa.

## Perche' i colori si riducono

Fino alla 7.2 questo progetto **non mostrava** la copertina, e c'era scritto
perche': a sessantaquattro pixel e' illeggibile, ed essendo fatta quasi solo di
mezzi toni e' il contenuto peggiore possibile per un pannello S-PWM. Non era
una svista: `safe_colors` esiste esattamente per questo, e meta' della storia
di questo progetto e' una caccia allo sfarfallio causato dai mezzi toni.

Quella decisione non si ribalta, si **aggira con lo stesso strumento gia'
usato altrove**: la Funcam mostra una telecamera su questo stesso vetro
riducendo i livelli per canale, e funziona. Qui si fa lo stesso. A due livelli
restano gli otto colori pieni -- quelli che non sfarfallano mai -- e il
disordine di Floyd-Steinberg restituisce le sfumature all'occhio invece che al
pannello. A zero livelli si lascia l'immagine com'e', per chi vuole provare.

## Perche' l'altezza e' fissa e la larghezza no

Una copertina di un disco e' quadrata, ma una locandina di un film no: Apple TV
serve immagini 16:9, e una serie puo' averne una verticale. Forzare il quadrato
vorrebbe dire tagliare o mettere le bande nere -- una decisione da prendere, e
sbagliata in tutti e due i modi.

Fissare l'**altezza** al pannello e lasciare libera la larghezza non richiede
nessuna decisione: l'immagine arriva come e', e occupa quello che le serve. Con
un tetto, pero', perche' un'immagine panoramica alta 64 sarebbe larga
centoquaranta e si mangerebbe meta' del vetro, lasciando i titoli senza spazio.
"""

import io
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image

AGENTE = "zedmd-pi/copertine (+https://github.com/kWGillo/zedmd-pi)"

# Quanto si aspetta una risposta. Generoso: sta in un thread suo e non blocca
# niente, e una copertina che arriva in ritardo e' meglio di una che non arriva.
ATTESA_SECONDI = 8

# Il tetto di quello che si scarica. Una copertina e' di solito sotto i 100 KB;
# oltre il mezzo megabyte c'e' quasi sicuramente un equivoco -- un'immagine da
# stampa, o un indirizzo che risponde con una pagina.
MASSIMO_BYTE = 2 * 1024 * 1024

# Quante copertine si tengono in memoria. Sono immagini gia' ridotte: a 64
# pixel di lato sono una dozzina di kilobyte l'una, quindi anche sedici sono
# meno di un fotogramma del pannello.
QUANTE = 16

# Quanto si aspetta prima di riprovare un indirizzo che ha gia' fallito. Senza
# questo, un indirizzo rotto verrebbe richiesto a ogni giro del disegno: il
# modo piu' rapido per trasformare una copertina mancante in un martellamento.
RIPROVA_SECONDI = 300


def assoluto(indirizzo, base=""):
    """Un indirizzo relativo diventa assoluto, se sappiamo rispetto a cosa.

    `entity_picture` di Home Assistant e' una **strada**, non un indirizzo:
    `/api/media_player_proxy/media_player.denon?token=...`. Senza sapere dove
    sta Home Assistant non si puo' chiedere niente a nessuno -- e si dice,
    invece di provare a indovinare un host.
    """
    indirizzo = (indirizzo or "").strip()
    if not indirizzo:
        return ""
    if indirizzo.startswith(("http://", "https://")):
        return indirizzo
    if not indirizzo.startswith("/"):
        return ""
    base = (base or "").strip().rstrip("/")
    if not base:
        return ""
    if not base.startswith(("http://", "https://")):
        base = "http://" + base
    return base + indirizzo


def riduci(dati, altezza, larghezza_massima, livelli=0):
    """I byte di un'immagine diventano un riquadro alto `altezza`.

    Torna `None` se non e' un'immagine: un indirizzo che risponde con una
    pagina di errore non deve sollevare, deve semplicemente non dare copertina.
    """
    try:
        immagine = Image.open(io.BytesIO(dati))
        immagine.load()
    except Exception:                     # noqa: BLE001 - PIL solleva di tutto
        return None
    immagine = immagine.convert("RGB")
    larghezza, alta = immagine.size
    if larghezza <= 0 or alta <= 0:
        return None
    nuova_larghezza = max(1, int(round(larghezza * altezza / float(alta))))
    if nuova_larghezza > larghezza_massima:
        # Oltre il tetto si **taglia al centro** invece di schiacciare: una
        # locandina panoramica compressa in un quadrato non e' piu'
        # riconoscibile, mentre il suo centro quasi sempre lo e'.
        proporzione = larghezza_massima / float(nuova_larghezza)
        taglio = max(1, int(round(larghezza * proporzione)))
        margine = (larghezza - taglio) // 2
        immagine = immagine.crop((margine, 0, margine + taglio, alta))
        nuova_larghezza = larghezza_massima
    # Prima si ridimensiona, poi si riducono i colori: al contrario, il
    # ridimensionamento rimescolerebbe i pixel gia' quantizzati e rimetterebbe
    # dentro tutti i mezzi toni appena tolti.
    ridotta = immagine.resize((nuova_larghezza, altezza), Image.LANCZOS)
    return riduci_colori(ridotta, livelli)


LIVELLI_MIN = 2
# Sei e non otto, e il motivo e' una legge della tavolozza: PIL puo' tenere al
# massimo **256 colori** in una tavolozza, e i livelli per canale fanno
# livelli**3 combinazioni. Sei danno 216 colori e ci stanno; sette ne
# darebbero 343 e otto 512, e la tavolozza verrebbe troncata a meta'.
#
# Troncata non vuol dire "un po' peggio": vuol dire che le combinazioni con
# molto rosso non esistono piu', e una faccia color pelle finisce verde. E'
# successo davvero, alla prima prova, con il limite messo a otto copiandolo
# dalla Funcam -- che pero' quantizza con l'aritmetica e non con una
# tavolozza, quindi quel limite non ce l'ha.
LIVELLI_MAX = 6


def riduci_colori(immagine, livelli):
    """Meno livelli per canale, con il disordine a compensare.

    `livelli` e' quanti valori puo' prendere ogni canale: due danno gli otto
    colori pieni -- gli stessi di `safe_colors` -- sei ne danno duecentosedici.
    Zero, o un numero fuori scala, lascia l'immagine com'e'.

    Il disordine (Floyd-Steinberg) non e' un abbellimento: senza, una faccia in
    otto colori diventa una macchia di campiture piatte. Con, l'occhio rimette
    insieme le sfumature da solo -- che e' lo stesso motivo per cui la Funcam
    e' guardabile.
    """
    try:
        quanti = int(livelli)
    except (TypeError, ValueError):
        return immagine
    if quanti < LIVELLI_MIN or quanti > LIVELLI_MAX:
        return immagine
    passo = 255.0 / (quanti - 1)
    tavolozza = []
    for r in range(quanti):
        for g in range(quanti):
            for b in range(quanti):
                tavolozza += [int(round(r * passo)), int(round(g * passo)),
                              int(round(b * passo))]
    # PIL vuole 256 voci: le mancanti si riempiono con l'ultima.
    ultimo = tavolozza[-3:] or [0, 0, 0]
    while len(tavolozza) < 768:
        tavolozza += ultimo
    riferimento = Image.new("P", (1, 1))
    riferimento.putpalette(tavolozza[:768])
    return immagine.quantize(palette=riferimento,
                             dither=Image.FLOYDSTEINBERG).convert("RGB")


def _scarica(indirizzo, timeout=ATTESA_SECONDI):
    richiesta = urllib.request.Request(indirizzo,
                                       headers={"User-Agent": AGENTE})
    with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
        tipo = (risposta.headers.get("Content-Type") or "").lower()
        if tipo and not tipo.startswith("image/"):
            # Non e' un'immagine: quasi sempre una pagina di errore travestita
            # da 200. Meglio accorgersene qui che dentro il decodificatore.
            raise ValueError("non e' un'immagine: %s" % tipo)
        return risposta.read(MASSIMO_BYTE + 1)[:MASSIMO_BYTE]


class Copertine(object):
    """Cache di copertine gia' ridotte, con un thread che le va a prendere."""

    def __init__(self, cfg):
        self.cfg = cfg
        self._lock = threading.Lock()
        self._pronte = {}          # indirizzo -> (immagine, altezza, quando)
        self._falliti = {}         # indirizzo -> quando, per non martellare
        self._coda = []
        # Gli indirizzi usciti dalla coda e non ancora finiti. Senza questo
        # insieme c'e' una finestra vera: il thread toglie l'indirizzo dalla
        # coda e comincia a scaricare, e per tutti i secondi che ci mette
        # quell'indirizzo non e' ne' in coda ne' fra i pronti -- quindi ogni
        # richiesta successiva lo rimette in coda e lo fa scaricare di nuovo.
        # Con un server veloce non si vede; con uno lento, che e' il caso in
        # cui conta, diventano dieci richieste per la stessa immagine.
        self._in_corso = set()
        self._sveglia = threading.Event()
        self._thread = None
        self._running = False
        self._errore = ""

    # ------------------------------------------------------- configurazione

    def _conf(self):
        return self.cfg.get("nowplaying") or {}

    def accese(self):
        return bool(self._conf().get("artwork", True))

    def base(self):
        return str(self._conf().get("artwork_base") or "").strip()

    def livelli(self):
        """Livelli per canale, come la Funcam. Zero = colore pieno."""
        try:
            return int(self._conf().get("artwork_livelli", 0) or 0)
        except (TypeError, ValueError):
            return 0

    def larghezza_massima(self, pannello):
        """Il tetto, in pixel. Di serie meta' del pannello."""
        try:
            valore = int(self._conf().get("artwork_larghezza_massima", 0) or 0)
        except (TypeError, ValueError):
            valore = 0
        return valore if valore > 0 else max(16, pannello // 2)

    # ------------------------------------------------------------ ciclo vita

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._sveglia.set()

    # ------------------------------------------------------------- richiesta

    def per(self, indirizzo, altezza, larghezza_pannello=256):
        """La copertina pronta per questo indirizzo, o `None`.

        **Non scarica e non aspetta mai.** Se non ce l'ha, la mette in coda e
        torna `None`: il pannello si disegna senza, e quando l'immagine arriva
        il fotogramma dopo la mostra.
        """
        if not self.accese():
            return None
        pieno = assoluto(indirizzo, self.base())
        if not pieno:
            return None
        with self._lock:
            voce = self._pronte.get(pieno)
            if voce is not None and voce[1] == altezza:
                return voce[0]
            fallito = self._falliti.get(pieno)
            if fallito is not None and time.time() - fallito < RIPROVA_SECONDI:
                return None
            if (pieno not in self._in_corso
                    and pieno not in [c[0] for c in self._coda]):
                self._coda.append((pieno, altezza,
                                   self.larghezza_massima(larghezza_pannello),
                                   self.livelli()))
        self._sveglia.set()
        if not self._running:
            self.start()
        return None

    def errore(self):
        return self._errore

    def quante(self):
        with self._lock:
            return len(self._pronte)

    # ------------------------------------------------------------------ ciclo

    def _loop(self):
        while self._running:
            with self._lock:
                lavoro = self._coda.pop(0) if self._coda else None
                if lavoro is not None:
                    self._in_corso.add(lavoro[0])
            if lavoro is None:
                self._sveglia.wait(2.0)
                self._sveglia.clear()
                continue
            indirizzo, altezza, tetto, quanti = lavoro
            try:
                immagine = riduci(_scarica(indirizzo), altezza, tetto, quanti)
            except (urllib.error.URLError, OSError, ValueError) as exc:
                immagine = None
                self._errore = str(exc)
            except Exception as exc:      # noqa: BLE001
                immagine = None
                self._errore = str(exc)
            with self._lock:
                self._in_corso.discard(indirizzo)
                if immagine is None:
                    self._falliti[indirizzo] = time.time()
                    continue
                self._errore = ""
                self._falliti.pop(indirizzo, None)
                self._pronte[indirizzo] = (immagine, altezza, time.time())
                # Si buttano le piu' vecchie: la copertina di due dischi fa non
                # serve piu' a nessuno, e la memoria su un Pi e' quella che e'.
                if len(self._pronte) > QUANTE:
                    vecchie = sorted(self._pronte.items(),
                                     key=lambda kv: kv[1][2])
                    for chiave, _v in vecchie[:len(self._pronte) - QUANTE]:
                        self._pronte.pop(chiave, None)
