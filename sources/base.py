"""Interfaccia comune a tutte le sorgenti di contenuto.

Una sorgente non tocca mai il pannello: dichiara se ha qualcosa da mostrare
(`active`) e restituisce un'immagine PIL (`frame`). Decide l'arbitro chi vince.
"""

import i18n


def lingua_del_pannello(cfg):
    """La lingua delle parole che finiscono sul vetro.

    **`clock.language` prima di tutto**, ed e' la regola scritta in
    `config.json`: *«web.language non ha effetto sul testo mostrato sul
    pannello»*. `web.language` e' la lingua dell'**interfaccia**, e di serie
    e' vuoto -- vuol dire «decidila tu dal browser», che su un pannello
    appeso al muro non vuol dire niente.

    La regola stava gia' in `Source.t` dalla 17.4.10, ma ogni posto che
    scrive una parola sul pannello se l'era riscritta a modo suo: il meteo
    con l'ordine rovesciato, i compleanni guardando solo la web, e i giochi
    -- quelli da cui e' arrivata la segnalazione, *«il gioco Quiz time ora
    e' in inglese»* -- passando il vuoto a `i18n.resolve`, che senza
    preferenza e senza browser risponde `FALLBACK`, cioe' inglese. Adesso la
    regola sta scritta una volta sola, e questa funzione e' quel posto.
    """
    cfg = cfg or {}
    return (((cfg.get("clock") or {}).get("language")
             or (cfg.get("web") or {}).get("language") or "").strip()
            or i18n.FALLBACK)


class Source:
    name = "base"
    label = "Base"
    priority = 0
    # Questa sorgente puo' stare in una fascia, o vuole tutto lo schermo?
    #
    # Dalla 17.1 un monitor mostra piu' tele insieme, una per fascia. Quasi
    # tutte le sorgenti ci stanno volentieri -- sono disegnate per 256x64 e
    # quella misura resta -- ma le **interattive** no: un gioco, Doom, il
    # Game Boy e l'anteprima della gestione media si guardano mentre si fa
    # qualcosa, e dentro una fascia su uno schermo grande sarebbero una
    # partita giocata col binocolo rovesciato. Quelle prendono la presa del
    # pannello e lo schermo intero, come hanno sempre fatto.
    in_fascia = True
    # Sorgenti che si danno il cambio e che devono stare **nella stessa**
    # fascia. Meteo, cielo e Info inutili non sono mai attivi insieme -- se
    # li da' il cambio `turni.py`, una finestra per volta -- e all'occhio
    # sono una cosa sola: la fascia che ogni tanto cambia argomento. Senza
    # questo, alla chiusura di una finestra il posto tornerebbe libero e
    # potrebbe prenderlo un altro, e il carosello salterebbe da una fascia
    # all'altra.
    gruppo = ""

    def __init__(self, cfg, width, height):
        self.cfg = cfg
        self.width = width
        self.height = height
        self.enabled = False

    # ------------------------------------------------------------------ lingua

    def t(self, key, lang=None, **values):
        """Testo tradotto, per la riga di stato o per il pannello.

        La lingua arriva dalla richiesta web quando c'e': quella la passa
        chi risponde a una pagina, e vince su tutto.

        **Senza, e' testo che finisce sul pannello**, e li' la lingua e'
        `clock.language` -- e' la regola scritta anche in `config.json`,
        «web.language non ha effetto sul testo mostrato sul pannello». Fino
        alla 17.4.10 questa riga guardava pero' `web.language`, che di serie
        e' **vuoto** perche' vuol dire «decidi tu dal browser»: il vuoto
        cadeva su `FALLBACK`, che e' l'inglese, e sul pannello italiano
        comparivano parole inglesi. Si vedeva nel meteo -- *«domani viene
        mostrato come Tomorrow»* -- ma riguardava tutte le sorgenti che
        scrivono una parola sul vetro.

        I messaggi di log restano in italiano: sono per chi legge
        `journalctl`, non per l'interfaccia.
        """
        return i18n.translate(key, lang or lingua_del_pannello(self.cfg),
                              **values)

    def start(self):
        """Avvia thread o socket. Chiamato quando il servizio viene abilitato."""

    def stop(self):
        """Rilascia le risorse. Chiamato quando il servizio viene disabilitato."""

    def active(self):
        """True se in questo momento la sorgente ha qualcosa da mostrare."""
        return False

    def frame(self):
        """Immagine PIL RGB (width x height) oppure None se nulla di nuovo."""
        return None

    def in_onda(self):
        """Il pannello e' appena passato a questa sorgente.

        Serve a distinguere due cose che fino alla 8.2 erano confuse: *ho
        deciso di mostrare qualcosa* e *qualcuno l'ha visto*. Sono diverse,
        perche' fra le due c'e' l'arbitro: una sorgente puo' aprire la sua
        finestra, restare accesa per tutta la sua durata e non andare mai a
        schermo perche' qualcuno con priorita' maggiore teneva il pannello.

        Chi conta i propri turni deve contarli **qui**, non quando apre la
        finestra. Il meteo lo faceva nel posto sbagliato e si e' misurato il
        prezzo: 460 turni bruciati al giorno contro 48 comparse vere.

        Predefinito: non fare niente. La maggior parte delle sorgenti non ha
        bisogno di saperlo.
        """

    def status(self, lang=None):
        """Riga di stato mostrata nella web UI, nella lingua richiesta."""
        return self.t("status.disabled", lang)
