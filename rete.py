# -*- coding: utf-8 -*-
"""La rete wifi vista e cambiata dalla pagina web.

Perche' esiste
--------------
Quando la wifi non va, per rimetterla a posto serviva un monitor, una
tastiera e un mouse attaccati al Raspberry. Per un oggetto che sta in
soggiorno e' una procedura assurda: il pannello e' li' acceso, il DMD
funziona, e l'unica cosa che manca e' scrivere una password.

Questo modulo e' il primo dei due pezzi che tolgono quella procedura: la
pagina da cui si vedono le reti e se ne sceglie una. Il secondo — l'hotspot
di soccorso che si alza da solo quando la connessione cade — arrivera' dopo,
e si appoggera' proprio a queste funzioni.

Come parla con il sistema
-------------------------
Con `nmcli`, e con nient'altro. Non si scrivono file di configurazione a
mano, non si tocca `wpa_supplicant`: NetworkManager e' il proprietario della
rete su Raspberry Pi OS recenti, e due proprietari sono peggio di nessuno.

Il vantaggio pratico e' che **le password non le custodiamo noi**. Quella
della rete scelta viene passata a NetworkManager, che le credenziali le
tiene gia' per mestiere, in `/etc/NetworkManager/system-connections` con i
permessi giusti. Nel `config.json` del DMD non finisce niente: non c'e' una
password da esportare per sbaglio, e non c'e' una password da perdere.

Il prezzo e' che la password passa dalla riga di comando di `nmcli`, dove per
un paio di secondi e' visibile a `ps`. Su una macchina con un utente solo e'
un rischio remoto; l'alternativa — scrivere il file di NetworkManager a mano
— vorrebbe dire diventare il secondo proprietario della rete, che e'
esattamente cio' che si sta evitando. La password non viene mai scritta nel
registro: le righe di log la sostituiscono con `***`.

Il collegamento non si fa dentro la richiesta web
-------------------------------------------------
Cambiare rete significa che il browser che ha premuto il pulsante **perde il
DMD**: era collegato attraverso la rete di prima. Una richiesta HTTP che
aspetta la fine del cambio non arriva a destinazione mai — resta li' finche'
scade, e l'utente non sa se e' andata bene.

Quindi il tentativo parte in un thread e la pagina risponde subito. L'esito
si deposita qui e la pagina lo mostra al ricaricamento successivo, quando la
si va a riaprire — sul nuovo indirizzo, se il cambio e' riuscito.
"""

import re
import shutil
import subprocess
import threading
import time

# Quanto si aspetta `nmcli`. La scansione con `--rescan yes` puo' prendersi
# una decina di secondi su una banda affollata; il collegamento anche di
# piu', perche' comprende il DHCP.
TIMEOUT_LETTURA = 20
TIMEOUT_CONNESSIONE = 60

# Reti che non si mostrano nell'elenco. Il DMD, quando alzera' il proprio
# hotspot di soccorso, vedra' se stesso: proporlo come rete a cui collegarsi
# sarebbe un invito a girare in tondo.
PREFISSO_SOCCORSO = "DMD-"


def disponibile():
    """Vero se su questa macchina si puo' comandare la rete."""
    return bool(shutil.which("nmcli"))


def _nmcli(args, timeout=TIMEOUT_LETTURA):
    """Esegue nmcli. Restituisce (codice, uscita, errore), senza sollevare.

    Questa e' la pagina che si apre quando la rete non va: non deve poter
    cadere. Un `nmcli` che non c'e', che si pianta o che risponde male e' un
    caso da raccontare, non un errore da propagare.
    """
    if not disponibile():
        return 127, "", "nmcli non installato"
    try:
        esito = subprocess.run(["nmcli"] + list(args), capture_output=True,
                               text=True, timeout=timeout)
        return esito.returncode, esito.stdout or "", esito.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", "nmcli non ha risposto entro %d secondi" % timeout
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, "", str(exc)


def _campi(riga):
    """Spezza una riga `nmcli -t` nei suoi campi.

    In modo terse i campi sono separati da due punti, e i due punti che fanno
    parte di un valore sono protetti da una barra rovesciata. Uno `split(":")`
    secco spezzerebbe a meta' ogni indirizzo MAC e ogni SSID che contiene i
    due punti — che esistono, e sono proprio quelli che poi non ci si spiega
    perche' non funzionano.
    """
    fuori, corrente, fuga = [], [], False
    for carattere in riga:
        if fuga:
            corrente.append(carattere)
            fuga = False
        elif carattere == "\\":
            fuga = True
        elif carattere == ":":
            fuori.append("".join(corrente))
            corrente = []
        else:
            corrente.append(carattere)
    fuori.append("".join(corrente))
    return fuori


def _interfaccia():
    """Il nome dell'interfaccia wifi, o "" se non ce n'e' una.

    Non si da' per scontato `wlan0`: con una chiavetta USB attaccata i nomi
    diventano due, e su alcune immagini il nome e' gia' diverso in partenza.
    """
    codice, uscita, _ = _nmcli(["-t", "-f", "DEVICE,TYPE", "device", "status"])
    if codice != 0:
        return ""
    for riga in uscita.splitlines():
        campi = _campi(riga)
        if len(campi) >= 2 and campi[1] == "wifi":
            return campi[0]
    return ""


def conosciute():
    """I nomi delle reti wifi gia' salvate, dalla piu' recente."""
    codice, uscita, _ = _nmcli(["-t", "-f", "NAME,TYPE", "connection", "show"])
    if codice != 0:
        return []
    fuori = []
    for riga in uscita.splitlines():
        campi = _campi(riga)
        if len(campi) >= 2 and campi[1] == "802-11-wireless" and campi[0]:
            fuori.append(campi[0])
    return fuori


def stato():
    """Fotografia della connessione attuale, per l'intestazione della pagina."""
    dati = {"disponibile": disponibile(), "interfaccia": "", "connessa": False,
            "ssid": "", "ip": "", "segnale": 0, "errore": ""}
    if not dati["disponibile"]:
        dati["errore"] = "nmcli non installato"
        return dati
    interfaccia = _interfaccia()
    dati["interfaccia"] = interfaccia
    if not interfaccia:
        dati["errore"] = "nessuna interfaccia wifi"
        return dati

    codice, uscita, errore = _nmcli(
        ["-t", "-f", "GENERAL.STATE,GENERAL.CONNECTION,IP4.ADDRESS",
         "device", "show", interfaccia])
    if codice != 0:
        dati["errore"] = errore.strip()
        return dati
    for riga in uscita.splitlines():
        campi = _campi(riga)
        if len(campi) < 2:
            continue
        chiave, valore = campi[0], ":".join(campi[1:])
        if chiave == "GENERAL.STATE":
            dati["connessa"] = "connected" in valore and "disconnected" not in valore
        elif chiave == "GENERAL.CONNECTION" and valore not in ("--", ""):
            dati["ssid"] = valore
        elif chiave.startswith("IP4.ADDRESS") and not dati["ip"]:
            dati["ip"] = valore.split("/")[0]

    for rete in scansiona(forza=False):
        if rete["attiva"]:
            dati["segnale"] = rete["segnale"]
            break
    return dati


def scansiona(forza=True):
    """Le reti visibili, dalla piu' forte. Lista vuota se non si puo' guardare.

    `forza` chiede a NetworkManager una scansione nuova invece della lista
    che ha in cache. Costa qualche secondo, quindi la pagina la fa quando
    gliela si chiede, e le funzioni che vogliono solo sapere com'e' messa la
    connessione attuale passano `False`.
    """
    argomenti = ["-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "device", "wifi",
                 "list"]
    if forza:
        argomenti += ["--rescan", "yes"]
    codice, uscita, _ = _nmcli(argomenti)
    if codice != 0:
        return []

    note = set(conosciute())
    per_nome = {}
    for riga in uscita.splitlines():
        campi = _campi(riga)
        if len(campi) < 4:
            continue
        attiva, ssid, segnale, sicurezza = campi[0], campi[1], campi[2], campi[3]
        # Le reti nascoste arrivano con l'SSID vuoto: senza nome non c'e'
        # niente da mostrare e niente su cui premere.
        if not ssid or ssid.startswith(PREFISSO_SOCCORSO):
            continue
        try:
            forza_segnale = max(0, min(100, int(segnale)))
        except ValueError:
            forza_segnale = 0
        voce = {"ssid": ssid, "segnale": forza_segnale,
                "sicurezza": sicurezza.strip(),
                "aperta": not sicurezza.strip(),
                "conosciuta": ssid in note,
                "attiva": attiva.strip() == "*"}
        # Lo stesso SSID compare una volta per ogni punto di accesso che lo
        # trasmette: in una casa con un ripetitore sono due o tre righe
        # identiche. Si tiene la piu' forte, che e' quella a cui ci si
        # collegherebbe comunque.
        vecchia = per_nome.get(ssid)
        if vecchia is None or voce["segnale"] > vecchia["segnale"]:
            voce["attiva"] = voce["attiva"] or (vecchia or {}).get("attiva", False)
            per_nome[ssid] = voce
        elif voce["attiva"]:
            vecchia["attiva"] = True

    return sorted(per_nome.values(),
                  key=lambda v: (-v["segnale"], v["ssid"].lower()))


# ------------------------------------------------------------- collegamento

# L'esito dell'ultimo tentativo. Lo scrive il thread, lo legge la pagina.
_tentativo = {"in_corso": False, "ssid": "", "esito": "", "messaggio": "",
              "quando": 0.0}
_lucchetto = threading.Lock()


def tentativo():
    with _lucchetto:
        return dict(_tentativo)


def _annota(**campi):
    with _lucchetto:
        _tentativo.update(campi)
        _tentativo["quando"] = time.time()


def _senza_password(argomenti):
    """Gli argomenti di nmcli con la password sostituita, per il registro."""
    fuori, prossimo_e_segreto = [], False
    for pezzo in argomenti:
        fuori.append("***" if prossimo_e_segreto else pezzo)
        prossimo_e_segreto = pezzo == "password"
    return " ".join(fuori)


def _esegui_connessione(ssid, password, interfaccia):
    if password:
        argomenti = ["device", "wifi", "connect", ssid, "password", password]
    elif ssid in conosciute():
        # Rete gia' salvata e nessuna password nuova: si riattiva il profilo
        # esistente invece di crearne un secondo con lo stesso nome.
        argomenti = ["connection", "up", ssid]
    else:
        argomenti = ["device", "wifi", "connect", ssid]
    if interfaccia and argomenti[0] == "device":
        argomenti += ["ifname", interfaccia]

    print("[rete] nmcli %s" % _senza_password(argomenti))
    codice, uscita, errore = _nmcli(argomenti, timeout=TIMEOUT_CONNESSIONE)
    if codice == 0:
        _annota(in_corso=False, esito="ok",
                messaggio=(uscita.strip().splitlines() or [""])[-1])
        return
    # NetworkManager, quando il tentativo fallisce, riattiva da solo il
    # profilo di prima: e' la ragione per cui qui non si smonta niente a mano
    # e non si cancella il profilo vecchio prima di aver provato il nuovo.
    messaggio = (errore.strip() or uscita.strip() or
                 "nmcli ha risposto %d" % codice)
    _annota(in_corso=False, esito="errore", messaggio=messaggio.splitlines()[-1])


def connetti(ssid, password=None):
    """Avvia il collegamento in un thread. Restituisce (avviato, motivo).

    Non aspetta l'esito di proposito: vedi la nota in cima al modulo.
    """
    ssid = (ssid or "").strip()
    if not ssid:
        return False, "nessuna rete indicata"
    if not disponibile():
        return False, "nmcli non installato"
    with _lucchetto:
        if _tentativo["in_corso"]:
            return False, "un tentativo e' gia' in corso"
        _tentativo.update({"in_corso": True, "ssid": ssid, "esito": "",
                           "messaggio": "", "quando": time.time()})
    interfaccia = _interfaccia()
    threading.Thread(target=_esegui_connessione, name="rete",
                     args=(ssid, password or None, interfaccia),
                     daemon=True).start()
    return True, ""


def dimentica(ssid):
    """Cancella il profilo salvato di una rete. Restituisce (fatto, motivo).

    Non si cancella la rete **attraverso cui si sta parlando**: sarebbe la
    pagina web che si stacca da sola il filo sotto i piedi, e per rimediare
    servirebbe di nuovo il monitor. Chi vuole liberarsene si collega prima a
    un'altra rete, e poi la dimentica.
    """
    ssid = (ssid or "").strip()
    if not ssid:
        return False, "nessuna rete indicata"
    if ssid not in conosciute():
        return False, "rete non salvata"
    if stato().get("ssid") == ssid:
        return False, "e' la rete a cui sei collegato adesso"
    codice, _, errore = _nmcli(["connection", "delete", ssid])
    if codice != 0:
        return False, (errore.strip() or "nmcli ha risposto %d" % codice)
    return True, ""


# --------------------------------------------------------------- indirizzi

_IPV4 = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")


def indirizzi():
    """Tutti gli indirizzi IPv4 della macchina, wifi ed ethernet.

    Serve alla pagina per dire «il DMD e' raggiungibile qui»: chi cambia rete
    ha bisogno di sapere dove ritrovarlo, e con il cavo attaccato gli
    indirizzi sono due.
    """
    codice, uscita, _ = _nmcli(["-t", "-f", "DEVICE,TYPE,STATE", "device",
                                "status"])
    if codice != 0:
        return []
    fuori = []
    for riga in uscita.splitlines():
        campi = _campi(riga)
        if len(campi) < 3 or campi[1] not in ("wifi", "ethernet"):
            continue
        if "connected" not in campi[2] or "disconnected" in campi[2]:
            continue
        _c, dettaglio, _e = _nmcli(["-t", "-f", "IP4.ADDRESS", "device",
                                    "show", campi[0]])
        for voce in dettaglio.splitlines():
            pezzi = _campi(voce)
            if len(pezzi) < 2:
                continue
            numero = ":".join(pezzi[1:]).split("/")[0]
            if _IPV4.match(numero):
                fuori.append({"interfaccia": campi[0], "tipo": campi[1],
                              "ip": numero})
    return fuori
