"""Comprehensive Twitter Integration Test"""

import os
import logging
import sqlite3
from datetime import datetime
from platforms.twitter.handler import TwitterHandler
from utils.personality_manager import PersonalityManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('twitter_comprehensive_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def verify_login():
    """Test 1: Verify Login
    - Test credentials work
    - Test session maintains"""
    logger.info("\n=== Test 1: Verifying Login ===")
    
    try:
        # Initialize handlers
        personality_manager = PersonalityManager()
        handler = TwitterHandler(personality_manager)
        
        # Test session maintenance by making two separate calls
        logger.info("Testing session persistence...")
        timeline1 = handler.get_timeline(limit=1)
        timeline2 = handler.get_timeline(limit=1)
        
        if timeline1 and timeline2:
            logger.info("✓ Login successful and session maintained")
            return True, handler
        else:
            logger.error("✗ Failed to maintain session")
            return False, None
    except Exception as e:
        logger.error(f"✗ Login verification failed: {str(e)}")
        return False, None

def test_basic_operations(handler):
    """Test 2: Basic Operations
    - Post a test tweet
    - Read timeline
    - Reply to a tweet
    - Check everything is stored in DB"""
    logger.info("\n=== Test 2: Testing Basic Operations ===")
    
    try:
        # Reset rate limit timers
        handler.last_tweet_time = None
        handler.last_reply_time = None
        
        # Post a test tweet
        logger.info("Posting test tweet...")
        test_content = f"Test tweet for comprehensive testing - {datetime.now().isoformat()}"
        tweet_id = handler.post_tweet(test_content)
        
        if not tweet_id:
            logger.error("✗ Failed to post test tweet")
            return False
        logger.info(f"✓ Successfully posted tweet: {tweet_id}")
        
        # Read timeline
        logger.info("Reading timeline...")
        tweets = handler.get_timeline(limit=5)
        if not tweets:
            logger.error("✗ Failed to read timeline")
            return False
        logger.info(f"✓ Successfully read {len(tweets)} tweets")
        
        # Reset rate limit timer for reply
        handler.last_reply_time = None
        
        # Reply to the tweet
        logger.info("Testing reply functionality...")
        reply_content = f"Test reply for comprehensive testing - {datetime.now().isoformat()}"
        reply_id = handler.reply_to_tweet(tweet_id, reply_content)
        
        if not reply_id:
            logger.error("✗ Failed to post reply")
            return False
        logger.info(f"✓ Successfully posted reply: {reply_id}")
        
        # Verify database storage
        logger.info("Verifying database storage...")
        conn = sqlite3.connect(handler.db_path)
        c = conn.cursor()
        
        # Check tweet storage
        c.execute('SELECT * FROM tweets WHERE tweet_id = ?', (tweet_id,))
        tweet_record = c.fetchone()
        
        # Check reply storage
        c.execute('SELECT * FROM tweet_interactions WHERE tweet_id = ?', (tweet_id,))
        reply_record = c.fetchone()
        
        conn.close()
        
        if tweet_record and reply_record:
            logger.info("✓ Database records verified")
            return True
        else:
            logger.error("✗ Database verification failed")
            return False
            
    except Exception as e:
        logger.error(f"✗ Basic operations test failed: {str(e)}")
        return False

def test_personality_integration(handler):
    """Test 3: Personality Integration
    - Load a personality
    - Generate a tweet
    - Post it
    - Verify it's tracked"""
    logger.info("\n=== Test 3: Testing Personality Integration ===")
    
    try:
        # Reset rate limit timers
        handler.last_tweet_time = None
        handler.last_reply_time = None
        
        # Load a personality
        logger.info("Loading test personality...")
        personality = handler.personality_manager.get_random_personality('twitter')
        if not personality:
            logger.error("✗ Failed to load personality")
            return False
        logger.info(f"✓ Successfully loaded personality: {personality['name']}")
        
        # Generate a tweet
        logger.info("Generating tweet content...")
        tweet_content = handler.generate_tweet_content(personality)
        if not tweet_content:
            logger.error("✗ Failed to generate tweet content")
            return False
        logger.info(f"✓ Successfully generated tweet content")
        
        # Post the tweet
        logger.info("Posting personality tweet...")
        tweet_id = handler.post_tweet(tweet_content, personality)
        if not tweet_id:
            logger.error("✗ Failed to post personality tweet")
            return False
        logger.info(f"✓ Successfully posted personality tweet: {tweet_id}")
        
        # Verify tracking
        logger.info("Verifying personality tracking...")
        conn = sqlite3.connect(handler.db_path)
        c = conn.cursor()
        
        # Check tweet with personality
        c.execute('''SELECT personality_id, personality_context 
                    FROM tweets 
                    WHERE tweet_id = ?''', (tweet_id,))
        tweet_record = c.fetchone()
        
        # Check personality stats
        c.execute('''SELECT total_tweets 
                    FROM personality_stats 
                    WHERE personality_id = ?''', (personality['name'],))
        stats_record = c.fetchone()
        
        conn.close()
        
        if tweet_record and tweet_record[0] == personality['name'] and stats_record:
            logger.info("✓ Personality tracking verified")
            return True
        else:
            logger.error("✗ Personality tracking verification failed")
            return False
            
    except Exception as e:
        logger.error(f"✗ Personality integration test failed: {str(e)}")
        return False

def main():
    logger.info("Starting comprehensive Twitter integration tests...")
    
    # Test 1: Verify Login
    success, handler = verify_login()
    if not success:
        logger.error("Login verification failed. Stopping tests.")
        return False
    
    # Test 2: Basic Operations
    if not test_basic_operations(handler):
        logger.error("Basic operations test failed. Stopping tests.")
        return False
    
    # Test 3: Personality Integration
    if not test_personality_integration(handler):
        logger.error("Personality integration test failed. Stopping tests.")
        return False
    
    logger.info("\n=== All comprehensive tests completed successfully! ===")
    return True

if __name__ == "__main__":
    # Set dry run mode for testing
    os.environ['TWITTER_DRY_RUN'] = 'true'
    # Use a test-specific database
    os.environ['DB_PATH'] = 'twitter_comprehensive_test.db'
    
    success = main()
    exit(0 if success else 1) 