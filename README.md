# Bad Bunny Ticket Monitor

Automated ticket monitoring system for Bad Bunny concerts. Get instant notifications when tickets become available!

## Features

- Real-time ticket monitoring (checks every 15 seconds)
- Discord notifications with direct ticket links
- Monitors multiple concert dates:
  - July 2025: 12, 18, 19
  - August 2025: 1-3, 8-10, 15-17, 22-24, 29-31
  - September 2025: 5-7, 12-14
- Visual and audio alerts
- Mobile-friendly interface

## Setup

1. Install requirements:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

## Discord Notifications

The monitor sends notifications through Discord with:
- @everyone mentions for urgent updates
- Direct links to ticket pages
- Timestamps and urgency indicators
- Follow-up reminders
