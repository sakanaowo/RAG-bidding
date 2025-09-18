import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PG_CONN = os.getenv("PG_CONN")
EMBED_MODEL = os.getenv("EMBED_MODEL")
EMBED_DIM = os.getenv("EMBED_DIM")
CHAT_MODEL = os.getenv("CHAT_MODEL")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")