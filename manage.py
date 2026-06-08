#!/usr/bin/env python
import os
import sys
from pathlib import Path

try:
    from django.core.management import execute_from_command_line
except ImportError as exc:
    raise ImportError(
        "Couldn't import Django. Are you sure it's installed and "
        "available on your PYTHONPATH environment variable? Did you "
        "forget to activate a virtual environment?"
    ) from exc


def _load_env():
    env_file = Path(__file__).resolve().parent / '.env'
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, val = line.partition('=')
            os.environ[key.strip()] = val.strip()


def main():
    _load_env()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
