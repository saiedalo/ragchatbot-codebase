# Development Setup Guide

Complete instructions for setting up the Enterprise RAG System for development and deployment.

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Local Development Setup](#local-development-setup)
3. [Environment Configuration](#environment-configuration)
4. [Running the Application](#running-the-application)
5. [Testing & Code Quality](#testing--code-quality)
6. [Production Deployment](#production-deployment)
7. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements
- **Python**: 3.13 or higher
- **RAM**: 2GB (4GB recommended)
- **Disk**: 2GB for dependencies + document storage
- **Internet**: Required for Anthropic API

### Supported Operating Systems
- macOS (Intel & Apple Silicon)
- Linux (Ubuntu 20.04+, Debian 11+)
- Windows 10+ (via WSL2 or native)

### Optional
- Docker/Docker Compose (for containerized deployment)
- Git (for version control)
- IDE: VS Code, PyCharm, or similar

---

## Local Development Setup

### Step 1: Install Python 3.13

**macOS (using Homebrew):**
```bash
brew install python@3.13
python3.13 --version
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install python3.13 python3.13-venv python3.13-dev
python3.13 --version
```

**Windows:**
- Download from [python.org](https://www.python.org/downloads/)
- Or use: `winget install Python.Python.3.13`

**Verify installation:**
```bash
python3 --version  # Should be 3.13.x
```

### Step 2: Install `uv` Package Manager

`uv` is a fast, reliable Python package manager. Installation is simple:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy BypassUser -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify
uv --version
```

For detailed instructions, see [uv installation guide](https://docs.astral.sh/uv/).

### Step 3: Clone the Repository

```bash
git clone https://github.com/yourusername/enterprise-rag-system.git
cd enterprise-rag-system
```

### Step 4: Install Dependencies

```bash
# Install all dependencies including dev tools
uv sync --group dev

# Or for production only (without dev dependencies)
uv sync
```

**What gets installed:**
- FastAPI & Uvicorn (web framework)
- ChromaDB (vector database)
- Anthropic SDK (Claude API)
- SentenceTransformers (embeddings)
- pytest & testing tools
- Black, isort, flake8, mypy (code quality)

### Step 5: Verify Installation

```bash
# Check Python
python --version

# Check uv
uv --version

# Check key packages
uv run python -c "import fastapi; print(fastapi.__version__)"
uv run python -c "import chromadb; print(chromadb.__version__)"
uv run python -c "import anthropic; print(anthropic.__version__)"
```

---

## Environment Configuration

### Step 1: Create Environment File

```bash
# Copy the example
cp .env.example .env

# Edit with your editor
# (macOS/Linux)
nano .env
# (Windows)
notepad .env
```

### Step 2: Configure Variables

**Minimum Required:**
```env
ANTHROPIC_API_KEY=your_actual_api_key_here
```

**Optional - Fine-tuning:**
```env
# Model (default: claude-sonnet-4-20250514)
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# Embedding model (default: all-MiniLM-L6-v2)
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Document processing
CHUNK_SIZE=800              # Characters per chunk
CHUNK_OVERLAP=100           # Character overlap
MAX_RESULTS=5               # Search results per query

# Session management
MAX_HISTORY=2               # Message pairs in memory
SESSION_TIMEOUT=3600        # Session lifetime (seconds)

# Database
CHROMA_PATH=./backend/chroma_db

# Development
DEBUG=true
```

### Step 3: Get Your API Key

1. Go to [Anthropic Console](https://console.anthropic.com)
2. Sign up or log in
3. Navigate to "API Keys"
4. Create a new API key
5. Copy and paste into `.env`

**Security Note**: Never commit `.env` to version control. It's already in `.gitignore`.

---

## Running the Application

### Quick Start (Recommended)

```bash
chmod +x run.sh
./run.sh
```

The application will start and be available at:
- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Manual Start

```bash
# Terminal 1: Start the backend
cd backend
uv run uvicorn app:app --reload --port 8000

# Terminal 2 (optional): Monitor logs
tail -f backend.log
```

### With Custom Port

```bash
cd backend
uv run uvicorn app:app --reload --port 8080
# Access at http://localhost:8080
```

### Production Mode (No Auto-Reload)

```bash
cd backend
uv run uvicorn app:app --port 8000 --workers 4
```

### Using Docker

```bash
# Build image
docker build -t rag-system .

# Run container
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY=your_key \
  rag-system
```

---

## Testing & Code Quality

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with output
uv run pytest -v

# Run specific test file
uv run pytest backend/tests/test_rag_system.py

# Run specific test
uv run pytest backend/tests/test_rag_system.py::test_query_basic -v

# Run with coverage report
uv run pytest --cov=backend --cov-report=html
# View report: open htmlcov/index.html
```

### Code Quality Checks

```bash
# Format code (auto-fix issues)
./scripts/format.sh

# Lint code (find issues)
./scripts/lint.sh

# Type checking
uv run mypy backend

# All checks together
./scripts/format.sh && ./scripts/lint.sh
```

### Pre-Commit Hook (Optional)

```bash
# Create pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
./scripts/format.sh || exit 1
./scripts/lint.sh || exit 1
uv run pytest || exit 1
EOF

chmod +x .git/hooks/pre-commit
```

---

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/my-feature
```

### 2. Make Changes

Edit files as needed. Example adding a new tool:

```python
# backend/search_tools.py
class CustomTool(Tool):
    """My custom tool"""
    def execute(self, **kwargs) -> str:
        return "result"
```

### 3. Test Your Changes

```bash
# Run relevant tests
uv run pytest backend/tests/test_search_tools.py -v

# Check code quality
./scripts/lint.sh
```

### 4. Commit Changes

```bash
git add .
git commit -m "Add custom search tool"
```

### 5. Push and Create PR

```bash
git push origin feature/my-feature
# Then create PR on GitHub
```

---

## Production Deployment

### Prerequisites
- Server with Python 3.13+
- Anthropic API key
- Domain name & SSL certificate
- Reverse proxy (nginx, Apache) for HTTPS

### Deployment Checklist

- [ ] Set `DEBUG=false` in production .env
- [ ] Configure proper CORS origins
- [ ] Implement authentication/rate limiting
- [ ] Set up persistent session storage (Redis/PostgreSQL)
- [ ] Configure document backup/versioning
- [ ] Set up monitoring & alerting
- [ ] Test with production documents

### Basic Deployment Example

```bash
# 1. Clone repository
git clone https://github.com/yourusername/enterprise-rag-system.git
cd enterprise-rag-system

# 2. Install dependencies
uv sync

# 3. Configure environment
cp .env.example .env
# Edit .env with production values

# 4. Run with production settings
cd backend
uv run uvicorn app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info
```

### With Nginx Reverse Proxy

```nginx
upstream rag_app {
    server 127.0.0.1:8000;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://rag_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Docker Production Deployment

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy application
COPY . /app

# Install Python dependencies
RUN /root/.local/bin/uv sync

# Expose port
EXPOSE 8000

# Run application
CMD ["/root/.local/bin/uv", "run", "uvicorn", \
     "backend.app:app", "--host", "0.0.0.0", \
     "--port", "8000", "--workers", "4"]
```

---

## Troubleshooting

### Issue: "command not found: python3.13"

**Solution:**
```bash
# Check installed version
python3 --version

# Use available version
python3 --version  # If 3.13+, use this
```

### Issue: "ModuleNotFoundError: No module named 'anthropic'"

**Solution:**
```bash
# Reinstall dependencies
uv sync

# Or verify installation
uv run python -c "import anthropic"
```

### Issue: "Failed to get embedding"

**Solution:**
```bash
# Check internet connection
ping huggingface.co

# First run downloads model (may take a minute)
# Check ~/.cache/huggingface/ for models
```

### Issue: "ANTHROPIC_API_KEY not set"

**Solution:**
1. Check `.env` file exists
2. Verify key format (should start with `sk-`)
3. Test key: `curl https://api.anthropic.com/v1/models -H "X-API-Key: $ANTHROPIC_API_KEY"`

### Issue: "Port 8000 already in use"

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000
# or (Windows)
netstat -ano | findstr :8000

# Kill process
kill -9 <PID>

# Or use different port
cd backend
uv run uvicorn app:app --port 8080
```

### Issue: "ChromaDB persistent data not found"

**Solution:**
```bash
# Check data location
ls -la backend/chroma_db/

# If missing, documents will be re-indexed on startup
# This is normal - just takes a moment

# To reset:
rm -rf backend/chroma_db/
```

### Issue: "Tests failing locally but not in CI"

**Solution:**
```bash
# Run tests with same environment
uv sync --group dev
uv run pytest --verbose

# Check Python version matches
python --version
```

---

## Performance Tuning

### For Large Document Collections

```env
# Increase chunk size for faster search
CHUNK_SIZE=1200

# Reduce overlap if memory-constrained
CHUNK_OVERLAP=50

# Reduce history for faster generation
MAX_HISTORY=1
```

### For Low-Latency Responses

```env
# Smaller chunks = faster search
CHUNK_SIZE=500

# Limit search results
MAX_RESULTS=3

# Reduce tool iterations
MAX_TOOL_ITERATIONS=1
```

### System-Level Optimization

- Add more workers: `--workers 8` (for 8-core CPU)
- Use async database connection pooling
- Implement caching for frequent queries
- Monitor with `top`, `htop`, or cloud provider tools

---

## Logging & Debugging

### Enable Debug Logging

```env
DEBUG=true
LOG_LEVEL=debug
```

### View Logs

```bash
# While running with run.sh
tail -f backend.log

# Or check server output directly
# (if running via uvicorn)
```

### Debug a Query

```python
# In backend/app.py or test file
import logging
logging.basicConfig(level=logging.DEBUG)

# Now detailed logs will show
```

---

## Resources

- **Anthropic Docs**: https://docs.anthropic.com
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **ChromaDB Docs**: https://docs.trychroma.com
- **uv Docs**: https://docs.astral.sh/uv

---

**Last Updated**: 2026-06-02  
**Version**: 1.0.0
