"""
Performance Monitoring Module
Handles monitoring, alerting, and reporting of system performance.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os
from utils.feedback.performance_metrics import PerformanceMetrics
from utils.feedback.sentiment_tracker import SentimentTracker
from utils.database import get_db_connection

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceMonitor:
    def __init__(self):
        """Initialize the performance monitor."""
        self.performance_metrics = PerformanceMetrics()
        self.sentiment_tracker = SentimentTracker()
        self.alert_thresholds = {
            'low_success_rate': 0.3,
            'high_success_rate': 0.8,
            'min_engagement': 5,
            'unusual_activity': 2.0  # Standard deviations from mean
        }
        
    def generate_daily_report(self) -> Dict:
        """
        Generate a comprehensive daily performance report.
        
        Returns:
            Dict: Daily performance metrics and insights
        """
        try:
            # Get comparative analysis
            comparative = self.performance_metrics.get_comparative_analysis()
            
            # Get performance trends
            trends = self.performance_metrics.get_performance_trends(days=1)
            
            # Calculate daily statistics
            daily_stats = self._calculate_daily_stats()
            
            # Generate alerts
            alerts = self._check_for_alerts(daily_stats, comparative)
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'daily_stats': daily_stats,
                'performance_summary': comparative.get('summary', {}),
                'personality_rankings': comparative.get('rankings', []),
                'alerts': alerts,
                'recommendations': self._generate_daily_recommendations(
                    daily_stats, alerts
                )
            }
            
            # Save report
            self._save_daily_report(report)
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            return {'error': str(e)}

    def _calculate_daily_stats(self) -> Dict:
        """Calculate daily performance statistics."""
        try:
            conn = get_db_connection()
            if not conn:
                return {}
                
            cursor = conn.cursor()
            
            # Get today's stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_posts,
                    AVG(upvote_ratio) as avg_upvote_ratio,
                    AVG(score) as avg_score,
                    AVG(num_comments) as avg_comments,
                    AVG(sentiment_score) as avg_sentiment
                FROM post_metrics
                WHERE date(last_updated) = date('now')
            """)
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'total_posts': result[0],
                    'avg_upvote_ratio': round(result[1] or 0, 3),
                    'avg_score': round(result[2] or 0, 2),
                    'avg_comments': round(result[3] or 0, 2),
                    'avg_sentiment': round(result[4] or 0, 3)
                }
            return {}
            
        except Exception as e:
            logger.error(f"Error calculating daily stats: {e}")
            return {}

    def _check_for_alerts(self, daily_stats: Dict, comparative: Dict) -> List[Dict]:
        """Check for unusual patterns and generate alerts."""
        alerts = []
        
        try:
            # Check for low activity
            if daily_stats.get('total_posts', 0) < 5:
                alerts.append({
                    'level': 'warning',
                    'type': 'low_activity',
                    'message': 'Unusually low posting activity today'
                })
            
            # Check for low engagement
            if daily_stats.get('avg_comments', 0) < self.alert_thresholds['min_engagement']:
                alerts.append({
                    'level': 'warning',
                    'type': 'low_engagement',
                    'message': 'Below average comment engagement'
                })
            
            # Check for unusual success rates
            for personality in comparative.get('rankings', []):
                success_rate = personality.get('success_rate', 0)
                
                if success_rate < self.alert_thresholds['low_success_rate']:
                    alerts.append({
                        'level': 'warning',
                        'type': 'low_performance',
                        'message': f"Low performance detected for {personality['personality']}"
                    })
                elif success_rate > self.alert_thresholds['high_success_rate']:
                    alerts.append({
                        'level': 'info',
                        'type': 'high_performance',
                        'message': f"Exceptional performance from {personality['personality']}"
                    })
            
            # Check for unusual sentiment patterns
            if daily_stats.get('avg_sentiment', 0) < 0.4:
                alerts.append({
                    'level': 'warning',
                    'type': 'low_sentiment',
                    'message': 'Overall low sentiment scores today'
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            return []

    def _generate_daily_recommendations(self, stats: Dict, alerts: List[Dict]) -> List[str]:
        """Generate recommendations based on daily performance."""
        recommendations = []
        
        try:
            # Activity-based recommendations
            if stats.get('total_posts', 0) < 5:
                recommendations.append(
                    "Consider increasing posting frequency to maintain engagement"
                )
            
            # Engagement-based recommendations
            if stats.get('avg_comments', 0) < self.alert_thresholds['min_engagement']:
                recommendations.append(
                    "Focus on creating more engaging content to encourage discussions"
                )
            
            # Alert-based recommendations
            alert_types = [alert['type'] for alert in alerts]
            
            if 'low_performance' in alert_types:
                recommendations.append(
                    "Review and adjust content strategy for underperforming personalities"
                )
            
            if 'low_sentiment' in alert_types:
                recommendations.append(
                    "Analyze successful posts to identify positive engagement patterns"
                )
            
            return recommendations or ["Maintain current performance strategy"]
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []

    def _save_daily_report(self, report: Dict) -> None:
        """Save daily report to file."""
        try:
            # Create reports directory if it doesn't exist
            os.makedirs('reports', exist_ok=True)
            
            # Generate filename with date
            filename = f"reports/daily_report_{datetime.now().strftime('%Y%m%d')}.json"
            
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2)
                
            logger.info(f"Saved daily report to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving daily report: {e}")

    def validate_data_collection(self) -> Dict:
        """
        Validate data collection and system integrity.
        
        Returns:
            Dict: Validation results and any issues found
        """
        try:
            validation = {
                'status': 'ok',
                'issues': [],
                'checks_passed': 0,
                'checks_failed': 0
            }
            
            # Check database connectivity
            conn = get_db_connection()
            if not conn:
                validation['issues'].append("Database connection failed")
                validation['checks_failed'] += 1
            else:
                validation['checks_passed'] += 1
                conn.close()
            
            # Check for recent data
            daily_stats = self._calculate_daily_stats()
            if not daily_stats:
                validation['issues'].append("No recent data found")
                validation['checks_failed'] += 1
            else:
                validation['checks_passed'] += 1
            
            # Check sentiment calculation
            test_sentiment = self.sentiment_tracker.calculate_sentiment_score(
                0.8, 10, 50
            )
            if test_sentiment is None:
                validation['issues'].append("Sentiment calculation failed")
                validation['checks_failed'] += 1
            else:
                validation['checks_passed'] += 1
            
            # Update status based on issues
            if validation['issues']:
                validation['status'] = 'warning' if validation['checks_passed'] > 0 else 'error'
            
            return validation
            
        except Exception as e:
            logger.error(f"Error validating system: {e}")
            return {
                'status': 'error',
                'issues': [str(e)],
                'checks_passed': 0,
                'checks_failed': 1
            }

    def get_performance_dashboard(self) -> Dict:
        """
        Generate a performance dashboard with key metrics.
        
        Returns:
            Dict: Dashboard data and visualizations
        """
        try:
            # Initialize default dashboard structure
            dashboard = {
                'current_status': {
                    'total_posts_today': 0,
                    'avg_sentiment_today': 0.0,
                    'active_personalities': 0,
                    'system_health': 'unknown'
                },
                'performance_trends': {
                    'personality_data': {},
                    'system_averages': {}
                },
                'top_performers': [],
                'recent_alerts': []
            }
            
            try:
                # Get recent performance data
                trends = self.performance_metrics.get_performance_trends(days=7)
                if trends:
                    dashboard['performance_trends']['personality_data'] = trends
            except Exception as e:
                logger.warning(f"Error getting performance trends: {e}")
            
            try:
                comparative = self.performance_metrics.get_comparative_analysis()
                if comparative:
                    dashboard['performance_trends']['system_averages'] = comparative.get('summary', {})
                    dashboard['top_performers'] = comparative.get('rankings', [])[:3]
            except Exception as e:
                logger.warning(f"Error getting comparative analysis: {e}")
            
            try:
                daily_stats = self._calculate_daily_stats()
                if daily_stats:
                    dashboard['current_status'].update({
                        'total_posts_today': daily_stats.get('total_posts', 0),
                        'avg_sentiment_today': daily_stats.get('avg_sentiment', 0),
                    })
            except Exception as e:
                logger.warning(f"Error getting daily stats: {e}")
            
            try:
                validation = self.validate_data_collection()
                dashboard['current_status']['system_health'] = validation['status']
                
                if validation['status'] != 'error':
                    dashboard['current_status']['active_personalities'] = len(
                        self.performance_metrics.get_all_personalities()
                    )
            except Exception as e:
                logger.warning(f"Error validating system: {e}")
            
            try:
                dashboard['recent_alerts'] = self._check_for_alerts(
                    daily_stats or {},
                    comparative or {'rankings': []}
                )
            except Exception as e:
                logger.warning(f"Error checking alerts: {e}")
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Error generating dashboard: {e}")
            return {
                'error': str(e),
                'current_status': {
                    'system_health': 'error',
                    'total_posts_today': 0,
                    'avg_sentiment_today': 0,
                    'active_personalities': 0
                }
            } 