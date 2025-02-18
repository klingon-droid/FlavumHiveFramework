"""Tweet data model and utilities"""

from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Tweet:
    """Represents a Twitter post"""
    content: str
    media_urls: Optional[List[str]] = None
    tweet_id: Optional[str] = None
    username: Optional[str] = None
    timestamp: Optional[datetime] = None
    personality_id: Optional[str] = None
    personality_context: Optional[Dict] = None  # Store personality context for the tweet
    
    MAX_TWEET_LENGTH = 280
    MAX_MEDIA_ITEMS = 4
    
    def __post_init__(self):
        """Validate tweet data after initialization"""
        if not self.content:
            raise ValueError("Tweet content cannot be empty")
        
        # Truncate content if it exceeds max length
        if len(self.content) > self.MAX_TWEET_LENGTH:
            self.content = self.content[:self.MAX_TWEET_LENGTH-3] + "..."
        
        if self.media_urls and len(self.media_urls) > self.MAX_MEDIA_ITEMS:
            raise ValueError(f"Cannot attach more than {self.MAX_MEDIA_ITEMS} media items")
        
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> dict:
        """Convert tweet to dictionary format"""
        return {
            'content': self.content,
            'media_urls': self.media_urls,
            'tweet_id': self.tweet_id,
            'username': self.username,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'personality_id': self.personality_id,
            'personality_context': self.personality_context
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Tweet':
        """Create Tweet instance from dictionary"""
        if 'timestamp' in data and data['timestamp']:
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
    
    def is_valid(self) -> bool:
        """Check if tweet data is valid"""
        try:
            self.__post_init__()
            return True
        except ValueError:
            return False
            
    def add_personality_signature(self, personality: Dict) -> None:
        """Add personality signature to tweet content"""
        if personality and 'name' in personality and 'bio' in personality:
            signature = f"\n\n- {personality['name']}, {personality['bio'][0]}"
            remaining_length = self.MAX_TWEET_LENGTH - len(signature)
            if len(self.content) > remaining_length:
                self.content = self.content[:remaining_length-3] + "..."
            self.content += signature 