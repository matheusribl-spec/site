import os
import sys
from pathlib import Path

project_home = Path(__file__).resolve().parent
if str(project_home) not in sys.path:
    sys.path.insert(0, str(project_home))

os.environ.setdefault("DB_USE_SQLITE", "1")
os.environ.setdefault("SQLITE_PATH", str(project_home / "data.sqlite"))
os.environ.setdefault("SECRET_KEY", "troque-esta-chave-para-uma-segura")

from app import app as application
