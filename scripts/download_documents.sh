#!/bin/bash
# Lädt öffentliche BaFin/Bundesbank-Regulierungsdokumente herunter
# Ausführung vom Projektstamm: bash scripts/download_documents.sh

DOCS_DIR="./docs"
mkdir -p "$DOCS_DIR"

# BaFin BAIT - Bankaufsichtliche Anforderungen an die IT
BAIT_URL="https://www.bafin.de/SharedDocs/Downloads/DE/Rundschreiben/dl_rs_1710_ba_BAIT.pdf?__blob=publicationFile&v=8"
BAIT_FILE="$DOCS_DIR/bafin_bait.pdf"

# Deutsche Bundesbank - Merkblatt Finanzdienstleistungen
BUNDESBANK_URL="https://www.bundesbank.de/resource/blob/622722/78b881d48752aff3037adec5290d77ce/mL/merkblatt-finanzdienstleistungen-data.pdf"
BUNDESBANK_FILE="$DOCS_DIR/bundesbank_finanzdienstleistungen.pdf"

# BaFin MaRisk - Mindestanforderungen an das Risikomanagement (manuelle Anleitung)
MARISK_FILE="$DOCS_DIR/bafin_marisk.pdf"

# BaFin GwG-Auslegungs- und Anwendungshinweise (manuelle Anleitung)
GWG_FILE="$DOCS_DIR/bafin_gwg_hinweise.pdf"

download_pdf() {
    local url="$1"
    local file="$2"
    local name="$3"

    if [ -f "$file" ]; then
        echo "Bereits vorhanden: $name ($file)"
        return 0
    fi

    echo "Lade herunter: $name..."
    if curl -L --max-time 120 --retry 3 --retry-delay 5 \
        -H "User-Agent: Mozilla/5.0 (compatible; educational-use)" \
        -o "$file" "$url" 2>/dev/null; then

        # Prüfe PDF-Signatur (magic bytes %PDF)
        local magic
        magic=$(head -c 4 "$file" 2>/dev/null | tr -d '\n')
        if echo "$magic" | grep -q "%PDF"; then
            local size
            size=$(wc -c < "$file" 2>/dev/null || echo 0)
            if [ "$size" -gt 10000 ]; then
                echo "✓ Erfolgreich: $name ($(( size / 1024 )) KB)"
                return 0
            else
                echo "WARNUNG: Datei zu klein für $name (${size} Bytes)"
                rm -f "$file"
            fi
        else
            echo "FEHLER: Heruntergeladene Datei ist kein PDF (evtl. URL-Redirect): $name"
            rm -f "$file"
        fi
    else
        echo "FEHLER: Download fehlgeschlagen für: $name"
    fi

    return 1
}

echo "=== Regulierungs-Assistent: Dokument-Download ==="
echo ""

download_pdf "$BAIT_URL" "$BAIT_FILE" "BaFin BAIT (Rundschreiben 10/2017)"
download_pdf "$BUNDESBANK_URL" "$BUNDESBANK_FILE" "Bundesbank Merkblatt Finanzdienstleistungen"

echo ""

# Hinweis für Dokumente mit geänderter BaFin-URL
if [ ! -f "$MARISK_FILE" ] || [ ! -f "$GWG_FILE" ]; then
    echo "--- Manuelle Downloads erforderlich ---"
    echo ""
    echo "Die BaFin ändert regelmäßig ihre Download-URLs."
    echo "Folgende Dokumente müssen manuell heruntergeladen werden:"
    echo ""
    if [ ! -f "$MARISK_FILE" ]; then
        echo "  MaRisk (Mindestanforderungen Risikomanagement):"
        echo "  → https://www.bafin.de/DE/Aufsicht/BankenFinanzdienstleister/Aufsichtsrecht/Rundschreiben/rundschreiben_node.html"
        echo "    Suche: 'MaRisk' → PDF speichern als: $MARISK_FILE"
        echo ""
    fi
    if [ ! -f "$GWG_FILE" ]; then
        echo "  GwG-Auslegungshinweise (Geldwäscheprävention):"
        echo "  → https://www.bafin.de/DE/Aufsicht/BankenFinanzdienstleister/Bekaempfung_Geldwaesche/bek_geldwaesche_node.html"
        echo "    Suche: 'Auslegungs- und Anwendungshinweise' → PDF speichern als: $GWG_FILE"
        echo ""
    fi
fi

echo "=== Download abgeschlossen ==="
echo ""
echo "Vorhandene PDF-Dokumente:"
ls -lh "$DOCS_DIR"/*.pdf 2>/dev/null || echo "Keine PDF-Dateien gefunden."
