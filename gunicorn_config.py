bind = "0.0.0.0:$PORT"  # Use Render's PORT environment variable
workers = 2  # Reduced for better stability
threads = 2  # Reduced for better stability
timeout = 300  # Increased timeout for long-running ticket checks
worker_class = 'gthread'  # Thread-based workers for async operations
max_requests = 0  # Disable max requests to prevent worker recycling
keepalive = 65  # Keep connections alive longer
worker_connections = 1000
forwarded_allow_ips = '*'  # Required for Render's proxy setup
accesslog = '-'  # Log to stdout for Render logging
errorlog = '-'  # Log errors to stdout for Render logging
loglevel = 'info'
capture_output = True  # Capture print statements
enable_stdio_inheritance = True  # Inherit stdio for better logging
