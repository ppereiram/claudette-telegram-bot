import os
import logging
from dotenv import load_dotenv

load_dotenv()

# LOGGING
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("claudette")

# --- KEYS ---
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY')
ELEVENLABS_VOICE_ID = os.environ.get('ELEVENLABS_VOICE_ID', 'JBFqnCBsd6RMkjVDRZzb')
OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY')
OWNER_CHAT_ID = os.environ.get('OWNER_CHAT_ID')
DATABASE_URL = os.environ.get('DATABASE_URL')

# --- CONSTANTES ---
DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_HISTORY = 20
MAX_TOOL_ROUNDS = 5

DEFAULT_LOCATION = {"lat": 9.9281, "lng": -84.0907, "name": "San José, Costa Rica (Default)"}

NEWS_TOPICS = [
    "inteligencia artificial AI noticias",
    "geopolitica internacional noticias",
    "mercados financieros economia noticias"
]

# --- VALIDACIÓN ---
if not TELEGRAM_BOT_TOKEN or not ANTHROPIC_API_KEY:
    raise ValueError("Faltan TELEGRAM_BOT_TOKEN o ANTHROPIC_API_KEY")
