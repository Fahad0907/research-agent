# DECISIONS.md - Codebase Research Agent

## Architecture Overview

┌─────────────────────────────────────────────────────────────────┐
│                         User API Layer                          │
│                    (Django REST Framework)                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ResearchService Layer                        │
│                   (Business Logic & Orchestration)              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              CodebaseResearchAgent (Core Reasoning)             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          Forced Tool Execution Strategy                  │  │
│  │  Layer 1: Initial Structure (Mandatory)                  │  │
│  │  Layer 2: Keyword-Based Fallback                        │  │
│  │  Layer 3: LLM Tool Calling (Optional)                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AgentTools (6 Tools)                         │
│  search_code • read_file • get_directory_structure              │
│  list_files • save_finding • get_previous_findings              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              Database (Repository → Session → ToolCall)         │
└─────────────────────────────────────────────────────────────────┘


🚀 PHASE 1 — Project Foundation (Django Backend)

## ✅ Task 1: Django Project Setup

Goal: Set up clean Django + DRF backend structure.

Prompt:
Create a Django project with Django REST Framework for an AI agent system.
The project should follow clean architecture principles with separation of concerns.

Include apps for:
- repositories (repo management)
- research_sessions (session tracking)
- agent (core reasoning logic)

Requirements:
- Use PostgreSQL (fallback SQLite for development)
- Configure settings cleanly (environment-based with python-decouple)
- Add DRF setup with proper serializers
- Create base project structure with clean folder organization
- No business logic yet, just scaffolding

Output only production-ready Django structure with:
- manage.py
- config/settings.py (with env vars)
- requirements.txt
- .env.example


## ✅ Task 2: Database Models Design

Goal: Design schema for Repository, ResearchSession, ToolCall, Finding

Prompt:

Design Django models for an AI codebase research agent.

Must include:

1. Repository model:
   - url (unique, CharField)
   - name (CharField)
   - local_path (CharField, nullable)
   - total_sessions (IntegerField, denormalized counter)
   - last_analyzed (DateTimeField)
   - created_at (DateTimeField)

2. ResearchSession model:
   - repository (ForeignKey to Repository)
   - question (TextField)
   - final_answer (TextField, nullable)
   - status (CharField: pending/processing/completed/failed)
   - total_iterations (IntegerField, default 0)
   - total_tool_calls (IntegerField, default 0)
   - token_usage (IntegerField, default 0)
   - created_at, started_at, completed_at (DateTimeFields)
   - error_message (TextField, nullable)

3. ToolCall model:
   - session (ForeignKey to ResearchSession)
   - tool_name (CharField)
   - tool_input (JSONField)
   - tool_output (TextField)
   - iteration (IntegerField)
   - execution_time_ms (IntegerField)
   - created_at (DateTimeField)

4. Finding model:
   - session (ForeignKey to ResearchSession)
   - file_path (CharField)
   - line_start, line_end (IntegerField, nullable)
   - note (TextField)
   - relevance_score (FloatField, 0-1)
   - created_at (DateTimeField)

Requirements:
- Normalize where needed, but keep schema simple
- Add proper indexes: (repository, -created_at), (session, iteration)
- Include helper methods: mark_completed(), increment_iteration()
- Use Django ORM only (no raw SQL)

Return only models.py code for all 4 models.


🧠 PHASE 2 — Agent Core (MOST IMPORTANT)

## ✅ Task 3: Agent Loop Design with Forced Tool Execution

Goal: Build reasoning loop with guaranteed tool usage

Prompt:

Build the core AI agent loop in Python for a Django project that works with unreliable LLMs.

The agent MUST use a 3-layer forced tool execution strategy:

Layer 1 - Mandatory Initial Exploration:
- ALWAYS execute get_directory_structure() on first iteration
- No LLM choice - this is forced

Layer 2 - Keyword-Based Tool Suggestion (Fallback):
- If question contains "docker" → force search_code("Dockerfile", "docker-compose")
- If question contains "auth" → force search_code("auth", "login", "password")
- If question contains "database" → force search_code("postgres", "sqlite", "mysql")
- If question contains "static" → force search_code("STATIC_URL", "static")
- Map keywords to relevant searches

Layer 3 - LLM Tool Calling (Optional):
- If LLM generates tool calls, execute those too
- But never rely on LLM alone

The agent should:
- Accept a user question + repository path
- Run iterative reasoning loop (max 8 steps)
- Stop when: max iterations OR final answer OR repeated tools detected
- Track all tool calls to database

Safety features:
- Hard iteration limit (8)
- Repeated tool call detection (prevent infinite loops)
- Visited file tracking
- Graceful error handling

Requirements:
- Must prevent infinite loops completely
- Must log every tool call to ToolCall model
- Must guarantee tool usage even if LLM fails
- Keep agent class design clean and modular

Return clean agent class (CodebaseResearchAgent) with:
- __init__(session_id, repo_path)
- research(question) → answer
- _reasoning_loop(system_prompt) → answer
- _suggest_tools_from_question(question) → [tool_calls]
- _is_repeating_tools(tool_calls) → bool
- _force_final_answer() → answer


## ✅ Task 4: Tool System Implementation

Goal: Create modular tool interface with safety

Prompt:
Implement a tool system for an LLM agent in Python.

Tools required:

1. search_code(query: str) → str
2. read_file(file_path: str) → str
3. list_files(path: str) → str
4. get_directory_structure(max_depth: int = 3) → str
5. save_finding(file_path: str, note: str, relevance_score: float) → str
6. get_previous_findings() → str

Requirements:
- Tools must be independent methods in AgentTools class
- Must integrate with Django ORM for logging (create ToolCall on each use)
- Must include safe file handling (path traversal checks, size limits)
- Tools return plain text (not objects) for LLM consumption
- Each tool logs: tool_name, input, output, iteration to ToolCall model


## ✅ Task 5: GitHub Repo Loader

Goal: Clone and cache repositories safely

Prompt:
Build a GitHub repository loader module for a Django backend.

Requirements:
- Accept GitHub URL
- Generate unique local path
- Clone repo to REPO_STORAGE_PATH
- Cache repos (git pull if exists)
- Extract repo name
- Provide get_or_clone(url)

Security:
- Validate GitHub URL
- Isolated storage
- No code execution

Methods:
- get_or_clone(url)
- _is_valid_github_url(url)
- _extract_repo_name(url)
- _clone_repository(url, local_path)


🧩 PHASE 3 — API LAYER

## ✅ Task 6: Start Research API

POST /api/research/start/

Flow:
1. Validate input
2. Clone repo
3. Create session
4. Run agent
5. Return result

## ✅ Task 7: Get Research Result API

GET /api/research/<session_id>/

Return:
- session details
- tool calls
- findings
- referenced files

## ✅ Task 8: List Repository Sessions API

GET /api/repositories/sessions/?repo_url=...

---

📚 PHASE 4 — LLM INTEGRATION

## ✅ Task 9: Ollama LLM Client

Build Ollama client with:
- chat_completion()
- tool parsing
- response parsing
- error handling

Config:
- LLM_API_URL
- LLM_MODEL
- LLM_MAX_TOKENS

(duplicate prompt removed — kept single version)


## ✅ Task 10: System Prompt

- Enforce tool usage
- Structured answers
- 200–300 lines
- Include examples


⚙️ PHASE 5 — SAFETY & OPTIMIZATION

## ✅ Task 11: Stop Conditions

- Max 8 iterations
- Prevent loops
- Track visited files
- Stop on repetition

## ✅ Task 12: Answer Formatting

Formats:
- YES/NO
- HOW/WHAT/WHERE

## ✅ Task 13: Context Management

- No full repo loading
- Search-first approach
- 1MB file limit
- Scalable to 5,000+ files


🎯 KEY DESIGN DECISIONS

- 6 tools only
- Forced tool execution (core innovation)
- Full DB logging
- No infinite loops (guaranteed)
- Search-first architecture
- Incremental exploration


📊 EXPECTED RESULTS

- 95% tool usage success
- 3–5 iterations avg
- 5–7 tool calls/session
- Safe + scalable + traceable system
