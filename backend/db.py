import sqlite3
from flask import g
from backend.config import Config

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(Config.DATABASE_NAME)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(error=None):
    if "db" in g:
        g.db.close()
