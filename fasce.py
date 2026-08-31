"""Fasce orarie: una regola sola, in un punto solo.

Night mode, Sleep mode e il timer del Media Player fanno tutti la stessa
domanda — *questo minuto cade dentro la fascia?* — e la risposta deve essere
identica per tutti e tre, passaggio di mezzanotte compreso. Finche' la regola
stava dentro dmdd le sorgenti non potevano usarla (importare dmdd da una
sorgente vuol dire un ciclo di import), e la scelta era fra duplicarla e
lasciare che il Media Player non sapesse perche' era spento.
"""

import time


def parse_hhmm(value, fallback=0):
    """'22:30' -> minuti dalla mezzanotte."""
    try:
        hours, minutes = str(value).split(":")
        return (int(hours) % 24) * 60 + (int(minutes) % 60)
    except (ValueError, AttributeError):
        return fallback


def in_window(minute, start, end):
    """True se `minute` cade nella fascia, gestendo il passaggio di mezzanotte."""
    if start == end:
        return False
    if start < end:
        return start <= minute < end
    return minute >= start or minute < end


def minuto(adesso=None):
    """Minuti dalla mezzanotte, ora locale. `adesso` serve alle prove."""
    if adesso is None:
        adesso = time.localtime()
    return adesso.tm_hour * 60 + adesso.tm_min


# --------------------------------------------------------------- Media Player

MEDIA_INIZIO = "08:00"
MEDIA_FINE = "23:00"


def media_consentito(cfg, adesso=None):
    """True se il Media Player puo' lavorare in questo momento.

    Il flag viene prima di tutto: senza timer il Media Player lavora sempre,
    che e' come si e' sempre comportato e come resta per chi aggiorna.

    Questa funzione **non sa niente dello Sleep**, ed e' voluto. Lo Sleep non
    e' una gara fra fasce che il Media Player potrebbe vincere: spegne il
    pannello a valle, qualunque sorgente abbia vinto. Sommare qui le due
    condizioni vorrebbe dire scrivere due volte la stessa precedenza, e prima
    o poi in due modi diversi.
    """
    conf = cfg.get("mediaplayer") or {}
    if not conf.get("timer_enabled"):
        return True
    return in_window(minuto(adesso),
                     parse_hhmm(conf.get("timer_start"), parse_hhmm(MEDIA_INIZIO)),
                     parse_hhmm(conf.get("timer_end"), parse_hhmm(MEDIA_FINE)))


def fascia_media(cfg):
    """La fascia come testo, per la riga di stato: ('08:00', '23:00')."""
    conf = cfg.get("mediaplayer") or {}
    return (str(conf.get("timer_start") or MEDIA_INIZIO),
            str(conf.get("timer_end") or MEDIA_FINE))
