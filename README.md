# Kansokusha (観測者) ── Forensic Social Insights & AI Risk Analysis Platform

**Kansokusha** (The Observer) is a premium, AI-driven digital forensics and open-source intelligence (OSINT) platform designed for deep behavioral auditing, psycholinguistic profiling, and risk analysis of public footprints.

Leveraging multi-stage LLM analysis pipelines via OpenRouter, the platform processes public activities across social channels to produce forensic risk profiles, highlight behavioral anomalies, and assess reputational security in real-time.

---

## 🚀 Key Modules & Architecture

### 1. Social Scraping & Discovery Integrations
- **GitHub Profile Auditing**: Synchronously extracts public repositories, commit events, and user bio descriptions via REST APIs.
- **YouTube Media Scraping**: Synchronously fetches video descriptions, upload catalogs, and processes up to 20 top-level viewer comments per video.
- **Reddit Behavior Scraping**: Integrates with Apify actors to fetch user submissions, comments, and scores.
- **Web Discovery (OSINT)**: Executes target search engine queries ("dorks") via Google Custom Search Engine to surface additional profiles, documents, forum mentions, and press articles.
- **Legacy Platform Scraping**: Apify actor orchestration for Twitter/X and Facebook profiles.

### 2. Multi-Stage AI Forensic Analysis
Kansokusha streams results line-by-line using a staged assessment workflow:
- **Phase 1: Risk Assessment & Red Flags**: Identifies threats, hate speech, or radicalization indicators.
- **Phase 2: Psycholinguistic & Behavioral Profiling**: Conducts emotional analysis, habit mapping, and cognitive indicators.
- **Phase 3: Ideological Mapping**: Identifies key values, biases, and alignment signals.
- **Phase 4: Synthesis & Scoring**: Calculates a normalized 0-100 risk score and compiles executive reviews.

### 3. Role-Based Access Control (RBAC)
- **Analyst / Reviewer**: Can view employee records, run reports, and view audit history.
- **Platform Manager**: Can trigger scraping jobs, run discovery runs, and launch forensic AI assessments.
- **System Administrator**: Full access to global OpenRouter keys, system settings, and diagnostic test routes.

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.9 or higher
- SQLite (for development) or PostgreSQL 14+ (for production environments)
- Git

### 1. Clone the Codebase
```bash
git clone https://github.com/louisjham/kansokusha.git
cd kansokusha
```

### 2. Configure Virtual Environment
Create and activate a virtual environment to manage dependencies cleanly:
```bash
# Create environment
python -m venv .venv

# Activate on Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Activate on Linux/macOS
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Setup Environment Settings
Create a `.env` file from the example template:
```bash
cp .env.example .env
```

Open `.env` and fill out the configuration parameters:
- **`SECRET_KEY`**: Set a long, secure random key for session encryption.
- **`OPENROUTER_API_KEY`**: Provide your OpenRouter API key.
- **`OPENROUTER_MODEL`**: Default is set to `google/gemini-2.0-flash-lite:free`.
- **`GITHUB_TOKEN`**: (Optional) To increase GitHub API limits from 60/hr to 5000/hr.
- **`YOUTUBE_API_KEY`**: Required to run YouTube scrapes.
- **`GOOGLE_CSE_API_KEY` & `GOOGLE_CSE_CX`**: Required to execute Web Discovery OSINT sweeps.
- **`APIFY_API_TOKEN`**: Required to scrape Reddit, Twitter, or Facebook.

### 5. Initialize Database & Seed Administrator
Setup the database tables and create the default admin user:
```bash
# Perform database migration
flask db upgrade

# Seed initial system administrator
python scripts/seed_admin.py
```
*Note: The seeding script outputs default credentials for initial login. Ensure you change your password on first sign-in.*

---

## 📈 Operation & Usage Guide

### 1. Launch the Development Server
```bash
python run.py
```
Open your browser and navigate to `http://localhost:4444`.

### 2. Add an Employee Profile
1. Log in with a **Platform Manager** or **Administrator** account.
2. Select **Employees** from the sidebar/navbar, then click **Add Employee**.
3. Fill out the employee details (First Name, Last Name, Email, Department, and Position) and click **Create**.

### 3. Configure Social Accounts
1. Inside the Employee view page, click **Add Social Account**.
2. Select the platform (e.g. YouTube, GitHub, Reddit, or Web Discovery).
3. Enter the **Username** or **Handle** and the target **Profile URL** (or channel URL for YouTube), then save.

### 4. Execute Scraping Jobs
1. On the Employee profile dashboard, locate the newly added account and click **Start Scraping**.
2. For synchronous platforms (GitHub, YouTube, Web Discovery), data will be fetched, scored, and mapped immediately, transitioning the status to `Completed`.
3. For asynchronous platforms (Twitter, Reddit, Facebook), a job is dispatched to Apify. Click **Refresh Status** on the Job details view to query completion progress and fetch logs.

### 5. Launch AI Assessment
1. Once scraping jobs are finished, click **Trigger Analysis** under the Employee profile dashboard.
2. Select the target scraping jobs to include in the context.
3. Choose the OpenRouter model (defaulting to the free Gemini model).
4. Click **Start Forensic Analysis**. The page will load a real-time streaming terminal interface displaying multi-stage cognitive assessments line-by-line.
5. Once completed, review the generated risk assessment, positive indicators, and executive PDF/CSV reports.

---

## 🔒 OSINT & Web Discovery Safeguards

The `web_discovery` module runs targeted search queries strictly for open-source profile and document attribution. To prevent malicious usage or credential exposure, the service enforces the following constraints:

1. **Identifier Leak Checks**: Scans incoming profile data for password strings, private tokens, SSN formats, or credit card numbers. If any are detected, query generation immediately aborts.
2. **Exploit Operator Block**: Forbids search hacking commands like `inurl:`, `intitle:`, or folder indices (e.g. `index of`) that could be used for scanning system weaknesses.
3. **Low-Value Spam Filtering**: Discards results originating from database brokers or spam aggregator domains (e.g., Whitepages, Spokeo, Radaris).
4. **Data Minimization**: Limits queries to public-domain search filters (such as LinkedIn, GitHub, GitLab, Reddit, StackOverflow, Medium, and Substack).

---

## ⚖️ License
Private and Proprietary. All Rights Reserved.
