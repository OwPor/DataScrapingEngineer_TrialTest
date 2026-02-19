from concurrent.futures import ThreadPoolExecutor, as_completed
from captcha_solver import CaptchaSolver, CaptchaSolverError
from api_client import APIClient, SessionExpiredError
from data_exporter import DataExporter

MAX_REAUTH_ATTEMPTS = 3
WORKERS = 3


class BusinessSearchScraper:

    def __init__(self, query, headless=True):
        self.query = query
        self.solver = CaptchaSolver(headless=headless)
        self.api = APIClient()
        self.exporter = DataExporter(query)

    def _authenticate(self):
        token = self.solver.solve()
        self.api.authenticate(token)

    def _fetch_and_collect(self, page):
        data = self.api.fetch_page(self.query, page)
        results = data.get('results', [])
        return page, results

    def run(self):
        print(f"\n[SCRAPER] Starting scrape for query: '{self.query}'")
        print(f"{'='*50}")

        self._authenticate()
        reauth_count = 0

        # Fetch page 1 first to discover totalPages
        try:
            data = self.api.fetch_page(self.query, 1)
        except Exception as e:
            print(f"[SCRAPER] Fatal error fetching page 1: {e}")
            self.exporter.save()
            return len(self.exporter.results)

        total_pages = data.get('totalPages', 1)
        total_results = data.get('totalResults', '?')
        new_count = self.exporter.add_results(data.get('results', []))
        print(f"[SCRAPER] Found {total_results} results across {total_pages} pages.")
        print(f"[SCRAPER] Page 1/{total_pages} — "
              f"{new_count} new, {len(self.exporter.results)} total")

        if total_pages <= 1:
            print("[SCRAPER] All pages scraped successfully.")
            self.exporter.save()
            self.exporter.verify_integrity()
            return len(self.exporter.results)

        # Fetch remaining pages concurrently
        remaining = list(range(2, total_pages + 1))
        current_workers = WORKERS

        while remaining and reauth_count <= MAX_REAUTH_ATTEMPTS:
            failed = []

            with ThreadPoolExecutor(max_workers=current_workers) as pool:
                futures = {
                    pool.submit(self._fetch_and_collect, p): p
                    for p in remaining
                }

                completed = {}
                for future in as_completed(futures):
                    page_num = futures[future]
                    try:
                        page_num, results = future.result()
                        completed[page_num] = results
                    except (SessionExpiredError, Exception) as e:
                        if not isinstance(e, SessionExpiredError):
                            print(f"[SCRAPER] Error on page {page_num}: {e}")
                        failed.append(page_num)

            for page_num in sorted(completed):
                new_count = self.exporter.add_results(completed[page_num])
                print(f"[SCRAPER] Page {page_num}/{total_pages} — "
                      f"{new_count} new, {len(self.exporter.results)} total")

            if not failed:
                break

            # Re-auth and retry failed pages with fewer workers
            reauth_count += 1
            if reauth_count > MAX_REAUTH_ATTEMPTS:
                print("[SCRAPER] Max re-authentication attempts reached. Saving partial data.")
                break

            current_workers = max(1, current_workers - 1)
            print(f"[SCRAPER] Session expired. Re-authenticating ({reauth_count}/{MAX_REAUTH_ATTEMPTS})... "
                  f"Reducing workers to {current_workers}.")
            try:
                self._authenticate()
                remaining = sorted(failed)
            except CaptchaSolverError as e:
                print(f"[SCRAPER] Re-authentication failed: {e}")
                break
        else:
            if not remaining or not failed:
                print("[SCRAPER] All pages scraped successfully.")

        self.exporter.save()
        self.exporter.verify_integrity()

        return len(self.exporter.results)
