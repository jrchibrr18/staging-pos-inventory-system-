"""Authentication routes."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from models import db, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if not User.query.first():
        return redirect(url_for('auth.setup'))
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter username and password.', 'danger')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if user.is_active:
                login_user(user, remember=request.form.get('remember', False))
                next_page = request.args.get('next') or url_for('dashboard.index')
                return redirect(next_page)
            flash('Account is disabled.', 'danger')
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    """One-time setup: create admin if no users exist."""
    if User.query.first():
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        
        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('auth/setup.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('auth/setup.html')
        
        user = User(username=username, full_name=full_name or username, role='admin')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Admin account created. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/setup.html')
