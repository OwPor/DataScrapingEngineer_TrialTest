## Data Scraping Engineer — Trial Test

Automated web scraper with **audio reCAPTCHA solving**, **API-first architecture**, and **dual-format output** (JSON + CSV).

### Architecture

```
main.py                  → CLI entry point
BusinessSearchScraper.py → Orchestrator
├── captcha_solver.py    → Audio reCAPTCHA solver (Vosk offline STT)
├── api_client.py        → Session management + HTTP data fetching
└── data_exporter.py     → CSV + JSON output with integrity checks
```

### Key Features

- **Audio reCAPTCHA Solving** — Uses Vosk (offline speech-to-text) to automatically solve reCAPTCHA v2 audio challenges. No AI APIs, no manual interaction, completely free.
- **API-First Architecture** — Playwright used only for CAPTCHA solving. All data extraction goes through the site's REST API using `requests`, making scraping fast and reliable.
- **One-Run Reliability** — Fully automated from start to finish. Auto re-authenticates on session expiry (up to 3 retries). Handles 5xx errors with exponential backoff.
- **Structured Output** — Outputs both `JSON` and `CSV` with deduplication, atomic writes, and post-export integrity verification. CSV uses BOM for Excel compatibility.

### Prerequisites

- Python 3.8+
- [FFmpeg](https://ffmpeg.org/download.html) (required by pydub for MP3→WAV conversion)
  - Windows: `winget install FFmpeg` or download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
  - Add to PATH

### Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

The Vosk speech model (~50 MB) downloads automatically on first run.

### Usage

```bash
# Default query "tech"
python main.py

# Custom query
python main.py "consulting"

# Visible browser (for debugging)
python main.py "tech" --no-headless
```

### Output

Results saved to `output/` directory:

**JSON** (`output/tech.json`):
```json
[
  {
    "business_name": "Silver Tech CORP",
    "registration_id": "SD0000001",
    "status": "Active",
    "filing_date": "1999-12-04",
    "agent_name": "Sara Smith",
    "agent_address": "1545 Maple Ave",
    "agent_email": "sara.smith...@example.com"
  }
]
```

**CSV** (`output/tech.csv`):
```
business_name,registration_id,status,filing_date,agent_name,agent_address,agent_email
Silver Tech CORP,SD0000001,Active,1999-12-04,Sara Smith,1545 Maple Ave,sara.smith...@example.com
```

### Design Choices

| Concern | Decision | Reasoning |
|---------|----------|-----------|
| CAPTCHA | Vosk offline STT | Free, no API keys, works offline, ~50 MB model |
| HTTP | `requests` library | Lightweight, fast, sufficient for REST API |
| Browser | Playwright (headless) | Only for CAPTCHA iframe. Not used for data extraction |
| Output | JSON + CSV, atomic writes | Prevents corrupt files if interrupted mid-write |
| Reliability | Auto re-auth + retry | Session expiry handled transparently |
