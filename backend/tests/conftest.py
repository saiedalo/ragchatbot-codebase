import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import MagicMock, patch


# ── load app.py with module-level side effects suppressed ─────────────────────
#
# app.py runs RAGSystem(config) and mounts StaticFiles(directory="../frontend")
# at import time. We neutralise both before the import so tests work without
# ChromaDB on disk, an Anthropic key, or the frontend directory present.

_rag_sentinel = MagicMock()

with (
    patch("rag_system.RAGSystem", return_value=_rag_sentinel),
    patch("fastapi.staticfiles.StaticFiles.__init__", return_value=None),
):
    import app as _app_module

# The DevStaticFiles instance created above is uninitialised (its __init__ was
# mocked).  Replace the broken mount with a trivial ASGI handler so GET /
# returns a predictable 200 response instead of AttributeError at request time.
from starlette.routing import Mount


async def _test_frontend(scope, receive, send):
    from starlette.responses import HTMLResponse
    await HTMLResponse("<html><body>Test frontend</body></html>")(scope, receive, send)


_app_module.app.router.routes = [
    r for r in _app_module.app.router.routes
    if getattr(r, "name", None) != "static"
]
_app_module.app.mount("/", _test_frontend, name="static")


# ── shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def mock_rag():
    """Fresh MagicMock wired into the live app as rag_system for one test."""
    m = MagicMock()
    _app_module.rag_system = m
    yield m
    _app_module.rag_system = _rag_sentinel


@pytest.fixture
def client(mock_rag):
    """Synchronous TestClient bound to the real FastAPI app with mocked RAG."""
    from fastapi.testclient import TestClient
    with TestClient(_app_module.app) as c:
        yield c


@pytest.fixture
def sample_sources():
    """Reusable source list matching the Source Pydantic schema."""
    return [{"label": "Python Basics - Lesson 1", "url": "https://example.com/l1"}]
