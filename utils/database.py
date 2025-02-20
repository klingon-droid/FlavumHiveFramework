import sqlite3

def initialize_db():
    try:
        conn = sqlite3.connect("reddit_bot.db")
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT UNIQUE,
            username TEXT,
            subreddit TEXT,
            post_title TEXT,
            timestamp DATETIME
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            comment_id TEXT UNIQUE,
            post_id TEXT,
            timestamp DATETIME
        )''')

        c.execute('''CREATE TABLE IF NOT EXISTS account_activity (
            account TEXT PRIMARY KEY,
            last_post_time DATETIME,
            last_comment_time DATETIME
        )''')

        print("++++++++++++++++++++++++++++++++++++")
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Connect Failed. Error: {e}")
        return False