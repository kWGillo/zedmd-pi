"""Profili hardware del pannello.

Un profilo e' l'insieme completo dei parametri che un certo tipo di pannello
vuole: geometria, tipo di driver, indirizzamento delle righe, taratura fine.
Sono venti numeri trovati per tentativi, e nessuno se li ricorda.

A che serve averli qui. Sbagliare un parametro del pannello non da' un errore:
da' un display illeggibile, e da li' non si torna indietro a memoria. Con un
profilo si torna alla configurazione buona in un clic, e si riparte.

Aggiungere un tipo di pannello significa aggiungere una voce a PRESETS: il
resto — menu a tendina, applicazione, etichette — funziona da solo.
"""

import re

# I valori sono esattamente quelli del capitolo 7 del manuale piu' la
# taratura fine trovata sul campo. Non toccarli senza aver riprovato sul
# pannello: sono il risultato di una campagna di prove, non una scelta di
# stile.
PRESETS = {
    "fm6373_dp32020b": {
        "label": "FM6373 & DP32020B",
        "values": {
            "rows": 64,
            "cols": 128,
            "chain": 2,
            "parallel": 1,
            # Il cablaggio NON sta qui: vedi CABLAGGI in fondo. Che pannello
            # e' e come e' collegato sono due fatti indipendenti, e mescolarli
            # vorrebbe dire che riapplicare il profilo del pannello ributta
            # l'uscita sul cablaggio diretto con la Bonnet montata.
            "panel_type": "fm6373",
            "spwm_row_address_type": 1,
            "spwm_scan_rows": 64,
            "spwm_data_layout": 0,
            "spwm_register_config": 2,
            "slowdown": 5,
            "limit_refresh": 0,
            "pwm_bits": 10,
            "pwm_lsb_nanoseconds": 200,
            "pwm_dither_bits": 1,
            "spwm_env": {
                "SPWM_END_OF_FRAME_EXTRA_ROW_CYCLES": "1",
                "SPWM_FRAME_END_SLEEP_US": "300",
            },
        },
    },
    # Segnaposto per i pannelli SM16380SC + 5368PS: la configurazione
    # funzionante non esiste ancora, ne' qui ne' pubblicamente. La voce
    # comparira' quando ci sara' qualcosa da mettere dentro.
}

# Voce che non applica niente: dice soltanto "questi parametri li ho scelti
# io". Serve perche' l'utente possa vedere, dal menu, che la configurazione
# attuale non corrisponde a nessun profilo noto.
CUSTOM = "custom"

# Il profilo che nasce da una taratura automatica. Non sta in PRESETS perche'
# non e' un fatto del pannello ma una misura di **questa** macchina: dipende
# dalla scheda SD, dal carico, da cosa gira accanto. Vive in
# `panel["autotune"]`, scritto da autotune.py, e compare nel menu solo se
# esiste davvero.
AUTOTUNE = "autotune"


def profilo_autotune(panel):
    blocco = (panel or {}).get(AUTOTUNE) or {}
    return blocco if blocco.get("values") else None


_ASSENTE = object()


def base_autotune(blocco):
    """Il profilo da cui e' partita la taratura, se e' uno di quelli noti.

    La taratura misura **un parametro**: gli altri diciannove sono quelli che
    c'erano quando e' partita. Perche' la voce «Autotune» nel menu voglia dire
    qualcosa bisogna sapere da dove partiva, altrimenti applicarla cambia un
    numero e lascia gli altri come capita — che e' esattamente il difetto:
    dopo aver portato il PWM a 8 a mano, scegliere «Autotune» lasciava il PWM
    a 8, perche' il profilo tarato il PWM non ce l'ha scritto.

    Tre casi. La chiave c'e' e nomina un profilo noto: e' quello. La chiave
    c'e' e dice altro — `custom`, tipicamente: la taratura e' partita da una
    configurazione fatta a mano, non c'e' nessun profilo a cui tornare e si
    applica solo il parametro misurato, come prima. La chiave **manca**: e' un
    profilo scritto da una versione precedente, che il campo non lo salvava,
    e finche' di profili ne esiste uno solo non c'e' niente da indovinare.
    """
    base = (blocco or {}).get("base", _ASSENTE)
    if base is _ASSENTE:
        return next(iter(PRESETS)) if len(PRESETS) == 1 else None
    return base if base in PRESETS else None


def valori_autotune(panel):
    """I valori completi del profilo tarato: la base piu' il parametro misurato."""
    blocco = profilo_autotune(panel)
    if not blocco:
        return None
    fuori = {}
    base = base_autotune(blocco)
    if base:
        for nome, valore in PRESETS[base]["values"].items():
            fuori[nome] = dict(valore) if isinstance(valore, dict) else valore
    for nome, valore in (blocco.get("values") or {}).items():
        if isinstance(valore, dict) and isinstance(fuori.get(nome), dict):
            fuori[nome].update(valore)
        else:
            fuori[nome] = valore
    return fuori


def _valori(panel, key):
    """I valori che quella voce del menu scrive nel pannello."""
    if key == AUTOTUNE:
        return valori_autotune(panel)
    blocco = PRESETS.get(key)
    return blocco["values"] if blocco else None


def choices(panel=None):
    """(chiave, etichetta) per il menu, con la voce personalizzata in fondo."""
    fuori = [(key, blocco["label"]) for key, blocco in PRESETS.items()]
    fuori.sort(key=lambda voce: voce[1])
    tarato = profilo_autotune(panel)
    if tarato:
        fuori.append((AUTOTUNE, tarato.get("label") or "Autotune"))
    fuori.append((CUSTOM, "Personalizzata"))
    return fuori


def known(key, panel=None):
    if key == AUTOTUNE:
        return profilo_autotune(panel) is not None
    return key in PRESETS


def apply(panel, key):
    """Scrive nel pannello i valori del profilo. Restituisce True se applicato.

    `custom` non applica niente di proposito: sceglierlo vuol dire tenere i
    valori attuali e continuare a modificarli a mano.
    """
    if key == CUSTOM:
        panel["preset"] = CUSTOM
        return False
    valori = _valori(panel, key)
    if not valori:
        return False
    for nome, valore in valori.items():
        if isinstance(valore, dict):
            ramo = panel.setdefault(nome, {})
            ramo.update(valore)
        else:
            panel[nome] = valore
    panel["preset"] = key
    return True


def matches(panel, key):
    """Vero se il pannello ha esattamente i valori del profilo indicato."""
    valori = _valori(panel, key)
    if not valori:
        return False
    for nome, valore in valori.items():
        if isinstance(valore, dict):
            ramo = panel.get(nome) or {}
            if any(str(ramo.get(k, "")) != str(v) for k, v in valore.items()):
                return False
        elif panel.get(nome) != valore:
            return False
    return True


def detect(panel):
    """Che voce mostrare nel menu: **quella scelta**, se regge ancora.

    La regola e' una sola, e viene prima di tutto il resto: se l'utente ha
    scelto una voce e i valori sono ancora quelli, il menu mostra **quella
    voce**. Non un'altra che per caso ha gli stessi numeri.

    Serviva dirlo perche' la versione precedente faceva il contrario: cercava
    a chi somigliassero i valori, e rispondeva con il primo profilo che
    combaciava. Due conseguenze, tutte e due sbagliate.

    La prima, la piu' fastidiosa: si sceglieva «Personalizzata», si salvava,
    e al ricaricamento il menu diceva «FM6373 & DP32020B». Vero che i numeri
    erano quelli — «Personalizzata» non li cambia, e' il suo mestiere — ma la
    scelta dell'utente era sparita dallo schermo. E non era solo estetica:
    `api_panel` applica il profilo che vede nel menu **dopo** aver scritto i
    campi del modulo, quindi finche' li' c'era scritto un profilo di fabbrica
    ogni modifica a mano veniva riscritta al salvataggio successivo. Mostrare
    «Personalizzata» e' cio' che rende possibile modificare a mano.

    La seconda riguardava il profilo tarato: ha un parametro solo, e un
    parametro solo coincide con mezzo mondo — a cominciare dal profilo di
    fabbrica, che quel valore ce l'ha uguale.

    `matches` resta come rete: se i valori non corrispondono piu' alla voce
    scelta — qualcuno ha modificato un campo a mano — la scelta e' decaduta e
    si torna a riconoscere dai valori. Per `custom` non c'e' niente da
    verificare: e' la voce che dice «questi numeri li ho scelti io».
    """
    scelto = (panel or {}).get("preset")
    if scelto == CUSTOM:
        return CUSTOM
    if scelto == AUTOTUNE and matches(panel, AUTOTUNE):
        return AUTOTUNE
    if scelto in PRESETS and matches(panel, scelto):
        return scelto
    for key in PRESETS:
        if matches(panel, key):
            return key
    return CUSTOM


# ------------------------------------------------------------------ cablaggio

# Come i segnali arrivano al pannello. E' un fatto della macchina, non del
# pannello: lo stesso FM6373 si pilota tal quale con i fili diretti o con la
# Bonnet, cambiano solo i piedini. Per questo sta fuori dai profili.
#
# Non e' un interruttore acceso/spento perche' gli stati sono tre, e il terzo
# non e' deducibile dal software: la Bonnet con la modifica PWM (un ponticello
# a saldare fra GPIO 4 e GPIO 18) e quella senza sono la stessa scheda, e solo
# chi ha in mano il saldatore sa quale delle due ha davanti.
#
#   regular          i fili diretti sui GPIO, com'e' nato il progetto
#   adafruit-hat     Bonnet Adafruit cosi' com'e'. L'OE finisce sul GPIO 4,
#                    che non e' un piedino PWM: gli impulsi li fa il software,
#                    e si vede.
#   adafruit-hat-pwm Bonnet con GPIO 4 e GPIO 18 uniti a saldare. L'OE torna
#                    su un piedino PWM e il generatore di impulsi hardware si
#                    riprende il lavoro, come con i fili diretti.
CABLAGGIO_DIRETTO = "regular"
CABLAGGI = (CABLAGGIO_DIRETTO, "adafruit-hat", "adafruit-hat-pwm")


def cablaggio_valido(nome):
    """Un nome fuori elenco non si scrive: sbagliarlo spegne il pannello."""
    return nome in CABLAGGI


# ----------------------------------------------------------- registri forzati

# Il blocco di registro RGB si scrive come lista di parole esadecimali di
# quattro cifre separate da virgola — `0000,0100,023f,...` — uguale per i tre
# canali, oppure una lista per canale con la forma `R:...;G:...;B:...`.
#
# La validazione e' volutamente grossolana: qui non si sa cosa significhino
# quelle parole, si sa solo che forma hanno. Serve a fermare l'errore di
# battitura e l'incolla sbagliato, non a giudicare i valori — quelli li
# giudica il pannello.
_PAROLA = re.compile(r"^[0-9a-fA-F]{4}$")


def registri_validi(testo):
    """Vero se il testo ha la forma di un blocco di registro (o e' vuoto).

    Vuoto e' valido e significa "usa il profilo": deve poter tornare indietro
    svuotando il campo, senza dover ricordare cosa c'era prima.
    """
    testo = (testo or "").strip()
    if not testo:
        return True
    for pezzo in testo.split(";"):
        pezzo = pezzo.strip()
        if not pezzo:
            continue
        if ":" in pezzo:
            etichetta, _, pezzo = pezzo.partition(":")
            if etichetta.strip().upper() not in ("R", "G", "B"):
                return False
        parole = [p.strip() for p in pezzo.split(",") if p.strip()]
        if not parole or not all(_PAROLA.match(p) for p in parole):
            return False
    return True


def normalizza_registri(testo):
    """Riscrive il blocco in forma pulita: niente spazi, niente virgole vuote.

    Quello che si salva e' quello che finisce nel chip: una virgola di troppo
    battuta per sbaglio non deve arrivare fin la' e farci poi chiedere perche'
    il pannello si comporta in modo strano.
    """
    testo = (testo or "").strip()
    if not testo:
        return ""
    fuori = []
    for pezzo in testo.split(";"):
        pezzo = pezzo.strip()
        if not pezzo:
            continue
        etichetta = ""
        if ":" in pezzo:
            etichetta, _, pezzo = pezzo.partition(":")
            etichetta = etichetta.strip().upper() + ":"
        parole = [p.strip().lower() for p in pezzo.split(",") if p.strip()]
        fuori.append(etichetta + ",".join(parole))
    return ";".join(fuori)
