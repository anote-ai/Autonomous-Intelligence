from flask import jsonify
import secrets
import string
from datetime import datetime
from database.db import user_for_credentials, update_session_token_for_user, get_salt_for_email, user_exists, create_user_from_credentials, update_user_credentials, verify_password_reset_code, update_password_reset_token
import bcrypt
import re
from flask_mail import Message

def LoginHandler(request):
    email = request.args.get('email')
    password = request.args.get('password')
    salt = get_salt_for_email(email)
    if salt:
        hashed_password = hash_password_with_salt(password, salt)
        user = user_for_credentials(email, hashed_password)
    else:
        user = None
    if user:
        NOW = datetime.now()

        if user["session_token_expiration"] >= NOW:
            token = user["session_token"]
        else:
            token = generate_session_token(length=32)
            update_session_token_for_user(email, token)

        return jsonify({
            "status": "OK",
            "token": token
        })
    else:
        return jsonify({
            "status": "Either account does not exist or password is wrong"
        })

def SignUpHandler(request):
    email = request.json["email"]
    password = request.json["password"]

    if not validate_email(email):
        return jsonify({
            "status": "Invalid email format"
        })

    isOk, message = validate_password(password)
    if not isOk:
        return jsonify({
            "status": message
        })

    user = user_exists(email)

    if user:
        return jsonify({
            "status": "User already exists"
        })
    else:
        token = generate_session_token(length=32)
        hashed_password, salt = hash_password(password)

        create_user_from_credentials(email, hashed_password, salt, token)

        return jsonify({
            "status": "OK",
            "token": token
        })

def ForgotPasswordHandler(request, mail):
    email = request.json["email"]
    if user_exists(email):
        host = request.referrer or "https://chat.anote.ai"
        # Generate and send the password reset email
        msg = Message('Anote Private Chatbot Password Reset', recipients=[email])
        generated_token = generate_session_token()
        update_password_reset_token(email, generated_token)
        reset_link = f'{host}?email={email}&passwordResetCode={generated_token}'
        msg.body = f'Here is your password reset link.  This is valid for 15 minutes or until another code is generated: {reset_link}'
        mail.send(msg)

    return jsonify({
        "status": "OK",
    })

def ResetPasswordHandler(request):
    email = request.json["email"]
    passwordResetCode = request.json["passwordResetCode"]
    password = request.json["password"]

    if not verify_password_reset_code(email, passwordResetCode):
        return jsonify({
        "status": "Invalid password reset code",
    })

    isOk, message = validate_password(password)
    if not isOk:
        return jsonify({
            "status": message
        })

    token = generate_session_token(length=32)
    hashed_password, salt = hash_password(password)

    update_user_credentials(email, hashed_password, salt, token)

    return jsonify({
        "status": "OK",
        "token": token
    })

def hash_password(password):
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8'), salt

def hash_password_with_salt(password, salt):
    # Generate a salt and hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt.encode('utf-8'))
    return hashed_password.decode('utf-8')

def generate_session_token(length=32):
    """Generate a random session token."""
    chars = string.ascii_letters + string.digits
    session_token = ''.join(secrets.choice(chars) for _ in range(length))
    return session_token


def validate_password(password):
    if not validate_password_less_than_8(password):
        return False, "Password should be at least 8 characters long"
    if not validate_password_letter(password):
        return False, "Password should contain at least one letter"
    if not validate_password_number(password):
        return False, "Password should contain at least one number"
    return True, ""

def validate_email(email):
    # Use regular expression to validate email format
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if not re.match(pattern, email):
        return False
    return True

def validate_password_less_than_8(password):
    if len(password) < 8:
        return False
    return True

def validate_password_letter(password):
    if not any(char.isalpha() for char in password):
        return False
    return True

def validate_password_number(password):
    if not any(char.isdigit() for char in password):
        return False
    return True