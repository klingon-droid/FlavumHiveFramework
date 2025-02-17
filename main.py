import time
import random
import logging
from datetime import datetime, timedelta
from utils.database import initialize_db
from utils.post import generate_posts
from utils.comment import generate_comments
from utils.personality_manager import PersonalityManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    print("Starting Reddit Bot...")
    print("=" * 40)

    # Initialize components
    if initialize_db():
        print("Database connection is working!")
    else:
        print("Database connection failed. Check your setup.")
        return

    # Load personalities and configuration
    personality_manager = PersonalityManager()
    rate_limits = personality_manager.get_rate_limits()
    
    print(f"Loaded {len(personality_manager.personalities)} personalities")
    print(f"Target subreddits: {', '.join(personality_manager.get_subreddits())}")
    print(f"Rate limits: {rate_limits['posts_per_day']} posts/day, {rate_limits['comments_per_day']} comments/day")
    print("=" * 40)

    posts_created = 0
    comments_created = 0

    while posts_created < rate_limits['posts_per_day'] or comments_created < rate_limits['comments_per_day']:
        start_time = datetime.now()

        # Generate posts
        for _ in range(rate_limits['posts_per_hour']):
            if posts_created >= rate_limits['posts_per_day']:
                break
            if generate_posts():
                posts_created += 1
                # Random delay between posts
                delay = random.randint(
                    rate_limits['min_delay_between_actions'],
                    rate_limits['max_delay_between_actions']
                )
                time.sleep(delay)

        # Generate comments
        for _ in range(rate_limits['comments_per_hour']):
            if comments_created >= rate_limits['comments_per_day']:
                break
            if generate_comments():
                comments_created += 1
                # Random delay between comments
                delay = random.randint(
                    rate_limits['min_delay_between_actions'],
                    rate_limits['max_delay_between_actions']
                )
                time.sleep(delay)

        # Wait until next hour if needed
        elapsed_time = datetime.now() - start_time
        if elapsed_time < timedelta(hours=1):
            sleep_time = (timedelta(hours=1) - elapsed_time).seconds
            logger.info(f"Waiting {sleep_time} seconds until next hour")
            time.sleep(sleep_time)

    print(f"Daily task completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
