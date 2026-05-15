import os
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search_tools import ReguliierungssuchTool
from vector_store import SearchResults


class TestReguliierungssuchTool:
    """Testfälle für ReguliierungssuchTool"""

    def test_execute_successful_search(self, mock_vector_store, sample_search_results):
        """Testet erfolgreiche Suche mit Ergebnissen"""
        mock_vector_store.search.return_value = sample_search_results
        tool = ReguliierungssuchTool(mock_vector_store)

        result = tool.execute("Testanfrage")

        assert "[MaRisk - Mindestanforderungen an das Risikomanagement - Abschnitt 1]" in result
        assert "[MaRisk - Mindestanforderungen an das Risikomanagement - Abschnitt 2]" in result
        assert "Willkommen zu den MaRisk" in result
        assert "Anforderungen an die Risikosteuerung" in result

        mock_vector_store.search.assert_called_once_with(
            query="Testanfrage", dokument_name=None, abschnitt_nummer=None
        )

    def test_execute_with_document_filter(self, mock_vector_store, sample_search_results):
        """Testet Suche mit Dokumentname-Filter"""
        mock_vector_store.search.return_value = sample_search_results
        tool = ReguliierungssuchTool(mock_vector_store)

        result = tool.execute("Testanfrage", dokument_name="MaRisk")

        assert "MaRisk" in result
        mock_vector_store.search.assert_called_once_with(
            query="Testanfrage", dokument_name="MaRisk", abschnitt_nummer=None
        )

    def test_execute_with_section_filter(self, mock_vector_store, sample_search_results):
        """Testet Suche mit Abschnittsnummer-Filter"""
        mock_vector_store.search.return_value = sample_search_results
        tool = ReguliierungssuchTool(mock_vector_store)

        result = tool.execute("Testanfrage", abschnitt_nummer=2)

        assert "MaRisk" in result
        mock_vector_store.search.assert_called_once_with(
            query="Testanfrage", dokument_name=None, abschnitt_nummer=2
        )

    def test_execute_with_both_filters(self, mock_vector_store, sample_search_results):
        """Testet Suche mit beiden Filtern"""
        mock_vector_store.search.return_value = sample_search_results
        tool = ReguliierungssuchTool(mock_vector_store)

        result = tool.execute(
            "Testanfrage", dokument_name="MaRisk", abschnitt_nummer=1
        )

        assert "MaRisk" in result
        mock_vector_store.search.assert_called_once_with(
            query="Testanfrage", dokument_name="MaRisk", abschnitt_nummer=1
        )

    def test_execute_empty_results(self, mock_vector_store, empty_search_results):
        """Testet die Behandlung leerer Suchergebnisse"""
        mock_vector_store.search.return_value = empty_search_results
        tool = ReguliierungssuchTool(mock_vector_store)

        result = tool.execute("nicht existierende Anfrage")

        assert result == "Keine relevanten Inhalte gefunden."

    def test_execute_empty_results_with_filters(
        self, mock_vector_store, empty_search_results
    ):
        """Testet leere Ergebnisse mit Filterinformationen"""
        mock_vector_store.search.return_value = empty_search_results
        tool = ReguliierungssuchTool(mock_vector_store)

        result = tool.execute(
            "Testanfrage", dokument_name="Nicht vorhandenes Dokument", abschnitt_nummer=5
        )

        expected = "Keine relevanten Inhalte gefunden in Dokument 'Nicht vorhandenes Dokument' in Abschnitt 5."
        assert result == expected

    def test_execute_search_error(self, mock_vector_store, error_search_results):
        """Testet die Behandlung von Suchfehlern"""
        mock_vector_store.search.return_value = error_search_results
        tool = ReguliierungssuchTool(mock_vector_store)

        result = tool.execute("Testanfrage")

        assert result == "Suchfehler: Datenbankverbindung fehlgeschlagen"

    def test_execute_max_results_zero_issue(self, mock_vector_store):
        """Testet das kritische MAX_RESULTS=0 Problem"""
        empty_results = SearchResults(documents=[], metadata=[], distances=[])
        mock_vector_store.search.return_value = empty_results
        tool = ReguliierungssuchTool(mock_vector_store)

        result = tool.execute("gültige Anfrage zu Regulierungsinhalten")

        assert result == "Keine relevanten Inhalte gefunden."

    def test_format_results_with_section_links(self, mock_vector_store):
        """Testet ob Abschnittslinks korrekt abgerufen und gespeichert werden"""
        search_results = SearchResults(
            documents=["Testinhalt"],
            metadata=[
                {"dokument_titel": "Test Dokument", "abschnitt_nummer": 1, "chunk_index": 0}
            ],
            distances=[0.1],
        )
        mock_vector_store.search.return_value = search_results
        mock_vector_store.get_abschnitt_quelle.return_value = "https://example.com/abschnitt1"

        tool = ReguliierungssuchTool(mock_vector_store)

        result = tool.execute("Testanfrage")

        assert "[Test Dokument - Abschnitt 1]" in result
        assert "Testinhalt" in result

        mock_vector_store.get_abschnitt_quelle.assert_called_once_with("Test Dokument", 1)

        assert tool.last_sources == ["Test Dokument - Abschnitt 1"]
        assert tool.last_source_links == ["https://example.com/abschnitt1"]

    def test_format_results_without_section_number(self, mock_vector_store):
        """Testet Formatierung wenn abschnitt_nummer None ist"""
        search_results = SearchResults(
            documents=["Testinhalt"],
            metadata=[{"dokument_titel": "Test Dokument", "chunk_index": 0}],
            distances=[0.1],
        )
        mock_vector_store.search.return_value = search_results

        tool = ReguliierungssuchTool(mock_vector_store)

        result = tool.execute("Testanfrage")

        assert "[Test Dokument]" in result
        assert "Testinhalt" in result

        assert tool.last_sources == ["Test Dokument"]
        assert tool.last_source_links == [None]

    def test_get_tool_definition(self, mock_vector_store):
        """Testet ob die Werkzeugdefinition korrekt strukturiert ist"""
        tool = ReguliierungssuchTool(mock_vector_store)

        definition = tool.get_tool_definition()

        assert definition["name"] == "regulierungsdokument_suchen"
        assert "description" in definition
        assert "input_schema" in definition

        schema = definition["input_schema"]
        assert schema["type"] == "object"
        assert "suchanfrage" in schema["properties"]
        assert "dokument_name" in schema["properties"]
        assert "abschnitt_nummer" in schema["properties"]
        assert schema["required"] == ["suchanfrage"]

    def test_source_tracking_reset(self, mock_vector_store, sample_search_results):
        """Testet ob Quellen korrekt verfolgt und zurückgesetzt werden"""
        tool = ReguliierungssuchTool(mock_vector_store)
        mock_vector_store.search.return_value = sample_search_results

        tool.execute("erste Anfrage")
        first_sources = tool.last_sources.copy()
        first_links = tool.last_source_links.copy()

        assert len(first_sources) > 0
        assert len(first_links) > 0

        mock_vector_store.search.return_value = SearchResults([], [], [])
        tool.execute("zweite Anfrage")

        assert tool.last_sources == []
        assert tool.last_source_links == []

    def test_multiple_documents_formatting(self, mock_vector_store):
        """Testet Formatierung wenn mehrere Dokumente zurückgegeben werden"""
        multi_results = SearchResults(
            documents=[
                "Erster Dokumentinhalt zu Risikomanagement",
                "Zweiter Dokumentinhalt zu IT-Sicherheit",
                "Dritter Dokumentinhalt zu Geldwäsche",
            ],
            metadata=[
                {"dokument_titel": "MaRisk", "abschnitt_nummer": 1, "chunk_index": 0},
                {"dokument_titel": "BAIT", "abschnitt_nummer": 2, "chunk_index": 1},
                {"dokument_titel": "GwG-Hinweise", "abschnitt_nummer": 1, "chunk_index": 0},
            ],
            distances=[0.1, 0.2, 0.3],
        )
        mock_vector_store.search.return_value = multi_results
        mock_vector_store.get_abschnitt_quelle.side_effect = [
            "https://example.com/marisk1",
            "https://example.com/bait2",
            "https://example.com/gwg1",
        ]

        tool = ReguliierungssuchTool(mock_vector_store)

        result = tool.execute("Testanfrage")

        assert "[MaRisk - Abschnitt 1]" in result
        assert "[BAIT - Abschnitt 2]" in result
        assert "[GwG-Hinweise - Abschnitt 1]" in result
        assert "Erster Dokumentinhalt zu Risikomanagement" in result
        assert "Zweiter Dokumentinhalt zu IT-Sicherheit" in result
        assert "Dritter Dokumentinhalt zu Geldwäsche" in result

        expected_sources = [
            "MaRisk - Abschnitt 1",
            "BAIT - Abschnitt 2",
            "GwG-Hinweise - Abschnitt 1",
        ]
        expected_links = [
            "https://example.com/marisk1",
            "https://example.com/bait2",
            "https://example.com/gwg1",
        ]

        assert tool.last_sources == expected_sources
        assert tool.last_source_links == expected_links
