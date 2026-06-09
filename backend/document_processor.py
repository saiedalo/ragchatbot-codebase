import os
import re
from typing import List, Optional, Tuple
from models import Abschnitt, Dokument, DokumentChunk


class DocumentProcessor:
    """Verarbeitet Regulierungsdokumente im Textformat und extrahiert strukturierte Informationen"""

    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def read_file(self, file_path: str) -> str:
        """Liest Dateiinhalt mit UTF-8 Kodierung"""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                return file.read()

    def chunk_text(self, text: str) -> List[str]:
        """Teilt Text in satzbasierte Chunks mit Überlappung auf"""

        text = re.sub(r"\s+", " ", text.strip())

        sentence_endings = re.compile(
            r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\!|\?)\s+(?=[A-Z])"
        )
        sentences = sentence_endings.split(text)

        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        i = 0

        while i < len(sentences):
            current_chunk = []
            current_size = 0

            for j in range(i, len(sentences)):
                sentence = sentences[j]

                space_size = 1 if current_chunk else 0
                total_addition = len(sentence) + space_size

                if current_size + total_addition > self.chunk_size and current_chunk:
                    break

                current_chunk.append(sentence)
                current_size += total_addition

            if current_chunk:
                chunks.append(" ".join(current_chunk))

                if hasattr(self, "chunk_overlap") and self.chunk_overlap > 0:
                    overlap_size = 0
                    overlap_sentences = 0

                    for k in range(len(current_chunk) - 1, -1, -1):
                        sentence_len = len(current_chunk[k]) + (
                            1 if k < len(current_chunk) - 1 else 0
                        )
                        if overlap_size + sentence_len <= self.chunk_overlap:
                            overlap_size += sentence_len
                            overlap_sentences += 1
                        else:
                            break

                    next_start = i + len(current_chunk) - overlap_sentences
                    i = max(next_start, i + 1)
                else:
                    i += len(current_chunk)
            else:
                i += 1

        return chunks

    def process_document(
        self, file_path: str
    ) -> Tuple[Dokument, List[DokumentChunk]]:
        """
        Verarbeitet ein Textdokument im Format:
        Zeile 1: Dokument-Titel: [titel]
        Zeile 2: Dokument-Quelle: [url]
        Zeile 3: Herausgeber: [herausgeber]
        Folgezeilen: Abschnitt-Marker und Inhalt
        """
        content = self.read_file(file_path)
        filename = os.path.basename(file_path)

        lines = content.strip().split("\n")

        dokument_titel = filename
        dokument_quelle = None
        herausgeber_name = "Unbekannt"

        if len(lines) >= 1 and lines[0].strip():
            titel_match = re.match(
                r"^Dokument-Titel:\s*(.+)$", lines[0].strip(), re.IGNORECASE
            )
            if titel_match:
                dokument_titel = titel_match.group(1).strip()
            else:
                dokument_titel = lines[0].strip()

        for i in range(1, min(len(lines), 4)):
            line = lines[i].strip()
            if not line:
                continue

            quelle_match = re.match(r"^Dokument-Quelle:\s*(.+)$", line, re.IGNORECASE)
            if quelle_match:
                dokument_quelle = quelle_match.group(1).strip()
                continue

            herausgeber_match = re.match(
                r"^Herausgeber:\s*(.+)$", line, re.IGNORECASE
            )
            if herausgeber_match:
                herausgeber_name = herausgeber_match.group(1).strip()
                continue

        dokument = Dokument(
            titel=dokument_titel,
            dokument_quelle=dokument_quelle,
            herausgeber=herausgeber_name if herausgeber_name != "Unbekannt" else None,
        )

        dokument_chunks = []
        aktueller_abschnitt = None
        abschnitt_titel = None
        abschnitt_quelle = None
        abschnitt_inhalt = []
        chunk_counter = 0

        start_index = 3
        if len(lines) > 3 and not lines[3].strip():
            start_index = 4

        i = start_index
        while i < len(lines):
            line = lines[i]

            abschnitt_match = re.match(
                r"^Abschnitt\s+(\d+):\s*(.+)$", line.strip(), re.IGNORECASE
            )

            if abschnitt_match:
                if aktueller_abschnitt is not None and abschnitt_inhalt:
                    abschnitt_text = "\n".join(abschnitt_inhalt).strip()
                    if abschnitt_text:
                        abschnitt = Abschnitt(
                            abschnitt_nummer=aktueller_abschnitt,
                            titel=abschnitt_titel,
                            abschnitt_quelle=abschnitt_quelle,
                        )
                        dokument.abschnitte.append(abschnitt)

                        chunks = self.chunk_text(abschnitt_text)
                        for idx, chunk in enumerate(chunks):
                            if idx == 0:
                                chunk_mit_kontext = (
                                    f"Abschnitt {aktueller_abschnitt} Inhalt: {chunk}"
                                )
                            else:
                                chunk_mit_kontext = chunk

                            dok_chunk = DokumentChunk(
                                inhalt=chunk_mit_kontext,
                                dokument_titel=dokument.titel,
                                abschnitt_nummer=aktueller_abschnitt,
                                chunk_index=chunk_counter,
                            )
                            dokument_chunks.append(dok_chunk)
                            chunk_counter += 1

                aktueller_abschnitt = int(abschnitt_match.group(1))
                abschnitt_titel = abschnitt_match.group(2).strip()
                abschnitt_quelle = None

                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    quelle_match = re.match(
                        r"^Abschnitt-Quelle:\s*(.+)$", next_line, re.IGNORECASE
                    )
                    if quelle_match:
                        abschnitt_quelle = quelle_match.group(1).strip()
                        i += 1

                abschnitt_inhalt = []
            else:
                abschnitt_inhalt.append(line)

            i += 1

        if aktueller_abschnitt is not None and abschnitt_inhalt:
            abschnitt_text = "\n".join(abschnitt_inhalt).strip()
            if abschnitt_text:
                abschnitt = Abschnitt(
                    abschnitt_nummer=aktueller_abschnitt,
                    titel=abschnitt_titel,
                    abschnitt_quelle=abschnitt_quelle,
                )
                dokument.abschnitte.append(abschnitt)

                chunks = self.chunk_text(abschnitt_text)
                for chunk in chunks:
                    chunk_mit_kontext = f"Dokument {dokument_titel} Abschnitt {aktueller_abschnitt} Inhalt: {chunk}"

                    dok_chunk = DokumentChunk(
                        inhalt=chunk_mit_kontext,
                        dokument_titel=dokument.titel,
                        abschnitt_nummer=aktueller_abschnitt,
                        chunk_index=chunk_counter,
                    )
                    dokument_chunks.append(dok_chunk)
                    chunk_counter += 1

        if not dokument_chunks and len(lines) > 2:
            remaining_content = "\n".join(lines[start_index:]).strip()
            if remaining_content:
                chunks = self.chunk_text(remaining_content)
                for chunk in chunks:
                    dok_chunk = DokumentChunk(
                        inhalt=chunk,
                        dokument_titel=dokument.titel,
                        chunk_index=chunk_counter,
                    )
                    dokument_chunks.append(dok_chunk)
                    chunk_counter += 1

        return dokument, dokument_chunks


class PDFDocumentProcessor:
    """Verarbeitet PDF-Regulierungsdokumente von BaFin, Bundesbank und EZB"""

    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._text_processor = DocumentProcessor(chunk_size, chunk_overlap)

    def process_pdf_document(
        self, file_path: str
    ) -> Tuple[Dokument, List[DokumentChunk]]:
        """Verarbeitet ein PDF-Regulierungsdokument und extrahiert Struktur und Inhalt"""
        import pdfplumber

        filename = os.path.basename(file_path)

        with pdfplumber.open(file_path) as pdf:
            titel, herausgeber = self._extract_title_and_publisher(pdf)
            if not titel:
                titel = os.path.splitext(filename)[0]

            pages_text = self._extract_pages_text(pdf)
            abschnitt_grenzen = self._detect_section_headings(pages_text, pdf)

        dokument = Dokument(
            titel=titel,
            dokument_quelle=file_path,
            herausgeber=herausgeber,
        )

        full_text = "\n".join(pages_text)

        if len(abschnitt_grenzen) < 2:
            abschnitt = Abschnitt(
                abschnitt_nummer=0,
                titel="Volltext",
                abschnitt_quelle=None,
            )
            dokument.abschnitte.append(abschnitt)

            chunks = self._text_processor.chunk_text(full_text)
            dokument_chunks = [
                DokumentChunk(
                    inhalt=chunk,
                    dokument_titel=dokument.titel,
                    abschnitt_nummer=0,
                    chunk_index=idx,
                )
                for idx, chunk in enumerate(chunks)
            ]
            return dokument, dokument_chunks

        dokument_chunks = []
        chunk_counter = 0

        for abs_idx, (char_start, abs_titel) in enumerate(abschnitt_grenzen):
            abs_nummer = abs_idx + 1

            char_end = (
                abschnitt_grenzen[abs_idx + 1][0]
                if abs_idx + 1 < len(abschnitt_grenzen)
                else len(full_text)
            )
            abschnitt_text = full_text[char_start:char_end].strip()

            abschnitt = Abschnitt(
                abschnitt_nummer=abs_nummer,
                titel=abs_titel,
                abschnitt_quelle=None,
            )
            dokument.abschnitte.append(abschnitt)

            if abschnitt_text:
                chunks = self._text_processor.chunk_text(abschnitt_text)
                for idx, chunk in enumerate(chunks):
                    if idx == 0:
                        chunk_mit_kontext = f"Abschnitt {abs_nummer} Inhalt: {chunk}"
                    else:
                        chunk_mit_kontext = chunk

                    dok_chunk = DokumentChunk(
                        inhalt=chunk_mit_kontext,
                        dokument_titel=dokument.titel,
                        abschnitt_nummer=abs_nummer,
                        chunk_index=chunk_counter,
                    )
                    dokument_chunks.append(dok_chunk)
                    chunk_counter += 1

        return dokument, dokument_chunks

    def _extract_pages_text(self, pdf) -> List[str]:
        """Extrahiert Text jeder Seite und bereinigt Kopf-/Fußzeilen"""
        pages_text = []

        recurring_lines: dict = {}
        all_page_lines = []
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            all_page_lines.append(lines)
            for line in lines[:3] + lines[-2:]:
                recurring_lines[line] = recurring_lines.get(line, 0) + 1

        total_pages = len(pdf.pages)
        noise_threshold = max(2, total_pages // 3)
        noise_set = {l for l, c in recurring_lines.items() if c >= noise_threshold}

        for lines in all_page_lines:
            filtered = [l for l in lines if l not in noise_set]
            pages_text.append("\n".join(filtered))

        return pages_text

    def _detect_section_headings(
        self, pages_text: List[str], pdf
    ) -> List[Tuple[int, str]]:
        """Erkennt Abschnittsüberschriften im Text regulatorischer PDF-Dokumente"""
        full_text = "\n".join(pages_text)
        lines = full_text.split("\n")

        heading_patterns = [
            re.compile(r"^(AT|BT[A-Z]|Anlage|MaRisk|BAIT)\s+\d+(\.\d+)*\b"),
            re.compile(r"^\d+(\.\d+)*\.?\s{2,}\S"),
            re.compile(r"^(Abschnitt|Kapitel|Teil)\s+[A-Z0-9]", re.IGNORECASE),
            re.compile(r"^[IVX]+\.\s+[A-ZÄÖÜ]"),
        ]

        headings: List[Tuple[int, str]] = []
        char_pos = 0

        for line in lines:
            stripped = line.strip()
            if stripped and any(p.match(stripped) for p in heading_patterns):
                if len(stripped) < 120:
                    headings.append((char_pos, stripped))
            char_pos += len(line) + 1

        return headings

    def _extract_title_and_publisher(
        self, pdf
    ) -> Tuple[str, Optional[str]]:
        """Extrahiert Titel und Herausgeber aus den ersten Seiten des PDFs"""
        titel = ""
        herausgeber = None

        publisher_keywords = [
            "bundesanstalt für finanzdienstleistungsaufsicht",
            "bafin",
            "deutsche bundesbank",
            "europäische zentralbank",
            "european central bank",
            "ecb",
            "bundesministerium",
        ]

        first_pages = pdf.pages[:min(3, len(pdf.pages))]

        for page in first_pages:
            text = page.extract_text() or ""
            lines = [l.strip() for l in text.split("\n") if l.strip()]

            for line in lines:
                line_lower = line.lower()
                for keyword in publisher_keywords:
                    if keyword in line_lower:
                        herausgeber = line
                        break

            if not titel and lines:
                chars = page.chars
                if chars:
                    try:
                        sizes = [float(c.get("size", 0)) for c in chars if c.get("size")]
                        if sizes:
                            max_size = max(sizes)
                            title_chars = [
                                c for c in chars
                                if float(c.get("size", 0)) >= max_size * 0.9
                            ]
                            if title_chars:
                                titel = "".join(
                                    c.get("text", "") for c in title_chars
                                ).strip()
                    except (TypeError, ValueError):
                        pass

            if not titel and lines:
                for line in lines[:5]:
                    if len(line) > 10 and not any(
                        kw in line.lower() for kw in publisher_keywords
                    ):
                        titel = line
                        break

        return titel, herausgeber
