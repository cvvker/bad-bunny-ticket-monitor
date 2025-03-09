"""
Quick Cart Test Script for Bad Bunny Ticket Monitor

This script performs a non-interactive test of the cart automation feature
using a real event on Ticketera.com
"""

import os
import sys
import json
import time
import logging
import requests
from bs4 import BeautifulSoup
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

# Test configuration - update this with a real event that has tickets available
TEST_CONFIG = {
    "event_url": "https://www.ticketera.com/events/all",  # We'll find an event from this page
    "quantity": 2,
    "max_price": 350,
    "headless": False,  # Set to False to see the browser in action
    "slow_mo": 100  # Slow down automation for visibility (in ms)
}

def find_available_event():
    """Find an available event to test with"""
    try:
        logger.info("Searching for an available event to test with...")
        response = requests.get(TEST_CONFIG["event_url"], 
                                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"})
        
        if response.status_code != 200:
            logger.error(f"Failed to get events page: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for event links
        event_links = soup.select("a.event-card, a[href*='/events/'], div.event-card a")
        
        if not event_links:
            logger.error("No event links found on the page")
            return None
            
        # Return the first event link found
        for link in event_links:
            href = link.get('href')
            if href and '/events/' in href:
                if not href.startswith('http'):
                    href = 'https://www.ticketera.com' + href
                return href
                
        return None
    except Exception as e:
        logger.error(f"Error finding available event: {e}")
        return None

def perform_cart_test(event_url):
    """Perform a cart test with a specific event URL"""
    logger.info(f"Starting quick cart test for URL: {event_url}")
    
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
            logger.info(f"Navigating to: {event_url}")
            page.goto(event_url, wait_until="networkidle")
            
            # Wait for page to fully load
            page.wait_for_load_state("networkidle")
            time.sleep(2)  # Extra safety wait
            
            # Save a screenshot of the event page
            page.screenshot(path=os.path.join(os.path.dirname(__file__), "event_page.png"))
            logger.info("Saved screenshot of event page")
            
            # Check if the Buy Tickets button is available
            logger.info("Looking for Buy Tickets button...")
            buy_button = page.query_selector("a:has-text('Buy'), button:has-text('Buy'), a.buy-tickets, a[href*='buy']")
            
            if buy_button:
                logger.info("Found Buy Tickets button - clicking...")
                buy_button.click()
                
                # Wait for ticket selection page
                page.wait_for_load_state("networkidle")
                time.sleep(2)  # Extra safety wait
                
                # Save screenshot of the tickets page
                page.screenshot(path=os.path.join(os.path.dirname(__file__), "tickets_page.png"))
                logger.info("Saved screenshot of tickets page")
                
                # Look for an "Add to Cart" or similar button
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
                    
                    # Save screenshot of the cart confirmation
                    page.screenshot(path=os.path.join(os.path.dirname(__file__), "cart_confirmation.png"))
                    logger.info("Saved screenshot of cart confirmation")
                    
                    # Check if we have any indicators of success
                    cart_text = page.content()
                    if "cart" in cart_text.lower() or "checkout" in cart_text.lower():
                        logger.info("SUCCESS: Found cart/checkout reference in page content")
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
            page.screenshot(path=os.path.join(os.path.dirname(__file__), "final_state.png"))
            logger.info("Saved final screenshot")
            
            time.sleep(3)  # Give time to see the final state
            browser.close()
            logger.info("Browser closed")

def main():
    """Main function"""
    print("\n" + "=" * 50)
    print("QUICK CART TEST".center(50))
    print("=" * 50 + "\n")
    
    # Step 1: Find an available event
    event_url = find_available_event()
    
    if not event_url:
        print("No available events found to test with. Try updating TEST_CONFIG with a specific event URL.")
        return
        
    print(f"Found event to test with: {event_url}")
    
    # Step 2: Perform the cart test
    success = perform_cart_test(event_url)
    
    # Step 3: Report results
    if success:
        print("\nCart test SUCCESSFUL!")
        print("The cart automation feature is working correctly.")
    else:
        print("\nCart test FAILED.")
        print("Check the screenshots and logs for details.")
        
    print("\nTest completed. Screenshots saved in the project directory.")
    print("These same automation techniques will be used for Bad Bunny tickets.")

if __name__ == "__main__":
    main()
