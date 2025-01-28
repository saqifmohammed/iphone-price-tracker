import os
from datetime import datetime
from typing import Dict, Optional, Union
import re
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

class BaseScraper:
    def __init__(self, driver):
        self.driver = driver
        self.spreadsheet_id = "1dIIM6lmDfX0HhK5L5TFWnThr3TWzBAJ1kmP30632_9k"  # Your shared spreadsheet ID
        self.sheet_id = "0"  # The gid from your URL
        self.sheets_service = self._initialize_sheets_service()

    def _initialize_sheets_service(self):
        """Initialize and return Google Sheets service"""
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=8080)
            with open("token.json", "w") as token:
                token.write(creds.to_json())

        try:
            service = build("sheets", "v4", credentials=creds)
            return service.spreadsheets()
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def format_product_name(self, product: str) -> str:
        """Format product name to maintain consistency"""
        try:
            # Remove any URL query parameters if present
            product = product.split('?')[0]
            
            # Remove any variant information from URL
            product = product.split('variant=')[0]
            
            # Clean up the name
            product = product.strip()
            
            # Fix iPhone capitalization
            product = product.replace('Iphone', 'iPhone')
            product = product.replace('iphone', 'iPhone')
            
            # Fix XR capitalization
            product = product.replace('Xr', 'XR')
            
            # Format storage information if present
            storage_match = re.search(r'\((\d+\s*(?:GB|TB))\)', product, re.IGNORECASE)
            if storage_match:
                storage = storage_match.group(1).upper().replace(' ', '')
                # Remove the old storage format and add the standardized one
                product = re.sub(r'\s*\(\d+\s*(?:GB|TB)\)', '', product, flags=re.IGNORECASE)
                product = f"{product} ({storage})"
            
            # Ensure "Apple" prefix is present and properly formatted
            if not product.startswith('Apple'):
                product = f"Apple {product}"
            
            # Remove any double spaces
            product = ' '.join(product.split())
            
            return product
            
        except Exception as e:
            print(f"Error formatting product name: {e}")
            return product

    def fetch_price(self, url: str) -> Optional[str]:
        """Base method for fetching price from a URL"""
        raise NotImplementedError("Subclasses must implement the fetch_price method")

    def load_existing_data(self) -> Dict[str, Dict[str, str]]:
        """Load existing data from Google Sheet"""
        existing_data = {}
        try:
            # Get all values from the sheet
            result = self.sheets_service.values().get(
                spreadsheetId=self.spreadsheet_id,
                range="A1:ZZ1000"
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return existing_data

            # First row contains headers (Product and dates)
            headers = values[0]
            
            # Process each row
            for row in values[1:]:
                product_name = self.format_product_name(row[0])
                if product_name not in existing_data:
                    existing_data[product_name] = {}
                
                # Add prices for each date
                for i, price in enumerate(row[1:], 1):
                    if i < len(headers):
                        existing_data[product_name][headers[i]] = price

            return existing_data

        except HttpError as error:
            print(f"Error loading data from Google Sheets: {error}")
            return existing_data

    def _ensure_sheet_exists(self, sheet_name: str) -> None:
        """Ensure the sheet exists, create if it doesn't"""
        try:
            # Get spreadsheet metadata
            spreadsheet = self.sheets_service.get(spreadsheetId=self.spreadsheet_id).execute()
            
            # Check if sheet exists
            sheet_exists = any(sheet['properties']['title'] == sheet_name 
                             for sheet in spreadsheet['sheets'])
            
            if not sheet_exists:
                # Create new sheet request
                request = {
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }
                
                body = {'requests': [request]}
                response = self.sheets_service.batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body=body
                ).execute()
                print(f"Created new sheet: {sheet_name}")
                
        except HttpError as error:
            print(f"Error ensuring sheet exists: {error}")

    def save_to_sheets(self, product: str, price: Union[str, int, float], platform: str) -> None:
        """Save or update product price in Google Sheet"""
        try:
            # Format the product name
            formatted_product = self.format_product_name(product)
            
            # Use platform name as sheet name
            sheet_name = f"{platform.lower()}_prices"
            
            # Ensure the sheet exists
            self._ensure_sheet_exists(sheet_name)
            
            # Get today's date
            today = datetime.now().strftime("%Y-%m-%d")
            
            try:
                # Get existing data from the sheet
                result = self.sheets_service.values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{sheet_name}!A1:ZZ1000"
                ).execute()
                
                existing_data = {}
                values = result.get('values', [])
                existing_headers = values[0] if values else ["Product"]
                
                # Process existing data
                for row in values[1:]:
                    product_name = self.format_product_name(row[0])
                    existing_data[product_name] = {}
                    for i, price_val in enumerate(row[1:], 1):
                        if i < len(existing_headers):
                            existing_data[product_name][existing_headers[i]] = price_val
                
            except HttpError:
                existing_data = {}
                existing_headers = ["Product"]
            
            # Add or update the new price
            if formatted_product not in existing_data:
                existing_data[formatted_product] = {}
            existing_data[formatted_product][today] = str(price)
            
            # Get all unique dates including today
            all_dates = sorted(set(
                date 
                for product_data in existing_data.values() 
                for date in product_data.keys()
            ) | {today})
            
            # Prepare header and data
            headers = ["Product"] + all_dates
            rows = [headers]
            
            # Add data rows
            for product_name, prices in existing_data.items():
                row = [product_name]
                for date in all_dates:
                    row.append(prices.get(date, ""))
                rows.append(row)
            
            # Update the sheet
            sheet_range = f"{sheet_name}!A1"
            self.sheets_service.values().update(
                spreadsheetId=self.spreadsheet_id,
                range=sheet_range,
                valueInputOption="RAW",
                body={"values": rows}
            ).execute()
            
            print(f"✓ Updated price for {formatted_product} in {sheet_name}")
            
        except HttpError as error:
            print(f"✗ Error saving data for {product}: {error}")

# Example usage:
# scraper = BaseScraper(driver, "your-spreadsheet-id-here")
# scraper.save_to_sheets("iPhone 14 Pro (256GB)", "999.99", "Amazon")