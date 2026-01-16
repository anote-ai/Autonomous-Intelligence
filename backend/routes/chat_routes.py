from flask import Blueprint, request, jsonify, session
from database.db import Database
from utils.auth import auth_required
import uuid

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/chats', methods=['POST'])
@auth_required
def create_chat():
    """Create a new chat for the authenticated user"""
    user_id = session.get('user_id')
    data = request.get_json() or {}
    
    chat_title = data.get('name', 'New Chat')
    chat_uuid = str(uuid.uuid4())
    
    try:
        query = 'INSERT INTO chats (chat_uuid, user_id, title) VALUES (%s, %s, %s)'
        Database.execute_query(query, (chat_uuid, user_id, chat_title))
        
        return jsonify({
            'chat_uuid': chat_uuid,
            'name': chat_title,
            'message': 'Chat created successfully'
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/chats', methods=['GET'])
@auth_required
def get_user_chats():
    """Get all chats for the authenticated user"""
    user_id = session.get('user_id')
    
    try:
        query = '''
            SELECT chat_uuid, title as name, created_at, updated_at 
            FROM chats 
            WHERE user_id = %s AND is_archived = FALSE
            ORDER BY updated_at DESC
        '''
        chats = Database.execute_query(query, (user_id))
        
        return jsonify({'chats': chats}), 200
    except Exception as e:
        import logging
        logging.error(f"Error fetching chats: {e}")
        return jsonify({'error': 'Failed to fetch chats'}), 500


@chat_bp.route('/chats/<chat_uuid>', methods=['GET'])
@auth_required
def get_chat(chat_uuid):
    """Get a specific chat with its messages"""
    user_id = session.get('user_id')
    
    try:
        # Verify chat belongs to user and get chat details
        chat_query = '''
            SELECT id, chat_uuid, title as name, created_at, updated_at 
            FROM chats 
            WHERE chat_uuid = %s AND user_id = %s AND is_archived = FALSE
        '''
        chat = Database.execute_query(chat_query, (chat_uuid, user_id), fetch_one=True)
        
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        # Get chat messages with files in a single query using LEFT JOIN
        messages_query = '''
            SELECT 
                m.message_id as id, 
                m.content, 
                m.sender_type as role, 
                m.created_at,
                f.file_uuid,
                f.original_filename as filename,
                f.file_size as size,
                f.mime_type
            FROM messages m
            LEFT JOIN files f ON m.message_id = f.message_id AND f.is_deleted = FALSE
            WHERE m.chat_uuid = %s AND m.is_deleted = FALSE
            ORDER BY m.created_at ASC, f.file_uuid ASC
        '''
        results = Database.execute_query(messages_query, (chat_uuid), fetch_all=True) or []
        
        # Group results by message - use OrderedDict to maintain insertion order
        from collections import OrderedDict
        messages_dict = OrderedDict()
        for row in results:
            msg_id = row['id']
            if msg_id not in messages_dict:
                messages_dict[msg_id] = {
                    'id': msg_id,
                    'content': row['content'],
                    'role': row['role'],
                    'created_at': row['created_at'],
                    'files': []
                }
            
            # Add file if it exists
            if row['file_uuid']:
                messages_dict[msg_id]['files'].append({
                    'uuid': row['file_uuid'],
                    'name': row['filename'],
                    'size': row['size'],
                    'url': f'/api/files/{row["file_uuid"]}',
                    'type': row['mime_type']
                })
        
        messages = list(messages_dict.values())
                
        return jsonify({
            'chat': chat,
            'messages': messages
        }), 200
    except Exception as e:
        import logging
        logging.error(f"Error fetching chat {chat_uuid}: {e}")
        return jsonify({'error': 'Failed to fetch chat'}), 500


@chat_bp.route('/chats/<chat_uuid>/messages', methods=['POST'])
@auth_required
def add_message(chat_uuid):
    """Add a message to a chat"""
    user_id = session.get('user_id')
    data = request.get_json() or {}
    
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'error': 'Message content cannot be empty'}), 400
    role = data.get('role', 'user')  # 'user' or 'assistant'
    
    try:
        # Verify chat belongs to user
        chat_query = 'SELECT chat_uuid FROM chats WHERE chat_uuid = %s AND user_id = %s AND is_archived = FALSE'
        chat = Database.execute_query(chat_query, (chat_uuid, user_id), fetch_one=True)
        
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        # Generate a UUID for the message
        message_uuid = str(uuid.uuid4())
        
        # Insert message with explicit commit
        insert_query = '''
            INSERT INTO messages (message_id, chat_uuid, user_id, content, sender_type) 
            VALUES (%s, %s, %s, %s, %s)
        '''
        Database.execute_query(insert_query, (message_uuid, chat_uuid, user_id, content, role), commit=True)
        
        # Get the created message with explicit fetch_one
        get_message_query = 'SELECT message_id, content, sender_type as role, created_at FROM messages WHERE message_id = %s'
        message = Database.execute_query(get_message_query, (message_uuid), fetch_one=True)
        
        if not message:
            return jsonify({'error': 'Failed to retrieve message'}), 500
        
        # Update chat's updated_at timestamp with explicit commit
        update_query = 'UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE chat_uuid = %s'
        Database.execute_query(update_query, (chat_uuid), commit=True)
        
        return jsonify({
            'id': message['message_id'],
            'content': message['content'],
            'role': message['role'],
            'created_at': message['created_at'].isoformat() if message['created_at'] else None,
            'message': 'Message added successfully'
        }), 201
    except Exception as e:
        import logging
        logging.error(f"Error adding message to chat {chat_uuid}: {e}")
        return jsonify({'error': 'Failed to send message'}), 500


@chat_bp.route('/chats/<chat_uuid>', methods=['DELETE'])
@auth_required
def delete_chat(chat_uuid):
    """Archive a chat"""
    user_id = session.get('user_id')
    
    try:
        # Verify chat belongs to user
        query = 'UPDATE chats SET is_archived = TRUE WHERE chat_uuid = %s AND user_id = %s AND is_archived = FALSE'
        Database.execute_query(query, (chat_uuid, user_id))
        
        return jsonify({'message': 'Chat deleted successfully'}), 200
    except Exception as e:
        import logging
        logging.error(f"Error deleting chat {chat_uuid}: {e}")
        return jsonify({'error': 'Failed to delete chat'}), 500


@chat_bp.route('/chats/<chat_uuid>', methods=['PUT'])
@auth_required
def update_chat(chat_uuid):
    """Update chat title"""
    user_id = session.get('user_id')
    data = request.get_json() or {}
    
    name = data.get('name')
    if not name:
        return jsonify({'error': 'Chat name is required'}), 400
    
    try:
        # Verify chat belongs to user and update
        query = '''
            UPDATE chats 
            SET title = %s, updated_at = CURRENT_TIMESTAMP 
            WHERE chat_uuid = %s AND user_id = %s AND is_archived = FALSE
        '''
        Database.execute_query(query, (name, chat_uuid, user_id))
        
        return jsonify({'message': 'Chat updated successfully', 'name': name}), 200
    except Exception as e:
        import logging
        logging.error(f"Error updating chat {chat_uuid}: {e}")
        return jsonify({'error': 'Failed to update chat'}), 500


@chat_bp.route('/chats/<chat_uuid>/share', methods=['POST'])
@auth_required
def create_share_link(chat_uuid):
    """Create a shareable link for a chat"""
    user_id = session.get('user_id')
    
    try:
        # Verify chat belongs to user
        chat_query = 'SELECT chat_uuid FROM chats WHERE chat_uuid = %s AND user_id = %s AND is_archived = FALSE'
        chat = Database.execute_query(chat_query, (chat_uuid, user_id), fetch_one=True)
        
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        # Check if share link already exists and is active
        existing_share_query = '''
            SELECT share_uuid FROM shared_chats 
            WHERE chat_uuid = %s AND user_id = %s AND is_active = TRUE
        '''
        existing_share = Database.execute_query(existing_share_query, (chat_uuid, user_id), fetch_one=True)
        
        if existing_share:
            return jsonify({
                'share_uuid': existing_share['share_uuid'],
                'message': 'Share link already exists'
            }), 200
        
        # Create new share link
        share_uuid = str(uuid.uuid4())
        insert_query = '''
            INSERT INTO shared_chats (share_uuid, chat_uuid, user_id, is_active) 
            VALUES (%s, %s, %s, TRUE)
        '''
        Database.execute_query(insert_query, (share_uuid, chat_uuid, user_id), commit=True)
        
        return jsonify({
            'share_uuid': share_uuid,
            'message': 'Share link created successfully'
        }), 201
    except Exception as e:
        import logging
        logging.error(f"Error creating share link for chat {chat_uuid}: {e}")
        return jsonify({'error': 'Failed to create share link'}), 500


@chat_bp.route('/chats/<chat_uuid>/share', methods=['DELETE'])
@auth_required
def delete_share_link(chat_uuid):
    """Deactivate a shareable link for a chat"""
    user_id = session.get('user_id')
    
    try:
        # Verify chat belongs to user
        chat_query = 'SELECT chat_uuid FROM chats WHERE chat_uuid = %s AND user_id = %s AND is_archived = FALSE'
        chat = Database.execute_query(chat_query, (chat_uuid, user_id), fetch_one=True)
        
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        # Deactivate share link
        update_query = '''
            UPDATE shared_chats 
            SET is_active = FALSE 
            WHERE chat_uuid = %s AND user_id = %s
        '''
        Database.execute_query(update_query, (chat_uuid, user_id), commit=True)
        
        return jsonify({'message': 'Share link deactivated successfully'}), 200
    except Exception as e:
        import logging
        logging.error(f"Error deleting share link for chat {chat_uuid}: {e}")
        return jsonify({'error': 'Failed to deactivate share link'}), 500


@chat_bp.route('/shared/<share_uuid>', methods=['GET'])
def get_shared_chat(share_uuid):
    """Get a shared chat by share UUID (public route)"""
    try:
        # Check if share link exists and is active
        share_query = '''
            SELECT chat_uuid, view_count 
            FROM shared_chats 
            WHERE share_uuid = %s AND is_active = TRUE
        '''
        share = Database.execute_query(share_query, (share_uuid), fetch_one=True)
        
        if not share:
            return jsonify({'error': 'Share link not found or expired'}), 404
        
        chat_uuid = share['chat_uuid']
        
        # Increment view count
        update_view_query = '''
            UPDATE shared_chats 
            SET view_count = view_count + 1 
            WHERE share_uuid = %s
        '''
        Database.execute_query(update_view_query, (share_uuid), commit=True)
        
        # Get chat details
        chat_query = '''
            SELECT id, chat_uuid, title as name, created_at 
            FROM chats 
            WHERE chat_uuid = %s AND is_archived = FALSE
        '''
        chat = Database.execute_query(chat_query, (chat_uuid), fetch_one=True)
        
        if not chat:
            return jsonify({'error': 'Chat not found'}), 404
        
        # Get chat messages with files
        messages_query = '''
            SELECT 
                m.message_id as id, 
                m.content, 
                m.sender_type as role, 
                m.created_at,
                f.file_uuid,
                f.original_filename as filename,
                f.file_size as size,
                f.mime_type
            FROM messages m
            LEFT JOIN files f ON m.message_id = f.message_id AND f.is_deleted = FALSE
            WHERE m.chat_uuid = %s AND m.is_deleted = FALSE
            ORDER BY m.created_at ASC, f.file_uuid ASC
        '''
        results = Database.execute_query(messages_query, (chat_uuid), fetch_all=True) or []
        
        # Group results by message
        from collections import OrderedDict
        messages_dict = OrderedDict()
        for row in results:
            msg_id = row['id']
            if msg_id not in messages_dict:
                messages_dict[msg_id] = {
                    'id': msg_id,
                    'content': row['content'],
                    'role': row['role'],
                    'created_at': row['created_at'],
                    'files': []
                }
            
            # Add file if it exists
            if row['file_uuid']:
                messages_dict[msg_id]['files'].append({
                    'uuid': row['file_uuid'],
                    'name': row['filename'],
                    'size': row['size'],
                    'url': f'/api/files/{row["file_uuid"]}',
                    'type': row['mime_type']
                })
        
        messages = list(messages_dict.values())
                
        return jsonify({
            'chat': chat,
            'messages': messages,
            'is_shared': True
        }), 200
    except Exception as e:
        import logging
        logging.error(f"Error fetching shared chat {share_uuid}: {e}")
        return jsonify({'error': 'Failed to fetch shared chat'}), 500
