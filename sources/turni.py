"""Il turno fra meteo, Info inutili e cielo: uno ogni due media, a turno.

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

**Info inutili viene attaccato al meteo** (11.4). Chiesto cosi': «il servizio
dovrebbe apparire come il meteo, anche subito dopo il meteo stesso». Quindi
non aspetta un turno suo: appena la finestra del meteo si chiude ed e' stata
vista, il pannello passa a lui senza intervallo, e le sue due schermate si
fanno una dopo l'altra. Se il meteo non c'e' -- spento, o senza coordinate --
allora entra nel giro per conto suo, altrimenti non si vedrebbe mai.
"""

import threading
import time
from datetime import datetime

OGNI_N_MEDIA = 2
# Quanto aspettare prima di riprovare un turno andato a vuoto.
RIPROVA_SECONDI = 60


class Turni(object):

    def __init__(self, cfg, meteo, cielo, media, inutili=None):
        self.cfg = cfg
        self.meteo = meteo
        self.cielo = cielo
        self.media = media
        self.inutili = inutili
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
        self.dati = {"meteo": 0, "cielo": 0, "inutili": 0, "persi": 0}

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

    def _inutili_pronto(self):
        s = self.inutili
        if s is None or not getattr(s, "enabled", False):
            return False
        try:
            return bool(s.slide_disponibili())
        except Exception:                        # pragma: no cover
            return False

    def _sorgente(self, chi):
        return {"meteo": self.meteo, "cielo": self.cielo,
                "inutili": self.inutili}.get(chi)

    def _cielo_pronto(self, adesso):
        c = self.cielo
        if c is None or not getattr(c, "enabled", False):
            return False
        try:
            return c.e_notte(adesso)
        except Exception:                        # pragma: no cover
            return False

    def scegli(self, adesso):
        """A chi va lo spazio adesso: "meteo", "cielo", "inutili" o None.

        Info inutili di solito non passa di qui: arriva attaccato al meteo.
        Sta nell'elenco per il caso in cui il meteo non ci sia, altrimenti un
        pannello senza coordinate non lo vedrebbe mai.
        """
        pronti = {"meteo": self._meteo_pronto(),
                  "cielo": self._cielo_pronto(adesso),
                  "inutili": self._inutili_pronto() and not self._meteo_pronto()}
        giro = ("meteo", "inutili", "cielo")
        inizio = giro.index(self._prossimo) if self._prossimo in giro else 0
        for scarto in range(len(giro)):
            chi = giro[(inizio + scarto) % len(giro)]
            if pronti.get(chi):
                return chi
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
            sorgente = self._sorgente(self._aperto)
            if sorgente is not None and sorgente.active():
                return None
            vista = bool(getattr(sorgente, "_vista", False))
            chi = self._aperto
            self._aperto = None
            if chi == "inutili":
                # Le sue schermate si fanno di fila: finita la prima, si
                # chiede la seconda. Quando non ce n'e' piu', il giro
                # riprende da dove sarebbe stato senza di lui.
                if vista and self._avanza_inutili():
                    return None
                if vista:
                    self.dati["inutili"] += 1
                else:
                    self.dati["persi"] += 1
                self._ultimo = ora
                self._ultimo_conteggio = self._conteggio()
                self._prossimo = "cielo"
                return None
            if vista:
                self.dati[chi] += 1
                self._ultimo = ora
                self._ultimo_conteggio = self._conteggio()
                self._prossimo = "cielo" if chi == "meteo" else "meteo"
                # Subito dopo il meteo, senza intervallo: e' il suo posto.
                if chi == "meteo" and self._apri_inutili(adesso):
                    return "inutili"
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
            elif chi == "inutili":
                aperto = self.inutili.apri_turno(adesso)
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

    def _apri_inutili(self, adesso=None):
        """Attacca Info inutili alla coda del meteo. Torna True se ha preso."""
        if not self._inutili_pronto_sempre():
            return False
        try:
            if self.inutili.apri_turno(adesso):
                self._aperto = "inutili"
                return True
        except Exception as exc:                 # pragma: no cover
            print("[turni] inutili non ha aperto: %s" % exc)
        return False

    def _inutili_pronto_sempre(self):
        """Come `_inutili_pronto`, ma senza la condizione sul meteo: qui il
        meteo c'e' per forza, visto che si viene dalla sua finestra."""
        s = self.inutili
        if s is None or not getattr(s, "enabled", False):
            return False
        try:
            return bool(s.slide_disponibili())
        except Exception:                        # pragma: no cover
            return False

    def _avanza_inutili(self):
        try:
            if self.inutili is not None and self.inutili.avanza():
                self._aperto = "inutili"
                return True
        except Exception as exc:                 # pragma: no cover
            print("[turni] inutili non ha avanzato: %s" % exc)
        return False

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
