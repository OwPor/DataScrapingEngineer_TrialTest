import requests
from playwright.sync_api import sync_playwright

URL = "https://scraping-trial-test.vercel.app/"

def get_recaptcha_token():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
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
                timeout=60000
            )
        except Exception:
            print("Timeout waiting for CAPTCHA solution.")
            browser.close()
            return None

        token = page.evaluate("document.querySelector('#g-recaptcha-response').value")
        print("Token retrieved successfully!")
        
        browser.close()
        return token

def make_request(token, search):
    if not token:
        print("Failed to get token.")
        return

    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': 'https://scraping-trial-test.vercel.app/search/results?q=silver',
        'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Microsoft Edge";v="144"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0',
        'x-recaptcha-token': token,
    }

    params = {
        'q': search,
        'page': '1',
    }

    response = requests.get('https://scraping-trial-test.vercel.app/api/search', params=params, headers=headers)
    
    try:
        data = response.json()
        open("api_response.json", "w").write(json.dumps(data, indent=2))
    except Exception:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    # Before everything else, enter the search query
    search = input("Enter search query: ")

    # Token only lasts temporarily, so we need the search query to be entered first
    token = get_recaptcha_token()
    if token and search:
        make_request(token, search)
