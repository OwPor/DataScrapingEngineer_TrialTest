import json
import time
import random
import requests
import os
import sys
from playwright.sync_api import sync_playwright

# Constants
BASE_URL = "https://scraping-trial-test.vercel.app"
API_URL = f"{BASE_URL}/api/search"
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
MAX_RETRIES = 3

class BusinessSearchScraper:

    def __init__(self, query):
        self.query = query
        self.filename = f"{query}.json"
        self.results = []
        self.seen_ids = set()
        self.page = 1
        self.session_id = None
        self.headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'referer': f'{BASE_URL}/',
            'user-agent': USER_AGENT,
        }

    def load_state(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    self.results = json.load(f)
                
                self.seen_ids = {item.get('registration_id') for item in self.results}
                self.page = (len(self.results) // 20) + 1
                print(f"Resuming from page {self.page} ({len(self.results)} results loaded).")
            except Exception as e:
                print(f"Could not load existing file ({e}). Starting fresh.")
        else:
            print("Starting fresh search.")

    def get_recaptcha_token(self):
        print("Launching browser to solve reCAPTCHA...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()
            
            try:
                page.goto(f"{BASE_URL}/")
                print("Waiting for reCAPTCHA...")

                try:
                    frame = page.frame_locator('iframe[src*="/api2/anchor"]')
                    checkbox = frame.locator('.recaptcha-checkbox-border')
                    checkbox.wait_for(timeout=10000)
                    checkbox.click()
                    print("Clicked reCAPTCHA checkbox.")
                except Exception:
                    print("Could not auto-click (checkbox might not be visible).")

                print("Please manually solve the CAPTCHA if presented...")
                
                page.wait_for_function(
                    "document.querySelector('#g-recaptcha-response') && document.querySelector('#g-recaptcha-response').value.length > 0",
                    timeout=120000
                )
                
                token = page.evaluate("document.querySelector('#g-recaptcha-response').value")
                print("Token acquired successfully.")
                browser.close()
                return token
                
            except Exception as e:
                print(f"Error getting token: {e}")
                browser.close()
                return None

    def refresh_session(self):
        print("Refreshing session...")
        token = self.get_recaptcha_token()
        if not token:
            raise Exception("Failed to retrieve reCAPTCHA token.")
        
        auth_headers = self.headers.copy()
        auth_headers['x-recaptcha-token'] = token
        auth_headers.pop('x-search-session', None)
        
        params = {'q': self.query, 'page': '1'}
        response = requests.get(API_URL, params=params, headers=auth_headers)
        
        if response.status_code == 200:
            data = response.json()
            new_session = data.get('session')
            if new_session:
                self.session_id = new_session
                self.headers['x-search-session'] = self.session_id
                print(f"New session established: {self.session_id}")
            else:
                print("Warning: No session ID returned in refresh response.")
        else:
            print(f"Failed to refresh session. Status: {response.status_code}")
            raise Exception(f"Session refresh failed: {response.status_code}")

    def fetch_page(self):
        attempts = 0
        while attempts < MAX_RETRIES:
            try:
                delay = random.uniform(1.0, 3.0)
                time.sleep(delay)
                
                params = {'q': self.query, 'page': str(self.page)}
                print(f"Fetching page {self.page}...")
                
                response = requests.get(API_URL, params=params, headers=self.headers, timeout=15)
                
                if response.status_code == 200:
                    return response.json()
                
                elif response.status_code == 403:
                    print("Session expired (403). Re-authenticating...")
                    try:
                        self.refresh_session()
                        attempts += 1
                        continue
                    except Exception as e:
                        print(f"Re-authentication failed: {e}")
                        break
                
                elif response.status_code >= 500:
                    print(f"Server error {response.status_code}. Retrying...")
                    attempts += 1
                    time.sleep(2 * attempts)
                    
                else:
                    print(f"Error {response.status_code}: {response.text}")
                    break

            except requests.RequestException as e:
                print(f"Network error: {e}")
                attempts += 1
                time.sleep(2)
        
        return None

    def process_and_save(self, data):
        new_results = []
        for item in data.get('results', []):
            reg_id = item.get("registrationId")
            if reg_id in self.seen_ids:
                continue

            agent = item.get("agent", {})
            record = {
                "business_name": item.get("businessName"),
                "registration_id": reg_id,
                "status": item.get("status"),
                "filing_date": item.get("filingDate"),
                "agent_name": agent.get("name"),
                "agent_address": agent.get("address"),
                "agent_email": agent.get("email")
            }
            new_results.append(record)
            self.seen_ids.add(reg_id)
        
        self.results.extend(new_results)
        
        temp_file = f"{self.filename}.tmp"
        with open(temp_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        os.replace(temp_file, self.filename)
        
        print(f"Processed {len(new_results)} items. Total saved: {len(self.results)}")

    def run(self):
        self.load_state()
        
        if not self.session_id:
             try:
                 print("Initializing session...")
                 self.refresh_session()
             except Exception:
                 print("Could not initialize session. Exiting.")
                 return

        while True:
            data = self.fetch_page()
            if not data:
                print("Failed to retrieve data. Stopping.")
                break
                
            self.process_and_save(data)
            
            total_pages = data.get('totalPages', 1)
            if self.page >= total_pages:
                print("Reached the last page. Scraping complete.")
                break
            
            self.page += 1

if __name__ == "__main__":
    try:
        query = input("Enter search query: ").strip()
        if not query:
            print("Query cannot be empty.")
            sys.exit(1)
            
        scraper = BusinessSearchScraper(query)
        scraper.run()
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user. Progress saved.")
        sys.exit(0)
