# -*- coding: utf-8 -*-
"""17.0 - Che macchina e' questa, e cosa cambia di conseguenza.

Fino alla 16.5 nel progetto non esisteva **nessun** rilevamento di
piattaforma: non c'era bisogno, perche' la macchina era una sola. Dalla 17.0
la risposta decide tre cose, e questa prova le guarda tutte e tre:

1. **se offrire il pannello LED.** Solo Pi 3 e 4: la libreria matrice pilota
   il blocco PWM del BCM, sul Pi 5 il controller GPIO e' un altro (RP1) e la
   libreria non lo supporta, e su un PC il modulo non c'e' nemmeno;
2. **quali schede audio rimandare in seconda fila.** Sul Raspberry hdmi,
   bcm2835 e headphones si scartano perche' *non possono* suonare -- nessun
   cavo HDMI, e il jack usa lo stesso PWM della matrice. Su un PC sono quello
   che c'e', e scartarle vorrebbe dire DMD muto;
3. **che uscita video scegliere** quando nessuno l'ha scelta.

Il modo di leggere la macchina e' quello che la macchina dice di se':
`/proc/device-tree/model`, e `/proc/cpuinfo` come riserva. Non
l'architettura: un Pi 4 a 64 bit e un PC ARM rispondono la stessa cosa, e la
domanda vera non e' "che processore e'" ma "c'e' un pannello che posso
pilotare".
"""

import os
import sys
import tempfile

os.environ.setdefault("DMD_DATA", tempfile.mkdtemp())
os.environ.setdefault("DMD_CONFIG", os.path.join(tempfile.mkdtemp(), "config.json"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import piattaforma
import suoni

esiti = []


def esigi(condizione, messaggio):
    esiti.append((bool(condizione), messaggio))
    print("%s %s" % ("OK  " if condizione else "FALLITO", messaggio))


def sep(titolo):
    print()
    print("=" * 74)
    print(titolo)
    print("=" * 74)


sep("1. Il numero di modello, da quello che la macchina dice di se'")

CASI = [
    ("Raspberry Pi 4 Model B Rev 1.4", "4", True),
    ("Raspberry Pi 3 Model B Plus Rev 1.3", "3", True),
    ("Raspberry Pi 3 Model A Plus Rev 1.0", "3", True),
    ("Raspberry Pi Compute Module 4 Rev 1.1", "4", True),
    ("Raspberry Pi 5 Model B Rev 1.0", "5", False),
    ("Raspberry Pi 2 Model B Rev 1.1", "2", False),
    ("Raspberry Pi Zero 2 W Rev 1.0", "", False),
    ("Raspberry Pi 400 Rev 1.0", "400", False),
    ("Intel(R) Core(TM) i5-8250U CPU @ 1.60GHz", "", False),
    ("", "", False),
]
for testo, numero, pannello in CASI:
    esigi(piattaforma._numero(testo) == numero,
          "%r -> numero %r" % (testo[:40], numero))
    esigi((piattaforma._numero(testo) in piattaforma.PANNELLO_SU) == pannello,
          "   pannello: %s" % ("si" if pannello else "no"))

esigi(piattaforma._numero("Raspberry Pi Compute Module 4") == "4",
      "il Compute Module 4 e' un Pi 4: il numero arriva dopo due parole, e "
      "li' i GPIO ci sono")
esigi(piattaforma._numero("Raspberry Pi 5") not in piattaforma.PANNELLO_SU,
      "il Pi 5 no: il controller GPIO e' l'RP1 e la libreria non lo pilota")


sep("2. Una macchina che non dice niente e' un PC, non un Raspberry")

vero_modello = piattaforma.modello
piattaforma.modello = lambda: ""
try:
    muta = piattaforma._leggi()
finally:
    piattaforma.modello = vero_modello
piattaforma._forza(muta)
esigi(piattaforma.famiglia() == piattaforma.PC,
      "un container o una macchina virtuale: la scelta prudente porta al "
      "monitor, non a pilotare GPIO che non ci sono")
esigi(piattaforma.pannello_possibile() is False,
      "e il pannello non si offre")


sep("3. Le tre risposte, macchina per macchina")

def finge(famiglia, modello, numero, pannello):
    piattaforma._forza({"famiglia": famiglia, "modello": modello,
                        "numero": numero, "pannello": pannello})


finge(piattaforma.PI, "Raspberry Pi 4 Model B", "4", True)
esigi(piattaforma.pannello_possibile() is True, "Pi 4: pannello si")
esigi(piattaforma.audio_interno_va_bene() is False,
      "Pi 4: l'audio interno no -- niente cavo HDMI, e il jack usa il PWM "
      "della matrice")
esigi(suoni._interne() == suoni._INTERNE_PI,
      "Pi 4: si scartano hdmi, bcm2835 e headphones")
esigi("Raspberry" in piattaforma.nome(), "e il nome si legge (%s)"
      % piattaforma.nome())

finge(piattaforma.PI, "Raspberry Pi 5 Model B", "5", False)
esigi(piattaforma.pannello_possibile() is False, "Pi 5: pannello no")
esigi(piattaforma.audio_interno_va_bene() is False,
      "Pi 5: resta un Raspberry, l'audio si comporta da Raspberry")

finge(piattaforma.PC, "HP EliteDesk 800", "", False)
esigi(piattaforma.pannello_possibile() is False, "PC: pannello no")
esigi(piattaforma.audio_interno_va_bene() is True,
      "PC: l'audio interno e' quello che c'e'")
esigi(suoni._interne() == suoni._INTERNE_PC,
      "PC: si rimanda in seconda fila il solo HDMI")


sep("4. La scheda audio scelta, su un PC e su un Raspberry")

SCHEDE = [
    {"indice": 0, "alsa": "plughw:0,0", "nome": "Dummy", "finta": True},
    {"indice": 1, "alsa": "plughw:1,0", "nome": "HDA Intel PCH ALC269",
     "finta": False},
    {"indice": 2, "alsa": "plughw:2,0", "nome": "vc4hdmi0 HDMI", "finta": False},
]
vero_dispositivi = suoni.dispositivi


def con(schede):
    def elenco():
        fuori = []
        for d in schede:
            voce = dict(d)
            voce["interna"] = suoni._interna(voce["nome"], "")
            fuori.append(voce)
        return fuori
    suoni.dispositivi = elenco


try:
    finge(piattaforma.PC, "PC", "", False)
    con(SCHEDE)
    esigi(suoni.uscita({"audio": {"device": ""}}) == "plughw:1,0",
          "su un PC con codec integrato e HDMI si sceglie il codec: l'HDMI "
          "suona solo se il monitor ha gli altoparlanti")

    con([SCHEDE[0], SCHEDE[2]])
    esigi(suoni.uscita({"audio": {"device": ""}}) == "plughw:2,0",
          "ma se l'HDMI e' l'unica cosa che c'e', si usa quella")

    con(SCHEDE + [{"indice": 3, "alsa": "plughw:3,0", "nome": "USB Audio",
                   "finta": False}])
    esigi(suoni.uscita({"audio": {"device": ""}}) == "plughw:3,0",
          "e una chiavetta USB appena infilata passa davanti, come sul Pi")

    finge(piattaforma.PI, "Raspberry Pi 4", "4", True)
    con([SCHEDE[0], {"indice": 1, "alsa": "plughw:1,0", "nome": "USB Audio",
                     "finta": False}, SCHEDE[2]])
    esigi(suoni.uscita({"audio": {"device": ""}}) == "plughw:1,0",
          "sul Pi la USB vince sull'HDMI anche se il kernel la elenca prima: "
          "e' il difetto della 9.x, e deve restare corretto")

    con([SCHEDE[0], SCHEDE[2]])
    esigi(suoni.uscita({"audio": {"device": ""}}) == "plughw:2,0",
          "e se non c'e' altro si ripiega sull'interna anche li'")

    finge(piattaforma.PC, "PC", "", False)
    con(SCHEDE)
    for innesto in ("default", "pulse", "pipewire", "sysdefault"):
        esigi(suoni.uscita({"audio": {"device": innesto}}) == innesto,
              "%r si accetta sulla parola: su un desktop con PipeWire la "
              "scheda vera e' occupata" % innesto)
    esigi(suoni.uscita({"audio": {"device": "plughw:9,0"}}) == "",
          "una scheda staccata invece no: meglio muto che l'altoparlante "
          "sbagliato")
    esigi(suoni.uscita({"audio": {"device": "plughw:1,0"}}) == "plughw:1,0",
          "e una scheda scelta a mano e presente si usa")
finally:
    suoni.dispositivi = vero_dispositivi
    piattaforma.leggi(rileggi=True)


sep("5. Su questa macchina, adesso")

print("   %s" % piattaforma.riepilogo())
esigi(piattaforma.famiglia() in (piattaforma.PI, piattaforma.PC),
      "la famiglia e' una delle due")
esigi(isinstance(piattaforma.pannello_possibile(), bool),
      "e la risposta sul pannello e' un si o un no, non un forse")


print()
print("=" * 74)
falliti = [m for ok, m in esiti if not ok]
if falliti:
    print("FALLITI %d su %d" % (len(falliti), len(esiti)))
    for m in falliti:
        print("  - %s" % m)
    sys.exit(1)
print("TUTTO BENE: %d prove" % len(esiti))
