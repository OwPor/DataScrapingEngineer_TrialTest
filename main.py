import json
import requests
from playwright.sync_api import sync_playwright

URL = "https://scraping-trial-test.vercel.app/"
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
def get_recaptcha_token():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=USER_AGENT
        )
        page = context.new_page()
        
        page.goto(URL)

        print("Waiting for reCAPTCHA...")
        
        try:
            frame_locator = page.frame_locator('iframe[src*="/api2/anchor"]')
            checkbox = frame_locator.locator('.recaptcha-checkbox-border')
            
            checkbox.wait_for(timeout=10000)
            print("Found checkbox, clicking...")
            checkbox.click()
        except Exception as e:
            print(f"Auto-click failed (might not be needed or frame different): {e}")

        print("Please solve the CAPTCHA manually if the challenge appears...")
        
        try:
            page.wait_for_function(
                "document.querySelector('#g-recaptcha-response') && document.querySelector('#g-recaptcha-response').value.length > 0",
                timeout=120000
            )
        except Exception:
            print("Timeout waiting for CAPTCHA solution.")
            browser.close()
            return None

        token = page.evaluate("document.querySelector('#g-recaptcha-response').value")
        print("Token retrieved successfully!")
        
        browser.close()
        return token

def make_request(search_query):
    current_page = 1
    all_results = []
    session_id = None
    
    print(f"Getting initial token...")
    token = get_recaptcha_token()
    if not token:
        print("Failed to get token.")
        return

    while True:
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://scraping-trial-test.vercel.app/',
            'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Microsoft Edge";v="144"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': USER_AGENT,
        }

        if current_page == 1:
            headers['x-recaptcha-token'] = token
        elif session_id:
            headers['x-search-session'] = session_id
        else:
            print("Error: No session ID found for pagination.")
            break

        params = {
            'q': search_query,
            'page': str(current_page),
        }

        print(f"Fetching page {current_page}...")
        response = requests.get('https://scraping-trial-test.vercel.app/api/search', params=params, headers=headers)

        


        if response.status_code == 200:
            data = response.json()
            
            if current_page == 1:
                session_id = data.get('session')
                if session_id:
                    print(f"Session established: {session_id}")
                else:
                    print("Warning: No session ID returned in page 1 response.")

            for item in data.get('results', []):

                agent_info = item.get("agent", {})
                all_results.append({
                    "business_name": item.get("businessName"),
                    "registration_id": item.get("registrationId"),
                    "status": item.get("status"),
                    "filing_date": item.get("filingDate"),
                    "agent_name": agent_info.get("name"),
                    "agent_address": agent_info.get("address"),
                    "agent_email": agent_info.get("email")
                })
            
            filename = f"{search_query}.json"
            with open(filename, "w") as f:
                f.write(json.dumps(all_results, indent=2))
            
            print(f"Page {current_page} processed. Total results so far: {len(all_results)}. Saved to {filename}")

            if current_page >= data.get('totalPages', 1):
                print("Reached the last page. Stopping.")
                break
            
            current_page += 1            
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            break

if __name__ == "__main__":
    search_query = input("Enter search query: ")
    if search_query:
        make_request(search_query)
