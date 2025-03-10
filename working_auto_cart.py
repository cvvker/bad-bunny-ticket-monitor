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
    Function to specifically handle seat selection from a seat map interface
    
    Steps:
    1. Wait for seat map to fully load
    2. Identify available seats (blue or green circles)
    3. Click on available seat
    4. Handle pop-up with seat details
    5. Confirm selection
    """
    logger.info("Step 2: Selecting available seats from the map...")
    
    try:
        # Wait for the seat map to fully load
        logger.info("Waiting for seat map to load completely...")
        # Give extra time for the seat map JavaScript to initialize
        await asyncio.sleep(5)
        await page.wait_for_load_state('networkidle')
        
        # Look for available seats (blue or green circles)
        blue_seats_selector = "circle[fill='#4a89dc'], circle[fill='#5D9CEC']"
        green_seats_selector = "circle[fill='#A0D468'], circle[fill='#8CC152']"
        
        # Additional fallback selectors for different seat types
        gray_seats_selector = "circle[fill='#CCD1D9'], circle[fill='#AAB2BD']"  # Sometimes gray seats are actually available
        any_circle_selector = "circle:not([fill='#E6E9ED']):not([fill='#F5F7FA'])"  # Any non-white circle
        any_seat_selector = ".seat-selector, .seat-item, [data-testid='seat'], [role='button'][aria-label*='seat']"
        
        logger.info("Looking for available seats (blue or green circles)...")
        
        # Check for blue seats first (usually cheaper)
        has_blue_seats = await page.locator(blue_seats_selector).count() > 0
        logger.info(f"Blue seats available: {has_blue_seats}")
        
        # Then check for green seats
        has_green_seats = await page.locator(green_seats_selector).count() > 0
        logger.info(f"Green seats available: {has_green_seats}")
        
        # If no blue or green seats, check for gray seats
        has_gray_seats = False
        if not has_blue_seats and not has_green_seats:
            has_gray_seats = await page.locator(gray_seats_selector).count() > 0
            logger.info(f"Gray seats available: {has_gray_seats}")
        
        # Try to select a seat based on availability
        seat_selected = False
        section_info = ""
        
        # First try blue seats
        if has_blue_seats:
            logger.info("Selecting blue seat...")
            blue_seat = await page.locator(blue_seats_selector).first
            await blue_seat.click()
            seat_selected = True
            section_info = "Blue section"
        # Then try green seats
        elif has_green_seats:
            logger.info("Selecting green seat...")
            green_seat = await page.locator(green_seats_selector).first
            await green_seat.click()
            seat_selected = True
            section_info = "Green section"
        # Then try gray seats as a fallback
        elif has_gray_seats:
            logger.info("Selecting gray seat (fallback)...")
            gray_seat = await page.locator(gray_seats_selector).first
            await gray_seat.click()
            seat_selected = True
            section_info = "Gray section"
        # Last resort: try any circle that might be a seat
        else:
            # Check if there are any clickable circles
            any_circles = await page.locator(any_circle_selector).count() > 0
            if any_circles:
                logger.info("Attempting to select any available circle...")
                await page.locator(any_circle_selector).first.click()
                seat_selected = True
                section_info = "Unknown section"
            # If no circles, try any element that might be a seat
            else:
                any_seats = await page.locator(any_seat_selector).count() > 0
                if any_seats:
                    logger.info("Attempting to select any seat element...")
                    await page.locator(any_seat_selector).first.click()
                    seat_selected = True
                    section_info = "Unknown section"
                else:
                    logger.warning("No available seats (blue, green, or fallback) found on the map")
                    await page.screenshot(path="no_available_seats.png")
                    return False, ""
        
        # Wait for popup to confirm selection
        logger.info("Waiting for confirmation popup after seat selection...")
        popup_confirmations = [
            "button:has-text('Confirmar')",
            "button:has-text('Confirm')",
            "button:has-text('Select')",
            "button:has-text('Add to Cart')",
            "[data-testid='confirm-button']",
            ".confirm-button",
            "button.btn-primary",
            "button.confirm-selection"
        ]
        
        for selector in popup_confirmations:
            try:
                if await page.locator(selector).count() > 0:
                    logger.info(f"Found confirmation button with selector: {selector}")
                    await page.locator(selector).click()
                    await page.wait_for_timeout(1000)  # Wait for the click to register
                    break
            except Exception as e:
                logger.warning(f"Couldn't click confirmation button with selector {selector}: {str(e)}")
        
        # Take screenshot of the result
        await page.screenshot(path="seat_selection_result.png")
        
        return seat_selected, section_info
        
    except Exception as e:
        logger.error(f"Error selecting seat: {str(e)}")
        await page.screenshot(path="seat_selection_error.png")
        return False, ""

async def automatic_cart_process(page, event_url, options=None):
    """
    Automated process for selecting seats and adding them to cart
    
    Args:
        page: Playwright page object
        event_url: URL of the event to cart
        options: Dictionary containing cart options:
            - quantity: Number of tickets to purchase (1-8)
            - auto_checkout: Whether to proceed to checkout automatically
            - best_available: Whether to select best available seats
    
    Returns:
        Dictionary with cart results
    """
    logger.info(f"Starting automatic carting process for: {event_url}")
    
    try:
        # Extract options
        quantity = options.get('quantity', 2) if options else 2
        auto_checkout = options.get('auto_checkout', False) if options else False
        best_available = options.get('best_available', True) if options else True
        event_date = options.get('event_date', 'Event') if options else 'Event'
        
        # Initialize result dictionary
        result = {
            "success": False,
            "message": "",
            "section": "",
            "quantity": quantity,
            "price": "",
            "cart_url": "",
            "screenshot_path": ""
        }
        
        # Step 1: Open the event page
        logger.info("Step 1: Opening event page...")
        logger.info(f"Navigating to {event_url}")
        await page.goto(event_url, wait_until='domcontentloaded')
        
        # Take screenshot for debugging
        await take_screenshot(page, "step1_event_page.png")
        
        # Step 2: Determine if this is a direct checkout link or event page
        logger.info("Step 2: Determining page type...")
        
        is_direct_checkout = "shop.ticketera.com/checkout" in event_url
        
        if is_direct_checkout:
            logger.info("Detected direct checkout link, processing...")
            # Handle direct checkout page
            result = await process_direct_checkout(page, quantity, event_date)
        else:
            # Regular event page flow
            logger.info("Waiting for seat map to load completely...")
            
            # Check if we need to wait for the seat map to load
            await page.wait_for_load_state('networkidle')
            
            seat_map_visible = await is_element_visible(page, "#seats .seat-map")
            
            if seat_map_visible:
                # Step 3: Select seats from the map
                logger.info("Step 3: Selecting available seats from the map...")
                seat_selected = await select_seat_from_map(page)
                
                if not seat_selected:
                    logger.warning("Failed to select seats from map, trying alternative options...")
                    # Try the "Best Available" option if enabled
                    if best_available:
                        logger.info("Trying 'Best Available' option...")
                        seat_selected = await select_best_available(page, quantity)
                    
                    if not seat_selected:
                        await take_screenshot(page, "failed_seat_selection.png")
                        result["message"] = "Failed to select any available seats"
                        return result
                
                # Step 4: Set quantity if needed
                logger.info(f"Step 4: Setting quantity to {quantity}...")
                await set_quantity(page, quantity)
                
                # Step 5: Handle any popups
                logger.info("Step 5: Handling popups...")
                await handle_popup(page)
            else:
                # Try alternative approaches if seat map is not visible
                logger.info("Seat map not detected, trying alternative approaches...")
                
                # Check if we have a section list instead
                sections_visible = await is_element_visible(page, ".sections-list")
                if sections_visible:
                    logger.info("Section list detected, selecting a section...")
                    section_selected = await select_section(page)
                    
                    if section_selected:
                        # Now we should have a seat map loaded
                        logger.info("Section selected, now selecting seats...")
                        seat_selected = await select_seat_from_map(page)
                        
                        # Set quantity after selecting section
                        await set_quantity(page, quantity)
                    else:
                        logger.warning("Failed to select a section")
                        result["message"] = "Failed to select a section"
                        return result
                else:
                    # Try Best Available option as a fallback
                    logger.info("Trying 'Best Available' option as fallback...")
                    seat_selected = await select_best_available(page, quantity)
                    
                    if not seat_selected:
                        logger.warning("Failed to select any available seats through all methods")
                        result["message"] = "No available seats found through any method"
                        return result
            
            # Step 6: Click the add to cart or checkout button
            logger.info("Step 6: Adding to cart...")
            cart_success = await add_to_cart(page)
            
            if not cart_success:
                logger.warning("Failed to add tickets to cart")
                result["message"] = "Failed to add tickets to cart"
                return result
        
        # Step 7: Extract cart information and take screenshot
        logger.info("Step 7: Extracting cart information...")
        cart_info = await extract_cart_info(page)
        
        if cart_info:
            result["success"] = True
            result["section"] = cart_info.get("section", "")
            result["price"] = cart_info.get("price", "")
            result["cart_url"] = page.url
            result["message"] = "Tickets added to cart successfully"
            
            # Take screenshot of successful cart
            screenshot_path = "successful_cart.png"
            await take_screenshot(page, screenshot_path)
            result["screenshot_path"] = screenshot_path
            
            # Send a Discord notification about the successful cart
            logger.info("Sending cart notification...")
            try:
                send_cart_notification(
                    event_date=event_date,
                    quantity=quantity,
                    section=result["section"],
                    price=result["price"],
                    cart_url=result["cart_url"]
                )
            except Exception as e:
                logger.error(f"Error sending cart notification: {str(e)}")
            
            # Step 8: Proceed to checkout if auto_checkout is enabled
            if auto_checkout:
                logger.info("Step 8: Proceeding to checkout...")
                checkout_success = await proceed_to_checkout(page)
                
                if checkout_success:
                    logger.info("Successfully proceeded to checkout")
                    result["message"] += ", and proceeded to checkout"
                else:
                    logger.warning("Failed to proceed to checkout, but tickets are in cart")
                    result["message"] += ", but failed to proceed to checkout"
            
            logger.info(f"Cart process completed successfully. Cart URL: {result['cart_url']}")
        else:
            logger.warning("Failed to extract cart information")
            result["message"] = "Tickets may be in cart, but failed to extract cart information"
            result["cart_url"] = page.url
        
        return result
        
    except Exception as e:
        logger.error(f"Error in automatic cart process: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Take screenshot for debugging
        await take_screenshot(page, "cart_error.png")
        
        return {
            "success": False,
            "message": f"Error: {str(e)}",
            "section": "",
            "quantity": quantity if 'quantity' in locals() else 2,
            "price": "",
            "cart_url": page.url,
            "screenshot_path": "cart_error.png"
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

def send_cart_notification(event_date, quantity, section, price, cart_url):
    """
    Send a Discord notification when tickets are successfully added to cart
    
    Args:
        event_date: Date of the event
        quantity: Number of tickets
        section: Section of the tickets
        price: Price of the tickets (if available)
        cart_url: URL to the cart
    """
    try:
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            logger.warning("No Discord webhook URL found in environment variables")
            return
            
        logger.info("Sending Discord notification...")
        
        # Format the price nicely if available
        price_text = f"Price: {price}" if price else "Price: Not available"
        
        # Prepare the embed for Discord
        embed = {
            "title": "🎟️ TICKETS SUCCESSFULLY CARTED! 🎟️",
            "description": "Tickets have been successfully added to your cart! Click the button below to complete your purchase.",
            "color": 5814783,  # Green color
            "fields": [
                {
                    "name": "📅 Event Date",
                    "value": str(event_date),
                    "inline": True
                },
                {
                    "name": "🎫 Quantity",
                    "value": str(quantity),
                    "inline": True
                },
                {
                    "name": "📍 Section",
                    "value": section if section else "Not specified",
                    "inline": True
                },
                {
                    "name": "💰 Price",
                    "value": price_text,
                    "inline": True
                },
                {
                    "name": "⏱️ Time Remaining",
                    "value": "⚠️ Complete your purchase ASAP! Cart may expire in 10-15 minutes.",
                    "inline": False
                }
            ],
            "footer": {
                "text": f"TOVK Band Auto-Cart System • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        }
        
        # Create a message with a button link to the cart
        message = {
            "content": "@everyone **TICKETS FOUND AND CARTED!** Complete your purchase immediately!",
            "embeds": [embed],
            "components": [
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "style": 5,  # Link button
                            "label": "🔗 GO TO CART",
                            "url": cart_url
                        }
                    ]
                }
            ]
        }
        
        # Add step-by-step checkout instructions
        instructions_embed = {
            "title": "📋 Checkout Instructions",
            "description": "Follow these steps to complete your purchase:",
            "color": 16776960,  # Yellow color
            "fields": [
                {
                    "name": "Step 1",
                    "value": "Sign in to your Ticketera account (if not already signed in)",
                    "inline": False
                },
                {
                    "name": "Step 2",
                    "value": "Verify your ticket selection and quantity",
                    "inline": False
                },
                {
                    "name": "Step 3",
                    "value": "Enter payment information and complete purchase",
                    "inline": False
                },
                {
                    "name": "Step 4",
                    "value": "Save/screenshot your confirmation page and order number",
                    "inline": False
                }
            ]
        }
        
        # Add the instructions embed to the message
        message["embeds"].append(instructions_embed)
        
        # Send the notification
        headers = {'Content-Type': 'application/json'}
        response = requests.post(webhook_url, json=message, headers=headers)
        
        # Send a second notification for critical changes (as per user preference)
        duplicate_message = {
            "content": "⚠️ **REMINDER: TICKETS IN CART - COMPLETE PURCHASE NOW!** ⚠️",
            "embeds": [embed]
        }
        time.sleep(1)  # Brief delay between messages
        requests.post(webhook_url, json=duplicate_message, headers=headers)
        
        if response.status_code == 204:
            logger.info("Discord notification sent successfully")
        else:
            logger.warning(f"Failed to send Discord notification: {response.status_code} {response.text}")
            
    except Exception as e:
        logger.error(f"Error sending Discord notification: {str(e)}")
        logger.error(traceback.format_exc())

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

async def take_screenshot(page, filename):
    """
    Take a screenshot and save it to the specified filename
    
    Args:
        page: Playwright page object
        filename: Name of the file to save the screenshot to
    """
    try:
        screenshot_dir = "screenshots"
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)
        
        full_path = os.path.join(screenshot_dir, filename)
        await page.screenshot(path=full_path)
        logger.info(f"Screenshot saved to {full_path}")
        return full_path
    except Exception as e:
        logger.error(f"Error taking screenshot: {str(e)}")
        return None


async def is_element_visible(page, selector, timeout=2000):
    """
    Check if an element is visible on the page
    
    Args:
        page: Playwright page object
        selector: CSS selector to check
        timeout: Timeout in milliseconds
        
    Returns:
        True if element is visible, False otherwise
    """
    try:
        element = await page.wait_for_selector(selector, timeout=timeout, state="visible")
        return element is not None
    except Exception:
        return False


async def click_element_if_visible(page, selector, timeout=2000):
    """
    Click an element if it is visible on the page
    
    Args:
        page: Playwright page object
        selector: CSS selector to click
        timeout: Timeout in milliseconds
        
    Returns:
        True if element was clicked, False otherwise
    """
    try:
        element = await page.wait_for_selector(selector, timeout=timeout, state="visible")
        if element:
            await element.click()
            return True
        return False
    except Exception:
        return False


async def select_best_available(page, quantity=2):
    """
    Select the "Best Available" option on the ticket page
    
    Args:
        page: Playwright page object
        quantity: Number of tickets to select
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Try different selectors for "Best Available" buttons
        best_available_selectors = [
            "button:has-text('Best Available')",
            "button:has-text('Mejor Disponible')",
            "[data-testid='best-available-button']",
            ".best-available-button",
            "a:has-text('Best Available')"
        ]
        
        for selector in best_available_selectors:
            if await click_element_if_visible(page, selector):
                logger.info(f"Clicked Best Available button: {selector}")
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(1)  # Wait for any animations
                
                # Set quantity if needed
                await set_quantity(page, quantity)
                
                # Look for any confirm buttons
                confirm_selectors = [
                    "button:has-text('Confirm')",
                    "button:has-text('Confirmar')",
                    "button:has-text('Continue')",
                    "button:has-text('Continuar')",
                    "button.btn-primary",
                    "button.confirm-button"
                ]
                
                for confirm_selector in confirm_selectors:
                    if await click_element_if_visible(page, confirm_selector):
                        logger.info(f"Clicked confirm button: {confirm_selector}")
                        await page.wait_for_load_state('networkidle')
                        break
                
                # If we got here but didn't find a confirm button,
                # we still consider it a success since we clicked Best Available
                return True
                
        logger.warning("Best Available option not found")
        return False
        
    except Exception as e:
        logger.error(f"Error selecting Best Available: {str(e)}")
        return False


async def set_quantity(page, quantity=2):
    """
    Set the quantity of tickets to purchase
    
    Args:
        page: Playwright page object
        quantity: Number of tickets to select
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Wait a moment for any quantity inputs to be visible
        await asyncio.sleep(0.5)
        
        # Look for quantity input fields
        quantity_selectors = [
            "input[type='number']",
            ".quantity-input",
            "[data-testid='quantity-input']",
            "select.quantity-select"
        ]
        
        for selector in quantity_selectors:
            quantity_element = await page.query_selector(selector)
            if quantity_element:
                logger.info(f"Found quantity input with selector: {selector}")
                
                # Check if it's a select element
                tag_name = await quantity_element.evaluate("el => el.tagName.toLowerCase()")
                
                if tag_name == "select":
                    # For select elements, try to select the option with the desired quantity
                    options = await quantity_element.query_selector_all("option")
                    option_found = False
                    
                    for option in options:
                        value = await option.get_attribute("value")
                        if value and value.isdigit() and int(value) == quantity:
                            await quantity_element.select_option(value=value)
                            logger.info(f"Selected quantity {quantity} from dropdown")
                            option_found = True
                            break
                    
                    if not option_found:
                        # If we couldn't find the exact quantity, pick the closest one
                        closest_value = None
                        closest_diff = float('inf')
                        
                        for option in options:
                            value = await option.get_attribute("value")
                            if value and value.isdigit():
                                diff = abs(int(value) - quantity)
                                if diff < closest_diff:
                                    closest_diff = diff
                                    closest_value = value
                        
                        if closest_value:
                            await quantity_element.select_option(value=closest_value)
                            logger.info(f"Selected closest quantity {closest_value} from dropdown")
                            return True
                else:
                    # For input elements
                    await quantity_element.fill(str(quantity))
                    logger.info(f"Set quantity to {quantity}")
                    
                    # Look for any "Apply" or "Update" buttons
                    update_selectors = [
                        "button:has-text('Apply')",
                        "button:has-text('Update')",
                        "button:has-text('Aplicar')",
                        "button:has-text('Actualizar')",
                        "button.apply-button",
                        "button.update-button"
                    ]
                    
                    for update_selector in update_selectors:
                        if await click_element_if_visible(page, update_selector):
                            logger.info(f"Clicked update button: {update_selector}")
                            await page.wait_for_load_state('networkidle')
                            break
                
                return True
        
        logger.info("No quantity input found, using default quantity")
        return False
        
    except Exception as e:
        logger.error(f"Error setting quantity: {str(e)}")
        return False


async def handle_popup(page):
    """
    Handle any popups that appear during the checkout process
    
    Args:
        page: Playwright page object
        
    Returns:
        True if a popup was handled, False otherwise
    """
    try:
        # Look for common popup elements and their confirm/continue buttons
        popup_button_selectors = [
            "button:has-text('Confirm')",
            "button:has-text('Confirmar')",
            "button:has-text('Continue')",
            "button:has-text('Continuar')",
            "button:has-text('Accept')",
            "button:has-text('Aceptar')",
            "button:has-text('OK')",
            "button.popup-confirm",
            "button.continue-button",
            ".popup button.btn-primary",
            ".modal button.btn-primary"
        ]
        
        for selector in popup_button_selectors:
            if await click_element_if_visible(page, selector):
                logger.info(f"Clicked popup button: {selector}")
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(0.5)  # Wait for any transitions
                
                # Check if we need to set quantity
                quantity_input = await page.query_selector("input[type='number'], .quantity-input")
                if quantity_input:
                    logger.info("Setting quantity to 2")
                    await quantity_input.fill("2")
                    
                    # Look for an apply or update button
                    update_button = await page.query_selector("button:has-text('Apply'), button:has-text('Update'), button:has-text('Aplicar'), button:has-text('Actualizar')")
                    if update_button:
                        await update_button.click()
                        await page.wait_for_load_state('networkidle')
                
                return True
                
        return False
        
    except Exception as e:
        logger.error(f"Error handling popup: {str(e)}")
        return False


async def add_to_cart(page):
    """
    Click the add to cart or proceed to checkout button
    
    Args:
        page: Playwright page object
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Look for add to cart or checkout buttons
        cart_button_selectors = [
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
        
        for selector in cart_button_selectors:
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
                                    try:
                                        await send_discord_notification({
                                            'success': True,
                                            'message': f"Successfully added {len(cart_items)} tickets to cart!",
                                            'url': cart_url,
                                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        })
                                    except Exception as notification_error:
                                        logger.error(f"Error sending Discord notification: {str(notification_error)}")
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
                                        return True
                                except Exception as e:
                                    logger.debug(f"Failed to click checkout button with selector {checkout_selector}: {str(e)}")
                            
                            # If we couldn't click a checkout button but are on cart page, still consider success
                            return True
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
            logger.info(f"Successfully on cart page: {page.url}")
            return True
        
        # Last resort: Try to look for text indicating we're on a relevant page
        try:
            page_text = await page.evaluate("() => document.body.innerText")
            if "cart" in page_text.lower() or "carrito" in page_text.lower():
                logger.info("Page text contains 'cart' or 'carrito', might be on cart page")
                return True
        except Exception as e:
            logger.debug(f"Error checking page text: {str(e)}")
            
        logger.warning("Could not add tickets to cart")
        return False
        
    except Exception as e:
        logger.error(f"Error adding to cart: {str(e)}")
        return False


async def verify_cart_page(page):
    """
    Verify if the current page is a cart page
    
    Args:
        page: Playwright page object
        
    Returns:
        True if the page is a cart page, False otherwise
    """
    try:
        # Check URL for cart/checkout indicators
        current_url = page.url
        if any(keyword in current_url.lower() for keyword in ['cart', 'carrito', 'checkout', 'pagar', 'payment']):
            logger.info(f"URL suggests we're on a cart/checkout page: {current_url}")
            return True
            
        # Check for cart/checkout page elements
        cart_page_selectors = [
            "h1:has-text('Shopping Cart'), h1:has-text('Carrito')",
            "h1:has-text('Checkout'), h1:has-text('Pagar')",
            "div.cart, div.cart-container",
            "div.checkout, div.checkout-container",
            ".cart-items, .checkout-items",
            "[data-testid='cart'], [data-testid='checkout']",
            ".cart-summary, .checkout-summary",
            "div:has-text('Shopping Cart'):not(:has-text('Shopping Cart.'))",
            "div:has-text('Carrito'):not(:has-text('Carrito.'))",
            "div:has-text('Order Summary'):not(:has-text('Order Summary.'))",
            "div:has-text('Resumen de Orden'):not(:has-text('Resumen de Orden.'))"
        ]
        
        for selector in cart_page_selectors:
            element = await page.query_selector(selector)
            if element:
                logger.info(f"Found cart/checkout page element with selector: {selector}")
                return True
                
        # Check page title
        title = await page.title()
        if any(keyword in title.lower() for keyword in ['cart', 'carrito', 'checkout', 'pagar', 'payment']):
            logger.info(f"Page title suggests we're on a cart/checkout page: {title}")
            return True
            
        # Check for order summary or cart total elements
        total_selectors = [
            ".order-total, .cart-total",
            ".summary-total, .checkout-total",
            "div:has-text('Total'):not(:has-text('Total.'))",
            ".price-total, .amount-total"
        ]
        
        for selector in total_selectors:
            element = await page.query_selector(selector)
            if element:
                logger.info(f"Found total/summary element with selector: {selector}")
                return True
                
        logger.warning("Could not verify if the current page is a cart page")
        return False
        
    except Exception as e:
        logger.error(f"Error verifying cart page: {str(e)}")
        return False

async def proceed_to_checkout(page):
    """
    Click the proceed to checkout button
    
    Args:
        page: Playwright page object
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Look for proceed to checkout buttons
        checkout_button_selectors = [
            "button:has-text('Proceed to Checkout')",
            "button:has-text('Checkout')",
            "button:has-text('Finalizar Compra')",
            "button:has-text('Complete Purchase')",
            "button:has-text('Completar Compra')",
            "button:has-text('Continuar')",
            "a:has-text('Checkout')",
            "a:has-text('Finalizar Compra')",
            "button.checkout-button",
            "[data-testid='checkout-button']",
            "button.btn-primary:has-text('Continue')",
            "button.btn-success"
        ]
        
        for selector in checkout_button_selectors:
            if await click_element_if_visible(page, selector):
                logger.info(f"Clicked proceed to checkout button: {selector}")
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(1)  # Wait for any transitions
                
                # Handle any popups that might appear
                await handle_popup(page)
                
                # Take a screenshot to help with debugging
                await take_screenshot(page, "after_proceed_to_checkout.png")
                
                return True
                
        logger.warning("Proceed to checkout button not found")
        await take_screenshot(page, "proceed_to_checkout_button_not_found.png")
        return False
        
    except Exception as e:
        logger.error(f"Error proceeding to checkout: {str(e)}")
        return False


async def send_discord_notification(data):
    """
    Send a notification to Discord webhook
    
    Args:
        data: Dictionary with notification data
    """
    try:
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            logger.warning("No Discord webhook URL found in environment variables")
            return
            
        # Create a Discord embed object
        embed = {
            "title": "🎟️ Ticket Monitor Alert",
            "description": data.get('message', 'Ticket status update'),
            "color": 5814783,  # Green color
            "fields": [],
            "footer": {
                "text": f"TOVK Band Ticket Monitor • {data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}"
            }
        }
        
        # Add URL as a field if available
        if 'url' in data:
            embed["fields"].append({
                "name": "🔗 URL",
                "value": data['url'],
                "inline": False
            })
            
        # Create the Discord message
        message = {
            "content": "@everyone **ALERT!** Ticket status change detected!",
            "embeds": [embed]
        }
        
        # Send the notification
        headers = {'Content-Type': 'application/json'}
        response = requests.post(webhook_url, json=message, headers=headers)
        
        if response.status_code == 204:
            logger.info("Discord notification sent successfully")
        else:
            logger.warning(f"Failed to send Discord notification: {response.status_code} {response.text}")
            
    except Exception as e:
        logger.error(f"Error sending Discord notification: {str(e)}")
