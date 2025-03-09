"""
Live Cart Testing Script

This script allows testing of the cart automation feature with a real Ticketera event page.
It loads a specified event URL and attempts to add tickets to cart.
"""

import os
import sys
import json
import time
import logging
from playwright.sync_api import sync_playwright

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("cart_test")

# Discord webhook from configuration
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1347702022039666783/IIgJ2B6vT5aQoTjNOadVxdAviHuEsCRR8zwu4CgWAvWzcob9BJ0_5XQC-BTyVauTljR_"

# Test configuration
TEST_CONFIG = {
    "event_url": "https://www.ticketera.com/",  # Replace with actual event URL
    "quantity": 2,                             # Number of tickets to attempt to cart
    "max_price": 350,                          # Maximum price per ticket
    "sections": [],                            # Preferred sections (leave empty for any)
    "headless": False,                         # Set to False to see the browser in action
    "slow_mo": 100                             # Slow down automation for visibility (in ms)
}

def perform_cart_test():
    """Perform a live cart test with Playwright"""
    logger.info(f"Starting live cart test for URL: {TEST_CONFIG['event_url']}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=TEST_CONFIG["headless"],
            slow_mo=TEST_CONFIG["slow_mo"]
        )
        
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        
        page = context.new_page()
        logger.info("Browser launched and page created")
        
        try:
            # Navigate to the event page
            logger.info(f"Navigating to: {TEST_CONFIG['event_url']}")
            page.goto(TEST_CONFIG["event_url"], wait_until="networkidle")
            
            # Wait for page to fully load
            page.wait_for_load_state("networkidle")
            
            # Check if we need to navigate to a specific event from the homepage
            if "ticketera.com/" in TEST_CONFIG["event_url"] and not "/events/" in TEST_CONFIG["event_url"]:
                logger.info("On homepage, looking for an event to test with...")
                
                # Click on one of the featured events
                event_links = page.query_selector_all("a.event-link, a.featured-event, a[href*='/events/']")
                if event_links and len(event_links) > 0:
                    # Click the first available event
                    event_url = event_links[0].get_attribute("href")
                    event_name = event_links[0].inner_text().strip() or "Test Event"
                    
                    logger.info(f"Found event: {event_name} - Navigating to: {event_url}")
                    page.goto(event_url, wait_until="networkidle")
                else:
                    logger.error("No events found on homepage. Please provide a direct event URL.")
                    return False
            
            # Check if the Buy Tickets button is available
            logger.info("Looking for Buy Tickets button...")
            buy_button = page.query_selector("a.buy-tickets, a[href*='buy'], button:has-text('Buy'), a:has-text('Buy')")
            
            if buy_button:
                logger.info("Found Buy Tickets button - clicking...")
                buy_button.click()
                
                # Wait for ticket selection page
                page.wait_for_load_state("networkidle")
                time.sleep(2)  # Extra safety wait
                
                # Try to select tickets
                logger.info("Attempting to select tickets...")
                
                # Try different selectors for ticket quantity dropdown
                quantity_selectors = [
                    "select#quantity",
                    "select.quantity-select",
                    "select[name='quantity']",
                    "select"
                ]
                
                for selector in quantity_selectors:
                    quantity_dropdown = page.query_selector(selector)
                    if quantity_dropdown:
                        logger.info(f"Found quantity dropdown with selector: {selector}")
                        quantity_dropdown.select_option(str(TEST_CONFIG["quantity"]))
                        logger.info(f"Selected {TEST_CONFIG['quantity']} tickets")
                        break
                
                # Try to select a section if available and if we have preferences
                if TEST_CONFIG["sections"] and len(TEST_CONFIG["sections"]) > 0:
                    section_selected = False
                    logger.info(f"Looking for preferred sections: {TEST_CONFIG['sections']}")
                    
                    for section in TEST_CONFIG["sections"]:
                        section_option = page.query_selector(f"option:has-text('{section}'), div:has-text('{section}')")
                        if section_option:
                            logger.info(f"Found preferred section: {section}")
                            section_option.click()
                            section_selected = True
                            break
                    
                    if not section_selected:
                        logger.info("No preferred sections found, proceeding with default selection")
                
                # Look for "Add to Cart" or similar buttons
                add_cart_button = page.query_selector(
                    "button:has-text('Add to Cart'), button:has-text('Add'), button:has-text('Cart'), "
                    "a:has-text('Add to Cart'), input[value='Add to Cart'], button.add-to-cart"
                )
                
                if add_cart_button:
                    logger.info("Found Add to Cart button - clicking...")
                    add_cart_button.click()
                    
                    # Wait for cart confirmation
                    page.wait_for_load_state("networkidle")
                    time.sleep(3)  # Wait for cart update
                    
                    # Check if we successfully added to cart
                    cart_indicators = [
                        page.query_selector("div:has-text('Successfully added to cart')"),
                        page.query_selector("div.cart-confirmation"),
                        page.query_selector("a:has-text('Checkout')"),
                        page.query_selector("div:has-text('Cart')")
                    ]
                    
                    if any(cart_indicators):
                        logger.info("SUCCESS: Tickets successfully added to cart!")
                        
                        # Try to get the cart URL for checkout
                        checkout_url = page.url
                        
                        # Take a screenshot of the success
                        screenshot_path = os.path.join(os.path.dirname(__file__), "cart_success.png")
                        page.screenshot(path=screenshot_path)
                        logger.info(f"Screenshot saved to: {screenshot_path}")
                        
                        # Show success message with instructions
                        logger.info("=" * 50)
                        logger.info("CART TEST SUCCESSFUL")
                        logger.info(f"Checkout URL: {checkout_url}")
                        logger.info("=" * 50)
                        
                        return True
                    else:
                        logger.warning("Could not confirm if tickets were added to cart")
                        return False
                else:
                    logger.error("Add to Cart button not found")
                    return False
            else:
                logger.error("Buy Tickets button not found")
                return False
                
        except Exception as e:
            logger.error(f"Error during test: {str(e)}")
            return False
        finally:
            # Take a final screenshot
            page.screenshot(path=os.path.join(os.path.dirname(__file__), "cart_test_final.png"))
            
            time.sleep(3)  # Give time to see the final state
            browser.close()
            logger.info("Browser closed")

def main():
    """Main function"""
    print("\n" + "=" * 50)
    print("LIVE CART TEST".center(50))
    print("=" * 50 + "\n")
    
    # Ask for a specific event URL if not provided
    if TEST_CONFIG["event_url"] == "https://www.ticketera.com/":
        custom_url = input("Enter a specific event URL to test (or press Enter to use a random event): ")
        if custom_url.strip():
            TEST_CONFIG["event_url"] = custom_url.strip()
    
    # Perform the test
    success = perform_cart_test()
    
    if success:
        print("\nCart test completed successfully!")
    else:
        print("\nCart test failed.")
    
    print("\nCheck the logs above for details.")

if __name__ == "__main__":
    main()
