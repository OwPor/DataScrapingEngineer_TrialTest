- **Auto-Authentication**: Uses Playwright to solve reCAPTCHA v2 and retrieve session tokens.
- **Session Management**: Automatically refreshes expired sessions (handles `403` errors) without restarting the script.
- **Politeness**: Random delays between requests to mimic human behavior.
- **Clean Output**: Saves data in a structured JSON format with flattened fields.

## Requirements
- Python 3.7+
- Playwright
- Requests

## Installation


1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   ```

## Usage

Run the script:
```bash
python main.py
```

1. Enter your search query (e.g., `tech`).
2. A browser window will open.
3. If the "I'm not a robot" checkbox is not clicked automatically, click it.
4. Solve the image puzzle if challenged.
5. The browser will close automatically once the token is captured.
6. The script will proceed to scrape all pages.

## Output
Data is saved to `{query}.json` (e.g., `tech.json`). The format is:
```json
[
  {
    "business_name": "Silver Tech CORP",
    "registration_id": "SD0000001",
    "status": "Active",
    "filing_date": "1999-12-04",
    "agent_name": "Sara Smith",
    "agent_address": "1545 Maple Ave",
    "agent_email": "..."
  }
]
```
