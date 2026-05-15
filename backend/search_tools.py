from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol

from vector_store import SearchResults, VectorStore


class Tool(ABC):
    """Abstrakte Basisklasse für alle Werkzeuge"""

    @abstractmethod
    def get_tool_definition(self) -> Dict[str, Any]:
        """Gibt die Anthropic-Werkzeugdefinition zurück"""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Führt das Werkzeug mit den gegebenen Parametern aus"""
        pass


class ReguliierungssuchTool(Tool):
    """Werkzeug zur semantischen Suche in Regulierungsdokumenten"""

    def __init__(self, vector_store: VectorStore):
        self.store = vector_store
        self.last_sources = []
        self.last_source_links = []

    def get_tool_definition(self) -> Dict[str, Any]:
        """Gibt die Anthropic-Werkzeugdefinition zurück"""
        return {
            "name": "regulierungsdokument_suchen",
            "description": "Durchsucht Regulierungsdokumente semantisch nach relevanten Informationen zu BaFin-Vorschriften, MaRisk-Anforderungen, AML-Pflichten und IT-Sicherheitsanforderungen für Kreditinstitute",
            "input_schema": {
                "type": "object",
                "properties": {
                    "suchanfrage": {
                        "type": "string",
                        "description": "Was im Regulierungsdokument gesucht werden soll (z.B. 'Mindestanforderungen Risikosteuerung', 'Sorgfaltspflichten Geldwäsche')",
                    },
                    "dokument_name": {
                        "type": "string",
                        "description": "Dokumenttitel zur Einschränkung der Suche (Teilübereinstimmungen möglich, z.B. 'MaRisk', 'BAIT', 'Geldwäsche')",
                    },
                    "abschnitt_nummer": {
                        "type": "integer",
                        "description": "Spezifische Abschnittsnummer zur Einschränkung der Suche (z.B. 1, 2, 3)",
                    },
                },
                "required": ["suchanfrage"],
            },
        }

    def execute(
        self,
        suchanfrage: str,
        dokument_name: Optional[str] = None,
        abschnitt_nummer: Optional[int] = None,
    ) -> str:
        """
        Führt die Suche mit den gegebenen Parametern aus.

        Args:
            suchanfrage: Was gesucht werden soll
            dokument_name: Optionaler Dokumentfilter
            abschnitt_nummer: Optionaler Abschnittsfilter
        """
        self.last_sources = []
        self.last_source_links = []

        results = self.store.search(
            query=suchanfrage,
            dokument_name=dokument_name,
            abschnitt_nummer=abschnitt_nummer,
        )

        if results.error:
            return results.error

        if results.is_empty():
            filter_info = ""
            if dokument_name:
                filter_info += f" in Dokument '{dokument_name}'"
            if abschnitt_nummer:
                filter_info += f" in Abschnitt {abschnitt_nummer}"
            return f"Keine relevanten Inhalte gefunden{filter_info}."

        return self._format_results(results)

    def _format_results(self, results: SearchResults) -> str:
        """Formatiert Suchergebnisse mit Dokument- und Abschnittskontext"""
        formatted = []
        sources = []
        source_links = []

        for doc, meta in zip(results.documents, results.metadata):
            dok_titel = meta.get("dokument_titel", "unbekannt")
            abs_num = meta.get("abschnitt_nummer")

            header = f"[{dok_titel}"
            if abs_num is not None:
                header += f" - Abschnitt {abs_num}"
            header += "]"

            source = dok_titel
            if abs_num is not None:
                source += f" - Abschnitt {abs_num}"
            sources.append(source)

            abschnitt_link = None
            if abs_num is not None:
                abschnitt_link = self.store.get_abschnitt_quelle(dok_titel, abs_num)
            source_links.append(abschnitt_link)

            formatted.append(f"{header}\n{doc}")

        self.last_sources = sources
        self.last_source_links = source_links

        return "\n\n".join(formatted)


class DokumentStrukturTool(Tool):
    """Werkzeug zum Abrufen der Struktur eines Regulierungsdokuments"""

    def __init__(self, vector_store: VectorStore):
        self.store = vector_store

    def get_tool_definition(self) -> Dict[str, Any]:
        """Gibt die Anthropic-Werkzeugdefinition zurück"""
        return {
            "name": "dokument_struktur_abrufen",
            "description": "Gibt die Struktur eines Regulierungsdokuments zurück: Titel, Quelle und vollständige Liste der Abschnitte mit Nummern und Titeln",
            "input_schema": {
                "type": "object",
                "properties": {
                    "dokument_name": {
                        "type": "string",
                        "description": "Dokumenttitel (Teilübereinstimmungen möglich, z.B. 'MaRisk', 'BAIT', 'Geldwäsche')",
                    }
                },
                "required": ["dokument_name"],
            },
        }

    def execute(self, dokument_name: str) -> str:
        """
        Gibt die Dokumentstruktur zurück.

        Args:
            dokument_name: Dokumentname für den die Struktur abgerufen werden soll
        """
        dokument_titel = self.store._resolve_dokument_name(dokument_name)
        if not dokument_titel:
            return f"Kein Dokument gefunden für '{dokument_name}'"

        try:
            results = self.store.dokument_katalog.get(ids=[dokument_titel])
            if not results or not results["metadatas"]:
                return f"Dokumentmetadaten nicht gefunden für '{dokument_titel}'"

            metadata = results["metadatas"][0]

            import json

            abschnitte_json = metadata.get("abschnitte_json")
            if not abschnitte_json:
                return f"Keine Abschnittsinformationen verfügbar für '{dokument_titel}'"

            abschnitte = json.loads(abschnitte_json)

            struktur = []
            struktur.append(
                f"**Dokument Titel:** {metadata.get('titel', dokument_titel)}"
            )
            struktur.append(
                f"**Dokument Quelle:** {metadata.get('dokument_quelle', 'N/A')}"
            )
            struktur.append(f"**Herausgeber:** {metadata.get('herausgeber', 'N/A')}")
            struktur.append(f"**Gesamtanzahl Abschnitte:** {len(abschnitte)}")
            struktur.append("\n**Abschnitts-Übersicht:**")

            for abschnitt in abschnitte:
                abs_num = abschnitt.get("abschnitt_nummer", "N/A")
                abs_titel = abschnitt.get("abschnitt_titel", "N/A")
                struktur.append(f"Abschnitt {abs_num}: {abs_titel}")

            return "\n".join(struktur)

        except Exception as e:
            return f"Fehler beim Abrufen der Dokumentstruktur: {str(e)}"


class ToolManager:
    """Verwaltet die verfügbaren Werkzeuge für die KI"""

    def __init__(self) -> None:
        self.tools: Dict[str, Tool] = {}

    def register_tool(self, tool: Tool) -> None:
        """Registriert ein Werkzeug, das die Tool-Schnittstelle implementiert"""
        tool_def = tool.get_tool_definition()
        tool_name = tool_def.get("name")
        if not tool_name:
            raise ValueError("Werkzeug muss einen 'name' in seiner Definition haben")
        self.tools[tool_name] = tool

    def get_tool_definitions(self) -> list:
        """Gibt alle Werkzeugdefinitionen für Anthropic-Werkzeugaufruf zurück"""
        return [tool.get_tool_definition() for tool in self.tools.values()]

    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """Führt ein Werkzeug anhand des Namens mit den gegebenen Parametern aus"""
        if tool_name not in self.tools:
            return f"Werkzeug '{tool_name}' nicht gefunden"

        return self.tools[tool_name].execute(**kwargs)

    def get_last_sources(self) -> list:
        """Gibt Quellen aus der letzten Suchoperation zurück"""
        for tool in self.tools.values():
            if hasattr(tool, "last_sources") and tool.last_sources:
                return tool.last_sources
        return []

    def get_last_source_links(self) -> list:
        """Gibt Quellenlinks aus der letzten Suchoperation zurück"""
        for tool in self.tools.values():
            if hasattr(tool, "last_source_links") and tool.last_source_links:
                return tool.last_source_links
        return []

    def reset_sources(self) -> None:
        """Setzt Quellen aller Werkzeuge zurück"""
        for tool in self.tools.values():
            if hasattr(tool, "last_sources"):
                tool.last_sources = []
            if hasattr(tool, "last_source_links"):
                tool.last_source_links = []
