import sqlite3
import os
import mysql.connector
from flask import request
import socket
from jwt import InvalidTokenError
from flask_jwt_extended import decode_token
from db_enums import PaidUserStatus
from flask_mail import Message
from constants.global_constants import productHashMap
from constants.global_constants import priceToPaymentPlan
from constants.global_constants import dbName, dbHost, dbUser, dbPassword

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def extractUserEmailFromRequest(request):
    # Get the JWT refresh token from the Authorization header
    authorization_header = request.headers["Authorization"]
    authorization_header_parts = authorization_header.split(" ")

    if len(authorization_header_parts) >= 2:
        jwt_token = authorization_header_parts[1]
        #print("extractUserEmailFromRequest1")

        try:
            #print("extractUserEmailFromRequest2")
            # Try to decode the JWT
            decoded_jwt = decode_token(jwt_token)
            #print("extractUserEmailFromRequest3")
            user_email = decoded_jwt["sub"]
            #print("extractUserEmailFromRequest4")
            print(user_email)
            return user_email
        except InvalidTokenError:
            try:
                session_token = jwt_token
                user_email = user_email_for_session_token(session_token)
                return user_email
            except Exception as e:
                try:
                    api_key = jwt_token
                    if is_api_key_valid(api_key):
                        return user_email_for_api_key(api_key)
                except:
                    raise InvalidTokenError() from e
    else:
        raise InvalidTokenError()

def get_db_connection():
    # print('in db_auth')
    if ('.local' in socket.gethostname() or '.lan' in socket.gethostname() or 'Shadow' in socket.gethostname()) or ('APP_ENV' in os.environ and os.environ['APP_ENV'] == 'local'):
        conn = mysql.connector.connect(
            user='root',
            unix_socket='/tmp/mysql.sock',
            database=dbName,
        )
    else:
        conn = mysql.connector.connect(
            host=dbHost,
            user=dbUser,
            password=dbPassword,
            database=dbName,
        )
    return conn, conn.cursor(dictionary=True)

def user_email_for_session_token(session_token):
    conn, cursor = get_db_connection()
    cursor.execute('SELECT email FROM users WHERE session_token=%s AND session_token_expiration > CURRENT_TIMESTAMP', [session_token])
    user = cursor.fetchone()
    conn.close()
    return user["email"]


def user_email_for_api_key(api_key):
    conn, cursor = get_db_connection()
    cursor.execute('SELECT p.email FROM users p JOIN apiKeys c ON c.user_id=p.id WHERE c.api_key=%s', [api_key])
    user = cursor.fetchone()
    conn.close()
    return user["email"]

def is_session_token_valid(session_token):
    conn, cursor = get_db_connection()
    cursor.execute('SELECT COUNT(*) FROM users WHERE session_token=%s AND session_token_expiration > CURRENT_TIMESTAMP', [session_token])
    user = cursor.fetchone()
    conn.close()
    if user and user["COUNT(*)"] > 0:
        return True
    else:
        return False

def is_api_key_valid(api_key):
    conn, cursor = get_db_connection()
    cursor.execute('SELECT COUNT(*) FROM users p JOIN apiKeys c ON c.user_id=p.id WHERE c.api_key=%s', [api_key])
    user = cursor.fetchone()
    conn.close()
    print(user["COUNT(*)"])
    if user and user["COUNT(*)"] > 0:
        return True
    else:
        return False

def user_id_for_email(email):
    conn, cursor = get_db_connection()
    cursor.execute('SELECT id FROM users WHERE email=%s', [email])
    user = cursor.fetchone()
    conn.close()
    return user["id"]

def paid_user_for_user_email_with_cursor(conn, cursor, user_email):
    cursor.execute('SELECT paid_user FROM Subscriptions gc JOIN StripeInfo c ON c.id=gc.stripe_info_id JOIN users p ON p.id=c.user_id WHERE gc.start_date < CURRENT_TIMESTAMP AND (gc.end_date IS NULL OR gc.end_date > CURRENT_TIMESTAMP) AND p.email = %s', [user_email])
    paidUser = cursor.fetchone()
    if paidUser:
        return paidUser["paid_user"]
    else:
        return 0

# Example of auth function.  You would need to define one that
# fits your SQL schema.
# def sequences_access_invalid(user_id, sequence_id):
#     conn, cursor = get_db_connection()
#     cursor.execute('SELECT COUNT(*) FROM sequences c JOIN lists p ON p.id=c.list_id WHERE c.id=%s AND p.user_id=%s', [sequence_id, user_id])
#     count = cursor.fetchone()
#     access_invalid = True
#     if count["COUNT(*)"] != 0:
#         access_invalid = False
#     conn.close()
#     return access_invalid

def verifyAuthForPaymentsTrustedTesters(user_email):
    return True
    # if user_email in EMAIL_WHITELIST:
    #     print("email in whitelist")
    #     return True
    # else:
    #     print("email not in whitelist")
    #     return False

def send_new_users_alert_email(mail, newSubscriptionsCount):
    msg = Message('Anote Private Chatbot New Users Alert', recipients=[
        "t.clifford@wustl.edu",
        "vidranatan@gmail.com"
    ])
    msg.body = f'{newSubscriptionsCount} users have created paid subscriptions in the last day.  Please check that no abuse is occurring.'
    mail.send(msg)

def verifyAuthForNewSubscriptipns(conn, cursor, mail, userEmail, newPaymentTier):
    # Check for total subscriptions in the last day for the specified tier
    limits = {
        PaidUserStatus.BASIC_TIER: 1000,
        PaidUserStatus.STANDARD_TIER: 500,
        PaidUserStatus.PREMIUM_TIER: 25,
        PaidUserStatus.ENTERPRISE_TIER: 5
    }
    if newPaymentTier not in limits:
        print("verifyAuthForNewSubscriptipns 111111")
        return False

    cursor.execute('SELECT COUNT(*) from Subscriptions WHERE paid_user = %s AND start_date >= NOW() - INTERVAL 1 DAY', [int(newPaymentTier)])
    newUsersCount = cursor.fetchone()
    newSubscriptionsCount = newUsersCount["COUNT(*)"]

    alert_thresholds = {5, 10, 50, 100, 200, 500}
    if newSubscriptionsCount in alert_thresholds:
        send_new_users_alert_email(mail, newSubscriptionsCount)

    if newSubscriptionsCount > limits[newPaymentTier]:
        print("verifyAuthForNewSubscriptipns 22222")
        return False

    # Check if user changed subscriptions more than once in the past month
    cursor.execute('''
        SELECT COUNT(*)
        from Subscriptions s
        JOIN StripeInfo c ON c.id = s.stripe_info_id
        JOIN users p ON p.id = c.user_id
        WHERE p.email = %s AND s.start_date >= NOW() - INTERVAL 1 MONTH
    ''', [userEmail])
    userChangesCount = cursor.fetchone()
    if userChangesCount["COUNT(*)"] > 1:
        print("verifyAuthForNewSubscriptipns 33333")
        return False
    print("verifyAuthForNewSubscriptipns 44444")
    return True

def verifyAuthForCheckoutSession(userEmail, mail):
    conn, cursor = get_db_connection()
    paid_user = paid_user_for_user_email_with_cursor(conn, cursor, userEmail)
    if paid_user == PaidUserStatus.FREE_TIER:
        new_price_id = productHashMap[request.json["product_hash"]]
        if verifyAuthForNewSubscriptipns(conn, cursor, mail, userEmail, priceToPaymentPlan[new_price_id]) == False:
            conn.close()
            return False
        conn.close()
        return True
    else:
        return False

def verifyAuthForPortalSession(request, userEmail, mail):
    conn, cursor = get_db_connection()

    # Fetching user's paid level
    paidLevel = paid_user_for_user_email_with_cursor(conn, cursor, userEmail)
    if paidLevel == 0:
        print("paind level 0")
        conn.close()
        return False

    newPaymentTier = request.json["paymentTier"]
    if newPaymentTier == 0:  # Canceling
        print("new paid level 0")
        conn.close()
        return True

    if verifyAuthForNewSubscriptipns(conn, cursor, mail, userEmail, newPaymentTier) == False:
        print("no verifyAuthForNewSubscriptipns")
        conn.close()
        return False

    if paidLevel == 1:
        if newPaymentTier == 2 or newPaymentTier == 3:
            print("path 111111")
            conn.close()
            return True
    elif paidLevel == 2:
        if newPaymentTier == 1 or newPaymentTier == 3:
            print("path 22222222")
            conn.close()
            return True
    elif paidLevel == 3:
        if newPaymentTier == 1 or newPaymentTier == 2:
            print("path 333333")
            conn.close()
            return True

    print("path end")

    conn.close()
    return False

def api_key_access_invalid(user_id, api_key_id):
    conn, cursor = get_db_connection()
    cursor.execute('SELECT COUNT(*) FROM apiKeys WHERE user_id=%s AND id=%s', [user_id, api_key_id])
    count = cursor.fetchone()
    conn.close()
    if(count["COUNT(*)"] != 0):
        return False
    return True