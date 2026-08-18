"""Interfaccia comune a tutte le sorgenti di contenuto.

Una sorgente non tocca mai il pannello: dichiara se ha qualcosa da mostrare
(`active`) e restituisce un'immagine PIL (`frame`). Decide l'arbitro chi vince.
"""


class Source:
    name = "base"
    label = "Base"
    priority = 0

    def __init__(self, cfg, width, height):
        self.cfg = cfg
        self.width = width
        self.height = height
        self.enabled = False

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

    def status(self):
        """Riga di stato mostrata nella web UI."""
        return "inattivo"
