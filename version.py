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
  1.7  Interfaccia web in italiano e inglese, con la lingua rilevata dal
       browser e un selettore in ogni pagina; link al progetto su GitHub nel
       piede di pagina.
  1.7.1 Un errore dell'interfaccia web non ferma piu' il servizio: il pannello
        resta acceso e il motivo finisce nel log invece di far riavviare il
        processo all'infinito.
  1.7.2 Impronte md5 di tutti i file e verifica automatica prima e dopo la
        copia: un file arrivato corrotto viene riconosciuto subito, per nome,
        invece di far fallire l'avvio senza spiegazioni.
  1.8  Esportazione e importazione della configurazione dalla web UI, con
       esclusione facoltativa delle coordinate del radar. La taratura del
       pannello, trovata per tentativi, non dipende piu' dalla scheda SD.
  1.9  Rolling banner: dieci testi scorrevoli con colore, dimensione,
       velocita' e lampeggio propri, a comparsa periodica. Controllo degli
       aggiornamenti della libreria della matrice, senza installazione
       automatica.
  1.9.1 L'aggiornamento via rete installa i file dichiarati dall'archivio
        scaricato, non quelli elencati nel codice gia' installato: una
        versione che aggiunge un file non lo lasciava indietro. Controllo
        dei file mancanti prima del riavvio e ripristino anche quando a
        fallire e' la copia.
  1.9.2 Il controllo della libreria funziona anche quando la cartella
        appartiene all'utente e il servizio gira come root: git rifiutava il
        repository con "dubious ownership".
  1.9.3 Il riquadro "Ora e sincronizzazione" passa dalla pagina Impostazioni
        a quella dell'Orologio, sotto le impostazioni di aspetto: le due cose
        si regolano insieme.
"""

__version__ = "1.9.3"
