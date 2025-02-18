import os
import logging
import praw
from datetime import datetime
from platforms.reddit.handler import RedditHandler
from utils.personality_manager import PersonalityManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reddit_integration_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def test_reddit_credentials():
    """Test Reddit API credentials"""
    logger.info("Testing Reddit credentials...")
    try:
        reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT'),
            username=os.getenv('REDDIT_USERNAME'),
            password=os.getenv('REDDIT_PASSWORD')
        )
        # Verify authentication
        username = reddit.user.me().name
        logger.info(f"Successfully authenticated as: {username}")
        return True
    except Exception as e:
        logger.error(f"Reddit authentication failed: {str(e)}")
        return False

def test_reddit_read_capabilities(reddit_handler):
    """Test ability to read from Reddit"""
    logger.info("Testing Reddit read capabilities...")
    try:
        # Get configured subreddits from handler
        subreddits = reddit_handler.config['target_subreddits']
        logger.info(f"Configured subreddits: {subreddits}")
        
        for subreddit_name in subreddits[:1]:  # Test with first subreddit
            subreddit = reddit_handler.reddit.subreddit(subreddit_name)
            # Try to fetch latest posts
            posts = list(subreddit.new(limit=1))
            if posts:
                post = posts[0]
                logger.info(f"Successfully read post from r/{subreddit_name}")
                logger.info(f"Post title: {post.title}")
                return True
            else:
                logger.warning(f"No posts found in r/{subreddit_name}")
                return False
    except Exception as e:
        logger.error(f"Failed to read from Reddit: {str(e)}")
        return False

def test_reddit_write_capabilities(reddit_handler):
    """Test ability to write to Reddit (with a test comment)"""
    logger.info("Testing Reddit write capabilities...")
    try:
        # Create a test comment on our own profile to avoid spamming
        test_message = f"Test comment - {datetime.now().isoformat()}"
        user_profile = reddit_handler.reddit.user.me()
        
        # Get the most recent self-post from our profile, or create one if none exists
        for post in user_profile.submissions.new(limit=1):
            if post.author == user_profile:
                test_post = post
                break
        else:
            # Create a test post on our profile
            test_post = reddit_handler.reddit.subreddit("u_" + user_profile.name).submit(
                title=f"Test Post - {datetime.now().isoformat()}",
                selftext="This is a test post for integration testing."
            )
        
        # Add a test comment
        comment = test_post.reply(test_message)
        logger.info(f"Successfully posted test comment: {comment.id}")
        
        # Clean up - delete the test comment
        comment.delete()
        logger.info("Successfully deleted test comment")
        return True
    except Exception as e:
        logger.error(f"Failed to write to Reddit: {str(e)}")
        return False

def test_database_integration(reddit_handler):
    """Test database integration"""
    logger.info("Testing database integration...")
    try:
        # Test platform stats
        stats = reddit_handler.get_platform_stats()
        logger.info(f"Platform stats: {stats}")
        
        # Test recent activity
        activity = reddit_handler.get_recent_activity(limit=5)
        logger.info(f"Recent activity count: {len(activity)}")
        return True
    except Exception as e:
        logger.error(f"Database integration test failed: {str(e)}")
        return False

def main():
    logger.info("Starting Reddit integration tests...")
    
    # Step 1: Test credentials
    if not test_reddit_credentials():
        logger.error("Credential test failed. Stopping tests.")
        return False
    
    # Initialize handlers
    personality_manager = PersonalityManager()
    reddit_handler = RedditHandler(personality_manager)
    
    # Step 2: Test read capabilities
    if not test_reddit_read_capabilities(reddit_handler):
        logger.error("Read capabilities test failed. Stopping tests.")
        return False
    
    # Step 3: Test write capabilities
    if not test_reddit_write_capabilities(reddit_handler):
        logger.error("Write capabilities test failed. Stopping tests.")
        return False
    
    # Step 4: Test database integration
    if not test_database_integration(reddit_handler):
        logger.error("Database integration test failed. Stopping tests.")
        return False
    
    logger.info("All Reddit integration tests completed successfully!")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 