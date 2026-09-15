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


# ------------------------------------------------------- fasce per servizio

# Dalla 8.1 ogni servizio puo' avere la sua fascia oraria. La regola resta
# questa, una sola: cambia soltanto da dove si leggono gli estremi.
#
# **Il flag viene prima di tutto.** Spento -- che e' il predefinito -- il
# servizio lavora sempre, cioe' come si e' sempre comportato: chi aggiorna non
# si accorge di niente finche' non accende una fascia lui.
#
# Il Media Player e' l'unico che una fascia ce l'aveva gia', sotto
# `mediaplayer.timer_*`. Quei campi restano dov'erano e questa funzione li
# legge da li': spostarli avrebbe voluto dire o perdere l'impostazione di chi
# aggiorna, o tenerne due copie che prima o poi divergono.

PREDEFINITA = {"enabled": False, "inizio": "08:00", "fine": "23:00"}


def fascia(cfg, nome):
    """La fascia di un servizio: (accesa, inizio, fine). Sempre tre valori."""
    if nome == "mediaplayer":
        conf = (cfg or {}).get("mediaplayer") or {}
        return (bool(conf.get("timer_enabled")),
                str(conf.get("timer_start") or MEDIA_INIZIO),
                str(conf.get("timer_end") or MEDIA_FINE))
    voce = ((cfg or {}).get("timing") or {}).get(nome) or {}
    return (bool(voce.get("enabled")),
            str(voce.get("inizio") or PREDEFINITA["inizio"]),
            str(voce.get("fine") or PREDEFINITA["fine"]))


def consentito(cfg, nome, adesso=None):
    """True se questo servizio puo' lavorare in questo momento.

    Non sa niente ne' dello Sleep ne' del night mode, ed e' voluto: quelli
    agiscono **a valle**, sul pannello, qualunque sorgente abbia vinto.
    Sommarli qui vorrebbe dire scrivere la stessa precedenza in due posti, e
    prima o poi in due modi diversi.
    """
    accesa, inizio, fine = fascia(cfg, nome)
    if not accesa:
        return True
    return in_window(minuto(adesso), parse_hhmm(inizio), parse_hhmm(fine))


def scrivi_fascia(cfg, nome, accesa, inizio, fine):
    """Salva la fascia di un servizio, dove quel servizio la tiene."""
    if nome == "mediaplayer":
        conf = cfg.setdefault("mediaplayer", {})
        conf["timer_enabled"] = bool(accesa)
        conf["timer_start"] = inizio
        conf["timer_end"] = fine
        return
    voce = cfg.setdefault("timing", {}).setdefault(nome, {})
    voce["enabled"] = bool(accesa)
    voce["inizio"] = inizio
    voce["fine"] = fine


def perche_fermo(cfg, nome, acceso, adesso=None):
    """Perche' questo servizio non sta lavorando adesso. "" se lavora.

    E' la ragione per cui la pagina Timing esiste. Aggiungere una fascia a
    quindici servizi moltiplica per quindici i modi in cui un servizio puo'
    non comparire: senza una colonna che risponda, fra un mese ci si chiede
    "perche' non vedo le scadenze" e si ricomincia a indovinare. E' gia'
    successo con il meteo, dove la colpa e' stata data a una fascia che non
    c'entrava niente.
    """
    if not acceso:
        return "spento"
    accesa, inizio, fine = fascia(cfg, nome)
    if not accesa:
        return ""
    if in_window(minuto(adesso), parse_hhmm(inizio), parse_hhmm(fine)):
        return ""
    return "fuori fascia %s-%s" % (inizio, fine)
