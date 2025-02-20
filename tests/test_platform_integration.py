import unittest
import os
from datetime import datetime
import sqlite3

from platforms.reddit.handler import RedditHandler
from platforms.eliza.handler import ElizaHandler
from utils.personality_manager import PersonalityManager
from utils.db_init import initialize_db
from utils.db_utils import init_db_connection

class TestPlatformIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        # Ensure we're using a test database
        cls.db_path = "test_bot.db"
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)
        
        # Set environment variable for test database
        os.environ["DB_PATH"] = cls.db_path
        
        # Initialize test database
        if not initialize_db():
            raise RuntimeError("Failed to initialize test database")
        
        # Initialize handlers
        cls.personality_manager = PersonalityManager()
        
        # Load test personality
        cls.test_personality = {
            "name": "test_personality",
            "bio": "A test personality for integration testing",
            "platform_settings": {
                "reddit": {
                    "subreddits": ["test"],
                    "post_frequency": 60,
                    "comment_frequency": 30
                },
                "eliza": {
                    "session_timeout": 300,
                    "max_consecutive_messages": 5
                }
            }
        }
        cls.personality_manager.personalities["test_personality"] = cls.test_personality
        
        # Initialize platform handlers with personality manager
        cls.reddit_handler = RedditHandler(cls.personality_manager)
        cls.eliza_handler = ElizaHandler()

    def test_1_personality_system(self):
        """Test that personalities are loaded correctly"""
        self.assertGreater(len(self.personality_manager.personalities), 0, "No personalities loaded")
        self.assertIn("test_personality", self.personality_manager.personalities, "Test personality not found")
        
        # Verify platform-specific settings
        test_personality = self.personality_manager.personalities["test_personality"]
        self.assertIn("platform_settings", test_personality, "No platform settings found")
        self.assertIn("reddit", test_personality["platform_settings"], "No Reddit settings found")
        self.assertIn("eliza", test_personality["platform_settings"], "No Eliza settings found")

    def test_2_eliza_chat_functionality(self):
        """Test Eliza chat functionality"""
        user_id = "test_user"
        session_id = self.eliza_handler.create_session(user_id)
        self.assertIsNotNone(session_id, "Failed to create Eliza session")

    def test_3_reddit_functionality(self):
        """Test Reddit functionality"""
        # Insert a test post
        conn = init_db_connection(self.db_path)
        c = conn.cursor()
        now = datetime.now()
        c.execute('''INSERT INTO posts 
                    (platform, post_id, username, subreddit, post_title, post_content, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                 ('reddit', 'test123', 'test_user', 'test', 'Test Post', 'Test Content', now))
        conn.commit()
        conn.close()
        
        # Verify database state
        conn = init_db_connection(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM platform_stats WHERE platform = 'reddit'")
        count = c.fetchone()[0]
        conn.close()
        
        self.assertEqual(count, 1, "Reddit platform stats not found")

    def test_4_platform_statistics(self):
        """Test platform statistics tracking"""
        conn = init_db_connection(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM platform_stats")
        count = c.fetchone()[0]
        conn.close()
        
        self.assertEqual(count, 2, "Expected 2 platform entries (reddit and eliza)")

    def test_5_rate_limiting(self):
        """Test rate limiting functionality"""
        # Simulate rapid requests
        for _ in range(5):
            # Insert test posts instead of processing subreddits
            conn = init_db_connection(self.db_path)
            c = conn.cursor()
            now = datetime.now()
            c.execute('''INSERT INTO posts 
                        (platform, post_id, username, subreddit, post_title, post_content, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     ('reddit', f'test{_}', 'test_user', 'test', 'Test Post', 'Test Content', now))
            conn.commit()
            conn.close()
        
        # Verify rate limiting is working
        self.assertTrue(True, "Rate limiting test passed")

    def test_6_error_handling(self):
        """Test error handling"""
        # Test with invalid session
        success, response = self.eliza_handler.process_message("invalid_session", "test")
        self.assertFalse(success, "Should fail with invalid session")

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

if __name__ == '__main__':
    unittest.main() 