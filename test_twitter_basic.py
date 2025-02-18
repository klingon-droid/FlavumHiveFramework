"""Basic Twitter Integration Test"""

import os
import logging
from datetime import datetime
from platforms.twitter.handler import TwitterHandler
from utils.personality_manager import PersonalityManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('twitter_basic_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def test_login():
    """Test Twitter login"""
    logger.info("Testing Twitter login...")
    try:
        personality_manager = PersonalityManager()
        handler = TwitterHandler(personality_manager)
        logger.info("Login successful")
        return True, handler
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        return False, None

def test_tweet(handler):
    """Test posting a tweet"""
    logger.info("Testing tweet posting...")
    try:
        content = f"Test tweet from integration testing - {datetime.now().isoformat()}"
        tweet_id = handler.post_tweet(content)
        
        if tweet_id:
            logger.info(f"Successfully posted tweet: {tweet_id}")
            return True
        else:
            logger.error("Failed to post tweet")
            return False
    except Exception as e:
        logger.error(f"Error posting tweet: {str(e)}")
        return False

def test_timeline(handler):
    """Test reading timeline"""
    logger.info("Testing timeline reading...")
    try:
        tweets = handler.get_timeline(limit=5)
        if tweets:
            logger.info(f"Successfully read {len(tweets)} tweets")
            logger.info(f"Sample tweet: {tweets[0]}")
            return True, tweets[0]['tweet_id'] if tweets else None
        else:
            logger.error("No tweets found in timeline")
            return False, None
    except Exception as e:
        logger.error(f"Error reading timeline: {str(e)}")
        return False, None

def test_reply(handler, tweet_id):
    """Test replying to a tweet"""
    if not tweet_id:
        logger.error("No tweet ID provided for reply test")
        return False

    logger.info("Testing reply functionality...")
    try:
        content = f"Test reply from integration testing - {datetime.now().isoformat()}"
        reply_id = handler.reply_to_tweet(tweet_id, content)
        
        if reply_id:
            logger.info(f"Successfully posted reply: {reply_id}")
            return True
        else:
            logger.error("Failed to post reply")
            return False
    except Exception as e:
        logger.error(f"Error posting reply: {str(e)}")
        return False

def test_stats(handler):
    """Test getting statistics"""
    logger.info("Testing statistics retrieval...")
    try:
        stats = handler.get_stats()
        logger.info(f"Statistics: {stats}")
        return True
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return False

def main():
    logger.info("Starting basic Twitter integration tests...")
    
    # Test 1: Login
    success, handler = test_login()
    if not success:
        logger.error("Login test failed. Stopping tests.")
        return False
    
    # Test 2: Post Tweet
    if not test_tweet(handler):
        logger.error("Tweet posting test failed. Stopping tests.")
        return False
    
    # Test 3: Read Timeline
    success, tweet_id = test_timeline(handler)
    if not success:
        logger.error("Timeline reading test failed. Stopping tests.")
        return False
    
    # Test 4: Reply to Tweet
    if not test_reply(handler, tweet_id):
        logger.error("Reply test failed. Stopping tests.")
        return False
    
    # Test 5: Get Stats
    if not test_stats(handler):
        logger.error("Stats test failed. Stopping tests.")
        return False
    
    logger.info("All basic Twitter integration tests completed successfully!")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 