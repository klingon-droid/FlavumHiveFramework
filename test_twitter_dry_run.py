"""Twitter Integration Dry Run Test"""

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
        logging.FileHandler('twitter_dry_run_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def test_dry_run():
    """Test Twitter integration in dry run mode"""
    logger.info("Starting Twitter dry run test...")
    
    try:
        # Initialize handlers
        personality_manager = PersonalityManager()
        # Use a test-specific database
        os.environ['DB_PATH'] = 'twitter_test.db'
        handler = TwitterHandler(personality_manager)
        
        # Get a test personality
        personality = personality_manager.get_random_personality('twitter')
        if not personality:
            logger.error("No personality available for testing")
            return False
        
        logger.info(f"Selected personality for testing: {personality['name']}")
        
        # Test 1: Generate and post a tweet
        logger.info("\nTesting tweet generation and posting...")
        tweet_content = handler.generate_tweet_content(personality)
        if not tweet_content:
            logger.error("Failed to generate tweet content")
            return False
            
        tweet_id = handler.post_tweet(tweet_content, personality)
        if tweet_id:
            logger.info(f"Tweet would be posted with content: {tweet_content}")
        
        # Test 2: Read timeline
        logger.info("\nTesting timeline reading...")
        tweets = handler.get_timeline(limit=3)
        logger.info(f"Found {len(tweets)} tweets in timeline")
        if tweets:
            logger.info("Sample tweet data:")
            for tweet in tweets[:1]:
                logger.info(f"- Username: {tweet['username']}")
                logger.info(f"- Content: {tweet['content']}")
        
        # Test 3: Generate and post a reply
        if tweets:
            logger.info("\nTesting reply generation and posting...")
            reply_content = handler.generate_reply_content(personality, tweets[0]['content'])
            if not reply_content:
                logger.error("Failed to generate reply content")
                return False
                
            tweet_id = tweets[0]['tweet_id']
            reply_id = handler.reply_to_tweet(tweet_id, reply_content, personality)
            if reply_id:
                logger.info(f"Reply would be posted to tweet {tweet_id}")
                logger.info(f"Reply content: {reply_content}")
        
        # Test 4: Check stats
        logger.info("\nTesting statistics...")
        stats = handler.get_stats()
        logger.info(f"Current statistics: {stats}")
        
        logger.info("\nDry run completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Dry run failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Ensure we're in dry run mode
    os.environ['TWITTER_DRY_RUN'] = 'true'
    
    success = test_dry_run()
    exit(0 if success else 1) 