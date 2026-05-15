import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_generator import AIGenerator


class TestAIGenerator:
    """Testfälle für AIGenerator"""

    def test_init(self):
        """Testet AIGenerator-Initialisierung"""
        generator = AIGenerator("test-api-key", "claude-sonnet-4-5")

        assert generator.model == "claude-sonnet-4-5"
        assert generator.base_params["model"] == "claude-sonnet-4-5"
        assert generator.base_params["temperature"] == 0
        assert generator.base_params["max_tokens"] == 1200

    def test_generate_response_without_tools(self, mock_anthropic_client):
        """Testet einfache Antworterzeugung ohne Werkzeuge"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_anthropic_client

            generator = AIGenerator("test-api-key", "claude-sonnet-4-5")

            response = generator.generate_response("Was ist KI?")

            assert response == "Dies ist eine Testantwort von Claude."

            mock_anthropic_client.messages.create.assert_called_once()
            call_args = mock_anthropic_client.messages.create.call_args[1]

            assert call_args["model"] == "claude-sonnet-4-5"
            assert call_args["temperature"] == 0
            assert call_args["max_tokens"] == 1200
            assert call_args["messages"] == [{"role": "user", "content": "Was ist KI?"}]
            assert "tools" not in call_args

    def test_generate_response_with_conversation_history(self, mock_anthropic_client):
        """Testet Antworterzeugung mit Gesprächshistorie"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_anthropic_client

            generator = AIGenerator("test-api-key", "claude-sonnet-4-5")

            history = "Vorheriger Gesprächskontext"
            response = generator.generate_response(
                "Folgefrage", conversation_history=history
            )

            assert response == "Dies ist eine Testantwort von Claude."

            call_args = mock_anthropic_client.messages.create.call_args[1]
            assert "Vorheriger Gesprächskontext" in call_args["system"]

    def test_generate_response_with_tools_no_tool_use(
        self, mock_anthropic_client, mock_tool_manager
    ):
        """Testet Antworterzeugung mit verfügbaren aber nicht genutzten Werkzeugen"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_anthropic_client

            generator = AIGenerator("test-api-key", "claude-sonnet-4-5")

            tools = mock_tool_manager.get_tool_definitions()
            response = generator.generate_response(
                "Was ist maschinelles Lernen?",
                tools=tools,
                tool_manager=mock_tool_manager,
            )

            assert response == "Dies ist eine Testantwort von Claude."

            call_args = mock_anthropic_client.messages.create.call_args[1]
            assert "tools" in call_args
            assert call_args["tool_choice"] == {"type": "auto"}
            assert call_args["tools"] == tools

    def test_generate_response_with_tool_use(self, mock_tool_manager):
        """Testet Antworterzeugung wenn Claude Werkzeugnutzung anfordert"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client

            initial_response = Mock()
            initial_response.stop_reason = "tool_use"
            initial_response.content = [Mock()]
            initial_response.content[0].type = "tool_use"
            initial_response.content[0].name = "regulierungsdokument_suchen"
            initial_response.content[0].id = "tool_123"
            initial_response.content[0].input = {"suchanfrage": "Testanfrage"}

            final_response = Mock()
            final_response.content = [Mock()]
            final_response.content[0].text = (
                "Basierend auf den Suchergebnissen hier die Antwort."
            )

            mock_client.messages.create.side_effect = [initial_response, final_response]

            generator = AIGenerator("test-api-key", "claude-sonnet-4-5")

            tools = mock_tool_manager.get_tool_definitions()
            response = generator.generate_response(
                "Was sind die MaRisk-Anforderungen?",
                tools=tools,
                tool_manager=mock_tool_manager,
            )

            assert response == "Basierend auf den Suchergebnissen hier die Antwort."

            mock_tool_manager.execute_tool.assert_called_once_with(
                "regulierungsdokument_suchen", suchanfrage="Testanfrage"
            )

            assert mock_client.messages.create.call_count == 2

    def test_generate_response_tool_use_multiple_tools(self, mock_tool_manager):
        """Testet Antworterzeugung wenn Claude mehrere Werkzeuge anfordert"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client

            initial_response = Mock()
            initial_response.stop_reason = "tool_use"

            tool1 = Mock()
            tool1.type = "tool_use"
            tool1.name = "regulierungsdokument_suchen"
            tool1.id = "tool_123"
            tool1.input = {"suchanfrage": "erste Anfrage"}

            tool2 = Mock()
            tool2.type = "tool_use"
            tool2.name = "dokument_struktur_abrufen"
            tool2.id = "tool_456"
            tool2.input = {"dokument_name": "MaRisk"}

            initial_response.content = [tool1, tool2]

            final_response = Mock()
            final_response.content = [Mock()]
            final_response.content[0].text = "Hier die umfassende Antwort."

            mock_client.messages.create.side_effect = [initial_response, final_response]

            generator = AIGenerator("test-api-key", "claude-sonnet-4-5")

            response = generator.generate_response(
                "Erläutern Sie die MaRisk",
                tools=mock_tool_manager.get_tool_definitions(),
                tool_manager=mock_tool_manager,
            )

            assert response == "Hier die umfassende Antwort."

            assert mock_tool_manager.execute_tool.call_count == 2
            mock_tool_manager.execute_tool.assert_any_call(
                "regulierungsdokument_suchen", suchanfrage="erste Anfrage"
            )
            mock_tool_manager.execute_tool.assert_any_call(
                "dokument_struktur_abrufen", dokument_name="MaRisk"
            )

    def test_handle_tool_execution_conversation_flow(self, mock_tool_manager):
        """Testet ob Werkzeugausführung den Gesprächsfluss korrekt pflegt"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client

            initial_response = Mock()
            initial_response.stop_reason = "tool_use"
            initial_response.content = [Mock()]
            initial_response.content[0].type = "tool_use"
            initial_response.content[0].name = "regulierungsdokument_suchen"
            initial_response.content[0].id = "tool_123"
            initial_response.content[0].input = {"suchanfrage": "MaRisk Inhalt"}

            final_response = Mock()
            final_response.content = [Mock()]
            final_response.content[0].text = "Endantwort mit Werkzeugergebnissen."

            mock_client.messages.create.side_effect = [initial_response, final_response]

            generator = AIGenerator("test-api-key", "claude-sonnet-4-5")

            response = generator.generate_response(
                "Was steht in MaRisk Abschnitt 1?",
                tools=mock_tool_manager.get_tool_definitions(),
                tool_manager=mock_tool_manager,
            )

            final_call_args = mock_client.messages.create.call_args_list[1][1]
            messages = final_call_args["messages"]

            assert len(messages) == 3
            assert messages[0]["role"] == "user"
            assert messages[0]["content"] == "Was steht in MaRisk Abschnitt 1?"
            assert messages[1]["role"] == "assistant"
            assert messages[1]["content"] == initial_response.content
            assert messages[2]["role"] == "user"
            assert messages[2]["content"][0]["type"] == "tool_result"
            assert messages[2]["content"][0]["tool_use_id"] == "tool_123"
            assert messages[2]["content"][0]["content"] == "Mock-Suchergebnis"

    def test_generate_response_tool_execution_error(self, mock_tool_manager):
        """Testet Fehlerbehandlung bei fehlgeschlagener Werkzeugausführung"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client

            initial_response = Mock()
            initial_response.stop_reason = "tool_use"
            initial_response.content = [Mock()]
            initial_response.content[0].type = "tool_use"
            initial_response.content[0].name = "regulierungsdokument_suchen"
            initial_response.content[0].id = "tool_123"
            initial_response.content[0].input = {"suchanfrage": "test"}

            final_response = Mock()
            final_response.content = [Mock()]
            final_response.content[0].text = "Fehler bei der Suche aufgetreten."

            mock_client.messages.create.side_effect = [initial_response, final_response]

            mock_tool_manager.execute_tool.return_value = "Error: Tool execution failed"

            generator = AIGenerator("test-api-key", "claude-sonnet-4-5")

            response = generator.generate_response(
                "Suche nach etwas",
                tools=mock_tool_manager.get_tool_definitions(),
                tool_manager=mock_tool_manager,
            )

            assert response == "Fehler bei der Suche aufgetreten."

            final_call_args = mock_client.messages.create.call_args_list[1][1]
            tool_result = final_call_args["messages"][2]["content"][0]
            assert tool_result["content"] == "Error: Tool execution failed"

    def test_system_prompt_content(self):
        """Testet ob der Systemprompt den erwarteten deutschen Inhalt enthält"""
        assert "Finanzregulierung" in AIGenerator.SYSTEM_PROMPT
        assert "regulierungsdokument_suchen" in AIGenerator.SYSTEM_PROMPT
        assert "dokument_struktur_abrufen" in AIGenerator.SYSTEM_PROMPT
        assert "2 Suchrunden" in AIGenerator.SYSTEM_PROMPT
        assert "Präzise und knapp" in AIGenerator.SYSTEM_PROMPT

    def test_api_parameters_consistency(self, mock_anthropic_client):
        """Testet ob API-Parameter über Aufrufe hinweg konsistent sind"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            mock_anthropic.return_value = mock_anthropic_client

            generator = AIGenerator("test-api-key", "claude-sonnet-4-5")

            generator.generate_response("Erste Frage")
            generator.generate_response(
                "Zweite Frage", conversation_history="Vorheriger Kontext"
            )

            calls = mock_anthropic_client.messages.create.call_args_list

            for call in calls:
                args = call[1]
                assert args["model"] == "claude-sonnet-4-5"
                assert args["temperature"] == 0
                assert args["max_tokens"] == 1200

    def test_no_tool_manager_with_tool_use(self):
        """Testet Verhalten wenn Werkzeuge angefordert werden aber kein tool_manager vorhanden"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client

            tool_response = Mock()
            tool_response.stop_reason = "tool_use"
            tool_response.content = [Mock()]
            tool_response.content[0].text = "Ich benötige ein Werkzeug"

            mock_client.messages.create.return_value = tool_response

            generator = AIGenerator("test-api-key", "claude-sonnet-4-5")

            response = generator.generate_response(
                "Suche nach etwas", tools=[{"name": "test_tool"}]
            )

            assert response == "Ich benötige ein Werkzeug"

            assert mock_client.messages.create.call_count == 1

    def test_empty_tool_results(self, mock_tool_manager):
        """Testet Behandlung wenn keine Werkzeugaufrufe in der tool_use Antwort"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client

            initial_response = Mock()
            initial_response.stop_reason = "tool_use"
            initial_response.content = []

            final_response = Mock()
            final_response.content = [Mock()]
            final_response.content[0].text = "Keine Werkzeuge wurden verwendet."

            mock_client.messages.create.side_effect = [initial_response, final_response]

            generator = AIGenerator("test-api-key", "claude-sonnet-4-5")

            response = generator.generate_response(
                "Testanfrage",
                tools=mock_tool_manager.get_tool_definitions(),
                tool_manager=mock_tool_manager,
            )

            assert response == "Keine Werkzeuge wurden verwendet."

            mock_tool_manager.execute_tool.assert_not_called()

            assert mock_client.messages.create.call_count == 2

    def test_sequential_tool_calling_two_rounds(self, mock_tool_manager):
        """Testet sequenzielle Werkzeugaufrufe über 2 Runden"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client

            round1_response = Mock()
            round1_response.stop_reason = "tool_use"
            round1_response.content = [Mock()]
            round1_response.content[0].type = "tool_use"
            round1_response.content[0].name = "dokument_struktur_abrufen"
            round1_response.content[0].id = "tool_1"
            round1_response.content[0].input = {"dokument_name": "MaRisk"}

            round2_response = Mock()
            round2_response.stop_reason = "tool_use"
            round2_response.content = [Mock()]
            round2_response.content[0].type = "tool_use"
            round2_response.content[0].name = "regulierungsdokument_suchen"
            round2_response.content[0].id = "tool_2"
            round2_response.content[0].input = {"suchanfrage": "AT 4 Inhalt"}

            final_response = Mock()
            final_response.content = [Mock()]
            final_response.content[0].text = (
                "Basierend auf der Dokumentstruktur und dem Inhalt hier die Antwort."
            )

            mock_client.messages.create.side_effect = [
                round1_response,
                round2_response,
                final_response,
            ]

            generator = AIGenerator("test-api-key", "claude-sonnet-4-5")

            response = generator.generate_response(
                "Finde AT 4 Inhalt aus MaRisk",
                tools=mock_tool_manager.get_tool_definitions(),
                tool_manager=mock_tool_manager,
            )

            assert (
                response
                == "Basierend auf der Dokumentstruktur und dem Inhalt hier die Antwort."
            )

            assert mock_tool_manager.execute_tool.call_count == 2
            mock_tool_manager.execute_tool.assert_any_call(
                "dokument_struktur_abrufen", dokument_name="MaRisk"
            )
            mock_tool_manager.execute_tool.assert_any_call(
                "regulierungsdokument_suchen", suchanfrage="AT 4 Inhalt"
            )

            assert mock_client.messages.create.call_count == 3

    def test_sequential_tool_calling_early_termination(self, mock_tool_manager):
        """Testet frühes Beenden der sequenziellen Werkzeugaufrufe"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client

            round1_response = Mock()
            round1_response.stop_reason = "tool_use"
            round1_response.content = [Mock()]
            round1_response.content[0].type = "tool_use"
            round1_response.content[0].name = "regulierungsdokument_suchen"
            round1_response.content[0].id = "tool_1"
            round1_response.content[0].input = {"suchanfrage": "Testanfrage"}

            round2_response = Mock()
            round2_response.stop_reason = "stop"
            round2_response.content = [Mock()]
            round2_response.content[0].text = (
                "Direkte Antwort basierend auf den Suchergebnissen."
            )

            mock_client.messages.create.side_effect = [round1_response, round2_response]

            generator = AIGenerator("test-api-key", "claude-sonnet-4-5")

            response = generator.generate_response(
                "Was steht in MaRisk?",
                tools=mock_tool_manager.get_tool_definitions(),
                tool_manager=mock_tool_manager,
            )

            assert response == "Direkte Antwort basierend auf den Suchergebnissen."

            assert mock_tool_manager.execute_tool.call_count == 1
            mock_tool_manager.execute_tool.assert_called_with(
                "regulierungsdokument_suchen", suchanfrage="Testanfrage"
            )

            assert mock_client.messages.create.call_count == 2

    def test_sequential_tool_calling_tool_failure_stops_rounds(self, mock_tool_manager):
        """Testet ob Werkzeugausführungsfehler die sequenziellen Runden stoppt"""
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client

            round1_response = Mock()
            round1_response.stop_reason = "tool_use"
            round1_response.content = [Mock()]
            round1_response.content[0].type = "tool_use"
            round1_response.content[0].name = "regulierungsdokument_suchen"
            round1_response.content[0].id = "tool_1"
            round1_response.content[0].input = {"suchanfrage": "Testanfrage"}

            final_response = Mock()
            final_response.content = [Mock()]
            final_response.content[0].text = "Fehler bei der Suche aufgetreten."

            mock_tool_manager.execute_tool.side_effect = Exception("Werkzeug fehlgeschlagen")

            mock_client.messages.create.side_effect = [round1_response, final_response]

            generator = AIGenerator("test-api-key", "claude-sonnet-4-5")

            response = generator.generate_response(
                "Suche nach etwas",
                tools=mock_tool_manager.get_tool_definitions(),
                tool_manager=mock_tool_manager,
            )

            assert response == "Fehler bei der Suche aufgetreten."

            assert mock_tool_manager.execute_tool.call_count == 1

            assert mock_client.messages.create.call_count == 2

            final_call_args = mock_client.messages.create.call_args_list[1][1]
            tool_result_message = final_call_args["messages"][-1]
            assert tool_result_message["role"] == "user"
            assert (
                "Error: Tool execution failed"
                in tool_result_message["content"][0]["content"]
            )
