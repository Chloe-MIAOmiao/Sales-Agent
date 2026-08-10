import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "sales_agent.db"
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
