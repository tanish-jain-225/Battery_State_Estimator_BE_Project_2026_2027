# gunicorn.conf.py — Gunicorn server configuration for Render production deployment
# Gunicorn automatically discovers and reads this file when launched from this directory.

# ── Worker Configuration ──────────────────────────────────────────────────────
# Single sync worker is required for Flask's in-process background simulator thread
# to share the same memory space as the web worker (simulation loop, readings buffer, etc.)
workers = 1

# Increase worker timeout to 300 seconds (5 minutes) to prevent Gunicorn from
# killing the process during long operations.
timeout = 300

# Keep-alive connections to Render's load balancer
keepalive = 5

# ── Binding ───────────────────────────────────────────────────────────────────
# Render sets the PORT environment variable automatically
import os
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# ── Logging ───────────────────────────────────────────────────────────────────
accesslog = "-"   # Log HTTP access to stdout
errorlog = "-"    # Log errors to stderr
loglevel = "info"
