from typing import Dict, List, Optional

from pydantic import BaseModel


class Abschnitt(BaseModel):
    """Repräsentiert einen Abschnitt innerhalb eines Regulierungsdokuments"""

    abschnitt_nummer: int
    titel: str
    abschnitt_quelle: Optional[str] = None


class Dokument(BaseModel):
    """Repräsentiert ein vollständiges Regulierungsdokument mit seinen Abschnitten"""

    titel: str
    dokument_quelle: Optional[str] = None
    herausgeber: Optional[str] = None
    abschnitte: List[Abschnitt] = []


class DokumentChunk(BaseModel):
    """Repräsentiert einen Text-Chunk aus einem Dokument für die Vektorspeicherung"""

    inhalt: str
    dokument_titel: str
    abschnitt_nummer: Optional[int] = None
    chunk_index: int
