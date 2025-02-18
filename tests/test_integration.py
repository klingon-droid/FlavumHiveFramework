import unittest
import json
import os
from datetime import datetime
import sqlite3

from platforms.eliza.handler import ElizaHandler
from utils.personality_manager import PersonalityManager
from utils.db_utils import init_db_connection

class TestMultiPlatformIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        # Ensure we're using a test database
        self.db_path = "test_bot.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        
        # Initialize test database
        self.conn = init_db_connection(self.db_path)
        self.create_test_schema()
        
        # Initialize handlers
        self.personality_manager = PersonalityManager()
        self.eliza_handler = ElizaHandler()
        self.eliza_handler.db_path = self.db_path  # Use test database

    def create_test_schema(self):
        """Create test database schema"""
        c = self.conn.cursor()
        
        # Create all necessary tables
        c.executescript('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT DEFAULT 'reddit',
                post_id TEXT UNIQUE,
                username TEXT,
                subreddit TEXT,
                post_title TEXT,
                timestamp DATETIME
            );

            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT DEFAULT 'reddit',
                username TEXT,
                comment_id TEXT UNIQUE,
                post_id TEXT,
                timestamp DATETIME
            );

            CREATE TABLE IF NOT EXISTS account_activity (
                account TEXT PRIMARY KEY,
                platform TEXT,
                last_post_time DATETIME,
                last_comment_time DATETIME,
                UNIQUE(account, platform)
            );

            CREATE TABLE IF NOT EXISTS eliza_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE,
                user_id TEXT,
                personality_type TEXT,
                start_time DATETIME,
                last_activity DATETIME,
                is_active BOOLEAN DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS eliza_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                message_type TEXT,
                content TEXT,
                timestamp DATETIME,
                FOREIGN KEY(session_id) REFERENCES eliza_sessions(session_id)
            );

            CREATE TABLE IF NOT EXISTS personality_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT,
                personality_name TEXT,
                interaction_count INTEGER DEFAULT 0,
                last_used DATETIME,
                UNIQUE(platform, personality_name)
            );

            CREATE TABLE IF NOT EXISTS platform_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT UNIQUE,
                total_interactions INTEGER DEFAULT 0,
                last_activity DATETIME,
                status TEXT
            );
        ''')
        
        # Insert test platforms
        platforms = ['reddit', 'eliza']
        now = datetime.now()
        for platform in platforms:
            c.execute('''INSERT OR IGNORE INTO platform_stats 
                        (platform, total_interactions, last_activity, status)
                        VALUES (?, 0, ?, 'active')''', 
                     (platform, now))
        
        self.conn.commit()

    def test_personality_loading(self):
        """Test that personalities are loaded correctly"""
        personalities = self.personality_manager.personalities
        self.assertGreater(len(personalities), 0, "No personalities loaded")
        
        # Check if therapist personality exists
        self.assertIn('therapist', personalities, "Therapist personality not found")
        
        # Verify platform-specific settings
        therapist = personalities['therapist']
        self.assertIn('platform_settings', therapist, "No platform settings found")
        self.assertIn('reddit', therapist['platform_settings'], "No Reddit settings found")
        self.assertIn('eliza', therapist['platform_settings'], "No Eliza settings found")

    def test_eliza_session_creation(self):
        """Test Eliza session creation and message handling"""
        # Create a new session
        user_id = "test_user"
        session_id = self.eliza_handler.create_session(user_id)
        
        self.assertIsNotNone(session_id, "Session creation failed")
        
        # Verify session in database
        c = self.conn.cursor()
        c.execute("SELECT user_id, personality_type, is_active FROM eliza_sessions WHERE session_id = ?",
                 (session_id,))
        result = c.fetchone()
        
        self.assertIsNotNone(result, "Session not found in database")
        self.assertEqual(result[0], user_id, "User ID mismatch")
        self.assertTrue(result[2], "Session should be active")

    def test_message_processing(self):
        """Test message processing in Eliza"""
        # Create a session
        session_id = self.eliza_handler.create_session("test_user")
        
        # Send a test message
        success, response = self.eliza_handler.process_message(session_id, "Hello")
        
        self.assertTrue(success, "Message processing failed")
        self.assertIsNotNone(response, "No response received")
        
        # Verify message history
        history = self.eliza_handler.get_session_history(session_id)
        self.assertGreaterEqual(len(history), 2, "Message history should contain at least 2 messages")

    def test_platform_stats(self):
        """Test platform statistics tracking"""
        # Create and use a session
        session_id = self.eliza_handler.create_session("test_user")
        self.eliza_handler.process_message(session_id, "Hello")
        
        # Check platform stats
        c = self.conn.cursor()
        c.execute("SELECT total_interactions FROM platform_stats WHERE platform = 'eliza'")
        result = c.fetchone()
        
        self.assertIsNotNone(result, "Platform stats not found")
        self.assertGreater(result[0], 0, "No interactions recorded")

    def test_session_cleanup(self):
        """Test inactive session cleanup"""
        # Create a session
        session_id = self.eliza_handler.create_session("test_user")
        
        # End the session
        success = self.eliza_handler.end_session(session_id)
        self.assertTrue(success, "Session ending failed")
        
        # Verify session is inactive
        c = self.conn.cursor()
        c.execute("SELECT is_active FROM eliza_sessions WHERE session_id = ?", (session_id,))
        result = c.fetchone()
        
        self.assertIsNotNone(result, "Session not found")
        self.assertFalse(result[0], "Session should be inactive")

    def tearDown(self):
        """Clean up test environment"""
        self.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

if __name__ == '__main__':
    unittest.main() 