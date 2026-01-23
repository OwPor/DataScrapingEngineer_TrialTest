import sys
from BusinessSearchScraper import BusinessSearchScraper

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
