import json
import os
import uuid
from datetime import datetime
from typing import Dict, Optional, Tuple, List

from utils.db_utils import init_db_connection

class ElizaHandler:
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)['platforms']['eliza']
        self.active_sessions = {}
        self.db_path = os.getenv("DB_PATH", "reddit_bot.db")

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r') as f:
            return json.load(f)

    def create_session(self, user_id: str, personality_type: Optional[str] = None) -> str:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        personality = personality_type or self.config['personality_mapping']['default']
        
        conn = init_db_connection(self.db_path)
        c = conn.cursor()
        
        try:
            now = datetime.now()
            c.execute('''INSERT INTO eliza_sessions 
                        (session_id, user_id, personality_type, start_time, last_activity)
                        VALUES (?, ?, ?, ?, ?)''',
                     (session_id, user_id, personality, now, now))
            
            # Get initial message based on personality
            initial_msg = self.config['personality_mapping'][personality]['initial_message']
            
            c.execute('''INSERT INTO eliza_messages
                        (session_id, message_type, content, timestamp)
                        VALUES (?, ?, ?, ?)''',
                     (session_id, 'bot', initial_msg, now))
            
            conn.commit()
            return session_id
        finally:
            conn.close()

    def process_message(self, session_id: str, message: str) -> Tuple[bool, Optional[str]]:
        """Process a user message and generate a response"""
        conn = init_db_connection(self.db_path)
        c = conn.cursor()
        
        try:
            # Check if session exists and is active
            c.execute('SELECT personality_type, is_active FROM eliza_sessions WHERE session_id = ?',
                     (session_id,))
            result = c.fetchone()
            
            if not result or not result[1]:
                return False, "Invalid or inactive session"
            
            personality_type = result[0]
            
            # Store user message
            now = datetime.now()
            c.execute('''INSERT INTO eliza_messages
                        (session_id, message_type, content, timestamp)
                        VALUES (?, ?, ?, ?)''',
                     (session_id, 'user', message, now))
            
            # Generate response based on personality
            response = self._generate_response(message, personality_type)
            
            # Store bot response
            c.execute('''INSERT INTO eliza_messages
                        (session_id, message_type, content, timestamp)
                        VALUES (?, ?, ?, ?)''',
                     (session_id, 'bot', response, now))
            
            # Update session activity
            c.execute('''UPDATE eliza_sessions 
                        SET last_activity = ?
                        WHERE session_id = ?''',
                     (now, session_id))
            
            # Update platform stats
            c.execute('''UPDATE platform_stats 
                        SET total_interactions = total_interactions + 1,
                            last_activity = ?
                        WHERE platform = 'eliza' ''',
                     (now,))
            
            conn.commit()
            return True, response
        finally:
            conn.close()

    def _generate_response(self, message: str, personality_type: str) -> str:
        """Generate a response based on the message and personality type"""
        # This is a placeholder - in a real implementation, this would use
        # a more sophisticated response generation system
        return f"I understand you're saying: {message}. Let me help you with that..."

    def get_session_history(self, session_id: str) -> List[Dict]:
        """Get message history for a session"""
        conn = init_db_connection(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute('''SELECT message_type, content, timestamp
                        FROM eliza_messages
                        WHERE session_id = ?
                        ORDER BY timestamp ASC''',
                     (session_id,))
            
            history = []
            for row in c.fetchall():
                history.append({
                    'type': row[0],
                    'content': row[1],
                    'timestamp': row[2]
                })
            return history
        finally:
            conn.close()

    def end_session(self, session_id: str) -> bool:
        """End a chat session"""
        conn = init_db_connection(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute('''UPDATE eliza_sessions 
                        SET is_active = 0,
                            last_activity = ?
                        WHERE session_id = ?''',
                     (datetime.now(), session_id))
            
            conn.commit()
            return True
        finally:
            conn.close()

    def get_platform_stats(self) -> Dict:
        """Get platform statistics"""
        conn = init_db_connection(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute('''SELECT total_interactions, last_activity 
                        FROM platform_stats 
                        WHERE platform = 'eliza' ''')
            result = c.fetchone()
            
            if result:
                return {
                    'total_interactions': result[0],
                    'last_activity': result[1]
                }
            return {'total_interactions': 0, 'last_activity': None}
        finally:
            conn.close()

    def cleanup_inactive_sessions(self, timeout_seconds: int = None) -> int:
        """Clean up inactive sessions"""
        if timeout_seconds is None:
            timeout_seconds = self.config['session_timeout']
            
        conn = init_db_connection(self.db_path)
        c = conn.cursor()
        
        try:
            now = datetime.now()
            c.execute('''UPDATE eliza_sessions 
                        SET is_active = 0
                        WHERE is_active = 1 
                        AND datetime(last_activity) <= datetime(?)''',
                     (now,))
            count = c.rowcount
            conn.commit()
            return count
        finally:
            conn.close() 