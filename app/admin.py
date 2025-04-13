from flask import jsonify, redirect, url_for, flash, request
from flask_login import current_user
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not (current_user.is_authenticated and current_user.is_admin):
            # Check if it's an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Unauthorized',
                    'message': 'You need administrator privileges to access this resource.'
                }), 403
            else:
                flash('You need administrator privileges to access this page.', 'danger')
                return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function 