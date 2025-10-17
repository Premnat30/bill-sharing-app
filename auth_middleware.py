# auth_middleware.py
from functools import wraps
from flask import session, flash, redirect, url_for

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
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        
        # Check if user is approved admin
        from app import User, db
        
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin or not getattr(user, 'admin_approved', False):
            flash('Admin access required. Please wait for admin approval.', 'error')
            return redirect(url_for('dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        
        # Check if user is the original super admin
        from app import User
        user = User.query.get(session['user_id'])
        
        # Super admin is the first admin user (usually username 'admin')
        if not user or user.username != 'admin':
            flash('Super admin access required', 'error')
            return redirect(url_for('dashboard'))
            
        return f(*args, **kwargs)
    return decorated_function
