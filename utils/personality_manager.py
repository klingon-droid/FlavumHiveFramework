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
                "target_subreddits": ["RedHarmonyAI"],
                "rate_limits": {
                    "posts_per_day": 20,
                    "comments_per_day": 100,
                    "posts_per_hour": 2,
                    "comments_per_hour": 5,
                    "min_delay_between_actions": 10,
                    "max_delay_between_actions": 20
                },
                "interaction_settings": {
                    "interaction_probability": 0.7,
                    "max_conversation_depth": 3,
                    "max_posts_per_thread": 5
                }
            }

    def load_personalities(self):
        """Load all personality profiles"""
        personality_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'personalities')
        for filename in os.listdir(personality_dir):
            if filename.endswith('.json'):
                with open(os.path.join(personality_dir, filename), 'r') as f:
                    personality = json.load(f)
                    # Update platform-specific settings
                    if 'platform_settings' in personality:
                        if 'reddit' in personality['platform_settings']:
                            personality['platform_settings']['reddit']['subreddits'] = self.config['target_subreddits']
                    self.personalities[personality['name']] = personality

    def get_random_personality(self, platform: str = 'reddit') -> Dict:
        """Get a random personality that supports the specified platform"""
        valid_personalities = [
            p for p in self.personalities.values()
            if 'platform_settings' in p and platform in p['platform_settings']
        ]
        return random.choice(valid_personalities) if valid_personalities else None

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
        interaction_prob = self.config['interaction_settings']['interaction_probability']
        if platform in self.config.get('platform_rate_limits', {}):
            # Adjust probability based on platform settings
            platform_limits = self.config['platform_rate_limits'][platform]
            if 'interaction_probability' in platform_limits:
                interaction_prob = platform_limits['interaction_probability']
        return random.random() < interaction_prob

    def get_platform_settings(self, platform: str) -> Dict:
        """Get platform-specific settings"""
        return self.config.get('platform_rate_limits', {}).get(platform, {})

    def get_subreddits(self) -> List[str]:
        """Get configured target subreddits"""
        return self.config['target_subreddits']

    def get_rate_limits(self) -> Dict:
        """Get configured rate limits"""
        return self.config['rate_limits']

    def get_interaction_settings(self) -> Dict:
        """Get configured interaction settings"""
        return self.config['interaction_settings'] 