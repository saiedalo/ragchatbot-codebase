"""
Tests for FastAPI endpoints in app.py.

Uses the TestClient and mock_rag/client fixtures defined in conftest.py.
All heavy dependencies (ChromaDB, Anthropic, StaticFiles) are mocked at the
conftest module level, so these tests exercise the real routing and request/
response logic without any external services.
"""
import pytest


class TestQueryEndpoint:
    """POST /api/query"""

    def test_returns_answer_sources_and_session_id(self, client, mock_rag, sample_sources):
        mock_rag.session_manager.create_session.return_value = "sess-abc"
        mock_rag.query.return_value = ("Python uses indentation.", sample_sources)

        resp = client.post("/api/query", json={"query": "What is Python?"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["answer"] == "Python uses indentation."
        assert body["session_id"] == "sess-abc"
        assert body["sources"][0]["label"] == "Python Basics - Lesson 1"

    def test_auto_creates_session_when_none_provided(self, client, mock_rag):
        mock_rag.session_manager.create_session.return_value = "new-session-99"
        mock_rag.query.return_value = ("Answer.", [])

        resp = client.post("/api/query", json={"query": "hello"})

        assert resp.status_code == 200
        assert resp.json()["session_id"] == "new-session-99"
        mock_rag.session_manager.create_session.assert_called_once()

    def test_uses_provided_session_id(self, client, mock_rag):
        mock_rag.query.return_value = ("Follow-up answer.", [])

        resp = client.post(
            "/api/query",
            json={"query": "follow-up", "session_id": "existing-session"},
        )

        assert resp.status_code == 200
        assert resp.json()["session_id"] == "existing-session"
        mock_rag.session_manager.create_session.assert_not_called()

    def test_passes_query_text_to_rag(self, client, mock_rag):
        mock_rag.query.return_value = ("ok", [])

        client.post(
            "/api/query",
            json={"query": "explain recursion", "session_id": "s1"},
        )

        assert "recursion" in mock_rag.query.call_args[0][0]

    def test_returns_422_for_missing_query_field(self, client, mock_rag):
        resp = client.post("/api/query", json={})

        assert resp.status_code == 422

    def test_returns_500_when_rag_raises(self, client, mock_rag):
        mock_rag.query.side_effect = RuntimeError("ChromaDB is down")

        resp = client.post("/api/query", json={"query": "something", "session_id": "s1"})

        assert resp.status_code == 500
        assert "ChromaDB is down" in resp.json()["detail"]


class TestCoursesEndpoint:
    """GET /api/courses"""

    def test_returns_total_courses_and_titles(self, client, mock_rag):
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 2,
            "course_titles": ["Python Basics", "Machine Learning"],
        }

        resp = client.get("/api/courses")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_courses"] == 2
        assert "Python Basics" in body["course_titles"]
        assert "Machine Learning" in body["course_titles"]

    def test_returns_zero_courses_when_catalog_empty(self, client, mock_rag):
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        resp = client.get("/api/courses")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_courses"] == 0
        assert body["course_titles"] == []

    def test_returns_500_when_rag_raises(self, client, mock_rag):
        mock_rag.get_course_analytics.side_effect = Exception("store unavailable")

        resp = client.get("/api/courses")

        assert resp.status_code == 500
        assert "store unavailable" in resp.json()["detail"]


class TestClearSessionEndpoint:
    """DELETE /api/session/{session_id}"""

    def test_returns_cleared_status_with_session_id(self, client, mock_rag):
        resp = client.delete("/api/session/my-session-id")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "cleared"
        assert body["session_id"] == "my-session-id"

    def test_calls_clear_session_with_correct_id(self, client, mock_rag):
        client.delete("/api/session/target-session")

        mock_rag.session_manager.clear_session.assert_called_once_with("target-session")


class TestFrontendMount:
    """GET / — static frontend served by the mounted handler"""

    def test_root_returns_200(self, client, mock_rag):
        resp = client.get("/")

        assert resp.status_code == 200
