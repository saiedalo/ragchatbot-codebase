# Examples & Use Cases

This directory contains real-world examples demonstrating the capabilities of the Enterprise RAG System. Each example shows a specific use case and how the system handles it.

## Quick Start

Each example includes:
- `query_example.json` - Sample query and response
- `explanation.md` - Why this matters and what it demonstrates

### Running Examples

```bash
# The examples are static documentation
# For interactive testing, use the web interface at http://localhost:8000
# or the API directly:

curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d @01-basic-query/query_example.json
```

## Example Categories

### 1. Basic Query (01-basic-query/)
**What it shows**: Simple semantic search with source attribution

Basic queries demonstrate the core RAG functionality - the system finds relevant documents and provides authoritative answers with proper citations.

**Use case**: Regulatory compliance teams checking specific requirements

### 2. Conversation Flow (02-conversation-flow/)
**What it shows**: Multi-turn conversations with context memory

Follow-up questions show how the system maintains conversation history, enabling exploratory research without losing context from previous exchanges.

**Use case**: Deep-dive research on complex regulatory topics

### 3. Tool Usage (03-tool-usage/)
**What it shows**: Claude AI using search tools for intelligent refinement

The system demonstrates intelligent tool-calling where Claude decides to search for additional information based on conversation context.

**Use case**: Complex queries requiring multiple search refinements

---

## Architecture & Design

```
Example Flow:
User Query
    ↓
FastAPI /api/query endpoint
    ↓
RAG System decides: search needed?
    ↓
Claude tool-calling
    ├─ Yes → Execute search
    └─ No → Use context
    ↓
Generate response with sources
    ↓
Return to user
```

## Document Sources

Examples use anonymized queries based on German banking regulations:
- BaFin BAIT (Banking IT requirements)
- Bundesbank guidelines
- MaRisk (Market risk management)

Actual documents are in `/docs/` directory.

## Contributing Examples

To add new examples:

1. Create a new directory: `XX-example-name/`
2. Add `query_example.json` with structure:
```json
{
  "query": "Your example question here",
  "session_id": "optional_session_id"
}
```

3. Add `explanation.md` explaining:
   - Why this is a useful example
   - What problem it demonstrates
   - Expected response characteristics

4. Update this README

---

**Last Updated**: 2026-06-02
