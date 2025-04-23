import json
import os
import random
from typing import Dict, List, Optional

class PersonalityManager:
    def __init__(self):
        self.personalities = {}
        self.config = self.load_config()
        self.load_personalities()
        self.conversation_threads = {}  # Keep track of which personality owns which thread

    def load_config(self) -> Dict:
        """Load user configuration"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}. Using defaults.")
            return {
                "global_settings": {
                    "debug_mode": False,
                    "dry_run": False,
                    "database": {
                        "path": "bot.db",
                        "backup_frequency": "daily"
                    }
                },
                "platforms": {
                    "reddit": {
                        "enabled": True,
                        "personality": {
                            "active": "crypto_researcher",
                            "settings": {
                                "add_signature": True,
                                "auto_reply": True,
                                "reply_probability": 0.7
                            }
                        },
                        "target_subreddits": ["FlavumHiveAI"],
                        "rate_limits": {
                            "posts_per_day": 10,
                            "comments_per_day": 50,
                            "posts_per_hour": 2,
                            "comments_per_hour": 5,
                            "min_delay_between_actions": 20
                        },
                        "interaction_settings": {
                            "max_conversation_depth": 4,
                            "max_posts_per_thread": 6
                        }
                    }
                }
            }

    def load_personalities(self):
        """Load all personality profiles"""
        personality_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'personalities')
        for filename in os.listdir(personality_dir):
            if filename.endswith('.json'):
                with open(os.path.join(personality_dir, filename), 'r') as f:
                    personality = json.load(f)
                    # Update platform-specific settings from config
                    if 'platform_settings' in personality:
                        for platform, settings in personality['platform_settings'].items():
                            if platform in self.config['platforms']:
                                platform_config = self.config['platforms'][platform]
                                if 'target_subreddits' in platform_config:
                                    settings['subreddits'] = platform_config['target_subreddits']
                    self.personalities[personality['name']] = personality

    def get_random_personality(self, platform: str = 'reddit') -> Dict:
        """Get a random personality that supports the specified platform"""
        valid_personalities = [
            p for p in self.personalities.values()
            if 'platform_settings' in p and platform in p['platform_settings']
        ]
        return random.choice(valid_personalities) if valid_personalities else None

    def get_personality(self, name: str) -> Optional[Dict]:
        """Get a specific personality by name"""
        return self.personalities.get(name)

    def get_personality_for_thread(self, thread_id: str, platform: str = 'reddit') -> Dict:
        """Get the personality that should respond in a thread"""
        if thread_id in self.conversation_threads:
            personality_name = self.conversation_threads[thread_id]
            personality = self.personalities[personality_name]
            if 'platform_settings' in personality and platform in personality['platform_settings']:
                return personality
        # If no personality assigned or current one doesn't support platform, assign one
        personality = self.get_random_personality(platform)
        if personality:
            self.conversation_threads[thread_id] = personality['name']
        return personality

    def get_contrasting_personality(self, current_personality: str, platform: str = 'reddit') -> Dict:
        """Get a different personality to create interaction"""
        valid_personalities = [
            p for name, p in self.personalities.items()
            if name != current_personality
            and 'platform_settings' in p
            and platform in p['platform_settings']
        ]
        return random.choice(valid_personalities) if valid_personalities else self.personalities[current_personality]

    def get_personality_prompt(self, personality: Dict, platform: str, is_reply: bool = False) -> str:
        """Generate a prompt based on personality traits and platform settings"""
        prompt = f"You are {personality['name']}. "
        prompt += " ".join(personality['bio'])
        
        # Get platform-specific style
        if platform in personality.get('platform_settings', {}):
            platform_style = personality['platform_settings'][platform].get('interaction_style', '')
            if platform_style:
                prompt += f"\n\nPlatform style ({platform}): {platform_style}"
        
        # Add general style
        prompt += "\n\nStyle: " + ", ".join(personality['style']['chat' if is_reply else 'post'])
        
        if is_reply:
            # Add example responses for tone
            examples = []
            for conv in personality['messageExamples']:
                for msg in conv:
                    if msg['user'] == personality['name']:
                        examples.append(msg['content']['text'])
            prompt += "\n\nExample responses in your style:\n" + "\n".join(examples)
        else:
            # Add example posts for tone
            prompt += "\n\nExample posts in your style:\n" + "\n".join(personality['postExamples'])

        return prompt

    def should_interact(self, post_personality: str, platform: str = 'reddit') -> bool:
        """Decide if we should create an interaction on this post"""
        if platform in self.config['platforms']:
            platform_config = self.config['platforms'][platform]
            if 'personality' in platform_config:
                return random.random() < platform_config['personality']['settings'].get('reply_probability', 0.7)
        return False

    def get_platform_settings(self, platform: str) -> Dict:
        """Get platform-specific settings"""
        return self.config['platforms'].get(platform, {})

    def get_subreddits(self) -> List[str]:
        """Get configured target subreddits"""
        reddit_config = self.config['platforms'].get('reddit', {})
        return reddit_config.get('target_subreddits', ['FlavumHiveAI'])

    def get_rate_limits(self, platform: str = 'reddit') -> Dict:
        """Get configured rate limits"""
        platform_config = self.config['platforms'].get(platform, {})
        return platform_config.get('rate_limits', {})

    def get_interaction_settings(self, platform: str = 'reddit') -> Dict:
        """Get configured interaction settings"""
        platform_config = self.config['platforms'].get(platform, {})
        return platform_config.get('interaction_settings', {}) 