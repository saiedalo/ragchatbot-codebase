# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
cp .env.example .env   # add ANTHROPIC_API_KEY to .env
./run.sh               # starts server at http://localhost:8000
```

Manual start (equivalent):
```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`.

## Package Management

Always use **uv** — never pip directly. Dependencies are declared in `pyproject.toml` and pinned in `uv.lock`. There is no `.venv` directory to activate — `uv run` handles the environment automatically.

```bash
uv add <package>      # add a dependency
uv sync               # install all dependencies from lock file
uv run <script.py>    # run any Python file
```

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot. The backend is a single FastAPI process (`backend/`) that serves both the REST API and the static frontend (`frontend/`).

**Query flow:**
1. Frontend (`script.js`) POSTs `{query, session_id}` to `POST /api/query`
2. `app.py` creates a session if needed and calls `RAGSystem.query()`
3. `RAGSystem` builds a prompt, fetches session history, and calls `AIGenerator.generate_response()`
4. Claude is called with a `search_course_content` tool — if it fires, `CourseSearchTool` runs a semantic search against ChromaDB
5. ChromaDB first resolves the course name via the `course_catalog` collection, then fetches ranked chunks from `course_content`
6. Tool results are sent back to Claude for a second call that produces the final answer
7. The exchange is saved to `SessionManager` (in-memory, resets on restart, capped at `MAX_HISTORY=2` exchanges)

**Two-collection ChromaDB design:**
- `course_catalog` — one document per course (title + metadata). Used for fuzzy course-name resolution at query time.
- `course_content` — one document per text chunk. Used for semantic retrieval.

Both use `all-MiniLM-L6-v2` embeddings via `SentenceTransformerEmbeddingFunction`. The DB is persisted at `backend/chroma_db/`.

## Course Document Format

Documents in `docs/` must follow this structure for `DocumentProcessor` to parse them correctly:

```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 1: <lesson title>
Lesson Link: <url>
<lesson content...>

Lesson 2: <lesson title>
...
```

The course title doubles as the unique ID in ChromaDB — duplicate titles are skipped on startup. Text is chunked at 800 characters with 100-character sentence-boundary overlap.

## Key Configuration (`backend/config.py`)

| Setting | Default | Effect |
|---|---|---|
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Model used for generation |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer for embeddings |
| `CHUNK_SIZE` | `800` | Max characters per chunk |
| `CHUNK_OVERLAP` | `100` | Overlap between chunks |
| `MAX_RESULTS` | `5` | ChromaDB results per search |
| `MAX_HISTORY` | `2` | Conversation exchanges retained per session |
| `CHROMA_PATH` | `./chroma_db` | ChromaDB persistence path (relative to `backend/`) |
