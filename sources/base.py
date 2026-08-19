"""Interfaccia comune a tutte le sorgenti di contenuto.

Una sorgente non tocca mai il pannello: dichiara se ha qualcosa da mostrare
(`active`) e restituisce un'immagine PIL (`frame`). Decide l'arbitro chi vince.
"""

import i18n


class Source:
    name = "base"
    label = "Base"
    priority = 0

    def __init__(self, cfg, width, height):
        self.cfg = cfg
        self.width = width
        self.height = height
        self.enabled = False

    # ------------------------------------------------------------------ lingua

    def t(self, key, lang=None, **values):
        """Testo tradotto per la riga di stato.

        La lingua arriva dalla richiesta web quando c'e'; altrimenti si usa
        quella salvata in configurazione. I messaggi di log restano in
        italiano: sono per chi legge `journalctl`, non per l'interfaccia.
        """
        if not lang:
            lang = (self.cfg.get("web") or {}).get("language") or ""
        return i18n.translate(key, lang or i18n.FALLBACK, **values)

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

    def status(self, lang=None):
        """Riga di stato mostrata nella web UI, nella lingua richiesta."""
        return self.t("status.disabled", lang)
