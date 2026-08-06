import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

SQLALCHEMY_DATABASE_URI = os.getenv(
    "DATABASE_URL", f"sqlite:///{BASE_DIR / 'gremlin.db'}"
)
SQLALCHEMY_TRACK_MODIFICATIONS = False

UPLOAD_FOLDER = str(BASE_DIR / "static" / "uploads")
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")

API_KEYS = [
    key.strip()
    for key in os.getenv("GEMINI_API_KEYS", "").split(",")
    if key.strip()
]

MODEL = "gemini-2.5-flash"

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
