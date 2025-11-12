# project/settings/demo.py
from .base import *

CLIENT = "demo"

DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["demo.gifterapp.us", "localhost", "127.0.0.1", "[::1]"],
)
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["https://demo.gifterapp.us", "http://localhost", "http://127.0.0.1"],
)

# Demo mode flag (useful for a “Demo” pill, optional guardrails)
DEMO_MODE = env.bool("DEMO_MODE", default=True)
