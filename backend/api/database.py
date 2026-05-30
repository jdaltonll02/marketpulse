"""
api/database.py — MongoDB connection singleton.

All collections live in the 'marketpulse' database:
    users         — registered accounts (auth.py)
    cache         — intelligence objects (server.py)

Usage:
    from api.database import get_db

    db = get_db()
    db.users.find_one({"email": "..."})
    db.cache.replace_one(...)
"""
import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

_client: MongoClient | None = None


def get_db():
    global _client
    if _client is None:
        uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        _client = MongoClient(uri)
    return _client.get_database("marketpulse")
