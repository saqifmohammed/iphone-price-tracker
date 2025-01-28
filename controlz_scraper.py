from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_scraper import BaseScraper
from typing import Dict, Optional, Tuple
import re
import time

class ControlzScraper(BaseScraper):
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
                "a.product__title h2.h1",
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
            
            #Variant Selector
            variant_selectors = [
                'div.var_container input[type="radio"]:not([disabled]) + label',
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
            
            full_title = title_element.get_attribute('textContent').strip()
            variant_text = variant_element.text.strip()
            
            # Pattern to match product details: name (color, storage)

            if full_title and variant_text:
                print(full_title)
                print(variant_text)
                return full_title, variant_text, " "
            else:
                # Fallback pattern matching
                storage_match = re.search(r'(\d+)\s*(?:GB|TB)', full_title, re.IGNORECASE)
                storage = f"{storage_match.group(1)}GB" if storage_match else None
                
                color_pattern = r'\(([\w\s]+)\)'
                color_match = re.search(color_pattern, full_title)
                color = color_match.group(1) if color_match else None
                
                # Clean product name
                product_name = re.sub(r'\(.*?\)', '', full_title).strip()
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
            
            # Try multiple possible selectors for price
            price_selectors = [
                '.price__sale .price-item--sale',
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

            if price_tag and product_name:
                price = price_tag.text.strip().replace(",", "").replace("₹", "")
                
                # Format full product name with color and storage
                if storage:
                    full_product_name = f"{product_name} ({storage})"
                else:
                    full_product_name = f"{product_name}"
                
                # Save to CSV
                self.save_to_sheets(full_product_name, price, "Controlz")
                print(f"✓ Successfully scraped: {full_product_name} - ₹{price}")
                return price
            
            else:
                print(f"Could not find price element for {product_name}")
                return None
                
        except Exception as e:
            print(f"Error fetching price from Controlz: {e}")
        return None