from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import Database
from utils.auth import redis_client, auth_required
from mysql.connector.errors import IntegrityError

auth_bp = Blueprint('auth', __name__)

# Use centralized Redis client from auth module
# redis_client is imported from auth

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    if not username or not email or not password:
        return jsonify({'error': 'username, email, and password are required'}), 400
    
    password_hash = generate_password_hash(password)

    try:
        # Let database constraints handle uniqueness validation atomically
        Database.execute_query(
            'INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)',
            (username, email, password_hash)
        )
        # Fetch the new user id
        user = Database.execute_query(
            'SELECT id FROM users WHERE username = %s', (username,), fetch_one=True
        )
        user_id = user['id'] if user else None
        
        # Update Redis cache after successful database insertion
        if user_id:
            redis_client.hset('users:username', username, user_id)
            redis_client.hset('users:email', email, user_id)
        
        # Store user_id in session
        session['user_id'] = user_id
    except IntegrityError as e:
        # Handle duplicate key violations (MySQL error code 1062)
        if e.errno == 1062:
            return jsonify({'error': 'Username or email already exists'}), 409
        raise
    return jsonify({'message': 'User registered successfully', 'username': username, 'email': email}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'email and password are required'}), 400
    
    user = Database.execute_query(
        'SELECT id, username, password_hash, is_active FROM users WHERE email = %s',
        (email,), fetch_one=True
    )

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    # Check if account is active
    if not user.get('is_active', True):
        return jsonify({'error': 'Account is deactivated'}), 403
    
    # Update last_login timestamp
    Database.execute_query(
        'UPDATE users SET last_login = NOW() WHERE id = %s',
        (user['id'])
    )
    
    session.permanent = True
    session['user_id'] = user['id']
    return jsonify({'message': 'Login successful', 'user_id': user['id'], 'username': user['username'], 'email': email}), 200

@auth_bp.route('/me', methods=['GET'])
@auth_required
def get_current_user():
    """Get current user from session"""
    user_id = session.get('user_id')
    
    user = Database.execute_query(
        'SELECT id, username, email FROM users WHERE id = %s',
        (user_id), fetch_one=True
    )
    
    if not user:
        session.pop('user_id', None)
        return jsonify({'error': 'User not found'}), 401
    
    return jsonify({
        'user_id': user['id'],
        'username': user['username'],
        'email': user['email']
    }), 200

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Logout user and clear session"""
    session.pop('user_id', None)
    session.modified = True
    return jsonify({'message': 'Logout successful'}), 200

@auth_bp.route('/account', methods=['DELETE'])
@auth_required
def delete_account():
    """Deactivate user account by setting is_active to FALSE"""
    user_id = session.get('user_id')
    
    try:
        # Set is_active to FALSE instead of deleting the user
        Database.execute_query(
            'UPDATE users SET is_active = FALSE WHERE id = %s',
            (user_id)
        )
        
        # Clear the session
        session.pop('user_id', None)
        session.modified = True
        
        return jsonify({'message': 'Account deactivated successfully'}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to deactivate account' }), 500
