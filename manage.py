#!/usr/bin/env python
import os
import sys
from pathlib import Path
import environ

if __name__ == '__main__':
    # Only load .env in local dev (when using .dev settings)
    if os.getenv('DJANGO_SETTINGS_MODULE', '').endswith('.dev'):
        BASE_DIR = Path(__file__).resolve().parent
        env = environ.Env()
        env.read_env(BASE_DIR / '.env')

    # Default to dev settings locally
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings.dev')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc

    execute_from_command_line(sys.argv)