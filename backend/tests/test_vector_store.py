import os
import shutil
import sys
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Abschnitt, Dokument, DokumentChunk
from vector_store import SearchResults, VectorStore


class TestVectorStore:
    """Testfälle für VectorStore"""

    def test_search_with_proper_max_results(self, test_config, mock_chroma_collection):
        """Testet Suche mit korrekter MAX_RESULTS-Einstellung"""
        with patch("vector_store.chromadb") as mock_chromadb:
            mock_client = Mock()
            mock_chromadb.PersistentClient.return_value = mock_client
            mock_client.get_or_create_collection.return_value = mock_chroma_collection

            vector_store = VectorStore(
                chroma_path=test_config.CHROMA_PATH,
                embedding_model=test_config.EMBEDDING_MODEL,
                max_results=test_config.MAX_RESULTS,
            )

            result = vector_store.search("Testanfrage")

            mock_chroma_collection.query.assert_called_once_with(
                query_texts=["Testanfrage"],
                n_results=5,
                where=None,
            )

            assert not result.is_empty()
            assert len(result.documents) == 1
            assert result.documents[0] == "Beispiel Dokument"

    def test_search_with_broken_max_results_zero(
        self, broken_config, mock_chroma_collection
    ):
        """Testet das kritische MAX_RESULTS=0 Problem"""
        with patch("vector_store.chromadb") as mock_chromadb:
            mock_client = Mock()
            mock_chromadb.PersistentClient.return_value = mock_client

            empty_collection = Mock()
            empty_collection.query.return_value = {
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]],
            }
            mock_client.get_or_create_collection.return_value = empty_collection

            vector_store = VectorStore(
                chroma_path=broken_config.CHROMA_PATH,
                embedding_model=broken_config.EMBEDDING_MODEL,
                max_results=broken_config.MAX_RESULTS,
            )

            result = vector_store.search("gültige Anfrage")

            empty_collection.query.assert_called_once_with(
                query_texts=["gültige Anfrage"], n_results=0, where=None
            )

            assert result.is_empty()
            assert len(result.documents) == 0

    def test_search_with_document_filter(self, test_config, mock_chroma_collection):
        """Testet Suche mit Dokumentname-Filter"""
        with patch("vector_store.chromadb") as mock_chromadb:
            mock_client = Mock()
            mock_chromadb.PersistentClient.return_value = mock_client

            dokument_katalog = Mock()
            dokument_katalog.query.return_value = {
                "documents": [["Test Dokument"]],
                "metadatas": [[{"titel": "Test Dokument"}]],
            }

            inhalt_collection = Mock()
            inhalt_collection.query.return_value = {
                "documents": [["Gefilterter Inhalt"]],
                "metadatas": [[{"dokument_titel": "Test Dokument", "abschnitt_nummer": 1}]],
                "distances": [[0.1]],
            }

            mock_client.get_or_create_collection.side_effect = [
                dokument_katalog,
                inhalt_collection,
            ]

            vector_store = VectorStore(
                chroma_path=test_config.CHROMA_PATH,
                embedding_model=test_config.EMBEDDING_MODEL,
                max_results=test_config.MAX_RESULTS,
            )

            result = vector_store.search("Testanfrage", dokument_name="Test")

            dokument_katalog.query.assert_called_once_with(
                query_texts=["Test"], n_results=1
            )

            inhalt_collection.query.assert_called_once_with(
                query_texts=["Testanfrage"],
                n_results=5,
                where={"dokument_titel": "Test Dokument"},
            )

            assert not result.is_empty()
            assert result.documents[0] == "Gefilterter Inhalt"

    def test_search_with_section_filter(self, test_config, mock_chroma_collection):
        """Testet Suche mit Abschnittsnummer-Filter"""
        with patch("vector_store.chromadb") as mock_chromadb:
            mock_client = Mock()
            mock_chromadb.PersistentClient.return_value = mock_client
            mock_client.get_or_create_collection.return_value = mock_chroma_collection

            vector_store = VectorStore(
                chroma_path=test_config.CHROMA_PATH,
                embedding_model=test_config.EMBEDDING_MODEL,
                max_results=test_config.MAX_RESULTS,
            )

            result = vector_store.search("Testanfrage", abschnitt_nummer=2)

            mock_chroma_collection.query.assert_called_once_with(
                query_texts=["Testanfrage"],
                n_results=5,
                where={"abschnitt_nummer": 2},
            )

    def test_search_with_both_filters(self, test_config):
        """Testet Suche mit beiden Filtern"""
        with patch("vector_store.chromadb") as mock_chromadb:
            mock_client = Mock()
            mock_chromadb.PersistentClient.return_value = mock_client

            dokument_katalog = Mock()
            dokument_katalog.query.return_value = {
                "documents": [["Spezifisches Dokument"]],
                "metadatas": [[{"titel": "Spezifisches Dokument"}]],
            }

            inhalt_collection = Mock()
            inhalt_collection.query.return_value = {
                "documents": [["Spezifischer Inhalt"]],
                "metadatas": [
                    [{"dokument_titel": "Spezifisches Dokument", "abschnitt_nummer": 3}]
                ],
                "distances": [[0.1]],
            }

            mock_client.get_or_create_collection.side_effect = [
                dokument_katalog,
                inhalt_collection,
            ]

            vector_store = VectorStore(
                chroma_path=test_config.CHROMA_PATH,
                embedding_model=test_config.EMBEDDING_MODEL,
                max_results=test_config.MAX_RESULTS,
            )

            result = vector_store.search(
                "Testanfrage", dokument_name="Spezifisch", abschnitt_nummer=3
            )

            expected_filter = {
                "$and": [
                    {"dokument_titel": "Spezifisches Dokument"},
                    {"abschnitt_nummer": 3},
                ]
            }
            inhalt_collection.query.assert_called_once_with(
                query_texts=["Testanfrage"], n_results=5, where=expected_filter
            )

    def test_resolve_dokument_name_success(self, test_config):
        """Testet erfolgreiche Dokumentname-Auflösung"""
        with patch("vector_store.chromadb") as mock_chromadb:
            mock_client = Mock()
            mock_chromadb.PersistentClient.return_value = mock_client

            dokument_katalog = Mock()
            dokument_katalog.query.return_value = {
                "documents": [["MaRisk - Mindestanforderungen an das Risikomanagement"]],
                "metadatas": [
                    [{"titel": "MaRisk - Mindestanforderungen an das Risikomanagement"}]
                ],
            }

            inhalt_collection = Mock()
            mock_client.get_or_create_collection.side_effect = [
                dokument_katalog,
                inhalt_collection,
            ]

            vector_store = VectorStore(
                chroma_path=test_config.CHROMA_PATH,
                embedding_model=test_config.EMBEDDING_MODEL,
                max_results=test_config.MAX_RESULTS,
            )

            resolved_name = vector_store._resolve_dokument_name("MaRisk")

            assert resolved_name == "MaRisk - Mindestanforderungen an das Risikomanagement"
            dokument_katalog.query.assert_called_once_with(
                query_texts=["MaRisk"], n_results=1
            )

    def test_resolve_dokument_name_not_found(self, test_config):
        """Testet Dokumentname-Auflösung wenn kein Dokument gefunden"""
        with patch("vector_store.chromadb") as mock_chromadb:
            mock_client = Mock()
            mock_chromadb.PersistentClient.return_value = mock_client

            dokument_katalog = Mock()
            dokument_katalog.query.return_value = {
                "documents": [[]],
                "metadatas": [[]],
            }

            inhalt_collection = Mock()
            mock_client.get_or_create_collection.side_effect = [
                dokument_katalog,
                inhalt_collection,
            ]

            vector_store = VectorStore(
                chroma_path=test_config.CHROMA_PATH,
                embedding_model=test_config.EMBEDDING_MODEL,
                max_results=test_config.MAX_RESULTS,
            )

            resolved_name = vector_store._resolve_dokument_name("NichtVorhandenesDocument")

            assert resolved_name is None

    def test_search_document_not_found(self, test_config):
        """Testet Suche wenn Dokumentname nicht aufgelöst werden kann"""
        with patch("vector_store.chromadb") as mock_chromadb:
            mock_client = Mock()
            mock_chromadb.PersistentClient.return_value = mock_client

            dokument_katalog = Mock()
            dokument_katalog.query.return_value = {"documents": [[]], "metadatas": [[]]}

            inhalt_collection = Mock()
            mock_client.get_or_create_collection.side_effect = [
                dokument_katalog,
                inhalt_collection,
            ]

            vector_store = VectorStore(
                chroma_path=test_config.CHROMA_PATH,
                embedding_model=test_config.EMBEDDING_MODEL,
                max_results=test_config.MAX_RESULTS,
            )

            result = vector_store.search(
                "Testanfrage", dokument_name="NichtVorhandenesDocument"
            )

            assert result.error == "Kein Dokument gefunden für 'NichtVorhandenesDocument'"
            assert result.is_empty()

    def test_search_database_error(self, test_config):
        """Testet Suche wenn Datenbankabfrage fehlschlägt"""
        with patch("vector_store.chromadb") as mock_chromadb:
            mock_client = Mock()
            mock_chromadb.PersistentClient.return_value = mock_client

            dokument_katalog = Mock()
            inhalt_collection = Mock()
            inhalt_collection.query.side_effect = Exception("Datenbankverbindung fehlgeschlagen")

            mock_client.get_or_create_collection.side_effect = [
                dokument_katalog,
                inhalt_collection,
            ]

            vector_store = VectorStore(
                chroma_path=test_config.CHROMA_PATH,
                embedding_model=test_config.EMBEDDING_MODEL,
                max_results=test_config.MAX_RESULTS,
            )

            result = vector_store.search("Testanfrage")

            assert result.error == "Suchfehler: Datenbankverbindung fehlgeschlagen"
            assert result.is_empty()

    def test_build_filter_no_filters(self, test_config):
        """Testet Filter-Aufbau ohne Filter"""
        with patch("vector_store.chromadb"):
            vector_store = VectorStore(
                chroma_path=test_config.CHROMA_PATH,
                embedding_model=test_config.EMBEDDING_MODEL,
                max_results=test_config.MAX_RESULTS,
            )

            filter_dict = vector_store._build_filter(None, None)
            assert filter_dict is None

    def test_build_filter_document_only(self, test_config):
        """Testet Filter-Aufbau nur mit Dokumentfilter"""
        with patch("vector_store.chromadb"):
            vector_store = VectorStore(
                chroma_path=test_config.CHROMA_PATH,
                embedding_model=test_config.EMBEDDING_MODEL,
                max_results=test_config.MAX_RESULTS,
            )

            filter_dict = vector_store._build_filter("Test Dokument", None)
            assert filter_dict == {"dokument_titel": "Test Dokument"}

    def test_build_filter_section_only(self, test_config):
        """Testet Filter-Aufbau nur mit Abschnittsfilter"""
        with patch("vector_store.chromadb"):
            vector_store = VectorStore(
                chroma_path=test_config.CHROMA_PATH,
                embedding_model=test_config.EMBEDDING_MODEL,
                max_results=test_config.MAX_RESULTS,
            )

            filter_dict = vector_store._build_filter(None, 2)
            assert filter_dict == {"abschnitt_nummer": 2}

    def test_build_filter_both(self, test_config):
        """Testet Filter-Aufbau mit beiden Filtern"""
        with patch("vector_store.chromadb"):
            vector_store = VectorStore(
                chroma_path=test_config.CHROMA_PATH,
                embedding_model=test_config.EMBEDDING_MODEL,
                max_results=test_config.MAX_RESULTS,
            )

            filter_dict = vector_store._build_filter("Test Dokument", 2)
            expected = {
                "$and": [{"dokument_titel": "Test Dokument"}, {"abschnitt_nummer": 2}]
            }
            assert filter_dict == expected

    def test_add_dokument_metadata(self, test_config, sample_dokument):
        """Testet Hinzufügen von Dokumentmetadaten zum Vektorspeicher"""
        with patch("vector_store.chromadb") as mock_chromadb:
            mock_client = Mock()
            mock_chromadb.PersistentClient.return_value = mock_client

            dokument_katalog = Mock()
            inhalt_collection = Mock()
            mock_client.get_or_create_collection.side_effect = [
                dokument_katalog,
                inhalt_collection,
            ]

            vector_store = VectorStore(
                chroma_path=test_config.CHROMA_PATH,
                embedding_model=test_config.EMBEDDING_MODEL,
                max_results=test_config.MAX_RESULTS,
            )

            vector_store.add_dokument_metadata(sample_dokument)

            dokument_katalog.add.assert_called_once()
            call_args = dokument_katalog.add.call_args

            assert call_args[1]["documents"] == [sample_dokument.titel]
            assert call_args[1]["ids"] == [sample_dokument.titel]

            metadata = call_args[1]["metadatas"][0]
            assert metadata["titel"] == sample_dokument.titel
            assert metadata["herausgeber"] == sample_dokument.herausgeber
            assert metadata["dokument_quelle"] == sample_dokument.dokument_quelle
            assert metadata["abschnitt_anzahl"] == len(sample_dokument.abschnitte)
            assert "abschnitte_json" in metadata

    def test_add_dokument_inhalt(self, test_config, sample_dokument_chunks):
        """Testet Hinzufügen von Dokument-Inhalt-Chunks zum Vektorspeicher"""
        with patch("vector_store.chromadb") as mock_chromadb:
            mock_client = Mock()
            mock_chromadb.PersistentClient.return_value = mock_client

            dokument_katalog = Mock()
            inhalt_collection = Mock()
            mock_client.get_or_create_collection.side_effect = [
                dokument_katalog,
                inhalt_collection,
            ]

            vector_store = VectorStore(
                chroma_path=test_config.CHROMA_PATH,
                embedding_model=test_config.EMBEDDING_MODEL,
                max_results=test_config.MAX_RESULTS,
            )

            vector_store.add_dokument_inhalt(sample_dokument_chunks)

            inhalt_collection.add.assert_called_once()
            call_args = inhalt_collection.add.call_args

            assert len(call_args[1]["documents"]) == len(sample_dokument_chunks)
            assert len(call_args[1]["metadatas"]) == len(sample_dokument_chunks)
            assert len(call_args[1]["ids"]) == len(sample_dokument_chunks)

            assert call_args[1]["documents"][0] == sample_dokument_chunks[0].inhalt
            assert (
                call_args[1]["metadatas"][0]["dokument_titel"]
                == sample_dokument_chunks[0].dokument_titel
            )
            assert (
                call_args[1]["metadatas"][0]["abschnitt_nummer"]
                == sample_dokument_chunks[0].abschnitt_nummer
            )

    def test_get_abschnitt_quelle(self, test_config):
        """Testet Abrufen der Abschnittsquelle"""
        with patch("vector_store.chromadb") as mock_chromadb:
            mock_client = Mock()
            mock_chromadb.PersistentClient.return_value = mock_client

            dokument_katalog = Mock()
            dokument_katalog.get.return_value = {
                "metadatas": [
                    {
                        "abschnitte_json": '[{"abschnitt_nummer": 1, "abschnitt_titel": "Anwendungsbereich", "abschnitt_quelle": "https://example.com/abschnitt1"}]'
                    }
                ]
            }

            inhalt_collection = Mock()
            mock_client.get_or_create_collection.side_effect = [
                dokument_katalog,
                inhalt_collection,
            ]

            vector_store = VectorStore(
                chroma_path=test_config.CHROMA_PATH,
                embedding_model=test_config.EMBEDDING_MODEL,
                max_results=test_config.MAX_RESULTS,
            )

            link = vector_store.get_abschnitt_quelle("Test Dokument", 1)

            assert link == "https://example.com/abschnitt1"
            dokument_katalog.get.assert_called_once_with(ids=["Test Dokument"])

    def test_search_results_from_chroma(self):
        """Testet SearchResults.from_chroma Methode"""
        chroma_results = {
            "documents": [["dok1", "dok2"]],
            "metadatas": [[{"meta1": "wert1"}, {"meta2": "wert2"}]],
            "distances": [[0.1, 0.2]],
        }

        results = SearchResults.from_chroma(chroma_results)

        assert results.documents == ["dok1", "dok2"]
        assert results.metadata == [{"meta1": "wert1"}, {"meta2": "wert2"}]
        assert results.distances == [0.1, 0.2]
        assert results.error is None
        assert not results.is_empty()

    def test_search_results_empty(self):
        """Testet SearchResults.empty Methode"""
        results = SearchResults.empty("Test-Fehlermeldung")

        assert results.documents == []
        assert results.metadata == []
        assert results.distances == []
        assert results.error == "Test-Fehlermeldung"
        assert results.is_empty()
