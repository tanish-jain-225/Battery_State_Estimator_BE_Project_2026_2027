# gunicorn.conf.py — Gunicorn server configuration for Render production deployment
# Gunicorn automatically discovers and reads this file when launched from this directory.

# ── Worker Configuration ──────────────────────────────────────────────────────
# Single sync worker is required for Flask's in-process background training thread
# to share the same memory space as the web worker (training_status dict, esn_soc, etc.)
workers = 1

# Increase worker timeout to 300 seconds (5 minutes) to prevent Gunicorn from
# killing the process during ESN model retraining, which runs as a background thread.
# Default is 30 seconds — far too short for reservoir computing on a free-tier container.
timeout = 300

# Keep-alive connections to Render's load balancer
keepalive = 5

# ── Binding ───────────────────────────────────────────────────────────────────
# Render sets the PORT environment variable automatically
import os
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# ── Logging ───────────────────────────────────────────────────────────────────
accesslog = "-"   # Log HTTP access to stdout
errorlog = "-"    # Log errors to stderr
loglevel = "info"
