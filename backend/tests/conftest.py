import os
import sys
import tempfile
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from models import Abschnitt, Dokument, DokumentChunk
from vector_store import SearchResults


@pytest.fixture
def sample_dokument():
    """Erstellt ein Beispieldokument für Tests"""
    abschnitte = [
        Abschnitt(
            abschnitt_nummer=1,
            titel="Anwendungsbereich",
            abschnitt_quelle="https://example.com/abschnitt1",
        ),
        Abschnitt(
            abschnitt_nummer=2,
            titel="Anforderungen an das Risikomanagement",
            abschnitt_quelle="https://example.com/abschnitt2",
        ),
        Abschnitt(
            abschnitt_nummer=3,
            titel="Schlussbestimmungen",
            abschnitt_quelle="https://example.com/abschnitt3",
        ),
    ]

    return Dokument(
        titel="MaRisk - Mindestanforderungen an das Risikomanagement",
        dokument_quelle="https://example.com/marisk",
        herausgeber="BaFin",
        abschnitte=abschnitte,
    )


@pytest.fixture
def sample_dokument_chunks():
    """Erstellt Beispiel-Chunks für Tests"""
    return [
        DokumentChunk(
            inhalt="Willkommen zu den MaRisk. Dieses Rundschreiben enthält Mindestanforderungen an das Risikomanagement.",
            dokument_titel="MaRisk - Mindestanforderungen an das Risikomanagement",
            abschnitt_nummer=1,
            chunk_index=0,
        ),
        DokumentChunk(
            inhalt="In diesem Abschnitt werden die Anforderungen an die Risikosteuerung und -überwachung erläutert.",
            dokument_titel="MaRisk - Mindestanforderungen an das Risikomanagement",
            abschnitt_nummer=2,
            chunk_index=1,
        ),
        DokumentChunk(
            inhalt="Die Kreditinstitute haben geeignete Prozesse zur Identifizierung, Beurteilung und Überwachung von Risiken einzurichten.",
            dokument_titel="MaRisk - Mindestanforderungen an das Risikomanagement",
            abschnitt_nummer=1,
            chunk_index=2,
        ),
    ]


@pytest.fixture
def sample_search_results():
    """Erstellt Beispiel-Suchergebnisse für Tests"""
    return SearchResults(
        documents=[
            "Willkommen zu den MaRisk. Dieses Rundschreiben enthält Mindestanforderungen an das Risikomanagement.",
            "In diesem Abschnitt werden die Anforderungen an die Risikosteuerung erläutert.",
        ],
        metadata=[
            {
                "dokument_titel": "MaRisk - Mindestanforderungen an das Risikomanagement",
                "abschnitt_nummer": 1,
                "chunk_index": 0,
            },
            {
                "dokument_titel": "MaRisk - Mindestanforderungen an das Risikomanagement",
                "abschnitt_nummer": 2,
                "chunk_index": 1,
            },
        ],
        distances=[0.1, 0.2],
    )


@pytest.fixture
def empty_search_results():
    """Erstellt leere Suchergebnisse für Tests"""
    return SearchResults(documents=[], metadata=[], distances=[])


@pytest.fixture
def error_search_results():
    """Erstellt Fehler-Suchergebnisse für Tests"""
    return SearchResults.empty("Suchfehler: Datenbankverbindung fehlgeschlagen")


@pytest.fixture
def mock_vector_store():
    """Erstellt einen Mock-Vektorspeicher für Tests"""
    mock = Mock()
    mock.search.return_value = SearchResults(
        documents=["Beispiel-Dokumentinhalt"],
        metadata=[{"dokument_titel": "Test Dokument", "abschnitt_nummer": 1}],
        distances=[0.1],
    )
    mock._resolve_dokument_name.return_value = "Test Dokument"
    mock.get_abschnitt_quelle.return_value = "https://example.com/abschnitt1"
    return mock


@pytest.fixture
def mock_anthropic_client():
    """Erstellt einen Mock Anthropic-Client für Tests"""
    mock_client = Mock()

    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = "Dies ist eine Testantwort von Claude."
    mock_response.stop_reason = "end_turn"

    mock_tool_response = Mock()
    mock_tool_response.stop_reason = "tool_use"
    mock_tool_content = Mock()
    mock_tool_content.type = "tool_use"
    mock_tool_content.name = "regulierungsdokument_suchen"
    mock_tool_content.id = "tool_123"
    mock_tool_content.input = {"suchanfrage": "Testanfrage"}
    mock_tool_response.content = [mock_tool_content]

    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_tool_manager():
    """Erstellt einen Mock-Werkzeugmanager für Tests"""
    mock = Mock()
    mock.get_tool_definitions.return_value = [
        {
            "name": "regulierungsdokument_suchen",
            "description": "Durchsucht Regulierungsdokumente",
            "input_schema": {
                "type": "object",
                "properties": {
                    "suchanfrage": {"type": "string", "description": "Was gesucht werden soll"}
                },
                "required": ["suchanfrage"],
            },
        }
    ]
    mock.execute_tool.return_value = "Mock-Suchergebnis"
    mock.get_last_sources.return_value = ["MaRisk - Abschnitt 1"]
    mock.get_last_source_links.return_value = ["https://example.com/abschnitt1"]
    return mock


@pytest.fixture
def test_config():
    """Erstellt eine Testkonfiguration mit korrekten Einstellungen"""
    return Config(
        ANTHROPIC_API_KEY="test-api-key",
        ANTHROPIC_MODEL="claude-sonnet-4-6",
        EMBEDDING_MODEL="all-MiniLM-L6-v2",
        CHUNK_SIZE=800,
        CHUNK_OVERLAP=100,
        MAX_RESULTS=5,
        MAX_HISTORY=2,
        CHROMA_PATH="./test_chroma_db",
    )


@pytest.fixture
def broken_config():
    """Erstellt eine Konfiguration mit defektem MAX_RESULTS=0"""
    return Config(
        ANTHROPIC_API_KEY="test-api-key",
        ANTHROPIC_MODEL="claude-sonnet-4-6",
        EMBEDDING_MODEL="all-MiniLM-L6-v2",
        CHUNK_SIZE=800,
        CHUNK_OVERLAP=100,
        MAX_RESULTS=0,
        MAX_HISTORY=2,
        CHROMA_PATH="./test_chroma_db",
    )


@pytest.fixture
def temp_chroma_db():
    """Erstellt ein temporäres ChromaDB-Verzeichnis für Tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    import shutil

    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def mock_chroma_collection():
    """Erstellt eine Mock ChromaDB-Collection für Tests"""
    mock = Mock()
    mock.query.return_value = {
        "documents": [["Beispiel Dokument"]],
        "metadatas": [[{"dokument_titel": "Test Dokument", "abschnitt_nummer": 1}]],
        "distances": [[0.1]],
    }
    mock.get.return_value = {
        "ids": ["test_dokument_1"],
        "metadatas": [
            {
                "titel": "Test Dokument",
                "herausgeber": "BaFin",
                "dokument_quelle": "https://example.com/dokument",
                "abschnitte_json": '[{"abschnitt_nummer": 1, "abschnitt_titel": "Abschnitt 1", "abschnitt_quelle": "https://example.com/abschnitt1"}]',
                "abschnitt_anzahl": 1,
            }
        ],
    }
    return mock


# Test-Datenkonstanten
SAMPLE_DOKUMENT_TEXT = """Dokument-Titel: MaRisk - Mindestanforderungen an das Risikomanagement
Dokument-Quelle: https://www.bafin.de/marisk
Herausgeber: BaFin

Abschnitt 1: Anwendungsbereich
Abschnitt-Quelle: https://www.bafin.de/marisk/abschnitt1
Dieses Rundschreiben richtet sich an alle Kreditinstitute im Sinne des KWG.

Abschnitt 2: Anforderungen an das Risikomanagement
Abschnitt-Quelle: https://www.bafin.de/marisk/abschnitt2
Die Institute haben angemessene Prozesse zur Identifizierung und Steuerung von Risiken einzurichten.
"""

SAMPLE_QUERY_RESPONSES = {
    "allgemein": "Dies ist eine allgemeine Wissensantwort.",
    "regulierungsspezifisch": "Basierend auf den Suchergebnissen hier die regulatorischen Anforderungen.",
    "werkzeugnutzung": "Ich suche nach den relevanten Informationen in den Regulierungsdokumenten.",
}


@pytest.fixture
def mock_rag_system():
    """Erstellt ein Mock-RAG-System für API-Tests"""
    mock = Mock()
    mock.query.return_value = (
        "Dies ist eine Testantwort zu den Regulierungsanforderungen.",
        ["MaRisk - Mindestanforderungen - Abschnitt 1"],
        ["https://example.com/abschnitt1"],
    )
    mock.get_dokument_statistiken.return_value = {
        "gesamt_dokumente": 2,
        "dokument_titel": [
            "MaRisk - Mindestanforderungen an das Risikomanagement",
            "BAIT - Bankaufsichtliche Anforderungen an die IT",
        ],
    }
    mock.session_manager.create_session.return_value = "test-session-123"
    mock.session_manager.clear_session.return_value = None
    return mock


@pytest.fixture
def test_app():
    """Erstellt eine Test-FastAPI-App mit gemockten Abhängigkeiten"""
    from typing import List, Optional

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from pydantic import BaseModel

    app = FastAPI(title="Regulierungs-Assistent RAG System Test", root_path="")

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[str]
        source_links: List[Optional[str]]
        session_id: str

    class DokumentStats(BaseModel):
        gesamt_dokumente: int
        dokument_titel: List[str]

    class ClearSessionRequest(BaseModel):
        session_id: str

    mock_rag = Mock()
    mock_rag.query.return_value = (
        "Dies ist eine Testantwort zu den Regulierungsanforderungen.",
        ["MaRisk - Mindestanforderungen - Abschnitt 1"],
        ["https://example.com/abschnitt1"],
    )
    mock_rag.get_dokument_statistiken.return_value = {
        "gesamt_dokumente": 2,
        "dokument_titel": [
            "MaRisk - Mindestanforderungen an das Risikomanagement",
            "BAIT - Bankaufsichtliche Anforderungen an die IT",
        ],
    }
    mock_rag.session_manager.create_session.return_value = "test-session-123"
    mock_rag.session_manager.clear_session.return_value = None

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        session_id = request.session_id or mock_rag.session_manager.create_session()
        answer, sources, source_links = mock_rag.query(request.query, session_id)
        return QueryResponse(
            answer=answer,
            sources=sources,
            source_links=source_links,
            session_id=session_id,
        )

    @app.get("/api/dokumente", response_model=DokumentStats)
    async def get_dokument_stats():
        statistiken = mock_rag.get_dokument_statistiken()
        return DokumentStats(
            gesamt_dokumente=statistiken["gesamt_dokumente"],
            dokument_titel=statistiken["dokument_titel"],
        )

    @app.post("/api/clear-session")
    async def clear_session(request: ClearSessionRequest):
        mock_rag.session_manager.clear_session(request.session_id)
        return {"status": "success", "message": "Sitzung erfolgreich gelöscht"}

    @app.get("/")
    async def root():
        return {"message": "Regulierungs-Assistent RAG System API"}

    return app


@pytest.fixture
def client(test_app):
    """Erstellt einen Test-Client für die FastAPI-App"""
    return TestClient(test_app)


@pytest.fixture
def sample_query_request():
    """Beispiel-Anfrage für Tests"""
    return {
        "query": "Was sind die MaRisk-Anforderungen an das Risikomanagement?",
        "session_id": "test-session-123",
    }


@pytest.fixture
def sample_clear_session_request():
    """Beispiel-Anfrage zum Löschen einer Sitzung"""
    return {"session_id": "test-session-123"}
