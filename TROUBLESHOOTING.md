# Troubleshooting Common Issues

## Issue 1: Agent Gives Generic Answers Without Exploring Repo

### Symptoms
```json
{
  "total_iterations": 0,
  "total_tool_calls": 0,
  "answer": "Docker can be set up by downloading..." // Generic tutorial
}
```

The agent answers from general knowledge instead of searching your repository.

---

### Why This Happens

**With Ollama models:**
- Model doesn't always follow tool-calling instructions
- Question might be interpreted as asking for general help
- Model takes the "easy path" of answering from training data

**With Claude API:**
- Rare, but can happen with very ambiguous questions

---

### ✅ Solution 1: Be More Explicit in Questions

**❌ Bad Questions (ambiguous):**
```json
"is there any docker setup?"
"how does authentication work?"
"where is the config?"
```

**✅ Good Questions (explicit):**
```json
"Search this repository for Dockerfile or docker-compose.yml and show me what you find"
"Find the authentication code in this repository and explain how it works"
"List all configuration files in this repository"
```

**Key words that help:**
- "Search this repository for..."
- "Find in this codebase..."
- "List all files..."
- "Show me the code for..."

---

### ✅ Solution 2: Use Two-Step Questions

**Step 1 - Force Exploration:**
```json
{
  "question": "List all files in this repository"
}
```

**Step 2 - Ask Your Real Question:**
```json
{
  "question": "Now search for Docker-related files (Dockerfile, docker-compose) and explain the Docker setup"
}
```

---

### ✅ Solution 3: Upgrade System Prompt

I've updated the system prompt to be more explicit. If you're still having issues, update your `agent/core.py` with the improved prompt (see latest version).

---

### ✅ Solution 4: Switch to Claude API

If Ollama consistently fails to use tools:

```bash
# In .env
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-api03-...
```

Claude has native tool-calling and is much more reliable.

---

## Issue 2: Agent Gets Stuck in Loop

### Symptoms
- Agent reaches max iterations (8)
- Keeps calling the same tool repeatedly
- Never produces a final answer

---

### Why This Happens
- Model doesn't know when to stop
- Model keeps finding "interesting" files
- Model doesn't synthesize findings into an answer

---

### ✅ Solution 1: Reduce Max Iterations

```python
# In config/settings.py
AGENT_MAX_ITERATIONS = 5  # Default is 8
```

---

### ✅ Solution 2: Ask Simpler Questions

Break complex questions into smaller ones:

**❌ Too Complex:**
"Explain the entire authentication flow including OAuth, JWT, session management, and all edge cases"

**✅ Simpler:**
"Where is the authentication code in this repository?"

Then follow up:
"How does the JWT validation work in [file you found]?"

---

## Issue 3: Agent Misses Important Files

### Symptoms
- Agent says "not found" but file exists
- Agent reads wrong files
- Agent doesn't find what you're looking for

---

### Why This Happens
- Search query doesn't match file names
- Model picks wrong search terms
- File is in an unexpected location

---

### ✅ Solution: Guide the Search

Be specific about WHERE to look:

```json
{
  "question": "List all files in the ./docker directory, then read any Dockerfile you find"
}
```

Or specify the exact filename:

```json
{
  "question": "Read the file at ./docker/Dockerfile and explain its contents"
}
```

---

## Issue 4: Very Slow Responses (Ollama)

### Symptoms
- Takes 5-10+ minutes per query
- System becomes unresponsive
- High CPU/RAM usage

---

### Why This Happens
- Model is too large for your hardware
- Other apps using resources
- First run (model loading)

---

### ✅ Solution 1: Use Smaller Model

```bash
# Instead of 7B model
ollama pull qwen2.5-coder:3b  # Smaller, faster

# Update .env
OLLAMA_MODEL=qwen2.5-coder:3b
```

---

### ✅ Solution 2: Free Up Resources

```bash
# Close browser tabs, other apps
# Check RAM usage
free -h  # Linux
top      # macOS
```

---

### ✅ Solution 3: Use Claude API

Much faster (10-30 seconds vs 2-5 minutes):

```bash
# In .env
LLM_PROVIDER=anthropic
```

---

## Issue 5: "Connection Refused" Error (Ollama)

### Symptoms
```
Connection refused to localhost:11434
```

---

### ✅ Solution

Start Ollama server:

```bash
ollama serve
```

Keep it running in a separate terminal.

---

## Issue 6: Tool Output Truncated

### Symptoms
- File content cuts off mid-way
- Incomplete search results
- Agent says "file too large"

---

### Why This Happens
- Files larger than 1MB are rejected
- Tool output truncated to 5000 chars for database

---

### ✅ Solution 1: Read Specific Lines

```json
{
  "question": "Read lines 1-100 from main.py"
}
```

**Note:** Current implementation doesn't support line ranges, but agent can read file and mention specific sections.

---

### ✅ Solution 2: Increase Limits

```python
# In config/settings.py
AGENT_MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB instead of 1MB
```

---

## Issue 7: Model Returns Malformed JSON

### Symptoms (Ollama only)
- Tool calls not parsed correctly
- Agent can't execute tools
- JSON parsing errors in logs

---

### Why This Happens
- Open-source models sometimes output invalid JSON
- Model doesn't follow format exactly

---

### ✅ Solution 1: Use Qwen2.5-Coder

Best at following structured output:

```bash
ollama pull qwen2.5-coder:7b
```

---

### ✅ Solution 2: Check Django Admin

View actual tool calls:
```
http://localhost:8000/admin/research_sessions/toolcall/
```

See what the model is trying to do.

---

### ✅ Solution 3: Use Claude API

Native tool-calling, no JSON parsing issues:

```bash
LLM_PROVIDER=anthropic
```

---

## Issue 8: Empty Answers

### Symptoms
```json
{
  "answer": "",
  "status": "completed"
}
```

---

### Why This Happens
- Model returned empty response
- Tool calls failed
- Max iterations reached without answer

---

### ✅ Solution

Check session details:

```bash
curl http://localhost:8000/api/research/{session_id}/
```

Look at:
- `tool_calls` - What did the agent try?
- `error_message` - Any errors?
- `total_iterations` - Did it reach max?

---

## Debugging Workflow

### Step 1: Check Session Details

```bash
curl http://localhost:8000/api/research/{session_id}/ | jq
```

Look for:
- `total_tool_calls`: Should be > 0
- `total_iterations`: Should be > 0
- `tool_calls`: What tools were used
- `error_message`: Any errors

---

### Step 2: Check Django Admin

```
http://localhost:8000/admin/
```

Navigate to:
- Research Sessions - See all sessions
- Tool Calls - See what agent did
- Findings - See what agent discovered

---

### Step 3: Check Ollama Logs

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# See available models
ollama list
```

---

### Step 4: Try Simpler Question

Test with a very simple question:

```json
{
  "repo_url": "https://github.com/psf/requests",
  "question": "List all Python files in this repository"
}
```

If this works, your question might be too complex.

---

## Best Practices to Avoid Issues

### 1. Start Simple
```json
// First request - simple
"List all files in this repository"

// Second request - specific
"Now find and read the main entry point"
```

### 2. Be Explicit
```json
// ❌ Ambiguous
"how does it work?"

// ✅ Explicit
"Search for authentication code in this repository and explain how it works"
```

### 3. Use Good Models
- **Ollama:** Qwen2.5-Coder 7B (best)
- **API:** Claude Sonnet 4 (most reliable)

### 4. Monitor Progress
Check Django admin after each request to see what the agent did.

### 5. Test Incrementally
- Test on small repos first
- Verify tools work with simple questions
- Then try complex queries

---

## Getting Help

### Check Logs
```bash
# Django logs
python manage.py runserver
# Watch output for errors

# Ollama logs
ollama serve
# Watch output
```

### Test Components Separately

**Test Ollama:**
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5-coder:7b",
  "prompt": "Say hello"
}'
```

**Test Django:**
```bash
python test_agent.py
```

**Test Repository Cloning:**
```bash
python manage.py shell
>>> from agent.repo_loader import get_repo_loader
>>> loader = get_repo_loader()
>>> path = loader.get_or_clone("https://github.com/psf/requests")
>>> print(path)
```

---

## When to Switch to Claude API

Consider switching if:
- ✅ Ollama consistently fails to use tools
- ✅ Responses take > 5 minutes
- ✅ You need production-quality answers
- ✅ Budget allows (~$0.02-0.05 per session)

```bash
# In .env
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-api03-...
```

---

## Still Having Issues?

1. Check `ARCHITECTURE.md` for system design
2. Review `OLLAMA_SETUP.md` for Ollama-specific help
3. Check session details via API
4. Look at tool_calls in Django admin
5. Try with Claude API to isolate if it's an Ollama issue

---

**Most Common Fix:** Make your questions more explicit about searching the repository! 🎯
