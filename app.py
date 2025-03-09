import os
from flask import Flask, render_template, jsonify, send_from_directory, request
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

# Cart automation settings
cart_config = {
    'enabled': False,
    'ticketQuantity': 2,
    'maxPrice': 500,
    'preferredSections': [],
    'fallbackToAnySection': True,
    'autoRetryAttempts': 3,
    'notifications': True
}

# Cart session storage
cart_session = {
    'activeCarts': {},
    'completedCarts': {},
    'failedCarts': {}
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

def send_discord_notification(message, use_mentions=False, title=None, color=None, image_url=None, cart_info=None):
    """
    Sends a notification to Discord webhook with optional mentions, title, color, and image
    
    Args:
        message: The message to send
        use_mentions: Whether to include @everyone in the message
        title: Title for the embed message
        color: Color for the embed message (hexadecimal integer)
        image_url: URL for an image to include in the embed
        cart_info: Dictionary with cart information (optional)
    """
    if use_mentions:
        message = "@everyone " + message
        
    payload = {
        "username": "Bad Bunny Ticket Monitor",
        "avatar_url": "https://i.imgur.com/MQ3Dvz0.png"
    }
    
    # If we have cart info, create a rich embed
    if cart_info:
        date = cart_info.get('date', 'Unknown date')
        quantity = cart_info.get('quantity', 'Unknown quantity')
        price = cart_info.get('price', 'Unknown price')
        section = cart_info.get('section', 'Unknown section')
        cart_url = cart_info.get('cart_url', '')
        
        embed = {
            "title": "🎫 TICKETS ADDED TO CART! 🎫",
            "color": 16711680,  # Red color
            "fields": [
                {
                    "name": "Event",
                    "value": f"Bad Bunny - {date}",
                    "inline": True
                },
                {
                    "name": "Quantity",
                    "value": str(quantity),
                    "inline": True
                }
            ],
            "footer": {
                "text": "Bad Bunny Ticket Monitor"
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Add price if available
        if price and price != 'Unknown price':
            embed["fields"].append({
                "name": "Price",
                "value": f"${price}",
                "inline": True
            })
            
        # Add section if available
        if section and section != 'Unknown section':
            embed["fields"].append({
                "name": "Section",
                "value": section,
                "inline": True
            })
        
        # Add cart URL as an action button (Discord uses Markdown for this)
        if cart_url:
            embed["description"] = f"**[PROCEED TO CHECKOUT]({cart_url})**\n\nMove quickly! Tickets may sell out."
        
        payload["embeds"] = [embed]
    elif title:
        embed = {
            "title": title,
            "description": message,
            "color": color if color else 5814783,  # Default to a blue color if none specified
        }
        
        if image_url:
            embed["image"] = {"url": image_url}
            
        payload["embeds"] = [embed]
        payload["content"] = "@everyone" if use_mentions else ""
    else:
        payload["content"] = message
    
    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending Discord notification: {e}")
        return False

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

async def add_to_cart(page, logger, event_url, browser_context, event_name, event_date, quantity=2):
    """
    Add tickets to cart for the given event and return the cart URL
    """
    success = False
    cart_url = None
    details = {}
    
    try:
        logger.info(f"Starting to add to cart for event: {event_name}")
        
        # Navigate to the event page
        logger.info(f"Navigating to event page: {event_url}")
        await page.goto(event_url, wait_until="networkidle")
        
        # Wait a bit for page to fully load
        await asyncio.sleep(2)
        
        # Take screenshot of the event page (for debugging)
        screenshots_dir = os.path.join(os.path.dirname(__file__), "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        await page.screenshot(path=os.path.join(screenshots_dir, "event_page.png"))
        
        # Try to find and click the buy tickets button
        buy_selectors = [
            "a.btn-primary:has-text('Buy')",
            "button:has-text('Buy')",
            "a:has-text('Buy')",
            "a:has-text('Purchase')",
            "button:has-text('Purchase')"
        ]
        
        for selector in buy_selectors:
            if await page.query_selector(selector):
                logger.info(f"Found buy button with selector: {selector}")
                await page.click(selector)
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
                break
        
        # Try to select ticket quantity if possible
        try:
            logger.info("Attempting to select ticket quantity...")
            quantity_selectors = [
                "select#quantity", 
                "select.quantity-select",
                "select[name='quantity']", 
                "select",
                "input[type='number'][name='quantity']"
            ]
            
            for selector in quantity_selectors:
                quantity_input = await page.query_selector(selector)
                if quantity_input:
                    logger.info(f"Found quantity selector: {selector}")
                    tag_name = await quantity_input.evaluate("el => el.tagName.toLowerCase()")
                    
                    if tag_name == "select":
                        # For dropdown selector
                        await page.select_option(selector, str(quantity))
                    else:
                        # For number input
                        await page.fill(selector, str(quantity))
                        
                    logger.info(f"Selected {quantity} tickets")
                    break
        except Exception as e:
            logger.warning(f"Could not select quantity: {e}")
        
        # Take screenshot after quantity selection (for debugging)
        await page.screenshot(path=os.path.join(screenshots_dir, "after_quantity.png"))
        
        # Look for add to cart button and click it
        add_cart_selectors = [
            "button:has-text('Add to Cart')",
            "button:has-text('Add')",
            "input[value='Add to Cart']",
            "button.add-to-cart",
            "a:has-text('Add to Cart')",
            "button:has-text('Cart')"
        ]
        
        cart_clicked = False
        for selector in add_cart_selectors:
            if await page.query_selector(selector):
                logger.info(f"Found add to cart button with selector: {selector}")
                await page.click(selector)
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(3)
                cart_clicked = True
                
                # Take screenshot after add to cart (for debugging)
                await page.screenshot(path=os.path.join(screenshots_dir, "after_add_to_cart.png"))
                break
        
        if not cart_clicked:
            logger.warning("Could not find add to cart button")
            # If we can't find an add to cart button, we might already be on a checkout page
            # Check if the URL contains 'checkout'
            if "checkout" in page.url:
                cart_url = page.url
                logger.info(f"Already on checkout page: {cart_url}")
                cart_clicked = True
            else:
                return False, None, {}
        
        # Get the cart URL - it should now be in a format like:
        # https://shop.ticketera.com/checkout/rock-of-ages-zmspx0 or 
        # https://shop.ticketera.com/checkout/67be0fb1c3855d04ea54843e
        cart_url = page.url
        logger.info(f"Cart URL after adding tickets: {cart_url}")
        
        # Extract additional details about the tickets
        
        # Try to extract price
        price = None
        price_element = await page.query_selector("span.price, .amount, .total, .subtotal, span:has-text('$')")
        if price_element:
            price_text = await price_element.inner_text()
            price_match = re.search(r'\$\s*(\d+(?:\.\d+)?)', price_text)
            if price_match:
                price = float(price_match.group(1))
                logger.info(f"Found ticket price: ${price}")
        
        # Try to extract section
        section = None
        section_element = await page.query_selector(".section, .seat-info, .ticket-type")
        if section_element:
            section = await section_element.inner_text()
            section = section.strip()
            logger.info(f"Found section: {section}")
        else:
            section = "General Admission"
        
        # Check if the URL contains 'checkout' to verify it's a cart URL
        if cart_url and "checkout" in cart_url:
            success = True
            details = {
                'date': event_date,
                'quantity': quantity,
                'price': price,
                'section': section,
                'cart_url': cart_url
            }
            
            # Take final screenshot (for debugging)
            await page.screenshot(path=os.path.join(screenshots_dir, "final_checkout.png"))
        else:
            logger.warning(f"Cart URL doesn't appear to be a checkout URL: {cart_url}")
    
    except Exception as e:
        logger.error(f"Error adding to cart: {str(e)}")
        traceback.print_exc()
    
    return success, cart_url, details

def check_with_playwright(event_url, attempt_carting=False, event_id=None):
    """Enhanced browser-based check with carting capability"""
    try:
        # Use our custom browser settings to avoid detection
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 720},
                device_scale_factor=1,
                locale='en-US'
            )
            
            # Add custom headers to appear more like a regular browser
            context.set_extra_http_headers({
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br"
            })
            
            page = context.new_page()
            
            # Add a small delay before navigating
            time.sleep(random.uniform(0.5, 1.5))
            
            # Navigate to the event page
            response = page.goto(event_url, wait_until="domcontentloaded", timeout=30000)
            
            if not response or response.status != 200:
                logger.error(f"Failed to load page: {response.status if response else 'No response'}")
                browser.close()
                return "⚠️ Error Loading Page"
            
            # Wait for important content to load
            page.wait_for_load_state("networkidle")
            
            # Take a screenshot for debugging if enabled
            if False:  # DEBUG_SCREENSHOTS
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"debug/ticketera_{timestamp}.png"
                page.screenshot(path=screenshot_path)
            
            # Check for ticket availability
            has_tickets = False
            ticket_status = "⚡ Not Yet Available"
            
            # Check different indicators of ticket availability
            available_sections = page.query_selector_all(".available-section, .section-item:not(.sold-out)")
            ticket_elements = page.query_selector_all(".ticket-selection, .ticket-item:not(.sold-out)")
            
            if available_sections and len(available_sections) > 0:
                has_tickets = True
                ticket_status = "🎫 TICKETS AVAILABLE! 🎫"
            elif ticket_elements and len(ticket_elements) > 0:
                has_tickets = True
                ticket_status = "🎫 TICKETS AVAILABLE! 🎫"
            else:
                # Check for "compra ahora" or "buy now" buttons
                buy_buttons = page.query_selector_all("a:text-matches('Compra ahora|Buy Now|Get Tickets', 'i')")
                if buy_buttons and len(buy_buttons) > 0:
                    has_tickets = True
                    ticket_status = "🎫 TICKETS AVAILABLE! 🎫"
                    
            # Attempt carting if requested and tickets are available
            if attempt_carting and has_tickets and event_id and cart_config['enabled']:
                logger.info(f"Attempting to cart tickets for event {event_id}")
                
                try:
                    # Get quantity from config
                    quantity = cart_config.get('ticketQuantity', 2)
                    max_price = cart_config.get('maxPrice', 500)
                    
                    # Notify that we're starting the carting process
                    cart_session['activeCarts'][event_id] = {
                        'startTime': datetime.now().isoformat(),
                        'eventUrl': event_url,
                        'eventName': f"Event {event_id}",
                        'status': 'starting'
                    }
                    
                    # Send notification
                    notification_text = f"🛒 **CART AUTOMATION STARTED** 🛒\nEvent {event_id}\nStarting automatic carting process"
                    send_discord_notification(notification_text)
                    
                    # Try to select tickets
                    if available_sections and len(available_sections) > 0:
                        # Click on first available section
                        available_sections[0].click()
                        page.wait_for_timeout(1000)
                    
                    # Look for quantity selector
                    quantity_selector = page.query_selector("select.ticket-quantity")
                    if quantity_selector:
                        quantity_selector.select_option(str(quantity))
                        page.wait_for_timeout(500)
                    
                    # Click add to cart button
                    add_to_cart = page.query_selector(".add-to-cart-btn, button[type='submit']:not(.disabled)")
                    if add_to_cart:
                        # Notify that we're adding to cart
                        notification_text = f"🛒 **ADDING TO CART** 🛒\nEvent {event_id}\nAdding {quantity} tickets to cart"
                        send_discord_notification(notification_text)
                        
                        # Click the button
                        add_to_cart.click()
                        page.wait_for_timeout(5000)
                        
                        # Check if we're now on cart page
                        if "cart" in page.url or "checkout" in page.url:
                            # Success! We've added tickets to cart
                            cart_session['completedCarts'][event_id] = {
                                'completedTime': datetime.now().isoformat(),
                                'checkoutUrl': page.url,
                                'ticketQuantity': quantity
                            }
                            
                            # Take screenshot of cart page
                            if False:  # DEBUG_SCREENSHOTS
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                screenshot_path = f"debug/cart_{timestamp}.png"
                                page.screenshot(path=screenshot_path)
                            
                            # Send success notification
                            notification_text = (
                                f"🎫 **TICKETS ADDED TO CART!** 🎫\n"
                                f"Event: {event_id}\n"
                                f"Quantity: {quantity}\n"
                                f"[PROCEED TO CHECKOUT]({page.url})"
                            )
                            send_discord_notification(notification_text, use_mentions=True)
                            
                            # Update ticket status
                            ticket_status = "🛒 TICKETS IN CART! CHECK DISCORD!"
                        else:
                            # Failed to add to cart
                            cart_session['failedCarts'][event_id] = {
                                'failedTime': datetime.now().isoformat(),
                                'reason': "Failed to reach cart page"
                            }
                            
                            # Send failure notification
                            notification_text = (
                                f"❌ **Carting Failed** ❌\n"
                                f"Event: {event_id}\n"
                                f"Reason: Failed to reach cart page"
                            )
                            send_discord_notification(notification_text)
                    else:
                        logger.error(f"Add to cart button not found for event {event_id}")
                        
                        # Record failure
                        cart_session['failedCarts'][event_id] = {
                            'failedTime': datetime.now().isoformat(),
                            'reason': "Add to cart button not found"
                        }
                except Exception as cart_error:
                    logger.error(f"Error during carting: {cart_error}")
                    
                    # Record failure
                    cart_session['failedCarts'][event_id] = {
                        'failedTime': datetime.now().isoformat(),
                        'reason': str(cart_error)
                    }
                    
                # Remove from active carts
                if event_id in cart_session['activeCarts']:
                    del cart_session['activeCarts'][event_id]
            
            browser.close()
            return ticket_status
    
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
            
            # Check if we should attempt carting
            attempt_carting = (
                cart_config['enabled'] and  # Carting is enabled
                event_id not in cart_session['completedCarts'] and  # Not already carted
                event_id not in cart_session['activeCarts']  # Not currently carting
            )
            
            # 10% chance to use Playwright for enhanced anti-bot capabilities
            # Always use Playwright if attempting carting
            if (PLAYWRIGHT_AVAILABLE and random.random() < 0.10) or attempt_carting:
                logger.info(f"Using Playwright to check {event_id} ({event_url})")
                status = check_with_playwright(event_url, attempt_carting, event_id)
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
                        
                        # If carting is enabled, automatically attempt to cart for available tickets
                        if (
                            cart_config['enabled'] and 
                            "TICKETS AVAILABLE" in status and
                            event_id not in cart_session['completedCarts'] and
                            event_id not in cart_session['activeCarts'] and
                            PLAYWRIGHT_AVAILABLE and
                            not attempt_carting  # Don't attempt twice in the same update
                        ):
                            logger.info(f"Automatically attempting to cart tickets for {event_id}")
                            
                            # Schedule carting attempt in a separate thread to not block the main thread
                            import threading
                            threading.Thread(
                                target=check_with_playwright,
                                args=(event_url, True, event_id),
                                daemon=True
                            ).start()
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

@app.route('/api/cart-config', methods=['GET'])
def get_cart_config():
    """API endpoint for getting cart configuration"""
    return jsonify(cart_config)

@app.route('/api/cart-config', methods=['POST'])
def update_cart_config():
    """API endpoint for updating cart configuration"""
    data = request.json
    if data:
        # Update only valid keys
        valid_keys = cart_config.keys()
        for key in valid_keys:
            if key in data:
                cart_config[key] = data[key]
        
        # Log the update
        logger.info(f"Cart configuration updated: {cart_config}")
        
        # Return the updated config
        return jsonify(cart_config)
    
    return jsonify({'error': 'Invalid data'}), 400

@app.route('/api/cart-status', methods=['GET'])
def get_cart_status():
    """API endpoint for getting current cart status"""
    return jsonify({
        'active': cart_session['activeCarts'],
        'completed': cart_session['completedCarts'],
        'failed': cart_session['failedCarts']
    })

@app.route('/api/send-cart-notification', methods=['POST'])
def send_cart_notification():
    """API endpoint to send Discord notification for carting events"""
    data = request.json
    if not data or 'eventId' not in data or 'message' not in data:
        return jsonify({'error': 'Invalid data'}), 400
    
    event_id = data['eventId']
    event_name = data.get('eventName', f"Event {event_id}")
    message = data['message']
    use_mentions = data.get('useMentions', False)
    
    # Send the notification via Discord
    notification_text = f"🛒 **CART AUTOMATION** 🛒\n{event_name}\n{message}"
    send_discord_notification(notification_text, use_mentions=use_mentions)
    
    return jsonify({'success': True})

@app.route('/api/start-carting', methods=['POST'])
def start_carting():
    """API endpoint to start carting for a specific event"""
    data = request.json
    if not data or 'eventId' not in data:
        return jsonify({'error': 'Invalid data'}), 400
    
    event_id = data['eventId']
    
    # Verify that the event exists in our ticket status
    if event_id not in ticket_status:
        return jsonify({'error': 'Event not found'}), 404
    
    event_name = ticket_status[event_id]['name']
    event_url = ticket_status[event_id]['url']
    
    # Check if carting is already in progress or completed
    if event_id in cart_session['activeCarts']:
        return jsonify({'error': 'Carting already in progress for this event'}), 400
    
    if event_id in cart_session['completedCarts']:
        return jsonify({'error': 'Carting already completed for this event'}), 400
    
    # Start carting for this event
    cart_session['activeCarts'][event_id] = {
        'startTime': datetime.now().isoformat(),
        'eventUrl': event_url,
        'eventName': event_name,
        'status': 'starting'
    }
    
    # Send notification to Discord
    notification_text = f"🛒 **CART AUTOMATION STARTED** 🛒\n{event_name}\nStarting automatic carting process"
    send_discord_notification(notification_text)
    
    return jsonify({
        'success': True,
        'eventId': event_id,
        'eventName': event_name
    })

@app.route('/api/cart-result', methods=['POST'])
def update_cart_result():
    """API endpoint to update cart results (success/failure)"""
    data = request.json
    if not data or 'eventId' not in data or 'status' not in data:
        return jsonify({'error': 'Invalid data'}), 400
    
    event_id = data['eventId']
    status = data['status']
    
    # Verify that the event exists in active carts
    if event_id not in cart_session['activeCarts']:
        return jsonify({'error': 'No active carting found for this event'}), 404
    
    event_name = cart_session['activeCarts'][event_id]['eventName']
    
    if status == 'success':
        # Move from active to completed
        cart_session['completedCarts'][event_id] = {
            'completedTime': datetime.now().isoformat(),
            'checkoutUrl': data.get('checkoutUrl', ''),
            'ticketQuantity': cart_config['ticketQuantity']
        }
        
        # Send success notification
        notification_text = (
            f"🎫 **TICKETS ADDED TO CART!** 🎫\n"
            f"Event: {event_name}\n"
            f"Quantity: {cart_config['ticketQuantity']}\n"
            f"[PROCEED TO CHECKOUT]({data.get('checkoutUrl', '')})"
        )
        send_discord_notification(notification_text, use_mentions=True)
    else:
        # Move from active to failed
        cart_session['failedCarts'][event_id] = {
            'failedTime': datetime.now().isoformat(),
            'reason': data.get('reason', 'Unknown error')
        }
        
        # Send failure notification
        notification_text = (
            f"❌ **Carting Failed** ❌\n"
            f"Event: {event_name}\n"
            f"Reason: {data.get('reason', 'Unknown error')}"
        )
        send_discord_notification(notification_text)
    
    # Remove from active carts
    del cart_session['activeCarts'][event_id]
    
    return jsonify({
        'success': True,
        'eventId': event_id,
        'status': status
    })

@app.route('/api/tickets')
def get_tickets():
    """API endpoint to get ticket status"""
    return jsonify(ticket_status)

@app.route('/api/start-cart')
def start_cart_api():
    """API endpoint to start automatic carting with custom options"""
    event_id = request.args.get('event_id')
    url = request.args.get('url')
    quantity = request.args.get('quantity', '2')
    auto_checkout = request.args.get('auto_checkout', 'true').lower() == 'true'
    best_available = request.args.get('best_available', 'true').lower() == 'true'
    
    if not event_id or not url:
        return jsonify({'success': False, 'error': 'Missing required parameters'}), 400
    
    try:
        # Convert quantity to integer
        quantity = int(quantity)
        if quantity < 1 or quantity > 8:
            quantity = 2  # Default to 2 if out of range
        
        # Update cart options for this event
        cart_options = {
            'event_id': event_id,
            'url': url,
            'quantity': quantity,
            'auto_checkout': auto_checkout,
            'best_available': best_available,
            'start_time': datetime.now().isoformat(),
            'status': 'Initializing cart process',
            'progress': 0
        }
        
        # Store cart options
        cart_session['activeCarts'][event_id] = cart_options
        
        # Get event details for notification
        event_details = ticket_status.get(event_id, {})
        event_name = event_details.get('name', f'Event {event_id}')
        
        # Send Discord notification about cart starting
        notification_text = (
            f"🛒 **Auto-Cart Started** 🛒\n"
            f"Event: {event_name}\n"
            f"Quantity: {quantity} ticket(s)\n"
            f"Auto-Checkout: {'Enabled' if auto_checkout else 'Disabled'}\n"
            f"Best Available: {'Enabled' if best_available else 'Disabled'}\n"
            f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_discord_notification(notification_text)
        
        # Start cart process in a background thread
        thread = threading.Thread(
            target=auto_cart_process,
            args=(event_id, url, quantity, auto_checkout, best_available)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True, 
            'message': f'Auto-cart started for {event_name}',
            'options': cart_options
        })
        
    except Exception as e:
        logger.error(f"Error starting auto-cart: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/cart-status')
def get_cart_status():
    """API endpoint to get status of active cart processes"""
    event_id = request.args.get('event_id')
    
    if event_id:
        # Return status for specific event
        active_cart = cart_session['activeCarts'].get(event_id)
        completed_cart = cart_session['completedCarts'].get(event_id)
        failed_cart = cart_session['failedCarts'].get(event_id)
        
        if active_cart:
            return jsonify({
                'status': active_cart.get('status', 'Processing...'),
                'progress': active_cart.get('progress', 0),
                'completed': False
            })
        elif completed_cart:
            return jsonify({
                'status': 'Cart process completed',
                'progress': 100,
                'completed': True,
                'completion_time': completed_cart.get('completionTime')
            })
        elif failed_cart:
            return jsonify({
                'status': f'Failed: {failed_cart.get("reason", "Unknown error")}',
                'progress': 0,
                'completed': True,
                'error': True
            })
        else:
            return jsonify({'status': 'No cart process found for this event', 'progress': 0})
    else:
        # Return all cart statuses
        return jsonify({
            'active': cart_session['activeCarts'],
            'completed': cart_session['completedCarts'],
            'failed': cart_session['failedCarts']
        })

def auto_cart_process(event_id, url, quantity, auto_checkout, best_available):
    """Background process to handle automated carting with options"""
    try:
        cart_session['activeCarts'][event_id]['status'] = 'Launching browser'
        cart_session['activeCarts'][event_id]['progress'] = 5
        
        # Initialize browser for carting
        browser = playwright.chromium.launch(headless=HEADLESS_MODE)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Navigate to ticket URL
        cart_session['activeCarts'][event_id]['status'] = 'Opening ticket page'
        cart_session['activeCarts'][event_id]['progress'] = 10
        page.goto(url, wait_until="networkidle")
        
        # Step 1: Locate and click on the appropriate ticket buttons
        cart_session['activeCarts'][event_id]['status'] = 'Looking for ticket options'
        cart_session['activeCarts'][event_id]['progress'] = 20
        
        logger.info(f"Looking for ticket selection elements for {event_id}")
        
        # Wait for page to be fully loaded
        page.wait_for_timeout(5000)
        
        # Take screenshot for debugging
        page.screenshot(path=f"screenshots/ticket_page_initial.png")
        
        # Try to find and click best available if option is enabled
        if best_available:
            try:
                cart_session['activeCarts'][event_id]['status'] = 'Selecting best available tickets'
                cart_session['activeCarts'][event_id]['progress'] = 30
                
                # Look for best available button and click it
                best_available_button = page.query_selector("button:has-text('Best Available')")
                if best_available_button:
                    best_available_button.click()
                    page.wait_for_timeout(2000)
                    logger.info("Clicked Best Available button")
                else:
                    logger.info("Best Available button not found, trying alternate methods")
            except Exception as e:
                logger.error(f"Error selecting best available: {e}")
        
        # Step 2: Set ticket quantity
        try:
            cart_session['activeCarts'][event_id]['status'] = f'Setting quantity to {quantity}'
            cart_session['activeCarts'][event_id]['progress'] = 40
            
            # Look for quantity dropdown or selector
            quantity_selector = page.query_selector("select.quantity-selector") or \
                               page.query_selector("[aria-label='Quantity']") or \
                               page.query_selector("select[name='quantity']")
                               
            if quantity_selector:
                quantity_selector.select_option(str(quantity))
                logger.info(f"Set quantity to {quantity}")
            else:
                logger.warning("Quantity selector not found, trying generic approach")
                
                # Try to find quantity buttons
                for i in range(1, quantity):
                    plus_button = page.query_selector("button:has-text('+')") or \
                                  page.query_selector(".quantity-increment")
                    if plus_button:
                        plus_button.click()
                        page.wait_for_timeout(500)
            
            page.wait_for_timeout(2000)
            page.screenshot(path=f"screenshots/after_quantity_selection.png")
            
        except Exception as e:
            logger.error(f"Error setting quantity: {e}")
        
        # Step 3: Add to cart
        try:
            cart_session['activeCarts'][event_id]['status'] = 'Adding to cart'
            cart_session['activeCarts'][event_id]['progress'] = 60
            
            # Look for add to cart button with various selectors
            add_to_cart_button = page.query_selector("button:has-text('Add to Cart')") or \
                                page.query_selector("button:has-text('Añadir')") or \
                                page.query_selector("button.add-to-cart") or \
                                page.query_selector("[data-testid='add-to-cart']")
                                
            if add_to_cart_button:
                add_to_cart_button.click()
                logger.info("Clicked Add to Cart button")
                page.wait_for_timeout(3000)
                page.screenshot(path=f"screenshots/after_add_to_cart.png")
                
                # Step 4: Proceed to checkout if auto-checkout is enabled
                if auto_checkout:
                    cart_session['activeCarts'][event_id]['status'] = 'Proceeding to checkout'
                    cart_session['activeCarts'][event_id]['progress'] = 80
                    
                    # Look for checkout button
                    checkout_button = page.query_selector("a:has-text('Checkout')") or \
                                     page.query_selector("button:has-text('Checkout')") or \
                                     page.query_selector("a:has-text('Proceed to Checkout')") or \
                                     page.query_selector("a.checkout-button")
                                     
                    if checkout_button:
                        checkout_button.click()
                        logger.info("Clicked Checkout button")
                        page.wait_for_timeout(5000)
                        page.screenshot(path=f"screenshots/checkout_final.png")
                        
                        cart_session['activeCarts'][event_id]['status'] = 'At checkout page'
                        cart_session['activeCarts'][event_id]['progress'] = 100
                        
                        # Record completion
                        cart_session['completedCarts'][event_id] = {
                            'completionTime': datetime.now().isoformat(),
                            'url': page.url
                        }
                        
                        # Remove from active carts
                        if event_id in cart_session['activeCarts']:
                            del cart_session['activeCarts'][event_id]
                        
                        # Send success notification
                        notification_text = (
                            f"✅ **Auto-Cart Completed** ✅\n"
                            f"Event: {ticket_status.get(event_id, {}).get('name', event_id)}\n"
                            f"Quantity: {quantity} ticket(s)\n"
                            f"Status: At checkout page\n"
                            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            f"**GO COMPLETE YOUR PURCHASE NOW!**"
                        )
                        send_discord_notification(notification_text, use_mentions=True)
                        
                    else:
                        logger.error("Checkout button not found")
                        
                        # Record failure
                        cart_session['failedCarts'][event_id] = {
                            'failedTime': datetime.now().isoformat(),
                            'reason': "Checkout button not found"
                        }
                        
                        # Send failure notification
                        notification_text = (
                            f"❌ **Auto-Cart Partial Success** ❌\n"
                            f"Event: {ticket_status.get(event_id, {}).get('name', event_id)}\n"
                            f"Status: Added to cart but couldn't proceed to checkout\n"
                            f"URL: {page.url}"
                        )
                        send_discord_notification(notification_text)
                else:
                    # Auto-checkout not enabled, so we're done after adding to cart
                    cart_session['activeCarts'][event_id]['status'] = 'Added to cart'
                    cart_session['activeCarts'][event_id]['progress'] = 100
                    
                    # Record completion
                    cart_session['completedCarts'][event_id] = {
                        'completionTime': datetime.now().isoformat(),
                        'url': page.url
                    }
                    
                    # Remove from active carts
                    if event_id in cart_session['activeCarts']:
                        del cart_session['activeCarts'][event_id]
                    
                    # Send success notification
                    notification_text = (
                        f"✅ **Added to Cart** ✅\n"
                        f"Event: {ticket_status.get(event_id, {}).get('name', event_id)}\n"
                        f"Quantity: {quantity} ticket(s)\n"
                        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"**Note:** Auto-checkout was disabled. Complete your purchase manually."
                    )
                    send_discord_notification(notification_text)
            else:
                logger.error("Add to cart button not found")
                
                # Record failure
                cart_session['failedCarts'][event_id] = {
                    'failedTime': datetime.now().isoformat(),
                    'reason': "Add to cart button not found"
                }
                
                # Send failure notification
                notification_text = (
                    f"❌ **Auto-Cart Failed** ❌\n"
                    f"Event: {ticket_status.get(event_id, {}).get('name', event_id)}\n"
                    f"Reason: Add to cart button not found\n"
                    f"URL: {page.url}"
                )
                send_discord_notification(notification_text)
        except Exception as e:
            logger.error(f"Error during auto-cart: {e}")
            
            # Record failure
            cart_session['failedCarts'][event_id] = {
                'failedTime': datetime.now().isoformat(),
                'reason': str(e)
            }
            
            # Remove from active carts
            if event_id in cart_session['activeCarts']:
                del cart_session['activeCarts'][event_id]
            
            # Send failure notification
            notification_text = (
                f"❌ **Auto-Cart Error** ❌\n"
                f"Event: {ticket_status.get(event_id, {}).get('name', event_id)}\n"
                f"Error: {str(e)}"
            )
            send_discord_notification(notification_text)
            
        # Close browser
        browser.close()
        
    except Exception as e:
        logger.error(f"Global error in auto-cart process: {e}")
        
        # Record failure
        cart_session['failedCarts'][event_id] = {
            'failedTime': datetime.now().isoformat(),
            'reason': str(e)
        }
        
        # Remove from active carts
        if event_id in cart_session['activeCarts']:
            del cart_session['activeCarts'][event_id]
        
        # Send failure notification
        notification_text = (
            f"❌ **Auto-Cart System Error** ❌\n"
            f"Event: {ticket_status.get(event_id, {}).get('name', event_id)}\n"
            f"System Error: {str(e)}"
        )
        send_discord_notification(notification_text)

if __name__ == '__main__':
    # Do initial check
    update_ticket_status()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
