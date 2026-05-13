"""
Tests for RAGSystem.query() content-question handling in rag_system.py.

Patches VectorStore, AIGenerator, and DocumentProcessor so tests run
without Chroma on disk or a live Anthropic key.
"""
import pytest
from unittest.mock import MagicMock, patch
from rag_system import RAGSystem


class FakeConfig:
    ANTHROPIC_API_KEY = "test-key"
    ANTHROPIC_MODEL = "claude-test"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 100
    MAX_RESULTS = 5
    MAX_HISTORY = 2
    CHROMA_PATH = "/tmp/test_chroma_rag"


@pytest.fixture
def rag(tmp_path):
    """RAGSystem with all heavy dependencies mocked out."""
    fake_cfg = FakeConfig()
    fake_cfg.CHROMA_PATH = str(tmp_path / "chroma")

    with (
        patch("rag_system.VectorStore"),
        patch("rag_system.AIGenerator") as mock_ai_cls,
        patch("rag_system.DocumentProcessor"),
    ):
        system = RAGSystem(fake_cfg)
        # ai_generator is already a MagicMock via the patch; expose as _ai for tests
        system._ai = system.ai_generator
        # Replace ToolManager with a MagicMock so tests can control return values
        system.tool_manager = MagicMock()
        yield system


# ── response + source pipeline ───────────────────────────────────────────────

class TestQueryPipeline:
    def test_returns_ai_response_text(self, rag):
        rag._ai.generate_response.return_value = "Python uses indentation for blocks."
        rag.tool_manager.get_last_sources.return_value = []

        response, _ = rag.query("What is Python indentation?")
        assert response == "Python uses indentation for blocks."

    def test_returns_sources_from_tool_manager(self, rag):
        rag._ai.generate_response.return_value = "Answer here."
        rag.tool_manager.get_last_sources.return_value = [
            {"label": "Python Course - Lesson 1", "url": "https://example.com/l1"},
        ]

        _, sources = rag.query("Explain decorators")
        assert len(sources) == 1
        assert sources[0]["label"] == "Python Course - Lesson 1"

    def test_empty_sources_when_no_tool_called(self, rag):
        rag._ai.generate_response.return_value = "General answer."
        rag.tool_manager.get_last_sources.return_value = []

        _, sources = rag.query("What is 2+2?")
        assert sources == []

    def test_multiple_sources_all_returned(self, rag):
        rag._ai.generate_response.return_value = "Answer."
        rag.tool_manager.get_last_sources.return_value = [
            {"label": "Course A - Lesson 1", "url": None},
            {"label": "Course A - Lesson 2", "url": "https://x.com/2"},
        ]

        _, sources = rag.query("Something spanning two lessons")
        assert len(sources) == 2


# ── prompt construction ───────────────────────────────────────────────────────

class TestPromptConstruction:
    def test_user_query_included_in_prompt(self, rag):
        rag._ai.generate_response.return_value = "ok"
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("explain recursion please")

        call_kwargs = rag._ai.generate_response.call_args[1]
        sent_query = call_kwargs.get("query") or rag._ai.generate_response.call_args[0][0]
        assert "recursion" in sent_query

    def test_tool_definitions_passed_to_ai(self, rag):
        rag._ai.generate_response.return_value = "ok"
        rag.tool_manager.get_last_sources.return_value = []
        rag.tool_manager.get_tool_definitions.return_value = [{"name": "search_course_content"}]

        rag.query("test")

        call_kwargs = rag._ai.generate_response.call_args[1]
        assert call_kwargs.get("tools") == [{"name": "search_course_content"}]

    def test_tool_manager_passed_to_ai(self, rag):
        rag._ai.generate_response.return_value = "ok"
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("test")

        call_kwargs = rag._ai.generate_response.call_args[1]
        assert call_kwargs.get("tool_manager") is rag.tool_manager


# ── source lifecycle ──────────────────────────────────────────────────────────

class TestSourceLifecycle:
    def test_sources_reset_after_each_query(self, rag):
        rag._ai.generate_response.return_value = "ok"
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("first question")

        rag.tool_manager.reset_sources.assert_called_once()

    def test_sources_reset_even_when_sources_exist(self, rag):
        rag._ai.generate_response.return_value = "ok"
        rag.tool_manager.get_last_sources.return_value = [{"label": "X", "url": None}]

        rag.query("second question")

        rag.tool_manager.reset_sources.assert_called_once()


# ── session / history wiring ──────────────────────────────────────────────────

class TestSessionHandling:
    def test_no_history_passed_when_session_id_is_none(self, rag):
        rag._ai.generate_response.return_value = "ok"
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("question", session_id=None)

        call_kwargs = rag._ai.generate_response.call_args[1]
        assert call_kwargs.get("conversation_history") is None

    def test_history_passed_when_session_exists(self, rag):
        session_id = rag.session_manager.create_session()
        rag.session_manager.add_exchange(session_id, "hello", "hi there")

        rag._ai.generate_response.return_value = "ok"
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("follow-up", session_id=session_id)

        call_kwargs = rag._ai.generate_response.call_args[1]
        assert call_kwargs.get("conversation_history") is not None
        assert "hello" in call_kwargs["conversation_history"]

    def test_exchange_saved_to_session_after_query(self, rag):
        session_id = rag.session_manager.create_session()
        rag._ai.generate_response.return_value = "The answer."
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("my question", session_id=session_id)

        history = rag.session_manager.get_conversation_history(session_id)
        assert history is not None
        assert "my question" in history
        assert "The answer." in history


# ── exception propagation ─────────────────────────────────────────────────────

class TestExceptionPropagation:
    def test_tool_loop_fallback_does_not_raise(self, rag):
        """
        Fixed: when the generator returns a fallback message (tool loop exhausted),
        rag.query() returns that string gracefully instead of raising.
        """
        fallback = "I was unable to generate a response after searching the course materials. Please try rephrasing your question."
        rag._ai.generate_response.return_value = fallback
        rag.tool_manager.get_last_sources.return_value = []

        response, sources = rag.query("content question that triggers tool loop")
        assert response == fallback

    def test_store_error_propagates(self, rag):
        rag._ai.generate_response.side_effect = RuntimeError("Chroma exploded")
        rag.tool_manager.get_last_sources.return_value = []

        with pytest.raises(RuntimeError, match="Chroma exploded"):
            rag.query("any question")
