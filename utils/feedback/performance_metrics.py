"""
Performance Metrics Module
Handles aggregation and analysis of personality performance metrics.
"""

import sqlite3
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
from utils.database import (
    get_db_connection,
    get_personality_stats,
    get_top_posts,
    get_performance_trends,
    batch_update_metrics
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceMetrics:
    def __init__(self, db_path: str = "reddit_bot.db"):
        """Initialize the performance metrics tracker."""
        self.db_path = db_path

    def update_personality_metrics(self, personality: str) -> bool:
        """
        Update performance metrics for a personality based on their posts.
        
        Args:
            personality: The personality to update metrics for
            
        Returns:
            bool: True if update was successful
        """
        try:
            # Get personality stats for the last 30 days
            stats = get_personality_stats(personality, days=30)
            if not stats:
                logger.info(f"No recent stats found for personality: {personality}")
                return False
            
            conn = get_db_connection()
            if not conn:
                return False
            
            cursor = conn.cursor()
            
            # Update personality performance metrics
            cursor.execute("""
                INSERT OR REPLACE INTO personality_performance
                (personality, avg_upvote_ratio, avg_score, 
                total_posts, successful_posts, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                personality,
                stats['avg_upvote_ratio'],
                stats['avg_score'],
                stats['total_posts'],
                stats['successful_posts'],
                datetime.now()
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error updating personality metrics: {e}")
            return False

    def get_personality_performance_report(self, personality: str) -> Dict:
        """
        Generate a comprehensive performance report for a personality.
        
        Args:
            personality: The personality to analyze
            
        Returns:
            Dict: Detailed performance metrics and insights
        """
        try:
            # Get basic stats
            stats = get_personality_stats(personality)
            if not stats:
                return {'error': 'No data available'}
                
            # Get top performing posts
            top_posts = get_top_posts(personality, limit=5)
            
            # Get performance trends
            trends = get_performance_trends(days=30)
            personality_trends = trends.get(personality, [])
            
            # Calculate trend indicators
            trend_data = []
            if personality_trends:
                for day, sentiment, count in personality_trends:
                    trend_data.append({
                        'date': day,
                        'sentiment': round(sentiment, 3),
                        'post_count': count
                    })
            
            # Calculate success metrics
            success_rate = stats['success_rate']
            performance_level = self._calculate_performance_level(success_rate)
            
            return {
                'personality': personality,
                'overall_stats': stats,
                'performance_level': performance_level,
                'top_posts': top_posts,
                'trend_data': trend_data,
                'recommendations': self._generate_recommendations(stats, performance_level)
            }
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {'error': str(e)}

    def get_comparative_analysis(self) -> Dict:
        """
        Generate a comparative analysis of all personalities.
        
        Returns:
            Dict: Comparative metrics and rankings
        """
        try:
            conn = get_db_connection()
            if not conn:
                return {'error': 'Database connection failed'}
                
            cursor = conn.cursor()
            
            # Get overall rankings
            cursor.execute("""
                SELECT 
                    personality,
                    avg_upvote_ratio,
                    avg_score,
                    CAST(successful_posts AS FLOAT) / total_posts as success_rate
                FROM personality_performance
                WHERE total_posts >= 5
                ORDER BY success_rate DESC
            """)
            
            rankings = cursor.fetchall()
            conn.close()
            
            # Process rankings
            comparative_data = {
                'rankings': [{
                    'personality': row[0],
                    'avg_upvote_ratio': row[1],
                    'avg_score': row[2],
                    'success_rate': round(row[3], 3)
                } for row in rankings],
                'summary': self._generate_comparative_summary(rankings)
            }
            
            return comparative_data
            
        except Exception as e:
            logger.error(f"Error generating comparative analysis: {e}")
            return {'error': str(e)}

    def _calculate_performance_level(self, success_rate: float) -> str:
        """Calculate performance level based on success rate."""
        if success_rate >= 0.8:
            return "Exceptional"
        elif success_rate >= 0.6:
            return "High Performing"
        elif success_rate >= 0.4:
            return "Performing Well"
        elif success_rate >= 0.2:
            return "Needs Improvement"
        else:
            return "Underperforming"

    def _generate_recommendations(self, stats: Dict, performance_level: str) -> List[str]:
        """Generate personalized recommendations based on performance metrics."""
        recommendations = []
        
        if stats['avg_upvote_ratio'] < 0.7:
            recommendations.append(
                "Focus on improving post quality to increase upvote ratio"
            )
            
        if stats['avg_comments'] < 5:
            recommendations.append(
                "Create more engaging content to encourage discussion"
            )
            
        if performance_level in ["Needs Improvement", "Underperforming"]:
            recommendations.append(
                "Review successful posts to identify effective patterns"
            )
            
        if stats['total_posts'] < 10:
            recommendations.append(
                "Increase posting frequency to gather more performance data"
            )
            
        return recommendations or ["Maintain current performance strategy"]

    def _generate_comparative_summary(self, rankings: List[Tuple]) -> Dict:
        """Generate summary insights from comparative rankings."""
        if not rankings:
            return {}
            
        total_personalities = len(rankings)
        avg_success_rate = sum(row[3] for row in rankings) / total_personalities
        
        return {
            'total_personalities': total_personalities,
            'avg_success_rate': round(avg_success_rate, 3),
            'top_performer': rankings[0][0] if rankings else None,
            'needs_improvement': [row[0] for row in rankings if row[3] < 0.4]
        }

    def update_all_personalities(self) -> bool:
        """
        Update metrics for all personalities.
        
        Returns:
            bool: True if all updates were successful
        """
        try:
            conn = get_db_connection()
            if not conn:
                return False
                
            cursor = conn.cursor()
            
            # Get all personalities
            cursor.execute("SELECT DISTINCT personality FROM post_metrics")
            personalities = cursor.fetchall()
            conn.close()
            
            success = True
            for (personality,) in personalities:
                if not self.update_personality_metrics(personality):
                    logger.warning(f"Failed to update metrics for {personality}")
                    success = False
                    
            return success
            
        except Exception as e:
            logger.error(f"Error updating all personalities: {e}")
            return False

    def get_personality_metrics(self, personality: str) -> Optional[Dict]:
        """
        Retrieve performance metrics for a specific personality.
        
        Args:
            personality: The personality to get metrics for
            
        Returns:
            Optional[Dict]: Performance metrics or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT avg_upvote_ratio, avg_score, 
                       total_posts, successful_posts, last_updated
                FROM personality_performance
                WHERE personality = ?
            """, (personality,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'avg_upvote_ratio': result[0],
                    'avg_score': result[1],
                    'total_posts': result[2],
                    'successful_posts': result[3],
                    'last_updated': result[4]
                }
            return None
            
        except sqlite3.Error as e:
            logger.error(f"Error retrieving personality metrics: {e}")
            return None

    def get_top_performing_personalities(self, limit: int = 3) -> List[Dict]:
        """
        Get the top performing personalities based on success rate.
        
        Args:
            limit: Number of top personalities to return
            
        Returns:
            List[Dict]: List of top performing personalities and their metrics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT personality, avg_upvote_ratio, avg_score,
                       total_posts, successful_posts,
                       CAST(successful_posts AS FLOAT) / total_posts as success_rate
                FROM personality_performance
                WHERE total_posts >= 5
                ORDER BY success_rate DESC
                LIMIT ?
            """, (limit,))
            
            results = cursor.fetchall()
            conn.close()
            
            return [{
                'personality': row[0],
                'avg_upvote_ratio': row[1],
                'avg_score': row[2],
                'total_posts': row[3],
                'successful_posts': row[4],
                'success_rate': row[5]
            } for row in results]
            
        except sqlite3.Error as e:
            logger.error(f"Error retrieving top personalities: {e}")
            return []

    def get_performance_summary(self) -> Dict:
        """
        Get a summary of overall system performance.
        
        Returns:
            Dict: Summary statistics of all personalities
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT personality) as total_personalities,
                    SUM(total_posts) as total_posts,
                    SUM(successful_posts) as total_successful_posts,
                    AVG(avg_upvote_ratio) as overall_upvote_ratio,
                    AVG(avg_score) as overall_avg_score
                FROM personality_performance
            """)
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'total_personalities': result[0],
                    'total_posts': result[1],
                    'total_successful_posts': result[2],
                    'overall_upvote_ratio': round(result[3], 3),
                    'overall_avg_score': round(result[4], 2),
                    'overall_success_rate': round(result[2] / result[1], 3) if result[1] else 0
                }
            return {}
            
        except sqlite3.Error as e:
            logger.error(f"Error retrieving performance summary: {e}")
            return {}

    def get_performance_trends(self, days: int = 7) -> Dict:
        """
        Get performance trends over time for all personalities.
        
        Args:
            days: Number of days to analyze (default: 7)
            
        Returns:
            Dict: Performance trends by personality
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get daily performance metrics for each personality
            cursor.execute("""
                SELECT 
                    personality,
                    date(last_updated) as day,
                    AVG(sentiment_score) as avg_sentiment,
                    AVG(score) as avg_score,
                    COUNT(*) as post_count,
                    AVG(engagement_rate) as avg_engagement
                FROM post_metrics
                WHERE datetime(last_updated) >= datetime('now', ?)
                GROUP BY personality, day
                ORDER BY personality, day ASC
            """, (f'-{days} days',))
            
            results = cursor.fetchall()
            conn.close()
            
            # Organize results by personality
            trends = {}
            for row in results:
                personality = row[0]
                if personality not in trends:
                    trends[personality] = []
                    
                trends[personality].append({
                    'date': row[1],
                    'sentiment': round(row[2] or 0, 3),
                    'score': round(row[3] or 0, 2),
                    'post_count': row[4],
                    'engagement': round(row[5] or 0, 3)
                })
            
            return trends
            
        except sqlite3.Error as e:
            logger.error(f"Error retrieving performance trends: {e}")
            return {}

    def get_all_personalities(self) -> List[Dict]:
        """
        Get a list of all personalities and their current performance metrics.
        
        Returns:
            List[Dict]: List of personalities with their metrics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    personality,
                    avg_upvote_ratio,
                    avg_score,
                    total_posts,
                    successful_posts,
                    avg_sentiment_score,
                    avg_engagement_rate,
                    last_updated
                FROM personality_performance
                ORDER BY 
                    CAST(successful_posts AS FLOAT) / 
                    CASE WHEN total_posts = 0 THEN 1 ELSE total_posts END DESC
            """)
            
            results = cursor.fetchall()
            conn.close()
            
            return [{
                'name': row[0],
                'metrics': {
                    'avg_upvote_ratio': round(row[1] or 0, 3),
                    'avg_score': round(row[2] or 0, 2),
                    'total_posts': row[3],
                    'successful_posts': row[4],
                    'avg_sentiment': round(row[5] or 0, 3),
                    'avg_engagement': round(row[6] or 0, 3),
                    'success_rate': round(row[4] / row[3], 3) if row[3] > 0 else 0,
                    'last_updated': row[7]
                }
            } for row in results]
            
        except sqlite3.Error as e:
            logger.error(f"Error retrieving all personalities: {e}")
            return [] 