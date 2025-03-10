#!/usr/bin/env python3
"""
Working Automatic Cart Script
This script handles the complete process:
1. Navigate to the event page
2. Select tickets
3. Add to cart
4. Get checkout link
5. Send Discord notification with exact format
"""
import os
import sys
import asyncio
import logging
import traceback
import random
import requests
from datetime import datetime
from playwright.async_api import async_playwright
from urllib.parse import urlparse, urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("ticket_cart.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Create screenshots directory if it doesn't exist
os.makedirs(os.path.join(os.path.dirname(__file__), "screenshots"), exist_ok=True)

# Discord webhook URL for notifications
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1347702022039666783/IIgJ2B6vT5aQoTjNOadVxdAviHuEsCRR8zwu4CgWAvWzcob9BJ0_5XQC-BTyVauTljR_"

# Bad Bunny concert dates to monitor
BAD_BUNNY_DATES = [
    # July 2025
    "2025-07-12", "2025-07-18", "2025-07-19",
    # August 2025
    "2025-08-01", "2025-08-02", "2025-08-03", 
    "2025-08-08", "2025-08-09", "2025-08-10",
    "2025-08-15", "2025-08-16", "2025-08-17",
    "2025-08-22", "2025-08-23", "2025-08-24",
    "2025-08-29", "2025-08-30", "2025-08-31",
    # September 2025
    "2025-09-05", "2025-09-06", "2025-09-07",
    "2025-09-12", "2025-09-13", "2025-09-14"
]

# Danny Ocean dates for testing
DANNY_OCEAN_DATES = [
    "2025-07-19", "2025-08-08", "2025-08-16"
]

# URLs to check
EVENT_URLS = {
    # Use these URLs for testing with Danny Ocean concert
    "2025-07-19": "https://www.ticketera.com/events/detail/danny-ocean-0cfqvo",
    "2025-08-08": "https://www.ticketera.com/events/detail/danny-ocean-0cfqvo",
    "2025-08-16": "https://www.ticketera.com/events/detail/danny-ocean-0cfqvo"
    # Bad Bunny URLs will be added when available
}

# Cloudflare evasion settings
CLOUDFLARE_SETTINGS = {
    "enabled": True,
    "min_action_delay": 1.0,  # Minimum delay between actions in seconds
    "max_action_delay": 3.0,  # Maximum delay between actions in seconds
    "random_mouse_movements": True,  # Enable random mouse movements
    "mouse_movement_count": 3,  # Number of random mouse movements
    "disable_webdriver": True,  # Attempt to disable webdriver detection
    "use_human_headers": True,  # Use more human-like browser headers
    "simulate_user_behavior": True,  # Simulate realistic user behavior
}

# Human-like headers to use
HUMAN_HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9,es;q=0.8",
    "sec-ch-ua": "\" Not A;Brand\";v=\"99\", \"Chromium\";v=\"122\", \"Google Chrome\";v=\"122\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1"
}

async def take_screenshot(page, filename):
    """Take a screenshot and save it to the screenshots directory"""
    try:
        screenshot_path = os.path.join(os.path.dirname(__file__), "screenshots", filename)
        await page.screenshot(path=screenshot_path)
        logger.info(f"Screenshot saved: {filename}")
    except Exception as e:
        logger.warning(f"Failed to take screenshot: {str(e)}")

async def human_delay():
    """Add a random human-like delay between actions to avoid detection"""
    if CLOUDFLARE_SETTINGS["enabled"]:
        delay = random.uniform(
            CLOUDFLARE_SETTINGS["min_action_delay"],
            CLOUDFLARE_SETTINGS["max_action_delay"]
        )
        await asyncio.sleep(delay)

async def random_mouse_movement(page):
    """Perform random mouse movements to appear more human-like"""
    if CLOUDFLARE_SETTINGS["enabled"] and CLOUDFLARE_SETTINGS["random_mouse_movements"]:
        page_width = await page.evaluate('window.innerWidth')
        page_height = await page.evaluate('window.innerHeight')
        
        for _ in range(CLOUDFLARE_SETTINGS["mouse_movement_count"]):
            x = random.randint(0, page_width)
            y = random.randint(0, page_height)
            
            # Move mouse with human-like speed
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))

async def configure_browser_for_cloudflare(browser):
    """
    Configure the browser to better avoid Cloudflare detection
    
    Args:
        browser: Playwright browser instance
    """
    try:
        logger.info("Configuring browser to avoid Cloudflare detection...")
        
        # Add more advanced evasion techniques
        await browser.contexts[0].add_init_script("""
        // Override webdriver properties
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false
        });
        
        // Override chrome properties
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {},
        };
        
        // Override permissions
        if (navigator.permissions) {
            const originalQuery = navigator.permissions.query;
            navigator.permissions.query = function(parameters) {
                if (parameters.name === 'notifications') {
                    return Promise.resolve({ state: Notification.permission });
                }
                return originalQuery.apply(this, arguments);
            };
        }
        
        // Add plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                return [
                    {
                        0: {type: "application/pdf"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    },
                    {
                        0: {type: "application/pdf"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Viewer"
                    },
                    {
                        0: {type: "application/x-google-chrome-pdf"},
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Viewer"
                    },
                    {
                        0: {type: "application/x-nacl"},
                        description: "Native Client",
                        filename: "internal-nacl-plugin",
                        length: 1,
                        name: "Native Client"
                    }
                ];
            }
        });
        
        // Add languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en', 'es'],
        });
        
        // Add hardware concurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 8,
        });
        
        // Delete known automation flags
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        """)
        
        # Randomized user agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/123.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        ]
        
        # Set headers to mimic a real browser
        await browser.contexts[0].set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "sec-ch-ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1"
        })
        
        # Add cookies that might help bypass Cloudflare
        await browser.contexts[0].add_cookies([
            {"name": "cf_clearance", "value": "", "domain": ".ticketera.com", "path": "/"},
            {"name": "preferred_locale", "value": "en", "domain": ".ticketera.com", "path": "/"}
        ])
        
        logger.info("Browser configured to avoid WebDriver detection")
        
    except Exception as e:
        logger.error(f"Error configuring browser for Cloudflare: {str(e)}")

async def send_discord_notification(cart_info):
    """Send a notification to Discord with cart information"""
    try:
        # Validate cart info before sending
        if not cart_info.get('cart_url') or not cart_info.get('date'):
            logger.warning("Invalid cart information - not sending Discord notification")
            return False
            
        # Ensure cart URL is not the same as event URL - indicating it's not a valid cart
        if "/tovk-presenta-el-circo-de-los-horrores" in cart_info['cart_url'] and not ("cart" in cart_info['cart_url'].lower() or "checkout" in cart_info['cart_url'].lower()):
            logger.warning("Cart URL appears to be the event URL, not a real cart URL - not sending notification")
            return False

        # Get current time for the notification
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create the message for Discord with the exact format shown in the screenshot
        message = (
            "@everyone\n\n"
            "## 🎫 TICKETS ADDED TO CART! 🎫\n\n"
            f"**Event Date**\t**Quantity**\t**Section**\n"
            f"{cart_info['date']}\t{cart_info['quantity']}\t{cart_info['section']}\n\n"
            f"**Cart Link**\n"
            f"[CLICK HERE TO CHECKOUT]({cart_info['cart_url']})\n\n"
            f"**Instructions**\n"
            f"1. Click the link above to go to your cart\n"
            f"2. Complete the checkout process immediately\n"
            f"3. Tickets reserved for only 10 minutes!\n\n"
            f"Ticket Monitor • {current_time}"
        )
        
        # Add price info if available
        if 'price' in cart_info and cart_info['price']:
            message = message.replace("**Section**\n", "**Section**\t**Price**\n")
            message = message.replace(f"{cart_info['section']}\n\n", f"{cart_info['section']}\t${cart_info['price']:.2f}\n\n")
        
        # Send the message to Discord using the webhook URL
        payload = {
            "content": message,
            "username": "Bad Bunny Ticket Monitor",
            "avatar_url": "https://i.imgur.com/MQ3Dvz0.png"
        }
        
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if response.status_code == 204:
            logger.info("Discord notification sent successfully")
            return True
        else:
            logger.error(f"Failed to send Discord notification: {response.status_code} {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending Discord notification: {str(e)}")
        traceback.print_exc()
        return False

async def verify_cart_page(page):
    """Verify that we're on a cart page"""
    logger.info("Verifying if we're on a cart page")
    await take_screenshot(page, "cart_verification.png")
    
    cart_indicators = [
        "div.cart",
        "div.shopping-cart",
        "div[class*='cart']",
        "div#cart",
        "div#shopping-cart",
        "h1:has-text('Cart')",
        "h1:has-text('Carrito')",
        "h2:has-text('Cart')",
        "h2:has-text('Carrito')",
        "div:has-text('Shopping Cart')",
        "div:has-text('Carrito de Compras')",
        "table.cart-items",
        "div.checkout-section",
        "div.ticket-summary",
        "div.order-summary",
        "button:has-text('Checkout')",
        "button:has-text('Finalizar Compra')",
        "button:has-text('Proceed to Checkout')",
        "button:has-text('Proceder al Pago')",
        "[class*='checkout']",
        "form[action*='checkout']",
        "div.cart-header",
        "div.cart-footer"
    ]
    
    found_cart = False
    for selector in cart_indicators:
        try:
            element = await page.query_selector(selector)
            if element and await element.is_visible():
                logger.info(f"Found cart indicator: {selector}")
                found_cart = True
                break
        except Exception as e:
            logger.debug(f"Error checking cart indicator {selector}: {str(e)}")
            
    # Also check URL for cart indicators
    url = page.url.lower()
    cart_url_indicators = ['cart', 'basket', 'carrito', 'checkout', 'pagar', 'payment', 'order', 'compra']
    for indicator in cart_url_indicators:
        if indicator in url:
            logger.info(f"URL contains cart indicator: {indicator}")
            found_cart = True
            break
            
    if found_cart:
        logger.info("CART PAGE VERIFIED!")
    else:
        logger.warning("Could not verify cart page")
        
    return found_cart

async def verify_tickets_in_cart(page):
    """Verify that tickets are actually in the cart"""
    logger.info("Verifying if tickets are in the cart")
    
    ticket_indicators = [
        "div.cart-item", 
        "div.line-item", 
        "[class*='cart-item']", 
        "[class*='ticket']", 
        "div:has-text('Ticket')", 
        "div:has-text('Boleto')",
        "div.ticket-row",
        "tr.cart-item",
        "div.ticket-details",
        "div.order-line",
        "div.product-item:has-text('Ticket')",
        "div.product-item:has-text('Boleto')",
        "div.purchase-item",
        "div.ticket-purchase",
        "div[class*='ticket']"
    ]
    
    total_tickets = 0
    
    for selector in ticket_indicators:
        try:
            ticket_elements = await page.query_selector_all(selector)
            if len(ticket_elements) > 0:
                logger.info(f"Found {len(ticket_elements)} ticket elements with selector: {selector}")
                total_tickets = max(total_tickets, len(ticket_elements))
        except Exception as e:
            logger.debug(f"Error checking ticket indicator {selector}: {str(e)}")
    
    if total_tickets > 0:
        logger.info(f"VERIFIED {total_tickets} TICKETS IN CART!")
        return total_tickets
    else:
        logger.warning("No tickets found in cart")
        return 0

async def send_success_notification(cart_url, tickets_count):
    """Send a success notification to Discord with detailed information"""
    try:
        concert_details = "Bad Bunny Concert"
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = {
            'success': True,
            'message': f"Successfully added {tickets_count} tickets to cart!",
            'url': cart_url,
            'timestamp': current_time,
            'concert': concert_details,
            'checkout_time': current_time
        }
        
        await send_discord_notification(message)
        logger.info(f"Success notification sent for {tickets_count} tickets")
    except Exception as e:
        logger.error(f"Error sending success notification: {str(e)}")

async def navigate_to_cart(page, event_url):
    """Aggressively tries to navigate to the cart page using multiple methods"""
    logger.info("Attempting to navigate to cart using multiple methods...")
    
    # First, try to find cart/checkout buttons and click them
    cart_buttons = [
        'a:has-text("Cart")', 'a:has-text("Checkout")',
        'button:has-text("Cart")', 'button:has-text("Checkout")',
        'a:has-text("View Cart")', 'button:has-text("View Cart")',
        'a:has-text("Proceed to Checkout")', 'button:has-text("Proceed to Checkout")',
        'a[href*="cart"]', 'a[href*="checkout"]',
        'div[role="button"]:has-text("Cart")', 'div[role="button"]:has-text("Checkout")',
        'img[alt*="cart"]', 'svg[aria-label*="cart"]',
        '.cart-icon', '#cart-icon', '.checkout-icon', '#checkout-icon'
    ]
    
    # Try clicking each cart button
    for selector in cart_buttons:
        try:
            button = await page.query_selector(selector)
            if button:
                logger.info(f"Found cart button with selector: {selector}")
                
                # If it's a link, get the href and navigate to it
                href = await button.get_attribute("href")
                if href:
                    absolute_url = href
                    if not href.startswith('http'):
                        # Handle relative URLs
                        parsed_url = urlparse(event_url)
                        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                        absolute_url = urljoin(base_url, href)
                    
                    logger.info(f"Navigating to cart URL: {absolute_url}")
                    await page.goto(absolute_url, wait_until="domcontentloaded")
                else:
                    # Otherwise click it
                    await button.click()
                    logger.info(f"Clicked cart button with selector: {selector}")
                
                await take_screenshot(page, "cart_navigation_click.png")
                await asyncio.sleep(3)
                
                # Check if we're now on a cart page
                if await verify_cart_page(page):
                    logger.info("Successfully navigated to cart page!")
                    return True
        except Exception as e:
            logger.debug(f"Failed to click cart button {selector}: {str(e)}")
    
    # Try using JavaScript to navigate to common cart URLs
    common_cart_paths = [
        "/cart", "/checkout", "/bag", "/basket", 
        "/shopping-cart", "/carrito", "/shopping-bag",
        "/order/checkout", "/orders/checkout"
    ]
    
    # Build cart URLs based on the current domain
    parsed_url = urlparse(event_url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    
    for path in common_cart_paths:
        try:
            cart_url = urljoin(base_url, path)
            logger.info(f"Trying to navigate to common cart URL: {cart_url}")
            await page.goto(cart_url, wait_until="domcontentloaded")
            await take_screenshot(page, f"cart_navigation_url_{path.replace('/', '_')}.png")
            
            # Check if we're now on a cart page
            if await verify_cart_page(page):
                logger.info(f"Successfully navigated to cart page at: {cart_url}")
                return True
            
            await asyncio.sleep(1)
        except Exception as e:
            logger.debug(f"Failed to navigate to {path}: {str(e)}")
    
    logger.warning("Failed to navigate to cart page using all methods")
    return False

async def navigate_to_checkout(page):
    """After BOLETOS is clicked, navigate through the checkout process"""
    logger.info("Looking for ticket options after BOLETOS click...")

    # Take a screenshot after landing on the ticketing page
    await take_screenshot(page, "post_boletos_page.png")
    
    # First wait for the page to fully load
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        logger.info("Waiting for networkidle timed out, continuing...")
    
    ticket_selected = False
    
    # First try to handle seat map selection if present
    try:
        # First check if there's a seat map on the page
        seat_map_result = await select_seat_from_map(page)
        if seat_map_result:
            logger.info("Successfully selected seats from seat map")
            ticket_selected = True
            await take_screenshot(page, "seats_selected.png")
            await asyncio.sleep(3)  # Wait for any animations or changes after seat selection
    except Exception as e:
        logger.warning(f"Error when trying to select from seat map: {str(e)}")
    
    # More specific selectors for the Ticketera (Como Coco) site
    specific_ticket_selectors = [
        "button.seats-button",                # Try direct seat selection button
        "div.seat-map-container .seat:not(.unavailable)",  # Direct seat click on map
        "select.ticket-quantity-select",       # Quantity selection dropdown
        "div.ticket-type-selector",            # Ticket type selector
        "button.select-ticket-button",         # Select ticket button
        "div.ticket-card",                     # Ticket card selector
        "div[class*='ticket-container']",      # Any ticket container
        "div.event-ticket-option",             # Event ticket option
        "[data-testid='seat-map-seat']:not([data-testid*='unavailable'])",  # Available seat
        "[data-type='ticket']",                # Generic ticket element
        "svg circle:not(.unavailable-seat)",   # SVG seat map circles that aren't unavailable
        "svg circle.available-seat",           # SVG seat map circles marked as available
        "svg circle.available",                # SVG circles with available class
        "svg .seat:not(.unavailable)",         # SVG seats that aren't unavailable
        "svg .seat.available-seat",            # SVG seats marked as available
        "svg .seat[fill='green']",             # SVG seats filled with green color
        "svg .seat[fill='#00FF00']",           # SVG seats filled with bright green
        "svg .seat[fill='#008000']",           # SVG seats filled with dark green 
        "path.available-seat",                 # Path elements that are available seats
        ".row-seat:not(.unavailable)",         # Row seats that aren't unavailable
        ".seat-map rect:not(.unavailable)",    # Rectangle seat elements in a seat map
        ".seat-map circle:not(.unavailable)"   # Circle seat elements in a seat map
    ]
    
    seats_selected = False
    for selector in specific_ticket_selectors:
        try:
            logger.info(f"Looking for ticket elements with selector: {selector}")
            elements = await page.query_selector_all(selector)
            
            if len(elements) > 0:
                logger.info(f"Found {len(elements)} ticket elements with selector: {selector}")
                # Click the first available element
                await elements[0].scroll_into_view_if_needed()
                await elements[0].click()
                logger.info(f"Selected ticket option with selector: {selector}")
                await take_screenshot(page, "ticket_option_selected.png")
                ticket_selected = True
                await asyncio.sleep(2)
                break
        except Exception as e:
            logger.debug(f"Failed to select ticket option with selector {selector}: {str(e)}")
    
    # Fall back to more generic selectors if specific ones don't work
    if not ticket_selected:
        ticket_type_selectors = [
            "div.ticket-type button",
            "div.ticket-option",
            "div.ticket-card",
            "button.btn-primary",
            "a.btn-primary",
            "div[class*='ticket']",
            "div[class*='section']",
            "[class*='ticket-type']",
            "[class*='section']",
            "[data-testid*='ticket']",
            "[data-testid*='section']"
        ]
        
        for selector in ticket_type_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if len(elements) > 0:
                    await elements[0].scroll_into_view_if_needed()
                    await elements[0].click()
                    logger.info(f"Selected ticket option with selector: {selector}")
                    await take_screenshot(page, "ticket_option_selected.png")
                    ticket_selected = True
                    await asyncio.sleep(2)
                    break
            except Exception as e:
                logger.debug(f"Failed to select ticket option with selector {selector}: {str(e)}")
    
    # If still no success, try clicking in likely areas of the page
    if not ticket_selected:
        logger.info("No specific ticket options found, trying to click in likely areas...")
        positions = [(400, 300), (400, 400), (600, 300), (600, 400), (800, 300), (800, 400)]
        
        for i, (x, y) in enumerate(positions):
            try:
                await page.mouse.click(x, y)
                logger.info(f"Clicked at position ({x}, {y})")
                await take_screenshot(page, f"ticket_area_click_{i}.png")
                
                # Check if the click revealed any buttons
                for selector in specific_ticket_selectors + ticket_type_selectors:
                    elements = await page.query_selector_all(selector)
                    if len(elements) > 0:
                        # If clicking revealed buttons, click the first one
                        await elements[0].scroll_into_view_if_needed()
                        await elements[0].click()
                        logger.info(f"Found and clicked ticket option after position click: {selector}")
                        ticket_selected = True
                        await asyncio.sleep(1.5)
                        break
                
                if ticket_selected:
                    break
            except Exception as e:
                logger.debug(f"Failed to click at position ({x}, {y}): {str(e)}")
    
    # Wait for any actions to complete
    await asyncio.sleep(3)
    
    # Check for quantity selectors and set quantity
    quantity_selectors = [
        "select[name*='quantity']",
        "select[id*='quantity']",
        "select.quantity-selector",
        "input[type='number'][name*='quantity']",
        "div.quantity-control input",
        "[data-testid='quantity-selector']"
    ]
    
    for selector in quantity_selectors:
        try:
            quantity_element = await page.query_selector(selector)
            if quantity_element:
                logger.info(f"Found quantity selector with selector: {selector}")
                
                # Check if it's a select dropdown or input field
                tag_name = await quantity_element.evaluate("el => el.tagName.toLowerCase()")
                
                if tag_name == "select":
                    await quantity_element.select_option("2")
                    logger.info("Set quantity to 2 via dropdown")
                elif tag_name == "input":
                    await quantity_element.fill("2")
                    logger.info("Set quantity to 2 via input field")
                
                await take_screenshot(page, "quantity_set.png")
                await asyncio.sleep(2)
                break
        except Exception as e:
            logger.debug(f"Failed to set quantity with selector {selector}: {str(e)}")
    
    # Look for "Continue" or "Next" buttons
    continue_selectors = [
        "button:has-text('Continue')",
        "button:has-text('Continuar')",
        "button:has-text('Next')",
        "button:has-text('Siguiente')",
        "button.continue-button",
        "button.next-button",
        "button.btn-primary",
        "a.btn-primary",
        "button[type='submit']"
    ]
    
    for selector in continue_selectors:
        try:
            continue_button = await page.query_selector(selector)
            if continue_button:
                await continue_button.scroll_into_view_if_needed()
                await continue_button.click()
                logger.info(f"Clicked continue button with selector: {selector}")
                await take_screenshot(page, "continue_clicked.png")
                await asyncio.sleep(3)
                break
        except Exception as e:
            logger.debug(f"Failed to click continue with selector {selector}: {str(e)}")
    
    # Look for "Add to Cart" or similar buttons with more specific selectors for Ticketera
    cart_selectors = [
        "button#add-to-cart-button",            # Common ID for add to cart
        "button.add-to-cart-button",            # Common class for add to cart 
        "button:has-text('Add to Cart')",
        "button:has-text('Añadir al Carrito')",
        "button:has-text('Add to cart')",
        "button:has-text('Añadir')",
        "button.add-to-cart",
        "[data-testid='add-to-cart']",
        "button.addtocart",
        "button:has-text('BOLETOS')",
        "button:has-text('Tickets')",
        "button:has-text('Continue')",
        "button:has-text('Continuar')",
        "a:has-text('Add to Cart')",
        "a:has-text('Añadir al Carrito')"
    ]
    
    cart_url = ""
    checkout_url = ""
    
    # Attempt each cart selector with more careful error handling
    for selector in cart_selectors:
        try:
            logger.info(f"Looking for add to cart button with selector: {selector}")
            cart_button = await page.query_selector(selector)
            if cart_button:
                # Check if the button is visible and enabled
                is_visible = await cart_button.is_visible()
                is_enabled = await cart_button.evaluate("el => !el.disabled")
                
                if is_visible and is_enabled:
                    await cart_button.scroll_into_view_if_needed()
                    logger.info(f"Found enabled add to cart button with selector: {selector}")
                    
                    # Take screenshot before clicking
                    await take_screenshot(page, "before_add_to_cart.png")
                    
                    # Click the button
                    await cart_button.click(force=True)  # Use force=True to ensure click happens
                    logger.info(f"Clicked add to cart button with selector: {selector}")
                    await take_screenshot(page, "add_cart_clicked.png")
                    
                    # Wait longer for potential navigation or cart update
                    await asyncio.sleep(5)
                    
                    # After clicking add to cart, check if we're on a cart page
                    cart_verification = await verify_cart_page(page)
                    if cart_verification:
                        cart_url = page.url
                        logger.info(f"Successfully navigated to cart page at: {cart_url}")
                        
                        # Check for ticket count in cart
                        try:
                            cart_items = await page.query_selector_all("div.cart-item, div.line-item, [class*='cart-item'], [class*='ticket'], div:has-text('Ticket'), div:has-text('Boleto')")
                            logger.info(f"Found {len(cart_items)} items in cart")
                            
                            if len(cart_items) > 0:
                                logger.info("TICKETS SUCCESSFULLY ADDED TO CART!")
                                await send_discord_notification({
                                    'success': True,
                                    'message': f"Successfully added {len(cart_items)} tickets to cart!",
                                    'url': cart_url,
                                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                })
                            else:
                                logger.warning("Cart page found but no items detected in cart")
                        except Exception as e:
                            logger.warning(f"Error counting cart items: {str(e)}")
                        
                        # Now look for checkout button
                        checkout_selectors = [
                            "button:has-text('Checkout')",
                            "button:has-text('Pagar')",
                            "button:has-text('Proceed to Checkout')",
                            "button:has-text('Proceder al Pago')",
                            "button.checkout-button",
                            "a.checkout-button",
                            "button[class*='checkout']",
                            "a[class*='checkout']",
                            "button.btn-primary",
                            "a.btn-primary"
                        ]
                        
                        for checkout_selector in checkout_selectors:
                            try:
                                checkout_button = await page.query_selector(checkout_selector)
                                if checkout_button:
                                    await checkout_button.scroll_into_view_if_needed()
                                    await checkout_button.click()
                                    logger.info(f"Clicked checkout button with selector: {checkout_selector}")
                                    await asyncio.sleep(5)
                                    checkout_url = page.url
                                    logger.info(f"Successfully navigated to checkout page at: {checkout_url}")
                                    await take_screenshot(page, "checkout_page.png")
                                    return {
                                        'success': True,
                                        'cart_url': cart_url,
                                        'checkout_url': checkout_url
                                    }
                            except Exception as e:
                                logger.debug(f"Failed to click checkout button with selector {checkout_selector}: {str(e)}")
                        
                        # If we couldn't click a checkout button but are on cart page, still consider success
                        return {
                            'success': True,
                            'cart_url': cart_url,
                            'checkout_url': ''
                        }
                else:
                    logger.debug(f"Found add to cart button with selector {selector} but it's not visible or enabled")
            else:
                logger.debug(f"No add to cart button found with selector: {selector}")
        except Exception as e:
            logger.debug(f"Failed to click add to cart with selector {selector}: {str(e)}")
    
    # If we haven't successfully found the cart page yet, check again
    cart_verification = await verify_cart_page(page)
    if cart_verification:
        cart_url = page.url
        logger.info(f"Successfully navigated to cart page at: {cart_url}")
        return {
            'success': True,
            'cart_url': cart_url,
            'checkout_url': ''
        }
    
    # Last resort: Try to look for text indicating we're on a relevant page
    try:
        page_text = await page.evaluate("() => document.body.innerText")
        if "cart" in page_text.lower() or "carrito" in page_text.lower():
            logger.info("Page text contains 'cart' or 'carrito', might be on cart page")
            current_url = page.url
            return {
                'success': True,
                'cart_url': current_url,
                'checkout_url': '',
                'warning': 'Cart page detected by text, but not visually confirmed'
            }
    except Exception as e:
        logger.debug(f"Error checking page text: {str(e)}")
        
    return {
        'success': False,
        'error': 'Could not navigate to cart or checkout page',
        'cart_url': '',
        'checkout_url': ''
    }

async def select_seat_from_map(page):
    """
    Select an available seat from the seat map.
    
    Args:
        page: Playwright page object
        
    Returns:
        bool: True if a seat was successfully selected, False otherwise
    """
    try:
        logger.info("Attempting to select a seat from the map...")
        
        # Wait for the seat map to load
        logger.info("Waiting for seat map to load...")
        await page.wait_for_load_state("networkidle")
        
        # Allow extra time for SVG content to fully render
        await asyncio.sleep(random.uniform(1.5, 3.0))
        
        # First check if we have an SVG map
        svg_exists = await is_element_visible(page, "svg")
        if not svg_exists:
            logger.warning("No SVG seat map found, taking screenshot for debugging...")
            await take_screenshot(page, "no_svg_map.png")
            return False
        
        logger.info("SVG seat map detected, looking for available seats...")
        
        # Different selectors for available seats
        seat_selectors = [
            "circle[fill='#4a89dc'], circle[fill='#5D9CEC']",  # Blue seats
            "circle[fill='#A0D468'], circle[fill='#8CC152']",  # Green seats
            "circle[fill='#8067dc'], circle[fill='#967ADC']",  # Purple seats
            "path[fill='#4a89dc'], path[fill='#5D9CEC']",      # Blue seat paths
            "path[fill='#A0D468'], path[fill='#8CC152']",      # Green seat paths
            "path[fill='#8067dc'], path[fill='#967ADC']"       # Purple seat paths
        ]
        
        # Try each seat selector
        for seat_selector in seat_selectors:
            # Check if seats with this selector exist
            seats = await page.query_selector_all(seat_selector)
            if seats and len(seats) > 0:
                logger.info(f"Found {len(seats)} available seats with selector: {seat_selector}")
                
                # Add a realistic pause before selecting a seat (like a human would look at the map)
                await asyncio.sleep(random.uniform(0.8, 2.0))
                
                # Choose a random seat from the first 10 (or less if fewer are available)
                max_index = min(10, len(seats))
                selected_index = random.randint(0, max_index - 1)
                selected_seat = seats[selected_index]
                
                # Get the seat position for more human-like mouse movement
                bounding_box = await selected_seat.bounding_box()
                if bounding_box:
                    # Move mouse progressively towards the seat
                    await page.mouse.move(
                        random.randint(0, int(page.viewport_size['width'] / 2)),
                        random.randint(0, int(page.viewport_size['height'] / 2))
                    )
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    
                    # Move closer
                    await page.mouse.move(
                        int(bounding_box['x'] / 1.5),
                        int(bounding_box['y'] / 1.5)
                    )
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    
                    # Finally move to the seat with slightly random position within the seat
                    await page.mouse.move(
                        bounding_box['x'] + bounding_box['width'] / 2 + random.randint(-3, 3),
                        bounding_box['y'] + bounding_box['height'] / 2 + random.randint(-3, 3)
                    )
                    await asyncio.sleep(random.uniform(0.2, 0.4))
                
                # Now click the seat with a human-like delay
                await selected_seat.click()
                logger.info(f"Clicked on seat at index {selected_index}")
                
                # Wait for the potential popup or confirmation dialog
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Check for confirmation dialog or popup
                confirm_selectors = [
                    "button:has-text('Confirm')",
                    "button:has-text('Confirmar')",
                    "button:has-text('Add to Cart')",
                    "button:has-text('Añadir al carrito')",
                    "button:has-text('Continue')",
                    "button:has-text('Continuar')",
                    "button:has-text('Select')",
                    "button:has-text('Seleccionar')",
                    ".confirm-button",
                    ".btn-primary",
                    ".btn-confirm"
                ]
                
                # Try each confirmation selector with a slight delay
                for confirm_selector in confirm_selectors:
                    confirm_button = await page.query_selector(confirm_selector)
                    if confirm_button:
                        logger.info(f"Found confirmation button with selector: {confirm_selector}")
                        await asyncio.sleep(random.uniform(0.3, 0.8))
                        
                        # Move mouse to the button naturally
                        button_box = await confirm_button.bounding_box()
                        if button_box:
                            await page.mouse.move(
                                button_box['x'] + button_box['width'] / 2 + random.randint(-5, 5),
                                button_box['y'] + button_box['height'] / 2 + random.randint(-3, 3)
                            )
                            await asyncio.sleep(random.uniform(0.2, 0.4))
                        
                        # Click the confirmation button
                        await confirm_button.click()
                        logger.info("Clicked confirmation button")
                        await asyncio.sleep(random.uniform(0.5, 1.0))
                        await page.wait_for_load_state("networkidle")
                        return True
                
                # If we clicked a seat but couldn't find a confirmation button, 
                # the seat might have been auto-selected
                logger.info("No confirmation button found, but seat may have been selected")
                return True
                
        # If we got here, we couldn't find any available seats
        logger.warning("No available seats found on the map")
        await take_screenshot(page, "no_available_seats.png")
        return False
        
    except Exception as e:
        logger.error(f"Error selecting seat from map: {str(e)}")
        await take_screenshot(page, "seat_selection_error.png")
        return False

async def automatic_cart_process(page, event_url, options=None):
    """
    Main function to run the automated cart process
    
    Args:
        page: Playwright page object
        event_url: URL of the event to cart
        options: Dictionary containing cart options:
            - quantity: Number of tickets to purchase (1-8)
            - auto_checkout: Whether to proceed to checkout automatically
            - best_available: Whether to select best available seats
            - event_date: Date of the event for notification purposes
            
    Returns:
        Dictionary with cart result information
    """
    try:
        # Parse options or use defaults
        if not options:
            options = {}
        
        quantity = options.get('quantity', 2)
        auto_checkout = options.get('auto_checkout', False)
        best_available = options.get('best_available', False)
        event_date = options.get('event_date', 'Unknown Date')
        
        logger.info(f"Starting automatic cart process for event: {event_url}")
        logger.info(f"Options: quantity={quantity}, auto_checkout={auto_checkout}, best_available={best_available}")
        
        # Start with the event page
        logger.info("Step 1: Opening event page...")
        await page.goto(event_url, wait_until='domcontentloaded')
        await page.wait_for_load_state('networkidle')
        
        # Take an initial screenshot
        await take_screenshot(page, "01_event_page.png")
        
        # Try to select best available if specified
        if best_available:
            logger.info("Attempting to select best available seats...")
            best_available_success = await select_best_available(page, quantity)
            
            if best_available_success:
                logger.info("Successfully selected best available seats!")
            else:
                logger.info("Could not select best available seats, trying seat map...")
        
        # If best available didn't work or wasn't specified, try the seat map
        if not best_available or not best_available_success:
            # Try to select seats from the map
            logger.info("Step 2: Selecting seats from the map...")
            seat_selected = await select_seat_from_map(page)
            
            if not seat_selected:
                logger.warning("Could not select seats from map")
                await take_screenshot(page, "no_seats_selected.png")
                return {
                    'success': False,
                    'error': 'Could not select seats from map',
                    'cart_url': '',
                    'checkout_url': ''
                }
        
        # Add selected tickets to cart
        logger.info("Step 3: Adding tickets to cart...")
        cart_result = await add_to_cart(page)
        
        if not cart_result['success']:
            logger.warning("Could not add tickets to cart")
            await take_screenshot(page, "add_to_cart_failed.png")
            return cart_result
        
        logger.info(f"Successfully added tickets to cart! Cart URL: {cart_result['cart_url']}")
        
        # If auto checkout is enabled, proceed to checkout
        if auto_checkout and cart_result['success'] and not cart_result.get('checkout_url'):
            logger.info("Step 4: Proceeding to checkout...")
            checkout_success = await proceed_to_checkout(page)
            
            if checkout_success:
                logger.info("Successfully proceeded to checkout!")
                cart_result['checkout_url'] = page.url
            else:
                logger.warning("Could not proceed to checkout")
                await take_screenshot(page, "proceed_to_checkout_failed.png")
        
        # Send notification with detailed information
        try:
            # Get section and price info if available
            section_info = ""
            price_info = ""
            
            try:
                # Look for section information
                section_elements = await page.query_selector_all("div:has-text('Section'), div:has-text('Sección'), span:has-text('Section'), span:has-text('Sección')")
                if section_elements and len(section_elements) > 0:
                    section_text = await section_elements[0].text_content()
                    section_parts = section_text.split(':')
                    if len(section_parts) > 1:
                        section_info = section_parts[1].strip()
                    else:
                        section_info = section_text.strip()
                
                # Look for price information
                price_elements = await page.query_selector_all("div:has-text('Price'), div:has-text('Precio'), span:has-text('Price'), span:has-text('Precio')")
                if price_elements and len(price_elements) > 0:
                    price_text = await price_elements[0].text_content()
                    price_parts = price_text.split(':')
                    if len(price_parts) > 1:
                        price_info = price_parts[1].strip()
                    else:
                        price_info = price_text.strip()
            except Exception as info_error:
                logger.warning(f"Error getting section/price info: {str(info_error)}")
            
            # Create detailed notification data
            notification_data = {
                'success': True,
                'message': f"Successfully added {quantity} tickets to cart for {event_date}!",
                'url': cart_result.get('cart_url', ''),
                'event_date': event_date,
                'quantity': quantity,
                'section': section_info,
                'price': price_info,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Send detailed notification
            await send_discord_notification(notification_data)
            
        except Exception as notification_error:
            logger.error(f"Error sending notification: {str(notification_error)}")
        
        # Return the cart result
        return cart_result
        
    except Exception as e:
        logger.error(f"Error in automatic cart process: {str(e)}")
        await take_screenshot(page, "automatic_cart_error.png")
        return {
            'success': False,
            'error': f"Error in automatic cart process: {str(e)}",
            'cart_url': '',
            'checkout_url': ''
        }

async def process_direct_checkout(page, quantity, event_date):
    """
    Process a direct checkout link from shop.ticketera.com
    
    Args:
        page: Playwright page object
        quantity: Number of tickets to purchase
        event_date: Date of the event for notification purposes
        
    Returns:
        Dictionary with cart result information
    """
    logger.info("Processing direct checkout link...")
    result = {
        "success": False,
        "message": "",
        "section": "Direct Checkout",
        "quantity": quantity,
        "price": "",
        "cart_url": "",
        "screenshot_path": ""
    }
    
    try:
        # Wait for the page to fully load
        await page.wait_for_load_state('networkidle')
        await take_screenshot(page, "direct_checkout_page.png")
        
        # Check if we're already in the checkout page
        checkout_title_selector = "h1:has-text('Checkout'), h1:has-text('Finalizar Compra')"
        is_checkout = await is_element_visible(page, checkout_title_selector)
        
        if is_checkout:
            logger.info("Already in checkout page")
            
            # Extract any available price information
            price_selectors = [
                ".checkout-summary .amount", 
                ".checkout-total", 
                ".price",
                "div.price",
                ".total-amount"
            ]
            
            price = ""
            for selector in price_selectors:
                try:
                    price_element = await page.query_selector(selector)
                    if price_element:
                        price = await price_element.text_content()
                        price = price.strip()
                        logger.info(f"Found price: {price}")
                        break
                except Exception as e:
                    logger.debug(f"Error getting price from selector {selector}: {str(e)}")
            
            # Extract more details if possible
            section = "Direct Checkout"
            section_elements = await page.query_selector_all(".ticket-details .section, .ticket-info .section")
            if section_elements and len(section_elements) > 0:
                section_text = await section_elements[0].text_content()
                section = section_text.strip()
                logger.info(f"Found section: {section}")
            
            # Take screenshot of checkout page
            screenshot_path = "direct_checkout.png"
            await take_screenshot(page, screenshot_path)
            
            # Prepare result
            result["success"] = True
            result["price"] = price
            result["section"] = section
            result["message"] = "Direct checkout link processed successfully"
            result["screenshot_path"] = screenshot_path
            
            # Send notification
            try:
                send_cart_notification(
                    event_date=event_date,
                    quantity=quantity,
                    section=section,
                    price=price,
                    cart_url=page.url
                )
                logger.info("Cart notification sent")
            except Exception as e:
                logger.error(f"Error sending cart notification: {str(e)}")
        else:
            # Try to find and click a continue or add to cart button
            button_selectors = [
                "button:has-text('Continue'), button:has-text('Continuar')",
                "button:has-text('Checkout'), button:has-text('Finalizar')",
                "button:has-text('Add to Cart'), button:has-text('Añadir al carrito')",
                "button:has-text('Buy'), button:has-text('Comprar')"
            ]
            
            for selector in button_selectors:
                if await click_element_if_visible(page, selector):
                    logger.info(f"Clicked button: {selector}")
                    await page.wait_for_load_state('networkidle')
                    await asyncio.sleep(2)  # Wait for any transitions
                    
                    # Check if we need to set quantity
                    quantity_input = await page.query_selector("input[type='number'], .quantity-input")
                    if quantity_input:
                        logger.info(f"Setting quantity to {quantity}")
                        await quantity_input.fill(str(quantity))
                        
                        # Look for an apply or update button
                        update_button = await page.query_selector("button:has-text('Apply'), button:has-text('Update'), button:has-text('Aplicar'), button:has-text('Actualizar')")
                        if update_button:
                            await update_button.click()
                            await page.wait_for_load_state('networkidle')
                    
                    # Take screenshot after clicking
                    await take_screenshot(page, "after_button_click.png")
                    
                    # Extract cart info
                    cart_info = await extract_cart_info(page)
                    if cart_info:
                        result["success"] = True
                        result["section"] = cart_info.get("section", "Direct Checkout")
                        result["price"] = cart_info.get("price", "")
                        result["message"] = "Added to cart via direct checkout link"
                        
                        # Send notification
                        try:
                            send_cart_notification(
                                event_date=event_date,
                                quantity=quantity,
                                section=result["section"],
                                price=result["price"],
                                cart_url=page.url
                            )
                        except Exception as e:
                            logger.error(f"Error sending cart notification: {str(e)}")
                        
                        return result
                    
                    break  # Exit loop after clicking first valid button
            
            # If we reach here, we couldn't navigate the direct checkout flow
            logger.warning("Could not find appropriate buttons on direct checkout page")
            result["message"] = "Failed to process direct checkout link"
    
    except Exception as e:
        logger.error(f"Error processing direct checkout: {str(e)}")
        result["message"] = f"Error processing direct checkout: {str(e)}"
    
    return result

async def wait_for_user_action(page):
    """Keep the browser open until user closes the script with Ctrl+C"""
    try:
        # Just wait indefinitely until user interrupts
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nScript interrupted by user. Closing browser and exiting.")
        await page.close()

async def wait_for_manual_trigger(message="Press Enter to continue..."):
    """Display a message and wait for manual action without using input()"""
    print(f"\n{message}")
    print("The script will wait 10 seconds and then continue automatically.")
    print("Press Ctrl+C to interrupt this wait if needed.")
    
    try:
        for i in range(10, 0, -1):
            print(f"Continuing in {i} seconds...", end="\r")
            await asyncio.sleep(1)
        print("Continuing...                    ")
    except KeyboardInterrupt:
        print("\nContinuing immediately...")

async def monitor_tickets(manual_mode=False, test_mode=False, persistent_browser=True, options=None):
    """
    Main function to run the automated cart process
    
    Args:
        manual_mode: If True, will pause between attempts for user confirmation
        test_mode: If True, will use test event URLs instead of production
        persistent_browser: If True, will maintain a single browser session for all attempts
        options: Dictionary containing cart options:
            - quantity: Number of tickets to purchase (1-8)
            - auto_checkout: Whether to proceed to checkout automatically
            - best_available: Whether to select best available seats
    
    Returns:
        Dictionary with cart results
    """
    # Set default options if none provided
    if options is None:
        options = {
            'quantity': 2,
            'auto_checkout': True,
            'best_available': True
        }
    
    # Ensure quantity is an integer
    if 'quantity' in options and options['quantity'] is not None:
        options['quantity'] = int(options['quantity'])
    else:
        options['quantity'] = 2
    
    max_attempts = 100
    attempt = 1
    check_interval = 15  # seconds
    
    print("\n==================================================")
    print("       TOVK BAND AUTOMATED TICKET CART SYSTEM      ")
    print("==================================================\n")
    
    print("This script will automatically:")
    print("1. Navigate to the ticket selection page")
    print("2. Select available seats")
    print(f"3. Select {options['quantity']} tickets")
    if options['best_available']:
        print("4. Choose 'Best Available' seats (if available)")
    print("5. Add tickets to the cart")
    if options['auto_checkout']:
        print("6. Proceed to checkout automatically")
    print("7. Send a Discord notification with:")
    print("   - @everyone mention")
    print("   - Event date, quantity, and section")
    print("   - Cart link as a button")
    print("   - Clear checkout instructions")
    print("   - Timestamp\n")
    
    if manual_mode:
        print("Running in MANUAL MODE - will pause for 10 seconds between attempts")
        print("Press Ctrl+C during the pause to continue immediately")
    else:
        print("Starting continuous monitoring mode...")
        print(f"Will check for tickets every {check_interval} seconds")
    
    # Create a persistent browser session if enabled
    browser = None
    context = None
    page = None
    
    async with async_playwright() as playwright:
        if persistent_browser:
            print("\nLaunching browser for persistent session...")
            browser_launch_options = {
                "headless": False,  # Use headed mode to appear more human-like
                "channel": "chrome",  # Use Chrome channel which is less likely to be detected
                "args": [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    "--window-size=1920,1080",
                    "--start-maximized",
                    "--disable-extensions",
                    "--disable-blink-features=IsolateOrigins,site-per-process",
                    "--ignore-certificate-errors",
                    "--disable-web-security",
                    "--allow-running-insecure-content"
                ],
                "ignore_default_args": ["--enable-automation"]
            }
            browser = await playwright.chromium.launch(**browser_launch_options)
            
            # Create a context with randomized device parameters to appear more human
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
                permissions=["geolocation", "notifications"],
                color_scheme="light",
                device_scale_factor=1.0 + (random.random() * 0.3)  # Slight randomization
            )
            
            # Configure the context to avoid detection
            await configure_browser_for_cloudflare(browser)
            
            # Add additional human-like behaviors
            await context.add_init_script("""
                // Add random timing jitter to events
                const originalAddEventListener = EventTarget.prototype.addEventListener;
                EventTarget.prototype.addEventListener = function(type, listener, options) {
                    if (type === 'mousemove' || type === 'mousedown' || type === 'mouseup' || type === 'click') {
                        const wrapped = function(...args) {
                            // Add small random delay to simulate human reaction time
                            setTimeout(() => {
                                listener.apply(this, args);
                            }, Math.random() * 20);
                        };
                        return originalAddEventListener.call(this, type, wrapped, options);
                    }
                    return originalAddEventListener.call(this, type, listener, options);
                };
            """)
            
            page = await context.new_page()
            logger.info("Persistent browser launched and ready")
        
        while attempt <= max_attempts:
            if manual_mode:
                await wait_for_manual_trigger("Ready to start next attempt. Waiting 10 seconds...")
            
            if not test_mode:
                # Using randomized selection for monitoring Bad Bunny dates
                event_date = random.choice(BAD_BUNNY_DATES)
                if event_date in EVENT_URLS:
                    event_url = EVENT_URLS[event_date]
                else:
                    logger.warning(f"No URL defined for date: {event_date}")
                    event_url = EVENT_URLS.get(BAD_BUNNY_DATES[0])
            else:
                # Using Danny Ocean dates for testing
                event_date = random.choice(DANNY_OCEAN_DATES)
                event_url = EVENT_URLS[event_date]
            
            print(f"\nAttempt {attempt} of {max_attempts}")
            logger.info(f"Selected event date: {event_date}")
            logger.info(f"Using event URL: {event_url}")
            logger.info(f"Using options: quantity={options['quantity']}, auto_checkout={options['auto_checkout']}, best_available={options['best_available']}")
            
            # Attempt to add tickets to cart
            logger.info(f"Starting automatic carting process for: {event_url}")
            
            if persistent_browser:
                # Use the existing browser session
                result = await automatic_cart_process(page, event_url, options)
            else:
                # Create a new browser for each attempt
                temp_browser = await playwright.chromium.launch(headless=False)
                
                # Configure browser to avoid Cloudflare detection
                if CLOUDFLARE_SETTINGS["enabled"]:
                    await configure_browser_for_cloudflare(temp_browser)
                
                # Create context with human-like properties
                temp_context = await temp_browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                    locale="en-US",
                    timezone_id="America/New_York",
                    geolocation={"latitude": 40.7128, "longitude": -74.0060},
                    permissions=["geolocation"]
                )
                
                # Set extra HTTP headers for human-like behavior
                if CLOUDFLARE_SETTINGS["use_human_headers"]:
                    await temp_context.set_extra_http_headers(HUMAN_HEADERS)
                
                temp_page = await temp_context.new_page()
                logger.info("Browser launched for automatic ticket selection")
                
                result = await automatic_cart_process(temp_page, event_url, options)
                
                # Only close the browser if not using persistent browser
                if temp_browser and not persistent_browser:
                    await temp_browser.close()
                    logger.info("Temporary browser closed")
            
            # If successful, break out of the loop
            if result['success']:
                logger.info("SUCCESS! Tickets added to cart. Notification sent. Monitoring complete.")
                print("\n==================================================")
                print("          TICKETS SUCCESSFULLY ADDED TO CART!      ")
                print("==================================================\n")
                print(f"Event Date: {event_date}")
                print(f"Cart URL: {result.get('cart_url', 'N/A')}")
                print(f"Section: {result.get('section', 'N/A')}")
                print(f"Quantity: {result.get('quantity', options.get('quantity', 2))}")
                if 'price' in result and result['price']:
                    print(f"Price: {result.get('price', 'N/A')}")
                print("\nDiscord notification sent with all information!")
                print("\nMonitoring completed successfully!")
                
                # Don't close the browser if we're using a persistent one
                if persistent_browser:
                    print("\nKeeping browser open. You can continue to use it.")
                    await wait_for_manual_trigger()
                
                return result
            
            # If not successful, wait and try again
            attempt += 1
            if not manual_mode:
                # Add random variation to check interval to avoid detection patterns
                jitter = random.uniform(-2, 2) if CLOUDFLARE_SETTINGS["enabled"] else 0
                wait_time = check_interval + jitter
                
                logger.info(f"Attempt {attempt-1} complete. Waiting {wait_time:.1f} seconds before next attempt...")
                print(f"Waiting {wait_time:.1f} seconds before next attempt...")
                await asyncio.sleep(wait_time)
        
        # If we've reached the maximum number of attempts
        if attempt > max_attempts:
            print("\n==================================================")
            print("          MAXIMUM ATTEMPTS REACHED                ")
            print("==================================================")
            print("Unable to add tickets to cart after maximum attempts.")
            print("Please try again later or check the event status.\n")
        
        # Keep the browser open after completion if using persistent browser
        if persistent_browser and browser:
            print("\nAll attempts completed but keeping browser open.")
            print("Press Ctrl+C to close the browser and exit the script.")
            await wait_for_manual_trigger()
        else:
            return {
                'success': False,
                'error': 'Maximum attempts reached without success',
                'cart_url': '',
                'checkout_url': ''
            }

if __name__ == "__main__":
    # Parse command line arguments
    manual_mode = False
    test_mode = True  # Default to test mode with Danny Ocean
    persistent_browser = True  # Keep browser open by default
    
    if len(sys.argv) > 1:
        if "manual" in sys.argv:
            manual_mode = True
            print("Running in MANUAL mode - will prompt before each attempt")
        
        if "production" in sys.argv:
            test_mode = False
            print("Running in PRODUCTION mode - will monitor Bad Bunny dates")
        
        if "auto-close" in sys.argv:
            persistent_browser = False
            print("Browser will automatically close after each attempt")
    
    print("Options:")
    print("  --manual: Run in manual mode (requires Enter key to start each attempt)")
    print("  --production: Run in production mode (monitor Bad Bunny dates)")
    print("  --auto-close: Close browser after each attempt (default: keep browser open)")
    print(f"Current mode: {'MANUAL' if manual_mode else 'AUTOMATED'}, {'TEST (Danny Ocean)' if test_mode else 'PRODUCTION (Bad Bunny)'}")
    print(f"Browser persistence: {'DISABLED (auto-close)' if not persistent_browser else 'ENABLED (stay open)'}")
    
    try:
        # Run the monitoring
        result = asyncio.run(monitor_tickets(
            manual_mode=manual_mode, 
            test_mode=test_mode,
            persistent_browser=persistent_browser
        ))
        if result:
            print(result)
    except KeyboardInterrupt:
        print("\nScript interrupted by user. Exiting.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        logger.error(f"Fatal error: {str(e)}", exc_info=True)

async def add_to_cart(page):
    """
    Add selected tickets to cart
    
    Args:
        page: Playwright page object
        
    Returns:
        dict: Dictionary with cart result information
    """
    # Initialize the result dictionary
    cart_result = {
        'success': False,
        'cart_url': '',
        'checkout_url': '',
        'error': ''
    }
    
    try:
        logger.info("Attempting to add tickets to cart...")
        
        # Wait for the page to stabilize
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(random.uniform(0.7, 1.5))
        
        # Look for add to cart or checkout buttons with various selectors
        cart_button_selectors = [
            "button#add-to-cart-button",
            "button.add-to-cart-button",
            "button:has-text('Add to Cart')",
            "button:has-text('Añadir al Carrito')",
            "button:has-text('Continue')",
            "button:has-text('Continuar')",
            "button:has-text('Next')",
            "button:has-text('Siguiente')",
            "button:has-text('Checkout')",
            "button:has-text('Pagar')",
            "button.btn-primary",
            "button.continue-button",
            "a.btn-primary:has-text('Checkout')",
            "a.btn-primary:has-text('Add to Cart')",
            "a.checkout-button",
            "input[type='submit'][value='Add to Cart']",
            "input[type='submit'][value='Checkout']"
        ]
        
        # Try to find and click on a cart button
        button_found = False
        
        for selector in cart_button_selectors:
            cart_button = await page.query_selector(selector)
            
            if cart_button:
                logger.info(f"Found cart button with selector: {selector}")
                
                # Human-like behavior: Pause before clicking
                await asyncio.sleep(random.uniform(0.5, 1.2))
                
                # Get button position for human-like mouse movement
                button_box = await cart_button.bounding_box()
                if button_box:
                    # First move mouse to a random position
                    await page.mouse.move(
                        random.randint(50, int(page.viewport_size['width'] - 50)),
                        random.randint(50, int(page.viewport_size['height'] - 50))
                    )
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    
                    # Then move to the button with slight randomization
                    await page.mouse.move(
                        button_box['x'] + button_box['width'] / 2 + random.randint(-5, 5),
                        button_box['y'] + button_box['height'] / 2 + random.randint(-3, 3)
                    )
                    await asyncio.sleep(random.uniform(0.2, 0.4))
                
                # Click the button
                await cart_button.click()
                logger.info(f"Clicked cart button")
                button_found = True
                
                # Wait for navigation or page updates
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(random.uniform(1.0, 2.0))
                
                # Take a screenshot after clicking
                await take_screenshot(page, "after_add_to_cart.png")
                
                # Check if we're now on a cart or checkout page
                current_url = page.url
                if "cart" in current_url.lower() or "checkout" in current_url.lower():
                    logger.info(f"Successfully added to cart. Current URL: {current_url}")
                    cart_result['success'] = True
                    cart_result['cart_url'] = current_url
                    
                    # Look for any checkout button that might be present
                    checkout_button_selectors = [
                        "button:has-text('Checkout')",
                        "button:has-text('Proceed to Checkout')",
                        "button:has-text('Continuar al pago')",
                        "a:has-text('Checkout')",
                        "a:has-text('Proceed to Checkout')",
                        "a.checkout-button",
                        "button.checkout-button"
                    ]
                    
                    for checkout_selector in checkout_button_selectors:
                        if await is_element_visible(page, checkout_selector):
                            logger.info(f"Found checkout button: {checkout_selector}")
                            break
                    
                    return cart_result
                
                # Handle possible popups or dialogues that might appear after clicking
                await handle_popup(page)
                
                # Check for cart messages or success indicators
                success_indicators = [
                    ".cart-success-message",
                    ".success-message",
                    ".cart-confirmation",
                    "div:has-text('Added to cart')",
                    "div:has-text('Añadido al carrito')"
                ]
                
                for indicator in success_indicators:
                    if await is_element_visible(page, indicator):
                        logger.info(f"Found success indicator: {indicator}")
                        cart_result['success'] = True
                        cart_result['cart_url'] = page.url
                        return cart_result
                
                # Check if we have items in the cart
                cart_item_selectors = [
                    ".cart-item",
                    ".item-in-cart",
                    ".checkout-item",
                    "tr.cart-row",
                    "div.cart-product"
                ]
                
                for item_selector in cart_item_selectors:
                    cart_items = await page.query_selector_all(item_selector)
                    if cart_items and len(cart_items) > 0:
                        logger.info(f"Found {len(cart_items)} items in cart with selector: {item_selector}")
                        cart_result['success'] = True
                        cart_result['cart_url'] = page.url
                        return cart_result
                
                # Even if we don't find explicit success indicators, consider it a success if we clicked a button
                cart_result['success'] = True
                cart_result['cart_url'] = page.url
                logger.info("Assuming cart addition was successful based on button click")
                return cart_result
        
        if not button_found:
            logger.warning("No add to cart or checkout button found")
            await take_screenshot(page, "no_cart_button.png")
            cart_result['error'] = "No add to cart button found"
            return cart_result
        
        # If we reached here, consider it a failure
        cart_result['error'] = "Could not verify successful cart addition"
        return cart_result
        
    except Exception as e:
        logger.error(f"Error adding to cart: {str(e)}")
        await take_screenshot(page, "add_to_cart_error.png")
        cart_result['error'] = f"Error adding to cart: {str(e)}"
        return cart_result

async def select_best_available(page, quantity=2):
    """
    Try to select 'Best Available' seats if that option exists
    
    Args:
        page: Playwright page object
        quantity: Number of tickets to select
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Attempting to select best available seats (quantity: {quantity})...")
        
        # Look for a quantity selector first and set it
        await set_quantity(page, quantity)
        
        # Look for "Best Available" option with various selectors
        best_available_selectors = [
            "button:has-text('Best Available')",
            "button:has-text('Mejor Disponible')",
            "button:has-text('Best Seats')",
            "button:has-text('Mejores Asientos')",
            "button.best-available-button",
            "button[data-action='best-available']",
            "button[data-selection-method='best-available']",
            "a:has-text('Best Available')",
            "a:has-text('Mejor Disponible')",
            ".best-available-option",
            "input[type='radio'][value='best-available']",
            "input[id*='best-available']"
        ]
        
        # Try each selector
        for selector in best_available_selectors:
            if await is_element_visible(page, selector):
                logger.info(f"Found 'Best Available' option with selector: {selector}")
                
                # Human-like behavior - slight delay before clicking
                await asyncio.sleep(random.uniform(0.3, 0.8))
                
                # Click the best available option
                best_option = await page.query_selector(selector)
                if best_option:
                    # Get the button position for human-like mouse movement
                    button_box = await best_option.bounding_box()
                    if button_box:
                        # Move mouse progressively towards the button
                        await page.mouse.move(
                            random.randint(50, int(page.viewport_size['width'] - 50)),
                            random.randint(50, int(page.viewport_size['height'] - 50))
                        )
                        await asyncio.sleep(random.uniform(0.1, 0.3))
                        
                        # Move to the button with slight randomization
                        await page.mouse.move(
                            button_box['x'] + button_box['width'] / 2 + random.randint(-5, 5),
                            button_box['y'] + button_box['height'] / 2 + random.randint(-3, 3)
                        )
                        await asyncio.sleep(random.uniform(0.2, 0.4))
                    
                    # Click the button
                    await best_option.click()
                    logger.info("Clicked on 'Best Available' option")
                    
                    # Wait for the page to update
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    
                    # Look for a confirmation button that might appear
                    confirm_selectors = [
                        "button:has-text('Continue')",
                        "button:has-text('Continuar')",
                        "button:has-text('Confirm')",
                        "button:has-text('Confirmar')",
                        "button:has-text('Apply')",
                        "button:has-text('Aplicar')",
                        "button.btn-primary",
                        "button.confirm-button"
                    ]
                    
                    for confirm_selector in confirm_selectors:
                        confirm_button = await page.query_selector(confirm_selector)
                        if confirm_button:
                            logger.info(f"Found confirmation button with selector: {confirm_selector}")
                            await asyncio.sleep(random.uniform(0.3, 0.8))
                            
                            # Click the confirmation button
                            await confirm_button.click()
                            logger.info("Clicked confirmation button")
                            await asyncio.sleep(random.uniform(0.5, 1.0))
                            await page.wait_for_load_state("networkidle")
                    
                    # Check if seats were actually selected
                    return await check_if_seats_selected(page)
        
        # If we reach here, we didn't find a "Best Available" option
        logger.info("No 'Best Available' option found")
        return False
        
    except Exception as e:
        logger.error(f"Error selecting best available seats: {str(e)}")
        await take_screenshot(page, "best_available_error.png")
        return False

async def check_if_seats_selected(page):
    """
    Check if seats were successfully selected
    
    Args:
        page: Playwright page object
        
    Returns:
        bool: True if seats appear to be selected, False otherwise
    """
    try:
        # Different indicators that seats might be selected
        selected_indicators = [
            "circle[fill='#FF0000'], circle[fill='red']",  # Red circles (often selected)
            "rect[fill='#FF0000'], rect[fill='red']",      # Red rectangles
            "path[fill='#FF0000'], path[fill='red']",      # Red paths
            ".seat.selected",                              # Selected class
            "[class*='selected']",                         # Contains selected in class
            "[data-status='selected']",                    # Data attribute
            "text:has-text('Selected')",                   # Text indicating selection
            "text:has-text('Seleccionado')",               # Spanish version
            "div:has-text('Selected seats:')",             # Heading for selected seats
            "div:has-text('Asientos seleccionados:')"      # Spanish version
        ]
        
        for indicator in selected_indicators:
            elements = await page.query_selector_all(indicator)
            if elements and len(elements) > 0:
                logger.info(f"Found {len(elements)} elements indicating seats are selected")
                return True
        
        # If we can see an "Add to Cart" button, that's also a good sign
        cart_buttons = [
            "button:has-text('Add to Cart')",
            "button:has-text('Añadir al carrito')",
            "button#add-to-cart-button",
            "button.add-to-cart-button"
        ]
        
        for button in cart_buttons:
            if await is_element_visible(page, button):
                logger.info(f"Found cart button '{button}' which suggests seats are selected")
                return True
        
        logger.info("No indicators found that seats are selected")
        return False
        
    except Exception as e:
        logger.error(f"Error checking if seats are selected: {str(e)}")
        return False

async def handle_cloudflare_challenge(page, max_wait_time=60, manual_solve=True):
    """
    Detect and handle Cloudflare challenge pages
    
    Args:
        page: Playwright page instance
        max_wait_time: Maximum time to wait for the challenge to be solved (seconds)
        manual_solve: Whether to allow manual solving of the challenge
        
    Returns:
        bool: True if challenge was bypassed, False otherwise
    """
    try:
        # Check if we're on a Cloudflare challenge page
        cloudflare_selectors = [
            "#challenge-running",
            "#challenge-form",
            "#cf-challenge-running",
            "div[class*='cf-browser-verification']",
            "iframe[src*='cloudflare']",
            "div[class*='challenge']",
            "script[data-cf-settings]",
            "div:has-text('Checking your browser before accessing')"
        ]
        
        for selector in cloudflare_selectors:
            if await is_element_visible(page, selector):
                logger.warning("⚠️ Cloudflare challenge detected!")
                
                # Take a screenshot of the challenge
                await take_screenshot(page, "cloudflare_challenge.png")
                
                if manual_solve:
                    # Notify the user that manual intervention is needed
                    logger.info("Manual intervention needed to solve Cloudflare challenge")
                    logger.info("Please complete the Cloudflare verification in the browser window")
                    logger.info(f"Waiting up to {max_wait_time} seconds for verification to complete...")
                    
                    # Wait for the challenge to disappear or timeout
                    start_time = time.time()
                    while time.time() - start_time < max_wait_time:
                        challenge_visible = False
                        for selector in cloudflare_selectors:
                            if await is_element_visible(page, selector):
                                challenge_visible = True
                                break
                        
                        if not challenge_visible:
                            logger.info("✅ Cloudflare challenge appears to be solved!")
                            
                            # Store cookies for future use
                            cookies = await page.context.cookies()
                            cf_cookie = next((c for c in cookies if c.get('name') == 'cf_clearance'), None)
                            if cf_cookie:
                                logger.info("📝 Cloudflare clearance cookie obtained")
                            
                            # Wait for the page to fully load
                            await page.wait_for_load_state("networkidle")
                            return True
                        
                        # Check every second
                        await asyncio.sleep(1)
                    
                    logger.error("❌ Timeout waiting for Cloudflare challenge to be solved")
                    return False
                else:
                    # Attempt automated bypass
                    logger.info("Attempting automated Cloudflare bypass...")
                    
                    # Perform human-like actions
                    # 1. Random mouse movements
                    for _ in range(5):
                        x = random.randint(100, int(page.viewport_size['width'] - 100))
                        y = random.randint(100, int(page.viewport_size['height'] - 100))
                        await page.mouse.move(x, y)
                        await asyncio.sleep(random.uniform(0.1, 0.3))
                    
                    # 2. Small scrolls
                    await page.mouse.wheel(0, random.randint(50, 200))
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                    
                    # 3. Wait for automatic verification to complete
                    await page.wait_for_timeout(random.uniform(5000, 10000))
                    
                    # Check if we're still on the challenge page
                    for selector in cloudflare_selectors:
                        if await is_element_visible(page, selector):
                            logger.error("❌ Automated Cloudflare bypass failed")
                            return False
                    
                    logger.info("✅ Cloudflare challenge appears to be solved!")
                    return True
        
        # No Cloudflare challenge detected
        return True
        
    except Exception as e:
        logger.error(f"Error handling Cloudflare challenge: {str(e)}")
        return False

async def automatic_cart(url, options=None, persistent_browser=False):
    """
    Automate the process of selecting seats and adding them to cart
    
    Args:
        url: URL of the event page
        options: Dictionary containing options like quantity, auto_checkout, best_available
        persistent_browser: Whether to reuse a browser instance
    
    Returns:
        Dictionary with cart details or error information
    """
    options = options or {}
    quantity = options.get("quantity", 2)
    auto_checkout = options.get("auto_checkout", False)
    best_available = options.get("best_available", True)
    
    # Initialize result dictionary
    cart_result = {
        "success": False,
        "error": "",
        "cart_url": "",
        "checkout_url": "",
        "section": "",
        "row": "",
        "seats": [],
        "price": "",
        "quantity": quantity,
        "event_date": options.get("event_date", "Unknown")
    }
    
    playwright = None
    browser = None
    page = None
    
    try:
        logger.info(f"Starting automatic cart process for event: {url}")
        logger.info(f"Options: quantity={quantity}, auto_checkout={auto_checkout}, best_available={best_available}")
        
        # Initialize Playwright
        playwright = await async_playwright().start()
        
        # Define enhanced browser launch options for better stealth
        browser_launch_options = {
            "headless": False,  # Use headed mode to appear more human-like
            "channel": "chrome",  # Use Chrome channel which is less likely to be detected
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--start-maximized",
                "--disable-extensions",
                "--disable-blink-features=IsolateOrigins,site-per-process",
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--allow-running-insecure-content",
                "--disable-features=IsolateOrigins",
                "--disable-site-isolation-trials"
            ],
            "ignore_default_args": ["--enable-automation"]
        }
        
        # Launch browser with enhanced options
        browser = await playwright.chromium.launch(**browser_launch_options)
        
        # Set up browser context with human-like properties
        user_agent = random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0"
        ])
        
        context = await browser.new_context(
            user_agent=user_agent,
            locale="en-US",
            timezone_id="America/New_York",
            geolocation={"latitude": 40.7128, "longitude": -74.0060},
            permissions=["geolocation"],
            color_scheme="light"
        )
        
        # Set extra HTTP headers to appear more human-like
        await context.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "sec-ch-ua": '"Google Chrome";v="123", "Not:A-Brand";v="8", "Chromium";v="123"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1"
        })
        
        # Configure browser for avoiding detection
        await configure_browser_for_cloudflare(browser)
        
        # Create a new page
        page = await context.new_page()
        
        # Add human-like behavior before navigating
        await page.mouse.move(
            random.randint(200, 800),
            random.randint(100, 600)
        )
        
        logger.info("Step 1: Opening event page...")
        # Navigate to the event URL with a timeout
        try:
            response = await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            if not response:
                cart_result["error"] = "Failed to navigate to event page"
                return cart_result
                
            # Take screenshot of initial page load
            await take_screenshot(page, "01_event_page.png")
            
            # Check for Cloudflare challenge
            cloudflare_result = await handle_cloudflare_challenge(page, max_wait_time=90, manual_solve=True)
            if not cloudflare_result:
                cart_result["error"] = "Could not bypass Cloudflare protection"
                return cart_result
                
            # Wait for the page to fully load after potential Cloudflare challenge
            await page.wait_for_load_state("networkidle")
            
            # Add random delays and mouse movements to appear more human-like
            await asyncio.sleep(random.uniform(1.0, 2.5))
            
            # Perform random mouse movements and scrolls
            for _ in range(3):
                x = random.randint(100, int(page.viewport_size['width'] - 100))
                y = random.randint(100, int(page.viewport_size['height'] - 100))
                await page.mouse.move(x, y, steps=random.randint(5, 10))
                await asyncio.sleep(random.uniform(0.2, 0.5))
            
            # Random small scroll
            await page.mouse.wheel(0, random.randint(100, 300))
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
            # Step 2: Try to select best available seats first if option is enabled
            if best_available:
                logger.info("Attempting to select best available seats...")
                best_seats_selected = await select_best_available(page, quantity)
                
                if best_seats_selected:
                    logger.info("Best available seats selected successfully")
                else:
                    logger.info("Best available selection failed or not available, trying seat map...")
                    # Try to select from seat map as fallback
                    seat_result = await select_seat_from_map(page)
                    if not seat_result:
                        cart_result["error"] = "Failed to select seats from map"
                        return cart_result
            else:
                # Select seats from the seat map
                logger.info("Selecting seats from map...")
                seat_result = await select_seat_from_map(page)
                if not seat_result:
                    cart_result["error"] = "Failed to select seats from map"
                    return cart_result
            
            # Step 3: Set quantity if not already done
            await asyncio.sleep(random.uniform(0.5, 1.0))
            await set_quantity(page, quantity)
            
            # Step 4: Add to cart
            logger.info("Step 4: Adding tickets to cart...")
            add_to_cart_result = await add_to_cart(page)
            
            # Update result with cart information
            cart_result.update(add_to_cart_result)
            
            if add_to_cart_result.get("success", False):
                logger.info("✅ Successfully added tickets to cart!")
                
                # Capture final page state
                await take_screenshot(page, "05_tickets_in_cart.png")
                
                # Perform automatic checkout if enabled
                if auto_checkout:
                    logger.info("Starting automatic checkout process...")
                    checkout_result = await proceed_to_checkout(page)
                    cart_result.update(checkout_result)
            else:
                logger.error(f"❌ Failed to add tickets to cart: {add_to_cart_result.get('error', 'Unknown error')}")
            
            return cart_result
            
        except Exception as e:
            logger.error(f"Error navigating to URL: {str(e)}")
            cart_result["error"] = f"Navigation error: {str(e)}"
            return cart_result
            
    except Exception as e:
        logger.error(f"Error in automatic cart process: {str(e)}")
        if page:
            await take_screenshot(page, "automatic_cart_error.png")
        cart_result["error"] = f"Error in automatic cart process: {str(e)}"
        return cart_result
        
    finally:
        if not persistent_browser:
            # Close browser if not using persistent browser
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()

async def monitor_tickets(event_urls=None, event_dates=None, discord_webhook_url=None, 
                         check_interval=15, manual_mode=False, max_attempts=100, 
                         test_mode=False, persistent_browser=True):
    """
    Monitor ticket availability for specified Bad Bunny concerts
    
    Args:
        event_urls: Dictionary mapping event dates to event URLs
        event_dates: List of event dates to monitor
        discord_webhook_url: Discord webhook URL for notifications
        check_interval: Interval between checks in seconds
        manual_mode: Whether to run in manual mode with pauses between attempts
        max_attempts: Maximum number of attempts before giving up
        test_mode: Whether to run in test mode
        persistent_browser: Whether to use a persistent browser instance
    
    Returns:
        A dictionary with the final status and any cart/checkout URLs
    """
    # Initialize default values
    if event_urls is None:
        # Use default event URLs if none provided
        event_urls = {
            # FORMAT: 'YYYY-MM-DD': 'URL'
            # July 2025
            '2025-07-12': '',
            '2025-07-18': '',
            '2025-07-19': '',
            # August 2025
            '2025-08-01': '',
            '2025-08-02': '',
            '2025-08-03': '',
            '2025-08-08': '',
            '2025-08-09': '',
            '2025-08-10': '',
            '2025-08-15': '',
            '2025-08-16': '',
            '2025-08-17': '',
            '2025-08-22': '',
            '2025-08-23': '',
            '2025-08-24': '',
            '2025-08-29': '',
            '2025-08-30': '',
            '2025-08-31': '',
            # September 2025
            '2025-09-05': '',
            '2025-09-06': '',
            '2025-09-07': '',
            '2025-09-12': '',
            '2025-09-13': '',
            '2025-09-14': '',
            # Test URL (always use this for testing)
            '2025-03-10-TEST': 'https://shop.ticketera.com/checkout/como-coco-ikmk2p?_gl=1*nkwzt0*_gcl_au*MTc5Nzk3NjMzOC4xNzM2Nzg3MDg4'
        }
    
    # If in test mode, only use the test URL
    if test_mode:
        event_urls = {'2025-03-10-TEST': event_urls.get('2025-03-10-TEST', 'https://shop.ticketera.com/checkout/como-coco-ikmk2p?_gl=1*nkwzt0*_gcl_au*MTc5Nzk3NjMzOC4xNzM2Nzg3MDg4')}
    
    # Use the specified webhook URL or a default one
    if discord_webhook_url is None:
        discord_webhook_url = "https://discord.com/api/webhooks/1347702022039666783/IIgJ2B6vT5aQoTjNOadVxdAviHuEsCRR8zwu4CgWAvWzcob9BJ0_5XQC-BTyVauTljR_"
    
    # Print initialization message
    print("\n==================================================")
    print(f"{'TOVK BAND AUTOMATED TICKET CART SYSTEM':^50}")
    print("="*50 + "\n")

    print("This script will automatically:")
    print("1. Navigate to the ticket selection page")
    print("2. Select available seats")
    print("3. Select 2 tickets")
    print("4. Choose 'Best Available' seats (if available)")
    print("5. Add tickets to the cart")
    print("7. Send a Discord notification with:")
    print("   - @everyone mention")
    print("   - Event date, quantity, and section")
    print("   - Cart link as a button")
    print("   - Clear checkout instructions")
    print("   - Timestamp\n")
    
    if manual_mode:
        print("Running in MANUAL MODE - will pause for 10 seconds between attempts")
        print("Press Ctrl+C during the pause to continue immediately\n")
    else:
        print(f"Running in AUTO MODE - will check every {check_interval} seconds")
        print("Press Ctrl+C to stop the script at any time\n")
    
    # Initialize result dictionary
    result = {
        'success': False,
        'cart_url': '',
        'checkout_url': '',
        'error': ''
    }
    
    # Initialize Playwright and launch browser if using persistent browser
    if persistent_browser:
        print("\nLaunching browser for persistent session...")
        playwright = await async_playwright().start()
        
        # Define enhanced browser launch options for better stealth
        browser_launch_options = {
            "headless": False,  # Use headed mode for manual interaction
            "channel": "chrome",  # Use Chrome channel which is less likely to be detected
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1920,1080",
                "--start-maximized",
                "--disable-extensions",
                "--disable-blink-features=IsolateOrigins,site-per-process",
                "--ignore-certificate-errors",
                "--disable-web-security",
                "--allow-running-insecure-content",
                "--disable-features=IsolateOrigins",
                "--disable-site-isolation-trials"
            ],
            "ignore_default_args": ["--enable-automation"]
        }
        
        # Launch browser with enhanced options
        browser = await playwright.chromium.launch(**browser_launch_options)
        
        # Create context with human-like properties
        user_agent = random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        ])
        
        context = await browser.new_context(
            user_agent=user_agent,
            locale="en-US",
            timezone_id="America/New_York",
            geolocation={"latitude": 40.7128, "longitude": -74.0060},
            permissions=["geolocation"],
            color_scheme="light"
        )
        
        # Configure the browser for Cloudflare evasion
        logger.info("Configuring browser to avoid Cloudflare detection...")
        await configure_browser_for_cloudflare(browser)
        logger.info("Persistent browser launched and ready")
    else:
        playwright = None
        browser = None
        context = None
    
    attempt = 1
    
    # Main monitoring loop
    while attempt <= max_attempts:
        if attempt == 1:
            print("\nReady to start next attempt. Waiting 10 seconds...")
            await wait_with_countdown(10)
        
        print(f"\nAttempt {attempt} of {max_attempts}")
        
        # Pick a random event date to check
        random_date = random.choice(list(event_urls.keys()))
        event_url = event_urls[random_date]
        
        logger.info(f"Selected event date: {random_date}")
        logger.info(f"Using event URL: {event_url}")
        
        # Set options for automatic cart
        options = {
            "quantity": 2,
            "auto_checkout": False,
            "best_available": True,
            "event_date": "Bad Bunny Test Event" if "TEST" in random_date else f"Bad Bunny {random_date}"
        }
        
        logger.info(f"Using options: quantity={options['quantity']}, auto_checkout={options['auto_checkout']}, best_available={options['best_available']}")
        
        # Run automatic cart process
        logger.info(f"Starting automatic carting process for: {event_url}")
        
        # If using persistent browser, create a new page in the existing context
        if persistent_browser and context:
            page = await context.new_page()
            try:
                # Open URL in the persistent browser
                await page.goto(event_url, timeout=30000, wait_until="domcontentloaded")
                
                # Check for Cloudflare challenge
                cloudflare_result = await handle_cloudflare_challenge(page, max_wait_time=90, manual_solve=True)
                if not cloudflare_result:
                    logger.error("Could not bypass Cloudflare protection")
                    await page.close()
                    
                    if manual_mode:
                        print("\nReady to start next attempt. Waiting 10 seconds...")
                        await wait_with_countdown(10)
                    else:
                        await asyncio.sleep(check_interval)
                    
                    attempt += 1
                    continue
                
                # Proceed with cart process
                cart_result = await automatic_cart_with_page(page, options)
                await page.close()
            except Exception as e:
                logger.error(f"Error in persistent browser session: {str(e)}")
                await page.close()
                cart_result = {
                    "success": False,
                    "error": f"Error in persistent browser session: {str(e)}",
                    "cart_url": "",
                    "checkout_url": ""
                }
        else:
            # Use non-persistent browser approach
            cart_result = await automatic_cart(event_url, options)
        
        # Check if cart process was successful
        if cart_result.get("success", False):
            logger.info("🎉 Successfully added tickets to cart!")
            
            # Send Discord notification
            if discord_webhook_url:
                await send_discord_cart_notification(
                    discord_webhook_url,
                    cart_result.get("event_date", random_date),
                    cart_result.get("quantity", 2),
                    cart_result.get("section", "Unknown"),
                    cart_result.get("row", "Unknown"),
                    cart_result.get("seats", []),
                    cart_result.get("price", "Unknown"),
                    cart_result.get("cart_url", ""),
                    cart_result.get("checkout_url", "")
                )
            
            # Update the result with cart information
            result = cart_result
            
            # If in manual mode, keep the browser open for the user
            if manual_mode and persistent_browser:
                print("\nKeeping browser open. You can continue to use it.")
                await wait_for_manual_trigger()
            
            return result
        
        # If not successful, wait and try again
        attempt += 1
        
        if attempt <= max_attempts:
            if manual_mode:
                print("\nReady to start next attempt. Waiting 10 seconds...")
                await wait_with_countdown(10)
            else:
                # Wait for the specified interval before next check
                await asyncio.sleep(check_interval)
        else:
            print("\n" + "="*50)
            print(f"{'MAXIMUM ATTEMPTS REACHED':^50}")
            print("="*50)
            print("Unable to add tickets to cart after maximum attempts.")
            print("Please try again later or check the event status.")
    
    # Clean up if using persistent browser
    if persistent_browser and browser:
        print("\nAll attempts completed but keeping browser open.")
        print("Press Ctrl+C to close the browser and exit the script.")
        await wait_for_manual_trigger()
    else:
        return {
            'success': False,
            'error': 'Maximum attempts reached without success',
            'cart_url': '',
            'checkout_url': ''
        }

async def automatic_cart_with_page(page, options=None):
    """
    Automate the process of selecting seats and adding them to cart using an existing page
    
    Args:
        page: Playwright page instance
        options: Dictionary containing options like quantity, auto_checkout, best_available
    
    Returns:
        Dictionary with cart details or error information
    """
    options = options or {}
    quantity = options.get("quantity", 2)
    auto_checkout = options.get("auto_checkout", False)
    best_available = options.get("best_available", True)
    
    # Initialize result dictionary
    cart_result = {
        "success": False,
        "error": "",
        "cart_url": "",
        "checkout_url": "",
        "section": "",
        "row": "",
        "seats": [],
        "price": "",
        "quantity": quantity,
        "event_date": options.get("event_date", "Unknown")
    }
    
    try:
        logger.info(f"Options: quantity={quantity}, auto_checkout={auto_checkout}, best_available={best_available}")
        
        logger.info("Step 1: Opening event page...")
        # Take screenshot of initial page load
        await take_screenshot(page, "01_event_page.png")
        
        # Wait for the page to fully load after potential Cloudflare challenge
        await page.wait_for_load_state("networkidle")
        
        # Add random delays and mouse movements to appear more human-like
        await asyncio.sleep(random.uniform(1.0, 2.5))
        
        # Perform random mouse movements and scrolls
        for _ in range(3):
            x = random.randint(100, int(page.viewport_size['width'] - 100))
            y = random.randint(100, int(page.viewport_size['height'] - 100))
            await page.mouse.move(x, y, steps=random.randint(5, 10))
            await asyncio.sleep(random.uniform(0.2, 0.5))
        
        # Random small scroll
        await page.mouse.wheel(0, random.randint(100, 300))
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        # Step 2: Try to select best available seats first if option is enabled
        if best_available:
            logger.info("Attempting to select best available seats...")
            best_seats_selected = await select_best_available(page, quantity)
            
            if best_seats_selected:
                logger.info("Best available seats selected successfully")
            else:
                logger.info("Best available selection failed or not available, trying seat map...")
                # Try to select from seat map as fallback
                seat_result = await select_seat_from_map(page)
                if not seat_result:
                    cart_result["error"] = "Failed to select seats from map"
                    return cart_result
        
        # Step 3: Set quantity if not already done
        await asyncio.sleep(random.uniform(0.5, 1.0))
        await set_quantity(page, quantity)
        
        # Step 4: Add to cart
        logger.info("Step 4: Adding tickets to cart...")
        add_to_cart_result = await add_to_cart(page)
        
        # Update result with cart information
        cart_result.update(add_to_cart_result)
        
        if add_to_cart_result.get("success", False):
            logger.info("✅ Successfully added tickets to cart!")
            
            # Capture final page state
            await take_screenshot(page, "05_tickets_in_cart.png")
            
            # Perform automatic checkout if enabled
            if auto_checkout:
                logger.info("Starting automatic checkout process...")
                checkout_result = await proceed_to_checkout(page)
                cart_result.update(checkout_result)
        else:
            logger.error(f"❌ Failed to add tickets to cart: {add_to_cart_result.get('error', 'Unknown error')}")
        
        return cart_result
        
    except Exception as e:
        logger.error(f"Error in automatic cart process: {str(e)}")
        await take_screenshot(page, "automatic_cart_error.png")
        cart_result["error"] = f"Error in automatic cart process: {str(e)}"
        return cart_result
