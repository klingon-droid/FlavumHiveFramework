import unittest
from datetime import datetime, timedelta
import sqlite3
import os
from utils.feedback.performance_metrics import PerformanceMetrics

class TestPerformanceMetrics(unittest.TestCase):
    def setUp(self):
        """Set up test database and metrics instance."""
        self.test_db = "test_reddit_bot.db"
        self.metrics = PerformanceMetrics(db_path=self.test_db)
        self._create_test_data()

    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def _create_test_data(self):
        """Create test data in the database."""
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()

        # Create required tables
        cursor.execute('''CREATE TABLE IF NOT EXISTS post_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT UNIQUE NOT NULL,
            personality TEXT NOT NULL,
            upvote_ratio FLOAT DEFAULT 1.0,
            score INTEGER DEFAULT 0,
            num_comments INTEGER DEFAULT 0,
            sentiment_score FLOAT DEFAULT 0.0,
            engagement_rate FLOAT DEFAULT 0.0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS personality_performance (
            personality TEXT PRIMARY KEY,
            avg_upvote_ratio FLOAT DEFAULT 0.0,
            avg_score FLOAT DEFAULT 0.0,
            total_posts INTEGER DEFAULT 0,
            successful_posts INTEGER DEFAULT 0,
            avg_sentiment_score FLOAT DEFAULT 0.0,
            avg_engagement_rate FLOAT DEFAULT 0.0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')

        # Insert test data
        # Add post metrics for the last 10 days
        personalities = ['shawmakesmagic', 'fxnction', 'infinity_gainz']
        base_date = datetime.now()
        
        for personality in personalities:
            for days_ago in range(10):
                date = base_date - timedelta(days=days_ago)
                cursor.execute("""
                    INSERT INTO post_metrics 
                    (post_id, personality, upvote_ratio, score, sentiment_score, 
                     engagement_rate, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    f"post_{personality}_{days_ago}",
                    personality,
                    0.8 + (days_ago % 3) * 0.1,
                    100 - days_ago * 5,
                    0.7 + (days_ago % 4) * 0.1,
                    0.6 + (days_ago % 3) * 0.1,
                    date.strftime('%Y-%m-%d %H:%M:%S')
                ))

        # Add personality performance data
        for personality in personalities:
            cursor.execute("""
                INSERT INTO personality_performance
                (personality, avg_upvote_ratio, avg_score, total_posts, 
                 successful_posts, avg_sentiment_score, avg_engagement_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                personality,
                0.85,
                80.0,
                10,
                7,
                0.75,
                0.65
            ))

        conn.commit()
        conn.close()

    def test_get_performance_trends(self):
        """Test getting performance trends."""
        trends = self.metrics.get_performance_trends(days=7)
        
        # Verify basic structure
        self.assertIsInstance(trends, dict)
        self.assertTrue(len(trends) > 0)
        
        # Check data for each personality
        for personality, data in trends.items():
            self.assertIsInstance(data, list)
            self.assertTrue(len(data) > 0)
            
            # Check first data point structure
            first_point = data[0]
            self.assertIn('date', first_point)
            self.assertIn('sentiment', first_point)
            self.assertIn('score', first_point)
            self.assertIn('post_count', first_point)
            self.assertIn('engagement', first_point)

    def test_get_all_personalities(self):
        """Test getting all personalities with metrics."""
        personalities = self.metrics.get_all_personalities()
        
        # Verify basic structure
        self.assertIsInstance(personalities, list)
        self.assertTrue(len(personalities) > 0)
        
        # Check first personality data structure
        first_personality = personalities[0]
        self.assertIn('name', first_personality)
        self.assertIn('metrics', first_personality)
        
        # Check metrics structure
        metrics = first_personality['metrics']
        self.assertIn('avg_upvote_ratio', metrics)
        self.assertIn('avg_score', metrics)
        self.assertIn('total_posts', metrics)
        self.assertIn('successful_posts', metrics)
        self.assertIn('avg_sentiment', metrics)
        self.assertIn('avg_engagement', metrics)
        self.assertIn('success_rate', metrics)
        self.assertIn('last_updated', metrics)

if __name__ == '__main__':
    unittest.main() 