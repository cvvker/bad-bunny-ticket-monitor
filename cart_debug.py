"""
Cart Automation Debug Utility

This script allows you to test the carting functionality without waiting for tickets to become available.
It simulates the ticket availability and carting process for debugging purposes.
"""

import os
import sys
import json
import requests
from datetime import datetime
import time
import random
import logging
import re

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("cart_debug")

# Discord webhook URL from the main configuration
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1347702022039666783/IIgJ2B6vT5aQoTjNOadVxdAviHuEsCRR8zwu4CgWAvWzcob9BJ0_5XQC-BTyVauTljR_"

# Test dates
BAD_BUNNY_DATES = {
    "july": ["12", "18", "19"],
    "august": ["01", "02", "03", "08", "09", "10", "15", "16", "17", "22", "23", "24", "29", "30", "31"],
    "september": ["05", "06", "07", "12", "13", "14"]
}

# Test configuration
TEST_CHECKOUT_URL = "https://shop.ticketera.com/checkout/67be0fb1c3855d04ea54843e"

def send_discord_notification(message, use_mentions=False):
    """Send a notification to Discord webhook"""
    if use_mentions:
        message = "@everyone " + message
    
    data = {
        "content": message,
        "username": "Bad Bunny Ticket Monitor",
        "avatar_url": "https://i.imgur.com/MQ3Dvz0.png"
    }
    
    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=data
        )
        response.raise_for_status()
        logger.info(f"Discord notification sent successfully")
    except Exception as e:
        logger.error(f"Error sending Discord notification: {e}")

def simulate_cart_success(event_id, event_name, checkout_url=TEST_CHECKOUT_URL):
    """Simulate a successful cart operation"""
    logger.info(f"Simulating successful cart for: {event_name}")
    
    # Extract date from event name
    date_match = re.search(r'(\w+ \d+)', event_name)
    event_date = date_match.group(1) if date_match else "Unknown date"
    
    # Create simulated cart info
    cart_info = {
        'date': event_date,
        'quantity': 2,
        'price': random.randint(150, 350),
        'section': random.choice(["Floor", "Lower Level", "Upper Level", "VIP", "General Admission"]),
        'cart_url': checkout_url
    }
    
    # Send enhanced notification with cart details
    try:
        data = {
            "username": "Bad Bunny Ticket Monitor",
            "avatar_url": "https://i.imgur.com/MQ3Dvz0.png",
            "embeds": [
                {
                    "title": "🎫 **[SIMULATION] TICKETS ADDED TO CART!** 🎫",
                    "color": 16711680,  # Red color
                    "fields": [
                        {
                            "name": "Event",
                            "value": f"Bad Bunny - {event_date}",
                            "inline": True
                        },
                        {
                            "name": "Quantity",
                            "value": str(cart_info['quantity']),
                            "inline": True
                        },
                        {
                            "name": "Price",
                            "value": f"${cart_info['price']}",
                            "inline": True
                        },
                        {
                            "name": "Section",
                            "value": cart_info['section'],
                            "inline": True
                        }
                    ],
                    "description": f"**[PROCEED TO CHECKOUT]({checkout_url})**\n\nMove quickly! Tickets may sell out.\n\n*This is a simulated carting success for testing purposes.*",
                    "footer": {
                        "text": "Bad Bunny Ticket Monitor - SIMULATION"
                    },
                    "timestamp": datetime.now().isoformat()
                }
            ],
            "content": "@everyone"
        }
        
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json=data
        )
        response.raise_for_status()
        logger.info(f"Discord notification sent successfully")
    except Exception as e:
        logger.error(f"Error sending Discord notification: {e}")
    
    return {
        'success': True,
        'eventId': event_id,
        'status': 'success',
        'cart_info': cart_info
    }

def simulate_cart_failure(event_id, event_name, reason="Simulation test - tickets sold out too quickly"):
    """Simulate a failed cart operation"""
    logger.info(f"Simulating failed cart for: {event_name}")
    
    # Create a notification message
    message = (
        f"❌ **[SIMULATION] Carting Failed** ❌\n"
        f"Event: {event_name}\n"
        f"Reason: {reason}\n\n"
        f"*This is a simulated carting failure for testing purposes.*"
    )
    
    # Send notification
    send_discord_notification(message)
    
    return {
        'success': False,
        'eventId': event_id,
        'status': 'failed',
        'reason': reason
    }

def simulate_ticket_availability(event_id, event_name):
    """Simulate ticket availability detection"""
    logger.info(f"Simulating ticket availability for: {event_name}")
    
    # Create a notification message
    message = (
        f"🔍 **[SIMULATION] Status Change** for {event_name}\n"
        f"⚡ Not Yet Available → 🎫 TICKETS AVAILABLE! 🎫\n"
        f"[Check Tickets](https://choli.ticketera.com/)\n\n"
        f"*This is a simulated availability update for testing purposes.*"
    )
    
    # Send notification
    send_discord_notification(message, use_mentions=True)
    
    return {
        'success': True,
        'eventId': event_id,
        'status': 'available'
    }

def run_simulation():
    """Run simulation for testing"""
    logger.info("Starting Bad Bunny ticket cart automation simulation")
    
    # Send initial notification
    send_discord_notification("🛒 **Cart Automation Debug Test Starting** 🛒\nTesting carting functionality...")
    
    # Choose a random event to simulate
    month = random.choice(list(BAD_BUNNY_DATES.keys()))
    day = random.choice(BAD_BUNNY_DATES[month])
    event_id = f"{month}-{day}"
    event_name = f"Bad Bunny - {month.capitalize()} {day}, 2025"
    
    # Simulate ticket availability
    logger.info(f"Selected event for simulation: {event_name}")
    time.sleep(2)
    simulate_ticket_availability(event_id, event_name)
    
    # Wait a few seconds
    time.sleep(5)
    
    # Simulate carting attempt (80% success rate)
    if random.random() < 0.8:
        simulate_cart_success(event_id, event_name)
    else:
        reasons = [
            "Test: Tickets sold out during checkout process",
            "Test: Unexpected error in checkout flow",
            "Test: Ticket page did not load correctly",
            "Test: Cart session expired"
        ]
        simulate_cart_failure(event_id, event_name, random.choice(reasons))
    
    # Summary
    logger.info("Simulation completed")
    send_discord_notification("✅ **Cart Automation Debug Test Completed** ✅\nCheck the above messages to see simulated notifications.")

if __name__ == "__main__":
    run_simulation()
