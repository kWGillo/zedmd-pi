#!/bin/bash
#
# Prepara Doom sul Pi: sorgenti, compilazione, WAD.
#   sudo ./setup_doom.sh
#
# I sorgenti di doomgeneric non stanno in questo repository, e non e' una
# dimenticanza: discendono dai sorgenti di Doom, che sono GPL versione 2, e
# questo progetto e' GPLv3. Il binario che ne esce e' un programma a se' —
# il servizio DMD lo avvia e gli parla da una pipe, non ci si collega — quindi
# le due licenze non si toccano mai. Qui si scarica e si compila, e basta.
#
# Il WAD e' Freedoom, che e' libero (licenza BSD). I WAD commerciali di id
# Software non si possono ridistribuire: se ne hai uno tuo, mettilo al posto
# di quello scaricato e cambia il percorso nella pagina Doom.
#
set -e

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
DOOM_DIR=${DOOM_DIR:-/opt/doomgeneric}
# Il binario compilato sta nello stato, non nel programma. Non e' pignoleria:
# l'aggiornamento OTA cancella e ricopia le sottocartelle di /opt/dmd, quindi
# un binario li' dentro sparirebbe a ogni aggiornamento e si dovrebbero
# aspettare due minuti di compilazione per riaverlo.
STATO=${STATO:-/var/lib/dmd/doom}
FREEDOOM_VER=${FREEDOOM_VER:-0.13.0}

echo "==> Strumenti di compilazione"
MISSING=""
command -v gcc  >/dev/null 2>&1 || MISSING="$MISSING gcc"
command -v make >/dev/null 2>&1 || MISSING="$MISSING make"
command -v git  >/dev/null 2>&1 || MISSING="$MISSING git"
command -v unzip >/dev/null 2>&1 || MISSING="$MISSING unzip"
command -v curl >/dev/null 2>&1 || MISSING="$MISSING curl"
if [ -n "$MISSING" ]; then
    echo "    da installare:$MISSING"
    apt update
    apt install -y $MISSING
else
    echo "    gia' presenti"
fi

echo "==> Sorgenti di doomgeneric in $DOOM_DIR"
if [ -d "$DOOM_DIR/.git" ]; then
    git -C "$DOOM_DIR" pull --ff-only || true
else
    rm -rf "$DOOM_DIR"
    git clone --depth 1 https://github.com/ozkl/doomgeneric.git "$DOOM_DIR"
fi

echo "==> Compilazione in $STATO"
mkdir -p "$STATO"
# Su un Pi 3B+ ci vogliono un paio di minuti. `-j` con il numero di core, ma
# non piu' di due: con quattro processi paralleli e mezzo giga di RAM la
# compilazione va in swap e ci mette di piu'.
CORES=$(nproc)
[ "$CORES" -gt 2 ] && CORES=2
make -C "$SRC_DIR" DOOMGENERIC="$DOOM_DIR/doomgeneric" \
     OUT="$STATO/doom-dmd" OBJDIR="$STATO/build" -j"$CORES"
echo "    fatto: $STATO/doom-dmd"

echo "==> WAD in $STATO"
# Chi ha comprato Doom copia il suo WAD qui e non deve ritrovarsi cinquanta
# megabyte di Freedoom scaricati per niente. I nomi sono quelli di id
# Software; Freedoom e' il ripiego, non la prima scelta.
PROPRIO=""
for nome in doom.wad doom2.wad plutonia.wad tnt.wad doom1.wad; do
    for trovato in "$STATO/$nome" "$STATO/$(echo "$nome" | tr 'a-z' 'A-Z')"; do
        [ -f "$trovato" ] && PROPRIO="$trovato" && break 2
    done
done

if [ -n "$PROPRIO" ]; then
    echo "    trovato un WAD tuo: $PROPRIO"
    echo "    non scarico Freedoom. Se vuoi anche quello, cancella questo file"
    echo "    e rilancia, oppure scaricalo da freedoom.github.io"
elif [ -f "$STATO/freedoom1.wad" ]; then
    echo "    freedoom1.wad gia' presente"
else
    TMP=$(mktemp -d)
    URL="https://github.com/freedoom/freedoom/releases/download/v$FREEDOOM_VER/freedoom-$FREEDOOM_VER.zip"
    echo "    scarico $URL"
    curl -sL -o "$TMP/freedoom.zip" "$URL"
    unzip -o -q "$TMP/freedoom.zip" -d "$TMP"
    find "$TMP" -name 'freedoom*.wad' -exec cp {} "$STATO/" \;
    rm -rf "$TMP"
    ls -l "$STATO"/*.wad
fi

# Doom scrive la configurazione e i salvataggi nella cartella di lavoro: se
# fosse /opt/dmd si sporcherebbe l'installazione e la verifica delle impronte
# fallirebbe al prossimo aggiornamento.
mkdir -p "$STATO/stato"

# Un WAD si riconosce dai primi quattro byte, non dal nome: un file scaricato
# a meta' o rinominato per sbaglio passerebbe il controllo del nome e poi Doom
# si fermerebbe con un errore che non spiega niente.
echo "==> Controllo dei WAD"
BUONI=0
for f in "$STATO"/*.[wW][aA][dD]; do
    [ -f "$f" ] || continue
    TIPO=$(head -c 4 "$f" 2>/dev/null || true)
    DIM=$(stat -c%s "$f" 2>/dev/null || echo 0)
    case "$TIPO" in
        IWAD) if [ "$DIM" -ge 2097152 ]; then
                  echo "    OK   $(basename "$f")  ($((DIM/1048576)) MB)"
                  BUONI=$((BUONI+1))
              else
                  echo "    NO   $(basename "$f"): troppo piccolo, forse scaricato a meta'"
              fi ;;
        PWAD) echo "    NO   $(basename "$f"): e' un'estensione, non un gioco completo" ;;
        *)    echo "    NO   $(basename "$f"): non e' un WAD" ;;
    esac
done
if [ "$BUONI" -eq 0 ]; then
    echo
    echo "Nessun WAD utilizzabile in $STATO."
    echo "Copiane uno li' dentro (doom.wad, doom1.wad, doom2.wad...) e rilancia."
    exit 1
fi

echo
echo "Fatto: $BUONI WAD utilizzabili."
echo "  programma:  $STATO/doom-dmd"
echo
echo "Nella pagina Doom scegli il WAD, poi accendi il servizio nella pagina"
echo "Servizi."
