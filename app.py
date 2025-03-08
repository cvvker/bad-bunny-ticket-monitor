import os
from flask import Flask, render_template, jsonify, send_from_directory
import requests
from datetime import datetime
import time
from bs4 import BeautifulSoup
import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables with defaults
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '15'))  # 15 seconds default
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/1347702022039666783/IIgJ2B6vT5aQoTjNOadVxdAviHuEsCRR8zwu4CgWAvWzcob9BJ0_5XQC-BTyVauTljR_')

# Base URLs for different venues
TICKETERA_URLS = {
    'July': {
        '12': 'https://choli.ticketera.com/checkout/67801ac67b15db4542eeed7e?underShop=67801ac67b15db4542eeee56&boxOnly=true',
        '18': 'https://choli.ticketera.com/checkout/67801c6485e7610f9b45cb54?underShop=67801c6585e7610f9b45cbce&boxOnly=true',
        '19': 'https://choli.ticketera.com/event/67801ccc52c0091cff4e33a7/67801ccd52c0091cff4e33f7'
    },
    'August': {
        '1': 'https://choli.ticketera.com/checkout/677ff055a1198f5724fc1158?underShop=677ff055a1198f5724fc11a8',
        '2': 'https://choli.ticketera.com/checkout/678276b19c10a4675dcd677b?underShop=678276b19c10a4675dcd67d4',
        '3': 'https://choli.ticketera.com/checkout/6782776b39978af92af5d38e?underShop=6782776c39978af92af5d3e7',
        '8': 'https://choli.ticketera.com/checkout/678278919c8c608b8c0ebdd2?underShop=678278929c8c608b8c0ebe2b',
        '9': 'https://choli.ticketera.com/checkout/6782790885a03cd75926079c?underShop=6782790885a03cd759260898',
        '10': 'https://choli.ticketera.com/checkout/67827a23406d3f4b30602cf9?underShop=67827a23406d3f4b30602d52',
        '15': 'https://choli.ticketera.com/checkout/67827aecbb4a8ef99dab15e8?underShop=67827aecbb4a8ef99dab1641',
        '16': 'https://choli.ticketera.com/checkout/67827b7b0cc574c721710a65?underShop=67827b7c0cc574c721710abe',
        '17': 'https://choli.ticketera.com/checkout/67827c0f96690559d725b430?underShop=67827c1096690559d725b489',
        '22': 'https://choli.ticketera.com/checkout/67827cf5564ad8f63c77f57d?underShop=67827cf5564ad8f63c77f5d8',
        '23': 'https://choli.ticketera.com/checkout/67827da9651f8bdbe0bd3f0e?underShop=67827daa651f8bdbe0bd3f67',
        '24': 'https://choli.ticketera.com/checkout/67827f39c3c7b7d600ca906a?underShop=67827f3ac3c7b7d600ca90ce',
        '29': 'https://choli.ticketera.com/checkout/67827fce1104e5b3ac99c82a?underShop=67827fce1104e5b3ac99c883',
        '30': 'https://choli.ticketera.com/checkout/678281fdc311c1c0762df8d6?underShop=678281fec311c1c0762df93d',
        '31': 'https://choli.ticketera.com/checkout/6782827df1edcc48da3866fb?underShop=6782827ef1edcc48da386754'
    },
    'September': {
        '5': 'https://choli.ticketera.com/checkout/678285d0a9936d5291154f60?underShop=678285d1a9936d5291154fb9',
        '6': 'https://choli.ticketera.com/checkout/67828834bb4a8ef99daf35b9?underShop=67828835bb4a8ef99daf361c',
        '7': 'https://choli.ticketera.com/checkout/67828abbf9dde02e3c3f059d?underShop=67828abcf9dde02e3c3f062d',
        '12': 'https://choli.ticketera.com/checkout/67828d8333f81d3543d0a47c?underShop=67828d8333f81d3543d0a575',
        '13': 'https://choli.ticketera.com/checkout/67828df40952cb5ab00ba5dd?underShop=67828df40952cb5ab00ba636',
        '14': 'https://choli.ticketera.com/checkout/67828e871104e5b3ac9ed068?underShop=67828e871104e5b3ac9ed0c1'
    }
}

# Concert dates to monitor
CONCERT_DATES = {
    'July': ['12', '18', '19'],
    'August': ['1', '2', '3', '8', '9', '10', '15', '16', '17', '22', '23', '24', '29', '30', '31'],
    'September': ['5', '6', '7', '12', '13', '14']
}

app = Flask(__name__)

# Global state
ticket_status = {}
last_check = None

def format_date(month, day):
    return f"{month} {day}, 2025"

def generate_event_url(month, day):
    # Get the specific event URL for this date
    url = TICKETERA_URLS.get(month, {}).get(str(day))
    if not url:
        return None
    return url

def send_discord_notification(message, title, description, url=None, is_urgent=False):
    try:
        embed = {
            "title": title,
            "description": (
                f"{description}\n\n"
                f"🎯 Direct Link: [Click here to check tickets]({url})\n\n"
                f"⚡ Act Fast: Tickets may sell out quickly!\n"
                f"🕒 Found at: {datetime.now().strftime('%I:%M:%S %p')}"
            ),
            "color": 16711680 if is_urgent else 5814783,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if url:
            embed["url"] = url

        payload = {
            "content": "@everyone " + message if is_urgent else message,
            "embeds": [embed]
        }

        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        
        if is_urgent:
            # Send a second notification for critical updates
            time.sleep(1)
            payload["content"] = "🚨 URGENT REMINDER: " + message
            requests.post(DISCORD_WEBHOOK_URL, json=payload)
            
        logger.info(f"Discord notification sent: {title}")
        
    except Exception as e:
        logger.error(f"Error sending Discord notification: {e}")

def check_ticketera_availability(event_url):
    try:
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = session.get(event_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for ticket availability indicators
        sold_out_indicators = [
            'sold out', 'agotado', 'no tickets available', 'no hay boletos',
            'evento finalizado', 'event ended'
        ]
        
        # Get visible text content
        page_text = ' '.join([
            text for text in soup.stripped_strings
            if not any(tag in str(text.parent) for tag in ['script', 'style', 'meta'])
        ]).lower()
        
        # Look for ticket-related elements
        ticket_elements = soup.find_all(['div', 'span', 'button'], string=lambda s: s and any(word in s.lower() for word in ['ticket', 'boleto', 'price', 'precio']))
        
        if any(indicator in page_text for indicator in sold_out_indicators):
            return "❌ Not Available"
        elif ticket_elements:
            # Check if any of the ticket elements indicate availability
            ticket_text = ' '.join(elem.get_text().lower() for elem in ticket_elements)
            if any(word in ticket_text for word in ['available', 'buy', 'comprar', 'add to cart', 'añadir']):
                return "✅ TICKETS AVAILABLE!"
            else:
                return "⚠️ CHECK NOW - Possible Tickets"
        else:
            return "⚡ Not Yet Available"
            
    except requests.RequestException as e:
        logger.error(f"Error checking Ticketera: {e}")
        return "⚡ Error checking availability"
    except Exception as e:
        logger.error(f"Unexpected error checking tickets: {e}")
        return "⚡ Error checking availability"

def update_ticket_status():
    global ticket_status, last_check
    
    try:
        current_status = {}
        
        for month, days in CONCERT_DATES.items():
            for day in days:
                event_url = generate_event_url(month, day)
                if not event_url:
                    logger.error(f"No URL found for {month} {day}")
                    continue
                    
                status = check_ticketera_availability(event_url)
                date = format_date(month, day)
                
                event_id = f"{month.lower()}-{day}"
                previous_status = ticket_status.get(event_id, {}).get('status')
                
                current_status[event_id] = {
                    'name': f"Bad Bunny - {date}",
                    'date': date,
                    'status': status,
                    'url': event_url,
                    'lastChecked': datetime.now().strftime('%I:%M:%S %p')
                }
                
                # Send notification if status changed
                if previous_status and previous_status != status:
                    is_urgent = "AVAILABLE" in status or "CHECK NOW" in status
                    send_discord_notification(
                        f"Status changed for {date}!",
                        f"Ticket Status Update - {date}",
                        f"Previous status: {previous_status}\nNew status: {status}",
                        event_url,
                        is_urgent
                    )
        
        ticket_status = current_status
        last_check = datetime.now()
        logger.info("Ticket status updated successfully")
        
    except Exception as e:
        logger.error(f"Error updating ticket status: {e}")
        return {"error": str(e)}

@app.route('/api/tickets')
def get_tickets():
    try:
        global last_check
        
        # Update status if it's been more than CHECK_INTERVAL seconds
        if not last_check or (datetime.now() - last_check).total_seconds() >= CHECK_INTERVAL:
            update_ticket_status()
        
        return jsonify(ticket_status)
    except Exception as e:
        logger.error(f"Error in /api/tickets endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # Do initial check
    update_ticket_status()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
