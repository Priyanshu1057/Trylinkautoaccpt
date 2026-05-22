import os
from typing import List

API_ID = os.environ.get("API_ID", "23685822")
API_HASH = os.environ.get("API_HASH", "ff0572e13ff2f63a50f6dc707e0c4c9f")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
BOT_TOKEN_2 = os.environ.get("BOT_TOKEN_2", "")  # Secondary bot — used to DM users who blocked the primary bot
ADMIN = int(os.environ.get("ADMIN", "6725874739"))
PICS = (os.environ.get("PICS", "https://i.ibb.co/1Y8Sv79v/x.jpg")).split()

LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1003054230445"))
NEW_REQ_MODE = os.environ.get("NEW_REQ_MODE", "True").lower() == "true"  # Set "True" For accept new requests

DB_URI = os.environ.get("DB_URI", "mongodb+srv://priyanshukumawat90_db_user:HtZWFwZpyQgNmdtv@cluster0.gmchzjb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
DB_NAME = os.environ.get("DB_NAME", "Cluster0")

IS_FSUB = os.environ.get("IS_FSUB", "True").lower() == "true"  # Set "True" For Enable Force Subscribe
AUTH_CHANNELS = list(map(int, os.environ.get("AUTH_CHANNEL", "-1001648037641").split())) # Add Multiple channel ids
