# API Documentation

Complete reference for the Enterprise RAG System REST API endpoints.

## Base URL

```
http://localhost:8000
```

For production deployments, replace `localhost:8000` with your deployed domain.

## Authentication

Currently, no authentication is required. For production deployment, consider implementing:
- OAuth2 with JWT tokens
- API key authentication
- Rate limiting per client

## Endpoints

### Query Endpoint

**POST** `/api/query`

Submit a query to the RAG system and receive an AI-generated response with sources.

#### Request

```json
{
  "query": "What are the main IT security requirements?",
  "session_id": "optional_session_id_for_context"
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | The question or query to answer |
| `session_id` | string | No | Session ID for conversation context. If omitted, creates new session. |

**Example:**
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main IT security requirements for financial institutions?",
    "session_id": "sess_12345"
  }'
```

#### Response

**200 OK**
```json
{
  "answer": "Financial institutions must implement comprehensive IT security measures including... [full answer]",
  "sources": [
    "BAIT Section 4.3 - Data Protection",
    "BAFIN Guidelines 3.2 - Encryption",
    "Bundesbank Regulations 4.1 - Access Control"
  ],
  "source_links": [
    "bafin_bait.pdf#section_4.3",
    "bafin_guidelines.pdf#section_3.2",
    "bundesbank_regs.pdf#section_4.1"
  ],
  "session_id": "sess_12345"
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | AI-generated answer to the query |
| `sources` | array[string] | List of source document sections cited |
| `source_links` | array[string] | Document links with optional anchors |
| `session_id` | string | Session ID for use in follow-up queries |

**Error Responses:**

**400 Bad Request**
```json
{
  "detail": "Query cannot be empty"
}
```

**500 Internal Server Error**
```json
{
  "detail": "Error processing query: [error description]"
}
```

---

### Document Statistics Endpoint

**GET** `/api/dokumente`

Retrieve statistics about indexed documents and their contents.

#### Request

No parameters required.

**Example:**
```bash
curl http://localhost:8000/api/dokumente
```

#### Response

**200 OK**
```json
{
  "gesamt_dokumente": 4,
  "dokument_titel": [
    "BaFin BAIT",
    "Bundesbank Finanzdienstleistungen",
    "BaFin GWG Hinweise",
    "BaFin MaRisk"
  ],
  "dokumente": [
    {
      "title": "BaFin BAIT",
      "instructor": "German Financial Authority",
      "course_link": "https://www.bafin.de/...",
      "lesson_count": 12,
      "lessons": [
        {
          "lesson_number": 1,
          "lesson_title": "Introduction",
          "lesson_link": "bafin_bait.pdf#page=1"
        },
        {
          "lesson_number": 2,
          "lesson_title": "IT Security Principles",
          "lesson_link": "bafin_bait.pdf#page=5"
        }
      ]
    }
  ]
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `gesamt_dokumente` | integer | Total number of indexed documents |
| `dokument_titel` | array[string] | List of document titles |
| `dokumente` | array[object] | Detailed document information |
| `dokumente[].title` | string | Document title |
| `dokumente[].instructor` | string | Document source/author |
| `dokumente[].course_link` | string | Link to original document |
| `dokumente[].lesson_count` | integer | Number of sections/lessons |
| `dokumente[].lessons` | array[object] | Section information |

---

### Clear Session Endpoint

**POST** `/api/clear-session`

Clear conversation history for a specific session, effectively ending that conversation.

#### Request

```json
{
  "session_id": "sess_12345"
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | string | Yes | The session ID to clear |

**Example:**
```bash
curl -X POST http://localhost:8000/api/clear-session \
  -H "Content-Type: application/json" \
  -d '{"session_id": "sess_12345"}'
```

#### Response

**200 OK**
```json
{
  "status": "success",
  "message": "Session cleared successfully"
}
```

**Error Responses:**

**404 Not Found**
```json
{
  "detail": "Session not found"
}
```

---

## Usage Patterns

### Single Query

For a one-off question:
```bash
curl -X POST http://localhost:8000/api/query \
  -d '{"query": "Your question here"}'
```

### Multi-Turn Conversation

1. First query (creates session):
```bash
curl -X POST http://localhost:8000/api/query \
  -d '{"query": "Initial question"}' > response1.json

# Extract session_id from response
SESSION_ID=$(jq -r '.session_id' response1.json)
```

2. Follow-up query (maintains context):
```bash
curl -X POST http://localhost:8000/api/query \
  -d "{\"query\": \"Follow-up question\", \"session_id\": \"$SESSION_ID\"}"
```

3. Continue as needed:
```bash
curl -X POST http://localhost:8000/api/query \
  -d "{\"query\": \"Another follow-up\", \"session_id\": \"$SESSION_ID\"}"
```

4. Clear when done:
```bash
curl -X POST http://localhost:8000/api/clear-session \
  -d "{\"session_id\": \"$SESSION_ID\"}"
```

### Batch Processing

Query multiple questions in a loop:
```bash
#!/bin/bash
QUERIES=(
  "What is BAIT?"
  "What about encryption requirements?"
  "How should we implement access controls?"
)

for query in "${QUERIES[@]}"; do
  curl -X POST http://localhost:8000/api/query \
    -d "{\"query\": \"$query\"}"
  echo "---"
done
```

---

## HTTP Status Codes

| Code | Meaning | When It Occurs |
|------|---------|---|
| 200 | OK | Request successful, response in body |
| 400 | Bad Request | Invalid parameters or empty query |
| 404 | Not Found | Session ID not found (clear-session only) |
| 500 | Server Error | Internal processing error |
| 502 | Bad Gateway | API connectivity issue |
| 503 | Service Unavailable | Server overloaded or maintenance |

---

## Rate Limiting

Currently, no rate limiting is enforced. For production use, consider:
- 100 requests/minute per IP
- 10 requests/second per session
- Implement via middleware or reverse proxy

---

## Latency & Performance

**Typical Response Times:**
- Simple query: 150-200ms
- Complex query (multi-round search): 250-350ms
- Session retrieval overhead: <50ms
- Network round-trip included

**Factors affecting latency:**
- Query complexity
- Document corpus size
- Claude API response time
- Network conditions

---

## Pagination & Large Results

Currently, no pagination is supported. API returns:
- Max 5 sources per query (configurable in `config.py`)
- Entire response in single request

For large datasets, implement:
- Result pagination
- Streaming responses
- Async processing

---

## CORS (Cross-Origin Resource Sharing)

**Development**: CORS enabled for all origins
```
Access-Control-Allow-Origin: *
```

**Production**: Configure specific allowed origins
```
Access-Control-Allow-Origin: https://yourdomain.com
```

---

## Webhooks & Real-Time Updates

Not currently supported. Future enhancements:
- WebSocket support for real-time responses
- Webhook notifications for long-running queries
- Server-sent events (SSE) for streaming

---

## API Client Examples

### Python
```python
import requests
import json

BASE_URL = "http://localhost:8000"

def query(question, session_id=None):
    response = requests.post(
        f"{BASE_URL}/api/query",
        json={"query": question, "session_id": session_id}
    )
    return response.json()

# Usage
result = query("What are IT security requirements?")
print(result["answer"])
print(result["session_id"])
```

### JavaScript / Fetch
```javascript
async function query(question, sessionId = null) {
  const response = await fetch("http://localhost:8000/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ 
      query: question, 
      session_id: sessionId 
    })
  });
  return await response.json();
}

// Usage
const result = await query("What are IT security requirements?");
console.log(result.answer);
```

### Curl
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query":"What are IT security requirements?"}'
```

---

## Interactive API Documentation

FastAPI provides interactive Swagger UI:
- **URL**: http://localhost:8000/docs
- **Features**: 
  - Try out endpoints directly
  - See request/response schemas
  - Auto-generated documentation

Alternative ReDoc documentation:
- **URL**: http://localhost:8000/redoc

---

## Troubleshooting

### "Query cannot be empty"
- Ensure query field is not empty
- Check JSON formatting

### "Session not found"
- Session may have expired (default: 1 hour)
- Create new query to start new session

### Slow responses
- Check Claude API status
- Verify network connectivity
- Monitor server CPU/memory

### Null/empty results
- Query may not match any documents
- Try broader search terms
- Check document index size with `/api/dokumente`

---

## Migration & Versioning

Currently v1.0.0. Breaking changes will increment major version.

Planned enhancements:
- v1.1: Pagination support
- v1.2: Advanced filtering
- v2.0: WebSocket support

---

**Last Updated**: 2026-06-02  
**API Version**: 1.0.0
