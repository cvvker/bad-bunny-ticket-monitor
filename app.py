import os
from flask import Flask, render_template, jsonify, send_from_directory
import requests
from datetime import datetime
import time
import random
import json
from bs4 import BeautifulSoup
import logging
from fake_useragent import UserAgent
import asyncio
import aiohttp
import backoff
from playwright.sync_api import sync_playwright
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables with defaults
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '15'))  # Default to 15 seconds if not set
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/1347702022039666783/IIgJ2B6vT5aQoTjNOadVxdAviHuEsCRR8zwu4CgWAvWzcob9BJ0_5XQC-BTyVauTljR_')

# Import Playwright for headless browser
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Playwright not available. Falling back to requests-only mode.")

# Bad Bunny tour dates (as per user specifications)
BAD_BUNNY_DATES = {
    'July': ['12', '18', '19'],
    'August': ['1', '2', '3', '8', '9', '10', '15', '16', '17', '22', '23', '24', '29', '30', '31'],
    'September': ['5', '6', '7', '12', '13', '14']
}

# Generate all event IDs for the Bad Bunny tour
BAD_BUNNY_EVENT_IDS = []
for month, days in BAD_BUNNY_DATES.items():
    for day in days:
        BAD_BUNNY_EVENT_IDS.append(f"{month.lower()}-{day}")

# Base Ticketera URL
TICKETERA_BASE_URL = "https://choli.ticketera.com/"

# Specific URLs for each Bad Bunny concert date
TICKETERA_URLS = {
    'July': {
        '12': "https://choli.ticketera.com/checkout/67801ac67b15db4542eeed7e?underShop=67801ac67b15db4542eeee56&boxOnly=true",
        '18': "https://choli.ticketera.com/checkout/67801c6485e7610f9b45cb54?underShop=67801c6585e7610f9b45cbce&boxOnly=true",
        '19': "https://choli.ticketera.com/event/67801ccc52c0091cff4e33a7/67801ccd52c0091cff4e33f7"
    },
    'August': {
        '1': "https://choli.ticketera.com/checkout/677ff055a1198f5724fc1158?underShop=677ff055a1198f5724fc11a8",
        '2': "https://choli.ticketera.com/checkout/678276b19c10a4675dcd677b?underShop=678276b19c10a4675dcd67d4",
        '3': "https://choli.ticketera.com/checkout/6782776b39978af92af5d38e?underShop=6782776c39978af92af5d3e7",
        '8': "https://choli.ticketera.com/checkout/678278919c8c608b8c0ebdd2?underShop=678278929c8c608b8c0ebe2b",
        '9': "https://choli.ticketera.com/checkout/6782790885a03cd75926079c?underShop=6782790885a03cd759260898",
        '10': "https://choli.ticketera.com/checkout/67827a23406d3f4b30602cf9?underShop=67827a23406d3f4b30602d52",
        '15': "https://choli.ticketera.com/checkout/67827aecbb4a8ef99dab15e8?underShop=67827aecbb4a8ef99dab1641",
        '16': "https://choli.ticketera.com/checkout/67827b7b0cc574c721710a65?underShop=67827b7c0cc574c721710abe",
        '17': "https://choli.ticketera.com/checkout/67827c0f96690559d725b430?underShop=67827c1096690559d725b489",
        '22': "https://choli.ticketera.com/checkout/67827cf5564ad8f63c77f57d?underShop=67827cf5564ad8f63c77f5d8",
        '23': "https://choli.ticketera.com/checkout/67827da9651f8bdbe0bd3f0e?underShop=67827daa651f8bdbe0bd3f67",
        '24': "https://choli.ticketera.com/checkout/67827f39c3c7b7d600ca906a?underShop=67827f3ac3c7b7d600ca90ce",
        '29': "https://choli.ticketera.com/checkout/67827fce1104e5b3ac99c82a?underShop=67827fce1104e5b3ac99c883",
        '30': "https://choli.ticketera.com/checkout/678281fdc311c1c0762df8d6?underShop=678281fec311c1c0762df93d",
        '31': "https://choli.ticketera.com/checkout/6782827df1edcc48da3866fb?underShop=6782827ef1edcc48da386754"
    },
    'September': {
        '5': "https://choli.ticketera.com/checkout/678285d0a9936d5291154f60?underShop=678285d1a9936d5291154fb9",
        '6': "https://choli.ticketera.com/checkout/67828834bb4a8ef99daf35b9?underShop=67828835bb4a8ef99daf361c",
        '7': "https://choli.ticketera.com/checkout/67828abbf9dde02e3c3f059d?underShop=67828abcf9dde02e3c3f062d",
        '12': "https://choli.ticketera.com/checkout/67828d8333f81d3543d0a47c?underShop=67828d8333f81d3543d0a575",
        '13': "https://choli.ticketera.com/checkout/67828df40952cb5ab00ba5dd?underShop=67828df40952cb5ab00ba636",
        '14': "https://choli.ticketera.com/checkout/67828e871104e5b3ac9ed068?underShop=67828e871104e5b3ac9ed0c1"
    }
}

# Concert dates to monitor
CONCERT_DATES = {
    'July': ['12', '18', '19'],
    'August': ['1', '2', '3', '8', '9', '10', '15', '16', '17', '22', '23', '24', '29', '30', '31'],
    'September': ['5', '6', '7', '12', '13', '14']
}

app = Flask(__name__)
logger = app.logger

# Monitoring settings
BASE_CHECK_INTERVAL = 60  # Base interval in seconds to avoid anti-bot detection
JITTER_MAX = 30  # Maximum random delay to add to each check (in seconds)
MAX_DATES_PER_CHECK = 3  # Only check a few dates each interval
CHECK_INTERVAL = int(os.environ.get('CHECK_INTERVAL', BASE_CHECK_INTERVAL))
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/1347702022039666783/IIgJ2B6vT5aQoTjNOadVxdAviHuEsCRR8zwu4CgWAvWzcob9BJ0_5XQC-BTyVauTljR_')

# Global state
ticket_status = {}
last_check = None
last_update_time = {}  # Track when each event was last checked

# Hardcoded Bad Bunny dates to ensure complete coverage
BAD_BUNNY_DATES = {
    'July': ['12', '18', '19'],
    'August': ['1', '2', '3', '8', '9', '10', '15', '16', '17', '22', '23', '24', '29', '30', '31'],
    'September': ['5', '6', '7', '12', '13', '14']
}

# Default URL mapping for each date
TICKETERA_URLS_DEFAULT = {
    'July': {
        '12': TICKETERA_BASE_URL,
        '18': TICKETERA_BASE_URL,
        '19': TICKETERA_BASE_URL
    },
    'August': {
        '1': TICKETERA_BASE_URL,
        '2': TICKETERA_BASE_URL,
        '3': TICKETERA_BASE_URL,
        '8': TICKETERA_BASE_URL,
        '9': TICKETERA_BASE_URL,
        '10': TICKETERA_BASE_URL,
        '15': TICKETERA_BASE_URL,
        '16': TICKETERA_BASE_URL,
        '17': TICKETERA_BASE_URL,
        '22': TICKETERA_BASE_URL,
        '23': TICKETERA_BASE_URL,
        '24': TICKETERA_BASE_URL,
        '29': TICKETERA_BASE_URL,
        '30': TICKETERA_BASE_URL,
        '31': TICKETERA_BASE_URL
    },
    'September': {
        '5': TICKETERA_BASE_URL,
        '6': TICKETERA_BASE_URL,
        '7': TICKETERA_BASE_URL,
        '12': TICKETERA_BASE_URL,
        '13': TICKETERA_BASE_URL,
        '14': TICKETERA_BASE_URL
    }
}

# Create initial ticket status with all dates at startup
for month, days in BAD_BUNNY_DATES.items():
    for day in days:
        event_id = f"{month.lower()}-{day}"
        date_str = f"{month} {day}, 2025"
        event_url = TICKETERA_URLS.get(month, {}).get(day, TICKETERA_URLS_DEFAULT[month][day])
        
        # Initialize with default values
        if event_id not in ticket_status:
            ticket_status[event_id] = {
                "name": f"Bad Bunny - {date_str}",
                "date": date_str,
                "status": "⚡ Not Yet Available",
                "url": event_url,
                "lastChecked": "Initializing..."
            }

# Initialize last_update_time variable at startup
for month, days in CONCERT_DATES.items():
    for day in days:
        event_id = f"{month.lower()}-{day}"
        last_update_time[event_id] = datetime.min

def format_date(month, day):
    return f"{month} {day}, 2025"

def generate_event_url(month, day):
    # Get the specific event URL for this date
    url = TICKETERA_URLS.get(month, {}).get(str(day))
    if not url:
        return None
    return url

def send_discord_notification(message, use_mentions=False):
    """Send a notification to Discord via webhook"""
    if not DISCORD_WEBHOOK_URL:
        logger.warning("Discord webhook URL not set, skipping notification")
        return
    
    try:
        # Add appropriate mentions if needed
        if use_mentions:
            message = f"@everyone {message}"
            
        payload = {
            "content": message,
            "username": "Bad Bunny Ticket Monitor",
            "avatar_url": "https://i.imgur.com/MJd3Vpx.jpg"
        }
        
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        
        # For high-priority alerts, send a second notification after a delay
        if "TICKETS AVAILABLE" in message or "CHECK NOW" in message:
            time.sleep(1)  # Short delay between notifications
            
            # Second notification with step-by-step instructions
            instructions = """
**URGENT: Tickets may be available!** 🔥

**Follow these steps immediately:**
1. Click the ticket link above
2. Select your ticket quantity
3. Complete checkout as quickly as possible
4. Tickets sell out fast - don't hesitate!

Good luck! 🍀
            """
            
            follow_up = {
                "content": instructions,
                "username": "Bad Bunny Ticket Monitor",
                "avatar_url": "https://i.imgur.com/MJd3Vpx.jpg"
            }
            
            response = requests.post(DISCORD_WEBHOOK_URL, json=follow_up)
            response.raise_for_status()
            
        logger.info("Discord notification sent successfully")
    except Exception as e:
        logger.error(f"Error sending Discord notification: {e}")

def check_ticketera_availability(event_url):
    """Check if tickets are available on Ticketera."""
    # Create a session with retry capability
    session = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    # Rotate user agents to avoid detection
    user_agents = [
        # Chrome Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        # Firefox Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
        # Safari macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        # Edge Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        # Mobile browsers
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
    ]
    user_agent = random.choice(user_agents)
    
    # Create headers that mimic a real browser
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "DNT": "1",
    }
    
    # Add cookies to simulate a real browser session
    cookies = {
        "_ga": f"GA1.2.{random.randint(1000000000, 9999999999)}.{int(time.time() - random.randint(3600, 86400))}",
        "_gid": f"GA1.2.{random.randint(1000000000, 9999999999)}.{int(time.time())}",
        "_fbp": f"fb.1.{int(time.time()) - random.randint(3600, 86400)}.{random.randint(1000000000, 9999999999)}",
    }
    
    # Add random delay to mimic human behavior (between 1 and 5 seconds)
    time.sleep(random.uniform(1, 5))
    
    try:
        # Get the page content
        response = session.get(event_url, headers=headers, cookies=cookies, timeout=30)
        response.raise_for_status()
        
        # Parse the html content
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Look for checkout links
        checkout_links = []
        # Search for checkout links in href attributes
        checkout_pattern = "/checkout/"
        for link in soup.find_all('a', href=True):
            if checkout_pattern in link['href']:
                checkout_links.append(link['href'])
        
        # Also look for checkout links in the page JavaScript
        for script in soup.find_all('script'):
            if script.string and checkout_pattern in script.string:
                # Extract potential checkout URLs from JavaScript
                script_text = script.string
                start_idx = 0
                while True:
                    start_idx = script_text.find(checkout_pattern, start_idx)
                    if start_idx == -1:
                        break
                    # Try to extract the full URL
                    end_idx = script_text.find('"', start_idx)
                    if end_idx == -1:
                        end_idx = script_text.find("'", start_idx)
                    if end_idx == -1:
                        end_idx = script_text.find('\\', start_idx)
                    if end_idx == -1:
                        end_idx = script_text.find(' ', start_idx)
                    if end_idx == -1:
                        end_idx = start_idx + 100  # Limit to reasonable length
                    
                    potential_link = script_text[start_idx-20:end_idx].strip()
                    if 'http' in potential_link:
                        http_start = potential_link.find('http')
                        potential_link = potential_link[http_start:]
                        checkout_links.append(potential_link)
                    else:
                        checkout_links.append('https://choli.ticketera.com' + potential_link)
                    
                    start_idx = end_idx
        
        # If we found checkout links, this is highly valuable information
        if checkout_links:
            checkout_links = list(set(checkout_links))  # Remove duplicates
            # Format the first checkout link for display
            formatted_link = checkout_links[0]
            if len(formatted_link) > 60:
                formatted_link = formatted_link[:60] + "..."
            
            # Save the checkout links to a file for quick access
            event_name = event_url.split('/')[-1]
            with open(f"checkout_links_{event_name}.txt", "w") as f:
                for link in checkout_links:
                    f.write(link + "\n")
            
            # Return a special message with checkout link information
            return f"🚨 DIRECT CHECKOUT AVAILABLE! 🚨 Link: {formatted_link}"
        
        # Look for indicators of ticket availability
        if "¡Entradas disponibles!" in response.text or "Comprar ahora" in response.text:
            # Try to extract actual inventory numbers if available
            try:
                # Look for the inventory counter in the JSON data that's often embedded in the page
                if "ticketsAvailable" in response.text or "availableCount" in response.text or "stockLevel" in response.text:
                    # Try to extract JSON data from script tags
                    scripts = soup.find_all('script')
                    inventory_count = None
                    
                    for script in scripts:
                        script_text = script.string if script.string else ""
                        # Look for inventory-related JSON
                        if "ticketsAvailable" in script_text or "availableCount" in script_text or "stockLevel" in script_text:
                            try:
                                # Find JSON objects in the script
                                json_start = script_text.find('{')
                                json_end = script_text.rfind('}') + 1
                                if json_start >= 0 and json_end > json_start:
                                    json_str = script_text[json_start:json_end]
                                    # Try to clean and parse the JSON
                                    json_data = json.loads(json_str)
                                    # Look for inventory fields using various common names
                                    for field in ['ticketsAvailable', 'availableCount', 'stockLevel', 'inventory', 'available', 'stock']:
                                        if field in json_data:
                                            inventory_count = json_data[field]
                                            break
                            except Exception as e:
                                print(f"Error parsing JSON from script: {e}")
                    
                    if inventory_count is not None:
                        return f"🔥 TICKETS AVAILABLE! {inventory_count} tickets in stock 🔥"
                
                # If we couldn't get exact inventory, try to find inventory indicators in the HTML
                inventory_elements = soup.select('[data-inventory], [data-stock], .inventory-count, .stock-level, .tickets-available')
                for element in inventory_elements:
                    if element.get_text().strip() and any(c.isdigit() for c in element.get_text()):
                        inventory_text = element.get_text().strip()
                        return f"🔥 TICKETS AVAILABLE! Stock: {inventory_text} 🔥"
            except Exception as e:
                print(f"Error trying to extract inventory: {e}")
                
            # If all inventory extraction fails, just return the basic availability message
            return "🔥 TICKETS AVAILABLE! CHECK NOW 🔥"
        elif "coming soon" in response.text.lower() or "próximamente" in response.text.lower():
            return "⚡ Coming Soon"
        elif "sold out" in response.text.lower() or "agotado" in response.text.lower():
            return "❌ Sold Out"
        else:
            # Check for specific elements that might indicate availability
            buy_buttons = soup.select('button.buy-button, .checkout-button, .buy-now')
            if buy_buttons:
                return "⚠️ Possible Availability - CHECK NOW"
            
            # Check for waitlist or queue indicators
            waitlist = soup.select('.waitlist, .queue, .waiting-room')
            if waitlist:
                return "⏳ In Queue/Waitlist"
            
            # Fallback message
            return "⚡ Not Yet Available"
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logger.error(f"Blocked by Ticketera: 403 Forbidden: {e}")
            return "🚫 Access Blocked - Using Cached Status"
        else:
            logger.error(f"HTTP Error: {e}")
            return "⚠️ Error Checking - Using Cached Status"
    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking Ticketera: {e}")
        return "⚡ Error checking availability"

def check_with_playwright(event_url):
    """
    Check ticket availability using Playwright for more sophisticated browser simulation.
    This is used when available as a fallback for anti-bot measures.
    """
    if not PLAYWRIGHT_AVAILABLE:
        return "⚠️ Cannot check (browser automation not available)"
    
    try:
        with sync_playwright() as p:
            # Launch a new browser with stealth mode settings
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US"
            )
            
            # Enable JavaScript and cookies
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false,
                });
            """)
            
            # Create a new page and navigate to the event URL
            page = context.new_page()
            
            # Set various headers to appear more like a real browser
            page.set_extra_http_headers({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "DNT": "1",
            })
            
            # Navigate to the event with a timeout
            page.goto(event_url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for potential lazy-loaded content
            page.wait_for_timeout(random.randint(2000, 5000))
            
            # Get the content
            content = page.content()
            
            # Check for ticket availability indicators in the content
            if "¡Entradas disponibles!" in content or "Comprar ahora" in content:
                # Look for checkout links in the page
                checkout_links = []
                checkout_pattern = "/checkout/"
                
                # Look for links in href attributes
                links = page.query_selector_all('a[href*="checkout"]')
                for link in links:
                    href = link.get_attribute('href')
                    if href and checkout_pattern in href:
                        checkout_links.append(href)
                
                # Look for checkout links in scripts
                scripts = page.query_selector_all('script')
                for script in scripts:
                    script_text = script.inner_text()
                    if script_text and checkout_pattern in script_text:
                        start_idx = 0
                        while True:
                            start_idx = script_text.find(checkout_pattern, start_idx)
                            if start_idx == -1:
                                break
                            # Try to extract the full URL
                            end_idx = script_text.find('"', start_idx)
                            if end_idx == -1:
                                end_idx = script_text.find("'", start_idx)
                            if end_idx == -1:
                                end_idx = script_text.find('\\', start_idx)
                            if end_idx == -1:
                                end_idx = script_text.find(' ', start_idx)
                            if end_idx == -1:
                                end_idx = start_idx + 100  # Limit to reasonable length
                            
                            potential_link = script_text[start_idx-20:end_idx].strip()
                            if 'http' in potential_link:
                                http_start = potential_link.find('http')
                                potential_link = potential_link[http_start:]
                                checkout_links.append(potential_link)
                            else:
                                checkout_links.append('https://choli.ticketera.com' + potential_link)
                            
                            start_idx = end_idx
                
                # If we found checkout links, this is highly valuable information
                if checkout_links:
                    checkout_links = list(set(checkout_links))  # Remove duplicates
                    # Format the first checkout link for display
                    formatted_link = checkout_links[0]
                    if len(formatted_link) > 60:
                        formatted_link = formatted_link[:60] + "..."
                    
                    # Save the checkout links to a file for quick access
                    event_name = event_url.split('/')[-1]
                    with open(f"checkout_links_{event_name}.txt", "w") as f:
                        for link in checkout_links:
                            f.write(link + "\n")
                    
                    browser.close()
                    # Return a special message with checkout link information
                    return f"🚨 DIRECT CHECKOUT AVAILABLE! 🚨 Link: {formatted_link}"
                
                # Try to extract actual inventory numbers if available
                try:
                    # Look for the inventory counter in the JSON data that's often embedded in the page
                    if "ticketsAvailable" in content or "availableCount" in content or "stockLevel" in content:
                        # Try to extract JSON data from script tags
                        scripts = page.query_selector_all('script')
                        inventory_count = None
                        
                        for script in scripts:
                            script_text = script.inner_text()
                            # Look for inventory-related JSON
                            if "ticketsAvailable" in script_text or "availableCount" in script_text or "stockLevel" in script_text:
                                try:
                                    # Find JSON objects in the script
                                    json_start = script_text.find('{')
                                    json_end = script_text.rfind('}') + 1
                                    if json_start >= 0 and json_end > json_start:
                                        json_str = script_text[json_start:json_end]
                                        # Try to clean and parse the JSON
                                        json_data = json.loads(json_str)
                                        # Look for inventory fields using various common names
                                        for field in ['ticketsAvailable', 'availableCount', 'stockLevel', 'inventory', 'available', 'stock']:
                                            if field in json_data:
                                                inventory_count = json_data[field]
                                                break
                                except Exception as e:
                                    print(f"Error parsing JSON from script: {e}")
                        
                        if inventory_count is not None:
                            browser.close()
                            return f"🔥 TICKETS AVAILABLE! {inventory_count} tickets in stock 🔥"
                    
                    # If we couldn't get exact inventory, try to find inventory indicators in the HTML
                    inventory_elements = page.query_selector_all('[data-inventory], [data-stock], .inventory-count, .stock-level, .tickets-available')
                    for element in inventory_elements:
                        if element.inner_text().strip() and any(c.isdigit() for c in element.inner_text()):
                            inventory_text = element.inner_text().strip()
                            browser.close()
                            return f"🔥 TICKETS AVAILABLE! Stock: {inventory_text} 🔥"
                except Exception as e:
                    print(f"Error trying to extract inventory: {e}")
                    
                # If all inventory extraction fails, just return the basic availability message
                browser.close()
                return "🔥 TICKETS AVAILABLE! CHECK NOW 🔥"
            elif "coming soon" in content.lower() or "próximamente" in content.lower():
                browser.close()
                return "⚡ Coming Soon"
            elif "sold out" in content.lower() or "agotado" in content.lower():
                browser.close()
                return "❌ Sold Out"
            else:
                # Check for specific elements that might indicate availability
                buy_button = page.query_selector('button:has-text("Comprar"), button:has-text("Buy"), a:has-text("Comprar"), a:has-text("Buy")')
                if buy_button:
                    browser.close()
                    return "⚠️ Possible Availability - CHECK NOW"
                
                # Check for waitlist or queue indicators
                waitlist = page.query_selector('text="waitlist", text="queue", text="waiting room", text="cola", text="espera"')
                if waitlist:
                    browser.close()
                    return "⏳ In Queue/Waitlist"
                
                # Fallback message
                browser.close()
                return "⚡ Not Yet Available"
    
    except Exception as e:
        logger.error(f"Playwright error checking Ticketera: {e}")
        return "⚠️ Error Checking (Browser) - Using Cached Status"

def update_ticket_status():
    """Enhanced update function with fallback mechanisms and smart date selection"""
    global ticket_status, last_check, last_update_time
    
    last_check = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Generate all Bad Bunny event dates if not in ticket_status
    for event_id in BAD_BUNNY_EVENT_IDS:
        if event_id not in ticket_status:
            # Extract month and day from the event ID
            month, day = event_id.split('-')
            month = month.capitalize()
            
            # Set up initial status for this event
            date_str = f"{month} {day}, 2025"
            
            # Get URL for this event if available, otherwise use the base URL
            event_url = TICKETERA_BASE_URL
            if month in TICKETERA_URLS and day in TICKETERA_URLS[month]:
                event_url = TICKETERA_URLS[month][day]
            
            ticket_status[event_id] = {
                "name": f"Bad Bunny - {date_str}",
                "date": date_str,
                "status": "⚡ Not Yet Available",
                "url": event_url,
                "lastChecked": "Pending..."
            }
    
    # Sort dates by last check time (oldest first)
    sorted_dates = sorted(
        ticket_status.keys(),
        key=lambda x: last_update_time.get(x, 0)
    )
    
    # Only check a subset of dates each time, prioritizing those checked least recently
    # This helps avoid triggering anti-bot detection
    max_checks = min(MAX_DATES_PER_CHECK, len(sorted_dates))
    dates_to_check = sorted_dates[:max_checks]
    
    for event_id in dates_to_check:
        # Only update if we have the event in our tracking
        if event_id in ticket_status:
            # Extract month and day
            month, day = event_id.split('-')
            month = month.capitalize()
            
            # Get URL for this event
            event_url = TICKETERA_BASE_URL
            if month in TICKETERA_URLS and day in TICKETERA_URLS[month]:
                event_url = TICKETERA_URLS[month][day]
            
            # 10% chance to use Playwright for enhanced anti-bot capabilities
            if PLAYWRIGHT_AVAILABLE and random.random() < 0.10:
                logger.info(f"Using Playwright to check {event_id} ({event_url})")
                status = check_with_playwright(event_url)
            else:
                # Otherwise use regular requests (which is faster but more detectable)
                logger.info(f"Using Requests to check {event_id} ({event_url})")
                status = check_ticketera_availability(event_url)
            
            # Add jitter to request timing to seem more human-like
            time.sleep(random.uniform(1, JITTER_MAX))
            
            # Update status and last check time
            previous_status = ticket_status[event_id]["status"]
            
            # Only send Discord notification if the status changed significantly
            if previous_status != status:
                logger.info(f"Status change for {event_id}: {previous_status} -> {status}")
                
                # Only notify for certain status changes (to avoid notification spam)
                should_notify = (
                    ("TICKETS AVAILABLE" in status) or
                    ("CHECK NOW" in status) or
                    (previous_status != "⚡ Not Yet Available" and "Not Yet Available" not in status)
                )
                
                if should_notify:
                    # Send Discord notification
                    event_name = ticket_status[event_id]["name"]
                    notification_text = f"**Status Change** for {event_name}\n{previous_status} → {status}\n[Check Tickets]({event_url})"
                    
                    # Add @everyone mention for high priority alerts
                    if "TICKETS AVAILABLE" in status or "CHECK NOW" in status:
                        send_discord_notification(notification_text, use_mentions=True)
                    else:
                        send_discord_notification(notification_text)
            
            # Update ticket status in our tracking
            ticket_status[event_id].update({
                "status": status,
                "lastChecked": datetime.now().strftime("%H:%M:%S")
            })
            
            # Update the last check time for this event
            last_update_time[event_id] = time.time()
            
    # Return the full status for all events (even those not checked this round)
    return ticket_status

def ensure_all_dates_exist():
    """Ensure all Bad Bunny dates exist in the ticket status"""
    current_time = datetime.now().strftime('%H:%M:%S')
    
    # Populate any missing dates with default values
    for month, days in BAD_BUNNY_DATES.items():
        for day in days:
            event_id = f"{month.lower()}-{day}"
            date_str = f"{month} {day}, 2025"
            
            # If this date doesn't exist in our tracking, add it
            if event_id not in ticket_status:
                # Get URL for this event if available, otherwise use the base URL
                event_url = TICKETERA_BASE_URL
                if month in TICKETERA_URLS and day in TICKETERA_URLS[month]:
                    event_url = TICKETERA_URLS[month][day]
                
                # Add default status for this date
                ticket_status[event_id] = {
                    "name": f"Bad Bunny - {date_str}",
                    "date": date_str,
                    "status": "⚡ Not Yet Available",
                    "url": event_url,
                    "lastChecked": current_time
                }

@app.route('/api/tickets')
def get_tickets():
    """API endpoint for getting ticket status"""
    # Make sure we have data for all dates
    ensure_all_dates_exist()
    
    # First, check if we have any data at all
    if not ticket_status or len(ticket_status) == 0:
        # Create fallback data for all dates
        current_time = datetime.now().strftime('%I:%M:%S %p')
        for month, days in CONCERT_DATES.items():
            for day in days:
                event_id = f"{month.lower()}-{day}"
                date = format_date(month, day)
                event_url = generate_event_url(month, day)
                
                if not event_url:
                    continue
                        
                ticket_status[event_id] = {
                    'name': f"Bad Bunny - {date}",
                    'date': date,
                    'status': "⚡ Not Yet Available",
                    'url': event_url,
                    'lastChecked': current_time
                }
        
    # Update status if it's been more than CHECK_INTERVAL seconds
    if not last_check or (datetime.now() - last_check).total_seconds() >= CHECK_INTERVAL:
        update_ticket_status()
        
    # If we still have no data, create fallback data
    if not ticket_status or len(ticket_status) == 0:
        return jsonify(generateFallbackData())
            
    return jsonify(ticket_status)

def generateFallbackData():
    """Generate fallback data for all dates in case of API failure"""
    fallback_data = {}
    current_time = datetime.now().strftime('%I:%M:%S %p')
    
    for month, days in CONCERT_DATES.items():
        for day in days:
            event_id = f"{month.lower()}-{day}"
            date = format_date(month, day)
            fallback_data[event_id] = {
                'name': f"Bad Bunny - {date}",
                'date': date,
                'status': "⚡ Not Yet Available",
                'url': "https://choli.ticketera.com/",
                'lastChecked': current_time
            }
    
    return fallback_data

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # Do initial check
    update_ticket_status()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
