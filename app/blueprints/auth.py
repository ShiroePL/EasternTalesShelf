from flask import Blueprint, flash, render_template, jsonify, request, session, url_for, redirect
from flask_login import login_user, login_required, logout_user, current_user
from app.functions.class_mangalist import Users, db_session
from app.oauth_handler import AniListOAuth
from app.oauth_config import ANILIST_CLIENT_ID, ANILIST_CLIENT_SECRET, ANILIST_REDIRECT_URI

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = Users.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                login_user(user, remember=True)
                db_session.commit()
                return jsonify({'success': True}), 200
            else:
                return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
    except Exception as e:
        db_session.rollback()
        raise e

@auth_bp.route('/logout')
def logout():
    logout_user()  # Flask-Login's logout function
    return redirect(url_for('main.home'))

@auth_bp.route('/auth/anilist')
def anilist_login():
    """Initiate AniList OAuth login flow"""
    # Check if user wants enhanced features
    store_token = request.args.get('store_token', 'false').lower() == 'true'
    
    # Store preference in session
    session['store_anilist_token'] = store_token
    
    return redirect(AniListOAuth.get_auth_url())

@auth_bp.route('/auth/anilist/callback')
def anilist_callback():
    """Handle the callback from AniList OAuth"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        
        # Get preference from session (default to False for privacy)
        store_token = session.get('store_anilist_token', False)
        
        if not code:
            flash('Authentication failed: No authorization code received', 'error')
            return redirect(url_for('main.home'))
            
        # Process the callback and get user info and access token
        user_info, access_token = AniListOAuth.handle_callback(code, state, store_token)
        
        if not user_info or 'id' not in user_info:
            flash('Authentication failed: Could not retrieve user information', 'error')
            return redirect(url_for('main.home'))
            
        # Find or create user with encrypted token
        user = Users.find_or_create_from_anilist(db_session, user_info, access_token)
        
        if user:
            # Log in the user
            login_user(user, remember=True)
            if store_token:
                flash(f'Welcome, {user.display_name or user.username}! Enhanced features are enabled.', 'success')
            else:
                flash(f'Welcome, {user.display_name or user.username}! (Privacy mode enabled)', 'success')
            return redirect(url_for('main.home'))
        else:
            flash('Authentication failed: User could not be created', 'error')
            return redirect(url_for('main.home'))
            
    except Exception as e:
        db_session.rollback()
        # Use current app's logger
        from flask import current_app
        current_app.logger.error(f"AniList OAuth error: {str(e)}")
        flash(f'Authentication error: {str(e)}', 'error')
        return redirect(url_for('main.home')) 