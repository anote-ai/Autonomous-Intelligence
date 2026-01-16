from flask import Blueprint, request, jsonify, Response, session
from werkzeug.utils import secure_filename
import uuid
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from database.db import Database
from utils.auth import auth_required

# Maximum file size: 16MB (must match Flask MAX_CONTENT_LENGTH)
MAX_FILE_SIZE = 16 * 1024 * 1024

MIME_TYPE_EXTENSION_MAP = {
    'text/plain': 'txt',
    'application/pdf': 'pdf',
    'image/png': 'png',
    'image/jpeg': 'jpg',
    'image/gif': 'gif',
    'application/msword': 'doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'application/vnd.ms-excel': 'xls',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    'application/vnd.ms-powerpoint': 'ppt',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
    # Add more as needed
}

file_bp = Blueprint('files', __name__)

# Initialize rate limiter with Redis storage for distributed rate limiting
import os
import redis
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'redis'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    password=os.getenv('REDIS_PASSWORD', None),
    db=2  # Use db=2 for rate limiting (db=0 for cache, db=1 for sessions)
)

redis_password = os.getenv('REDIS_PASSWORD')
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=f"redis://{os.getenv('REDIS_HOST', 'redis')}:{os.getenv('REDIS_PORT', 6379)}/2",
    storage_options={"password": redis_password} if redis_password else {},
    default_limits=["200 per hour"]  # Global default rate limit
)


@file_bp.route('/upload', methods=['POST'])
@auth_required
def upload_file():
    """Handle file upload"""
    try:
        # Get user_id from session (authenticated user)
        user_id = session.get('user_id')
        
        # Validate required fields before file handling
        chat_uuid = request.form.get('chat_uuid') or (request.json.get('chat_uuid') if request.is_json and request.json else None)
        # message_id is optional - only set if provided from the request
        message_id = request.form.get('message_id') or (request.json.get('message_id') if request.is_json and request.json else None)
        
        if not chat_uuid:
            return jsonify({'error': 'chat_uuid is required'}), 400

        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in request'}), 400
        
        file = request.files['file']
        filename = file.filename
        
        # Check if file is selected
        if not filename:
            return jsonify({'error': 'No file selected'}), 400

        # Check for extension
        if '.' not in filename:
            return jsonify({'error': 'File must have an extension'}), 400

        # Validate MIME type is in allowed list
        mime_type = file.mimetype
        if mime_type not in MIME_TYPE_EXTENSION_MAP:
            return jsonify({'error': f'Unsupported MIME type: {mime_type}'}), 400
        
        # Verify file extension matches the declared MIME type
        expected_ext = MIME_TYPE_EXTENSION_MAP[mime_type]
        filename_parts = filename.rsplit('.', 1)
        if len(filename_parts) < 2:
            return jsonify({'error': 'File must have an extension'}), 400
        uploaded_ext = filename_parts[1].lower()

        if uploaded_ext != expected_ext:
            return jsonify({'error': f'File extension does not match MIME type. Expected: {expected_ext}'}), 400

        # Secure the filename and add unique identifier
        original_filename = secure_filename(filename)
        original_parts = original_filename.rsplit('.', 1)
        if len(original_parts) < 2:
            unique_filename = f"{original_filename}_{uuid.uuid4().hex[:8]}.{expected_ext}"
        else:
            unique_filename = f"{original_parts[0]}_{uuid.uuid4().hex[:8]}.{original_parts[1]}"
        
        # Read file data as bytes
        file_data = file.read()
        file_size = len(file_data)
        
        # Validate file size to prevent database performance issues
        if file_size > MAX_FILE_SIZE:
            return jsonify({'error': f'File size exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)}MB'}), 400
        
        if file_size == 0:
            return jsonify({'error': 'File is empty'}), 400
        
        file_uuid = str(uuid.uuid4())

        # Insert file into database
        insert_query = '''
            INSERT INTO files (
                file_uuid, user_id, chat_uuid, message_id, original_filename, stored_filename, file_data, mime_type, file_type_id, file_size
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        params = (
            file_uuid, user_id, chat_uuid, message_id, original_filename, unique_filename, file_data, mime_type, None, file_size
        )
        
        Database.execute_query(insert_query, params)
        
        return jsonify({
            'uuid': file_uuid,
            'filename': original_filename,
            'size': file_size,
            'url': f'/api/files/{file_uuid}',
            'message': 'File uploaded and stored in database successfully'
        }), 200
    
    except Exception as e:
        import logging
        logging.error(f"Error uploading file: {e}")
        return jsonify({'error': 'Failed to upload file'}), 500
    

@file_bp.route('/files/<file_uuid>', methods=['GET'])
@limiter.limit("50 per minute")  # Limit file downloads to prevent abuse
@auth_required
def get_file_from_db(file_uuid):
    """Serve file stored in the database by file_uuid"""
    try:
        user_id = session.get('user_id')
        
        if not file_uuid: 
            return jsonify({'error': 'Invalid file_uuid provided'}), 404

        # Verify file belongs to user or is accessible to them
        query = "SELECT original_filename, mime_type, file_data FROM files WHERE file_uuid = %s AND user_id = %s AND is_deleted = FALSE"
        result = Database.execute_query(query, (file_uuid, user_id), fetch_one=True)
        if not result:
            return jsonify({'error': 'File not found'}), 404
        
        # Check if download parameter is set, otherwise show inline
        download = request.args.get('download', 'false').lower() == 'true'
        
        return Response(
            result['file_data'],
            mimetype=result['mime_type'],
            headers={
                'Content-Disposition': f"{'attachment' if download else 'inline'}; filename={result['original_filename']}"
            }
        )
    except Exception as e:
        import logging
        logging.error(f"Error retrieving file {file_uuid}: {e}")
        return jsonify({'error': 'Failed to retrieve file'}), 500