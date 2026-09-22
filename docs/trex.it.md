---
title: "T-Rex"
subtitle: "La corsa del dinosauro: salta i cactus, abbassati sotto gli pterodattili"
---

# 1. Il nome e il disegno

Il gioco che il browser mostra quando manca la rete ha un dinosauro suo,
disegnato da altri, e resta loro. Lo schema — una corsa infinita, un tasto per
saltare, uno per abbassarsi, la velocità che cresce — non è di nessuno.
Questo **T-Rex** è disegnato per il pannello, pixel per pixel: più tozzo, a
colori, con le creste arancio sulla schiena e la pancia chiara.

# 2. Il pannello

La corsa è orizzontale, e il 4:1 è il formato giusto: 256 pixel di pista sono
più di due secondi di anticipo per vedere arrivare un ostacolo alla velocità
di partenza. Il tabellone sta in una riga in alto — punteggio, record,
livello — e la pista prende tutto il resto.

Il cielo è **nero**: un'area grande di colore basso, sul pannello, mostra le
righe del refresh (è la lezione di Squadriglia). Per questo il giorno e la
notte non si fanno invertendo i colori come nell'originale, ma cambiando la
tavolozza: di notte escono la luna e le stelle, e il dinosauro, i cactus e la
pista si fanno più freddi.

# 3. I comandi

| Comando | Pad | Tastiera |
|---|---|---|
| **saltare** | **X**, **cerchio**, su | spazio, Ctrl, Alt, freccia su, W |
| **abbassarsi** | giù (croce o levetta) | freccia giù, S |
| uscire | **Share/Select** | Esc |

**Il salto è più alto se tieni premuto**: un colpo secco fa un salto corto,
che basta per un cactus piccolo; tenendo il tasto il dinosauro sale di più,
e serve per i gruppi di cactus grandi quando si va veloci. Tenendo premuto
anche dopo l'atterraggio si risalta subito.

**Giù** a terra abbassa il dinosauro, lungo e basso, per passare sotto gli
pterodattili a mezza altezza. In aria lo fa ricadere in picchiata: utile
quando si è saltato troppo presto.

Fuoco fa anche cominciare e rigiocare (a partita finita, dopo mezzo secondo:
il salto che ti ha fatto perdere non deve farti ripartire).

# 4. Gli ostacoli

| Ostacolo | Da quando | Come si passa |
|---|---|---|
| cactus piccolo, da uno a tre | subito (i gruppi da un po' di velocità) | un salto |
| cactus grande, uno o due | da un po' di velocità | un salto, tenuto se sono due |
| pterodattilo **basso** | 300 punti | un salto |
| pterodattilo **medio** | 300 punti | abbassarsi (o un salto alto) |
| pterodattilo **alto** | 300 punti | niente: passa sopra, ma non saltarci dentro |

Gli pterodattili volano: vanno un poco più svelti della pista. Lo spazio fra
un ostacolo e l'altro cresce con la velocità, perché anche il salto, in
pixel, diventa più lungo.

Gli urti sono **al pixel**: conta la sagoma, non un rettangolo attorno. Una
coda che sfiora la punta di un cactus non è un urto se i pixel non si toccano.

# 5. Velocità, punti, giorno e notte

- Si parte a 110 pixel al secondo e si accelera piano, fino a 260.
- Circa otto punti al secondo alla partenza, di più andando veloci.
- Ogni **100 punti** un segnale: il punteggio lampeggia e suona.
- Ogni **500 punti** un gradino di livello sul tabellone.
- Da **700 punti** arriva la notte, e dura 250 punti; poi torna il giorno, e
  di nuovo notte ogni 700.
- Una vita sola, come nell'originale. Il record resta, come in tutti i giochi.

# 6. Suoni e musica

Un blip che sale a ogni salto, il segnale dei 100 punti e il suono della
partita persa. Sotto, un motivo originale in sol maggiore, saltellante, a
ottavi ribattuti; la casella **Musica di sottofondo nei giochi** della pagina
Giochi lo spegne.

# 7. Come è stato provato

Le prove controllano ogni regola da sola — il salto corto e quello tenuto, la
picchiata, l'abbassarsi, gli urti con ogni ostacolo e a ogni quota, il game
over e la ripartenza, giorno e notte — e poi fanno correre un pilota
automatico con un ritardo di reazione casuale: con un errore di qualche
centesimo di secondo arriva in fondo quasi sempre, con un decimo muore fra i
cento e i quindicimila punti, come una persona. Un fotogramma costa una
frazione di millisecondo.

