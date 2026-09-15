# -*- coding: utf-8 -*-
"""Fermare il tempo a un processo esterno, senza ucciderlo.

Serve alla sveglia. Doom e il Game Boy non sono codice nostro: girano come
processi a se', e ognuno ha un thread che ne svuota la pipe dei fotogrammi in
continuazione. Quando il pannello passa a qualcun altro loro **non si fermano**
— continuano a giocare da soli, e chi torna si trova morto.

I giochi scritti per il pannello si fermano con una variabile, perche' il loro
ciclo e' nostro. Per un processo esterno la variabile non c'e', e il sistema
operativo offre esattamente lo strumento giusto: `SIGSTOP` lo sospende, e
`SIGCONT` lo fa ripartire da dov'era, con la memoria intatta e senza che il
programma debba saperne niente.

Un limite da dire a voce alta
-----------------------------
Un processo sospeso **non chiude i file che teneva aperti**, scheda audio
compresa. Se Doom sta suonando quando la sveglia scatta, la scheda resta sua e
la sveglia non puo' suonarci sopra: il pannello lampeggia, ma il suono no.

Non e' un difetto introdotto qui — succedeva gia' prima, e senza nemmeno il
congelamento — ed e' scritto nella documentazione invece che risolto, perche'
l'unico modo di liberare quella scheda sarebbe chiudere la partita. Fra una
sveglia muta e una partita persa, la partita vale di piu': il lampeggio si
vede, e chi cucina guarda il pannello.
"""

import os
import signal


def sospendi(proc):
    """Ferma il processo. (fatto, motivo).

    `proc` e' un `subprocess.Popen` o None. Un processo gia' morto non e' un
    errore da segnalare: e' semplicemente niente da fermare.
    """
    return _segnale(proc, signal.SIGSTOP, "sospeso")


def riprendi(proc):
    """Fa ripartire il processo. (fatto, motivo)."""
    return _segnale(proc, signal.SIGCONT, "ripreso")


def _segnale(proc, segnale, cosa):
    if proc is None or proc.poll() is not None:
        return False, ""
    try:
        os.kill(proc.pid, segnale)
    except (OSError, ProcessLookupError) as exc:
        return False, str(exc)
    return True, cosa
