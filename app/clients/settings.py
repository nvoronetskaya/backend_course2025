import os
from dotenv import load_dotenv

load_dotenv()

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "redpanda:29092")
TOPIC = os.getenv("TOPIC", "moderation")
API_PORT = int(os.getenv("API_PORT", "8000"))
