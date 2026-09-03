import os

# Telegram API Credentials
API_ID = int(os.environ.get("API_ID", "123456"))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "YourBotUsername") # यहाँ अपना Bot Username डालें

# Database & Channel Settings
MONGO_URL = os.environ.get("MONGO_URL", "mongodb+srv://...")
SOURCE_CHANNEL = int(os.environ.get("SOURCE_CHANNEL", "-1004477265073"))
DB_CHANNEL = int(os.environ.get("DB_CHANNEL", "-1003882908020"))
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1003814751875"))

# Admins List (Comma Separated IDs)
ADMINS = [int(x) for x in os.environ.get("ADMINS", "123456789").split()]

# Force Subscribe Channels Default Fallbacks
FSUB_CHANNEL_1 = os.environ.get("FSUB_CHANNEL_1", "https://t.me/freestoryhubMR")
FSUB_CHANNEL_2 = os.environ.get("FSUB_CHANNEL_2", "https://t.me/freestoryhubMR")
FSUB_CHANNEL_3 = os.environ.get("FSUB_CHANNEL_3", "https://t.me/freestoryhubMR")
FSUB_CHANNEL_4 = os.environ.get("FSUB_CHANNEL_4", "https://t.me/freestoryhubMR")

# Web Server Port for Render / Koyeb
PORT = int(os.environ.get("PORT", "8080"))

# Dynamic Feature Fallback Defaults
DEFAULT_THRESHOLD = 5
PROTECT_CONTENT = os.environ.get("PROTECT_CONTENT", "True").lower() == "true"
AUTO_DELETE_ENABLED = os.environ.get("AUTO_DELETE_ENABLED", "True").lower() == "true"
AUTO_DELETE_MINUTES = int(os.environ.get("AUTO_DELETE_MINUTES", "5"))

# Shortener & Security Settings
SHORTENER_VERIFY_ENABLED = os.environ.get("SHORTENER_VERIFY_ENABLED", "True").lower() == "true"
VERIFY_EXPIRE_HOURS = int(os.environ.get("VERIFY_EXPIRE_HOURS", "12"))
SHORTENER_URL = os.environ.get("SHORTENER_URL", "gplinks.in")
SHORTENER_API = os.environ.get("SHORTENER_API", "")

# Anti-Bypass Security Credentials
SECRET_KEY = os.environ.get("SECRET_KEY", "Kaluu_Secret_Key_2026") # Secret Key

# Updates Channel
UPDATES_CHANNEL = os.environ.get("UPDATES_CHANNEL", "https://t.me/freestoryhubMR")
