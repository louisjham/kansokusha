# Social Media Insight & Forensic Analysis Platform

A scalable, AI-driven intelligence platform designed for deep behavioral assessment and risk analysis of social media footprints. This system leverages advanced LLMs (Gemini, Open/Local AI) to perform multi-stage forensic profiling, providing real-time insights into risk factors, character traits, and behavioral patterns.

## Key Features

- **Multi-Stage Forensic AI Analysis**:
  - **Risk Assessment**: Automated detection of security threats, radicalization indicators, and red flags.
  - **Psycholinguistic Profiling**: Deep analysis of cognitive patterns and emotional landscapes.
  - **Behavioral Matrix**: Mapping of social dynamics and posting habits.
  - **Ideological Mapping**: Assessment of values, beliefs, and alignment.
- **Real-Time Streaming**: Live terminal-style feedback during high-latency AI operations.
- **Social Media Scraping**: Integrated job management for retrieving data from platforms via Apify.
- **Role-Based Access Control (RBAC)**: secure hierarchy (Admin, Manager, Analyst) for data protection.
- **Reporting**: Comprehensive export options (PDF, CSV) with tiered data visibility.
- **Audit Logging**: Full traceability of all user actions and system events.

## Tech Stack

- **Backend**: Python 3.8+, Flask, SQLAlchemy (ORM)
- **Database**: PostgreSQL (Production) / SQLite (Dev)
- **AI Integration**: Google Gemini, Z.AI, OpenRouter (OpenAI-compatible)
- **Frontend**: Bootstrap 5, Jinja2, Marked.js

## Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository_url>
    cd <repository_drive>
    ```

2.  **Set up Virtual Environment**:
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Linux/Mac
    source .venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration**:
    Copy `.env.example` to `.env` and populate your API keys:
    ```bash
    cp .env.example .env
    ```
    *Required keys: `SECRET_KEY`, `DATABASE_URL` (or default sqlite), and AI provider keys (`GOOGLE_API_KEY`, etc.).*

5.  **Initialize Database**:
    ```bash
    flask db upgrade
    # Seed initial admin user
    python scripts/seed_admin.py
    ```

## Usage

1.  **Start the Server**:
    ```bash
    python run.py
    ```
    The application typically runs on port `4444`.

2.  **Workflow**:
    - Log in as an Admin/Manager.
    - Create an Employee profile.
    - Initiate a Scraping Job (e.g., Twitter/X profile).
    - Once scraping is complete, trigger **"Start Analysis"**.
    - Watch the real-time forensic assessment.
    - View and export the final report.

## License

Private / Proprietary.

## OSINT & Web Discovery Safeguards

The `web_discovery` platform is designed strictly for lawful, open-source intelligence (OSINT) enrichment to locate public presence. It implements several hardcoded safeguards to prevent abuse:

1. **Information Leakage Prevention**: Queries avoid exposing full emails, private identifiers, or personal secrets. Domain filters isolate domain suffixes for organization searches instead of raw email handles.
2. **Exploit Protection**: The query builder forbids search engine hacking operators (e.g. `inurl:`, `intitle:`) and keywords related to exploit search payloading or security vulnerability probing.
3. **Keyword Safeguards**: The system screens all user input profiles against a blocklist of security, credential-harvesting, and bank/financial risk keywords, returning zero results if any violations are detected.
4. **Aggregation Filters**: Low-value search spam and commercial database aggregators (people-search scrapers like Spokeo/Whitepages) are automatically blocked and stripped from output lists.

