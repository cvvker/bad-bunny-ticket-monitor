# Bad Bunny Ticket Monitor

Automated ticket monitoring system for Bad Bunny concerts in 2025. Monitors Ticketera for ticket availability and sends notifications via Discord.

## Features

- Monitors multiple concert dates (July, August, September 2025)
- 15-second check interval
- Discord notifications with @everyone mentions for urgent updates
- Visual indicators and sound alerts
  - Customizable sounds (upload your own or choose from presets)
  - Toggle sound alerts on/off
- Real-time status tracking
- Countdown timer
- Auto-deployment enabled (changes deploy automatically)

## Deployment on Render

1. Fork or clone this repository
2. Create a new Web Service on Render
3. Connect your GitHub repository
4. Configure the following settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn -c gunicorn_config.py app:app`
   - Environment Variables:
     - `CHECK_INTERVAL`: 15 (seconds between checks)
     - `DISCORD_WEBHOOK_URL`: Your Discord webhook URL

The service will automatically deploy when you push changes to your repository.

## Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python app.py
   ```

## Concert Dates

### July 2025
- July 12, 18, 19

### August 2025
- August 1-3
- August 8-10
- August 15-17
- August 22-24
- August 29-31

### September 2025
- September 5-7
- September 12-14
