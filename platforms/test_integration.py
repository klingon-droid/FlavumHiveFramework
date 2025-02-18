"""Integration test for platform implementations."""

import unittest
from platforms.reddit import RedditPlatform

class TestPlatformIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test cases."""
        self.reddit = RedditPlatform()
        
    def test_reddit_feed(self):
        """Test that we can get a Reddit feed."""
        feed = self.reddit.get_feed(subreddit='test', limit=1)
        self.assertIsInstance(feed, list)
        
    def test_platform_interface(self):
        """Test that Reddit platform implements all required methods."""
        self.assertTrue(hasattr(self.reddit, 'create_post'))
        self.assertTrue(hasattr(self.reddit, 'create_comment'))
        self.assertTrue(hasattr(self.reddit, 'get_feed'))
        
if __name__ == '__main__':
    unittest.main() 