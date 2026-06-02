# Example 2: Conversation Flow - Multi-Turn Context Management

## What This Demonstrates

This example shows how the system **maintains context across multiple turns**, enabling exploratory research and follow-up questions without losing previous context.

## The Conversation

### Turn 1: Initial Query
```
"What are the key requirements for data backup and recovery?"
```

### Turn 2: Follow-Up Question
```
"How frequently should these backups be tested?"
```
(Note: Uses same `session_id` to maintain context)

### Turn 3: Deeper Dive
```
"What about recovery time objectives?"
```

## Why This Matters

**Regulatory Research is Exploratory**
- Initial question opens broad topic
- Follow-ups narrow scope to specifics
- Each answer may raise new questions
- Researchers need context from previous turns

**Cost & Time Efficiency**
- No need to re-explain context
- Claude sees conversation history
- More focused, shorter responses
- Faster research workflow

## How Session Memory Works

```
┌─────────────────────────────────────────────┐
│        SessionManager (In-Memory)            │
│                                              │
│  session_id: "sess_conversation_demo_001"   │
│  created_at: 2026-06-02T10:00:00Z          │
│  history: [                                  │
│    {role: "user", content: "Turn 1..."},    │
│    {role: "assistant", content: "Ans 1..."} │
│    {role: "user", content: "Turn 2..."},    │
│    {role: "assistant", content: "Ans 2..."} │
│  ]                                           │
│  max_history: 2 pairs (configurable)        │
└─────────────────────────────────────────────┘

Query Processing:
1. API receives Turn 3 + session_id
2. SessionManager retrieves history (last 2 exchanges)
3. Claude sees all context from previous turns
4. Generates answer aware of prior discussion
5. New turn added to history for next query
```

## Expected Behavior by Turn

### Turn 1 Answer
- **Length**: Full answer to broad question
- **Focus**: Overview of backup requirements
- **Sources**: Multiple regulation sections

### Turn 2 Answer
- **Length**: Shorter, focused answer
- **Context**: References backup requirements from Turn 1
- **Assumption**: Assumes knowledge from Turn 1

### Turn 3 Answer
- **Refinement**: Very specific to RTO topic
- **Integration**: Builds on backup & test frequency context
- **Depth**: Technical implementation details

## Real-World Use Case

**Scenario**: Compliance audit preparation

**Research Flow**:
1. Auditor: "What must we document for compliance?"
   - Gets overview of documentation requirements
2. Auditor: "How should we organize this documentation?"
   - System knows auditor is focused on documentation
   - Gives targeted answer about structure
3. Auditor: "What retention period applies?"
   - System connects to documentation context
   - Provides specific retention rules

**Without Context Memory**: Each question needs full re-explanation
**With Context Memory**: Natural research conversation

## Configuration Notes

```python
# From backend/config.py
MAX_HISTORY = 2  # Number of (user, assistant) pairs stored
SESSION_TIMEOUT = 3600  # Session lifetime in seconds

# Adjust for your use case:
# - Small value (1 pair): Faster responses, less context
# - Large value (5+ pairs): More context, slower responses
```

## Testing This Example

```bash
# Turn 1: Create new session
curl -X POST http://localhost:8000/api/query \
  -d '{"query":"What are the key requirements for data backup and recovery?"}'

# Copy the session_id from response, then:

# Turn 2: Same session
curl -X POST http://localhost:8000/api/query \
  -d '{
    "query":"How frequently should these backups be tested?",
    "session_id":"sess_conversation_demo_001"
  }'

# Turn 3: Continue conversation
curl -X POST http://localhost:8000/api/query \
  -d '{
    "query":"What about recovery time objectives?",
    "session_id":"sess_conversation_demo_001"
  }'

# Clear session when done
curl -X POST http://localhost:8000/api/clear-session \
  -d '{"session_id":"sess_conversation_demo_001"}'
```

## Architecture Notes

### Session Storage
- **Current**: In-memory only (Python dict)
- **Limitation**: Lost on server restart
- **Production**: Implement with Redis or PostgreSQL

### Memory Efficiency
- Only stores last N message pairs
- Reduces token usage for Claude API
- Balances context vs. response cost

### Scalability
For multiple users:
```
Load Balancer
    ├─ Instance 1: sessions for users 1-10
    ├─ Instance 2: sessions for users 11-20
    └─ Shared Redis: Central session store
```

---

**Performance**: ~100-150ms (shorter responses than Turn 1)  
**Memory Per Session**: ~1KB average
