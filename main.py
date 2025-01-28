import argparse
import json
from selenium import webdriver
from amazon_scraper import AmazonScraper
from flipkart_scraper import FlipkartScraper
from cashify_scraper import CashifyScraper
from controlz_scraper import ControlzScraper

def load_platform_urls(filename="platform_urls.json"):
    """Load platform URLs from the configuration file"""
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except Exception as e:
        print(f"Error loading configuration file: {e}")
        return {}

def initialize_webdriver():
    """Initialize Chrome WebDriver with options"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)

def main():
    # Load platform URLs from the configuration file
    platform_urls = load_platform_urls()

    # Define the argument parser
    parser = argparse.ArgumentParser(description="Run scraper for a specific platform.")
    parser.add_argument(
        "-p", 
        "--platform", 
        type=str, 
        required=True, 
        help="Platform to scrape (Amazon, Flipkart, Cashify, Controlz)"
    )
    args = parser.parse_args()

    # Initialize Chrome WebDriver
    driver = initialize_webdriver()

    try:
        # Map platforms to their respective scraper classes
        scrapers = {
            "amazon": AmazonScraper(driver),
            "flipkart": FlipkartScraper(driver),
            "cashify": CashifyScraper(driver),
            "controlz": ControlzScraper(driver)
        }

        platform = args.platform.lower()

        # Run the scraper for the specified platform
        if platform in scrapers:
            scraper = scrapers[platform]
            platform_data = platform_urls.get(platform)

            if platform_data:
                print(f"\nFetching prices for {platform.title()}...")
                print("-" * 50)

                # Iterate through all products for the platform
                for product_name, url in platform_data.items():
                    try:
                        print(f"\nProcessing {product_name}...")
                        price = scraper.fetch_price(url)
                        if price:
                            print(f"✓ {product_name}: ₹{price}")
                        else:
                            print(f"✗ Failed to fetch price for {product_name}")
                    except Exception as e:
                        print(f"✗ Error processing {product_name}: {e}")

                print("\nScraping completed!")
            else:
                print(f"No URLs found for {platform} in configuration file.")
        else:
            print(f"Platform {platform} is not supported.")
            print(f"Supported platforms: {', '.join(scrapers.keys())}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()