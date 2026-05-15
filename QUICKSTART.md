# 🚀 QUICK START - Ollama Setup (5 Minutes)

This is a **working, tested** version optimized for Ollama.

---

## ✅ What's Fixed in This Version

1. **Stronger System Prompt** - Forces the agent to use tools
2. **Better Tool Formatting** - Crystal clear instructions for Ollama
3. **Improved Error Handling** - Better fallbacks
4. **Optimized for Qwen2.5-Coder** - Best open-source model for code

---

## 📋 Prerequisites

- **Python 3.10+**
- **8GB RAM minimum** (16GB recommended)
- **5GB free disk space** (for model download)

---

## 🔧 Step-by-Step Setup

### Step 1: Install Ollama (2 minutes)

**macOS:**
```bash
brew install ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download from: https://ollama.com/download

---

### Step 2: Start Ollama Server

Open a **new terminal window** and run:
```bash
ollama serve
```

**Keep this running!** Don't close this terminal.

---

### Step 3: Download the Model (5-10 min download)

Open **another terminal** and run:
```bash
# Download the recommended model
ollama pull qwen2.5-coder:7b
```

**Download size:** ~4.7GB (one-time)

**Verify it downloaded:**
```bash
ollama list
```

You should see: `qwen2.5-coder:7b`

---

### Step 4: Setup the Project (2 minutes)

```bash
# Navigate to project
cd codebase-research-agent

# Install Python dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Initialize database
python manage.py migrate
```

---

### Step 5: Test the Setup

```bash
# Test Ollama is working
curl http://localhost:11434/api/tags

# Should return JSON with your models

# Test Django
python test_agent.py
```

If you see `✓ All tests passed`, you're ready!

---

### Step 6: Start the Server

```bash
python manage.py runserver
```

Server starts at: `http://localhost:8000`

---

## 🧪 Test with Your Repo

### Test 1: Simple Question

```bash
curl -X POST http://localhost:8000/api/research/start/ \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/Fahad0907/kafka.git",
    "question": "Search for Docker files in this repository. List any Dockerfile or docker-compose files you find."
  }'
```

**Expected response (~2-3 minutes):**
```json
{
  "session_id": 1,
  "status": "completed",
  "answer": "I found the following Docker files...",
  "metadata": {
    "total_tool_calls": 3,
    "total_iterations": 2
  }
}
```

---

### Test 2: Check Session Details

```bash
# Replace 1 with your session_id from above
curl http://localhost:8000/api/research/1/ | jq
```

Look for:
- `"total_tool_calls"` - Should be > 0
- `"tool_calls"` - See what the agent did
- `"answer"` - Should reference actual files from YOUR repo

---

## 🎯 Writing Good Questions

### ❌ Bad (Ambiguous):
```
"is there docker setup?"
"how does it work?"
"what's the architecture?"
```

**Problem:** Agent might answer from general knowledge instead of searching your code.

---

### ✅ Good (Explicit):
```
"Search this repository for Dockerfile or docker-compose.yml and show me what you find"

"List all Python files in this repository, then find the main entry point"

"Find the database configuration in this codebase and explain how it's set up"
```

**Why better:** Forces the agent to search YOUR specific repository.

---

## 🐛 Troubleshooting

### Issue: "Connection refused to localhost:11434"

**Solution:** Ollama server not running.
```bash
# Start it in a separate terminal
ollama serve
```

---

### Issue: "Model not found"

**Solution:** Pull the model first.
```bash
ollama pull qwen2.5-coder:7b
```

---

### Issue: Agent doesn't use tools (total_tool_calls: 0)

**Check 1:** Is your question explicit enough?
```bash
# Instead of: "is there docker setup?"
# Try: "Search for 'Dockerfile' in this repository"
```

**Check 2:** View the session details:
```bash
curl http://localhost:8000/api/research/SESSION_ID/
```

Look at the `tool_calls` array.

---

### Issue: Very slow responses (>5 minutes)

**Solution 1:** Use a smaller model
```bash
ollama pull qwen2.5-coder:3b

# Update .env
LLM_MODEL=qwen2.5-coder:3b
```

**Solution 2:** Close other apps to free RAM

---

### Issue: Agent gives generic answers

This version has **much better prompts** to prevent this, but if it still happens:

1. **Be more explicit:** "Search THIS repository for..."
2. **Check tool_calls:** Verify tools were actually called
3. **Try a different model:**
   ```bash
   ollama pull deepseek-coder:6.7b
   # Update LLM_MODEL in .env
   ```

---

## 📊 Expected Performance

| Metric | Performance |
|--------|-------------|
| **First tool call** | 5-10 seconds |
| **Per iteration** | 10-20 seconds |
| **Full research** | 2-5 minutes |
| **Quality vs Claude** | 70-80% as good |
| **Cost** | **FREE** ✅ |

---

## 🎓 Tips for Best Results

### 1. Start Simple
Test with a simple question first:
```json
{"question": "List all files in this repository"}
```

### 2. Be Specific
Include keywords like "search", "find", "list", "show me"

### 3. Check Progress
Use Django admin to see what the agent is doing:
```
http://localhost:8000/admin/
```

Login with your superuser (create one if needed):
```bash
python manage.py createsuperuser
```

### 4. Monitor Tool Calls
In admin, go to: **Research Sessions → Tool Calls**

See exactly what the agent searched for and found.

---

## 🔄 Switching Models

Edit `.env`:

```bash
# Current (recommended)
LLM_MODEL=qwen2.5-coder:7b

# Alternatives:
LLM_MODEL=deepseek-coder:6.7b  # Also good for code
LLM_MODEL=llama3.1:8b           # Good general model
LLM_MODEL=mistral:7b            # Faster but less accurate
```

Then restart Django:
```bash
python manage.py runserver
```

---

## 🎉 You're All Set!

**Next Steps:**

1. Try the test commands above
2. Test with YOUR repository
3. Check Django admin to see what the agent is doing
4. Read TROUBLESHOOTING.md if you hit issues

---

## 📚 Additional Resources

- **Full Documentation:** README.md
- **Troubleshooting:** TROUBLESHOOTING.md
- **Architecture:** ARCHITECTURE.md
- **Ollama Docs:** https://ollama.com/docs

---

**Having issues?** Check TROUBLESHOOTING.md for detailed solutions!

**Questions about the code?** Check ARCHITECTURE.md to understand how it works!

Happy coding! 🚀
