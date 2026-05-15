# Deployment Guide

## Quick Start (5 minutes)

### 1. Prerequisites
```bash
# Verify Python version
python --version  # Should be 3.10+

# Verify Git
git --version
```

### 2. Install Dependencies
```bash
cd codebase-research-agent
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your Anthropic API key
# LLM_API_KEY=your-key-here
nano .env  # or use your preferred editor
```

### 4. Initialize Database
```bash
python manage.py migrate
```

### 5. Run Server
```bash
python manage.py runserver
```

Server will start at `http://localhost:8000`

---

## Testing the Installation

### Option 1: Create Sample Data (Recommended)
```bash
python manage.py create_sample_data
```

This will research 2 repositories and take ~5-10 minutes depending on your API limits.

### Option 2: Manual Test
```bash
curl -X POST http://localhost:8000/api/research/start/ \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/psf/requests",
    "question": "How does requests handle HTTP sessions?"
  }'
```

### Verify Results
```bash
# Get session details (replace 1 with your session_id)
curl http://localhost:8000/api/research/1/
```

---

## Configuration Options

### Using PostgreSQL (Production)

1. Install PostgreSQL and create database:
```bash
createdb codebase_agent
```

2. Update `.env`:
```bash
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=codebase_agent
DATABASE_USER=postgres
DATABASE_PASSWORD=your_password
DATABASE_HOST=localhost
DATABASE_PORT=5432
```

3. Run migrations:
```bash
python manage.py migrate
```

### Adjusting Agent Behavior

Edit `config/settings.py`:

```python
# Agent Configuration
AGENT_MAX_ITERATIONS = 8          # Max reasoning loops
AGENT_MAX_FILE_SIZE = 1024 * 1024 # Max file read size (1MB)
AGENT_IGNORED_DIRS = ['.git', 'node_modules', ...]
```

### Repository Storage Location

Default: `/tmp/codebase_repos`

To change, update `.env`:
```bash
REPO_STORAGE_PATH=/var/app/repos
```

---

## Admin Interface

1. Create superuser:
```bash
python manage.py createsuperuser
```

2. Access admin at:
```
http://localhost:8000/admin/
```

View:
- All research sessions
- Tool call traces
- Findings and insights
- Repository metadata

---

## Production Deployment

### Using Gunicorn

1. Install Gunicorn:
```bash
pip install gunicorn
```

2. Run with workers:
```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### Using Docker (Optional)

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python manage.py migrate

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

Build and run:
```bash
docker build -t codebase-agent .
docker run -p 8000:8000 --env-file .env codebase-agent
```

---

## Troubleshooting

### "No module named 'decouple'"
```bash
pip install python-decouple
```

### "LLM_API_KEY is not configured"
Ensure `.env` file exists in project root with:
```
LLM_API_KEY=sk-ant-...
```

### Repository clone fails
- Check GitHub URL is public
- Verify internet connection
- Ensure Git is installed and in PATH

### SQLite database locked
- Use PostgreSQL for production
- Or reduce concurrent requests to 1-2

### Agent gives incomplete answers
- Increase `AGENT_MAX_ITERATIONS` in settings.py
- Check `LLM_MAX_TOKENS` is at least 4096
- Review session tool_calls to see what agent explored

---

## Performance Tips

### For Large Repositories

1. Clone takes time on first request - consider pre-cloning:
```python
from agent.repo_loader import get_repo_loader
loader = get_repo_loader()
loader.get_or_clone("https://github.com/large/repo")
```

2. Increase timeouts if needed:
```python
# In agent/llm_client.py
response = requests.post(..., timeout=180)  # 3 minutes
```

### For Cost Optimization

1. Track token usage via admin interface
2. Limit max iterations for exploratory queries
3. Use directory structure before reading files
4. Cache repository clones

---

## API Rate Limits

### Anthropic API
- Claude Sonnet: 50 requests/minute (free tier)
- Consider implementing request queuing for high volume

### GitHub API
- Cloning is unlimited for public repos
- Private repos require authentication token

---

## Monitoring

### Check System Health
```bash
# View recent sessions
python manage.py shell
>>> from research_sessions.models import ResearchSession
>>> ResearchSession.objects.filter(status='failed')
```

### Database Queries
```bash
# Count total sessions
python manage.py shell
>>> from research_sessions.models import ResearchSession
>>> ResearchSession.objects.count()
```

---

## Support

For issues or questions:
1. Check README.md for detailed documentation
2. Review tool_calls in session details for debugging
3. Check Django logs for error traces

---

## Next Steps

After deployment:
1. Test with sample data: `python manage.py create_sample_data`
2. Review sessions in admin interface
3. Test API endpoints with your repositories
4. Monitor token usage and costs
5. Consider adding authentication for production use
