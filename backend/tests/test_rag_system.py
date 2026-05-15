import os
import sys
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Abschnitt, Dokument, DokumentChunk
from rag_system import RAGSystem


class TestRAGSystem:
    """Testfälle für RAGSystem End-to-End-Integration"""

    def test_init_with_proper_config(self, test_config):
        """Testet RAGSystem-Initialisierung mit korrekter Konfiguration"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.PDFDocumentProcessor"),
            patch("rag_system.VectorStore"),
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
        ):

            rag_system = RAGSystem(test_config)

            assert rag_system.config == test_config
            assert rag_system.document_processor is not None
            assert rag_system.pdf_processor is not None
            assert rag_system.vector_store is not None
            assert rag_system.ai_generator is not None
            assert rag_system.session_manager is not None
            assert rag_system.tool_manager is not None
            assert rag_system.search_tool is not None
            assert rag_system.outline_tool is not None

    def test_init_with_broken_config(self, broken_config):
        """Testet RAGSystem-Initialisierung mit defektem MAX_RESULTS=0"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.PDFDocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vector_store,
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
        ):

            rag_system = RAGSystem(broken_config)

            mock_vector_store.assert_called_once_with(
                broken_config.CHROMA_PATH,
                broken_config.EMBEDDING_MODEL,
                0,
            )

    def test_query_successful_with_tool_use(self, test_config):
        """Testet erfolgreiche Anfragebearbeitung mit Werkzeugnutzung"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.PDFDocumentProcessor"),
            patch("rag_system.VectorStore"),
            patch("rag_system.AIGenerator") as mock_ai_gen,
            patch("rag_system.SessionManager") as mock_session,
        ):

            mock_ai_gen.return_value.generate_response.return_value = (
                "Basierend auf den MaRisk-Anforderungen hier die Antwort."
            )
            mock_session.return_value.get_conversation_history.return_value = None

            rag_system = RAGSystem(test_config)

            rag_system.tool_manager.get_last_sources = Mock(
                return_value=["MaRisk - Abschnitt 1"]
            )
            rag_system.tool_manager.get_last_source_links = Mock(
                return_value=["https://example.com/abschnitt1"]
            )

            response, sources, source_links = rag_system.query(
                "Was sind die MaRisk-Anforderungen?"
            )

            assert response == "Basierend auf den MaRisk-Anforderungen hier die Antwort."
            assert sources == ["MaRisk - Abschnitt 1"]
            assert source_links == ["https://example.com/abschnitt1"]

            mock_ai_gen.return_value.generate_response.assert_called_once()
            call_args = mock_ai_gen.return_value.generate_response.call_args[1]
            assert "tools" in call_args
            assert "tool_manager" in call_args

    def test_query_with_session_history(self, test_config):
        """Testet Anfragebearbeitung mit Gesprächshistorie"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.PDFDocumentProcessor"),
            patch("rag_system.VectorStore"),
            patch("rag_system.AIGenerator") as mock_ai_gen,
            patch("rag_system.SessionManager") as mock_session,
        ):

            mock_ai_gen.return_value.generate_response.return_value = (
                "Folgeantwort zur Regulierungsfrage."
            )
            mock_session.return_value.get_conversation_history.return_value = (
                "Vorheriges Gespräch"
            )

            rag_system = RAGSystem(test_config)
            rag_system.tool_manager.get_last_sources = Mock(return_value=[])
            rag_system.tool_manager.get_last_source_links = Mock(return_value=[])

            response, sources, source_links = rag_system.query(
                "Folgefrage", session_id="session123"
            )

            assert response == "Folgeantwort zur Regulierungsfrage."

            mock_session.return_value.get_conversation_history.assert_called_once_with(
                "session123"
            )
            call_args = mock_ai_gen.return_value.generate_response.call_args[1]
            assert call_args["conversation_history"] == "Vorheriges Gespräch"

            mock_session.return_value.add_exchange.assert_called_once_with(
                "session123",
                "Folgefrage",
                "Folgeantwort zur Regulierungsfrage.",
            )

    def test_query_failed_scenario_max_results_zero(self, broken_config):
        """Testet das 'Anfrage fehlgeschlagen'-Szenario wegen MAX_RESULTS=0"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.PDFDocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vector_store,
            patch("rag_system.AIGenerator") as mock_ai_gen,
            patch("rag_system.SessionManager"),
        ):

            mock_vector_store_instance = Mock()
            mock_vector_store.return_value = mock_vector_store_instance

            mock_ai_gen.return_value.generate_response.return_value = (
                "Keine relevanten Informationen gefunden."
            )

            rag_system = RAGSystem(broken_config)

            rag_system.tool_manager.get_last_sources = Mock(return_value=[])
            rag_system.tool_manager.get_last_source_links = Mock(return_value=[])

            response, sources, source_links = rag_system.query(
                "Was sind die Regulierungsanforderungen?"
            )

            assert "keine" in response.lower() or "gefunden" in response.lower()
            assert sources == []
            assert source_links == []

    def test_query_with_no_session(self, test_config):
        """Testet Anfragebearbeitung ohne Sitzungs-ID"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.PDFDocumentProcessor"),
            patch("rag_system.VectorStore"),
            patch("rag_system.AIGenerator") as mock_ai_gen,
            patch("rag_system.SessionManager") as mock_session,
        ):

            mock_ai_gen.return_value.generate_response.return_value = (
                "Antwort ohne Sitzung."
            )

            rag_system = RAGSystem(test_config)
            rag_system.tool_manager.get_last_sources = Mock(return_value=[])
            rag_system.tool_manager.get_last_source_links = Mock(return_value=[])

            response, sources, source_links = rag_system.query("Was ist KWG?")

            assert response == "Antwort ohne Sitzung."

            mock_session.return_value.get_conversation_history.assert_not_called()
            mock_session.return_value.add_exchange.assert_not_called()

    def test_add_dokument_success(self, test_config, sample_dokument):
        """Testet Hinzufügen eines einzelnen Regulierungsdokuments"""
        with (
            patch("rag_system.DocumentProcessor") as mock_doc_proc,
            patch("rag_system.PDFDocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vector_store,
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
        ):

            mock_chunks = [
                DokumentChunk(
                    inhalt="chunk1", dokument_titel="Test Dokument", chunk_index=0
                ),
                DokumentChunk(
                    inhalt="chunk2", dokument_titel="Test Dokument", chunk_index=1
                ),
            ]
            mock_doc_proc.return_value.process_document.return_value = (
                sample_dokument,
                mock_chunks,
            )

            rag_system = RAGSystem(test_config)

            dokument, chunk_count = rag_system.add_dokument("/pfad/zum/dokument.txt")

            assert dokument == sample_dokument
            assert chunk_count == 2

            mock_doc_proc.return_value.process_document.assert_called_once_with(
                "/pfad/zum/dokument.txt"
            )

            mock_vector_store.return_value.add_dokument_metadata.assert_called_once_with(
                sample_dokument
            )
            mock_vector_store.return_value.add_dokument_inhalt.assert_called_once_with(
                mock_chunks
            )

    def test_add_dokument_error(self, test_config):
        """Testet Fehlerbehandlung wenn Dokumentverarbeitung fehlschlägt"""
        with (
            patch("rag_system.DocumentProcessor") as mock_doc_proc,
            patch("rag_system.PDFDocumentProcessor"),
            patch("rag_system.VectorStore"),
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
        ):

            mock_doc_proc.return_value.process_document.side_effect = Exception(
                "Verarbeitung fehlgeschlagen"
            )

            rag_system = RAGSystem(test_config)

            dokument, chunk_count = rag_system.add_dokument(
                "/pfad/zum/defekten_dokument.txt"
            )

            assert dokument is None
            assert chunk_count == 0

    def test_add_dokument_ordner_success(self, test_config):
        """Testet Hinzufügen mehrerer Dokumente aus einem Ordner"""
        with (
            patch("rag_system.DocumentProcessor") as mock_doc_proc,
            patch("rag_system.PDFDocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vector_store,
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
            patch("os.path.exists") as mock_exists,
            patch("os.listdir") as mock_listdir,
        ):

            mock_exists.return_value = True
            mock_listdir.return_value = [
                "marisk.pdf",
                "bait.txt",
                "gwg.docx",
                "ignore.jpg",
            ]
            mock_vector_store.return_value.get_existing_dokument_titel.return_value = []

            dokumente = [
                Dokument(titel="MaRisk", abschnitte=[]),
                Dokument(titel="BAIT", abschnitte=[]),
                Dokument(titel="GwG", abschnitte=[]),
            ]
            chunks = [
                [DokumentChunk(inhalt="c1", dokument_titel="MaRisk", chunk_index=0)],
                [DokumentChunk(inhalt="c2", dokument_titel="BAIT", chunk_index=0)],
                [DokumentChunk(inhalt="c3", dokument_titel="GwG", chunk_index=0)],
            ]

            mock_doc_proc.return_value.process_document.side_effect = [
                (dokumente[1], chunks[1]),
                (dokumente[2], chunks[2]),
            ]

            mock_pdf_proc_inst = Mock()
            mock_pdf_proc_inst.process_pdf_document.return_value = (dokumente[0], chunks[0])

            rag_system = RAGSystem(test_config)
            rag_system.pdf_processor = mock_pdf_proc_inst

            with patch("os.path.isfile", return_value=True):
                gesamt_dokumente, gesamt_chunks = rag_system.add_dokument_ordner(
                    "/pfad/zu/docs", clear_existing=False
                )

            assert gesamt_dokumente == 3
            assert gesamt_chunks == 3

    def test_add_dokument_ordner_with_clear_existing(self, test_config):
        """Testet Hinzufügen von Dokumenten mit clear_existing=True"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.PDFDocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vector_store,
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
            patch("os.path.exists") as mock_exists,
            patch("os.listdir") as mock_listdir,
        ):

            mock_exists.return_value = True
            mock_listdir.return_value = []

            rag_system = RAGSystem(test_config)

            rag_system.add_dokument_ordner("/pfad/zu/docs", clear_existing=True)

            mock_vector_store.return_value.clear_all_data.assert_called_once()

    def test_add_dokument_ordner_skip_existing(self, test_config):
        """Testet ob vorhandene Dokumente übersprungen werden"""
        with (
            patch("rag_system.DocumentProcessor") as mock_doc_proc,
            patch("rag_system.PDFDocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vector_store,
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
            patch("os.path.exists") as mock_exists,
            patch("os.listdir") as mock_listdir,
        ):

            mock_exists.return_value = True
            mock_listdir.return_value = ["marisk.txt"]

            mock_vector_store.return_value.get_existing_dokument_titel.return_value = [
                "Vorhandenes Dokument"
            ]

            vorhandenes_dokument = Dokument(titel="Vorhandenes Dokument", abschnitte=[])
            mock_chunks = [
                DokumentChunk(
                    inhalt="inhalt",
                    dokument_titel="Vorhandenes Dokument",
                    chunk_index=0,
                )
            ]
            mock_doc_proc.return_value.process_document.return_value = (
                vorhandenes_dokument,
                mock_chunks,
            )

            rag_system = RAGSystem(test_config)

            gesamt_dokumente, gesamt_chunks = rag_system.add_dokument_ordner(
                "/pfad/zu/docs"
            )

            assert gesamt_dokumente == 0
            assert gesamt_chunks == 0

            mock_vector_store.return_value.add_dokument_metadata.assert_not_called()
            mock_vector_store.return_value.add_dokument_inhalt.assert_not_called()

    def test_add_dokument_ordner_nonexistent(self, test_config):
        """Testet Behandlung eines nicht vorhandenen Ordners"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.PDFDocumentProcessor"),
            patch("rag_system.VectorStore"),
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
            patch("os.path.exists") as mock_exists,
        ):

            mock_exists.return_value = False

            rag_system = RAGSystem(test_config)

            gesamt_dokumente, gesamt_chunks = rag_system.add_dokument_ordner(
                "/nicht/vorhandener/pfad"
            )

            assert gesamt_dokumente == 0
            assert gesamt_chunks == 0

    def test_get_dokument_statistiken(self, test_config):
        """Testet Abruf der Dokumentstatistiken"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.PDFDocumentProcessor"),
            patch("rag_system.VectorStore") as mock_vector_store,
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
        ):

            mock_vector_store.return_value.get_dokument_anzahl.return_value = 4
            mock_vector_store.return_value.get_existing_dokument_titel.return_value = [
                "MaRisk",
                "BAIT",
                "GwG-Hinweise",
                "Merkblatt Finanzdienstleistungen",
            ]

            rag_system = RAGSystem(test_config)

            statistiken = rag_system.get_dokument_statistiken()

            assert statistiken["gesamt_dokumente"] == 4
            assert len(statistiken["dokument_titel"]) == 4
            assert "MaRisk" in statistiken["dokument_titel"]

    def test_tool_registration(self, test_config):
        """Testet ob Werkzeuge korrekt beim Werkzeugmanager registriert werden"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.PDFDocumentProcessor"),
            patch("rag_system.VectorStore"),
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
        ):

            rag_system = RAGSystem(test_config)

            tool_definitions = rag_system.tool_manager.get_tool_definitions()
            tool_names = [tool["name"] for tool in tool_definitions]

            assert "regulierungsdokument_suchen" in tool_names
            assert "dokument_struktur_abrufen" in tool_names

    def test_source_tracking_and_reset(self, test_config):
        """Testet ob Quellen korrekt verfolgt und nach Anfragen zurückgesetzt werden"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.PDFDocumentProcessor"),
            patch("rag_system.VectorStore"),
            patch("rag_system.AIGenerator") as mock_ai_gen,
            patch("rag_system.SessionManager"),
        ):

            mock_ai_gen.return_value.generate_response.return_value = "Testantwort"

            rag_system = RAGSystem(test_config)

            rag_system.tool_manager.get_last_sources = Mock(return_value=["Quelle 1"])
            rag_system.tool_manager.get_last_source_links = Mock(
                return_value=["Link 1"]
            )
            rag_system.tool_manager.reset_sources = Mock()

            response, sources, source_links = rag_system.query("Testanfrage")

            assert sources == ["Quelle 1"]
            assert source_links == ["Link 1"]

            rag_system.tool_manager.reset_sources.assert_called_once()

    def test_end_to_end_query_flow_integration(self, test_config):
        """Testet vollständigen End-to-End-Anfrage-Verarbeitungsfluss"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.PDFDocumentProcessor"),
            patch("rag_system.VectorStore"),
            patch("rag_system.AIGenerator") as mock_ai_gen,
            patch("rag_system.SessionManager") as mock_session,
        ):

            mock_session.return_value.create_session.return_value = "neue_session_123"
            mock_session.return_value.get_conversation_history.return_value = None
            mock_ai_gen.return_value.generate_response.return_value = (
                "Umfassende Antwort basierend auf den Regulierungsdokumenten."
            )

            rag_system = RAGSystem(test_config)
            rag_system.tool_manager.get_last_sources = Mock(
                return_value=["MaRisk - Abschnitt 4"]
            )
            rag_system.tool_manager.get_last_source_links = Mock(
                return_value=["https://example.com/abschnitt4"]
            )

            response, sources, source_links = rag_system.query(
                "Erläutern Sie die MaRisk AT 4 Anforderungen vollständig"
            )

            assert "Umfassende Antwort" in response
            assert sources == ["MaRisk - Abschnitt 4"]
            assert source_links == ["https://example.com/abschnitt4"]

            call_args = mock_ai_gen.return_value.generate_response.call_args[1]
            assert (
                call_args["query"]
                == "Beantworten Sie diese Frage zu deutschen Regulierungsdokumenten: Erläutern Sie die MaRisk AT 4 Anforderungen vollständig"
            )
            assert "tools" in call_args
            assert "tool_manager" in call_args
