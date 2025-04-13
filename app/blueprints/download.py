from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app.admin import admin_required
from app.functions import sqlalchemy_fns
import logging
from app.functions.class_mangalist import db_session
from app.models.scraper_models import ScrapeQueue
import requests
from bs4 import BeautifulSoup
import re

download_bp = Blueprint('download', __name__, url_prefix='/api')

@download_bp.route('/download/status')
@login_required
@admin_required
def get_download_status():
    try:
        statuses = sqlalchemy_fns.get_download_statuses()
        return jsonify(statuses)
    except Exception as e:
        logging.error(f"Error getting download status: {e}")
        return jsonify({'error': str(e)}), 500

@download_bp.route('/download/status/update', methods=['POST'])
@login_required
@admin_required
def update_download_status():
    try:
        data = request.json
        anilist_id = data.get('anilist_id')
        status = data.get('status')
        
        if not anilist_id or not status:
            return jsonify({'error': 'anilist_id and status are required'}), 400
            
        sqlalchemy_fns.update_download_status(anilist_id, status)
        
        # Notify clients about the status update
        try:
            current_app.socketio.emit('download_status_update', {
                'anilist_id': anilist_id,
                'status': status
            })
        except Exception as e:
            logging.error(f"Error emitting socketio event: {e}")
            # Continue even if the socketio event fails
        
        return jsonify({'success': True}), 200
    except Exception as e:
        logging.error(f"Error updating download status: {e}")
        return jsonify({'error': str(e)}), 500

# Queue management routes
@download_bp.route('/queue/add', methods=['POST'])
@login_required
@admin_required
def add_to_queue_route():
    try:
        data = request.json
        if not data:
            logging.error("No JSON data received in request")
            return jsonify({'error': 'No data provided'}), 400
            
        title = data.get('title')
        bato_url = data.get('bato_url')
        anilist_id = data.get('anilist_id')

        logging.info(f"Adding to queue: title={title}, anilist_id={anilist_id}")
        
        if not all([title, bato_url]):
            return jsonify({'error': 'Missing required fields (title or bato_url)'}), 400

        # Add to queue
        result = sqlalchemy_fns.add_to_queue(title, bato_url, anilist_id)
        if not result:
            return jsonify({'error': 'Failed to add to queue - database operation failed'}), 500
            
        # Emit WebSocket event for real-time update
        try:
            current_app.socketio.emit('download_status_update', {
                'anilist_id': anilist_id,
                'status': 'pending'
            })
            logging.info(f"Emitted download_status_update event for anilist_id={anilist_id}")
        except Exception as e:
            logging.error(f"Error emitting socketio event: {e}")
            # Continue even if the socketio event fails
            
        return jsonify({'success': True}), 200
    except Exception as e:
        logging.exception(f"Error adding to queue: {e}")
        return jsonify({'error': str(e)}), 500

@download_bp.route('/queue/status')
@login_required
@admin_required
def get_queue_status_route():
    try:
        current_task, pending_tasks = sqlalchemy_fns.get_queue_status()
        
        return jsonify({
            'current_task': {
                'title': current_task.manhwa_title if current_task else None,
                'status': current_task.status if current_task else None,
                'current_chapter': current_task.current_chapter if current_task else 0,
                'total_chapters': current_task.total_chapters if current_task else 0,
                'error_message': current_task.error_message if current_task else None,
                'anilist_id': current_task.anilist_id if current_task else None
            } if current_task else None,
            'queued_tasks': [{
                'title': task.manhwa_title,
                'status': task.status,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'current_chapter': task.current_chapter,
                'total_chapters': task.total_chapters,
                'anilist_id': task.anilist_id
            } for task in pending_tasks]
        })
    except Exception as e:
        logging.error(f"Error getting queue status: {e}")
        return jsonify({'error': str(e)}), 500

@download_bp.route('/queue/pause', methods=['POST'])
@login_required
@admin_required
def pause_queue_task_route():
    try:
        data = request.json
        title = data.get('title')
        if not title:
            return jsonify({'error': 'Title is required'}), 400

        task = db_session.query(ScrapeQueue).filter_by(manhwa_title=title).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404
            
        if task and task.anilist_id:
            sqlalchemy_fns.pause_queue_task(title)
            # Emit both events
            try:
                current_app.socketio.emit('queue_update', {'type': 'task_paused'})
                current_app.socketio.emit('download_status_update', {
                    'anilist_id': task.anilist_id,
                    'status': 'stopped'
                })
                logging.info(f"Emitted status update for {task.anilist_id}: stopped")
            except Exception as e:
                logging.error(f"Error emitting socketio events: {e}")
                # Continue even if the socketio events fail
        return jsonify({'success': True}), 200
    except Exception as e:
        logging.error(f"Error in pause_queue_task_route: {e}")
        return jsonify({'error': str(e)}), 500

@download_bp.route('/queue/resume', methods=['POST'])
@login_required
@admin_required
def resume_queue_task_route():
    try:
        data = request.json
        title = data.get('title')
        if not title:
            return jsonify({'error': 'Title is required'}), 400

        task = db_session.query(ScrapeQueue).filter_by(manhwa_title=title).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404
            
        if task and task.anilist_id:
            sqlalchemy_fns.resume_queue_task(title)
            try:
                current_app.socketio.emit('queue_update', {'type': 'task_resumed'})
                current_app.socketio.emit('download_status_update', {
                    'anilist_id': task.anilist_id,
                    'status': 'pending'
                })
            except Exception as e:
                logging.error(f"Error emitting socketio events: {e}")
                # Continue even if the socketio events fail
        return jsonify({'success': True}), 200
    except Exception as e:
        logging.error(f"Error in resume_queue_task_route: {e}")
        return jsonify({'error': str(e)}), 500

@download_bp.route('/queue/remove', methods=['POST'])
@login_required
@admin_required
def remove_queue_task_route():
    try:
        data = request.json
        title = data.get('title')
        if not title:
            return jsonify({'error': 'Title is required'}), 400

        task = db_session.query(ScrapeQueue).filter_by(manhwa_title=title).first()
        if not task:
            return jsonify({'error': 'Task not found'}), 404
            
        if task and task.anilist_id:
            # Store the anilist_id before removing the task
            anilist_id = task.anilist_id
            
            if sqlalchemy_fns.remove_queue_task(title):
                try:
                    current_app.socketio.emit('queue_update', {'type': 'task_removed'})
                    current_app.socketio.emit('download_status_update', {
                        'anilist_id': anilist_id,
                        'status': 'not_downloaded'
                    })
                except Exception as e:
                    logging.error(f"Error emitting socketio events: {e}")
                    # Continue even if the socketio events fail
                return jsonify({'success': True}), 200
        return jsonify({'error': 'Failed to remove task'}), 500
    except Exception as e:
        logging.error(f"Error in remove_queue_task_route: {e}")
        return jsonify({'error': str(e)}), 500

@download_bp.route('/queue/force_priority', methods=['POST'])
@login_required
@admin_required
def force_priority_route():
    try:
        data = request.json
        title = data.get('title')
        if not title:
            return jsonify({'error': 'Title is required'}), 400

        if not sqlalchemy_fns.force_task_priority(title):
            return jsonify({'error': 'Failed to update priority'}), 500
            
        try:
            current_app.socketio.emit('queue_update', {'type': 'priority_changed'})
        except Exception as e:
            logging.error(f"Error emitting socketio event: {e}")
            # Continue even if the socketio event fails
            
        return jsonify({'success': True}), 200
    except Exception as e:
        logging.error(f"Error in force_priority_route: {e}")
        return jsonify({'error': str(e)}), 500 