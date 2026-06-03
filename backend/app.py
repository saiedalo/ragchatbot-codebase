import warnings

warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

import os
import shutil
from typing import List, Optional

from config import config
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Regulierungs-Assistent RAG System", root_path="")

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# RAG-System wird im Startup-Event initialisiert
rag_system = None


class QueryRequest(BaseModel):
    """Anfrage-Modell für Regulierungsanfragen"""

    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    """Antwort-Modell für Regulierungsanfragen"""

    answer: str
    sources: List[str]
    source_links: List[Optional[str]]
    session_id: str


class DokumentInfo(BaseModel):
    """Einzelnes Dokument mit Metadaten"""

    titel: str
    herausgeber: str = ""
    dokument_quelle: str = ""


class DokumentStats(BaseModel):
    """Antwort-Modell für Dokumentstatistiken"""

    gesamt_dokumente: int
    dokument_titel: List[str]
    dokumente: List[DokumentInfo] = []


class ClearSessionRequest(BaseModel):
    """Anfrage-Modell zum Löschen einer Sitzung"""

    session_id: str


# API-Endpunkte


@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Verarbeitet eine Anfrage und gibt die Antwort mit Quellen zurück"""
    try:
        session_id = request.session_id
        if not session_id:
            session_id = rag_system.session_manager.create_session()

        answer, sources, source_links = rag_system.query(request.query, session_id)

        return QueryResponse(
            answer=answer,
            sources=sources,
            source_links=source_links,
            session_id=session_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dokumente", response_model=DokumentStats)
async def get_dokument_stats():
    """Gibt Dokumentstatistiken zurück"""
    try:
        statistiken = rag_system.get_dokument_statistiken()
        dokumente = [
            DokumentInfo(
                titel=d["titel"],
                herausgeber=d.get("herausgeber", ""),
                dokument_quelle=d.get("dokument_quelle", ""),
            )
            for d in statistiken.get("dokumente", [])
        ]
        return DokumentStats(
            gesamt_dokumente=statistiken["gesamt_dokumente"],
            dokument_titel=statistiken["dokument_titel"],
            dokumente=dokumente,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/clear-session")
async def clear_session(request: ClearSessionRequest):
    """Löscht eine Gesprächssitzung"""
    try:
        rag_system.session_manager.clear_session(request.session_id)
        return {"status": "success", "message": "Sitzung erfolgreich gelöscht"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _migrate_chroma_if_needed(chroma_path: str) -> None:
    """Löscht altes ChromaDB-Schema wenn alte Collections (course_catalog) erkannt werden"""
    if not os.path.exists(chroma_path):
        return
    try:
        import chromadb
        from chromadb.config import Settings

        temp_client = chromadb.PersistentClient(
            path=chroma_path, settings=Settings(anonymized_telemetry=False)
        )
        existing = [c.name for c in temp_client.list_collections()]
        if "course_catalog" in existing or "course_content" in existing:
            print("Altes Datenbankschema erkannt — bereinige ChromaDB...")
            del temp_client
            shutil.rmtree(chroma_path)
            print("ChromaDB bereinigt. Neues Schema wird erstellt.")
    except Exception:
        pass


@app.on_event("startup")
async def startup_event():
    """Lädt initiale Dokumente beim Start"""
    global rag_system

    _migrate_chroma_if_needed(config.CHROMA_PATH)

    from rag_system import RAGSystem

    rag_system = RAGSystem(config)

    docs_path = "../docs"
    if os.path.exists(docs_path):
        print("Lade regulatorische Dokumente...")
        try:
            dokumente, chunks = rag_system.add_dokument_ordner(
                docs_path, clear_existing=False
            )
            print(f"{dokumente} Dokumente mit {chunks} Chunks geladen")
        except Exception as e:
            print(f"Fehler beim Laden der Dokumente: {e}")


from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


class DevStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, FileResponse):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")
