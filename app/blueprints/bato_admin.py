"""
Bato Admin Blueprint
Admin dashboard for monitoring Bato.to scraping system

Provides endpoints for:
- Scraping statistics and performance metrics
- Recent scraping job logs
- Error rate monitoring
- Admin dashboard page
"""

from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required, current_user
from app.admin import admin_required
from app.database_module.bato_repository import BatoRepository
from datetime import datetime, timedelta
import logging
import os
import json

logger = logging.getLogger(__name__)

bato_admin_bp = Blueprint('bato_admin', __name__)


def load_color_settings():
    """Load user-specific color settings"""
    user_id = current_user.id if current_user.is_authenticated else 'default'
    settings_dir = os.path.join('app', 'user_settings')
    settings_path = os.path.join(settings_dir, f'user_color_settings_{user_id}.json')
    
    try:
        with open(settings_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Return default settings
        default_settings = {
            'background_color': '#1a1a2e',
            'primary_color': '#16213e',
            'secondary_color': '#0f3460',
            'accent_color': '#e94560'
        }
        return default_settings


@bato_admin_bp.route('/admin/bato', methods=['GET'])
@admin_required
@login_required
def bato_admin_dashboard():
    """
    Render the Bato admin dashboard page.
    
    Returns:
        Rendered HTML template
        
    Requirements: 10.3
    """
    try:
        color_settings = load_color_settings()
        return render_template(
            'pages/bato_admin.html',
            color_settings=color_settings,
            isDevelopment=(os.getenv('FLASK_ENV') == 'development'),
            graphql_safety_key=os.getenv('GRAPHQL_SAFETY_KEY', '')
        )
    except Exception as e:
        logger.error(f"Error rendering Bato admin dashboard: {e}", exc_info=True)
        return "Error loading admin dashboard", 500


@bato_admin_bp.route('/api/bato/admin/stats', methods=['GET'])
@login_required
@admin_required
def get_scraping_stats():
    """
    Get scraping statistics for monitoring.
    
    Query Parameters:
        hours (int): Number of hours to look back (default: 24)
    
    Returns:
        JSON response with scraping statistics
        
    Requirements: 10.3, 10.4, 10.5
    """
    try:
        hours = request.args.get('hours', 24, type=int)
        
        # Get statistics from repository
        stats = BatoRepository.get_scraping_stats(hours=hours)
        
        # Get recent logs
        recent_logs = BatoRepository.get_recent_logs(limit=20)
        
        # Convert logs to JSON-serializable format
        logs_data = []
        for log in recent_logs:
            logs_data.append({
                'id': log.id,
                'anilist_id': log.anilist_id,
                'bato_link': log.bato_link,
                'scrape_type': log.scrape_type,
                'status': log.status,
                'chapters_found': log.chapters_found,
                'new_chapters': log.new_chapters,
                'duration_seconds': log.duration_seconds,
                'error_message': log.error_message,
                'scraped_at': log.scraped_at.isoformat() if log.scraped_at else None
            })
        
        # Check for high error rate warning
        warning = None
        if stats.get('error_rate', 0) > 10:
            warning = {
                'type': 'high_error_rate',
                'message': f"Error rate is {stats['error_rate']:.1f}% over the last {hours} hours (threshold: 10%)",
                'severity': 'warning'
            }
        
        return jsonify({
            'success': True,
            'stats': stats,
            'recent_logs': logs_data,
            'warning': warning,
            'period_hours': hours
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching scraping stats: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch scraping statistics'
        }), 500


@bato_admin_bp.route('/api/bato/admin/system-status', methods=['GET'])
@login_required
@admin_required
def get_system_status():
    """
    Get system status information.
    
    Returns:
        JSON response with system status
    """
    try:
        from app.functions.class_mangalist import db_session
        from app.models.bato_models import (
            BatoMangaDetails,
            BatoScrapingSchedule,
            BatoScraperLog
        )
        
        # Count records in each table
        manga_count = db_session.query(BatoMangaDetails).count()
        schedule_count = db_session.query(BatoScrapingSchedule).filter(
            BatoScrapingSchedule.is_active == True
        ).count()
        log_count = db_session.query(BatoScraperLog).count()
        
        # Get next scheduled scrape
        next_scrape = db_session.query(BatoScrapingSchedule).filter(
            BatoScrapingSchedule.is_active == True
        ).order_by(BatoScrapingSchedule.next_scrape_at).first()
        
        db_session.remove()
        
        return jsonify({
            'success': True,
            'status': {
                'manga_tracked': manga_count,
                'active_schedules': schedule_count,
                'total_logs': log_count,
                'next_scrape_at': next_scrape.next_scrape_at.isoformat() if next_scrape else None,
                'has_data': log_count > 0
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching system status: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch system status'
        }), 500


@bato_admin_bp.route('/api/bato/admin/activity', methods=['GET'])
@login_required
@admin_required
def get_scraping_activity():
    """
    Get scraping activity data for charts.
    Returns hourly aggregated data for the specified time period.
    
    Query Parameters:
        hours (int): Number of hours to look back (default: 24)
    
    Returns:
        JSON response with hourly activity data
        
    Requirements: 10.3, 10.4
    """
    try:
        hours = request.args.get('hours', 24, type=int)
        
        # Get all logs for the period
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        from app.functions.class_mangalist import db_session
        from app.models.bato_models import BatoScraperLog
        
        logs = db_session.query(BatoScraperLog).filter(
            BatoScraperLog.scraped_at >= cutoff_time
        ).all()
        
        # Aggregate by hour
        hourly_data = {}
        for log in logs:
            if log.scraped_at:
                hour_key = log.scraped_at.replace(minute=0, second=0, microsecond=0)
                hour_str = hour_key.isoformat()
                
                if hour_str not in hourly_data:
                    hourly_data[hour_str] = {
                        'timestamp': hour_str,
                        'total': 0,
                        'success': 0,
                        'failed': 0,
                        'chapters_found': 0,
                        'new_chapters': 0
                    }
                
                hourly_data[hour_str]['total'] += 1
                if log.status == 'success':
                    hourly_data[hour_str]['success'] += 1
                elif log.status == 'failed':
                    hourly_data[hour_str]['failed'] += 1
                
                hourly_data[hour_str]['chapters_found'] += log.chapters_found or 0
                hourly_data[hour_str]['new_chapters'] += log.new_chapters or 0
        
        # Convert to sorted list
        activity_data = sorted(hourly_data.values(), key=lambda x: x['timestamp'])
        
        db_session.remove()
        
        return jsonify({
            'success': True,
            'activity': activity_data,
            'period_hours': hours
        }), 200
        
    except Exception as e:
        logger.error(f"Error fetching scraping activity: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch scraping activity'
        }), 500
