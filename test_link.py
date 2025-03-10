#!/usr/bin/env python3
"""
Test script to run the autocart with a specific URL
"""
import asyncio
import os
import json
from datetime import datetime
from working_auto_cart import monitor_tickets, EVENT_URLS, DANNY_OCEAN_DATES

async def main():
    # Set the test URL directly
    test_url = "https://shop.ticketera.com/checkout/como-coco-ikmk2p?_gl=1*nkwzt0*_gcl_au*MTc5Nzk3NjMzOC4xNzM2Nzg3MDg4"
    
    # Set a specific test date to use
    test_date = "2025-03-10-TEST"
    
    # Save original URLs
    original_urls = EVENT_URLS.copy()
    
    try:
        # Add our test URL with a specific test date
        EVENT_URLS[test_date] = test_url
        
        # Force use of our test date by modifying DANNY_OCEAN_DATES temporarily
        original_dates = DANNY_OCEAN_DATES.copy()
        DANNY_OCEAN_DATES.clear()
        DANNY_OCEAN_DATES.append(test_date)
        
        # Test options
        options = {
            "quantity": 2,
            "auto_checkout": False,
            "best_available": True,
            "event_date": "Bad Bunny Test Event"  # Provide a friendly name for the notification
        }
        
        print("\n==================================================")
        print("          TICKETERA AUTOCART TEST                 ")
        print("==================================================")
        print(f"Testing autocart with URL: {test_url}")
        print(f"Test date: {test_date}")
        print(f"Options: {json.dumps(options, indent=2)}")
        print("==================================================\n")
        
        start_time = datetime.now()
        
        # Run the monitor with test mode enabled
        result = await monitor_tickets(
            event_urls={test_date: test_url},
            event_dates=[test_date],
            manual_mode=True,       # Set to True to see the process step by step
            test_mode=True,         # Use test URLs
            persistent_browser=True, # Keep browser open after completion
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Display detailed results
        print("\n==================================================")
        print("          TEST RESULTS                            ")
        print("==================================================")
        print(f"Success: {'✅ YES' if result.get('success', False) else '❌ NO'}")
        
        if result.get('success', False):
            print(f"Cart URL: {result.get('cart_url', 'N/A')}")
            print(f"Checkout URL: {result.get('checkout_url', 'N/A')}")
            
            # Any additional information in the result dictionary
            for key, value in result.items():
                if key not in ['success', 'cart_url', 'checkout_url', 'error']:
                    print(f"{key.capitalize()}: {value}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
        
        print(f"Test duration: {duration:.2f} seconds")
        print("==================================================\n")
        
    finally:
        # Restore the original URLs and dates
        EVENT_URLS.clear()
        EVENT_URLS.update(original_urls)
        
        DANNY_OCEAN_DATES.clear()
        DANNY_OCEAN_DATES.extend(original_dates)
        
        print("Original URLs and dates restored.")
        print("Test completed.")

if __name__ == "__main__":
    asyncio.run(main())
