from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_scraper import BaseScraper
from typing import Dict, Optional, Tuple
import re
import time

class CashifyScraper(BaseScraper):
    def check_availability(self, url: str) -> bool:
        """
        Check if the product is in stock
        
        Args:
            url (str): Product URL
            
        Returns:
            bool: True if product is available, False if out of stock or error
        """
        try:
            # Try to find either "Buy Now" button or "Notify Me" span
            buy_now_selector = 'h2.h2'
            notify_selector = 'span.text-primary-text-contrast.text-md'
            
            try:
                # Check for Buy Now first
                buy_button = WebDriverWait(self.driver, 2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, buy_now_selector))
                )
                if buy_button and "Buy Now" in buy_button.text:
                    return True
            except:
                pass
                
            try:
                # Check for Notify Me
                notify_span = WebDriverWait(self.driver, 2).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, notify_selector))
                )
                if notify_span and "Notify Me" in notify_span.text:
                    return False
            except:
                pass
            
            # If we find a price tag, consider it available
            price_tag = self.driver.find_element(By.CSS_SELECTOR, 'span.h1[itemprop="price"]')
            if price_tag and '₹' in price_tag.text:
                return True
                
            return False
            
        except Exception as e:
            print(f"Error checking availability: {e}")
            # If we're unsure, assume it's available if we can find a price
            try:
                price_tag = self.driver.find_element(By.CSS_SELECTOR, 'span.h1[itemprop="price"]')
                return bool(price_tag and '₹' in price_tag.text)
            except:
                return False

    def extract_product_info(self, url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extract product name, storage variant, and color from the page
        
        Args:
            url (str): Product URL
            
        Returns:
            Tuple[Optional[str], Optional[str], Optional[str]]: (product_name, storage_variant, color)
        """
        try:
            time.sleep(2)  # Wait for page load
            
            # Try multiple possible selectors for the title
            title_selectors = [
                "h3.h3.line-clamp-2",
            ]
            
            title_element = None
            for selector in title_selectors:
                try:
                    title_element = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if title_element:
                        break
                except:
                    continue
                    
            if not title_element:
                # Fallback to URL-based extraction
                product_name = url.split('/')[-1].replace('-', ' ').title()
                return product_name, None, None
            
            variant_selectors = [
                "div.body2.mb-2.text-surface-text",
            ]
            
            variant_element = None
            for selector in variant_selectors:
                try:
                    variant_element = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if variant_element:
                        break
                except:
                    continue
            
            if not variant_element:
                # Fallback to URL-based extraction
                product_name = url.split('/')[-1].replace('-', ' ').title()
                return product_name, None, None
            
            full_title = title_element.text.strip() + " | " + variant_element.text.strip()
            
            # Clean up redundant text
            full_title = full_title.replace("Apple iPhone", "iPhone")
            full_title = re.sub(r"iPhone\s+iPhone", "iPhone", full_title)
            
            # Extract basic iPhone model number
            # More specific pattern that handles Pro Max first
            iphone_pattern = r"iPhone\s+(\d+(?:\s*(?:Pro\s*Max|Pro|Plus|mini)?)\s*(?:-\s*Refurbished)?)"
            iphone_match = re.search(iphone_pattern, full_title, re.IGNORECASE)
            
            if iphone_match:
                model = iphone_match.group(1).strip()
                # Ensure proper spacing for Pro Max
                model = re.sub(r'Pro\s*Max', 'Pro Max', model, flags=re.IGNORECASE)
                # Ensure proper spacing for other variants
                model = re.sub(r'Pro', 'Pro', model, flags=re.IGNORECASE)
                product_name = f"iPhone {model}"
                # Remove "Refurbished" from product name
                product_name = re.sub(r'\s*-\s*Refurbished', '', product_name)
            else:
                product_name = "iPhone"  # fallback
            
            # Try to extract both RAM and storage
            storage = None
            
            # First try to match pattern with RAM and storage
            ram_storage_pattern = r"(\d+)\s*GB\s*RAM\s*/\s*(\d+)\s*(?:GB|TB)"
            storage_match = re.search(ram_storage_pattern, full_title)
            
            if storage_match:
                storage_size = storage_match.group(2)
                # Determine if it's TB or GB
                if re.search(rf"{storage_size}\s*TB", full_title, re.IGNORECASE):
                    storage = f"{storage_size}TB"
                else:
                    storage = f"{storage_size}GB"
            else:
                # Try to find standalone storage pattern (avoid matching RAM)
                storage_pattern = r"(?<!RAM\s)(\d+)\s*(TB|GB)(?:\s*storage|\s*$|\s*,)"
                storage_match = re.search(storage_pattern, full_title, re.IGNORECASE)
                if storage_match:
                    size = storage_match.group(1)
                    unit = storage_match.group(2).upper()
                    storage = f"{size}{unit}"
                
            # Extract color
            color_pattern = r',\s*([^,\|]+?)(?:\s*\(|$)'
            color_match = re.search(color_pattern, full_title)
            color = color_match.group(1).strip() if color_match else None
            
            return product_name, storage, color
                
        except Exception as e:
            print(f"Error extracting product info: {e}")
            return None, None, None

    def fetch_price(self, url: str) -> Optional[str]:
        """
        Fetch price from the product page
        
        Args:
            url (str): Product URL
            
        Returns:
            Optional[str]: Price if found, None otherwise
        """
        try:
            self.driver.get(url)
            time.sleep(2)  # Wait for page to load
            
            # Extract product info
            product_name, storage, color = self.extract_product_info(url)
            
            # Check availability
            is_available = self.check_availability(url)
            
            # Try multiple possible selectors for price
            price_selectors = [
                'span.h1[itemprop="price"]',
            ]
            
            price_tag = None
            for selector in price_selectors:
                try:
                    price_tag = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if price_tag and '₹' in price_tag.text:
                        break
                except:
                    continue
            
            if product_name:
                # Format full product name with storage
                if storage:
                    full_product_name = f"{product_name} ({storage})"
                else:
                    full_product_name = product_name
                
                if is_available and price_tag:
                    # If available, use the actual price
                    price = price_tag.text.strip().replace(",", "").replace("₹", "")
                else:
                    # If not available, set price as "Out of Stock"
                    price = "Out of Stock"
                
                # Save to Google Sheets
                self.save_to_sheets(full_product_name, price, "Cashify")
                print(f"✓ Successfully scraped: {full_product_name} - {price}")
                return price
            
            else:
                print(f"Could not find price element for {product_name}")
                return None
                
        except Exception as e:
            print(f"Error fetching price from Cashify: {e}")
            return None