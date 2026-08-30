"""Interfaccia comune a tutte le sorgenti di contenuto.

Una sorgente non tocca mai il pannello: dichiara se ha qualcosa da mostrare
(`active`) e restituisce un'immagine PIL (`frame`). Decide l'arbitro chi vince.
"""

import i18n


class Source:
    name = "base"
    label = "Base"
    priority = 0

    # Un "riempitivo" e' una sorgente che sta li' quando non c'e' di meglio e
    # che puo' subentrare a una sorgente rimasta **ferma**, pur avendo questa
    # una priorita' piu' alta. Doom in attract mode e' l'unico, per ora: senza
    # questa deroga non comparirebbe mai su un cabinato acceso, perche' ZeDMD
    # resta legittimamente padrone del pannello finche' Batocera e' collegato.
    riempitivo = False

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

    def cede_a_riempitivo(self):
        """True se ha diritto al pannello ma e' ferma da abbastanza tempo.

        Avere diritto al pannello e avere qualcosa da dire non sono la stessa
        cosa: una sorgente che mostra la stessa identica immagine da minuti
        puo' lasciare il posto a un riempitivo, e riprenderselo al primo
        contenuto nuovo. Solo ZeDMD lo fa; per tutte le altre e' `False`, e il
        comportamento non cambia di una virgola.
        """
        return False

    def frame(self):
        """Immagine PIL RGB (width x height) oppure None se nulla di nuovo."""
        return None

    def status(self, lang=None):
        """Riga di stato mostrata nella web UI, nella lingua richiesta."""
        return self.t("status.disabled", lang)
