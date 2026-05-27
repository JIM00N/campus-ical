import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/ical_db",
)
# Railway/Heroku/Supabase 등 매니지드 DB는 보통 prefix가 psycopg2를 의미하는
# postgresql:// 또는 postgres:// 로 주입된다. 우리는 psycopg3를 쓰므로
# 명시적으로 드라이버를 박아 둔다.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgres://"):]
elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgresql://"):]
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
ADSENSE_CLIENT_ID = os.environ.get("ADSENSE_CLIENT_ID", "")
ADSENSE_SLOT_ID = os.environ.get("ADSENSE_SLOT_ID", "")
