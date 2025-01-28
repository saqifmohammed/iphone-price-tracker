from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_scraper import BaseScraper
from typing import Dict, Optional, Tuple
import re
import time

class FlipkartScraper(BaseScraper):
    def extract_product_info(self, url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        try:
            time.sleep(2)
            
            title_selectors = [
                "span.VU-ZEz",
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
                product_name = url.split('/')[-1].replace('-', ' ').title()
                return product_name, None, None
            
            full_title = title_element.text.strip()
            
            pattern = r"([\w\s]+)\s*\(([\w\s]+),\s*(\d+\s*[GT]B)\)"
            match = re.search(pattern, full_title)
            
            if match:
                product_name = match.group(1).strip()
                color = match.group(2).strip() 
                storage = match.group(3).strip().replace(" ", "")
                return product_name, storage, color
            else:
                storage_match = re.search(r'(\d+)\s*(?:GB|TB)', full_title, re.IGNORECASE)
                storage = f"{storage_match.group(1)}GB" if storage_match else None
                
                color_pattern = r'\(([\w\s]+)\)'
                color_match = re.search(color_pattern, full_title)
                color = color_match.group(1) if color_match else None
                
                product_name = re.sub(r'\(.*?\)', '', full_title).strip()
                return product_name, storage, color
                
        except Exception as e:
            print(f"Error extracting product info: {e}")
            return None, None, None

    def fetch_price(self, url: str) -> Optional[str]:
        try:
            self.driver.get(url)
            time.sleep(2)
            
            product_name, storage, color = self.extract_product_info(url)
            
            # Check for Notify Me button first
            try:
                notify_me = self.driver.find_element(By.CLASS_NAME, 'QqFHMw.AMnSvF.v6sqKe')
                if notify_me:
                    full_product_name = f"{product_name} ({storage})" if storage else product_name
                    self.save_to_sheets(full_product_name, "Out of stock", "Flipkart")
                    print(f"✓ Scraped: {full_product_name} - Out of stock")
                    return "Out of stock"
            except:
                pass
            
            price_selectors = [
                'div._30jeq3._16Jk6d',
                'div.Nx9bqj.CxhGGd',
                '._30jeq3', 
                '.product-price'
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
                
                try:
                    out_of_stock = self.driver.find_element(By.CLASS_NAME, '_16FRp0').text
                    if 'OUT OF STOCK' in out_of_stock.upper():
                        price = "Out of Stock"
                except:
                    pass

                full_product_name = f"{product_name} ({storage})" if storage else product_name
                self.save_to_sheets(full_product_name, price, "Flipkart")
                
                print(f"✓ Scraped: {full_product_name} - ₹{price}")
                return price
            
            print(f"Price not found for {product_name}")
            return None
                
        except Exception as e:
            print(f"Error fetching price from Flipkart: {e}")
            return None