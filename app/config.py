import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/ical_db",
)
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
ADSENSE_CLIENT_ID = os.environ.get("ADSENSE_CLIENT_ID", "")
ADSENSE_SLOT_ID = os.environ.get("ADSENSE_SLOT_ID", "")

CRAWL_MONTHS_AHEAD = int(os.environ.get("CRAWL_MONTHS_AHEAD", "4"))
