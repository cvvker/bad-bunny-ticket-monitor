@echo off
echo Installing Bad Bunny Ticket Monitor dependencies...
pip install -r requirements.txt

echo.
echo Installing Playwright browsers (for advanced anti-bot capabilities)...
python -m playwright install chromium

echo.
echo Installation complete! You can now run the app with:
echo python app.py
