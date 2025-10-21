from functools import wraps
from flask import session, flash, redirect, url_for, current_app
from flask_sqlalchemy import SQLAlchemy

def get_current_user():
    """Helper function to get current user without circular imports"""
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
        
        # Check admin status with safe attribute access
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
        
        # Flexible super admin check
        is_super_admin = (getattr(user, 'is_super_admin', False) or 
                         getattr(user, 'role', '') == 'super_admin' or
                         user.username == 'admin')
        
        if not is_super_admin:
            flash('Super admin access required', 'error')
            return redirect(url_for('dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function
