## Data Scraping Engineer – Trial Test

- **Automated Audio reCAPTCHA:** Uses `Playwright` combined with `Vosk` (offline speech-to-text) to automatically solve reCAPTCHA v2 audio challenges with zero manual interaction.

- **Reverse-Engineered API Architecture:** Bypasses brittle HTML parsing entirely. Uses `Playwright` strictly for the initial authentication, then switches to `requests` to extract data directly from the reverse-engineered internal REST APIs.

- **One-Run Reliability:** Fully automated from start to finish. Automatically self-heals by refreshing expired sessions (handling `403` and `5xx` errors) without restarting the script.

- **Structured Output:** Saves data cleanly in both `JSON` and `CSV` formats using atomic writes to ensure data integrity.

## Requirements

- Python 3.8+
- Playwright
- Requests
- Vosk & FFmpeg (for audio processing)
- Docker (Recommended for zero-setup execution)

## Installation

### Option 1: Docker (Recommended)

Everything is bundled (Python, FFmpeg, Chromium, Vosk model) for a zero-setup run.

```bash
docker build -t scraper .
docker run --rm -v "${PWD}/output:/app/output" scraper "tech"
```

### Option 2: Local Setup

**System Dependencies:** Ensure FFmpeg is installed and added to your system PATH.

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Install Playwright browsers:

```bash
playwright install chromium
```

## Usage

```bash
# Docker
docker run --rm -v "${PWD}/output:/app/output" scraper "tech"

# Local (defaults to "tech" if no query given)
python main.py
python main.py "consulting"
```

1. The script initializes a headless browser and navigates to the target site.
2. It automatically requests the audio challenge and solves it using the Vosk STT model.
3. Once the session token is captured, the browser closes.
4. The script directly queries the internal REST API to scrape all paginated results autonomously.

## Design Choices

- **API-First Architecture:** I used Playwright specifically to handle the dynamic reCAPTCHA v2 challenge and retrieve session cookies. Once authenticated, the script switches to Requests to hit the internal JSON endpoints. This avoids HTML parsing entirely, combining the reliability of a browser for login with the speed of an API for data extraction.

- **Fully Automated Audio Solver:** To ensure a true "one-run" execution, I replaced manual image puzzle solving with an automated audio-challenge workflow using Vosk. This handles the CAPTCHA entirely offline without needing paid third-party APIs.

- **Resilient Session Handling:** The solution includes a self-healing mechanism. If the session token expires during scraping, the script automatically pauses, re-authenticates to get a fresh token, and resumes exactly where it left off.

- **Data Integrity:** I implemented atomic writes for both the JSON and CSV outputs. This prevents file corruption if the scraper is ever forcefully stopped mid-write.

## Output

Data is saved to the `output/` directory (e.g., `output/tech.json` and `output/tech.csv`). The JSON format is:

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
