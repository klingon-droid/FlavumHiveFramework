"""Reddit Platform Handler"""

import praw
import json
import os
import logging
import sqlite3
from datetime import datetime
from typing import Dict, Optional, List
import threading
from contextlib import contextmanager

from utils.db_utils import init_db_connection
from utils.personality_manager import PersonalityManager
from utils.openai_utils import get_openai_response
from utils.post import generate_post_content, generate_title, get_appropriate_flair

logger = logging.getLogger(__name__)

class RedditHandler:
    def __init__(self, personality_manager: PersonalityManager, config_path: str = "config.json"):
        self._thread_local = threading.local()
        self._init_thread_state()
        thread_id = threading.get_ident()
        logging.info(f"[Thread Lifecycle] Handler initialized in thread {thread_id}")
        
        try:
            logger.info(f"Current working directory: {os.getcwd()}")
            logger.info(f"Using config path: {os.path.abspath(config_path)}")
            
            self.config = self._load_config(config_path)['platforms']['reddit']
            if not self.config['enabled']:
                raise ValueError("Reddit platform is not enabled in config")
            logger.info("Config loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load config: {str(e)}", exc_info=True)
            raise

        self.personality_manager = personality_manager
        self.db_path = os.getenv("DB_PATH", "bot.db")
        logger.info(f"Using database path in handler: {self.db_path}")
        
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
            
            # Test Reddit connection
            username = self.reddit.user.me().name
            logger.info(f"Successfully authenticated as: {username}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Reddit API client: {str(e)}", exc_info=True)
            raise

    def _init_thread_state(self):
        """Initialize thread-local state"""
        self._thread_local.connection_thread_id = None
        self._thread_local.connection_active = False
        self._thread_local.transaction_count = 0
        self._thread_local.last_transaction_id = 0

    @property
    def next_transaction_id(self):
        """Get next transaction ID for this thread"""
        if not hasattr(self._thread_local, 'last_transaction_id'):
            self._thread_local.last_transaction_id = 0
        self._thread_local.last_transaction_id += 1
        return self._thread_local.last_transaction_id

    @property
    def db_conn(self):
        """Get thread-local database connection"""
        thread_id = threading.get_ident()
        if not hasattr(self._thread_local, 'db_conn'):
            logging.info(f"[Thread State] Creating new connection in thread {thread_id} (No previous connection)")
            self._init_thread_state()
            self._thread_local.db_conn = init_db_connection(self.db_path)
            self._thread_local.connection_thread_id = thread_id
            self._thread_local.connection_active = True
            logging.info(f"[Thread State] Connection established in thread {thread_id} (State: Active=True, Transactions=0)")
        elif self._thread_local.connection_thread_id != thread_id:
            old_thread = self._thread_local.connection_thread_id
            logging.info(f"[Thread Transition] Moving connection from thread {old_thread} to {thread_id}")
            logging.info(f"[Thread State] Old connection state - Active={self._thread_local.connection_active}, Transactions={self._thread_local.transaction_count}")
            self._cleanup_thread()
            self._init_thread_state()
            self._thread_local.db_conn = init_db_connection(self.db_path)
            self._thread_local.connection_thread_id = thread_id
            self._thread_local.connection_active = True
            logging.info(f"[Thread State] New connection established in thread {thread_id}")
        return self._thread_local.db_conn

    @property
    def db_cursor(self):
        """Get thread-local database cursor"""
        if not hasattr(self._thread_local, 'db_cursor'):
            self._thread_local.db_cursor = self.db_conn.cursor()
        return self._thread_local.db_cursor

    @contextmanager
    def get_db_connection(self):
        """Context manager for database operations"""
        thread_id = threading.get_ident()
        transaction_id = self.next_transaction_id
        
        # Ensure thread state is initialized
        if not hasattr(self._thread_local, 'transaction_count'):
            self._init_thread_state()
        
        self._thread_local.transaction_count += 1
        logging.info(f"[Transaction] Starting transaction {transaction_id} in thread {thread_id} (Total active: {self._thread_local.transaction_count})")
        
        try:
            conn = self.db_conn
            cursor = self.db_cursor
            logging.info(f"[Connection State] Using connection in thread {thread_id} (Active={self._thread_local.connection_active}, Transactions={self._thread_local.transaction_count})")
            yield conn, cursor
        except Exception as e:
            logging.error(f"[Transaction Error] Error in transaction {transaction_id} in thread {thread_id}: {str(e)}")
            if hasattr(self._thread_local, 'db_conn'):
                self._thread_local.db_conn.rollback()
                logging.info(f"[Transaction] Rolled back transaction {transaction_id} in thread {thread_id}")
            raise
        else:
            if hasattr(self._thread_local, 'db_conn'):
                self._thread_local.db_conn.commit()
                logging.info(f"[Transaction] Committed transaction {transaction_id} in thread {thread_id}")
        finally:
            self._thread_local.transaction_count = max(0, self._thread_local.transaction_count - 1)
            logging.info(f"[Transaction] Completed transaction {transaction_id} in thread {thread_id} (Remaining active: {self._thread_local.transaction_count})")
            
            # Consider cleanup if no active transactions
            if self._thread_local.transaction_count == 0:
                logging.info(f"[Connection State] No active transactions in thread {thread_id}, marking for cleanup")
                self._thread_local.connection_active = False

    def _cleanup_thread(self):
        """Clean up thread-local resources"""
        thread_id = threading.get_ident()
        transaction_count = getattr(self._thread_local, 'transaction_count', 0)
        connection_active = getattr(self._thread_local, 'connection_active', False)
        
        logging.info(f"[Cleanup] Starting cleanup for thread {thread_id} (Active={connection_active}, Transactions={transaction_count})")
        
        if hasattr(self._thread_local, 'db_cursor'):
            logging.info(f"[Cleanup] Closing cursor in thread {thread_id}")
            self._thread_local.db_cursor.close()
            delattr(self._thread_local, 'db_cursor')
        
        if hasattr(self._thread_local, 'db_conn'):
            if transaction_count > 0:
                logging.warning(f"[Cleanup] Cleaning up connection with {transaction_count} active transactions in thread {thread_id}")
            logging.info(f"[Cleanup] Closing connection in thread {thread_id}")
            self._thread_local.db_conn.close()
            self._init_thread_state()
            delattr(self._thread_local, 'db_conn')

    def __del__(self):
        """Destructor to ensure cleanup"""
        if hasattr(self, '_thread_local'):
            self._cleanup_thread()

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

    def process_subreddits(self, commenters_config: Dict = None):
        """Process configured subreddits"""
        thread_id = threading.get_ident()
        logging.info(f"[Process] Starting subreddit processing in thread {thread_id}")
        
        try:
            with self.get_db_connection() as (conn, cursor):
                # Test connection
                cursor.execute("SELECT COUNT(*) FROM posts")
                count = cursor.fetchone()[0]
                logger.info(f"Current post count in thread {thread_id}: {count}")

                for subreddit_name in self.config.get('target_subreddits', ['RedHarmonyAI']):
                    logger.info(f"Processing subreddit: {subreddit_name}")
                    
                    try:
                        subreddit = self.reddit.subreddit(subreddit_name)
                        logger.info(f"Successfully accessed subreddit: {subreddit_name}")
                        
                        # Generate and submit a new post
                        personality = self.active_personality or self.personality_manager.get_random_personality('reddit')
                        if personality:
                            logger.info(f"Generating post as personality: {personality['name']}")
                            post_content = generate_post_content(personality)
                            if post_content:
                                title = generate_title(post_content, personality)
                                flair_id = get_appropriate_flair(self.reddit, subreddit_name)
                                
                                submission = subreddit.submit(title=title, selftext=post_content, flair_id=flair_id)
                                logger.info(f"Created new post: {submission.id}")
                                
                                # Store the post
                                now = datetime.now()
                                cursor.execute('''INSERT INTO posts 
                                            (platform, post_id, username, subreddit, post_title, post_content, 
                                             personality_id, personality_context, timestamp)
                                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                         ('reddit', submission.id, submission.author.name,
                                          subreddit_name, title, post_content, personality['name'],
                                          json.dumps({'name': personality['name'], 'style': personality['style']['post']}),
                                          now))
                                
                                # Process comments for new post
                                self._process_comments(submission, cursor)
                        
                        # Process existing posts
                        for submission in subreddit.new(limit=5):
                            logger.debug(f"Processing existing submission: {submission.id}")
                            cursor.execute("SELECT id FROM posts WHERE post_id = ?", (submission.id,))
                            if not cursor.fetchone():
                                logger.info(f"Processing new post: {submission.id}")
                                try:
                                    now = datetime.now()
                                    cursor.execute('''INSERT INTO posts 
                                                (platform, post_id, username, subreddit, post_title, post_content, timestamp)
                                                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                             ('reddit', submission.id, submission.author.name,
                                              subreddit_name, submission.title, submission.selftext, now))
                                    
                                    logger.info(f"Successfully stored post {submission.id}")
                                    
                                    # Process comments for existing post
                                    self._process_comments(submission, cursor)
                                        
                                except Exception as e:
                                    logger.error(f"Error processing post {submission.id}: {str(e)}", exc_info=True)
                                    continue
                            
                            conn.commit()
                            logger.debug(f"Committed changes for subreddit {subreddit_name}")
                        
                    except Exception as e:
                        logger.error(f"Error processing subreddit {subreddit_name}: {str(e)}", exc_info=True)
                        continue
                    
        except Exception as e:
            logging.error(f"[Process Error] Failed in thread {thread_id}: {str(e)}")
            raise
        finally:
            if hasattr(self._thread_local, 'connection_active'):
                logging.info(f"[Process] Ending subreddit processing in thread {thread_id} (Active={self._thread_local.connection_active}, Transactions={self._thread_local.transaction_count})")
            if hasattr(self._thread_local, 'connection_active') and not self._thread_local.connection_active:
                self._cleanup_thread()

    def _process_comments(self, submission: praw.models.Submission, cursor, forced_personality: Dict = None) -> None:
        """Process comments for a submission"""
        # Use specified personality, active personality, or get a random one
        personality = forced_personality or self.active_personality or self.personality_manager.get_random_personality('reddit')
        if not personality:
            return

        # Check reply probability unless using forced personality
        if not forced_personality and not self._should_reply():
            logger.info("Skipping reply based on probability settings")
            return

        # Generate and post comment
        comment_text = self.generate_comment_content(personality, submission.title, submission.selftext)
        if not comment_text:
            logger.warning("Failed to generate comment content")
            return
        
        try:
            # Add personality signature
            comment_text = f"*Insights from **{personality['name']}** - {personality['bio'][0]}*\n\n{comment_text}"
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
            
            logger.info(f"Successfully posted comment as {personality['name']}")
            
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