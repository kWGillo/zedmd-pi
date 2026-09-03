# -*- coding: utf-8 -*-
"""Lanciare un processo che deve sopravvivere al riavvio del servizio.

Il problema, che e' costato una taratura
----------------------------------------
Due cose in questo progetto riavviano il servizio `dmd` mentre stanno
lavorando: l'aggiornamento via rete, che riavvia per verificare di essere
ripartito, e la taratura, che riavvia a ogni configurazione perche' la
libreria matrice legge i parametri una volta sola, alla costruzione.

Tutte e due girano in un processo separato, e fin qui e' giusto. Il punto e'
**come** lo si separa. `start_new_session=True` stacca il processo dal
terminale e dal gruppo di processi, e sembra abbastanza: non lo e'. Il figlio
resta nel **cgroup** del servizio, e `systemctl restart` con il `KillMode`
predefinito — `control-group` — ammazza tutto quello che sta nel cgroup, non
solo il processo principale.

Risultato: la taratura lanciata dalla pagina web moriva al primo riavvio,
cioe' dopo pochi secondi, lasciando il pannello sul primo valore di prova e
un file di stato fermo a "0 su 10". Da fuori sembrava che stesse lavorando.

Non era emerso prima perche' l'aggiornamento via rete lo lanciavamo sempre da
SSH: quel processo nasce nel cgroup della sessione ssh, non del servizio, e
sopravvive. Lo stesso aggiornamento fatto **dal pulsante** nella pagina web
sarebbe morto allo stesso modo — nel momento peggiore, con `/opt/dmd` gia'
riscritto a meta' e il ripristino automatico mai eseguito.

La soluzione
------------
`systemd-run` crea un'unita' transitoria: un cgroup suo, fuori da quello del
servizio. Da li' nessun `systemctl restart dmd` lo puo' toccare.

Se `systemd-run` non c'e' — non e' un systemd, e' un contenitore, e' una
prova — si ripiega su `Popen` staccato, che e' quello di prima: meglio di
niente, e nelle prove il servizio non viene riavviato davvero.
"""

import os
import shutil
import subprocess
import time


def disponibile():
    """Vero se si puo' davvero uscire dal cgroup del servizio."""
    return bool(shutil.which("systemd-run"))


def lancia(args, nome):
    """Avvia `args` fuori dal cgroup del servizio.

    `nome` diventa il nome dell'unita' transitoria, con un numero in coda
    perche' due tarature avviate nella stessa giornata non si contendano lo
    stesso nome. `--collect` fa sparire l'unita' da sola quando finisce,
    anche se e' finita male: senza, resterebbe li' in stato "failed" e la
    volta dopo il nome sarebbe occupato.

    Restituisce True se e' partita come unita' transitoria, False se si e'
    dovuto ripiegare sul processo figlio.
    """
    if disponibile():
        unita = "%s-%d" % (nome, int(time.time()))
        completo = ["systemd-run", "--collect", "--quiet",
                    "--unit=%s" % unita] + list(args)
        try:
            esito = subprocess.run(completo, capture_output=True, timeout=30)
            if esito.returncode == 0:
                return True
        except (OSError, subprocess.SubprocessError):
            pass
    subprocess.Popen(list(args), start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return False
