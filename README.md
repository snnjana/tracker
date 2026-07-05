# AI Incident Timeline Correlator

A web application that helps engineers identify root causes of production incidents by correlating GitHub commit history (with code diffs) and issues using AI-powered analysis via Groq.

## How It Works

1. Paste a GitHub repository URL and select a time range (up to 7 days)
2. Optionally provide your GitHub token for private repo access
3. The tool fetches commits (with diffs) and issues from that window
4. Groq AI analyzes the data to identify correlations
5. You get a structured report with:
   - Chronological timeline of events
   - Suspicious commits with confidence levels and code-level explanations
   - Related GitHub issues
   - Root cause summary
   - Suggested rollback commands

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite |
| Backend | Python 3.11+, FastAPI, Pydantic |
| GitHub Integration | PyGithub |
| AI Analysis | Groq SDK (`llama-3.3-70b-versatile`) |
| Styling | Custom CSS (dark theme, glassmorphism) |

## Prerequisites

- Python 3.11+
- Node.js 18+
- A Groq API key ([get one free](https://console.groq.com/keys))

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
GROQ_API_KEY=gsk_your_groq_key_here
```

Start the server:

```bash
uvicorn app.main:app --reload --port 8000
```

API available at `http://localhost:8000`. Health check: `GET /health`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App available at `http://localhost:5173`. The Vite dev server proxies `/api` to the backend.

## Usage

1. Open `http://localhost:5173`
2. Enter the GitHub repo URL (e.g., `https://github.com/owner/repo`)
3. Paste your GitHub token (stored in memory only — cleared on page reload)
4. Pick a start and end date (max 7 days apart)
5. Click "Start Investigation"

## API

### POST /api/investigate

```json
{
  "repoUrl": "https://github.com/owner/repo",
  "timeRange": {
    "start": "2024-01-15T10:00:00Z",
    "end": "2024-01-15T18:00:00Z"
  },
  "githubToken": "ghp_optional_user_token"
}
```

Returns an `IncidentReport` JSON with timeline, suspicious commits, root cause, rollback suggestions, and related issues.

### GET /health

Returns `{"status": "healthy"}`.

## Project Structure

```
├── backend/
│   ├── .env                        # Groq API key + optional GitHub token
│   ├── requirements.txt
│   └── app/
│       ├── main.py                 # FastAPI app + CORS
│       ├── config.py               # Settings from .env
│       ├── models.py               # Pydantic models
│       ├── routers/
│       │   └── investigate.py      # POST /api/investigate
│       └── services/
│           ├── input_validator.py  # URL + time range validation
│           ├── commit_fetcher.py   # GitHub commits + diffs
│           ├── issue_fetcher.py    # GitHub issues
│           ├── analysis_engine.py  # Groq AI prompt + call
│           └── report_generator.py # AI response → IncidentReport
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── index.css
│       ├── api/client.ts
│       ├── types/index.ts
│       ├── components/
│       │   ├── InvestigationForm.tsx
│       │   ├── IncidentReport.tsx
│       │   ├── Timeline.tsx
│       │   └── ErrorDisplay.tsx
│       └── pages/Home.tsx
└── README.md
```

## Security

- **GitHub tokens** provided via the UI are held in React state only (no localStorage, no cookies). On the backend, they exist in memory only for the duration of the request — never written to disk or logged.
- The server `.env` file is in `.gitignore`.
- CORS is restricted to localhost origins.

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq API key for AI analysis |
| `GROQ_MODEL` | No | Model to use (default: `llama-3.3-70b-versatile`) |
