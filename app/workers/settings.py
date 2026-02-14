import os
from dotenv import load_dotenv

load_dotenv()

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC = os.getenv("TOPIC", "moderation")
DLQ_TOPIC = os.getenv("DLQ_TOPIC", "moderation_dlq")
CONSUMER_GROUP = os.getenv("CONSUMER_GROUP", "moderation-worker")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
