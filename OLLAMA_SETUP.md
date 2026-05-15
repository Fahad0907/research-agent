# Using Ollama (Free Open-Source Models)

This guide shows you how to run the agent with **Ollama** instead of paid APIs like Claude or GPT-4.

---

## ✅ Benefits of Ollama

- **FREE** - No API costs
- **Private** - Runs locally, your code never leaves your machine
- **No Internet Required** - After downloading models
- **Good for Testing** - Understand how the agent works
- **Multiple Models** - Try different open-source models

---

## ⚠️ Trade-offs

- **Quality** - Not as good as Claude/GPT-4 (but decent for code)
- **Speed** - Depends on your hardware (needs good CPU/GPU)
- **RAM** - Models need 8-16GB RAM
- **Tool Calling** - Simulated (not native like Claude)

---

## 🚀 Quick Setup (10 minutes)

### Step 1: Install Ollama

**On macOS:**
```bash
brew install ollama
```

**On Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**On Windows:**
Download from: https://ollama.com/download

---

### Step 2: Start Ollama Server

```bash
ollama serve
```

Leave this running in the background.

---

### Step 3: Pull a Model

**Recommended: Qwen2.5-Coder 7B** (Best for code analysis)
```bash
ollama pull qwen2.5-coder:7b
```

**Alternative Options:**

```bash
# DeepSeek Coder (specialized for code)
ollama pull deepseek-coder:6.7b

# Llama 3.1 (good general model)
ollama pull llama3.1:8b

# Mistral (fast and capable)
ollama pull mistral:7b
```

**Download size:** ~4-5GB per model

---

### Step 4: Configure the Project

Edit your `.env` file:

```bash
cd codebase-research-agent
cp .env.example .env
nano .env
```

**Set these values:**
```bash
# Change provider to ollama
LLM_PROVIDER=ollama

# Configure Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b

# You can leave these empty (not needed for Ollama)
LLM_API_KEY=
```

---

### Step 5: Test It

```bash
# Test Ollama directly
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5-coder:7b",
  "prompt": "Say hello"
}'

# Test the agent
python test_agent.py
```

---

### Step 6: Run the Agent

```bash
python manage.py runserver
```

Test with a small repo:
```bash
curl -X POST http://localhost:8000/api/research/start/ \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/psf/requests",
    "question": "How does requests handle HTTP sessions?"
  }'
```

---

## 🎯 Recommended Models for This Project

### 1. **Qwen2.5-Coder 7B** ⭐ BEST
```bash
ollama pull qwen2.5-coder:7b
```
- **Best for:** Code analysis
- **Size:** 4.7GB
- **RAM needed:** 8GB
- **Quality:** Excellent for code tasks

### 2. **DeepSeek-Coder 6.7B**
```bash
ollama pull deepseek-coder:6.7b
```
- **Best for:** Code generation and analysis
- **Size:** 3.8GB
- **RAM needed:** 8GB
- **Quality:** Very good for code

### 3. **Llama 3.1 8B**
```bash
ollama pull llama3.1:8b
```
- **Best for:** General purpose
- **Size:** 4.7GB
- **RAM needed:** 8GB
- **Quality:** Good overall

### 4. **Mistral 7B** (Fastest)
```bash
ollama pull mistral:7b
```
- **Best for:** Speed
- **Size:** 4.1GB
- **RAM needed:** 8GB
- **Quality:** Decent

---

## ⚙️ Hardware Requirements

| Model | RAM Needed | CPU | GPU (Optional) |
|-------|-----------|-----|----------------|
| 7B models | 8GB | 4 cores | NVIDIA GPU speeds up |
| 13B models | 16GB | 8 cores | Recommended |
| 70B+ models | 48GB+ | 16 cores | Required |

**For this project:** 7B models work great!

---

## 🔧 How Ollama Integration Works

### The Problem
Ollama **doesn't natively support tool calling** like Claude does.

### The Solution
We **simulate tool calling** by:

1. **Including tools in the prompt:**
   ```
   You have these tools available:
   - read_file: Read a file from the repo
   - search_code: Search for patterns
   ...
   
   To use a tool, respond with JSON:
   {
     "tool": "read_file",
     "parameters": {"file_path": "main.py"}
   }
   ```

2. **Parsing JSON from response:**
   The model responds with JSON blocks, we extract and execute them.

3. **Converting to standard format:**
   We convert Ollama's response to match Claude's format so the rest of the code works unchanged.

---

## 📊 Expected Performance

### Quality Comparison

| Aspect | Claude Sonnet 4 | Qwen2.5-Coder | DeepSeek-Coder |
|--------|----------------|---------------|----------------|
| Code Understanding | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Tool Usage Accuracy | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Answer Quality | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Speed | Fast | Medium | Medium |
| Cost | $0.02-0.05 | FREE | FREE |

### Speed Expectations

**With good hardware (8 cores, 16GB RAM):**
- Tool call decision: 3-5 seconds
- File reading + analysis: 5-10 seconds
- Full research session: 2-5 minutes

**With basic hardware (4 cores, 8GB RAM):**
- Tool call decision: 10-15 seconds
- File reading + analysis: 15-30 seconds
- Full research session: 5-10 minutes

---

## 🐛 Troubleshooting

### Issue: "Connection refused to localhost:11434"
**Solution:** Start Ollama server:
```bash
ollama serve
```

### Issue: "Model not found"
**Solution:** Pull the model first:
```bash
ollama pull qwen2.5-coder:7b
```

### Issue: "Out of memory"
**Solution:** Use a smaller model or close other apps:
```bash
ollama pull mistral:7b  # Smaller model
```

### Issue: "Very slow responses"
**Solution:** 
1. Close other apps to free RAM
2. Use a smaller model
3. Consider using a GPU (if available)

### Issue: "Tool calls not working"
**Solution:** The model might not be following the JSON format. Try:
1. Using Qwen2.5-Coder (best at following instructions)
2. Checking the tool output in Django admin
3. Simplifying your question

---

## 💡 Tips for Best Results

### 1. **Start with Simple Questions**
```bash
# Good first test
"Where is the main entry point of this code?"

# Complex (might struggle)
"Explain the entire authentication flow with all edge cases"
```

### 2. **Use Code-Specific Models**
- Qwen2.5-Coder ✅
- DeepSeek-Coder ✅
- Llama (general) ⚠️
- Mistral (general) ⚠️

### 3. **Be Patient**
Open-source models are slower than API calls. A session might take 3-5 minutes.

### 4. **Monitor in Django Admin**
Watch the ToolCall logs to see what the agent is doing:
```
http://localhost:8000/admin/
```

---

## 🔄 Switching Between Ollama and Claude

You can switch providers anytime by editing `.env`:

**Use Ollama (Free):**
```bash
LLM_PROVIDER=ollama
```

**Use Claude (Paid, Better Quality):**
```bash
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-api03-...
```

No code changes needed!

---

## 📈 When to Use What

### Use Ollama When:
- ✅ Testing the agent architecture
- ✅ Learning how tool-calling works
- ✅ Working on private/sensitive code
- ✅ No budget for API calls
- ✅ Have decent hardware (8GB+ RAM)

### Use Claude API When:
- ✅ Need best quality answers
- ✅ Production use
- ✅ Complex codebases
- ✅ Time-sensitive (faster responses)
- ✅ Limited hardware

---

## 🎓 Learning Benefits

Using Ollama helps you understand:
1. **How tool calling works** - You see the JSON prompts
2. **Agent reasoning** - Slower = easier to follow
3. **Model limitations** - Appreciate Claude's quality
4. **Local AI** - No dependency on external APIs

---

## 📚 Additional Resources

- **Ollama Docs:** https://ollama.com/docs
- **Model Library:** https://ollama.com/library
- **Qwen2.5-Coder:** https://ollama.com/library/qwen2.5-coder
- **DeepSeek-Coder:** https://ollama.com/library/deepseek-coder

---

## ✅ Quick Start Checklist

- [ ] Install Ollama
- [ ] Start Ollama server (`ollama serve`)
- [ ] Pull a model (`ollama pull qwen2.5-coder:7b`)
- [ ] Edit `.env` file (set `LLM_PROVIDER=ollama`)
- [ ] Test with `python test_agent.py`
- [ ] Start Django (`python manage.py runserver`)
- [ ] Try a simple question first
- [ ] Monitor progress in Django admin

---

**Questions?** Check the troubleshooting section above or the main README.md!

Happy coding! 🚀
