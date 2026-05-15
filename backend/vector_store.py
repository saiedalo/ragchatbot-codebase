from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings
from models import Dokument, DokumentChunk
from sentence_transformers import SentenceTransformer


@dataclass
class SearchResults:
    """Container für Suchergebnisse mit Metadaten"""

    documents: List[str]
    metadata: List[Dict[str, Any]]
    distances: List[float]
    error: Optional[str] = None

    @classmethod
    def from_chroma(cls, chroma_results: Dict) -> "SearchResults":
        """Erstellt SearchResults aus ChromaDB-Abfrageergebnissen"""
        return cls(
            documents=(
                chroma_results["documents"][0] if chroma_results["documents"] else []
            ),
            metadata=(
                chroma_results["metadatas"][0] if chroma_results["metadatas"] else []
            ),
            distances=(
                chroma_results["distances"][0] if chroma_results["distances"] else []
            ),
        )

    @classmethod
    def empty(cls, error_msg: str) -> "SearchResults":
        """Erstellt leere Ergebnisse mit Fehlermeldung"""
        return cls(documents=[], metadata=[], distances=[], error=error_msg)

    def is_empty(self) -> bool:
        """Prüft ob Ergebnisse leer sind"""
        return len(self.documents) == 0


class VectorStore:
    """Vektorspeicher auf Basis von ChromaDB für Regulierungsdokumente"""

    def __init__(self, chroma_path: str, embedding_model: str, max_results: int = 5):
        self.max_results = max_results
        self.client = chromadb.PersistentClient(
            path=chroma_path, settings=Settings(anonymized_telemetry=False)
        )

        self.embedding_function = (
            chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=embedding_model
            )
        )

        self.dokument_katalog = self._create_collection("dokument_katalog")
        self.dokument_inhalt = self._create_collection("dokument_inhalt")

    def _create_collection(self, name: str):
        """Erstellt oder ruft eine ChromaDB-Collection ab"""
        return self.client.get_or_create_collection(
            name=name, embedding_function=self.embedding_function
        )

    def search(
        self,
        query: str,
        dokument_name: Optional[str] = None,
        abschnitt_nummer: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> SearchResults:
        """
        Hauptsuchschnittstelle mit Dokumentauflösung und Inhaltssuche.

        Args:
            query: Suchanfrage
            dokument_name: Optionaler Dokumentname zum Filtern
            abschnitt_nummer: Optionale Abschnittsnummer zum Filtern
            limit: Maximale Anzahl Ergebnisse
        """
        dokument_titel = None
        if dokument_name:
            dokument_titel = self._resolve_dokument_name(dokument_name)
            if not dokument_titel:
                return SearchResults.empty(
                    f"Kein Dokument gefunden für '{dokument_name}'"
                )

        filter_dict = self._build_filter(dokument_titel, abschnitt_nummer)

        search_limit = limit if limit is not None else self.max_results

        try:
            results = self.dokument_inhalt.query(
                query_texts=[query], n_results=search_limit, where=filter_dict
            )
            return SearchResults.from_chroma(results)
        except Exception as e:
            return SearchResults.empty(f"Suchfehler: {str(e)}")

    def _resolve_dokument_name(self, dokument_name: str) -> Optional[str]:
        """Verwendet Vektorsuche um das am besten passende Dokument zu finden"""
        try:
            results = self.dokument_katalog.query(
                query_texts=[dokument_name], n_results=1
            )

            if results["documents"][0] and results["metadatas"][0]:
                return results["metadatas"][0][0]["titel"]
        except Exception as e:
            print(f"Fehler bei Dokumentauflösung: {e}")

        return None

    def _build_filter(
        self, dokument_titel: Optional[str], abschnitt_nummer: Optional[int]
    ) -> Optional[Dict]:
        """Erstellt ChromaDB-Filter aus Suchparametern"""
        if not dokument_titel and abschnitt_nummer is None:
            return None

        if dokument_titel and abschnitt_nummer is not None:
            return {
                "$and": [
                    {"dokument_titel": dokument_titel},
                    {"abschnitt_nummer": abschnitt_nummer},
                ]
            }

        if dokument_titel:
            return {"dokument_titel": dokument_titel}

        return {"abschnitt_nummer": abschnitt_nummer}

    @staticmethod
    def _sanitize_metadata(meta: Dict) -> Dict:
        """Entfernt None-Werte aus Metadaten (ChromaDB akzeptiert keine None-Werte)"""
        return {k: v for k, v in meta.items() if v is not None}

    def add_dokument_metadata(self, dokument: Dokument) -> None:
        """Fügt Dokumentinformationen zum Katalog für semantische Suche hinzu"""
        import json

        dokument_text = dokument.titel

        abschnitte_metadata = []
        for abschnitt in dokument.abschnitte:
            abschnitte_metadata.append(
                {
                    "abschnitt_nummer": abschnitt.abschnitt_nummer,
                    "abschnitt_titel": abschnitt.titel,
                    "abschnitt_quelle": abschnitt.abschnitt_quelle,
                }
            )

        raw_meta = {
            "titel": dokument.titel,
            "herausgeber": dokument.herausgeber,
            "dokument_quelle": dokument.dokument_quelle,
            "abschnitte_json": json.dumps(abschnitte_metadata),
            "abschnitt_anzahl": len(dokument.abschnitte),
        }

        self.dokument_katalog.add(
            documents=[dokument_text],
            metadatas=[self._sanitize_metadata(raw_meta)],
            ids=[dokument.titel],
        )

    def add_dokument_inhalt(self, chunks: List[DokumentChunk]) -> None:
        """Fügt Dokument-Inhalt-Chunks zum Vektorspeicher hinzu"""
        if not chunks:
            return

        documents = [chunk.inhalt for chunk in chunks]
        metadatas = [
            self._sanitize_metadata(
                {
                    "dokument_titel": chunk.dokument_titel,
                    "abschnitt_nummer": chunk.abschnitt_nummer,
                    "chunk_index": chunk.chunk_index,
                }
            )
            for chunk in chunks
        ]
        ids = [
            f"{chunk.dokument_titel.replace(' ', '_')}_{chunk.chunk_index}"
            for chunk in chunks
        ]

        self.dokument_inhalt.add(documents=documents, metadatas=metadatas, ids=ids)

    def clear_all_data(self) -> None:
        """Löscht alle Daten aus beiden Collections"""
        try:
            self.client.delete_collection("dokument_katalog")
            self.client.delete_collection("dokument_inhalt")
            self.dokument_katalog = self._create_collection("dokument_katalog")
            self.dokument_inhalt = self._create_collection("dokument_inhalt")
        except Exception as e:
            print(f"Fehler beim Löschen der Daten: {e}")

    def get_existing_dokument_titel(self) -> List[str]:
        """Gibt alle vorhandenen Dokumenttitel aus dem Vektorspeicher zurück"""
        try:
            results = self.dokument_katalog.get()
            if results and "ids" in results:
                return results["ids"]
            return []
        except Exception as e:
            print(f"Fehler beim Abrufen der Dokumenttitel: {e}")
            return []

    def get_dokument_anzahl(self) -> int:
        """Gibt die Gesamtanzahl der Dokumente im Vektorspeicher zurück"""
        try:
            results = self.dokument_katalog.get()
            if results and "ids" in results:
                return len(results["ids"])
            return 0
        except Exception as e:
            print(f"Fehler beim Abrufen der Dokumentanzahl: {e}")
            return 0

    def get_all_dokumente_metadata(self) -> List[Dict[str, Any]]:
        """Gibt Metadaten aller Dokumente im Vektorspeicher zurück"""
        import json

        try:
            results = self.dokument_katalog.get()
            if results and "metadatas" in results:
                parsed_metadata = []
                for metadata in results["metadatas"]:
                    dok_meta = metadata.copy()
                    if "abschnitte_json" in dok_meta:
                        dok_meta["abschnitte"] = json.loads(dok_meta["abschnitte_json"])
                        del dok_meta["abschnitte_json"]
                    parsed_metadata.append(dok_meta)
                return parsed_metadata
            return []
        except Exception as e:
            print(f"Fehler beim Abrufen der Dokumentmetadaten: {e}")
            return []

    def get_dokument_quelle(self, dokument_titel: str) -> Optional[str]:
        """Gibt die Dokumentquelle für einen gegebenen Dokumenttitel zurück"""
        try:
            results = self.dokument_katalog.get(ids=[dokument_titel])
            if results and "metadatas" in results and results["metadatas"]:
                metadata = results["metadatas"][0]
                return metadata.get("dokument_quelle")
            return None
        except Exception as e:
            print(f"Fehler beim Abrufen der Dokumentquelle: {e}")
            return None

    def get_abschnitt_quelle(
        self, dokument_titel: str, abschnitt_nummer: int
    ) -> Optional[str]:
        """Gibt die Abschnittsquelle für einen gegebenen Dokumenttitel und Abschnittsnummer zurück"""
        import json

        try:
            results = self.dokument_katalog.get(ids=[dokument_titel])
            if results and "metadatas" in results and results["metadatas"]:
                metadata = results["metadatas"][0]
                abschnitte_json = metadata.get("abschnitte_json")
                if abschnitte_json:
                    abschnitte = json.loads(abschnitte_json)
                    for abschnitt in abschnitte:
                        if abschnitt.get("abschnitt_nummer") == abschnitt_nummer:
                            return abschnitt.get("abschnitt_quelle")
            return None
        except Exception as e:
            print(f"Fehler beim Abrufen der Abschnittsquelle: {e}")
            return None
