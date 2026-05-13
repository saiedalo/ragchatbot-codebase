"""
Tests for CourseSearchTool.execute() in search_tools.py.

Covers: successful results, empty results, course/lesson filters,
store errors, source tracking, and multi-result formatting.
"""
import pytest
from unittest.mock import MagicMock
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


# ── helpers ──────────────────────────────────────────────────────────────────

def make_results(docs, metadatas):
    return SearchResults(
        documents=docs,
        metadata=metadatas,
        distances=[0.1] * len(docs),
    )


@pytest.fixture
def store():
    s = MagicMock()
    s.get_lesson_link.return_value = None
    return s


# ── execute() output ─────────────────────────────────────────────────────────

class TestExecuteOutput:
    def test_returns_course_title_and_content_when_results_exist(self, store):
        store.search.return_value = make_results(
            ["Python functions allow code reuse."],
            [{"course_title": "Python Basics", "lesson_number": 1}],
        )
        tool = CourseSearchTool(store)
        result = tool.execute(query="Python functions")

        assert "Python Basics" in result
        assert "Lesson 1" in result
        assert "Python functions allow code reuse." in result

    def test_returns_no_content_message_when_collection_empty(self, store):
        store.search.return_value = SearchResults(documents=[], metadata=[], distances=[])
        tool = CourseSearchTool(store)
        result = tool.execute(query="nonexistent topic")

        assert "No relevant content found" in result

    def test_empty_message_names_course_when_filter_applied(self, store):
        store.search.return_value = SearchResults(documents=[], metadata=[], distances=[])
        tool = CourseSearchTool(store)
        result = tool.execute(query="anything", course_name="ML Course")

        assert "ML Course" in result

    def test_empty_message_names_lesson_when_filter_applied(self, store):
        store.search.return_value = SearchResults(documents=[], metadata=[], distances=[])
        tool = CourseSearchTool(store)
        result = tool.execute(query="anything", lesson_number=4)

        assert "lesson 4" in result.lower()

    def test_returns_store_error_string_verbatim(self, store):
        store.search.return_value = SearchResults.empty("ChromaDB is empty, unable to query")
        tool = CourseSearchTool(store)
        result = tool.execute(query="anything")

        assert "ChromaDB is empty, unable to query" in result

    def test_multiple_results_all_appear_in_output(self, store):
        store.search.return_value = make_results(
            ["Lesson 1 content here.", "Lesson 2 content here."],
            [
                {"course_title": "Python Basics", "lesson_number": 1},
                {"course_title": "Python Basics", "lesson_number": 2},
            ],
        )
        tool = CourseSearchTool(store)
        result = tool.execute(query="Python")

        assert "Lesson 1" in result
        assert "Lesson 2" in result
        assert "Lesson 1 content here." in result
        assert "Lesson 2 content here." in result


# ── store call args ───────────────────────────────────────────────────────────

class TestExecuteForwardsCriteria:
    def test_passes_query_only_by_default(self, store):
        store.search.return_value = SearchResults(documents=[], metadata=[], distances=[])
        tool = CourseSearchTool(store)
        tool.execute(query="neural networks")

        store.search.assert_called_once_with(
            query="neural networks", course_name=None, lesson_number=None
        )

    def test_passes_course_name_filter(self, store):
        store.search.return_value = SearchResults(documents=[], metadata=[], distances=[])
        tool = CourseSearchTool(store)
        tool.execute(query="neural networks", course_name="Deep Learning")

        store.search.assert_called_once_with(
            query="neural networks", course_name="Deep Learning", lesson_number=None
        )

    def test_passes_lesson_number_filter(self, store):
        store.search.return_value = SearchResults(documents=[], metadata=[], distances=[])
        tool = CourseSearchTool(store)
        tool.execute(query="backprop", lesson_number=3)

        store.search.assert_called_once_with(
            query="backprop", course_name=None, lesson_number=3
        )

    def test_passes_both_filters(self, store):
        store.search.return_value = SearchResults(documents=[], metadata=[], distances=[])
        tool = CourseSearchTool(store)
        tool.execute(query="backprop", course_name="Deep Learning", lesson_number=3)

        store.search.assert_called_once_with(
            query="backprop", course_name="Deep Learning", lesson_number=3
        )


# ── source tracking ───────────────────────────────────────────────────────────

class TestSourceTracking:
    def test_last_sources_empty_before_any_search(self, store):
        tool = CourseSearchTool(store)
        assert tool.last_sources == []

    def test_sources_populated_after_successful_search(self, store):
        store.search.return_value = make_results(
            ["Some lesson content"],
            [{"course_title": "Data Science", "lesson_number": 2}],
        )
        store.get_lesson_link.return_value = "https://example.com/lesson/2"
        tool = CourseSearchTool(store)
        tool.execute(query="data analysis")

        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["label"] == "Data Science - Lesson 2"
        assert tool.last_sources[0]["url"] == "https://example.com/lesson/2"

    def test_sources_empty_when_no_results(self, store):
        store.search.return_value = SearchResults(documents=[], metadata=[], distances=[])
        tool = CourseSearchTool(store)
        tool.execute(query="nothing here")

        assert tool.last_sources == []

    def test_sources_count_matches_result_count(self, store):
        store.search.return_value = make_results(
            ["doc1", "doc2", "doc3"],
            [
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course A", "lesson_number": 2},
                {"course_title": "Course B", "lesson_number": 1},
            ],
        )
        tool = CourseSearchTool(store)
        tool.execute(query="test")

        assert len(tool.last_sources) == 3
