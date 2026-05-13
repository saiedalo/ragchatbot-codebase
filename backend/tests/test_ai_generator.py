"""
Tests for AIGenerator in ai_generator.py.

Covers: direct text responses, tool-use triggering, the agentic loop,
correct message construction for second API call, and error paths.
"""
import pytest
from unittest.mock import MagicMock, call, patch
from ai_generator import AIGenerator


# ── mock factories ────────────────────────────────────────────────────────────

def text_block(text):
    b = MagicMock()
    b.type = "text"
    b.text = text
    return b


def tool_use_block(name, tool_id, input_dict):
    b = MagicMock()
    b.type = "tool_use"
    b.name = name
    b.id = tool_id
    b.input = input_dict
    return b


def api_response(stop_reason, blocks):
    r = MagicMock()
    r.stop_reason = stop_reason
    r.content = blocks
    return r


@pytest.fixture
def gen():
    """AIGenerator with the Anthropic client replaced by a MagicMock."""
    with patch("ai_generator.anthropic.Anthropic") as mock_cls:
        client = MagicMock()
        mock_cls.return_value = client
        g = AIGenerator(api_key="fake", model="claude-test")
        g._client = client          # expose for assertions
        yield g


def tool_manager_mock(result="[Course]\nContent."):
    tm = MagicMock()
    tm.execute_tool.return_value = result
    return tm


# ── direct (no tool) responses ────────────────────────────────────────────────

class TestDirectResponse:
    def test_returns_text_for_end_turn_response(self, gen):
        gen._client.messages.create.return_value = api_response(
            "end_turn", [text_block("Python is a language.")]
        )
        assert gen.generate_response("What is Python?") == "Python is a language."

    def test_system_prompt_sent_in_api_call(self, gen):
        gen._client.messages.create.return_value = api_response("end_turn", [text_block("ok")])
        gen.generate_response("hi")
        kwargs = gen._client.messages.create.call_args[1]
        assert "system" in kwargs
        assert len(kwargs["system"]) > 0

    def test_tools_absent_from_call_when_not_provided(self, gen):
        gen._client.messages.create.return_value = api_response("end_turn", [text_block("ok")])
        gen.generate_response("hi")
        kwargs = gen._client.messages.create.call_args[1]
        assert "tools" not in kwargs

    def test_tools_present_in_call_when_provided(self, gen):
        gen._client.messages.create.return_value = api_response("end_turn", [text_block("ok")])
        tools = [{"name": "search_course_content", "description": "search"}]
        gen.generate_response("hi", tools=tools)
        kwargs = gen._client.messages.create.call_args[1]
        assert kwargs.get("tools") == tools

    def test_conversation_history_appended_to_system_prompt(self, gen):
        gen._client.messages.create.return_value = api_response("end_turn", [text_block("ok")])
        gen.generate_response("hi", conversation_history="User: hello\nAssistant: hi")
        kwargs = gen._client.messages.create.call_args[1]
        assert "hello" in kwargs["system"]


# ── tool-use / agentic loop ───────────────────────────────────────────────────

class TestToolUseLoop:
    def test_executes_tool_when_claude_requests_it(self, gen):
        gen._client.messages.create.side_effect = [
            api_response("tool_use", [tool_use_block("search_course_content", "t1", {"query": "MCP"})]),
            api_response("end_turn", [text_block("MCP stands for Model Context Protocol.")]),
        ]
        tm = tool_manager_mock("[MCP Course]\nMCP content here.")
        result = gen.generate_response(
            query="What is MCP?",
            tools=[{"name": "search_course_content"}],
            tool_manager=tm,
        )
        assert result == "MCP stands for Model Context Protocol."
        tm.execute_tool.assert_called_once_with("search_course_content", query="MCP")

    def test_tool_result_included_in_second_api_call(self, gen):
        """The second call to Claude must carry the tool result in messages."""
        gen._client.messages.create.side_effect = [
            api_response("tool_use", [tool_use_block("search_course_content", "t42", {"query": "test"})]),
            api_response("end_turn", [text_block("Final answer")]),
        ]
        tm = tool_manager_mock("Relevant search content")
        gen.generate_response(
            query="test question",
            tools=[{"name": "search_course_content"}],
            tool_manager=tm,
        )

        second_call_kwargs = gen._client.messages.create.call_args_list[1][1]
        messages = second_call_kwargs["messages"]

        # Last message should be user role with tool_result blocks
        last_msg = messages[-1]
        assert last_msg["role"] == "user"

        tool_results = last_msg["content"]
        assert len(tool_results) == 1
        tr = tool_results[0]
        assert tr["type"] == "tool_result"
        assert tr["tool_use_id"] == "t42"
        assert tr["content"] == "Relevant search content"

    def test_assistant_message_appended_before_tool_result(self, gen):
        """The assistant's tool_use message must precede the user's tool_result."""
        first_resp = api_response(
            "tool_use", [tool_use_block("search_course_content", "t1", {"query": "q"})]
        )
        gen._client.messages.create.side_effect = [
            first_resp,
            api_response("end_turn", [text_block("Done")]),
        ]
        gen.generate_response(
            query="q",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager_mock(),
        )

        second_call_kwargs = gen._client.messages.create.call_args_list[1][1]
        messages = second_call_kwargs["messages"]

        # messages[-2] = assistant (tool_use), messages[-1] = user (tool_result)
        assert messages[-2]["role"] == "assistant"
        assert messages[-1]["role"] == "user"

    def test_returns_fallback_message_after_exhausting_max_rounds(self, gen):
        """If Claude never produces text, a user-friendly message is returned instead of HTTP-500."""
        gen._client.messages.create.return_value = api_response(
            "tool_use",
            [tool_use_block("search_course_content", "t1", {"query": "loop"})],
        )
        tm = tool_manager_mock()
        result = gen.generate_response(
            query="loop forever",
            tools=[{"name": "search_course_content"}],
            tool_manager=tm,
        )
        assert "unable to generate" in result.lower() or "try rephrasing" in result.lower()

    def test_no_tool_manager_with_tool_use_response_returns_fallback(self, gen):
        """
        Fixed: if Claude returns tool_use but no tool_manager is passed,
        generate_response returns a graceful fallback instead of raising AttributeError.
        """
        tb = MagicMock(spec=["type", "name", "id", "input"])  # no .text
        tb.type = "tool_use"
        gen._client.messages.create.return_value = api_response("tool_use", [tb])

        result = gen.generate_response(
            query="content question",
            tools=[{"name": "search_course_content"}],
            # tool_manager intentionally omitted
        )
        assert "unable to process" in result.lower() or "try again" in result.lower()


# ── second API call parameters ────────────────────────────────────────────────

class TestSecondApiCallParams:
    def test_second_call_uses_same_model(self, gen):
        gen._client.messages.create.side_effect = [
            api_response("tool_use", [tool_use_block("search_course_content", "t1", {"query": "x"})]),
            api_response("end_turn", [text_block("ok")]),
        ]
        gen.generate_response(
            query="x",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager_mock(),
        )
        second_kwargs = gen._client.messages.create.call_args_list[1][1]
        assert second_kwargs["model"] == "claude-test"

    def test_second_call_includes_tools(self, gen):
        tools = [{"name": "search_course_content"}]
        gen._client.messages.create.side_effect = [
            api_response("tool_use", [tool_use_block("search_course_content", "t1", {"query": "x"})]),
            api_response("end_turn", [text_block("ok")]),
        ]
        gen.generate_response(query="x", tools=tools, tool_manager=tool_manager_mock())
        second_kwargs = gen._client.messages.create.call_args_list[1][1]
        assert second_kwargs.get("tools") == tools
