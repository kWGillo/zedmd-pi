"""Versione del DMD Controller.

Storico:
  1.0  Prima versione: ricevitore ZeDMD-WiFi, orologio, web UI.
  1.1  Colori di ora e data separati, formato 12/24h, lingua dei giorni,
       Media Player separato dall'orologio con foto e video a rotazione,
       Night mode e Sleep mode, condivisione SMB e upload da web.
  1.1.1 update.sh: installa ffmpeg e samba in modo indipendente.
  1.2  Regolazioni fini del driver S-PWM dalla web UI, per eliminare i lampi
       orizzontali; riavvio del servizio dall'interfaccia.
  1.3  Air Radar: informazioni degli aerei in transito entro un raggio da una
       coordinata GPS, tramite le API pubbliche ADS-B della comunita'.
  1.3.1 Nessuna coordinata preimpostata: la posizione resta solo nella
        configurazione locale, mai nel codice distribuito.
  1.4  Air Radar: scelta dei parametri di volo da mostrare e registro CSV dei
       passaggi, scaricabile dalla web UI.
  1.5  Aggiornamento via rete dal repository GitHub, con verifica preventiva
       dell'archivio e ripristino automatico se il servizio non riparte.
  1.5.1 Air Radar: la rotta veniva cercata solo se era attiva una seconda
        casella, ora rimossa; ricerca su hexdb.io piu' robusta.
  1.5.2 Le rotte arrivano dal servizio routeset di adsb.lol, in blocco e con
        codici IATA; prova diagnostica nella pagina Radar; pulsanti separati
        nella pagina Media.
  1.6  L'elenco della libreria media viene tenuto in memoria invece di
       rileggere il disco a ogni contenuto e a ogni richiesta della web UI:
       con librerie molto grandi la scansione continua occupava CPU e scheda
       SD e si vedeva come righe bianche sul pannello.
"""

__version__ = "1.6"
