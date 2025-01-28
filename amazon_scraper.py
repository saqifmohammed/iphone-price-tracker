from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_scraper import BaseScraper
from typing import Dict, Optional, Tuple
import re
import time
import traceback

class AmazonScraper(BaseScraper):
   def extract_product_info(self, url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
       """
       Extract product name, storage variant, and color from the Amazon product page
       """
       try:
           time.sleep(2)
           title_element = WebDriverWait(self.driver, 10).until(
               EC.presence_of_element_located((By.CSS_SELECTOR, "span#productTitle"))
           )
           print("Product title element found")
           
           if not title_element:
               print("Could not find product title")
               return None, None, None
               
           full_title = title_element.text.strip()
           print(f"Extracted title: {full_title}")
           
           if "iPhone" in full_title:
               model_match = re.search(r'iPhone\s+(\d+(?:\s+(?:Pro|Plus|mini|Pro Max))?)', full_title)
               if model_match:
                   product_name = model_match.group(0)
                   
                   storage_match = re.search(r'(\d+)\s*(TB|GB)', full_title, re.IGNORECASE)
                   if storage_match:
                       storage_size = storage_match.group(1)
                       storage_unit = storage_match.group(2).upper()
                       storage = f"{storage_size}{storage_unit}"
                   else:
                       storage = None
                   
                   color_match = re.search(r'\(([\w\s]+)\)', full_title)
                   color = color_match.group(1) if color_match else None
                   
                   print(f"Extracted iPhone info - Model: {product_name}, Storage: {storage}, Color: {color}")
                   return product_name, storage, color

           storage_match = re.search(r'(\d+)\s*(TB|GB)', full_title, re.IGNORECASE)
           if storage_match:
               storage_size = storage_match.group(1)
               storage_unit = storage_match.group(2).upper()
               storage = f"{storage_size}{storage_unit}"
           else:
               storage = None
           
           color_match = re.search(r'\(([\w\s]+)\)', full_title)
           color = color_match.group(1) if color_match else None
           
           product_name = re.sub(r'\(.*?\)', '', full_title).strip()
           print(f"Extracted generic product info - Name: {product_name}, Storage: {storage}, Color: {color}")
           return product_name, storage, color
               
       except Exception as e:
           print(f"Error extracting product info: {str(e)}")
           traceback.print_exc()
           return None, None, None

   def _check_out_of_stock(self) -> bool:
       """Check if the product is out of stock using various indicators"""
       out_of_stock_selectors = [
           '#availability .a-color-price',
           '#outOfStock',
           '.a-color-price.a-text-bold',
           '.a-size-medium.a-color-price',
           '#availability span'
       ]
       
       try:
           for selector in out_of_stock_selectors:
               elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
               for element in elements:
                   text = element.text.lower()
                   if any(phrase in text for phrase in [
                       'currently unavailable',
                       'out of stock',
                       'not available',
                       'discontinued'
                   ]):
                       return True
           return False
       except Exception:
           return False

   def fetch_price(self, url: str) -> str:
       """
       Fetch price from Amazon product page with error handling and debugging
       """
       try:
           print(f"\nProcessing URL: {url}")
           self.driver.get(url)
           print("Successfully loaded page")
           
           try:
               WebDriverWait(self.driver, 10).until(
                   EC.presence_of_element_located((By.CSS_SELECTOR, "span#productTitle"))
               )
               print("Page fully loaded")
           except Exception as e:
               print(f"Error waiting for page load: {str(e)}")
               return "Error: Page load timeout"

           product_name, storage, color = self.extract_product_info(url)
           if not product_name:
               print("Failed to extract product info")
               return "Error: Could not extract product info"
               
           full_name = f"{product_name} ({storage})" if storage else product_name
           print(f"Processing product: {full_name}")

           # Updated price selectors
           price_selectors = [
               '.a-price[data-a-color="price"] .a-offscreen',
               '.a-price .a-offscreen',
               '.a-price[data-a-color="base"] .a-offscreen',
               'span[data-a-color="price"] .a-offscreen',
               '#priceblock_ourprice',
               '.a-size-medium.a-color-price'
           ]
           
           print("Attempting to find price...")
           for selector in price_selectors:
               try:
                   print(f"Trying selector: {selector}")
                   price_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                   
                   for price_tag in price_elements:
                       price_text = price_tag.get_attribute('textContent').strip()
                       print(f"Found price text: {price_text}")
                       
                       if price_text and '₹' in price_text:
                           price = price_text.replace(",", "").replace("₹", "").strip()
                           print(f"Cleaned price: {price}")
                           
                           if price.isdigit():
                               self.save_to_sheets(full_name, price, "Amazon")
                               print(f"✓ Successfully saved: {full_name} - ₹{price}")
                               return price
               except Exception as e:
                   print(f"Selector {selector} failed: {str(e)}")
                   continue

           print("No price found, checking if out of stock...")
           if self._check_out_of_stock():
               self.save_to_sheets(full_name, "Out of stock", "Amazon")
               print(f"✓ {full_name}: Out of stock")
               return "Out of stock"

           self.save_to_sheets(full_name, "Out of stock", "Amazon")
           print(f"✓ {full_name}: Out of stock (No price found)")
           return "Out of stock"

       except Exception as e:
           print(f"Error in fetch_price: {str(e)}")
           traceback.print_exc()
           return "Error: Could not fetch price"

   def __del__(self):
       """
       Clean up the driver when the scraper is destroyed
       """
       try:
           if hasattr(self, 'driver'):
               self.driver.quit()
       except:
           pass