"""
Sentiment Tracker Module
Handles tracking and analysis of post performance and sentiment.
"""

import sqlite3
from datetime import datetime
import logging
from typing import Dict, Optional, Tuple, List
import praw
from utils.helper import get_reddit_instance

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SentimentTracker:
    def __init__(self, db_path: str = "reddit_bot.db"):
        """Initialize the sentiment tracker."""
        self.db_path = db_path
        self.reddit = get_reddit_instance()

    def fetch_post_stats(self, post_id: str) -> Optional[Dict]:
        """
        Fetch current statistics for a Reddit post.
        
        Args:
            post_id: The Reddit post ID
            
        Returns:
            Optional[Dict]: Post statistics or None if fetch failed
        """
        try:
            if not self.reddit:
                logger.error("No Reddit instance available")
                return None
                
            submission = self.reddit.submission(id=post_id)
            submission.refresh()  # Ensure we have the latest data
            
            stats = {
                'upvote_ratio': submission.upvote_ratio,
                'score': submission.score,
                'num_comments': len(submission.comments),
            }
            
            # Calculate sentiment score
            stats['sentiment_score'] = self.calculate_sentiment_score(
                stats['upvote_ratio'],
                stats['num_comments'],
                stats['score']
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error fetching post stats: {str(e)}", exc_info=True)
            return None

    def update_post_stats(self, post_id: str) -> bool:
        """
        Fetch and update statistics for a post.
        
        Args:
            post_id: The Reddit post ID
            
        Returns:
            bool: True if update was successful
        """
        try:
            # Fetch current stats
            stats = self.fetch_post_stats(post_id)
            if not stats:
                return False
                
            # Update metrics in database
            return self.update_post_metrics(post_id, stats)
            
        except Exception as e:
            logger.error(f"Error updating post stats: {str(e)}", exc_info=True)
            return False

    def initialize_post_tracking(self, post_id: str, personality: str) -> bool:
        """
        Initialize tracking for a new post.
        
        Args:
            post_id: The Reddit post ID
            personality: The personality that created the post
            
        Returns:
            bool: True if initialization was successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO post_metrics 
                (post_id, personality, upvote_ratio, score, num_comments, 
                sentiment_score, last_updated)
                VALUES (?, ?, 1.0, 0, 0, 0.0, ?)
            """, (post_id, personality, datetime.now()))
            
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error initializing post tracking: {e}")
            return False

    def update_post_metrics(self, post_id: str, metrics: Dict) -> bool:
        """
        Update metrics for a post.
        
        Args:
            post_id: The Reddit post ID
            metrics: Dictionary containing updated metrics
                    (upvote_ratio, score, num_comments, sentiment_score)
                    
        Returns:
            bool: True if update was successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE post_metrics
                SET upvote_ratio = ?,
                    score = ?,
                    num_comments = ?,
                    sentiment_score = ?,
                    last_updated = ?
                WHERE post_id = ?
            """, (
                metrics.get('upvote_ratio', 0.0),
                metrics.get('score', 0),
                metrics.get('num_comments', 0),
                metrics.get('sentiment_score', 0.0),
                datetime.now(),
                post_id
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error updating post metrics: {e}")
            return False

    def get_post_metrics(self, post_id: str) -> Optional[Dict]:
        """
        Retrieve metrics for a specific post.
        
        Args:
            post_id: The Reddit post ID
            
        Returns:
            Optional[Dict]: Post metrics or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT upvote_ratio, score, num_comments, 
                       sentiment_score, last_updated
                FROM post_metrics
                WHERE post_id = ?
            """, (post_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'upvote_ratio': result[0],
                    'score': result[1],
                    'num_comments': result[2],
                    'sentiment_score': result[3],
                    'last_updated': result[4]
                }
            return None
            
        except sqlite3.Error as e:
            logger.error(f"Error retrieving post metrics: {e}")
            return None

    def calculate_sentiment_score(self, upvote_ratio: float, 
                                num_comments: int, score: int) -> float:
        """
        Calculate a sentiment score based on post metrics.
        
        Args:
            upvote_ratio: Post's upvote ratio
            num_comments: Number of comments
            score: Post score
            
        Returns:
            float: Calculated sentiment score
        """
        # Simple weighted average of metrics
        # Can be enhanced with more sophisticated calculations
        weights = {
            'upvote_ratio': 0.5,
            'engagement': 0.3,
            'score': 0.2
        }
        
        # Normalize comment count (assuming 20+ comments is high engagement)
        normalized_comments = min(num_comments / 20.0, 1.0)
        
        # Normalize score (assuming 100+ is high)
        normalized_score = min(max(score, 0) / 100.0, 1.0)
        
        sentiment_score = (
            weights['upvote_ratio'] * upvote_ratio +
            weights['engagement'] * normalized_comments +
            weights['score'] * normalized_score
        )
        
        return round(sentiment_score, 3)

    def get_posts_needing_update(self, hours_threshold: int = 24) -> List[str]:
        """
        Get list of post IDs that need metric updates.
        
        Args:
            hours_threshold: Hours since last update to consider for refresh
            
        Returns:
            List[str]: List of post IDs needing updates
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT post_id
                FROM post_metrics
                WHERE datetime(last_updated) <= datetime('now', ?)
                AND datetime(last_updated) >= datetime('now', '-7 days')
            """, (f'-{hours_threshold} hours',))
            
            posts = cursor.fetchall()
            conn.close()
            
            return [post[0] for post in posts]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting posts for update: {e}")
            return [] 