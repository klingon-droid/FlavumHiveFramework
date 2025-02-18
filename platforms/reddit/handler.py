import praw
import json
import os
import logging
from datetime import datetime
from typing import Dict, Optional, List

from utils.db_utils import init_db_connection
from utils.personality_manager import PersonalityManager

logger = logging.getLogger(__name__)

class RedditHandler:
    def __init__(self, personality_manager: PersonalityManager, config_path: str = "config.json"):
        logger.info("Initializing Reddit handler")
        try:
            self.config = self._load_config(config_path)
            logger.info("Config loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load config: {str(e)}")
            raise

        self.personality_manager = personality_manager
        self.db_path = os.getenv("DB_PATH", "reddit_bot.db")
        
        try:
            # Log environment variables (without sensitive data)
            env_vars = {
                'REDDIT_CLIENT_ID': bool(os.getenv('REDDIT_CLIENT_ID')),
                'REDDIT_CLIENT_SECRET': bool(os.getenv('REDDIT_CLIENT_SECRET')),
                'REDDIT_USER_AGENT': bool(os.getenv('REDDIT_USER_AGENT')),
                'REDDIT_USERNAME': bool(os.getenv('REDDIT_USERNAME')),
                'REDDIT_PASSWORD': bool(os.getenv('REDDIT_PASSWORD'))
            }
            logger.info(f"Environment variables present: {env_vars}")
            
            self.reddit = self._init_reddit()
            logger.info("Reddit API client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit API client: {str(e)}")
            raise

    def _load_config(self, config_path: str) -> Dict:
        logger.debug(f"Loading config from {config_path}")
        with open(config_path, 'r') as f:
            return json.load(f)

    def _init_reddit(self) -> praw.Reddit:
        """Initialize Reddit API client"""
        required_vars = ['REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET', 'REDDIT_USER_AGENT',
                        'REDDIT_USERNAME', 'REDDIT_PASSWORD']
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        return praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT'),
            username=os.getenv('REDDIT_USERNAME'),
            password=os.getenv('REDDIT_PASSWORD')
        )

    def process_subreddits(self):
        """Process configured subreddits"""
        logger.info("Starting subreddit processing")
        conn = init_db_connection(self.db_path)
        logger.info(f"Database connection established: {self.db_path}")
        
        try:
            c = conn.cursor()
            
            # Verify database state
            c.execute("PRAGMA table_info(posts)")
            columns = c.fetchall()
            logger.info(f"Posts table columns: {[col[1] for col in columns]}")
            
            for subreddit_name in self.config['target_subreddits']:
                logger.info(f"Processing subreddit: {subreddit_name}")
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Process new posts
                for submission in subreddit.new(limit=10):
                    # Check if post already processed
                    c.execute("SELECT id FROM posts WHERE post_id = ?", (submission.id,))
                    if not c.fetchone():
                        logger.info(f"Processing new post: {submission.id}")
                        try:
                            # Store new post
                            now = datetime.now()
                            c.execute('''INSERT INTO posts 
                                        (platform, post_id, username, subreddit, post_title, post_content, timestamp)
                                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                     ('reddit', submission.id, submission.author.name,
                                      subreddit_name, submission.title, submission.selftext, now))
                            
                            # Update platform stats
                            c.execute('''UPDATE platform_stats 
                                        SET total_interactions = total_interactions + 1,
                                            last_activity = ?
                                        WHERE platform = 'reddit' ''',
                                     (now,))
                            
                            logger.info(f"Successfully stored post {submission.id}")
                            
                            # Process comments if needed
                            if self.personality_manager.should_interact(submission.author.name, 'reddit'):
                                self._process_comments(submission, c)
                                
                        except Exception as e:
                            logger.error(f"Error processing post {submission.id}: {str(e)}")
                            continue
                    
                    conn.commit()
                    logger.debug(f"Committed changes for subreddit {subreddit_name}")
                
        except Exception as e:
            logger.error(f"Error in process_subreddits: {str(e)}")
            conn.rollback()
            logger.info("Changes rolled back due to error")
            raise
        finally:
            conn.close()
            logger.info("Database connection closed")

    def _process_comments(self, submission: praw.models.Submission, cursor) -> None:
        """Process comments for a submission"""
        # Get a personality for this interaction
        personality = self.personality_manager.get_random_personality('reddit')
        if not personality:
            return

        # Generate and post comment
        prompt = self.personality_manager.get_personality_prompt(personality, 'reddit', is_reply=True)
        comment_text = self._generate_comment(submission.title + "\n" + submission.selftext, prompt)
        
        try:
            comment = submission.reply(comment_text)
            
            # Store comment in database
            now = datetime.now()
            cursor.execute('''INSERT INTO comments 
                            (platform, username, comment_id, post_id, comment_content, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?)''',
                         ('reddit', personality['name'], comment.id,
                          submission.id, comment_text, now))
            
            # Update platform stats
            cursor.execute('''UPDATE platform_stats 
                            SET total_interactions = total_interactions + 1,
                                last_activity = ?
                            WHERE platform = 'reddit' ''',
                         (now,))
            
        except Exception as e:
            logger.error(f"Error posting comment: {str(e)}")

    def _generate_comment(self, context: str, prompt: str) -> str:
        """Generate a comment based on context and personality prompt"""
        # This is a placeholder - in a real implementation, this would use
        # a more sophisticated response generation system
        return f"Thank you for sharing! I understand your perspective and would like to add my thoughts..."

    def get_platform_stats(self) -> Dict:
        """Get platform statistics"""
        conn = init_db_connection(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute('''SELECT total_interactions, last_activity 
                        FROM platform_stats 
                        WHERE platform = 'reddit' ''')
            result = c.fetchone()
            
            if result:
                return {
                    'total_interactions': result[0],
                    'last_activity': result[1]
                }
            return {'total_interactions': 0, 'last_activity': None}
        finally:
            conn.close()

    def get_recent_activity(self, limit: int = 10) -> List[Dict]:
        """Get recent platform activity"""
        conn = init_db_connection(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute('''SELECT p.post_id, p.username, p.subreddit, p.post_title,
                               c.comment_id, c.timestamp
                        FROM posts p
                        LEFT JOIN comments c ON p.post_id = c.post_id
                        WHERE p.platform = 'reddit'
                        ORDER BY c.timestamp DESC
                        LIMIT ?''',
                     (limit,))
            
            activities = []
            for row in c.fetchall():
                activities.append({
                    'post_id': row[0],
                    'username': row[1],
                    'subreddit': row[2],
                    'title': row[3],
                    'comment_id': row[4],
                    'timestamp': row[5]
                })
            return activities
        finally:
            conn.close() 