# Taratura automatica del pannello

Il DMD misura sé stesso e ti dice quale configurazione conviene. Serve a
sostituire il metodo che abbiamo usato per settimane — cambia un parametro,
guarda il pannello, decidi se sembra meglio — che con un difetto casuale non
distingue un miglioramento vero da una serie fortunata.

---

## 1. Che cosa misura, e perché si può misurare

La libreria che pilota la matrice scrive nel log il refresh di **ogni
fotogramma**. In regime il valore sta fermo — 29,3 Hz, sempre quello — e ogni
tanto crolla.

Un tuffo a 18,6 Hz vuol dire un fotogramma durato 53 millisecondi invece di
34: diciannove millisecondi passati ad aspettare la memoria. E se quei
millisecondi cadono mentre una riga del pannello è accesa, quella riga resta
accesa venti volte più del dovuto.

**È la riga chiara.** Non un'ipotesi ricostruita guardando il pannello: un
numero che il pannello stesso scrive, fotogramma per fotogramma. Contare i
tuffi è contare il difetto.

> Il valore nel log si vede solo con `journalctl -a`. La libreria lo riscrive
> sulla stessa riga con un ritorno a capo, come una barra di avanzamento:
> journald riceve un messaggio senza fine riga, decide che è binario e mostra
> `[29.8K blob data]`. È il genere di cosa che fa credere per mesi che
> un'opzione non funzioni.

---

## 2. La soglia è relativa, e non è un dettaglio

Un fotogramma è **disturbato** se sta più del 5% sotto il *regime della sua
configurazione* — il massimo della finestra, cioè il valore che il pannello
tiene quando nessuno lo disturba. **Grave** se sta più del 10% sotto.

Le due colonne dicono cose diverse. La prima vede anche il *tremolio*, cioè
una configurazione che oscilla di suo; la seconda solo i *tuffi* veri.
Distinguerli conta: una configurazione può avere il refresh più alto di tutte
e tremolare, e allora non va bene lo stesso.

La soglia non può essere fissa in Hz. La prima versione lo era — 28 Hz — e
appena lo sweep ha cominciato a muovere il refresh stesso ha dichiarato il
**100%** dei fotogrammi disturbati su una configurazione che girava a 25,9:
stava misurando «la media sta sotto 28?», non «ci sono tuffi?».

---

## 3. I fotogrammi contaminati

Ogni richiesta alla web UI è Python che lavora e rete che si muove, cioè
**esattamente il disturbo che stiamo misurando**. È misurato: con la scheda SD
sotto carico i fotogrammi disturbati passano dallo 0,95% all'8,90%.

Spegnere l'interfaccia durante la taratura non si può — servirebbe per farla
partire e per leggerne i risultati. Quindi si fa l'altra cosa: durante ogni
finestra si **conta** il traffico, e le finestre sporcate si dichiarano e si
buttano. Una misura sporca dichiarata vale più di una misura che credi pulita.

Per la stessa ragione **la pagina non si aggiorna da sola**. Non è una
dimenticanza: un auto-refresh genererebbe da solo il disturbo da contare.
Aggiorni a mano quando vuoi, e la misura in corso verrà marcata come
contaminata — il che è meglio che falsarla di nascosto.

---

## 4. Come si usa

Nella pagina **Taratura**:

1. scegli il parametro (il rallentamento GPIO è quello che conta di più);
2. scrivi i valori da provare, separati da virgola;
3. scegli quanti minuti per misura e quanti giri.

Due minuti danno circa 3.000 campioni, cioè un fotogramma per fotogramma: sono
abbastanza perché una frazione dello 0,1% si distingua dal caso.

**I giri servono.** Misurare le configurazioni in fila attribuisce alla prima
tutto il rumore del suo momento: è successo davvero, venti fotogrammi
disturbati subito dopo un aggiornamento, con la scheda ancora occupata a
smaltire le scritture. Con due giri le configurazioni si alternano e il rumore
si spalma su tutte.

Cinque valori per due giri, due minuti l'uno, fanno una quarantina di minuti.
Il pannello si riavvia a ogni configurazione: è normale.

---

## 5. La regola con cui sceglie

> Fra le configurazioni che si disturbano di meno, quella con il **refresh più
> alto**.

Non la più veloce e basta: il valore col refresh nominale più alto può essere
quello che gira al limite e tremola. E non la più tranquilla e basta, che
sarebbe sempre la più lenta.

Mezzo punto percentuale di tolleranza sul minimo, perché fra lo 0,07% e lo
0,18% non c'è differenza vera e pretendere il minimo esatto vuol dire farsi
guidare dal rumore.

La tabella resta lì: se non sei d'accordo col consiglio, applichi la riga che
preferisci.

---

## 6. Che cosa si può tarare, e che cosa no

| Parametro | Che cosa fa |
|---|---|
| Rallentamento GPIO | La leva vera del refresh. Più basso = più Hz, ma sotto un certo punto il ciclo non ha più margine per assorbire i disturbi. |
| Profondità PWM | Su un pannello S-PWM la modulazione la fa il chip: qui quasi non muove il refresh. |
| Durata bit minimo | Accorcia ogni sotto-frame. Sotto gli 80 ns i toni scuri diventano imprecisi. |
| Bit con dithering | Alza il refresh a parità di profondità dichiarata, con un po' di brulichio sulle sfumature. |

Geometria, tipo di chip e cablaggio **non** si tarano: non sono una
regolazione, sono la dichiarazione di che pannello si ha e come è collegato.
Stanno nei profili.

---

## 7. Il profilo «Autotune»

Applicando un risultato, il valore viene scritto nel pannello e salvato come
profilo, che compare fra gli altri nella pagina Impostazioni. Serve a poterci
tornare: la taratura andrà rifatta con un'altra scheda SD o un altro carico,
perché dipende da **questa macchina**, non dal tipo di pannello — ed è la
ragione per cui non sta fra i profili di fabbrica.

Il profilo contiene **solo il parametro tarato**. Una taratura non ha misurato
righe, colonne e tipo di chip, e non deve riscriverli: un profilo che riscrive
tutto spegnerebbe il pannello.
