# AI Incident Timeline Correlator

A web application that correlates GitHub commit history with AWS CloudWatch logs and metrics to identify root causes of production incidents. Uses Amazon Bedrock Claude for intelligent analysis.

## Architecture

- **Backend**: Python FastAPI server handling data fetching, AI analysis, and report generation
- **Frontend**: React + TypeScript SPA with Vite for the investigation interface

## Prerequisites

- Python 3.11+
- Node.js 18+
- AWS credentials configured (for CloudWatch and Bedrock access)
- GitHub token (optional, for private repos or higher rate limits)

## Environment Variables

```bash
# AWS (configured via ~/.aws/credentials or environment)
export AWS_DEFAULT_REGION=us-east-1

# GitHub (optional - enables private repo access and higher rate limits)
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

## Running the Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Health check: `GET /health`.

## Running the Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The app will be available at `http://localhost:5173`. The Vite dev server proxies `/api` requests to the backend at port 8000.

## API Endpoints

### POST /api/investigate

Accepts an investigation request and returns a structured incident report.

**Request Body:**
```json
{
  "repoUrl": "https://github.com/owner/repo",
  "timeRange": {
    "start": "2024-01-15T10:00:00Z",
    "end": "2024-01-15T12:00:00Z"
  },
  "logGroupNames": ["/aws/lambda/my-function"],
  "metricQueries": [
    {
      "metricName": "CPUUtilization",
      "namespace": "AWS/EC2"
    }
  ]
}
```

**Alternative with CloudWatch Alarm:**
```json
{
  "repoUrl": "https://github.com/owner/repo",
  "alarmArn": "arn:aws:cloudwatch:us-east-1:123456789:alarm:high-cpu"
}
```

**Response:** An `IncidentReport` with timeline, suspicious commits, root cause, and rollback suggestions.

### GET /health

Returns service health status.

## Project Structure

```
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── main.py                 # FastAPI app entry point
│       ├── models.py               # Pydantic data models
│       ├── routers/
│       │   └── investigate.py      # /api/investigate endpoint
│       ├── services/
│       │   ├── input_validator.py  # Input validation
│       │   ├── time_window_resolver.py  # Alarm ARN → TimeWindow
│       │   ├── commit_fetcher.py   # GitHub commit fetching
│       │   ├── log_fetcher.py      # CloudWatch logs & metrics
│       │   ├── analysis_engine.py  # Bedrock Claude analysis
│       │   └── report_generator.py # Report structuring
│       └── utils/
│           └── retry.py            # Async retry with backoff
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx                # React entry point
│       ├── App.tsx                 # Root component
│       ├── index.css               # Global styles
│       ├── api/
│       │   └── client.ts           # Backend API client
│       ├── types/
│       │   └── index.ts            # TypeScript interfaces
│       ├── components/
│       │   ├── InvestigationForm.tsx
│       │   ├── IncidentReport.tsx
│       │   ├── Timeline.tsx
│       │   └── ErrorDisplay.tsx
│       └── pages/
│           └── Home.tsx
└── README.md
```

## How It Works

1. User submits a GitHub repo URL and time range (or CloudWatch alarm ARN)
2. Backend validates input and resolves the investigation time window
3. Commits and CloudWatch data are fetched in parallel
4. Combined data is sent to Amazon Bedrock Claude for analysis
5. AI response is structured into an incident report with:
   - Chronological timeline of correlated events
   - Suspicious commits with confidence scores
   - Root cause summary
   - Suggested rollback commands
