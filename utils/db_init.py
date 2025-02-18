import sqlite3
import logging
import os
from datetime import datetime

from utils.db_utils import init_db_connection

logger = logging.getLogger(__name__)

def initialize_db():
    """Initialize the database with all required tables"""
    logger.info("Starting database initialization")
    try:
        # Use the database path from environment variable or default
        db_path = os.getenv("DB_PATH", "reddit_bot.db")
        logger.info(f"Using database path: {db_path}")
        logger.info(f"Database file exists before connection: {os.path.exists(db_path)}")
        
        conn = init_db_connection(db_path)
        logger.info("Database connection established")
        
        # Log SQLite settings
        c = conn.cursor()
        c.execute("PRAGMA foreign_keys")
        logger.info(f"Foreign keys enabled: {c.fetchone()[0]}")
        c.execute("PRAGMA journal_mode")
        logger.info(f"Journal mode: {c.fetchone()[0]}")
        
        logger.debug("Creating tables...")
        
        # Start transaction explicitly
        conn.execute("BEGIN TRANSACTION")
        logger.info("Started database transaction")
        
        try:
            # Reddit-specific tables
            c.execute('''CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT DEFAULT 'reddit',
                post_id TEXT UNIQUE,
                username TEXT,
                subreddit TEXT,
                post_title TEXT,
                post_content TEXT,
                timestamp DATETIME
            )''')
            logger.debug("Created posts table")
            
            # Verify table structure
            c.execute("PRAGMA table_info(posts)")
            columns = c.fetchall()
            logger.info(f"Posts table columns: {[col[1] for col in columns]}")

            c.execute('''CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT DEFAULT 'reddit',
                username TEXT,
                comment_id TEXT UNIQUE,
                post_id TEXT,
                comment_content TEXT,
                timestamp DATETIME,
                FOREIGN KEY(post_id) REFERENCES posts(post_id)
            )''')
            logger.debug("Created comments table")

            c.execute('''CREATE TABLE IF NOT EXISTS account_activity (
                account TEXT PRIMARY KEY,
                platform TEXT,
                last_post_time DATETIME,
                last_comment_time DATETIME,
                total_posts INTEGER DEFAULT 0,
                total_comments INTEGER DEFAULT 0,
                UNIQUE(account, platform)
            )''')
            logger.debug("Created account_activity table")

            # Eliza-specific tables
            c.execute('''CREATE TABLE IF NOT EXISTS eliza_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE,
                user_id TEXT,
                personality_type TEXT,
                start_time DATETIME,
                last_activity DATETIME,
                is_active BOOLEAN DEFAULT 1
            )''')
            logger.debug("Created eliza_sessions table")

            c.execute('''CREATE TABLE IF NOT EXISTS eliza_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                message_type TEXT,
                content TEXT,
                timestamp DATETIME,
                FOREIGN KEY(session_id) REFERENCES eliza_sessions(session_id)
            )''')
            logger.debug("Created eliza_messages table")

            # Platform-agnostic tables
            c.execute('''CREATE TABLE IF NOT EXISTS personality_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                personality_name TEXT,
                interaction_count INTEGER DEFAULT 0,
                last_used DATETIME,
                UNIQUE(platform, personality_name)
            )''')
            logger.debug("Created personality_usage table")

            c.execute('''CREATE TABLE IF NOT EXISTS platform_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT UNIQUE,
                total_interactions INTEGER DEFAULT 0,
                last_activity DATETIME,
                status TEXT
            )''')
            logger.debug("Created platform_stats table")

            # Insert default platforms
            platforms = ['reddit', 'eliza']
            now = datetime.now()
            for platform in platforms:
                c.execute('''INSERT OR IGNORE INTO platform_stats 
                            (platform, total_interactions, last_activity, status)
                            VALUES (?, 0, ?, 'active')''', 
                         (platform, now))
            logger.debug("Inserted default platform stats")

            conn.commit()
            logger.info("Transaction committed successfully")
            
            # Verify tables after commit
            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = c.fetchall()
            logger.info(f"Tables after commit: {[table[0] for table in tables]}")
            
            conn.close()
            logger.info("Database connection closed")
            
            # Verify file exists after close
            logger.info(f"Database file exists after close: {os.path.exists(db_path)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during table creation: {str(e)}")
            conn.rollback()
            logger.info("Transaction rolled back due to error")
            raise
            
    except sqlite3.Error as e:
        logger.error(f"Database initialization failed. Error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {e}")
        return False

if __name__ == "__main__":
    # Configure logging for command-line usage
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    initialize_db() 