import os
from typing import Dict, List, Optional, Tuple

from ai_generator import AIGenerator
from document_processor import DocumentProcessor, PDFDocumentProcessor
from models import Abschnitt, Dokument, DokumentChunk
from search_tools import DokumentStrukturTool, ReguliierungssuchTool, ToolManager
from session_manager import SessionManager
from vector_store import VectorStore


class RAGSystem:
    """Haupt-Orchestrator für das Retrieval-Augmented Generation System"""

    def __init__(self, config) -> None:
        self.config = config

        self.document_processor = DocumentProcessor(
            config.CHUNK_SIZE, config.CHUNK_OVERLAP
        )
        self.pdf_processor = PDFDocumentProcessor(
            config.CHUNK_SIZE, config.CHUNK_OVERLAP
        )
        self.vector_store = VectorStore(
            config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS
        )
        self.ai_generator = AIGenerator(
            config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL
        )
        self.session_manager = SessionManager(config.MAX_HISTORY)

        self.tool_manager = ToolManager()
        self.search_tool = ReguliierungssuchTool(self.vector_store)
        self.outline_tool = DokumentStrukturTool(self.vector_store)
        self.tool_manager.register_tool(self.search_tool)
        self.tool_manager.register_tool(self.outline_tool)

    def add_dokument(self, file_path: str) -> Tuple[Optional[Dokument], int]:
        """
        Fügt ein einzelnes Regulierungsdokument zur Wissensbasis hinzu.

        Args:
            file_path: Pfad zum Dokument

        Returns:
            Tuple aus (Dokument-Objekt, Anzahl erstellter Chunks)
        """
        try:
            if file_path.lower().endswith(".pdf"):
                dokument, dok_chunks = self.pdf_processor.process_pdf_document(
                    file_path
                )
            else:
                dokument, dok_chunks = self.document_processor.process_document(
                    file_path
                )

            self.vector_store.add_dokument_metadata(dokument)
            self.vector_store.add_dokument_inhalt(dok_chunks)

            return dokument, len(dok_chunks)
        except Exception as e:
            print(f"Fehler beim Verarbeiten von {file_path}: {e}")
            return None, 0

    def add_dokument_ordner(
        self, folder_path: str, clear_existing: bool = False
    ) -> Tuple[int, int]:
        """
        Fügt alle Regulierungsdokumente aus einem Ordner hinzu.

        Args:
            folder_path: Pfad zum Ordner mit Dokumenten
            clear_existing: Ob vorhandene Daten vorher gelöscht werden sollen

        Returns:
            Tuple aus (Gesamtanzahl Dokumente, Gesamtanzahl Chunks)
        """
        gesamt_dokumente = 0
        gesamt_chunks = 0

        if clear_existing:
            print("Lösche vorhandene Daten für Neuaufbau...")
            self.vector_store.clear_all_data()

        if not os.path.exists(folder_path):
            print(f"Ordner {folder_path} existiert nicht")
            return 0, 0

        vorhandene_titel = set(self.vector_store.get_existing_dokument_titel())

        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            if os.path.isfile(file_path) and file_name.lower().endswith(
                (".pdf", ".docx", ".txt")
            ):
                try:
                    if file_path.lower().endswith(".pdf"):
                        dokument, dok_chunks = self.pdf_processor.process_pdf_document(
                            file_path
                        )
                    else:
                        dokument, dok_chunks = self.document_processor.process_document(
                            file_path
                        )

                    if dokument and dokument.titel not in vorhandene_titel:
                        self.vector_store.add_dokument_metadata(dokument)
                        self.vector_store.add_dokument_inhalt(dok_chunks)
                        gesamt_dokumente += 1
                        gesamt_chunks += len(dok_chunks)
                        print(
                            f"Dokument hinzugefügt: {dokument.titel} ({len(dok_chunks)} Chunks)"
                        )
                        vorhandene_titel.add(dokument.titel)
                    elif dokument:
                        print(f"Dokument bereits vorhanden: {dokument.titel} — übersprungen")
                except Exception as e:
                    print(f"Fehler beim Verarbeiten von {file_name}: {e}")

        return gesamt_dokumente, gesamt_chunks

    def query(
        self, query: str, session_id: Optional[str] = None
    ) -> Tuple[str, List[str], List[str]]:
        """
        Verarbeitet eine Benutzeranfrage mit dem RAG-System.

        Args:
            query: Frage des Benutzers
            session_id: Optionale Sitzungs-ID für Gesprächskontext

        Returns:
            Tuple aus (Antwort, Quellenliste, Quellenlink-Liste)
        """
        prompt = f"Beantworten Sie diese Frage zu deutschen Regulierungsdokumenten: {query}"

        history = None
        if session_id:
            history = self.session_manager.get_conversation_history(session_id)

        response = self.ai_generator.generate_response(
            query=prompt,
            conversation_history=history,
            tools=self.tool_manager.get_tool_definitions(),
            tool_manager=self.tool_manager,
        )

        sources = self.tool_manager.get_last_sources()
        source_links = self.tool_manager.get_last_source_links()

        self.tool_manager.reset_sources()

        if session_id:
            self.session_manager.add_exchange(session_id, query, response)

        return response, sources, source_links

    def get_dokument_statistiken(self) -> Dict:
        """Gibt Statistiken über den Dokumentkatalog zurück"""
        titel_liste = self.vector_store.get_existing_dokument_titel()
        alle_metadata = self.vector_store.get_all_dokumente_metadata()

        dokumente = []
        meta_by_titel = {m.get("titel", ""): m for m in alle_metadata}
        for titel in titel_liste:
            meta = meta_by_titel.get(titel, {})
            dokumente.append(
                {
                    "titel": titel,
                    "herausgeber": meta.get("herausgeber", ""),
                    "dokument_quelle": meta.get("dokument_quelle", ""),
                }
            )

        return {
            "gesamt_dokumente": self.vector_store.get_dokument_anzahl(),
            "dokument_titel": titel_liste,
            "dokumente": dokumente,
        }
