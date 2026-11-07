import hashlib
from datetime import timedelta
from flask import Blueprint, render_template, session, redirect, url_for, jsonify, abort, request
from sqlalchemy import select, delete, func
from werkzeug.security import check_password_hash, generate_password_hash
from database import db
from models import User, LoginAttempt, now
from .common import payload, string, role_required

auth = Blueprint('auth', __name__)

@auth.get('/login')
def login_page():
    return render_template('login.html')

@auth.post('/api/login')
def login():
    data = payload()
    username = string(data, 'username', 1, 80).lower()
    password = string(data, 'password', 1, 200)
    # Rate-limit by address, so rotating usernames cannot bypass the limit.
    attempt_key = hashlib.sha256((request.remote_addr or 'unknown').encode()).hexdigest()
    cutoff = now() - timedelta(minutes=10)
    db.session.execute(delete(LoginAttempt).where(LoginAttempt.created_at < cutoff))
    count = db.session.scalar(select(func.count()).select_from(LoginAttempt).where(LoginAttempt.key == attempt_key))
    if count >= 10:
        abort(429, description='Too many sign-in attempts. Try again in 10 minutes.')
    user = db.session.scalar(select(User).where(User.username == username))
    if not user or not check_password_hash(user.password_hash, password):
        db.session.add(LoginAttempt(key=attempt_key))
        db.session.commit()
        abort(401, description='Incorrect username or password.')
    db.session.execute(delete(LoginAttempt).where(LoginAttempt.key == attempt_key))
    db.session.commit()
    import secrets
    session.clear()
    session['user_id'] = user.id
    session['csrf'] = secrets.token_urlsafe(32)
    session.permanent = True
    return jsonify(redirect='/staff', role=user.role)

@auth.post('/api/logout')
def logout():
    session.clear()
    return jsonify(redirect='/login')

@auth.post('/api/password')
@role_required('admin', 'waiter', 'kitchen')
def password():
    data = payload()
    user = db.session.get(User, session['user_id'])
    if not check_password_hash(user.password_hash, string(data, 'current_password', 1, 200)):
        abort(400, description='Current password is incorrect.')
    value = string(data, 'new_password', 10, 200)
    user.password_hash = generate_password_hash(value)
    db.session.commit()
    return jsonify(message='Password updated.')
