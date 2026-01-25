---
trigger: always_on
---

text
# CrystalLens Development Workspace

## Project Overview
Flask-based social media analysis platform using AI (Ollama/Gemini) for evidence-driven assessment. Integrates Apify for scraping Twitter/Facebook and provides RBAC, audit logging, and PDF reporting capabilities.

## Environment Setup

### Required Tools
- Python 3.8+ with venv
- Ollama (optional, for local LLM inference)
- PostgreSQL (production) or SQLite (dev)
- Apify account with API token

### Initial Setup Commands
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/WSL
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Seed admin user
python scripts/seed_admin.py

# Run development server
python run.py
Environment Variables (.env)
APIFY_API_TOKEN: Required for social media scraping

OLLAMA_API_URL: http://localhost:11434 (if using local Ollama)

OLLAMA_MODEL: llama3.1:8b or qwen2.5:7b-instruct

GOOGLE_API_KEY: For Gemini cloud analysis

ANALYSIS_PROVIDER: ollama or gemini

DATABASE_URL: PostgreSQL connection string (production)

SECRET_KEY: Flask secret key for sessions

Code Style & Conventions
Python Standards
Follow PEP 8 style guidelines

Use type hints where appropriate

Keep functions focused and modular

Document complex analysis logic

Flask Structure
Routes in app/routes/

Models in app/models/

Services/business logic separated from routes

Templates use Jinja2 in app/templates/

Security Considerations
Never commit .env or secrets

Validate all user inputs (WTForms)

Use parameterized SQL queries (SQLAlchemy ORM)

Implement RBAC checks on sensitive endpoints

Audit log all critical actions

Development Workflow
Working with AI Providers
Test both Ollama (privacy) and Gemini (speed) paths

Handle JSON parsing errors gracefully

Implement retry logic for API failures

Cache analysis results to reduce API calls

Database Migrations
Use Flask-Migrate for schema changes (if adding)

Test migrations on SQLite before PostgreSQL

Back up production data before migrations

Testing Apify Integration
Use Apify's free tier for development

Mock Apify responses for unit tests

Handle rate limiting and job failures

Store raw scraped data for re-analysis

Key Features to Understand
Analysis Modes
Single-request: Fast, direct assessment

Staged: Evidence extraction → Assessment (more robust)

Assessment Types
Political orientation

Religious orientation

Bias detection

Personal issues

Violence tendency

Affiliation analysis

Role suitability

RBAC Roles
Admin: Full system access

Manager: Can initiate analysis, view reports

Reviewer: Read-only access to reports

Ethical & Legal Guidelines
⚠️ Critical: This tool is for educational/research purposes only

Comply with all applicable laws and regulations

Respect social media platforms' Terms of Service

Do not use for unauthorized surveillance

Consider privacy implications of social media analysis

Document legitimate use cases only

Optimization Opportunities
Performance
Implement caching for LLM responses

Batch process multiple profiles

Use async for Apify job polling

Optimize database queries (indexes)

Feature Enhancements
Add OpenAI/Claude provider support

Implement detail level presets

Chunk-and-synthesize for long timelines

Enhanced PDF report templates

Real-time scraping progress indicators

Security Hardening
Implement rate limiting per user

Add 2FA for admin accounts

Encrypt sensitive data at rest

Regular security audit logging review

Input sanitization for all user content

Debugging & Troubleshooting
Common Issues
Ollama connection: Ensure ollama serve is running

Apify failures: Check token validity and rate limits

Database errors: Verify migrations are current

LLM JSON parsing: Add retry logic with prompt refinement

Slow analysis: Consider switching to Gemini or using smaller models

Logs & Monitoring
Check Flask logs: stdout when running python run.py

Review audit logs in database for RBAC issues

Monitor Apify job status through dashboard

Track LLM API usage/costs

Integration with Your Security Workflow
Use Cases for Security Research
Threat actor profiling from public social media

OSINT automation for investigations

Pattern detection across multiple accounts

Evidence collection with citations

Tool Integration
Export CSV data for further analysis

Integrate with existing OSINT pipelines

API endpoints for automated workflows

Combine with network reconnaissance data

File Structure Priority
text
CrystalLens/
├── app/                 # Main application code
├── scripts/             # Utility scripts (seed_admin.py)
├── config.py            # Configuration management
├── requirements.txt     # Python dependencies
├── run.py              # Application entry point
├── .env.example        # Environment template
└── README.md           # Project documentation
Deployment Notes
Production Checklist
Use PostgreSQL (not SQLite)

Set strong SECRET_KEY

Use gunicorn as WSGI server

Enable HTTPS only

Regular database backups

Monitor API usage/costs

Review audit logs regularly