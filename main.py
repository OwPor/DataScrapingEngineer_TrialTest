import sys
from BusinessSearchScraper import BusinessSearchScraper

DEFAULT_QUERY = "tech"


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_QUERY
    headless = "--no-headless" not in sys.argv

    print(f"Data Scraping Engineer — Trial Test")
    print(f"Query: '{query}' | Headless: {headless}")
    print()

    scraper = BusinessSearchScraper(query, headless=headless)

    try:
        count = scraper.run()
        print(f"Done. {count} records scraped.")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\nInterrupted. Saving partial results...")
        scraper.exporter.save()
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        if scraper.exporter.results:
            print("Saving partial results before exit...")
            scraper.exporter.save()
        sys.exit(1)


if __name__ == "__main__":
    main()
