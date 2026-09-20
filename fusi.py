# -*- coding: utf-8 -*-
"""World Time: che ore sono adesso dall'altra parte del mondo.

Perche' il fuso e non le coordinate
-----------------------------------
La domanda naturale e' *«scrivo la citta' o il GPS?»*, e la risposta giusta
non e' nessuna delle due: si scrive il **fuso orario IANA**, tipo
`America/New_York`, e la citta' e' solo il modo comodo di sceglierlo.

Il motivo e' l'ora legale. «New York = UTC-5» e' sbagliato per meta'
dell'anno, e sbagliato in silenzio: nessuno se ne accorge finche' non arriva
in ritardo a una chiamata. Il fuso invece porta con se' le regole, e le regole
cambiano -- gli Stati che spostano le date, quelli che l'ora legale l'hanno
abolita. Quelle regole stanno gia' sul Raspberry, nel database dei fusi del
sistema, e si aggiornano con gli aggiornamenti di sistema: `zoneinfo` le legge
senza rete e senza dipendenze nuove.

Le coordinate GPS sono state scartate per un motivo pratico: tradurre
latitudine e longitudine in un fuso vuol dire un archivio di poligoni da
cinquanta o cento megabyte, oppure un servizio online con la sua chiave. Su un
pacchetto che ne pesa tre, il primo e' fuori scala; il secondo aggiunge una
dipendenza di rete a una cosa che funziona benissimo da sola.

L'elenco delle citta'
---------------------
Serve solo alla tendina della pagina web: e' un modo di scegliere un fuso
senza sapere come si chiama. Chi il nome lo sa puo' scriverlo a mano, e chi
sta in un posto che qui non c'e' non resta fuori. Per questo l'elenco non
pretende di essere completo -- sono le capitali e le citta' che si nominano
parlando, in italiano dove l'italiano un nome ce l'ha.

Due citta' possono condividere un fuso (Milano e Roma, Pechino e Shanghai) ed
e' giusto cosi': il fuso e' una regione, non un punto.
"""

# `zoneinfo` e' nella libreria standard dal 3.9, ma il database dei fusi puo'
# mancare su un sistema ridotto all'osso. L'importazione e' morbida come per
# tutte le dipendenze del progetto: senza, il World Time non si mostra e il
# resto dell'orologio continua a funzionare -- che e' molto meglio di un
# pannello nero.
try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones
    DISPONIBILE = True
except Exception:                                     # pragma: no cover
    ZoneInfo = None
    ZoneInfoNotFoundError = Exception
    available_timezones = None
    DISPONIBILE = False

from datetime import datetime

# Quante localita' si possono impostare. Cinque: sul pannello ne stanno tre
# per volta, quindi cinque vuol dire due giri di rotazione -- oltre, per
# vedere l'ultima si aspetterebbe troppo.
QUANTE = 5

# Le citta' della tendina: (nome mostrato, fuso IANA). Ogni fuso e' stato
# verificato contro il database del sistema prima di finire qui.
CITTA = (
    # Europa
    ("Roma", "Europe/Rome"),
    ("Milano", "Europe/Rome"),
    ("Londra", "Europe/London"),
    ("Parigi", "Europe/Paris"),
    ("Madrid", "Europe/Madrid"),
    ("Lisbona", "Europe/Lisbon"),
    ("Berlino", "Europe/Berlin"),
    ("Amsterdam", "Europe/Amsterdam"),
    ("Bruxelles", "Europe/Brussels"),
    ("Vienna", "Europe/Vienna"),
    ("Zurigo", "Europe/Zurich"),
    ("Praga", "Europe/Prague"),
    ("Varsavia", "Europe/Warsaw"),
    ("Budapest", "Europe/Budapest"),
    ("Bucarest", "Europe/Bucharest"),
    ("Atene", "Europe/Athens"),
    ("Istanbul", "Europe/Istanbul"),
    ("Stoccolma", "Europe/Stockholm"),
    ("Oslo", "Europe/Oslo"),
    ("Copenaghen", "Europe/Copenhagen"),
    ("Helsinki", "Europe/Helsinki"),
    ("Dublino", "Europe/Dublin"),
    ("Reykjavik", "Atlantic/Reykjavik"),
    ("Mosca", "Europe/Moscow"),
    ("Kiev", "Europe/Kyiv"),
    ("Belgrado", "Europe/Belgrade"),
    ("Zagabria", "Europe/Zagreb"),
    ("Sofia", "Europe/Sofia"),
    ("Malta", "Europe/Malta"),
    # Americhe
    ("New York", "America/New_York"),
    ("Miami", "America/New_York"),
    ("Chicago", "America/Chicago"),
    ("Denver", "America/Denver"),
    ("Los Angeles", "America/Los_Angeles"),
    ("Anchorage", "America/Anchorage"),
    ("Honolulu", "Pacific/Honolulu"),
    ("Toronto", "America/Toronto"),
    ("Montreal", "America/Toronto"),
    ("Vancouver", "America/Vancouver"),
    ("Citta del Messico", "America/Mexico_City"),
    ("L'Avana", "America/Havana"),
    ("Bogota", "America/Bogota"),
    ("Caracas", "America/Caracas"),
    ("Lima", "America/Lima"),
    ("Santiago", "America/Santiago"),
    ("Buenos Aires", "America/Argentina/Buenos_Aires"),
    ("San Paolo", "America/Sao_Paulo"),
    ("Rio de Janeiro", "America/Sao_Paulo"),
    # Asia
    ("Tokyo", "Asia/Tokyo"),
    ("Seul", "Asia/Seoul"),
    ("Pechino", "Asia/Shanghai"),
    ("Shanghai", "Asia/Shanghai"),
    ("Hong Kong", "Asia/Hong_Kong"),
    ("Taipei", "Asia/Taipei"),
    ("Singapore", "Asia/Singapore"),
    ("Bangkok", "Asia/Bangkok"),
    ("Hanoi", "Asia/Ho_Chi_Minh"),
    ("Giacarta", "Asia/Jakarta"),
    ("Manila", "Asia/Manila"),
    ("Kuala Lumpur", "Asia/Kuala_Lumpur"),
    ("Nuova Delhi", "Asia/Kolkata"),
    ("Mumbai", "Asia/Kolkata"),
    ("Karachi", "Asia/Karachi"),
    ("Dacca", "Asia/Dhaka"),
    ("Colombo", "Asia/Colombo"),
    ("Kathmandu", "Asia/Kathmandu"),
    ("Tashkent", "Asia/Tashkent"),
    ("Almaty", "Asia/Almaty"),
    ("Baku", "Asia/Baku"),
    ("Tbilisi", "Asia/Tbilisi"),
    ("Erevan", "Asia/Yerevan"),
    ("Teheran", "Asia/Tehran"),
    ("Baghdad", "Asia/Baghdad"),
    ("Dubai", "Asia/Dubai"),
    ("Doha", "Asia/Qatar"),
    ("Riad", "Asia/Riyadh"),
    ("Kuwait", "Asia/Kuwait"),
    ("Gerusalemme", "Asia/Jerusalem"),
    ("Beirut", "Asia/Beirut"),
    ("Amman", "Asia/Amman"),
    ("Novosibirsk", "Asia/Novosibirsk"),
    ("Vladivostok", "Asia/Vladivostok"),
    # Africa
    ("Il Cairo", "Africa/Cairo"),
    ("Casablanca", "Africa/Casablanca"),
    ("Tunisi", "Africa/Tunis"),
    ("Algeri", "Africa/Algiers"),
    ("Tripoli", "Africa/Tripoli"),
    ("Dakar", "Africa/Dakar"),
    ("Accra", "Africa/Accra"),
    ("Lagos", "Africa/Lagos"),
    ("Nairobi", "Africa/Nairobi"),
    ("Addis Abeba", "Africa/Addis_Ababa"),
    ("Johannesburg", "Africa/Johannesburg"),
    ("Citta del Capo", "Africa/Johannesburg"),
    # Oceania
    ("Sydney", "Australia/Sydney"),
    ("Melbourne", "Australia/Melbourne"),
    ("Brisbane", "Australia/Brisbane"),
    ("Adelaide", "Australia/Adelaide"),
    ("Darwin", "Australia/Darwin"),
    ("Perth", "Australia/Perth"),
    ("Auckland", "Pacific/Auckland"),
    ("Wellington", "Pacific/Auckland"),
    ("Fiji", "Pacific/Fiji"),
    ("Tahiti", "Pacific/Tahiti"),
    ("Guam", "Pacific/Guam"),
    ("Port Moresby", "Pacific/Port_Moresby"),
    # E il riferimento di tutti.
    ("UTC", "UTC"),
)

# Dal nome della citta' al fuso, per la tendina.
PER_CITTA = dict(CITTA)


def elenco():
    """Le citta' della tendina, in ordine alfabetico italiano."""
    return sorted(CITTA, key=lambda voce: voce[0].lower())


def tutti():
    """Tutti i fusi che il sistema conosce. Vuoto se il database manca."""
    if not DISPONIBILE:                               # pragma: no cover
        return []
    try:
        return sorted(available_timezones())
    except Exception:                                 # pragma: no cover
        return []


def valido(fuso):
    """Vero se questo fuso esiste davvero su questo sistema."""
    if not DISPONIBILE or not fuso:
        return False
    try:
        ZoneInfo(str(fuso))
        return True
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return False
    except Exception:                                 # pragma: no cover
        return False


def orario(fuso, ore24=True, adesso=None):
    """(ora da mostrare, scarto di giorno). ("", 0) se il fuso non va.

    Lo **scarto di giorno** e' la ragione per cui questa funzione non
    restituisce solo una stringa. A Roma le 05:54 sono l'una e cinquantaquattro
    di New York, ma di **ieri**: mostrare solo l'ora nasconde proprio
    l'informazione che uno cerca guardando un orologio del mondo. Vale -1 se
    la' e' il giorno prima, +1 se e' il giorno dopo, 0 se e' lo stesso.
    """
    if not DISPONIBILE or not fuso:
        return "", 0
    try:
        zona = ZoneInfo(str(fuso))
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return "", 0
    except Exception:                                 # pragma: no cover
        return "", 0
    qui = adesso or datetime.now().astimezone()
    la = qui.astimezone(zona)
    testo = la.strftime("%H:%M" if ore24 else "%I:%M").lstrip("0") \
        if not ore24 else la.strftime("%H:%M")
    scarto = (la.date() - qui.date()).days
    return testo, max(-1, min(1, scarto))


def scarto_orario(fuso, adesso=None):
    """Di quante ore e' avanti o indietro, come numero. None se non va.

    Serve alla pagina web, non al pannello: sul pannello c'e' l'ora, qui si
    vuole capire a colpo d'occhio se il fuso scelto e' quello giusto.
    """
    if not DISPONIBILE or not fuso:
        return None
    try:
        zona = ZoneInfo(str(fuso))
    except Exception:
        return None
    qui = adesso or datetime.now().astimezone()
    la = qui.astimezone(zona)
    differenza = (la.utcoffset() - qui.utcoffset()).total_seconds() / 3600.0
    return round(differenza, 2)
