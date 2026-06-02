# Example 1: Basic Query - Semantic Search Fundamentals

## What This Demonstrates

This example shows the **core RAG capability**: finding relevant regulatory requirements through semantic search, without requiring exact keyword matches.

## The Query

```
"What are the main IT security requirements for financial institutions in Germany?"
```

## Why This Matters

- **No Exact Keywords**: Query doesn't use regulatory acronyms (BAIT, MaRisk)
- **Semantic Understanding**: System understands intent and finds relevant sections
- **Source Attribution**: Response includes citations for verification
- **Regulatory Compliance**: Financial institutions need authoritative answers backed by official sources

## How the System Handles It

```
1. USER ASKS: "What are the main IT security requirements..."
   └─ Query converted to embedding vector

2. SEMANTIC SEARCH: Vector compared against document embeddings
   ├─ Searches across BAIT (Banking IT requirements)
   ├─ Searches across Bundesbank guidelines
   └─ Returns top-5 most similar sections

3. CLAUDE GENERATION: LLM reads search results
   ├─ Synthesizes answer from multiple sources
   ├─ Maintains context and relationships
   └─ Cites source documents

4. RESPONSE: Answer with source links
   ├─ Clear, structured response
   ├─ Professional tone
   └─ Provides ways to dive deeper
```

## Expected Output Characteristics

- **Answer Length**: 2-3 paragraphs covering main categories
- **Sources**: Typically 2-4 document sections cited
- **Tone**: Professional, regulatory-focused
- **Completeness**: Covers at least 3 major requirement areas

## Real-World Use Case

**Scenario**: New compliance officer joins a financial institution and needs to understand IT security obligations quickly.

**Value Proposition**:
- No manual search through 400+ page documents
- Gets authoritative answer in seconds
- Knows which documents to review for details
- Can ask follow-up questions without context loss

## Variations to Try

Similar queries that demonstrate semantic search flexibility:

1. "How should banks protect their data systems?"
   - Tests: Synonym understanding, broad vs. specific

2. "What does BAIT say about information security?"
   - Tests: Acronym recognition, document-specific queries

3. "List the key infrastructure security controls"
   - Tests: List generation, technical terminology

---

**Performance**: ~150-200ms end-to-end (includes network latency)  
**Model**: Claude Sonnet 4.5 with tool-calling enabled
