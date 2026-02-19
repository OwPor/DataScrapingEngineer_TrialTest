import sys
import time
from captcha_solver import CaptchaSolver, CaptchaSolverError
from api_client import APIClient, SessionExpiredError
from data_exporter import DataExporter

MAX_REAUTH_ATTEMPTS = 3


class BusinessSearchScraper:

    def __init__(self, query, headless=True):
        self.query = query
        self.solver = CaptchaSolver(headless=headless)
        self.api = APIClient()
        self.exporter = DataExporter(query)

    def _authenticate(self):
        token = self.solver.solve()
        self.api.authenticate(token)

    def run(self):
        print(f"\n[SCRAPER] Starting scrape for query: '{self.query}'")
        print(f"{'='*50}")

        self._authenticate()

        page = 1
        total_pages = None
        reauth_count = 0

        while True:
            try:
                data = self.api.fetch_page(self.query, page)
            except SessionExpiredError:
                reauth_count += 1
                if reauth_count > MAX_REAUTH_ATTEMPTS:
                    print("[SCRAPER] Max re-authentication attempts reached. Saving partial data.")
                    break
                print(f"[SCRAPER] Re-authenticating ({reauth_count}/{MAX_REAUTH_ATTEMPTS})...")
                try:
                    self._authenticate()
                    continue
                except CaptchaSolverError as e:
                    print(f"[SCRAPER] Re-authentication failed: {e}")
                    break
            except Exception as e:
                print(f"[SCRAPER] Fatal error fetching page {page}: {e}")
                break

            results = data.get('results', [])
            new_count = self.exporter.add_results(results)

            if total_pages is None:
                total_pages = data.get('totalPages', 1)
                total_results = data.get('totalResults', '?')
                print(f"[SCRAPER] Found {total_results} results across {total_pages} pages.")

            print(f"[SCRAPER] Page {page}/{total_pages} — "
                  f"{new_count} new, {len(self.exporter.results)} total")

            if page >= total_pages:
                print("[SCRAPER] All pages scraped successfully.")
                break

            page += 1

        self.exporter.save()
        self.exporter.verify_integrity()

        return len(self.exporter.results)