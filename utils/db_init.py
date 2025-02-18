"""Database initialization script"""

import os
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def verify_table_schema(cursor, table_name):
    """Verify table schema and log column information"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    column_types = [col[2] for col in columns]
    logger.info(f"Table {table_name} schema:")
    for name, type_ in zip(column_names, column_types):
        logger.info(f"  - Column: {name} (Type: {type_})")
    return column_names

def init_database(db_path: str = "bot.db", force_recreate: bool = False):
    """Initialize database with required tables"""
    logger.info(f"Initializing database at {db_path}")
    
    # Drop existing database if force_recreate is True
    if force_recreate and os.path.exists(db_path):
        logger.info(f"Dropping existing database at {db_path}")
        os.remove(db_path)
        logger.info(f"Database file exists after removal: {os.path.exists(db_path)}")
    
    conn = sqlite3.connect(db_path)
    try:
        c = conn.cursor()
        
        # Drop existing tables if force_recreate is True
        if force_recreate:
            logger.info("Dropping existing tables")
            tables = ['platform_stats', 'posts', 'comments', 'personality_stats']
            for table in tables:
                c.execute(f"DROP TABLE IF EXISTS {table}")
                logger.info(f"Dropped table: {table}")
        
        # Log initial database state
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = c.fetchall()
        logger.info(f"Existing tables before creation: {[t[0] for t in existing_tables]}")
        
        # Create platform stats table
        c.execute('''CREATE TABLE IF NOT EXISTS platform_stats
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     platform TEXT UNIQUE,
                     total_interactions INTEGER DEFAULT 0,
                     total_posts INTEGER DEFAULT 0,
                     total_comments INTEGER DEFAULT 0,
                     last_activity DATETIME)''')
        logger.info("Created platform_stats table")
        verify_table_schema(c, 'platform_stats')
        
        # Create posts table
        c.execute('''CREATE TABLE IF NOT EXISTS posts
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     platform TEXT,
                     post_id TEXT UNIQUE,
                     username TEXT,
                     subreddit TEXT,
                     post_title TEXT,
                     post_content TEXT,
                     personality_id TEXT,
                     personality_context TEXT,
                     timestamp DATETIME,
                     UNIQUE(platform, post_id))''')
        logger.info("Created posts table")
        verify_table_schema(c, 'posts')
        
        # Create comments table
        c.execute('''CREATE TABLE IF NOT EXISTS comments
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     platform TEXT,
                     username TEXT,
                     comment_id TEXT UNIQUE,
                     post_id TEXT,
                     comment_content TEXT,
                     personality_id TEXT,
                     personality_context TEXT,
                     timestamp DATETIME,
                     FOREIGN KEY(post_id) REFERENCES posts(post_id),
                     UNIQUE(platform, comment_id))''')
        logger.info("Created comments table")
        verify_table_schema(c, 'comments')
        
        # Create personality stats table
        c.execute('''CREATE TABLE IF NOT EXISTS personality_stats
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     personality_id TEXT,
                     platform TEXT,
                     total_posts INTEGER DEFAULT 0,
                     total_comments INTEGER DEFAULT 0,
                     last_activity DATETIME,
                     UNIQUE(personality_id, platform))''')
        logger.info("Created personality_stats table")
        verify_table_schema(c, 'personality_stats')
        
        # Initialize platform stats if empty
        c.execute('SELECT COUNT(*) FROM platform_stats')
        if c.fetchone()[0] == 0:
            platforms = ['reddit', 'twitter', 'discord', 'telegram']
            now = datetime.now()
            for platform in platforms:
                c.execute('''INSERT OR IGNORE INTO platform_stats 
                            (platform, total_interactions, total_posts, total_comments, last_activity)
                            VALUES (?, 0, 0, 0, ?)''',
                         (platform, now))
                logger.info(f"Initialized stats for platform: {platform}")
        
        # Verify final database state
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        final_tables = c.fetchall()
        logger.info(f"Final tables after creation: {[t[0] for t in final_tables]}")
        
        conn.commit()
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    init_database(force_recreate=True) 