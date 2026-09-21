"""Il turno fra meteo e cielo: uno ogni due media, a turno.

La regola, detta come l'ha detta chi la voleva: *ogni due media compare il
meteo o la Luna, e si danno il cambio. La Luna solo di sera.* Di giorno, dato
che la Luna non c'e', lo spazio va sempre al meteo.

Sta qui, e non dentro il meteo o dentro il cielo, perche' e' **una** regola
che riguarda due sorgenti: scritta due volte, prima o poi le due copie
direbbero cose diverse.

Due cose che la frase non dice, e che servono:

* **il tetto di tempo.** Al mattino i media sono spenti, e contare i media
  vorrebbe dire non mostrare mai niente -- proprio quando il meteo serve. E'
  lo stesso difetto che OnAir aveva gia' incontrato, con la stessa cura:
  passato il tetto -- i minuti del giro del meteo, dieci di serie -- lo
  spazio si apre comunque;
* **il turno si consuma quando qualcuno lo vede.** La lezione della 8.2: se
  in quel momento il pannello era di un aereo o di una notifica, la finestra
  si chiude senza essere vista, e il turno non e' speso. Si riprova dopo un
  minuto, e si riprova la **stessa** sorgente, senza passare all'altra.

La fascia del mattino del meteo resta sua: dentro la fascia il turno non
decide niente, e il meteo mostra il bollettino ogni due minuti per conto suo.
"""

import threading
import time
from datetime import datetime

OGNI_N_MEDIA = 2
# Quanto aspettare prima di riprovare un turno andato a vuoto.
RIPROVA_SECONDI = 60


class Turni(object):

    def __init__(self, cfg, meteo, cielo, media):
        self.cfg = cfg
        self.meteo = meteo
        self.cielo = cielo
        self.media = media
        self._prossimo = "meteo"
        self._ultimo = time.monotonic()
        self._ultimo_conteggio = self._conteggio()
        # La sorgente a cui si e' appena dato lo spazio, finche' la sua
        # finestra non si chiude. E quando riprovare, se non l'ha vista nessuno.
        self._aperto = None
        self._riprova = 0.0
        self._running = False
        self._thread = None
        self._sveglia = threading.Event()
        # I numeri, per la pagina: quanti spazi dati e a chi.
        self.dati = {"meteo": 0, "cielo": 0, "persi": 0}

    # ------------------------------------------------------------ i media

    def _conteggio(self):
        try:
            return int(getattr(self.media, "_shown", 0))
        except (TypeError, ValueError):          # pragma: no cover
            return 0

    def _media_acceso(self):
        return bool(getattr(self.media, "enabled", False))

    def _tetto(self):
        """Dopo quanti secondi lo spazio si apre anche senza media.

        Sono i minuti del giro del meteo, quelli che c'erano gia' nella
        pagina: una manopola in piu' che dice la stessa cosa sarebbe una
        manopola di troppo. Zero spegne il tetto.
        """
        try:
            minuti = int((self.cfg.get("meteo") or {}).get("ogni_minuti", 10) or 0)
        except (TypeError, ValueError):
            minuti = 10
        return max(0, minuti) * 60

    # ------------------------------------------------------------ chi

    def _meteo_pronto(self):
        m = self.meteo
        if m is None or not getattr(m, "enabled", False):
            return False
        try:
            return m._meteo.dati() is not None
        except Exception:                        # pragma: no cover
            return False

    def _cielo_pronto(self, adesso):
        c = self.cielo
        if c is None or not getattr(c, "enabled", False):
            return False
        try:
            return c.e_notte(adesso)
        except Exception:                        # pragma: no cover
            return False

    def scegli(self, adesso):
        """A chi va lo spazio adesso: "meteo", "cielo" o None."""
        pronti = {"meteo": self._meteo_pronto(),
                  "cielo": self._cielo_pronto(adesso)}
        if pronti.get(self._prossimo):
            return self._prossimo
        altro = "cielo" if self._prossimo == "meteo" else "meteo"
        if pronti.get(altro):
            return altro
        return None

    def _mattino(self, adesso):
        m = self.meteo
        if m is None or not getattr(m, "enabled", False):
            return False
        try:
            return m.in_mattino(m.conf(), adesso)
        except Exception:                        # pragma: no cover
            return False

    # ------------------------------------------------------------ il passo

    def passo(self, ora=None, adesso=None):
        """Un controllo. Torna la sorgente a cui si e' dato lo spazio, o None.

        `ora` e' il tempo monotono, `adesso` l'ora locale: si passano nelle
        prove, per far scorrere una giornata in un secondo.
        """
        ora = time.monotonic() if ora is None else ora
        adesso = adesso or datetime.now().astimezone()

        # Una finestra aperta: si aspetta che si chiuda, poi si guarda se
        # l'ha vista qualcuno.
        if self._aperto is not None:
            sorgente = self.meteo if self._aperto == "meteo" else self.cielo
            if sorgente is not None and sorgente.active():
                return None
            vista = bool(getattr(sorgente, "_vista", False))
            chi = self._aperto
            self._aperto = None
            if vista:
                self.dati[chi] += 1
                self._ultimo = ora
                self._ultimo_conteggio = self._conteggio()
                self._prossimo = "cielo" if chi == "meteo" else "meteo"
            else:
                self.dati["persi"] += 1
                self._riprova = ora + RIPROVA_SECONDI
                self._prossimo = chi
            return None

        if self._mattino(adesso):
            # La fascia del mattino e' del meteo. Si tiene fermo il conto,
            # cosi' alle nove non arriva uno spazio "arretrato" appena finita.
            self._ultimo = ora
            self._ultimo_conteggio = self._conteggio()
            return None

        if self._riprova:
            if ora < self._riprova:
                return None
            self._riprova = 0.0
            dovuto = True
        else:
            dovuto = False
            if self._media_acceso():
                dovuto = (self._conteggio() - self._ultimo_conteggio
                          >= OGNI_N_MEDIA)
            tetto = self._tetto()
            if not dovuto and tetto and ora - self._ultimo >= tetto:
                dovuto = True
        if not dovuto:
            return None

        chi = self.scegli(adesso)
        if chi is None:
            # Nessuno pronto: di giorno con il meteo spento, per esempio. Lo
            # spazio non si accumula.
            self._ultimo = ora
            self._ultimo_conteggio = self._conteggio()
            return None
        aperto = False
        try:
            if chi == "meteo":
                aperto = self.meteo.apri_turno()
            else:
                aperto = self.cielo.apri_turno(adesso)
        except Exception as exc:                 # pragma: no cover
            print("[turni] %s non ha aperto: %s" % (chi, exc))
        if aperto:
            self._aperto = chi
            return chi
        self._ultimo = ora
        self._ultimo_conteggio = self._conteggio()
        return None

    # ------------------------------------------------------------ thread

    def start(self):
        if self._running:
            return
        self._running = True
        if self.meteo is not None:
            self.meteo.turni_attivi = True
        self._thread = threading.Thread(target=self._loop, name="turni",
                                        daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._sveglia.set()
        if self.meteo is not None:
            self.meteo.turni_attivi = False

    def _loop(self):
        while self._running:
            self._sveglia.wait(0.5)
            self._sveglia.clear()
            if not self._running:
                return
            try:
                self.passo()
            except Exception as exc:             # pragma: no cover
                print("[turni] errore: %s" % exc)
