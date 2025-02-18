"""Reddit Platform Handler"""

import praw
import json
import os
import logging
from datetime import datetime
from typing import Dict, Optional, List

from utils.db_utils import init_db_connection
from utils.personality_manager import PersonalityManager
from utils.openai_utils import get_openai_response

logger = logging.getLogger(__name__)

class RedditHandler:
    def __init__(self, personality_manager: PersonalityManager, config_path: str = "config.json"):
        logger.info("Initializing Reddit handler")
        try:
            self.config = self._load_config(config_path)['platforms']['reddit']
            if not self.config['enabled']:
                raise ValueError("Reddit platform is not enabled in config")
            logger.info("Config loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load config: {str(e)}")
            raise

        self.personality_manager = personality_manager
        self.db_path = os.getenv("DB_PATH", "bot.db")  # Use bot.db as default
        logger.info(f"Using database path: {self.db_path}")
        self.active_personality = None
        self._load_active_personality()
        
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

    def _load_active_personality(self):
        """Load the active personality from config"""
        try:
            personality_name = self.config['personality']['active']
            if not personality_name:
                logger.warning("No active personality configured in config.json")
                return
                
            self.active_personality = self.personality_manager.get_personality(personality_name)
            if self.active_personality:
                logger.info(f"Loaded active personality: {personality_name}")
            else:
                logger.error(f"Failed to load configured personality: {personality_name}")
        except Exception as e:
            logger.error(f"Error loading active personality: {str(e)}")

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
            
            for subreddit_name in self.config.get('target_subreddits', ['RedHarmonyAI']):
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
                            if self.config['personality']['settings']['auto_reply']:
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
        # Use active personality if available
        personality = self.active_personality or self.personality_manager.get_random_personality('reddit')
        if not personality:
            return

        # Check reply probability
        if not self._should_reply():
            logger.info("Skipping reply based on probability settings")
            return

        # Generate and post comment
        comment_text = self.generate_comment_content(personality, submission.title, submission.selftext)
        if not comment_text:
            logger.warning("Failed to generate comment content")
            return
        
        try:
            comment = submission.reply(comment_text)
            
            # Store comment in database
            now = datetime.now()
            cursor.execute('''INSERT INTO comments 
                            (platform, username, comment_id, post_id, comment_content, timestamp,
                             personality_id, personality_context)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                         ('reddit', personality['name'], comment.id,
                          submission.id, comment_text, now,
                          personality['name'],
                          json.dumps({'name': personality['name'], 'style': personality['style']['chat']})))
            
            # Update platform stats
            cursor.execute('''UPDATE platform_stats 
                            SET total_interactions = total_interactions + 1,
                                last_activity = ?
                            WHERE platform = 'reddit' ''',
                         (now,))
            
        except Exception as e:
            logger.error(f"Error posting comment: {str(e)}")

    def _should_reply(self) -> bool:
        """Check if we should reply based on probability settings"""
        import random
        return random.random() < self.config['personality']['settings'].get('reply_probability', 0.7)

    def generate_comment_content(self, personality: Dict, title: str, content: str) -> Optional[str]:
        """Generate a comment based on personality and context"""
        try:
            base_prompt = self.personality_manager.get_personality_prompt(personality, 'reddit', is_reply=True)
            enhanced_prompt = f"""
{base_prompt}

As {personality['name']}, engage thoughtfully with this Reddit post from your unique perspective.
Write a natural, engaging response that adds value to the discussion.

The post title: {title}
The post content: {content}

Remember:
- You are {personality['name']}, {personality['bio'][0]}
- Draw from your specific knowledge in: {', '.join(personality['knowledge'][:3])}
- Maintain your characteristic style: {', '.join(personality['style']['chat'])}
- Keep the response concise but informative
"""
            return get_openai_response(enhanced_prompt)
        except Exception as e:
            logger.error(f"Error generating comment content: {str(e)}")
            return None

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
            # Verify table schemas before query
            logger.info("Verifying table schemas before query...")
            c.execute("PRAGMA table_info(posts)")
            posts_columns = [col[1] for col in c.fetchall()]
            logger.info(f"Posts table columns: {posts_columns}")
            
            c.execute("PRAGMA table_info(comments)")
            comments_columns = [col[1] for col in c.fetchall()]
            logger.info(f"Comments table columns: {comments_columns}")
            
            # Get recent posts and their associated comments
            query = '''SELECT p.post_id, p.username, p.subreddit, p.post_title,
                             p.personality_id, p.personality_context,
                             c.comment_id, c.comment_content, c.timestamp
                      FROM posts p
                      LEFT JOIN comments c ON p.post_id = c.post_id
                      WHERE p.platform = 'reddit'
                      ORDER BY COALESCE(c.timestamp, p.timestamp) DESC
                      LIMIT ?'''
            logger.info(f"Executing query: {query}")
            
            c.execute(query, (limit,))
            rows = c.fetchall()
            logger.info(f"Query returned {len(rows)} rows")
            
            activities = []
            for row in rows:
                activity = {
                    'post_id': row[0],
                    'username': row[1],
                    'subreddit': row[2],
                    'title': row[3],
                    'personality_id': row[4],
                    'personality_context': json.loads(row[5]) if row[5] else None,
                    'comment_id': row[6],
                    'comment_content': row[7],
                    'timestamp': row[8]
                }
                activities.append(activity)
                logger.debug(f"Processed activity: {activity}")
            
            return activities
        except Exception as e:
            logger.error(f"Error in get_recent_activity: {str(e)}")
            logger.error(f"Database path: {self.db_path}")
            raise
        finally:
            conn.close() 