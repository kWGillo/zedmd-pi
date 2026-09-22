---
title: "Kingo Bongo"
subtitle: "Due gorilla sui tetti, una banana, il vento: tu contro il computer"
---

# 1. Da dove viene

Con il DOS 5 arrivava un gioco in QBasic: due gorilla in piedi sui palazzi di
una città di notte si lanciavano banane esplosive, scegliendo angolo e
velocità, con il vento di mezzo. Il nome e il disegno erano di chi l'aveva
scritto e restano suoi. Lo schema — un tiro a parabola per volta, il vento, i
palazzi che si bucano — non è di nessuno. Questo è **Kingo Bongo**, con
città, gorilla e musica disegnati e scritti per il pannello.

# 2. Il campo

Tutto il pannello sotto una riga di tabellone. La città cambia a ogni
ripresa: palazzi di larghezza e altezza a caso, con le finestre accese qua e
là e qualche stella sopra. Tu sei il gorilla arancio a sinistra, il computer
quello grigio a destra.

Le altezze dei palazzi si estraggono a caso e poi **si abbassano tutte
insieme**, finché il più basso del quadro non resta alto due o tre righe di pixel: quello che
conta in un tiro a parabola è il dislivello fra un tetto e l'altro, non
quanto è alta la città, e così sopra resta cielo libero per la banana.

A ogni ripresa la città **entra dall'alto e si abbassa** fino al suo posto,
in poco più di un secondo. Il punto di vista è fermo — la strada resta
l'ultima riga e le stelle non si muovono — sono i palazzi a scendere, con i
gorilla sopra i loro tetti, come se l'inquadratura scoprisse la città
dall'alto. Mentre scende non si mira e non si tira; il computer, intanto,
sceglie già il suo tiro.

I palazzi sono **contorni con le finestre**, non blocchi pieni: su un'area
grande di colore basso il pannello mostra le righe del refresh (la lezione di
Squadriglia e Gnam Gnam). Quando una banana colpisce un palazzo ci fa un
**buco**, e il contorno lo segue: i buchi restano fino alla fine della
ripresa, e cambiano i tiri successivi.

Il tabellone, da sinistra: punteggio, record, **angolo e velocità** del tiro
(arancio i tuoi, grigi quelli del computer mentre sceglie), la **freccia del
vento** (lunga quanto soffia, verso dove soffia; un punto se non c'è vento),
il livello e le riprese vinte, TU contro CPU.

# 3. I comandi

Nell'originale angolo e velocità si scrivevano con la tastiera. Qui ci sono un
pad e la pulsantiera della pagina Giochi, quindi:

| Comando | Pad | Tastiera |
|---|---|---|
| angolo **+1 / -1** | su / giù | frecce su e giù, W S |
| velocità **+1 / -1** | destra / sinistra | frecce destra e sinistra, A D |
| **lanciare** | **X** (o cerchio, quadrato, R1, R2) | spazio, Ctrl, Alt |
| uscire | **Share/Select** | Esc |

Un tocco cambia il numero di uno. **Tenendo premuto** il numero corre, sempre
più svelto: da 45 a 80 gradi ci vuole un secondo e mezzo. L'angolo va da 0
a 90 gradi, la velocità da 5 a 100. Tra un tiro e l'altro i numeri restano
dove li hai lasciati: si corregge, non si ricomincia.

Davanti al tuo gorilla una **linea tratteggiata** mostra la direzione del
tiro, più lunga quanto più forte. Un triangolino lampeggia sopra il gorilla a
cui tocca.

Se la banana esce dal pannello in alto, un puntino giallo sulla prima riga
mostra dove sta: ricadrà lì sotto.

# 4. La fisica

Una parabola, con la gravità e il vento. A 45 gradi e velocità 60 il tiro fa
circa 130 pixel, metà pannello; il vento spinge la banana di lato per tutto
il volo, quindi pesa di più sui tiri alti e lenti. Il vento cambia a ogni
ripresa e resta uguale per tutti i tiri della ripresa.

# 5. Il computer

Fa come farebbe una persona: sceglie un angolo, di solito un tiro teso, e ci
prova. Il **primo tiro è largo**, poi si corregge, e a ogni tiro sbaglia meno
— di circa un terzo ogni volta. Quanto è largo il primo tiro dipende dal
**livello**: a ogni partita che vinci, il computer ne comincia una nuova più
preciso.

Sotto, il computer calcola davvero i tiri con la stessa fisica della banana
vera, palazzi e buchi compresi. Il ragionamento è diviso in piccoli pezzi,
qualche tiro di prova per fotogramma, mentre sul tabellone scorrono i numeri
che sta scegliendo: il pannello non si ferma mai.

# 6. Riprese, partite, punti

- Vince la **ripresa** chi colpisce l'altro gorilla. Chi colpisce **se
  stesso** la regala all'avversario, come nell'originale.
- La ripresa dopo comincia chi ha perso l'ultima. La prima la cominci tu.
- Alla **terza ripresa** vinta la partita è tua: 2000 punti, **livello** in
  più, e si ricomincia da 0 a 0 con il computer più bravo.
- Se le tre riprese le vince il computer, è **GAME OVER**.

| Cosa | Punti |
|---|---|
| ripresa vinta | 1000 |
| tiri risparmiati | 250 per ogni tiro sotto i quattro (al primo colpo: 750) |
| partita vinta | 2000 |

# 7. Suoni e musica

Il lancio, il tonfo sul palazzo, l'esplosione del gorilla, il segnale della
ripresa vinta o persa e della partita vinta. Sotto, un motivo originale in la
minore con i tamburi, a botta e risposta; la casella **Musica di sottofondo
nei giochi** della pagina Giochi lo spegne.

# 8. Come è stato provato

Le prove controllano i comandi (il tocco, la corsa tenendo premuto, i
limiti), la città (larghezza, gorilla sui tetti, i buchi), la fisica (una
parabola senza vento torna alla gittata teorica, il vento sposta), il
computer (senza errore colpisce in almeno 17 città su 20), le riprese, il
colpo su se stessi, la partita vinta e persa e la ripartenza. Poi fanno
giocare partite intere a un pilota che mira bene ma sbaglia la velocità di
qualche unità: con un errore piccolo arriva a livelli alti, con uno grande
perde la prima partita. Il fotogramma peggiore, mentre il computer ragiona,
costa meno di due millisecondi sul computer di prova.

