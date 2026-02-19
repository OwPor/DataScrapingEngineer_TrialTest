import time
import random
import requests

BASE_URL = "https://scraping-trial-test.vercel.app"
API_URL = f"{BASE_URL}/api/search"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/134.0.0.0 Safari/537.36"
)
MAX_RETRIES = 3
MIN_DELAY = 1.0
MAX_DELAY = 3.0


class SessionExpiredError(Exception):
    pass


class APIClient:

    def __init__(self):
        self.session_id = None
        self.headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'referer': f'{BASE_URL}/',
            'user-agent': USER_AGENT,
        }

    def authenticate(self, recaptcha_token):
        print("[API] Authenticating with reCAPTCHA token...")
        auth_headers = self.headers.copy()
        auth_headers['x-recaptcha-token'] = recaptcha_token

        response = requests.get(
            API_URL,
            params={'q': 'test', 'page': '1'},
            headers=auth_headers,
            timeout=15,
        )

        if response.status_code != 200:
            raise Exception(
                f"Authentication failed: HTTP {response.status_code} — {response.text}"
            )

        data = response.json()
        session = data.get('session')
        if not session:
            raise Exception("Authentication response missing session ID")

        self.session_id = session
        self.headers['x-search-session'] = self.session_id
        print(f"[API] Session established: {self.session_id}")
        return data

    def fetch_page(self, query, page):
        if not self.session_id:
            raise Exception("Not authenticated — call authenticate() first")

        params = {'q': query, 'page': str(page)}

        for attempt in range(1, MAX_RETRIES + 1):
            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            time.sleep(delay)

            try:
                print(f"[API] Fetching page {page}...")
                response = requests.get(
                    API_URL,
                    params=params,
                    headers=self.headers,
                    timeout=15,
                )

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 403:
                    raise SessionExpiredError("Session expired (403)")

                if response.status_code >= 500:
                    wait = 2 ** attempt
                    print(f"[API] Server error {response.status_code}. "
                          f"Retry {attempt}/{MAX_RETRIES} in {wait}s...")
                    time.sleep(wait)
                    continue

                raise Exception(
                    f"Unexpected HTTP {response.status_code}: {response.text}"
                )

            except requests.RequestException as e:
                if attempt < MAX_RETRIES:
                    wait = 2 ** attempt
                    print(f"[API] Network error: {e}. "
                          f"Retry {attempt}/{MAX_RETRIES} in {wait}s...")
                    time.sleep(wait)
                else:
                    raise

        raise Exception(f"Failed to fetch page {page} after {MAX_RETRIES} retries")
