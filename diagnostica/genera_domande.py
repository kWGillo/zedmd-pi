# -*- coding: utf-8 -*-
"""Costruisce le due banche di domande di Super Quiz: italiano e inglese.

Due banche **indipendenti**
---------------------------
Fino alla 14.2 erano gemelle: la stessa domanda con lo stesso identificativo
nelle due lingue, per poter tenere un conto solo delle domande gia' uscite.
Sembrava elegante e costava carissimo -- e la segnalazione che l'ha
smontata e' di una riga: *«le domande in inglese possono tranquillamente
essere diverse da quelle in italiano»*. Giusto. Legate com'erano, ogni riga
con la traduzione rotta **in una sola** delle due lingue veniva buttata da
tutte e due: circa cinquecento domande perse senza motivo, con l'italiano
pulito e l'inglese che aveva tradotto un nome proprio, o viceversa.

Adesso ogni lingua ha la sua banca, le sue regole e i suoi identificativi, e
il conto delle domande gia' uscite e' uno per lingua. Costa una riga di
configurazione in piu' e rende due banche piu' grandi e piu' pulite.

Da dove vengono
---------------
**OpenQuizzDB** (CC BY-SA 4.0) per tutte e due le lingue: e' l'unico archivio
di quiz a scelta multipla con l'italiano dentro e una licenza che ne permette
la ridistribuzione. E' un progetto francese, e questo si sente -- vedi sotto.

**Open Trivia DB** (CC BY-SA 4.0) per il solo inglese: cinquemila e passa
domande verificate a mano, di qualita' piu' alta della media. In italiano non
esiste, e tradurle a macchina sarebbe rifare esattamente il difetto da cui
veniamo.

Il prezzo da pagare su OpenQuizzDB
----------------------------------
Le traduzioni sono automatiche e partono dal francese. Nei 3.323 quesiti
italiani si trovano parole rimaste in francese dentro le risposte, domande
su Christophe Willem e sui dipartimenti della Bretagna, e tre modi diversi di
scrivere la stessa difficolta'. Quindi questo script non scarica e basta:
**butta via**. Butta interi pacchetti che parlano di cose francesi, butta le
domande che portano ancora addosso il francese, butta quelle troppo lunghe
per un pannello da 256x64. Di quello che resta si fida.

Il francese resta l'arbitro dei nomi propri -- «L'Humanite» diventato
«Umanita» non e' una risposta imprecisa, e' una risposta sbagliata -- ma
adesso arbitra **una lingua per volta**.

Meglio duemila domande buone che tremila con dentro una che non ha senso: in
un quiz una domanda sbagliata non e' un difetto fra gli altri, e' l'unico
imperdonabile.

Si lancia a mano, sul computer e non sul Raspberry:

    python3 diagnostica/genera_domande.py

e scrive `domande.it.csv` e `domande.en.csv` in cima all'installazione.
Scaricare da Open Trivia DB richiede qualche minuto: l'archivio ammette una
richiesta ogni cinque secondi, e si rispetta.
"""

import csv
import glob
import io
import os
import re
import subprocess
import sys
import tempfile
import unicodedata

QUI = os.path.dirname(os.path.abspath(__file__))
DESTINAZIONE = os.path.dirname(QUI)

FONTE = "https://github.com/Zeuh/OpenQuizzDB.git"
CREDITO = "OpenQuizzDB (openquizzdb.org) - CC BY-SA 4.0"

# Open Trivia DB: solo per l'inglese. L'API da' cinquanta domande per volta e
# ammette una richiesta ogni cinque secondi; con un gettone di sessione non
# ripete niente finche' non ha finito l'archivio, e allora risponde "vuoto".
TDB_API = "https://opentdb.com/api.php"
TDB_TOKEN = "https://opentdb.com/api_token.php"
TDB_CREDITO = "Open Trivia DB (opentdb.com) - CC BY-SA 4.0"
TDB_PAUSA = 5.5
TDB_PER_VOLTA = 50

# Le misure del pannello, che decidono cosa ci sta e cosa no. Con il font dei
# giochi una riga porta 63 caratteri e ce ne stanno otto: la domanda ne
# occupa due, le quattro risposte due, e il resto sono montepremi e tempo.
MAX_DOMANDA = 100
MAX_RISPOSTA = 20
MAX_CURIOSITA = 150

# Da tre nomi francesi, piu' le varianti che i pacchetti piu' nuovi scrivono
# gia' tradotte, a tre numeri.
DIFFICOLTA = {
    "débutant": 1, "beginner": 1, "newbie": 1, "principiante": 1,
    "confirmé": 2, "confirmed": 2, "confermato": 2,
    "expert": 3, "esperto": 3,
}

# I pacchetti che non arrivano sul pannello, e perche'. Non e' snobismo: sono
# quiz scritti per un pubblico francese, e una domanda sui dipartimenti della
# Bretagna o sul vincitore di Secret Story, in una cucina italiana, non e'
# difficile -- e' impossibile, che in un quiz e' un'altra cosa.
SCARTATI = {
    14: "i dipartimenti della Bretagna",
    193: "la citta' di Vannes",
    221: "il Perigord",
    203: "le foreste di Francia",
    9: "i formaggi francesi",
    231: "Mouscron, cittadina belga",
    250: "commedie francesi",
    253: "Florence Foresti, comica francese",
    270: "Jean-Marie Bigard, comico francese",
    194: "France Gall, cantante francese",
    189: "Secret Story, reality francese",
    21: "reality francesi",
    25: "presentatori televisivi francesi",
    179: "gli stadi della Ligue 1",
    214: "la cerimonia dei Cesar",
    167: "belli del cinema francese",
    166: "moda e personaggi francesi",
    234: "il franglais, gioco di parole intraducibile",
    219: "modi di dire francesi: in italiano non vogliono dire niente",
    233: "citazioni brevi: tradotte perdono la battuta",
    226: "nomi propri francesi",
    251: "soprannomi di citta' francesi",
    235: "Traci Lords, attrice porno",
    273: "attrici di nome Virginie",
    271: "gossip di ottobre 2018",
    429: "gossip di febbraio 2021",
    434: "gossip di marzo 2021",
    441: "gossip di aprile 2021",
    463: "gossip di giugno 2021",
    543: "retrospettiva del 2021: invecchia in un anno",
    382: "ricordi del 2019: invecchia in un anno",
    541: "la variante Omicron: invecchia in un mese",
    393: "COVID-19: cronaca, non cultura generale",
    208: "Auroville, citta' sperimentale indiana: troppo di nicchia",
    187: "«cultura alla rinfusa»: meta' e' cultura francese",
    190: "«cultura alla rinfusa»: meta' e' cultura francese",
    249: "«cultura alla rinfusa»: meta' e' cultura francese",
    254: "«cultura alla rinfusa»: meta' e' cultura francese",
    259: "«cultura alla rinfusa»: meta' e' cultura francese",
    266: "«cultura alla rinfusa»: meta' e' cultura francese",
    172: "fatti di societa' francese",
    200: "«imbattibile»: domande francesi",
    228: "cultura giovane francese",
    213: "«star mondiali» che sono personaggi della tv francese",
    217: "«star mondiali» che sono personaggi della tv francese",
    220: "«star mondiali» che sono personaggi della tv francese",
    227: "«star mondiali» che sono personaggi della tv francese",
}

# Le lettere che l'italiano e l'inglese non hanno e il francese si'. Sono il
# modo piu' rapido di accorgersi che una parola non e' stata tradotta. Si
# perde qualche nome proprio legittimo -- Citroen, Chateau -- e va benissimo:
# di domande ce ne sono abbastanza.
LETTERE_FRANCESI = "âêîôûëïüçœæ"

# E le parole: una traduzione che lascia «avec» o «dans» in mezzo non e' una
# domanda, e' un refuso che si vede da tre metri.
PAROLE_FRANCESI = re.compile(
    r"\b(avec|dans|pour|vous|nous|leur|leurs|cette|cet|ceux|celui|celle|"
    r"aujourd|toujours|beaucoup|combien|lequel|laquelle|quel|quelle|quels|"
    r"quelles|est-il|est-ce|qu'est|c'est|n'est|d'un|d'une|plusieurs|"
    r"français|française|autre|autres|entre|chez|sans|sous|très|entre|"
    r"depuis|jusqu|entre|selon|parmi|ainsi|alors|donc|mais|ou bien)\b",
    re.I)

# «quel» e «quelle» sono parole italiane vere, quindi in italiano non si
# possono cercare: si toglierebbero domande buone. In inglese invece non
# esistono, e li' si cercano tutte.
# Le parole francesi che si trovano dentro le **risposte**: corte, comuni, e
# senza un omonimo italiano o inglese che le salvi. Una risposta che ne porta
# una non e' stata tradotta, punto.
RISPOSTE_FRANCESI = set("""
sec seche seches chaud chaude froid froide humide mouille mouillee
pipeau gardien gardiens lapin chien chienne oiseau oiseaux poisson poissons
voiture maison arbre arbres fleur fleurs pierre verre argent cuivre plomb
bois feuille feuilles couteau fourchette cuillere assiette bouteille
vert verte rouge jaune noir noire blanc blanche gris grise brun
cheval chevaux vache mouton cochon poule coq canard souris renard loup ours
ete hiver printemps automne matin soir nuit jour semaine mois annee
gauche droite haut bas devant derriere dedans dehors
manger boire dormir courir marcher parler ecrire lire voir entendre
petit petite grand grande gros grosse long longue court courte
toit mur porte fenetre escalier plancher jardin champ foret riviere
pain fromage beurre lait oeuf viande poulet gateau bonbon miel
tete main pied bras jambe coeur ventre dos epaule genou
""".split())


PAROLE_ITALIANO = re.compile(
    r"\b(avec|dans|pour|vous|nous|leurs|cette|aujourd|toujours|beaucoup|"
    r"laquelle|lequel|est-il|est-ce|qu'est|c'est|n'est|d'une|plusieurs|"
    r"française|français)\b",
    re.I)


def scarica():
    """Il mirror del database, clonato in una cartella temporanea."""
    cartella = tempfile.mkdtemp(prefix="oqdb-")
    print("  scarico %s" % FONTE)
    subprocess.run(["git", "clone", "--depth", "1", FONTE, cartella],
                   check=True, capture_output=True)
    return os.path.join(cartella, "data")


def titolo(percorso):
    """Il tema del pacchetto, dal file di descrizione che gli sta accanto."""
    desc = percorso.replace(".csv", ".desc")
    try:
        testo = open(desc, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""
    trovato = re.search(r"TITRE\s*:\s*(.+)", testo)
    return trovato.group(1).strip() if trovato else ""


def numero_pacchetto(percorso):
    trovato = re.search(r"_(\d+)\.csv$", os.path.basename(percorso))
    return int(trovato.group(1)) if trovato else 0


def francese(testo, lingua):
    """Vero se questo testo si porta ancora addosso il francese."""
    if any(ch in LETTERE_FRANCESI for ch in testo):
        return True
    schema = PAROLE_ITALIANO if lingua == "it" else PAROLE_FRANCESI
    return bool(schema.search(testo))


# ------------------------------------------------- i nomi che non si traducono

def _piatto(testo):
    """Il testo senza accenti, minuscolo e senza punteggiatura: per confronti."""
    piatto = unicodedata.normalize("NFD", (testo or "").lower())
    piatto = "".join(c for c in piatto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", piatto)


def _e_un_nome(testo):
    """Se questa risposta francese e' un nome proprio, e non una parola comune.

    Il segno e' la **maiuscola in mezzo**: la prima lettera e' maiuscola in
    tutte le risposte, quindi non dice niente, ma «L'Humanite», «Mega Mindy» e
    «PlayStation 2» hanno una maiuscola o una cifra dopo, e «Vert» no.
    """
    corpo = (testo or "")[1:]
    return bool(re.search(r"[A-ZÀ-Þ]", corpo) or re.search(r"\d", corpo))


# Sigle e nomi che dicono «questa domanda parla della Francia», anche quando
# la traduzione e' perfetta. Sapere chi ha sostituito Laurence Ferrari al
# telegiornale di TF1 non e' cultura generale: e' un'altra nazione.
FRANCESI_DENTRO = re.compile(
    r"\b(tf1|france 2|france 3|france 5|m6|canal\+|rtl|europe 1|arte|"
    r"nouvelle star|koh-lanta|ligue 1|cesar|molieres|nrj|skyrock|"
    r"assemblea nazionale|assemblee|elysee|eliseo|matignon|sncf|edf|"
    r"laurence ferrari|jean-luc|jean-pierre|jean-marie|marie-claire)\b", re.I)


def non_tradotta(fr, it, en):
    """Vero se una delle due lingue ha lasciato la parola di un'altra.

    Il caso tipico: il francese dice «Pomme», l'inglese «Apple», e l'italiano
    dice **anche lui** «Apple». Se quella parola fosse un nome proprio andrebbe
    bene -- i nomi non si traducono -- ma «Pomme» non lo e', e allora l'unica
    spiegazione e' che la traduzione italiana non e' avvenuta.

    Si guarda **solo in quella direzione**. Il controllo simmetrico -- inglese
    uguale al francese e diverso dall'italiano -- sembrava ovvio e buttava via
    quattrocento domande buone: «Lion», «Football», «Orange» e «Nature» si
    scrivono uguali in francese e in inglese perche' sono la stessa parola, non
    perche' qualcuno ha dimenticato di tradurre.
    """
    for quale in range(4):
        if _e_un_nome(fr[quale]):
            continue
        p_fr, p_it, p_en = (_piatto(fr[quale]), _piatto(it[quale]),
                            _piatto(en[quale]))
        if p_it == p_en != p_fr and p_it:
            return True          # l'italiano ha tenuto l'inglese
    return False


def nomi_rovinati_in(fr, mia):
    """Vero se **questa** lingua ha tradotto un nome proprio che non andava.

    E' la stessa regola di sempre, applicata a una lingua per volta: prima
    bastava che l'inglese rovinasse un nome per buttare anche la riga
    italiana, che magari era perfetta.
    """
    nomi = [_e_un_nome(r) for r in fr]
    if sum(nomi) >= 2:
        nomi = [True] * 4
    for quale, e_nome in enumerate(nomi):
        if e_nome and _piatto(mia[quale]) != _piatto(fr[quale]):
            return True
    return False


def non_tradotta_in(fr, mia, altra):
    """Vero se **questa** lingua ha lasciato la parola di un'altra.

    Il caso tipico: il francese dice «Pomme», l'inglese «Apple», e
    l'italiano dice **anche lui** «Apple». Il sospetto cade sulla lingua che
    ripete l'altra, non su tutte e due: l'inglese, li', e' giusto.
    """
    for quale in range(4):
        if _e_un_nome(fr[quale]):
            continue
        p_fr, p_mia, p_altra = (_piatto(fr[quale]), _piatto(mia[quale]),
                                _piatto(altra[quale]))
        if p_mia and p_mia == p_altra != p_fr:
            return True
    return False


def nomi_rovinati(fr, it, en):
    """Vero se una traduzione ha tradotto un nome proprio che non andava tradotto.

    E' il difetto peggiore di questa fonte, e non e' un dettaglio: «L'Humanite»
    diventato «Umanita» non e' una risposta imprecisa, e' una **risposta
    sbagliata** -- il giornale si chiama cosi' anche in italiano. Un quiz con
    dentro una domanda del genere non e' difficile, e' rotto.

    Due regole, e la seconda vale piu' della prima. Se una risposta francese e'
    riconoscibilmente un nome, le altre due lingue devono ripeterlo uguale. E
    se **almeno due** delle quattro sono nomi, allora lo sono tutte e quattro:
    quando le alternative sono Mega Mindy, Gwen Tennyson e Sif, anche «Blink»
    e' un personaggio, e «Lampeggia» e' una traduzione che nessuno voleva.
    """
    nomi = [_e_un_nome(r) for r in fr]
    if sum(nomi) >= 2:
        nomi = [True] * 4
    for quale, e_nome in enumerate(nomi):
        if not e_nome:
            continue
        atteso = _piatto(fr[quale])
        if _piatto(it[quale]) != atteso or _piatto(en[quale]) != atteso:
            return True
    return False


def pulisci(testo):
    """Spazi normali, niente virgolette strane, niente spazio prima del ?.

    Il francese scrive «mot ?» con lo spazio prima del punto interrogativo, e
    quella spaziatura arriva pari pari nelle traduzioni. In italiano e in
    inglese e' un errore di battitura.
    """
    testo = unicodedata.normalize("NFC", (testo or "").strip())
    testo = testo.replace(" ", " ").replace("’", "'")
    testo = testo.replace("«", '"').replace("»", '"')
    testo = re.sub(r"\s+([?!:;])", r"\1", testo)
    # Il francese scrive « mot » con gli spazi dentro le virgolette: si
    # stringe quello che sta fra due virgolette, non quello che sta intorno --
    # altrimenti si incollano le parole: «la serie"La casa di carta"».
    testo = re.sub(r'"\s*([^"]*?)\s*"', r'"\1"', testo)
    return " ".join(testo.split())


def buona(riga, lingua, controlla_francese=True):
    """Se questa domanda merita di finire sul pannello. Torna (sì/no, motivo).

    `controlla_francese` si spegne per le fonti che con il francese non
    c'entrano niente: in una domanda inglese di Open Trivia DB un accento non
    e' un residuo di traduzione, e' Beyonce'.
    """
    domanda, risposte = riga["domanda"], riga["risposte"]
    if not domanda or len(risposte) != 4 or not all(risposte):
        return False, "incompleta"
    if len(domanda) > MAX_DOMANDA:
        return False, "domanda lunga"
    if max(len(r) for r in risposte) > MAX_RISPOSTA:
        return False, "risposta lunga"
    if len(set(r.lower() for r in risposte)) != 4:
        return False, "risposte ripetute"
    if not domanda.endswith("?") and " " not in domanda[-12:]:
        return False, "non sembra una domanda"
    if controlla_francese:
        for pezzo in [domanda] + risposte:
            if francese(pezzo, lingua):
                return False, "francese rimasto"
        for risposta in risposte:
            if _piatto(risposta) in RISPOSTE_FRANCESI:
                return False, "risposta in francese"
    return True, ""


def leggi(cartella):
    """Tutte le righe dei pacchetti, per (pacchetto, posizione, lingua).

    **La posizione, non il numero scritto nel file.** In meta' dei pacchetti
    la numerazione riparte da uno per ogni lingua, nell'altra meta' prosegue:
    il quiz 165 ha il francese da 1 a 30, l'inglese da 31 a 60 e l'italiano
    da 121 a 150. Accoppiare le lingue per numero scritto vuol dire non
    accoppiarne nessuna, e si perdono milleduecento domande senza accorgersene
    -- e' successo al primo giro.
    """
    fuori = {}
    temi = {}
    for percorso in sorted(glob.glob(os.path.join(cartella, "*.csv"))):
        pacco = numero_pacchetto(percorso)
        temi[pacco] = titolo(percorso)
        quante = {"it": 0, "en": 0, "fr": 0}
        with open(percorso, encoding="utf-8", errors="replace") as handle:
            for campi in csv.reader(handle, delimiter=";"):
                if len(campi) < 9 or len(campi[1]) != 2:
                    continue
                lingua = campi[1]
                if lingua not in ("it", "en", "fr"):
                    continue
                quante[lingua] += 1
                fuori[(pacco, quante[lingua], lingua)] = {
                    "domanda": pulisci(campi[2]),
                    "risposte": [pulisci(c) for c in campi[3:7]],
                    "difficolta": DIFFICOLTA.get(pulisci(campi[7]).lower(), 2),
                    "curiosita": pulisci(campi[8])[:MAX_CURIOSITA],
                }
    return fuori, temi


# Il tema del pacchetto diventa la categoria mostrata sul pannello, nelle due
# lingue. I titoli originali sono in francese: qui sono tradotti a mano una
# volta sola, perche' sono poche decine e perche' una traduzione automatica di
# una riga di due parole sbaglia piu' spesso di quanto si creda.
CATEGORIE = {
    237: ("Api e alveari", "Bees and hives"),
    196: ("Alan Turing", "Alan Turing"),
    265: ("Alberti famosi", "Famous Alberts"),
    241: ("La saga di Alien", "The Alien saga"),
    175: ("Animali in cifre", "Animals by numbers"),
    184: ("Animali alla rinfusa", "Animals at random"),
    269: ("Artisti elettronici", "Electronic artists"),
    186: ("Intorno alla neve", "All about snow"),
    243: ("Brad Pitt al cinema", "Brad Pitt on screen"),
    238: ("Britney Spears", "Britney Spears"),
    224: ("Cactus", "Cacti"),
    247: ("Central Park", "Central Park"),
    257: ("Charlize Theron", "Charlize Theron"),
    173: ("Cavalli", "Horses"),
    24: ("Castelli", "Castles"),
    205: ("Coca-Cola", "Coca-Cola"),
    413: ("Colombofilia", "Pigeon racing"),
    256: ("Commedie al cinema", "Film comedies"),
    223: ("Criptovalute", "Cryptocurrencies"),
    187: ("Cultura alla rinfusa", "Culture at random"),
    190: ("Cultura alla rinfusa", "Culture at random"),
    249: ("Cultura alla rinfusa", "Culture at random"),
    254: ("Cultura alla rinfusa", "Culture at random"),
    259: ("Cultura alla rinfusa", "Culture at random"),
    266: ("Cultura alla rinfusa", "Culture at random"),
    165: ("Cultura generale", "General knowledge"),
    228: ("Cultura giovane", "Youth culture"),
    202: ("Ceramica", "Ceramics"),
    177: ("Cartoni animati", "Cartoons"),
    207: ("La colazione", "Breakfast"),
    191: ("Arrampicata", "Climbing"),
    172: ("Fatti di societa'", "Society"),
    244: ("Narrativa per tutti", "Fiction for all"),
    405: ("Folclore giapponese", "Japanese folklore"),
    272: ("Calcio 1990-2000", "Football 1990-2000"),
    268: ("Calcio 2000-2010", "Football 2000-2010"),
    264: ("Calcio 2010-2020", "Football 2010-2020"),
    294: ("San Nicola", "Saint Nicholas"),
    209: ("Gin", "Gin"),
    188: ("Gladiatori", "Gladiators"),
    212: ("Golf", "Golf"),
    277: ("Halloween", "Halloween"),
    3: ("Harry Potter", "Harry Potter"),
    200: ("Imbattibile", "Unbeatable"),
    239: ("Instagram", "Instagram"),
    263: ("Giardino giapponese", "Japanese garden"),
    262: ("John McEnroe", "John McEnroe"),
    180: ("Buon Natale", "Merry Christmas"),
    267: ("La casa di carta", "Money Heist"),
    206: ("Magnesio", "Magnesium"),
    168: ("Trucco", "Make-up"),
    365: ("Microsoft", "Microsoft"),
    192: ("Mike Horn", "Mike Horn"),
    255: ("Mont Saint-Michel", "Mont Saint-Michel"),
    246: ("Misteri del mondo", "Mysteries of the world"),
    195: ("Numeri", "Numbers"),
    232: ("OpenBSD", "OpenBSD"),
    248: ("Pamela Anderson", "Pamela Anderson"),
    204: ("PlayStation 2", "PlayStation 2"),
    260: ("La patata", "The potato"),
    211: ("PyeongChang 2018", "PyeongChang 2018"),
    185: ("Sport invernali", "Winter sports"),
    18: ("Star Trek", "Star Trek"),
    213: ("Star mondiali", "World stars"),
    217: ("Star mondiali", "World stars"),
    220: ("Star mondiali", "World stars"),
    227: ("Star mondiali", "World stars"),
    201: ("Supereroine", "Superheroines"),
    383: ("Sul campo da tennis", "On the tennis court"),
    23: ("Tennis", "Tennis"),
    197: ("The Cure", "The Cure"),
    8: ("Tutankhamon", "Tutankhamun"),
    236: ("Successi disco", "Disco hits"),
    174: ("Citta' del mondo", "Cities of the world"),
    199: ("Vulcani attivi", "Active volcanoes"),
    261: ("World of Warcraft", "World of Warcraft"),
    403: ("iPhone", "iPhone"),
    199 + 0: ("Vulcani attivi", "Active volcanoes"),
}


def costruisci(cartella):
    """Le due banche, ciascuna con le sue regole. Torna {lingua: [voci]}."""
    righe, temi = leggi(cartella)
    # Il francese sta nelle righe solo come arbitro dei nomi propri: i
    # pacchetti che hanno solo lui non sono domande mancanti, non sono
    # domande.
    chiavi = sorted({(p, n) for p, n, l in righe if l in ("it", "en")})
    banche = {"it": [], "en": []}
    scarti = {"it": {}, "en": {}}
    fuori_pacco = 0
    for pacco, numero in chiavi:
        if pacco in SCARTATI:
            fuori_pacco += 1
            continue
        categoria = CATEGORIE.get(pacco)
        if categoria is None:
            for lingua in ("it", "en"):
                scarti[lingua]["pacchetto senza categoria"] = \
                    scarti[lingua].get("pacchetto senza categoria", 0) + 1
            continue
        fr = righe.get((pacco, numero, "fr"))
        coppia = {"it": righe.get((pacco, numero, "it")),
                  "en": righe.get((pacco, numero, "en"))}
        for lingua in ("it", "en"):
            mia = coppia[lingua]
            altra = coppia["en" if lingua == "it" else "it"]

            def butta(motivo):
                scarti[lingua][motivo] = scarti[lingua].get(motivo, 0) + 1

            if not mia:
                butta("manca in questa lingua")
                continue
            ok, motivo = buona(mia, lingua)
            if not ok:
                butta(motivo)
                continue
            if fr and nomi_rovinati_in(fr["risposte"], mia["risposte"]):
                butta("nome proprio tradotto")
                continue
            if (fr and altra
                    and non_tradotta_in(fr["risposte"], mia["risposte"],
                                        altra["risposte"])):
                butta("risposta non tradotta")
                continue
            if FRANCESI_DENTRO.search(mia["domanda"] + " "
                                      + " ".join(mia["risposte"])):
                butta("domanda sulla Francia")
                continue
            banche[lingua].append({
                "id": "oq-%d-%d" % (pacco, numero),
                "categoria": categoria[0 if lingua == "it" else 1],
                "difficolta": mia["difficolta"],
                "domanda": mia["domanda"],
                "risposte": mia["risposte"],
                "curiosita": mia["curiosita"],
            })
    print("  pacchetti esclusi a monte: %d" % fuori_pacco)
    for lingua in ("it", "en"):
        print("  [%s] tenute %d" % (lingua, len(banche[lingua])))
        for motivo, quante in sorted(scarti[lingua].items(), key=lambda x: -x[1]):
            print("       scartate per \u00ab%s\u00bb: %d" % (motivo, quante))
    return banche


# ------------------------------------------------------------ Open Trivia DB

# Le categorie di Open Trivia DB, accorciate per il pannello. "Entertainment:
# Japanese Anime & Manga" e' un'etichetta da database, non una da leggere a
# tre metri.
TDB_CATEGORIE = {
    "General Knowledge": "General knowledge",
    "Entertainment: Books": "Books",
    "Entertainment: Film": "Film",
    "Entertainment: Music": "Music",
    "Entertainment: Musicals & Theatres": "Musicals and theatre",
    "Entertainment: Television": "Television",
    "Entertainment: Video Games": "Video games",
    "Entertainment: Board Games": "Board games",
    "Entertainment: Comics": "Comics",
    "Entertainment: Japanese Anime & Manga": "Anime and manga",
    "Entertainment: Cartoon & Animations": "Cartoons",
    "Science & Nature": "Science and nature",
    "Science: Computers": "Computers",
    "Science: Mathematics": "Mathematics",
    "Science: Gadgets": "Gadgets",
    "Mythology": "Mythology",
    "Sports": "Sport",
    "Geography": "Geography",
    "History": "History",
    "Politics": "Politics",
    "Art": "Art",
    "Celebrities": "Celebrities",
    "Animals": "Animals",
    "Vehicles": "Vehicles",
}

TDB_DIFFICOLTA = {"easy": 1, "medium": 2, "hard": 3}


def _tdb_chiedi(url):
    import json
    import urllib.request
    with urllib.request.urlopen(url, timeout=30) as risposta:
        return json.loads(risposta.read().decode("utf8"))


def scarica_tdb(massimo=6000):
    """Tutte le domande a scelta multipla di Open Trivia DB, in inglese.

    Con un gettone di sessione l'archivio non ripete niente: si chiede finche'
    non risponde «finite» (codice 4). Una richiesta ogni cinque secondi e
    mezzo, che e' il limite dichiarato piu' un margine: e' un servizio
    gratuito, e chi lo usa di corsa lo fa chiudere a tutti.
    """
    import time
    import urllib.parse
    try:
        gettone = _tdb_chiedi(TDB_TOKEN + "?command=request").get("token", "")
    except Exception as exc:
        print("  Open Trivia DB non risponde: %s" % exc)
        return []
    fuori = []
    while len(fuori) < massimo:
        url = "%s?amount=%d&type=multiple&encode=url3986&token=%s" % (
            TDB_API, TDB_PER_VOLTA, gettone)
        try:
            dati = _tdb_chiedi(url)
        except Exception as exc:
            print("  Open Trivia DB: %s" % exc)
            break
        codice = dati.get("response_code", 1)
        if codice == 4:                       # archivio finito: e' la fine
            break
        if codice == 5:                       # troppo in fretta: si aspetta
            time.sleep(TDB_PAUSA * 2)
            continue
        if codice != 0:
            break
        for voce in dati.get("results", []):
            fuori.append({k: urllib.parse.unquote(v) if isinstance(v, str)
                          else [urllib.parse.unquote(x) for x in v]
                          for k, v in voce.items()})
        print("    scaricate %d..." % len(fuori))
        time.sleep(TDB_PAUSA)
    return fuori


def costruisci_tdb(grezze, gia_viste):
    """Da Open Trivia DB alla nostra forma. Torna le voci tenute."""
    tenute, scarti = [], {}
    for indice, voce in enumerate(grezze):
        def butta(motivo):
            scarti[motivo] = scarti.get(motivo, 0) + 1

        categoria = TDB_CATEGORIE.get(voce.get("category", ""))
        if categoria is None:
            butta("categoria sconosciuta")
            continue
        risposte = [pulisci(voce.get("correct_answer", ""))] + [
            pulisci(r) for r in voce.get("incorrect_answers", [])]
        riga = {"domanda": pulisci(voce.get("question", "")),
                "risposte": risposte,
                "difficolta": TDB_DIFFICOLTA.get(voce.get("difficulty"), 2),
                "curiosita": ""}
        # Il controllo sul francese non si fa: qui il francese non c'e' mai,
        # e una domanda su Beyonce' o sul cafe' non e' un difetto.
        ok, motivo = buona(riga, "en", controlla_francese=False)
        if not ok:
            butta(motivo)
            continue
        impronta = _piatto(riga["domanda"])
        if impronta in gia_viste:
            butta("gia' presente")
            continue
        gia_viste.add(impronta)
        tenute.append({
            "id": "tdb-%d" % (indice + 1),
            "categoria": categoria,
            "difficolta": riga["difficolta"],
            "domanda": riga["domanda"],
            "risposte": riga["risposte"],
            "curiosita": "",
        })
    print("  [en] da Open Trivia DB: %d" % len(tenute))
    for motivo, quante in sorted(scarti.items(), key=lambda x: -x[1]):
        print("       scartate per \u00ab%s\u00bb: %d" % (motivo, quante))
    return tenute


INTESTAZIONE = {
    "it": ("Le domande di Super Quiz, in italiano.",
           "  id;categoria;difficolta;domanda;giusta;sbagliata1;sbagliata2;"
           "sbagliata3;curiosita",
           "La difficolta' va da 1 a 3. Questa banca e' indipendente da",
           "quella inglese: le due lingue non fanno le stesse domande, e",
           "ognuna tiene il conto suo di quelle gia' uscite.",
           "Gli identificativi dicono da dove viene la riga: oq- da",
           "OpenQuizzDB, tdb- da Open Trivia DB.",
           "Puoi aggiungerne di tue mettendo un domande.it.csv nella cartella",
           "dati (/var/lib/dmd), con lo stesso formato. Quelle tue non vengono",
           "mai toccate dagli aggiornamenti."),
    "en": ("Super Quiz questions, in English.",
           "  id;category;difficulty;question;right;wrong1;wrong2;wrong3;trivia",
           "Difficulty runs from 1 to 3. This bank is independent from the",
           "Italian one: the two languages do not ask the same questions, and",
           "each keeps its own record of what has already been asked.",
           "The id says where the row comes from: oq- OpenQuizzDB, tdb- Open",
           "Trivia DB.",
           "You can add your own by putting a domande.en.csv in the data",
           "folder (/var/lib/dmd), same format. Yours are never touched by",
           "updates."),
}


def scrivi(voci, lingua, crediti):
    percorso = os.path.join(DESTINAZIONE, "domande.%s.csv" % lingua)
    fuori = io.StringIO()
    for riga in INTESTAZIONE[lingua]:
        fuori.write("# %s\n" % riga)
    fuori.write("#\n")
    for credito in crediti:
        fuori.write("# Fonte: %s\n" % credito)
    fuori.write("# %d domande.\n" % len(voci))
    scrittore = csv.writer(fuori, delimiter=";", lineterminator="\n")
    for voce in voci:
        scrittore.writerow([
            voce["id"],
            voce["categoria"],
            voce["difficolta"],
            voce["domanda"],
            voce["risposte"][0],
            voce["risposte"][1],
            voce["risposte"][2],
            voce["risposte"][3],
            voce["curiosita"],
        ])
    with open(percorso, "w", encoding="utf-8") as handle:
        handle.write(fuori.getvalue())
    print("  %-20s %5d domande  %6.0f KiB"
          % (os.path.basename(percorso), len(voci),
             os.path.getsize(percorso) / 1024.0))


# ------------------------------------------------------- OpenTriviaQA (inglese)

OTQA_FONTE = "https://github.com/uberspot/OpenTriviaQA.git"
OTQA_CREDITO = "OpenTriviaQA (github.com/uberspot/OpenTriviaQA) - CC BY-SA 4.0"

# Le categorie che arrivano sul pannello, con l'etichetta da mostrare. Fuori
# restano `celebrities`, `television`, `for-kids`, `rated`, `newest` e
# `video-games`: sono quasi solo televisione e gossip americani degli anni
# Novanta, e una domanda impossibile per chi gioca non e' una domanda
# difficile -- e' una domanda rotta. `newest` e `rated` sono poi doppioni
# delle altre.
OTQA_CATEGORIE = {
    "animals": "Animals",
    "brain-teasers": "Brain teasers",
    "general": "General knowledge",
    "geography": "Geography",
    "history": "History",
    "hobbies": "Hobbies",
    "humanities": "Humanities",
    "literature": "Literature",
    "movies": "Film",
    "music": "Music",
    "people": "People",
    "religion-faith": "Religion and faith",
    "science-technology": "Science and technology",
    "sports": "Sport",
    "world": "The world",
}

# Le domande che si riconoscono rotte dal testo: un buco da riempire, un
# rimando a "the above", una domanda che comincia con un trattino. Sono i
# difetti tipici di un archivio scritto da mille mani diverse.
OTQA_ROTTE = re.compile(r"(_{2,}|\.{3,}|^\W|\bof the above\b|\ball of these\b)", re.I)


def leggi_otqa(cartella):
    """Le domande di OpenTriviaQA, dal suo formato a righe.

        #Q Questa bibita contiene caffeina.
        ^ Caffe'
        A Acqua minerale
        ...

    Il formato e' comodo da correggere a mano e scomodo da leggere a
    macchina: una domanda puo' stare su piu' righe, e la risposta giusta e'
    ripetuta fra le quattro. Si tiene solo quello che ha esattamente quattro
    alternative e una giusta che e' fra quelle.
    """
    fuori = []
    for nome, etichetta in sorted(OTQA_CATEGORIE.items()):
        percorso = os.path.join(cartella, "categories", nome)
        if not os.path.isfile(percorso):
            continue
        blocchi = open(percorso, encoding="utf8", errors="replace").read().split("#Q ")
        for blocco in blocchi[1:]:
            righe = [r.strip() for r in blocco.strip().splitlines()]
            domanda, giusta, alternative = [], "", []
            for riga in righe:
                if riga.startswith("^ "):
                    giusta = riga[2:].strip()
                elif re.match(r"^[A-E] ", riga):
                    alternative.append(riga[2:].strip())
                elif not giusta and not alternative:
                    domanda.append(riga)
            fuori.append({
                "categoria": etichetta,
                "domanda": " ".join(d for d in domanda if d),
                "giusta": giusta,
                "alternative": alternative,
            })
    return fuori


def costruisci_otqa(grezze, gia_viste):
    """Da OpenTriviaQA alla nostra forma, con la mano pesante sui filtri."""
    tenute, scarti = [], {}
    for indice, voce in enumerate(grezze):
        def butta(motivo):
            scarti[motivo] = scarti.get(motivo, 0) + 1

        if len(voce["alternative"]) != 4 or voce["giusta"] not in voce["alternative"]:
            butta("non ha quattro risposte")
            continue
        domanda = pulisci(voce["domanda"])
        if OTQA_ROTTE.search(domanda):
            butta("domanda malformata")
            continue
        risposte = [pulisci(voce["giusta"])] + [
            pulisci(a) for a in voce["alternative"] if a != voce["giusta"]]
        riga = {"domanda": domanda, "risposte": risposte, "difficolta": 2,
                "curiosita": ""}
        ok, motivo = buona(riga, "en", controlla_francese=False)
        if not ok:
            butta(motivo)
            continue
        impronta = _piatto(domanda)
        if impronta in gia_viste:
            butta("gia' presente")
            continue
        gia_viste.add(impronta)
        tenute.append({
            "id": "otqa-%d" % (indice + 1),
            "categoria": voce["categoria"],
            "difficolta": 2,
            "domanda": domanda,
            "risposte": risposte,
            "curiosita": "",
        })
    print("  [en] da OpenTriviaQA: %d" % len(tenute))
    for motivo, quante in sorted(scarti.items(), key=lambda x: -x[1]):
        print("       scartate per \u00ab%s\u00bb: %d" % (motivo, quante))
    return tenute


# Le categorie di Open Trivia DB in italiano, per le domande tradotte.
TDB_CATEGORIE_IT = {
    "General Knowledge": "Cultura generale",
    "Entertainment: Books": "Libri",
    "Entertainment: Film": "Cinema",
    "Entertainment: Music": "Musica",
    "Entertainment: Musicals & Theatres": "Musical e teatro",
    "Entertainment: Television": "Televisione",
    "Entertainment: Video Games": "Videogiochi",
    "Entertainment: Board Games": "Giochi da tavolo",
    "Entertainment: Comics": "Fumetti",
    "Entertainment: Japanese Anime & Manga": "Anime e manga",
    "Entertainment: Cartoon & Animations": "Cartoni animati",
    "Science & Nature": "Scienze e natura",
    "Science: Computers": "Informatica",
    "Science: Mathematics": "Matematica",
    "Science: Gadgets": "Congegni",
    "Mythology": "Mitologia",
    "Sports": "Sport",
    "Geography": "Geografia",
    "History": "Storia",
    "Politics": "Politica",
    "Art": "Arte",
    "Celebrities": "Personaggi famosi",
    "Animals": "Animali",
    "Vehicles": "Mezzi di trasporto",
}

# Le traduzioni italiane delle domande di Open Trivia DB, una per riga:
#
#     tdb-1002 ~ La Terra si trova in quale galassia? ~ Via Lattea ~ ...
#
# La riga «id ~ SALTA ~ motivo» dice che quella domanda **non** si traduce, e
# il motivo sta li' per chi legge il file fra un anno: uno scherzo di parole
# inglese, una domanda di sport, un cartone animato.
#
# Perche' un file e non una traduzione al volo: una traduzione fatta a mano
# si rilegge, si corregge e si tiene. Rifarla ogni volta che si rigenerano le
# banche vorrebbe dire non poterla correggere mai.
TRADUZIONI = os.path.join(QUI, "traduzioni.tsv")


def leggi_traduzioni(percorso=None):
    """Le traduzioni italiane, per identificativo. Salta le righe «SALTA»."""
    percorso = percorso or TRADUZIONI
    fuori = {}
    if not os.path.isfile(percorso):
        return fuori
    with open(percorso, encoding="utf8") as handle:
        for riga in handle:
            riga = riga.strip()
            if not riga or riga.startswith("#"):
                continue
            campi = [c.strip() for c in riga.split(" ~ ")]
            if len(campi) == 3 and campi[1] == "SALTA":
                continue
            if len(campi) != 6:
                print("  traduzione malformata: %s" % campi[0])
                continue
            fuori[campi[0]] = {"domanda": campi[1], "risposte": campi[2:6]}
    return fuori


def costruisci_tdb_italiano(grezze, traduzioni, gia_viste):
    """Le domande di Open Trivia DB tradotte a mano, per la banca italiana."""
    tenute, scarti = [], {}
    for indice, voce in enumerate(grezze):
        chiave = "tdb-%d" % (indice + 1)
        tradotta = traduzioni.get(chiave)
        if tradotta is None:
            continue

        def butta(motivo):
            scarti[motivo] = scarti.get(motivo, 0) + 1

        categoria = TDB_CATEGORIE_IT.get(voce.get("category", ""))
        if categoria is None:
            butta("categoria sconosciuta")
            continue
        riga = {"domanda": tradotta["domanda"],
                "risposte": list(tradotta["risposte"]),
                "difficolta": TDB_DIFFICOLTA.get(voce.get("difficulty"), 2),
                "curiosita": ""}
        # Le stesse misure di tutti: una domanda tradotta non entra nel
        # pannello solo perche' e' stata tradotta a mano.
        ok, motivo = buona(riga, "it", controlla_francese=False)
        if not ok:
            butta(motivo)
            print("  [it] scartata %s (%s): %s" % (chiave, motivo, riga["domanda"]))
            continue
        impronta = _piatto(riga["domanda"])
        if impronta in gia_viste:
            butta("gia' presente")
            continue
        gia_viste.add(impronta)
        tenute.append({"id": chiave, "categoria": categoria,
                       "difficolta": riga["difficolta"],
                       "domanda": riga["domanda"],
                       "risposte": riga["risposte"], "curiosita": ""})
    print("  [it] da Open Trivia DB, tradotte a mano: %d" % len(tenute))
    for motivo, quante in sorted(scarti.items(), key=lambda x: -x[1]):
        print("       scartate per \u00ab%s\u00bb: %d" % (motivo, quante))
    return tenute


def leggi_tdb_da_disco(cartella):
    """Le risposte gia' scaricate di Open Trivia DB, da una cartella di JSON.

    Serve quando la rete di qui non arriva a opentdb.com: si scarica altrove
    -- il computer di casa, lo script che sta in `diagnostica/scarica_tdb.sh`
    -- e si mettono i file in una cartella, uno per richiesta.
    """
    import json
    import urllib.parse
    fuori = []
    for percorso in sorted(glob.glob(os.path.join(cartella, "*.json"))):
        try:
            dati = json.load(open(percorso, encoding="utf8"))
        except Exception as exc:
            print("  %s: %s" % (os.path.basename(percorso), exc))
            continue
        for voce in dati.get("results", []):
            fuori.append({k: urllib.parse.unquote(v) if isinstance(v, str)
                          else [urllib.parse.unquote(x) for x in v]
                          for k, v in voce.items()})
    print("  Open Trivia DB: %d domande lette da %s" % (len(fuori), cartella))
    return fuori


def main():
    # La cartella di OpenQuizzDB e' l'argomento senza trattini -- ma non il
    # valore di un'opzione: `--con-otqa /tmp/otqa` non e' la fonte italiana.
    cartella = None
    salta = False
    for argomento in sys.argv[1:]:
        if salta:
            salta = False
            continue
        if argomento in ("--tdb-da", "--con-otqa", "--traduzioni"):
            salta = True
            continue
        if not argomento.startswith("--"):
            cartella = argomento
    cartella = cartella or scarica()
    print("dati in %s" % cartella)
    banche = costruisci(cartella)
    crediti = {"it": [CREDITO], "en": [CREDITO]}
    gia_viste = {_piatto(v["domanda"]) for v in banche["en"]}

    # Open Trivia DB: dalla rete, oppure da una cartella di risposte gia'
    # scaricate altrove -- `--tdb-da /percorso`. Il "--senza-tdb" serve a
    # rifare le banche senza aspettare dieci minuti di rete mentre si sta
    # lavorando sulle regole di pulizia.
    grezze = []
    da_disco = _valore("--tdb-da")
    if da_disco:
        grezze = leggi_tdb_da_disco(da_disco)
    elif "--senza-tdb" not in sys.argv:
        print("Open Trivia DB (una richiesta ogni %.1f secondi)..." % TDB_PAUSA)
        grezze = scarica_tdb()
    if grezze:
        aggiunte = costruisci_tdb(grezze, gia_viste)
        if aggiunte:
            banche["en"].extend(aggiunte)
            crediti["en"].append(TDB_CREDITO)
        # E le stesse domande tradotte a mano in italiano, quelle che ci sono.
        traduzioni = leggi_traduzioni(_valore("--traduzioni") or None)
        if traduzioni:
            viste_it = {_piatto(v["domanda"]) for v in banche["it"]}
            tradotte = costruisci_tdb_italiano(grezze, traduzioni, viste_it)
            if tradotte:
                banche["it"].extend(tradotte)
                crediti["it"].append(TDB_CREDITO + ", tradotte a mano")

    # OpenTriviaQA: cinquantamila domande inglesi, di mano molto diversa.
    # Non e' accesa di suo -- si chiede con `--con-otqa /percorso/al/clone`.
    otqa = _valore("--con-otqa")
    if otqa:
        aggiunte = costruisci_otqa(leggi_otqa(otqa), gia_viste)
        if aggiunte:
            banche["en"].extend(aggiunte)
            crediti["en"].append(OTQA_CREDITO)

    for lingua in ("it", "en"):
        scrivi(banche[lingua], lingua, crediti[lingua])
    return 0


def _valore(nome):
    """Il valore di un argomento `--cosa valore`, o "" se non c'e'."""
    for indice, argomento in enumerate(sys.argv):
        if argomento == nome and indice + 1 < len(sys.argv):
            return sys.argv[indice + 1]
        if argomento.startswith(nome + "="):
            return argomento.split("=", 1)[1]
    return ""


if __name__ == "__main__":
    sys.exit(main())
