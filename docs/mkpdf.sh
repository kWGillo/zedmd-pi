#!/bin/sh
# Rigenera i PDF dei manuali dai .md.
#
# Serve pandoc e wkhtmltopdf. I PDF **non** vanno in /opt/dmd: sul Raspberry
# non servono, e l'aggiornamento via rete copia soltanto cio' che il servizio
# esegue. Stanno in docs/ solo per essere letti offline o stampati.
#
# Uso:   sh mkpdf.sh /percorso/della/cartella/docs [nome.it.md ...]
#        senza argomenti dopo la cartella, li rifa' tutti.
set -e

DOCS="${1:-docs}"
shift 2>/dev/null || true

if [ ! -d "$DOCS" ]; then
    echo "cartella non trovata: $DOCS" >&2
    exit 1
fi

STILE=$(mktemp /tmp/dmdstile.XXXXXX.css)
trap 'rm -f "$STILE"' EXIT

cat > "$STILE" <<'CSS'
body {
    font-family: "DejaVu Sans", sans-serif;
    font-size: 10.5pt;
    line-height: 1.5;
    color: #333;
    margin: 0;
    padding: 0 8mm;
}
h1, h2, h3, h4 {
    color: #1f5c99;
    font-weight: bold;
    line-height: 1.25;
}
h1.title {
    font-size: 15pt;
    border-bottom: 2px solid #1f5c99;
    padding-bottom: 6px;
    margin-bottom: 24px;
}
h1 { font-size: 16pt; border-bottom: 2px solid #1f5c99; padding-bottom: 6px;
     margin-top: 26px; }
h2 { font-size: 13pt; margin-top: 24px; }
h3 { font-size: 11.5pt; margin-top: 18px; }
h4 { font-size: 10.5pt; margin-top: 14px; }
p { margin: 0 0 10px 0; }
a { color: #1f5c99; text-decoration: none; }
ul, ol { margin: 0 0 10px 0; padding-left: 34px; }
li { margin-bottom: 4px; }
hr { border: 0; border-top: 1px solid #dcdcdc; margin: 20px 0; }
code {
    font-family: "DejaVu Sans Mono", monospace;
    font-size: 9pt;
    background: #f6f8fa;
    border: 1px solid #dfe3e8;
    border-radius: 3px;
    padding: 0 3px;
}
pre {
    background: #f6f8fa;
    border-left: 4px solid #1f5c99;
    padding: 8px 12px;
    margin: 12px 0;
    /* Un blocco di comandi spezzato a meta' fra due pagine e' illeggibile e
       si copia male. */
    page-break-inside: avoid;
}
pre code { background: none; border: 0; padding: 0; font-size: 9pt; }
blockquote {
    background: #fdf8ec;
    border-left: 4px solid #e8b84b;
    margin: 14px 0;
    padding: 10px 14px;
    page-break-inside: avoid;
}
blockquote p:last-child { margin-bottom: 0; }
table {
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 9.5pt;
    page-break-inside: avoid;
}
th, td {
    border: 1px solid #dcdcdc;
    padding: 5px 9px;
    text-align: left;
    vertical-align: top;
}
th { background: #f0f4f8; color: #1f5c99; }
img { max-width: 100%; }
/* Un titolo in fondo alla pagina con il testo nella successiva e' la cosa
   che fa sembrare stampato male un documento fatto bene. */
h1, h2, h3, h4 { page-break-after: avoid; }
CSS

fai() {
    sorgente="$1"
    base=$(basename "$sorgente" .it.md)
    # DMD_now_playing.pdf da now-playing.it.md: i trattini diventano _
    nome=$(echo "$base" | tr '-' '_')
    uscita="$DOCS/DMD_${nome}.pdf"
    # Il titolo e' il primo titolo di primo livello del documento.
    titolo=$(sed -n 's/^# //p' "$sorgente" | head -1)
    tmphtml=$(mktemp /tmp/dmdpdf.XXXXXX.html)
    pandoc "$sorgente" \
        --standalone \
        --from=gfm \
        --to=html5 \
        --css="$STILE" \
        --self-contained \
        --output="$tmphtml" 2>/dev/null \
    || pandoc "$sorgente" --standalone --from=gfm --to=html5 \
        --css="$STILE" --embed-resources \
        --output="$tmphtml"
    wkhtmltopdf \
        --quiet \
        --page-size A4 \
        --margin-top 18mm --margin-bottom 18mm \
        --margin-left 34mm --margin-right 34mm \
        --encoding utf-8 \
        --disable-smart-shrinking \
        --enable-local-file-access \
        "$tmphtml" "$uscita"
    rm -f "$tmphtml"
    echo "  $uscita"
}

if [ $# -gt 0 ]; then
    for f in "$@"; do
        case "$f" in
            /*) fai "$f" ;;
            *)  fai "$DOCS/$f" ;;
        esac
    done
else
    for f in "$DOCS"/*.it.md; do
        case "$(basename "$f")" in
            README.it.md|pubblicazione.it.md) continue ;;
        esac
        fai "$f"
    done
fi
