from typing import Any, Dict, List, Optional

import anthropic


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """Sie sind ein KI-Assistent, spezialisiert auf deutsche Finanzregulierung und Compliance, mit Zugriff auf Suchwerkzeuge für regulatorische Dokumente.

Verfügbare Werkzeuge:
- **regulierungsdokument_suchen**: Für Fragen zu spezifischen regulatorischen Anforderungen, Paragraphen oder Inhalten
- **dokument_struktur_abrufen**: Für Fragen zur Gliederung, Abschnittslisten oder Überblicke über Regulierungswerke

Werkzeug-Richtlinien:
- Nutzen Sie die Inhaltssuche für detaillierte Anforderungen (z.B. MaRisk AT 4.3, BAIT Tz. 12, GwG § 10)
- Nutzen Sie das Strukturwerkzeug für Fragen zur Gliederung oder vollständige Abschnittsübersichten
- **Sie können bis zu 2 Suchrunden durchführen**, um umfassende Informationen zu sammeln
- Nutzen Sie mehrere Runden bei komplexen Anfragen, die zuerst Informationssammlung und dann Präzisierung erfordern
- Synthetisieren Sie die Ergebnisse zu präzisen, faktenbasierten Antworten

Kritisch: Relevanzprüfung der Suchergebnisse:
- Prüfen Sie IMMER, ob die Suchergebnisse tatsächlich die gestellte Frage beantworten
- Wenn Suchergebnisse das gesuchte Dokument (z.B. MaRisk, GwG) NICHT enthalten und stattdessen Inhalte eines anderen Dokuments (z.B. BAIT) zurückgeben, teilen Sie dies klar mit
- Antworten Sie in diesem Fall: "Das Dokument [Name] ist in der aktuellen Wissensbasis nicht vollständig verfügbar. Die Suchergebnisse stammen aus [anderes Dokument] und sind für diese Frage nicht relevant."
- Erfinden Sie KEINE Antworten auf Basis irrelevanter Suchergebnisse

Antwortprotokoll:
- **Allgemeine Wissensfragen**: Beantworten Sie diese ohne Suche
- **Regulierungsspezifische Fragen**: Nutzen Sie zuerst das passende Werkzeug, dann antworten Sie
- **Kein Meta-Kommentar**: Geben Sie direkte Antworten — kein Hinweis auf Suchprozesse oder Werkzeugnutzung

Alle Antworten müssen:
1. **Präzise und knapp** sein — kommen Sie schnell auf den Punkt
2. **Fachlich korrekt** — Verwenden Sie die korrekte regulatorische Terminologie
3. **Verständlich** — Erklären Sie komplexe Anforderungen klar
4. **Quellenbasiert** — Antworten Sie nur auf Basis der gefundenen Dokumente, nicht aus allgemeinem Wissen
Geben Sie nur die direkte Antwort auf die gestellte Frage.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 1200}

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        Supports up to 2 sequential rounds of tool calling.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Start with initial messages
        messages = [{"role": "user", "content": query}]

        # Execute up to 2 rounds of tool calling
        for round_num in range(2):
            # Prepare API call parameters
            api_params = {
                **self.base_params,
                "messages": messages,
                "system": system_content,
            }

            # Add tools if available
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = {"type": "auto"}

            # Get response from Claude
            response = self.client.messages.create(**api_params)

            # Handle tool execution if needed
            if response.stop_reason == "tool_use" and tool_manager:
                messages, should_continue = self._handle_tool_execution(
                    response, messages, tool_manager
                )
                if not should_continue:
                    break
            else:
                # No tool use, return direct response
                return response.content[0].text

        # After max rounds, make final call without tools to get response
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content,
        }

        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text

    def _handle_tool_execution(self, initial_response, messages: List, tool_manager):
        """
        Handle execution of tool calls and update message history.

        Args:
            initial_response: The response containing tool use requests
            messages: Current message history
            tool_manager: Manager to execute tools

        Returns:
            Tuple of (updated_messages, should_continue)
        """
        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})

        # Execute all tool calls and collect results
        tool_results = []
        for content_block in initial_response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result,
                        }
                    )
                except Exception as e:
                    # Tool execution failed, stop rounds
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": f"Error: Tool execution failed - {str(e)}",
                        }
                    )
                    # Add tool results and signal to stop
                    if tool_results:
                        messages.append({"role": "user", "content": tool_results})
                    return messages, False

        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        # Continue with next round
        return messages, True
