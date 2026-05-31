"""
Gunicorn production configuration for CareerConnect on Render.

Render free-tier gives 0.1 CPU and 512 MB RAM.
Production/paid plans can increase workers and threads.
"""
import os
import multiprocessing

# ── Binding ──────────────────────────────────────────────────────────────────
# Render always injects the PORT env var; fall back to 10000 for local testing
bind = f"0.0.0.0:{os.getenv('PORT', '10000')}"

# ── Workers ──────────────────────────────────────────────────────────────────
# Formula: (2 × CPU cores) + 1  — capped at 4 for Render's free tier
workers = min((2 * multiprocessing.cpu_count()) + 1, 4)

# ── Worker class ─────────────────────────────────────────────────────────────
# 'sync' is the default (no extra deps).
# Switch to 'gthread' or 'gevent' if you add async/IO-heavy routes.
worker_class = "sync"

# ── Threads ──────────────────────────────────────────────────────────────────
# Allows each worker to handle multiple requests concurrently
threads = 2

# ── Timeouts ─────────────────────────────────────────────────────────────────
timeout          = 120   # Kill worker if a request takes > 120 s
keepalive        = 5     # How long to wait between requests on a Keep-Alive connection
graceful_timeout = 30    # Grace period for in-flight requests on restart

# ── Logging ──────────────────────────────────────────────────────────────────
accesslog  = "-"         # stdout (Render captures it automatically)
errorlog   = "-"         # stderr
loglevel   = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s µs'

# ── Process naming ───────────────────────────────────────────────────────────
proc_name = "careerconnect"

# ── Max requests (memory leak mitigation) ────────────────────────────────────
# Restart each worker after 1000–1100 requests to prevent slow memory leaks
max_requests      = 1000
max_requests_jitter = 100    # Random jitter avoids all workers restarting at once

# ── Preload ───────────────────────────────────────────────────────────────────
# Load application code before forking workers for faster restarts and
# lower per-worker memory (COW pages are shared).
# NOTE: APScheduler's init_scheduler() is called inside app_context; workers
# that inherit the pre-loaded app must NOT start duplicate scheduler threads.
# The scheduler service handles this guard internally (only the master process
# starts the scheduler when preload_app is True).
preload_app = True
