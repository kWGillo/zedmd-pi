# Il font dell'orologio

`DejaVuSansMono-Bold.ttf`, versione 2.37, la stessa che Debian distribuisce.

## Perché sta qui dentro

L'orologio è disegnato sulle larghezze di questo font. Non è una preferenza
estetica: è a larghezza fissa, quindi `11:11` e `20:38` occupano lo stesso
spazio, e un orologio centrato non si sposta a ogni minuto. I due punti e lo
spazio occupano la stessa cella, e il lampeggio non muove le cifre.

Fino a Debian 12 il font stava in `fonts-dejavu-core`, che
`install.sh` ha sempre installato. Dalla 13 le facce monospaziate sono in un
pacchetto a parte, `fonts-dejavu-mono`, e su quelle macchine ci si ritrovava
senza — con il ripiego su `DejaVuSans-Bold`, che è proporzionale. Il difetto
che ne è venuto fuori è raccontato nella 17.3.3: *«quando i due punti
scompaiono, l'ultima cifra si sposta a sinistra di qualche pixel»*.

Il programma adesso regge qualunque font, ma le proporzioni giuste sono
queste, e una copia nel progetto è l'unico modo per averle **senza chiedere
niente alla rete** — né al momento dell'installazione, né fra cinque anni,
quando un indirizzo che oggi risponde potrebbe non rispondere più.

## In che ordine si cerca

In `sources/clock.py`, `FONT_CANDIDATES`:

1. `/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf` — quello di
   sistema, se c'è: lo aggiorna la distribuzione, ed è giusto che vinca;
2. questa copia, accanto al programma;
3. `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf` — proporzionale,
   l'ultima spiaggia.

`install.sh` prova comunque `fonts-dejavu-mono` da apt, e se non riesce
installa questa copia in `/usr/local/share/fonts/dmd/`, così ce l'ha anche
il resto della macchina.

## Licenza

Bitstream Vera Fonts Copyright © 2003 Bitstream, Inc., con le modifiche
DejaVu in pubblico dominio. Il testo completo è in `LICENZA-DejaVu.txt`, e
dice espressamente che il font si può ridistribuire, anche dentro un altro
programma. Fonte: <https://dejavu-fonts.github.io/>
