import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch


@pytest.mark.api
class TestAPIEndpoints:
    """Testsuite für FastAPI-Endpunkte"""

    def test_root_endpoint(self, client):
        """Testet ob der Root-Endpunkt die korrekte Meldung zurückgibt"""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Regulierungs-Assistent RAG System API"}

    def test_query_endpoint_with_session_id(self, client, sample_query_request):
        """Testet /api/query Endpunkt mit vorhandener session_id"""
        response = client.post("/api/query", json=sample_query_request)

        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert "sources" in data
        assert "source_links" in data
        assert "session_id" in data

        assert data["answer"] == "Dies ist eine Testantwort zu den Regulierungsanforderungen."
        assert data["sources"] == ["MaRisk - Mindestanforderungen - Abschnitt 1"]
        assert data["source_links"] == ["https://example.com/abschnitt1"]
        assert data["session_id"] == "test-session-123"

    def test_query_endpoint_without_session_id(self, client):
        """Testet /api/query Endpunkt ohne session_id (neue Sitzung wird erstellt)"""
        request_data = {"query": "Was sind die MaRisk-Anforderungen?"}
        response = client.post("/api/query", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["session_id"] == "test-session-123"
        assert data["answer"] == "Dies ist eine Testantwort zu den Regulierungsanforderungen."

    def test_query_endpoint_invalid_request(self, client):
        """Testet /api/query Endpunkt mit ungültigen Anfragedaten"""
        response = client.post("/api/query", json={})
        assert response.status_code == 422

    def test_query_endpoint_empty_query(self, client):
        """Testet /api/query Endpunkt mit leerer Anfrage"""
        request_data = {"query": ""}
        response = client.post("/api/query", json=request_data)

        assert response.status_code == 200

    def test_dokumente_endpoint(self, client):
        """Testet /api/dokumente Endpunkt gibt Dokumentstatistiken zurück"""
        response = client.get("/api/dokumente")

        assert response.status_code == 200
        data = response.json()

        assert "gesamt_dokumente" in data
        assert "dokument_titel" in data

        assert data["gesamt_dokumente"] == 2
        assert data["dokument_titel"] == [
            "MaRisk - Mindestanforderungen an das Risikomanagement",
            "BAIT - Bankaufsichtliche Anforderungen an die IT",
        ]

    def test_clear_session_endpoint(self, client, sample_clear_session_request):
        """Testet /api/clear-session Endpunkt"""
        response = client.post("/api/clear-session", json=sample_clear_session_request)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["message"] == "Sitzung erfolgreich gelöscht"

    def test_clear_session_endpoint_invalid_request(self, client):
        """Testet /api/clear-session Endpunkt mit ungültiger Anfrage"""
        response = client.post("/api/clear-session", json={})
        assert response.status_code == 422

    def test_nonexistent_endpoint(self, client):
        """Testet den Zugriff auf einen nicht existierenden Endpunkt"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404


@pytest.mark.api
class TestAPIErrorHandling:
    """Testsuite für API-Fehlerbehandlung"""

    def test_query_endpoint_with_rag_system_error(self, client):
        """Testet /api/query Endpunkt-Struktur"""
        request_data = {"query": "Testanfrage"}
        response = client.post("/api/query", json=request_data)

        assert response.status_code == 200

    def test_dokumente_endpoint_with_rag_system_error(self, client):
        """Testet /api/dokumente Endpunkt"""
        response = client.get("/api/dokumente")
        assert response.status_code == 200


@pytest.mark.api
class TestAPIRequestValidation:
    """Testsuite für API-Anfrage-Validierung"""

    def test_query_endpoint_with_extra_fields(self, client):
        """Testet ob /api/query extra Felder ignoriert"""
        request_data = {
            "query": "Was sind die MaRisk-Anforderungen?",
            "session_id": "test-123",
            "extra_field": "wird ignoriert",
        }
        response = client.post("/api/query", json=request_data)
        assert response.status_code == 200

    def test_query_endpoint_with_wrong_types(self, client):
        """Testet /api/query mit falschen Feldtypen"""
        request_data = {
            "query": 123,
            "session_id": "test-123",
        }
        response = client.post("/api/query", json=request_data)
        assert response.status_code == 422

    def test_clear_session_with_wrong_types(self, client):
        """Testet /api/clear-session mit falschen Feldtypen"""
        request_data = {"session_id": 123}
        response = client.post("/api/clear-session", json=request_data)
        assert response.status_code == 422


@pytest.mark.api
class TestAPIHeaders:
    """Testsuite für API-Header und CORS"""

    def test_cors_headers(self, client):
        """Testet ob CORS-Header korrekt gesetzt sind"""
        response = client.get("/")
        assert response.status_code == 200

    def test_options_request(self, client):
        """Testet OPTIONS-Anfrage für CORS-Preflight"""
        response = client.options("/api/query")
        assert response.status_code in [200, 405]


@pytest.mark.api
@pytest.mark.integration
class TestAPIIntegration:
    """Integrationstests für API-Endpunkte"""

    def test_full_query_workflow(self, client):
        """Testet einen vollständigen Anfrage-Workflow"""
        dokumente_response = client.get("/api/dokumente")
        assert dokumente_response.status_code == 200

        query_response = client.post(
            "/api/query",
            json={"query": "Welche Dokumente sind verfügbar?"},
        )
        assert query_response.status_code == 200
        session_id = query_response.json()["session_id"]

        follow_up_response = client.post(
            "/api/query",
            json={
                "query": "Können Sie das genauer erläutern?",
                "session_id": session_id,
            },
        )
        assert follow_up_response.status_code == 200
        assert follow_up_response.json()["session_id"] == session_id

        clear_response = client.post(
            "/api/clear-session", json={"session_id": session_id}
        )
        assert clear_response.status_code == 200

    def test_multiple_concurrent_sessions(self, client):
        """Testet die Behandlung mehrerer gleichzeitiger Sitzungen"""
        response1 = client.post(
            "/api/query", json={"query": "Erste Sitzungsanfrage"}
        )
        session1 = response1.json()["session_id"]

        response2 = client.post(
            "/api/query", json={"query": "Zweite Sitzungsanfrage"}
        )
        session2 = response2.json()["session_id"]

        assert response1.status_code == 200
        assert response2.status_code == 200
