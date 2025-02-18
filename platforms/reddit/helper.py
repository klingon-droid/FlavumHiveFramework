import logging
import json
import praw
import sqlite3
import os
import time
from dotenv import load_dotenv
from openai import OpenAI

from datetime import datetime, timedelta
from typing import List, Dict
from utils.constant import openAI_generate

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_accounts(filepath="accounts.json") -> List[Dict[str, str]]:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            accounts = json.load(f)
        logger.info(f"Loaded {len(accounts)} accounts.")
        return accounts
    
    except FileNotFoundError:
        logger.error(f"Accounts file not found at {filepath}.")
        return []
    except json.JSONDecodeError:
        logger.error("Error decoding JSON from accounts file.")
        return []
    
def get_reddit_instance():
    """Get authenticated Reddit instance"""
    try:
        reddit = praw.Reddit(
            username=os.getenv("REDDIT_USERNAME"),
            password=os.getenv("REDDIT_PASSWORD"),
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent=os.getenv("REDDIT_USER_AGENT")
        )
        # Test the connection
        username = reddit.user.me().name
        logger.info(f"Successfully authenticated as {username}")
        return reddit
    except Exception as e:
        logger.error(f"Error authenticating with Reddit: {str(e)}", exc_info=True)
        return None

def get_openai_response(prompt: str) -> str:
    """Get response from OpenAI with retry logic"""
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a Reddit user creating engaging content. Keep responses concise and natural."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.8
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API error (attempt {attempt + 1}/{max_retries}): {str(e)}", exc_info=True)
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise

def is_valid_subreddit(reddit: praw.Reddit, subreddit_name: str) -> bool:
    """Check if subreddit exists and is accessible"""
    try:
        subreddit = reddit.subreddit(subreddit_name)
        _ = subreddit.id  # This will fail if subreddit doesn't exist
        return True
    except Exception as e:
        logger.error(f"Error checking subreddit {subreddit_name}: {str(e)}", exc_info=True)
        return False

def get_random_post():
    db_path = "reddit_bot.db" 

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        now = datetime.now()
        start_time = now - timedelta(days=3)

        query = """
        SELECT post_id, username, timestamp
        FROM posts
        WHERE timestamp >= ?
        ORDER BY RANDOM()
        LIMIT 1;
        """

        cursor.execute(query, (start_time.strftime("%Y-%m-%d %H:%M:%S"),))
        post = cursor.fetchone()
        conn.close()

        if post:
            return {
                "post_id": post[0],
                "account_username": post[1],
                "timestamp": post[2],
            }
        else:
            print("WARNING - No eligible post found for commenting.")
            return None
        
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def save_post(post_id, username, subreddit, title):
    timestamp = datetime.now()
    conn = sqlite3.connect('reddit_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO posts (post_id, username, subreddit, post_title, timestamp) VALUES (?, ?, ?, ?, ?)", (post_id, username, subreddit, title, timestamp))
    conn.commit()
    
    print(f"Post created by {username}: {post_id} at {timestamp}")

def save_comment(username, comment_id, post_id):
    timestamp = datetime.now()
    conn = sqlite3.connect('reddit_bot.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO comments (username, comment_id, post_id, timestamp) VALUES (?, ?, ?, ?)", (username, comment_id, post_id, timestamp))
    conn.commit()
    
    print(f"Comment created by {username}: {comment_id} at {timestamp}")

def get_flairs(reddit, subreddit_name):
    try:
        subreddit = reddit.subreddit(subreddit_name)
        flair_templates = subreddit.flair.link_templates
        flairs = [
            {"flair_id": flair["id"], "flair_text": flair["text"]}
            for flair in flair_templates
        ]
        return flairs
    except Exception as e:
        print(f"Error fetching flairs for subreddit '{subreddit_name}': {e}")
        return []

def handle_rate_limit(func):
    """Decorator to handle Reddit API rate limits"""
    def wrapper(*args, **kwargs):
        max_retries = 3
        retry_delay = 60  # Start with 1 minute delay
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except praw.exceptions.RedditAPIException as e:
                if "RATELIMIT" in str(e):
                    wait_time = retry_delay * (attempt + 1)
                    logger.warning(f"Rate limited. Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    raise
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                raise
        return None
    return wrapper