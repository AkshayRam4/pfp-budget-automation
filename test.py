#!/usr/bin/env python3
"""
Fully Automated Google Sheets Updater
Directly updates Google Sheets with scraped sign counts using Google Sheets API
"""

import requests
import json
import time
import sys
import argparse
import csv
from urllib.parse import urlparse
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os.path
import pickle

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_google_sheets_service():
    """Get authenticated Google Sheets service"""
    creds = None
    # The file token.pickle stores the user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("🔄 Refreshing expired token...")
                creds.refresh(Request())
                print("✅ Token refreshed successfully!")
            except Exception as e:
                print(f"❌ Token refresh failed: {e}")
                print("🔄 Starting fresh authentication...")
                creds = None
        
        if not creds:
            if not os.path.exists('credentials.json'):
                print("Google Sheets authentication required...")
                print("Please follow these steps:")
                print("1. Go to https://console.cloud.google.com/")
                print("2. Create a new project or select existing one")
                print("3. Enable Google Sheets API")
                print("4. Create credentials (OAuth 2.0 Client ID)")
                print("5. Download the credentials JSON file")
                print("6. Save it as 'credentials.json' in this folder")
                print("\nAfter setting up credentials, run this script again.")
                return None
            
            # Start OAuth flow
            print("🔐 Starting OAuth authentication...")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0, open_browser=False)
            print("✅ Authentication successful!")
        
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
        print("💾 Credentials saved for future use")
    
    try:
        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        print(f"❌ Error creating Google Sheets service: {e}")
        return None

def scrape_with_selenium(url):
    """Scrape signature count using Selenium"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        import time
        import re
        import os
        import shutil
    except ImportError:
        print("Selenium not installed. Please run: pip install selenium webdriver-manager")
        return None
    
    try:
        # Setup Chrome driver
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Clear any cached drivers and force fresh download
        cache_dir = os.path.expanduser("~/.wdm")
        if os.path.exists(cache_dir):
            try:
                shutil.rmtree(cache_dir)
                print("🧹 Cleared old driver cache")
            except:
                pass
        
        # Try to use system ChromeDriver first (for GitHub Actions)
        system_chromedriver = "/usr/local/bin/chromedriver"
        print(f"Checking for system ChromeDriver at: {system_chromedriver}")
        print(f"File exists: {os.path.exists(system_chromedriver)}")
        if os.path.exists(system_chromedriver):
            print(f"File is executable: {os.access(system_chromedriver, os.X_OK)}")
        
        if os.path.exists(system_chromedriver) and os.access(system_chromedriver, os.X_OK):
            print(f"✅ Using system ChromeDriver at: {system_chromedriver}")
            service = Service(system_chromedriver)
        else:
            # Fallback to webdriver-manager
            print("❌ System ChromeDriver not found or not executable, using webdriver-manager...")
            try:
                driver_path = ChromeDriverManager().install()
                print(f"Using ChromeDriver at: {driver_path}")
                
                # Verify the driver is executable and not corrupted
                if not os.access(driver_path, os.X_OK):
                    print(f"Making driver executable: {driver_path}")
                    os.chmod(driver_path, 0o755)
                
                # Check if the file is actually a ChromeDriver binary (not a text file)
                if 'THIRD_PARTY_NOTICES' in driver_path or not driver_path.endswith('chromedriver'):
                    print(f"❌ ChromeDriver path looks corrupted: {driver_path}")
                    raise Exception("ChromeDriver path is corrupted")
                
                service = Service(driver_path)
            except Exception as e:
                print(f"❌ ChromeDriver setup failed: {e}")
                raise e
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        print(f"Scraping: {url}")
        driver.get(url)
        
        # Handle chng.it redirects
        if 'chng.it' in url:
            print("Following chng.it redirect...")
            time.sleep(3)  # Wait for redirect
            current_url = driver.current_url
            print(f"Redirected to: {current_url}")
        
        # Wait for page to load
        time.sleep(5)
        
        # Get page source and look for signature count in JavaScript data
        page_source = driver.page_source
        
        # Try to extract from JavaScript data (most accurate)
        js_signature_patterns = [
            r'"signatureCount":\s*{\s*"displayed":\s*(\d+),',
            r'"signatureCount":\s*{\s*"total":\s*(\d+),',
            r'"signatureState":\s*{\s*"signatureCount":\s*{\s*"total":\s*(\d+),',
            r'"signatureState":\s*{\s*"signatureCount":\s*{\s*"displayed":\s*(\d+),'
        ]
        
        for pattern in js_signature_patterns:
            matches = re.findall(pattern, page_source)
            if matches:
                signature_count = int(matches[0])
                print(f"Found signature count in JavaScript data: {signature_count:,}")
                driver.quit()
                return signature_count
        
        # If no JavaScript data found, try text patterns
        signature_patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*signatures?',
            r'(\d{1,3}(?:,\d{3})*)\s*people\s*signed',
            r'(\d{1,3}(?:,\d{3})*)\s*supporters',
            r'data-signature-count="(\d+)"',
            r'signature-count[^>]*>(\d+)',
            r'petition-signatures[^>]*>(\d+)'
        ]
        
        for pattern in signature_patterns:
            matches = re.findall(pattern, page_source, re.IGNORECASE)
            if matches:
                # Get the largest number that could be a signature count
                valid_numbers = []
                for match in matches:
                    num = int(match.replace(',', ''))
                    if 1 <= num <= 1000000:  # Reasonable range for signatures
                        valid_numbers.append(num)
                
                if valid_numbers:
                    largest = max(valid_numbers)
                    print(f"Found signature count in page text: {largest:,}")
                    driver.quit()
                    return largest
        
        print("No signature count found")
        driver.quit()
        return None
        
    except Exception as e:
        print(f"❌ Error scraping with Selenium: {e}")
        try:
            driver.quit()
        except:
            pass
        
        # Fallback: try with requests if Selenium fails
        print("🔄 Trying fallback method with requests...")
        return scrape_with_requests_fallback(url)

def scrape_with_requests_fallback(url):
    """Fallback scraping method using requests (for GitHub Actions)"""
    try:
        import re
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        print(f"Fallback scraping: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Handle chng.it redirects
        if 'chng.it' in url and response.url != url:
            print(f"Following redirect to: {response.url}")
            response = requests.get(response.url, headers=headers, timeout=30)
            response.raise_for_status()
        
        page_content = response.text
        
        # Try to extract from JavaScript data (most accurate)
        js_signature_patterns = [
            r'"signatureCount":\s*{\s*"displayed":\s*(\d+),',
            r'"signatureCount":\s*{\s*"total":\s*(\d+),',
            r'"signatureState":\s*{\s*"signatureCount":\s*{\s*"total":\s*(\d+),',
            r'"signatureState":\s*{\s*"signatureCount":\s*{\s*"displayed":\s*(\d+),'
        ]
        
        for pattern in js_signature_patterns:
            matches = re.findall(pattern, page_content)
            if matches:
                signature_count = int(matches[0])
                print(f"Found signature count in JavaScript data: {signature_count:,}")
                return signature_count
        
        # If no JavaScript data found, try text patterns
        signature_patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*signatures?',
            r'(\d{1,3}(?:,\d{3})*)\s*people\s*signed',
            r'(\d{1,3}(?:,\d{3})*)\s*supporters',
            r'data-signature-count="(\d+)"',
            r'signature-count[^>]*>(\d+)',
            r'petition-signatures[^>]*>(\d+)'
        ]
        
        for pattern in signature_patterns:
            matches = re.findall(pattern, page_content, re.IGNORECASE)
            if matches:
                # Get the largest number that could be a signature count
                valid_numbers = []
                for match in matches:
                    num = int(match.replace(',', ''))
                    if 1 <= num <= 1000000:  # Reasonable range for signatures
                        valid_numbers.append(num)
                
                if valid_numbers:
                    largest = max(valid_numbers)
                    print(f"Found signature count in page text: {largest:,}")
                    return largest
        
        print("No signature count found with fallback method")
        return None
        
    except Exception as e:
        print(f"❌ Error with fallback scraping: {e}")
        return None

def fetch_csv_data(csv_url, service=None, spreadsheet_id=None):
    """Fetch CSV data from Google Sheets"""
    try:
        # If we have the service and spreadsheet_id, use the API
        if service and spreadsheet_id:
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='A:H'  # Get all columns
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return []
            
            # Convert to CSV format for processing
            headers = values[0]
            rows = []
            for row in values[1:]:
                # Pad row to match headers length
                while len(row) < len(headers):
                    row.append('')
                rows.append(dict(zip(headers, row)))
            
            return rows
        else:
            # Fallback to CSV URL
            response = requests.get(csv_url)
            response.raise_for_status()
            
            lines = response.text.strip().split('\n')
            reader = csv.DictReader(lines)
            return list(reader)
        
    except Exception as e:
        print(f"Error fetching CSV data: {e}")
        return []

def update_google_sheets_directly(spreadsheet_id, sign_counts, service):
    """Update Google Sheets directly using Google Sheets API"""
    print("Updating Google Sheets directly...")
    
    try:
        # Get the actual spreadsheet ID from the published URL
        if spreadsheet_id.startswith('http') and '/e/' in spreadsheet_id:
            # Extract the actual ID from the published URL
            parts = spreadsheet_id.split('/e/')[1].split('/')
            if parts:
                actual_id = parts[0].replace('2PACX-1v', '').replace('2PACX-', '')
                # Try to find the actual spreadsheet using the Drive API or by trying different formats
                print("📝 Attempting to find the actual spreadsheet...")
                
                # For now, let's ask the user to share the edit link
                print("❌ Cannot directly update published sheets.")
                print("📝 Please share the EDIT link to your Google Sheets (not the published link)")
                print("💡 The edit link looks like: https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID]/edit")
                print("💡 You can get this by clicking 'Share' in your Google Sheets and copying the link")
                return False
        
        # First, check if VoteTally column exists
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='A1:Z1'
        ).execute()
        
        headers = result.get('values', [[]])[0]
        vote_tally_col = None
        
        # Find VoteTally - Eng column or add it
        for i, header in enumerate(headers):
            if header.lower() == 'votetally - eng':
                vote_tally_col = chr(65 + i)  # Convert to column letter
                break
        
        if not vote_tally_col:
            # Add VoteTally - Eng column
            print("📝 Adding VoteTally - Eng column...")
            vote_tally_col = chr(65 + len(headers))  # Next column after existing headers
            
            # Add header
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f'{vote_tally_col}1',
                valueInputOption='RAW',
                body={'values': [['VoteTally - Eng']]}
            ).execute()
        
        # Update sign counts
        print(f"Updating sign counts in column {vote_tally_col}...")
        
        updates = []
        for i, (title, count) in enumerate(sign_counts):
            if count is not None:
                row_num = i + 2  # +2 because we start from row 2 (after header)
                updates.append({
                    'range': f'{vote_tally_col}{row_num}',
                    'values': [[str(count)]]
                })
        
        if updates:
            # Batch update
            batch_body = {
                'valueInputOption': 'RAW',
                'data': updates
            }
            
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=batch_body
            ).execute()
            
            print(f"Successfully updated {len(updates)} sign counts!")
            return True
        else:
            print("⚠️  No sign counts to update")
            return True
            
    except Exception as e:
        print(f"❌ Error updating Google Sheets: {e}")
        return False



def extract_spreadsheet_id(csv_url):
    """Extract spreadsheet ID from CSV URL"""
    try:
        # Handle both /d/ and /e/ formats
        if '/d/' in csv_url:
            spreadsheet_id = csv_url.split('/d/')[1].split('/')[0]
            return spreadsheet_id
        elif '/e/' in csv_url:
            # For published URLs, extract the ID from the /e/ part
            parts = csv_url.split('/e/')
            if len(parts) > 1:
                spreadsheet_id = parts[1].split('/')[0]
                return spreadsheet_id
            else:
                print("❌ Could not extract spreadsheet ID from published URL")
                return None
        else:
            print("❌ Could not extract spreadsheet ID from URL")
            return None
    except Exception as e:
        print(f"❌ Error extracting spreadsheet ID: {e}")
        return None

def is_change_org_url(url):
    """Check if URL is a Change.org petition (including chng.it short URLs)"""
    if not url:
        return False
    parsed = urlparse(url)
    return 'change.org' in parsed.netloc or 'chng.it' in parsed.netloc

def main():
    parser = argparse.ArgumentParser(description='Automatically update Google Sheets with scraped sign counts')
    parser.add_argument('--api-key', help='Firecrawl API key (no longer required, using Selenium)')
    parser.add_argument('--csv-url', default='https://docs.google.com/spreadsheets/d/12I3l5W2CBLvuyMpSnau9NiHBMpmIeptQTcP6vUjY-ls/edit?usp=sharing',
                       help='Google Sheets URL')
    parser.add_argument('--delay', type=float, default=2.0,
                       help='Delay between requests in seconds')
    
    args = parser.parse_args()
    
    print("Fully Automated Google Sheets Updater")
    print("=" * 45)
    
    # Get Google Sheets service
    service = get_google_sheets_service()
    if not service:
        print("❌ Failed to authenticate with Google Sheets")
        return
    
    # Extract spreadsheet ID
    spreadsheet_id = extract_spreadsheet_id(args.csv_url)
    if not spreadsheet_id:
        return
    
    print(f"Spreadsheet ID: {spreadsheet_id}")
    
    # For direct edit URLs, extract the ID
    if '/edit' in args.csv_url:
        spreadsheet_id = args.csv_url.split('/d/')[1].split('/')[0]
        print(f"Using direct spreadsheet ID: {spreadsheet_id}")
    
    print("Fetching current data from Google Sheets...")
    # Use CSV export method for better compatibility
    csv_export_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=csv"
    csv_data = fetch_csv_data(csv_export_url, None, None)
    
    if not csv_data:
        print("❌ No CSV data found")
        return
    
    print(f"Found {len(csv_data)} rows")
    
    # Scrape sign counts
    sign_counts = []
    for row in csv_data:
        title = row.get('Title_Eng', 'Unknown')
        vote_form_url = row.get('VoteForm - Eng', '').strip()
        
        if vote_form_url and is_change_org_url(vote_form_url):
            print(f"Scraping votes for: {title}")
            print(f"URL: {vote_form_url}")
            sign_count = scrape_with_selenium(vote_form_url)
            print(f"Found {sign_count} votes")
            sign_counts.append((title, sign_count))
            time.sleep(args.delay)
        else:
            sign_counts.append((title, None))
            if vote_form_url:
                print(f"Skipping non-Change.org URL: {vote_form_url}")
            else:
                print("No VoteForm - Eng URL found for row")
    
    # Update Google Sheets
    success = update_google_sheets_directly(spreadsheet_id, sign_counts, service)
    
    if success:
        print("\nSuccessfully updated Google Sheets!")
        print("Refresh your webpage to see the updated sign counts.")
    else:
        print("\nFailed to update Google Sheets")

if __name__ == "__main__":
    main()
