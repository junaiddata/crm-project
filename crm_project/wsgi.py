import os
from pathlib import Path
from django.core.wsgi import get_wsgi_application


def _load_env():
    env_file = Path(__file__).resolve().parent.parent / '.env'
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, _, val = line.partition('=')
            os.environ.setdefault(key.strip(), val.strip())


_load_env()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
application = get_wsgi_application()
