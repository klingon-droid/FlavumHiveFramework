import unittest
import os
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from main import MultiPlatformBot
from utils.personality_manager import PersonalityManager
from platforms.reddit.handler import RedditHandler
from platforms.eliza.handler import ElizaHandler

class TestMultiPlatformIntegration(unittest.TestCase):
    def setUp(self):
        # Create test config
        self.test_config = {
            "target_subreddits": ["TestSubreddit"],
            "platforms": {
                "reddit": True,
                "eliza": True
            },
            "platform_rate_limits": {
                "reddit": {
                    "posts_per_day": 5,
                    "comments_per_day": 10,
                    "min_delay_between_actions": 5
                },
                "eliza": {
                    "messages_per_minute": 5,
                    "session_timeout": 300
                }
            },
            "eliza_settings": {
                "personality_mapping": {
                    "default": "therapist",
                    "therapist": {
                        "initial_message": "Hello, how can I help?",
                        "style": "empathetic"
                    }
                }
            }
        }
        
        # Write test config to file
        with open("test_config.json", "w") as f:
            json.dump(self.test_config, f)
        
        # Set up test environment
        os.environ["DB_PATH"] = "test_bot.db"
        os.environ["REDDIT_CLIENT_ID"] = "test_id"
        os.environ["REDDIT_CLIENT_SECRET"] = "test_secret"
        os.environ["REDDIT_USER_AGENT"] = "test_agent"
        os.environ["REDDIT_USERNAME"] = "test_user"
        os.environ["REDDIT_PASSWORD"] = "test_pass"
        
        # Initialize bot with test config
        self.bot = MultiPlatformBot("test_config.json")

    def tearDown(self):
        # Clean up test files
        if os.path.exists("test_config.json"):
            os.remove("test_config.json")
        if os.path.exists("test_bot.db"):
            os.remove("test_bot.db")

    def test_platform_initialization(self):
        """Test that platforms are properly initialized"""
        self.assertIn("reddit", self.bot.platform_handlers)
        self.assertIn("eliza", self.bot.platform_handlers)
        
        self.assertIsInstance(self.bot.platform_handlers["reddit"], RedditHandler)
        self.assertIsInstance(self.bot.platform_handlers["eliza"], ElizaHandler)

    @patch("platforms.reddit.handler.praw.Reddit")
    def test_reddit_functionality(self, mock_reddit):
        """Test Reddit platform functionality"""
        # Mock Reddit API responses
        mock_submission = MagicMock()
        mock_submission.id = "test_post"
        mock_submission.author = MagicMock()
        mock_submission.author.name = "test_author"
        mock_submission.title = "Test Post"
        mock_submission.selftext = "Test Content"
        
        mock_subreddit = MagicMock()
        mock_subreddit.new.return_value = [mock_submission]
        
        mock_reddit_instance = MagicMock()
        mock_reddit_instance.subreddit.return_value = mock_subreddit
        
        # Configure the mock to avoid authentication
        mock_reddit.return_value = mock_reddit_instance
        mock_reddit_instance.auth = MagicMock()
        mock_reddit_instance.auth.authenticate = MagicMock()
        mock_reddit_instance.read_only = False
        
        # Test Reddit handler
        reddit_handler = self.bot.platform_handlers["reddit"]
        reddit_handler.config = self.test_config  # Use the test config
        reddit_handler.reddit = mock_reddit_instance  # Replace the real Reddit instance
        reddit_handler.process_subreddits()
        
        # Verify interactions
        mock_reddit_instance.subreddit.assert_called_with("TestSubreddit")
        mock_subreddit.new.assert_called_once()

    def test_eliza_functionality(self):
        """Test Eliza platform functionality"""
        eliza_handler = self.bot.platform_handlers["eliza"]
        
        # Test session creation
        session_id = eliza_handler.create_session("test_user")
        self.assertIsNotNone(session_id)
        
        # Test message processing
        success, response = eliza_handler.process_message(session_id, "Hello")
        self.assertTrue(success)
        self.assertIsNotNone(response)
        
        # Test session cleanup
        count = eliza_handler.cleanup_inactive_sessions(timeout_seconds=0)
        self.assertGreaterEqual(count, 0)

    def test_personality_integration(self):
        """Test personality system integration"""
        personality_manager = self.bot.personality_manager
        
        # Test personality loading for Reddit
        reddit_personality = personality_manager.get_random_personality("reddit")
        self.assertIsNotNone(reddit_personality)
        self.assertIn("platform_settings", reddit_personality)
        self.assertIn("reddit", reddit_personality["platform_settings"])
        
        # Test personality loading for Eliza
        eliza_personality = personality_manager.get_random_personality("eliza")
        self.assertIsNotNone(eliza_personality)
        self.assertIn("platform_settings", eliza_personality)
        self.assertIn("eliza", eliza_personality["platform_settings"])

    def test_platform_stats(self):
        """Test platform statistics tracking"""
        # Test Reddit stats
        reddit_stats = self.bot.platform_handlers["reddit"].get_platform_stats()
        self.assertIn("total_interactions", reddit_stats)
        self.assertIn("last_activity", reddit_stats)
        
        # Test Eliza stats
        eliza_stats = self.bot.platform_handlers["eliza"].get_platform_stats()
        self.assertIn("total_interactions", eliza_stats)
        self.assertIn("last_activity", eliza_stats)

if __name__ == "__main__":
    unittest.main() 