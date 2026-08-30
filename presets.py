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
            "hardware_mapping": "regular",
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


def choices():
    """(chiave, etichetta) per il menu, con la voce personalizzata in fondo."""
    fuori = [(key, blocco["label"]) for key, blocco in PRESETS.items()]
    fuori.sort(key=lambda voce: voce[1])
    fuori.append((CUSTOM, "Personalizzata"))
    return fuori


def known(key):
    return key in PRESETS


def apply(panel, key):
    """Scrive nel pannello i valori del profilo. Restituisce True se applicato.

    `custom` non applica niente di proposito: sceglierlo vuol dire tenere i
    valori attuali e continuare a modificarli a mano.
    """
    if key == CUSTOM:
        panel["preset"] = CUSTOM
        return False
    blocco = PRESETS.get(key)
    if not blocco:
        return False
    for nome, valore in blocco["values"].items():
        if isinstance(valore, dict):
            ramo = panel.setdefault(nome, {})
            ramo.update(valore)
        else:
            panel[nome] = valore
    panel["preset"] = key
    return True


def matches(panel, key):
    """Vero se il pannello ha esattamente i valori del profilo indicato."""
    blocco = PRESETS.get(key)
    if not blocco:
        return False
    for nome, valore in blocco["values"].items():
        if isinstance(valore, dict):
            ramo = panel.get(nome) or {}
            if any(str(ramo.get(k, "")) != str(v) for k, v in valore.items()):
                return False
        elif panel.get(nome) != valore:
            return False
    return True


def detect(panel):
    """Il profilo a cui corrisponde la configurazione attuale, o `custom`."""
    for key in PRESETS:
        if matches(panel, key):
            return key
    return CUSTOM
