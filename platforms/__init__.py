"""
Platform-agnostic interface for social media interactions.
This module provides the base classes and interfaces that all platform implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict

class SocialPlatform(ABC):
    """Base class for all social media platform implementations."""
    
    @abstractmethod
    def create_post(self, content: str, **kwargs) -> Optional[str]:
        """Create a post on the platform.
        
        Args:
            content: The content of the post
            **kwargs: Platform-specific arguments
            
        Returns:
            Optional[str]: Post ID if successful, None otherwise
        """
        pass
    
    @abstractmethod
    def create_comment(self, post_id: str, content: str, **kwargs) -> Optional[str]:
        """Create a comment on a post.
        
        Args:
            post_id: The ID of the post to comment on
            content: The content of the comment
            **kwargs: Platform-specific arguments
            
        Returns:
            Optional[str]: Comment ID if successful, None otherwise
        """
        pass
    
    @abstractmethod
    def get_feed(self, **kwargs) -> List[Dict]:
        """Get a feed of posts from the platform.
        
        Args:
            **kwargs: Platform-specific arguments
            
        Returns:
            List[Dict]: List of posts with platform-specific data
        """
        pass
