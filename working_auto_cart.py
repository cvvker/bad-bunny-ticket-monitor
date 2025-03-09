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
    """Configure the browser to better avoid Cloudflare detection"""
    if CLOUDFLARE_SETTINGS["enabled"]:
        try:
            # Access the browser's DevTools Protocol session
            cdp_session = await browser.new_cdp_session()
            
            if CLOUDFLARE_SETTINGS["disable_webdriver"]:
                # Attempt to disable webdriver flags that Cloudflare might detect
                await cdp_session.execute(
                    'Page.addScriptToEvaluateOnNewDocument',
                    {
                        'source': '''
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => false,
                        });
                        
                        // Prevent Cloudflare from detecting automation
                        if (window.navigator.permissions) {
                            window.navigator.permissions.query = (parameters) => {
                                return Promise.resolve({state: 'granted'});
                            };
                        }
                        
                        // Hide the fact that we're running headless
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3, 4, 5],
                        });
                        
                        // Override the languages
                        Object.defineProperty(navigator, 'languages', {
                            get: () => ['en-US', 'en', 'es'],
                        });
                        '''
                    }
                )
            
            logger.info("Browser configured to avoid Cloudflare detection")
            return True
        except Exception as e:
            logger.warning(f"Failed to configure browser for Cloudflare: {str(e)}")
            return False

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
    """Verify if the current page is actually a cart page with tickets in it"""
    
    # Try multiple methods to verify we're on a cart page
    
    # Method 1: Check URL for cart-related keywords
    current_url = page.url
    url_is_cart = any(keyword in current_url.lower() for keyword in [
        "cart", "checkout", "basket", "bag", "purchase", "boletos", "tickets"
    ])
    
    # Method 2: Check page title for cart-related keywords
    title = await page.title()
    title_is_cart = title and any(keyword in title.lower() for keyword in [
        "cart", "checkout", "basket", "bag", "purchase", "boletos", "carrito", "tickets"
    ])
    
    # Method 3: Check for cart page elements
    cart_page_selectors = [
        'h1:has-text("Shopping Cart")', 'h1:has-text("Cart")',
        'h1:has-text("Checkout")', 'h1:has-text("Carrito")',
        'div[class*="cart"]', 'div[id*="cart"]',
        'div[class*="checkout"]', 'div[id*="checkout"]',
        'table[class*="cart"]', 'tr[class*="cart-item"]',
        'div[class*="ticket"]', 'div[class*="boleto"]',
        'button:has-text("Checkout")', 'button:has-text("Proceed to Checkout")',
        'span:has-text("subtotal")', 'span:has-text("total")'
    ]
    
    content_is_cart = False
    for selector in cart_page_selectors:
        try:
            element = await page.query_selector(selector)
            if element:
                content_is_cart = True
                logger.info(f"Detected cart page element with selector: {selector}")
                break
        except Exception as e:
            pass
    
    # Method 4: Check if there are any indicators that tickets are in the cart
    ticket_indicators = [
        'div:has-text("General Admission")', 'div:has-text("Ticket")',
        'div:has-text("Section")', 'div:has-text("Quantity")',
        'span:has-text("Price")', 'span:has-text("Fee")',
        'tr[class*="item"]', 'div[class*="item"]',
        'div:has-text("TOVK")'
    ]
    
    has_tickets = False
    for selector in ticket_indicators:
        try:
            element = await page.query_selector(selector)
            if element:
                has_tickets = True
                logger.info(f"Detected tickets in cart with selector: {selector}")
                break
        except Exception as e:
            logger.debug(f"Error checking selector {selector}: {str(e)}")
    
    # Return true only if at least two methods confirm we're on a cart page
    confirmation_count = sum([url_is_cart, title_is_cart, content_is_cart, has_tickets])
    is_cart = confirmation_count >= 2
    
    if is_cart:
        logger.info("VERIFICATION SUCCESSFUL: Current page is confirmed to be a cart page")
        # Take an extra screenshot of the verified cart page
        await page.screenshot(path=os.path.join(os.path.dirname(__file__), "screenshots", "verified_cart.png"))
        return True
    else:
        logger.warning("VERIFICATION FAILED: Current page does not appear to be a valid cart page")
        logger.warning(f"URL check: {url_is_cart}, Title check: {title_is_cart}, Content check: {content_is_cart}, Ticket check: {has_tickets}")
        return False

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
    
    # Step 1: Look for ticket type/section options that might appear after clicking BOLETOS
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
    
    ticket_selected = False
    for selector in ticket_type_selectors:
        try:
            elements = await page.query_selector_all(selector)
            if len(elements) > 0:
                # Click the first ticket option
                await elements[0].click()
                logger.info(f"Selected ticket option with selector: {selector}")
                await take_screenshot(page, "ticket_option_selected.png")
                ticket_selected = True
                await asyncio.sleep(2)
                break
        except Exception as e:
            logger.debug(f"Failed to select ticket option with selector {selector}: {str(e)}")
    
    # If couldn't find specific elements, try clicking in strategic areas
    if not ticket_selected:
        logger.info("No specific ticket options found, trying to click in likely areas...")
        # Define a grid of positions to try clicking
        positions = [
            (400, 300),  # Center-left
            (400, 400),  # Middle-left
            (600, 300),  # Center
            (600, 400),  # Middle
            (800, 300),  # Center-right
            (800, 400)   # Middle-right
        ]
        
        for i, (x, y) in enumerate(positions):
            try:
                await page.mouse.click(x, y)
                logger.info(f"Clicked at position ({x}, {y})")
                await take_screenshot(page, f"ticket_area_click_{i}.png")
                await asyncio.sleep(1.5)
            except Exception as e:
                logger.debug(f"Failed to click at position ({x}, {y}): {str(e)}")
    
    # Step 2: Look for quantity selectors and select quantity
    quantity_selectors = [
        "select[name*='quantity']",
        "select[id*='quantity']",
        "div[class*='quantity'] select",
        "[aria-label*='quantity']",
        "input[type='number']"
    ]
    
    for selector in quantity_selectors:
        try:
            quantity_element = await page.query_selector(selector)
            if quantity_element:
                tag_name = await quantity_element.evaluate("el => el.tagName.toLowerCase()")
                
                if tag_name == "select":
                    # If it's a dropdown, select value "2"
                    await quantity_element.select_option("2")
                elif tag_name == "input":
                    # If it's an input, type "2"
                    await quantity_element.fill("2")
                
                logger.info(f"Set quantity to 2 using selector: {selector}")
                await take_screenshot(page, "quantity_set.png")
                await asyncio.sleep(1)
                break
        except Exception as e:
            logger.debug(f"Failed to set quantity with selector {selector}: {str(e)}")
    
    # Step 3: Look for continue/next buttons to move through the process
    continue_selectors = [
        "button:has-text('Continue')",
        "button:has-text('Continuar')",
        "button:has-text('Next')",
        "button:has-text('Siguiente')",
        "button.continue-button",
        "button.btn-primary",
        "a.btn-primary",
        "[class*='continue']",
        "[class*='next']",
        "footer button",
        "button[type='submit']"
    ]
    
    for selector in continue_selectors:
        try:
            continue_button = await page.query_selector(selector)
            if continue_button:
                # First screenshot before clicking
                await take_screenshot(page, "before_continue_button.png")
                
                await continue_button.click()
                logger.info(f"Clicked continue button with selector: {selector}")
                await take_screenshot(page, "continue_clicked.png")
                await asyncio.sleep(3)
                break
        except Exception as e:
            logger.debug(f"Failed to click continue with selector {selector}: {str(e)}")
    
    # Step 4: Look for "Add to Cart" or similar buttons
    cart_selectors = [
        "button:has-text('Add to Cart')",
        "button:has-text('Añadir al Carrito')",
        "button:has-text('Checkout')",
        "button:has-text('Pagar')",
        "button.checkout-button",
        "button.add-to-cart",
        "button.btn-primary",
        "a.btn-primary",
        "[class*='cart']",
        "[class*='checkout']",
        "footer button",
        "button[type='submit']"
    ]
    
    for selector in cart_selectors:
        try:
            cart_button = await page.query_selector(selector)
            if cart_button:
                await cart_button.click()
                logger.info(f"Clicked add to cart button with selector: {selector}")
                await take_screenshot(page, "add_cart_clicked.png")
                await asyncio.sleep(3)
                
                # After clicking add to cart, check if we're on the cart page
                if await verify_cart_page(page):
                    logger.info("Successfully navigated to cart page!")
                    return True
        except Exception as e:
            logger.debug(f"Failed to click add to cart with selector {selector}: {str(e)}")
    
    # If we haven't successfully found the cart page yet, check again
    if await verify_cart_page(page):
        logger.info("Successfully navigated to cart page!")
        return True
        
    return False

async def automatic_cart_process(page, event_url, options=None):
    """
    Attempt to automatically add tickets to the cart
    
    Args:
        page: Playwright page object
        event_url: URL to the event page
        options: Dictionary containing cart options:
            - quantity: Number of tickets to purchase (1-8)
            - auto_checkout: Whether to proceed to checkout automatically
            - best_available: Whether to select best available seats
    
    Returns:
        Dictionary with cart results
    """
    try:
        # Use default options if none provided
        if options is None:
            options = {
                'quantity': 2,
                'auto_checkout': True,
                'best_available': True
            }
        
        # Ensure quantity is an integer
        quantity = int(options.get('quantity', 2))
        auto_checkout = options.get('auto_checkout', True)
        best_available = options.get('best_available', True)
        
        logger.info(f"Starting auto-cart with options: quantity={quantity}, auto_checkout={auto_checkout}, best_available={best_available}")

        # Navigate to the event page
        await page.goto(event_url, wait_until="domcontentloaded")
        logger.info(f"Navigated to event page: {event_url}")
        
        # Take initial screenshot
        await take_screenshot(page, "event_page_initial.png")
        
        # Wait for page to fully load with additional timeout
        try:
            await page.wait_for_load_state("networkidle", timeout=30000)
        except Exception as e:
            logger.warning(f"Network idle wait timed out: {str(e)}")
        
        # Add random delay and mouse movements for human-like behavior
        await human_delay()
        await random_mouse_movement(page)
        
        # If best available is enabled, look for a best available option
        if best_available:
            try:
                logger.info("Looking for best available option")
                
                # Look for "Best Available" button with various selectors
                best_available_selectors = [
                    "button:has-text('Best Available')",
                    "button:has-text('Mejor Disponible')",
                    ".best-available-button",
                    "[data-testid='best-available']"
                ]
                
                for selector in best_available_selectors:
                    best_available_button = await page.query_selector(selector)
                    if best_available_button:
                        logger.info(f"Found best available button with selector: {selector}")
                        await best_available_button.click()
                        logger.info("Clicked Best Available button")
                        await human_delay()
                        await take_screenshot(page, "after_best_available.png")
                        break
            except Exception as e:
                logger.warning(f"Error selecting best available: {str(e)}")
        
        # Look for a quantity selector and set the desired quantity
        try:
            logger.info(f"Setting quantity to {quantity}")
            
            # Try different quantity selector patterns
            quantity_selectors = [
                "select#quantity",
                "select.quantity-select",
                "select[name='quantity']",
                "select",
                "input[type='number'][name='quantity']"
            ]
            
            quantity_set = False
            for selector in quantity_selectors:
                quantity_element = await page.query_selector(selector)
                if quantity_element:
                    logger.info(f"Found quantity selector with selector: {selector}")
                    
                    # Check if it's a select dropdown or input field
                    tag_name = await quantity_element.evaluate("el => el.tagName.toLowerCase()")
                    
                    if tag_name == "select":
                        await quantity_element.select_option(str(quantity))
                        quantity_set = True
                        logger.info(f"Set quantity to {quantity} via dropdown")
                    elif tag_name == "input":
                        await quantity_element.fill(str(quantity))
                        quantity_set = True
                        logger.info(f"Set quantity to {quantity} via input field")
                    
                    await human_delay()
                    await take_screenshot(page, "after_quantity_selection.png")
                    break
            
            # If no quantity selector found, try to use +/- buttons
            if not quantity_set:
                logger.info("Trying to set quantity using +/- buttons")
                
                # Try to find + button and click it repeatedly
                plus_button_selectors = [
                    "button:has-text('+')",
                    ".increment-button",
                    ".quantity-plus",
                    "[data-testid='increment']"
                ]
                
                for selector in plus_button_selectors:
                    plus_button = await page.query_selector(selector)
                    if plus_button:
                        logger.info(f"Found plus button with selector: {selector}")
                        
                        # Default quantity is usually 1, so click (quantity-1) times
                        for _ in range(quantity - 1):
                            await plus_button.click()
                            await asyncio.sleep(0.2)  # Short delay between clicks
                        
                        quantity_set = True
                        logger.info(f"Set quantity to {quantity} via plus button")
                        await human_delay()
                        await take_screenshot(page, "after_quantity_buttons.png")
                        break
        except Exception as e:
            logger.warning(f"Error setting quantity: {str(e)}")
        
        # Look for add to cart button or proceed button
        add_to_cart_success = False
        try:
            logger.info("Looking for add to cart button")
            
            # Common add to cart button selectors
            cart_button_selectors = [
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
            
            for selector in cart_button_selectors:
                cart_button = await page.query_selector(selector)
                if cart_button:
                    logger.info(f"Found add to cart button with selector: {selector}")
                    await cart_button.click()
                    logger.info("Clicked Add to Cart button")
                    add_to_cart_success = True
                    await take_screenshot(page, "after_add_to_cart.png")
                    
                    # Wait for navigation or confirmation
                    try:
                        await page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception as e:
                        logger.warning(f"Wait for navigation after add to cart timed out: {str(e)}")
                    
                    # Add human delay
                    await human_delay()
                    break
            
            if not add_to_cart_success:
                logger.warning("Could not find add to cart button with standard selectors")
                
                # If we couldn't find a standard add to cart button, try to navigate to cart page directly
                cart_info = await navigate_to_cart(page, event_url)
                if cart_info and 'cart_url' in cart_info and cart_info['cart_url']:
                    add_to_cart_success = True
                    await take_screenshot(page, "after_navigate_to_cart.png")
        except Exception as e:
            logger.error(f"Error adding to cart: {str(e)}")
        
        # If add to cart was successful, proceed to checkout if auto_checkout is enabled
        if add_to_cart_success:
            # Try to verify we're on a cart page
            is_cart = await verify_cart_page(page)
            
            if is_cart:
                # Get the current URL (could be redirect to cart)
                current_url = page.url
                logger.info(f"Current URL after adding to cart: {current_url}")
                
                # Try to extract additional information from the cart page
                cart_info = await extract_cart_info(page)
                
                # Complete with auto-checkout if enabled
                if auto_checkout:
                    logger.info("Auto-checkout is enabled, proceeding to checkout")
                    
                    checkout_success = False
                    try:
                        # Look for checkout button with various selectors
                        checkout_button_selectors = [
                            "a:has-text('Checkout')",
                            "button:has-text('Checkout')",
                            "a:has-text('Proceed to Checkout')",
                            "button:has-text('Proceed to Checkout')",
                            "a:has-text('Complete Purchase')",
                            "button:has-text('Complete Purchase')",
                            "a.checkout-button",
                            "button.checkout-button",
                            "[data-testid='checkout']"
                        ]
                        
                        for selector in checkout_button_selectors:
                            checkout_button = await page.query_selector(selector)
                            if checkout_button:
                                logger.info(f"Found checkout button with selector: {selector}")
                                await checkout_button.click()
                                logger.info("Clicked Checkout button")
                                checkout_success = True
                                await take_screenshot(page, "after_checkout_click.png")
                                
                                # Wait for navigation
                                try:
                                    await page.wait_for_load_state("networkidle", timeout=10000)
                                except Exception as e:
                                    logger.warning(f"Wait for navigation after checkout timed out: {str(e)}")
                                
                                # Get the final checkout URL
                                checkout_url = page.url
                                logger.info(f"Checkout URL: {checkout_url}")
                                
                                # Update cart info with checkout URL
                                cart_info['cart_url'] = checkout_url
                                break
                        
                        if not checkout_success:
                            logger.warning("Could not find checkout button with standard selectors")
                    except Exception as e:
                        logger.error(f"Error during checkout: {str(e)}")
                
                # Send notification with cart information
                if cart_info and cart_info.get('cart_url'):
                    # Enhance cart info with our known quantity
                    if 'quantity' not in cart_info or not cart_info['quantity']:
                        cart_info['quantity'] = quantity
                    
                    # Send Discord notification
                    await send_discord_notification(cart_info)
                    
                    return {
                        'success': True,
                        'date': cart_info.get('date', 'Unknown'),
                        'quantity': cart_info.get('quantity', quantity),
                        'section': cart_info.get('section', 'General'),
                        'price': cart_info.get('price'),
                        'cart_url': cart_info.get('cart_url')
                    }
            
        # If we couldn't add to cart or verify cart page, return failure
        logger.error("Could not successfully add tickets to cart")
        await take_screenshot(page, "cart_failure.png")
        return {
            'success': False,
            'date': '2025-07-19',
            'quantity': quantity,
            'section': 'General',
            'cart_url': ''
        }
    except Exception as e:
        logger.error(f"Error during automatic cart process: {str(e)}")
        traceback.print_exc()
        await take_screenshot(page, "error_state.png")
        return {
            'success': False,
            'date': '2025-07-19',
            'quantity': quantity if 'quantity' in locals() else 2,
            'section': 'General',
            'cart_url': ''
        }

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
            browser = await playwright.chromium.launch(headless=False)
            
            # Configure browser to avoid Cloudflare detection
            if CLOUDFLARE_SETTINGS["enabled"]:
                try:
                    # Alternative configuration for Cloudflare evasion
                    context = await browser.new_context(
                        viewport={"width": 1280, "height": 800},
                        user_agent=HUMAN_HEADERS["user-agent"],
                        locale="en-US",
                        timezone_id="America/New_York",
                        geolocation={"latitude": 40.7128, "longitude": -74.0060},
                        permissions=["geolocation"]
                    )
                    
                    # Inject script to evade detection
                    await context.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => false,
                        });
                        
                        // Prevent Cloudflare from detecting automation
                        if (window.navigator.permissions) {
                            window.navigator.permissions.query = (parameters) => {
                                return Promise.resolve({state: 'granted'});
                            };
                        }
                        
                        // Hide the fact that we're running headless
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3, 4, 5],
                        });
                        
                        // Override the languages
                        Object.defineProperty(navigator, 'languages', {
                            get: () => ['en-US', 'en', 'es'],
                        });
                    """)
                    
                    logger.info("Browser configured to avoid Cloudflare detection")
                except Exception as e:
                    logger.warning(f"Failed to configure browser for Cloudflare: {str(e)}")
                    # Fall back to standard context creation
                    context = await browser.new_context(
                        viewport={"width": 1280, "height": 800},
                        user_agent=HUMAN_HEADERS["user-agent"]
                    )
            else:
                # Standard context creation
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent=HUMAN_HEADERS["user-agent"]
                )
            
            # Set extra HTTP headers for human-like behavior
            if CLOUDFLARE_SETTINGS["use_human_headers"]:
                await context.set_extra_http_headers(HUMAN_HEADERS)
            
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
                    viewport={"width": 1280, "height": 800},
                    user_agent=HUMAN_HEADERS["user-agent"],
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
                print("==================================================")
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
                
                break
            
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
        asyncio.run(monitor_tickets(
            manual_mode=manual_mode, 
            test_mode=test_mode,
            persistent_browser=persistent_browser
        ))
    except KeyboardInterrupt:
        print("\nScript interrupted by user. Exiting.")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
