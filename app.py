import os
from flask import Flask, render_template, jsonify
import requests
from datetime import datetime
import time
from threading import Thread
from pyngrok import ngrok

app = Flask(__name__)

# Discord webhook configuration
DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1347702022039666783/IIgJ2B6vT5aQoTjNOadVxdAviHuEsCRR8zwu4CgWAvWzcob9BJ0_5XQC-BTyVauTljR_'

def send_discord_notification(message, title, description, url=None, is_urgent=False):
    try:
        # Create the payload with the exact format requested
        current_time = datetime.now().strftime("%I:%M:%S %p")
        
        if url:
            description = (
                f"{description}\n\n"
                f"🎯 Direct Link: [Click here to check tickets]({url})\n\n"
                f"⚡ Act Fast: Tickets may sell out quickly!\n"
                f"🕒 Found at: {current_time}"
            )
        
        payload = {
            "content": "@everyone " + message if is_urgent else message,
            "embeds": [{
                "title": title,
                "description": description,
                "color": int("ff0000", 16) if is_urgent else int("00ff00", 16)
            }]
        }
        
        # Send the notification
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        print(f"Discord webhook response: {response.status_code}")
        
        if response.status_code != 204:
            print(f"Failed to send Discord notification: {response.status_code}")
            return False
            
        # Send follow-up for urgent notifications
        if is_urgent:
            time.sleep(1)
            follow_up = {
                "content": "⚠️ **REMINDER: Check the tickets NOW before they're gone!** ⚠️"
            }
            requests.post(DISCORD_WEBHOOK_URL, json=follow_up)
            
        return True
    except Exception as e:
        print(f"Error sending Discord notification: {e}")
        return False

tickets = {
    'main_page': {
        'name': 'Bad Bunny - Main Event Page',
        'date': 'N/A',
        'status': 'Checking availability...',
        'url': 'https://www.ticketera.com/events/detail/bad-bunny',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'aug_01': {
        'name': 'Bad Bunny',
        'date': 'Thursday, August 1',
        'status': 'Checking availability...',
        'url': 'https://choli.ticketera.com/checkout/677ff055a1198f5724fc1158?underShop=677ff055a1198f5724fc11a8',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'aug_02': {
        'name': 'Bad Bunny',
        'date': 'Saturday, August 2',
        'url': 'https://choli.ticketera.com/checkout/678276b19c10a4675dcd677b?underShop=678276b19c10a4675dcd67d4',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'aug_03': {
        'name': 'Bad Bunny',
        'date': 'Sunday, August 3',
        'url': 'https://choli.ticketera.com/checkout/6782776b39978af92af5d38e?underShop=6782776c39978af92af5d3e7',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'aug_08': {
        'name': 'Bad Bunny',
        'date': 'Friday, August 8',
        'url': 'https://choli.ticketera.com/checkout/678278919c8c608b8c0ebdd2?underShop=678278929c8c608b8c0ebe2b',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'aug_09': {
        'name': 'Bad Bunny',
        'date': 'Saturday, August 9',
        'url': 'https://choli.ticketera.com/checkout/6782790885a03cd75926079c?underShop=6782790885a03cd759260898',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'aug_10': {
        'name': 'Bad Bunny',
        'date': 'Sunday, August 10',
        'url': 'https://choli.ticketera.com/checkout/67827a23406d3f4b30602cf9?underShop=67827a23406d3f4b30602d52',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'aug_15': {
        'name': 'Bad Bunny',
        'date': 'Friday, August 15',
        'url': 'https://choli.ticketera.com/checkout/67827aecbb4a8ef99dab15e8?underShop=67827aecbb4a8ef99dab1641',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'aug_16': {
        'name': 'Bad Bunny',
        'date': 'Saturday, August 16',
        'url': 'https://choli.ticketera.com/checkout/67827b7b0cc574c721710a65?underShop=67827b7c0cc574c721710abe',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'aug_17': {
        'name': 'Bad Bunny',
        'date': 'Sunday, August 17',
        'url': 'https://choli.ticketera.com/checkout/67827c0f96690559d725b430?underShop=67827c1096690559d725b489',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'aug_22': {
        'name': 'Bad Bunny',
        'date': 'Friday, August 22',
        'url': 'https://choli.ticketera.com/checkout/67827cf5564ad8f63c77f57d?underShop=67827cf5564ad8f63c77f5d8',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'aug_23': {
        'name': 'Bad Bunny',
        'date': 'Saturday, August 23',
        'url': 'https://choli.ticketera.com/checkout/67827da9651f8bdbe0bd3f0e?underShop=67827daa651f8bdbe0bd3f67',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'aug_24': {
        'name': 'Bad Bunny',
        'date': 'Sunday, August 24',
        'url': 'https://choli.ticketera.com/checkout/67827f39c3c7b7d600ca906a?underShop=67827f3ac3c7b7d600ca90ce',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'aug_29': {
        'name': 'Bad Bunny',
        'date': 'Friday, August 29',
        'url': 'https://choli.ticketera.com/checkout/67827fce1104e5b3ac99c82a?underShop=67827fce1104e5b3ac99c883',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'aug_30': {
        'name': 'Bad Bunny',
        'date': 'Saturday, August 30',
        'url': 'https://choli.ticketera.com/checkout/678281fdc311c1c0762df8d6?underShop=678281fec311c1c0762df93d',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'aug_31': {
        'name': 'Bad Bunny',
        'date': 'Saturday, August 31',
        'url': 'https://choli.ticketera.com/checkout/6782827df1edcc48da3866fb?underShop=6782827ef1edcc48da386754',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'jul_12': {
        'name': 'Bad Bunny',
        'date': 'Friday, July 12',
        'url': 'https://choli.ticketera.com/checkout/67801ac67b15db4542eeed7e?underShop=67801ac67b15db4542eeee56',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'jul_18': {
        'name': 'Bad Bunny',
        'date': 'Thursday, July 18',
        'url': 'https://choli.ticketera.com/checkout/67801c6485e7610f9b45cb54?underShop=67801c6585e7610f9b45cbce',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'jul_19': {
        'name': 'Bad Bunny',
        'date': 'Friday, July 19',
        'url': 'https://choli.ticketera.com/event/67801ccc52c0091cff4e33a7/67801ccd52c0091cff4e33f7',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'sep_05': {
        'name': 'Bad Bunny',
        'date': 'Friday, September 5',
        'url': 'https://choli.ticketera.com/checkout/678285d0a9936d5291154f60?underShop=678285d1a9936d5291154fb9',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'sep_06': {
        'name': 'Bad Bunny',
        'date': 'Saturday, September 6',
        'url': 'https://choli.ticketera.com/checkout/67828834bb4a8ef99daf35b9?underShop=67828835bb4a8ef99daf361c',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'sep_07': {
        'name': 'Bad Bunny',
        'date': 'Sunday, September 7',
        'url': 'https://choli.ticketera.com/checkout/67828abbf9dde02e3c3f059d?underShop=67828abcf9dde02e3c3f062d',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'sep_12': {
        'name': 'Bad Bunny',
        'date': 'Friday, September 12',
        'url': 'https://choli.ticketera.com/checkout/67828d8333f81d3543d0a47c?underShop=67828d8333f81d3543d0a575',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'sep_13': {
        'name': 'Bad Bunny',
        'date': 'Saturday, September 13',
        'url': 'https://choli.ticketera.com/checkout/67828df40952cb5ab00ba5dd?underShop=67828df40952cb5ab00ba636',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    },
    'sep_14': {
        'name': 'Bad Bunny',
        'date': 'Sunday, September 14',
        'url': 'https://choli.ticketera.com/checkout/67828e871104e5b3ac9ed068?underShop=67828e871104e5b3ac9ed0c1',
        'status': 'Checking availability...',
        'lastChecked': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'previouslyAvailable': False
    }
}

def check_ticketera_availability(event_url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(event_url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            if 'No hay boletos disponibles' not in response.text:
                # Send urgent notification
                send_discord_notification(
                    '🚨 **URGENT: TICKETS AVAILABLE!** 🚨',
                    '🎫 Tickets Available for Bad Bunny!',
                    'Tickets found and available for purchase!',
                    url=event_url,
                    is_urgent=True
                )
                return True, '🎫 TICKETS AVAILABLE! CHECK NOW!'
            return False, 'No tickets available'
        else:
            return False, f'Error checking tickets: {response.status_code}'
    except Exception as e:
        return False, f'Error: {str(e)}'

@app.route('/api/tickets')
def get_tickets():
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for ticket_id, ticket in tickets.items():
            if ticket_id != 'main_page':  # Skip the main page
                available, status = check_ticketera_availability(ticket['url'])
                ticket['status'] = status
                ticket['lastChecked'] = current_time
                
                # Track status changes for notifications
                if available != ticket.get('previouslyAvailable', False):
                    ticket['previouslyAvailable'] = available
                    
                    if available:
                        # Send additional Discord notification for status change
                        send_discord_notification(
                            '@everyone 🔄 **Status Change: Tickets Now Available!** 🎫',
                            f'🎫 Status Change for {ticket["date"]}',
                            f'Tickets are now showing as available!\n\n' +
                            f'🎯 **Check Now**: [Click to view tickets]({ticket["url"]})\n\n' +
                            f'⏰ Changed at: {current_time}',
                            is_urgent=True
                        )
        
        return jsonify(tickets)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test-webhook')
def test_webhook():
    try:
        send_discord_notification(
            '🔔 **TEST NOTIFICATION** 🔔',
            '🎫 Test Alert',
            'Testing Discord notifications for Bad Bunny Ticket Monitor\n' +
            '⏰ Time: ' + datetime.now().strftime("%I:%M:%S %p"),
            is_urgent=True
        )
        return jsonify({"status": "success", "message": "Test webhook sent!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/test_notification')
def test_notification():
    try:
        print("Starting notification test...")
        
        # Send test notification with the exact format requested
        success = send_discord_notification(
            '🚨 **URGENT: TEST NOTIFICATION** 🚨',
            '🎫 Test: Tickets Available for Bad Bunny!',
            '[TEST ALERT] Tickets found for July 12!',
            url='https://choli.ticketera.com/checkout/67801ac67b15db4542eeed7e?underShop=67801ac67b15db4542eeee56',
            is_urgent=True
        )
        
        if not success:
            return jsonify({
                'status': 'error',
                'message': 'Failed to send Discord notification'
            }), 500
            
        # Update UI status
        tickets['jul_12']['status'] = '🎫 TEST: TICKETS AVAILABLE!'
        tickets['jul_12']['previouslyAvailable'] = True
        
        # Reset after 5 seconds
        def reset_status():
            time.sleep(5)
            tickets['jul_12']['status'] = 'Checking availability...'
            tickets['jul_12']['previouslyAvailable'] = False
        
        Thread(target=reset_status).start()
        
        return jsonify({
            'status': 'success',
            'message': 'Test notification sent successfully'
        })
        
    except Exception as e:
        print(f"Error in test_notification: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    # Check if running on development server
    if os.environ.get('PYTHONANYWHERE_SITE'):
        app.run()
    else:
        print("\nBad Bunny Ticket Monitor is running locally!")
        print("Access at: http://localhost:5000")
        app.run(debug=True)
