# Pre-Flight Checklist

## Before Running the Agent

Use this checklist to ensure everything is properly configured.

### ✓ Installation Checklist

- [ ] Python 3.10+ installed
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created from `.env.example`
- [ ] `LLM_API_KEY` configured in `.env`
- [ ] Database migrated (`python manage.py migrate`)
- [ ] Server starts without errors (`python manage.py runserver`)

### ✓ Configuration Checklist

- [ ] LLM API key is valid (test with `python test_agent.py`)
- [ ] Repository storage directory exists (default: `/tmp/codebase_repos`)
- [ ] Git is installed and accessible
- [ ] Internet connection available for repository cloning

### ✓ Testing Checklist

- [ ] Test script passes (`python test_agent.py`)
- [ ] Admin interface accessible at `http://localhost:8000/admin/`
- [ ] API endpoints respond (test with curl or Postman)
- [ ] Sample data creates successfully (optional)

### ✓ Production Checklist (If Deploying)

- [ ] Change `SECRET_KEY` in production
- [ ] Set `DEBUG=False` in `.env`
- [ ] Configure `ALLOWED_HOSTS` properly
- [ ] Use PostgreSQL instead of SQLite
- [ ] Set up proper logging
- [ ] Configure CORS if needed
- [ ] Add authentication to API endpoints
- [ ] Set up monitoring/alerting
- [ ] Configure backup strategy for database

## Quick Test Commands

### 1. Verify Installation
```bash
python test_agent.py
```

### 2. Test API Endpoint
```bash
curl -X POST http://localhost:8000/api/research/start/ \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/psf/requests",
    "question": "How does requests handle sessions?"
  }'
```

### 3. Check Database
```bash
python manage.py shell
>>> from research_sessions.models import ResearchSession
>>> ResearchSession.objects.count()
```

### 4. Create Sample Data
```bash
python manage.py create_sample_data
```

## Common Issues

### Issue: "LLM_API_KEY is not configured"
**Solution**: Ensure `.env` file exists with valid API key

### Issue: Repository clone fails
**Solution**: 
- Check internet connection
- Verify GitHub URL is public
- Ensure Git is installed

### Issue: Import errors
**Solution**: Verify all dependencies installed:
```bash
pip install -r requirements.txt
```

### Issue: Database errors
**Solution**: Run migrations:
```bash
python manage.py migrate
```

## Support

If all checks pass but you still have issues:
1. Check Django logs for detailed errors
2. Review `tool_calls` in session details for debugging
3. Verify Anthropic API status
4. Check GitHub API limits

## Ready to Go!

Once all items are checked:
1. Start server: `python manage.py runserver`
2. Test with sample data or manual requests
3. Review results in admin interface
4. Monitor token usage and costs

Good luck with your research! 🚀
