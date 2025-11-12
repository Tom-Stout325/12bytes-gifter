# project/settings/stout.py
from .base import *

CLIENT = "stout"


ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["stout.gifterapp.us", "localhost", "127.0.0.1", "[::1]"],
)  
    
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["https://stout.gifterapp.us", "http://localhost", "http://127.0.0.1"],
)

# Stout runs as a real tenant (no demo banner)
DEMO_MODE = env.bool("DEMO_MODE", default=False)






# Pull these from env so it works locally and on Heroku
# DEBUG = env.bool("DEBUG", default=False)

# ALLOWED_HOSTS = env.list(
#     "ALLOWED_HOSTS",
#     default=["stout.gifterapp.us", "localhost", "127.0.0.1", "[::1]"],
# )
