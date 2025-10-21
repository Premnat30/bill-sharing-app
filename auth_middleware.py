# auth_middleware.py
from functools import wraps
from flask import session, flash, redirect, url_for, current_app

def get_current_user():
    if 'user_id' not in session:
        return None
    try:
        with current_app.app_context():
            from app import User
            return User.query.get(session['user_id'])
    except Exception:
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        
        is_admin = getattr(user, 'is_admin', False)
        admin_approved = getattr(user, 'admin_approved', False)
        
        if not is_admin or not admin_approved:
            flash('Admin access required. Please wait for admin approval.', 'error')
            return redirect(url_for('dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        
        if not getattr(user, 'is_super_admin', False):
            flash('Super admin access required', 'error')
            return redirect(url_for('dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function
