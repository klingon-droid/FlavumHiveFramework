import sqlite3
from datetime import datetime
from typing import Any

def adapt_datetime(dt: datetime) -> str:
    """Adapt datetime to SQL format"""
    return dt.isoformat()

def convert_datetime(val: str) -> datetime:
    """Convert SQL value to datetime"""
    try:
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None

def init_db_connection(db_path: str) -> sqlite3.Connection:
    """Initialize database connection with proper adapters"""
    sqlite3.register_adapter(datetime, adapt_datetime)
    sqlite3.register_converter("datetime", convert_datetime)
    return sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES) 