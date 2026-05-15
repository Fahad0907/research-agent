# Architecture Documentation

## System Overview

The Codebase Research Agent is a Django-based application that uses LLM tool-calling to intelligently explore and answer questions about code repositories.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client/User                           │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/JSON
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Django REST API                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  research/start/  │  research/{id}/  │  repositories/ │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Service Layer                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           ResearchService                             │  │
│  │  - start_research()                                   │  │
│  │  - get_session_details()                              │  │
│  │  - list_repository_sessions()                         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────┬──────────────────────────────────────┬───────────────┘
      │                                       │
      │                                       │
┌─────▼──────────────────┐          ┌───────▼────────────────┐
│   Agent Core           │          │   Repository Loader    │
│                        │          │                        │
│  CodebaseResearchAgent │          │  - Clone repos         │
│  - research()          │          │  - List files          │
│  - _reasoning_loop()   │◄─────────┤  - Read files          │
│  - Tool execution      │          │  - Search code         │
└─────┬──────────────────┘          └────────────────────────┘
      │
      │
┌─────▼──────────────────────────────────────────────────────┐
│                    LLM Client                               │
│  - chat_completion()                                        │
│  - Tool calling                                             │
│  - Token tracking                                           │
└─────┬──────────────────────────────────────────────────────┘
      │
      │ API Calls
      │
┌─────▼──────────────────────────────────────────────────────┐
│              Anthropic Claude API                           │
│              (claude-sonnet-4-20250514)                     │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. API Layer (Django REST Framework)

**Location**: `research_sessions/views.py`

**Responsibilities**:
- Request validation
- Response serialization
- HTTP error handling
- Thin controllers (delegate to service layer)

**Endpoints**:
```python
POST   /api/research/start/              # Start new research
GET    /api/research/{session_id}/       # Get session details
GET    /api/repositories/sessions/       # List repo sessions
```

### 2. Service Layer

**Location**: `research_sessions/services.py`

**Responsibilities**:
- Business logic orchestration
- Transaction management
- Repository and session lifecycle
- Error handling and recovery

**Key Methods**:
```python
start_research(repo_url, question)
  → Clones repo
  → Creates session
  → Runs agent
  → Returns results

get_session_details(session_id)
  → Fetches session with related data
  → Serializes tool calls and findings

list_repository_sessions(repo_url)
  → Lists all sessions for a repository
```

### 3. Agent Core

**Location**: `agent/core.py`

**Responsibilities**:
- Multi-step reasoning loop
- Tool selection and execution
- Stop condition enforcement
- Conversation history management

**Reasoning Loop Flow**:
```
┌─────────────────────────────────────────────────────────────┐
│                   Agent Reasoning Loop                       │
└─────────────────────────────────────────────────────────────┘

    ┌───────────────────────────────────────────────┐
    │ 1. Send conversation + tools to LLM           │
    └───────────────┬───────────────────────────────┘
                    │
    ┌───────────────▼───────────────────────────────┐
    │ 2. LLM returns tool_calls or final_answer     │
    └───────────────┬───────────────────────────────┘
                    │
            ┌───────┴────────┐
            │                │
   ┌────────▼─────┐   ┌─────▼──────────┐
   │  Tool Calls  │   │  Final Answer  │
   │   Present    │   │    Present     │
   └────────┬─────┘   └─────┬──────────┘
            │               │
   ┌────────▼─────┐         │
   │ 3. Execute   │         │
   │    Tools     │         │
   └────────┬─────┘         │
            │               │
   ┌────────▼─────┐         │
   │ 4. Add Tool  │         │
   │   Results to │         │
   │ Conversation │         │
   └────────┬─────┘         │
            │               │
   ┌────────▼─────┐         │
   │ 5. Check     │         │
   │    Stop      │         │
   │  Conditions  │         │
   └────────┬─────┘         │
            │               │
            └───────┐       │
                    │       │
    ┌───────────────▼───────▼───────────────────────┐
    │ Continue?  NO → Return Answer                 │
    │           YES → Loop to Step 1                │
    └───────────────────────────────────────────────┘
```

**Stop Conditions**:
1. Max iterations reached (8 by default)
2. LLM returns text response (no tool calls)
3. Repeated tool calls detected (safety)
4. Empty response after retry

### 4. Tool System

**Location**: `agent/tools.py`

**Available Tools**:

| Tool | Purpose | Inputs | Output |
|------|---------|--------|--------|
| `list_files` | List directory contents | path, max_depth | File list |
| `read_file` | Read file contents | file_path | File with line numbers |
| `search_code` | Search for patterns | query, extensions | Matches with locations |
| `get_directory_structure` | Tree view | max_depth | ASCII tree |
| `save_finding` | Save insight | file_path, note, lines | Confirmation |
| `get_previous_findings` | Retrieve past research | limit | Previous sessions |

**Tool Execution Flow**:
```python
1. LLM decides: "I need to read fastapi/dependencies.py"
2. Agent calls: tools.execute_tool("read_file", {"file_path": "..."})
3. Tool executes:
   - Reads file from disk
   - Adds line numbers
   - Truncates if too large
   - Logs to database (ToolCall model)
4. Returns formatted content
5. Agent adds to conversation
```

### 5. Repository Loader

**Location**: `agent/repo_loader.py`

**Responsibilities**:
- Git clone operations
- Repository caching
- Safe file reading (path traversal prevention)
- Code search operations

**Caching Strategy**:
```python
repo_hash = md5(repo_url)[:16]
local_path = /tmp/codebase_repos/{repo_hash}/

if exists(local_path):
    git pull  # Update existing
else:
    git clone --depth=1  # Shallow clone
```

### 6. LLM Client

**Location**: `agent/llm_client.py`

**Responsibilities**:
- API request/response handling
- Tool-calling format conversion
- Token counting
- Retry logic

**Tool Calling Format** (Anthropic):
```json
{
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 4096,
  "messages": [...],
  "tools": [
    {
      "name": "read_file",
      "description": "Read a file...",
      "input_schema": {
        "type": "object",
        "properties": {...}
      }
    }
  ]
}
```

## Database Schema

### Entity Relationship Diagram

```
┌──────────────────┐
│   Repository     │
│──────────────────│
│ id (PK)          │
│ url (unique)     │──┐
│ name             │  │
│ local_path       │  │
│ total_sessions   │  │
│ last_analyzed    │  │
└──────────────────┘  │
                      │ 1
                      │
                      │ N
          ┌───────────┴──────────────┐
          │   ResearchSession        │
          │──────────────────────────│
          │ id (PK)                  │
          │ repository_id (FK)       │──┐
          │ question                 │  │
          │ final_answer             │  │
          │ status                   │  │
          │ total_iterations         │  │
          │ total_tool_calls         │  │
          │ token_usage              │  │
          └──────────────────────────┘  │
                   │                     │
         ┌─────────┴─────────┐           │ 1
         │ 1                 │ 1         │
         │ N                 │ N         │
         │                   │           │
┌────────▼────────┐  ┌───────▼─────────┐│
│    ToolCall     │  │    Finding      ││
│─────────────────│  │─────────────────││
│ id (PK)         │  │ id (PK)         ││
│ session_id (FK) │  │ session_id (FK) ││
│ tool_name       │  │ file_path       ││
│ tool_input      │  │ line_start      ││
│ tool_output     │  │ line_end        ││
│ iteration       │  │ note            ││
│ execution_ms    │  │ relevance_score ││
└─────────────────┘  └─────────────────┘
```

### Key Indexes

**Performance Optimizations**:
```sql
-- Fast repository lookup
INDEX ON repositories(url)

-- Session queries by status
INDEX ON research_sessions(status)

-- Sessions by repository and date
INDEX ON research_sessions(repository_id, created_at DESC)

-- Tool calls by session
INDEX ON tool_calls(session_id, created_at)

-- Findings by relevance
INDEX ON findings(session_id, relevance_score DESC)
```

## Data Flow Example

### Complete Research Session Flow

```
User Request
    ↓
POST /api/research/start/ 
{
  "repo_url": "https://github.com/user/repo",
  "question": "How does X work?"
}
    ↓
┌─────────────────────────────────────────┐
│ ResearchService.start_research()        │
├─────────────────────────────────────────┤
│ 1. Get/Create Repository model          │
│ 2. Clone repo → /tmp/repos/hash/        │
│ 3. Create ResearchSession (pending)     │
│ 4. Initialize Agent                     │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ CodebaseResearchAgent.research()        │
├─────────────────────────────────────────┤
│ Session status → processing             │
│ Iteration 0:                            │
│   → LLM call with tools                 │
│   → Returns: search_code("X")           │
│   → Execute tool                        │
│   → Log ToolCall to DB                  │
│   → Add result to conversation          │
│                                         │
│ Iteration 1:                            │
│   → LLM call with updated context       │
│   → Returns: read_file("module/x.py")   │
│   → Execute tool                        │
│   → Log ToolCall to DB                  │
│   → Add result to conversation          │
│                                         │
│ Iteration 2:                            │
│   → LLM call                            │
│   → Returns: save_finding(...)          │
│   → Execute tool                        │
│   → Save Finding to DB                  │
│   → Add result to conversation          │
│                                         │
│ Iteration 3:                            │
│   → LLM call                            │
│   → Returns: final answer (text)        │
│   → No tool calls → STOP                │
└─────────────────┬───────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ Save Results                            │
├─────────────────────────────────────────┤
│ - Update session.final_answer           │
│ - Update session.status = completed     │
│ - Update session.completed_at           │
│ - Return formatted response             │
└─────────────────┬───────────────────────┘
                  ↓
Response to User
{
  "session_id": 1,
  "status": "completed",
  "answer": "X works by...",
  "metadata": {
    "total_iterations": 4,
    "total_tool_calls": 7,
    "token_usage": 5234
  }
}
```

## Safety & Performance

### Safety Mechanisms

1. **Path Traversal Prevention**
```python
# In repo_loader.py
full_path = os.path.normpath(os.path.join(local_path, file_path))
if not full_path.startswith(local_path):
    raise ValueError("Invalid file path")
```

2. **File Size Limits**
```python
if file_size > AGENT_MAX_FILE_SIZE:  # 1MB
    raise ValueError("File too large")
```

3. **Iteration Limits**
```python
for iteration in range(AGENT_MAX_ITERATIONS):  # Max 8
    ...
```

4. **Repeated Tool Detection**
```python
if self._is_repeating_tools(tool_calls):
    return self._force_final_answer()
```

### Performance Optimizations

1. **Repository Caching**
   - Clone once, reuse for multiple sessions
   - `git pull` to update existing clones

2. **Tool Output Truncation**
```python
ToolCall.objects.create(
    tool_output=output[:5000]  # Truncate long outputs
)
```

3. **Selective File Reading**
   - Agent chooses which files to read
   - Never reads entire repository

4. **Database Query Optimization**
```python
# Use select_related and prefetch_related
session = ResearchSession.objects.select_related('repository').get(id=session_id)
tool_calls = session.tool_calls.all()  # Single query
```

## Extension Points

### Adding New Tools

1. Define tool in `agent/tools.py`:
```python
def get_tool_definitions(self):
    return [
        # ... existing tools ...
        {
            "name": "analyze_dependencies",
            "description": "Analyze package dependencies",
            "input_schema": {...}
        }
    ]

def execute_tool(self, tool_name, tool_input):
    if tool_name == "analyze_dependencies":
        return self._analyze_dependencies(**tool_input)
```

### Adding New LLM Provider

Modify `agent/llm_client.py`:
```python
class OpenAIClient(LLMClient):
    def chat_completion(self, messages, tools=None, system=None):
        # OpenAI-specific implementation
        ...
```

### Adding RAG/Vector Search

Create new tool:
```python
def _semantic_search(self, query: str) -> str:
    # Embed query
    query_embedding = embed_text(query)
    
    # Search vector DB
    results = vector_db.search(query_embedding)
    
    return format_results(results)
```

## Security Considerations

### Current Mitigations

- ✅ Path traversal prevention
- ✅ File size limits
- ✅ No code execution from repos
- ✅ Input validation (URL, file paths)
- ✅ Ignored dangerous directories

### Production TODOs

- [ ] API authentication (JWT/OAuth)
- [ ] Rate limiting per user
- [ ] Request logging and monitoring
- [ ] CORS configuration
- [ ] Secret rotation
- [ ] SQL injection prevention (using ORM)

## Monitoring & Debugging

### Key Metrics to Track

1. **Session Success Rate**
```python
completed = ResearchSession.objects.filter(status='completed').count()
total = ResearchSession.objects.count()
success_rate = completed / total
```

2. **Average Tool Calls per Session**
```python
avg_tools = ResearchSession.objects.aggregate(
    avg=Avg('total_tool_calls')
)
```

3. **Token Usage**
```python
total_tokens = ResearchSession.objects.aggregate(
    total=Sum('token_usage')
)
```

### Debugging Failed Sessions

```python
# Get failed session
session = ResearchSession.objects.get(id=X, status='failed')

# Check error message
print(session.error_message)

# Review tool calls
for tc in session.tool_calls.all():
    print(f"{tc.tool_name}: {tc.tool_output[:100]}")
```

---

## Conclusion

This architecture provides:
- ✅ Clean separation of concerns
- ✅ Extensible tool system
- ✅ Persistent research history
- ✅ Safety mechanisms
- ✅ Production-ready foundation

The agent can be extended with additional tools, LLM providers, and features without major refactoring.
