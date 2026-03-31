import json
import os
import secrets
import time
import uuid
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from flask import jsonify

from constants.global_constants import (
    chatgptLimit,
    kPasswordResetExpirationTime,
    kSessionTokenExpirationTime,
    planToCredits,
)
from db_enums import PaidUserStatus
from database.db_pool import get_db_connection


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def create_7_day_free_trial(user_id):
    conn, cursor = get_db_connection()
    cursor.execute("INSERT INTO StripeInfo (user_id) VALUES (%s)", [user_id])
    cursor.execute("SELECT LAST_INSERT_ID()")
    stripe_info_id = cursor.fetchone()["LAST_INSERT_ID()"]
    end_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('INSERT INTO Subscriptions (stripe_info_id, subscription_id, end_date, paid_user, is_free_trial) VALUES (%s, %s, %s, 1, 1)', [stripe_info_id, "id", end_date])
    conn.commit()
    conn.close()

def create_user_if_does_not_exist(email, google_id, person_name, profile_pic_url):
    conn, cursor = get_db_connection()
    cursor.execute('SELECT COUNT(*), id FROM users WHERE email=%s GROUP BY id', [email])
    count = cursor.fetchone()
    user_id = -1
    if count is None or count["COUNT(*)"] == 0:
        # Create new user with 20 credits by default
        cursor.execute('INSERT INTO users (credits, email, google_id, person_name, profile_pic_url) VALUES (100, %s,%s,%s,%s)', [email, google_id, person_name, profile_pic_url])
        row = cursor.fetchone()
        conn.commit()
        conn.close()
        user_id = cursor.lastrowid
        create_7_day_free_trial(user_id)
    else:
        user_id = count["id"]

    return user_id

def user_for_credentials(email, password_hash):
    conn, cursor = get_db_connection()
    cursor.execute('SELECT * FROM users WHERE email = %s AND password_hash = %s', [email, password_hash])
    return cursor.fetchone()

def get_salt_for_email(email):
    conn, cursor = get_db_connection()
    cursor.execute('SELECT salt FROM users WHERE email = %s', [email])
    salt = cursor.fetchone()
    if salt and salt["salt"]:
        return salt["salt"]
    else:
        return None

def user_exists(email):
    conn, cursor = get_db_connection()
    cursor.execute('SELECT * FROM users WHERE email = %s', [email])
    return cursor.fetchone()

def create_user_from_credentials(email, password_hash, salt, session_token):
    conn, cursor = get_db_connection()
    NOW = datetime.now()
    expiration_limit = NOW + kSessionTokenExpirationTime
    cursor.execute('INSERT INTO users (email, password_hash, session_token, session_token_expiration, salt) VALUES (%s, %s, %s, %s, %s)', [email, password_hash, session_token, expiration_limit, salt])
    conn.commit()
    conn.close()

def update_session_token_for_user(email, session_token):
    conn, cursor = get_db_connection()
    NOW = datetime.now()
    expiration_limit = NOW + kSessionTokenExpirationTime
    cursor.execute("UPDATE users SET session_token = %s , session_token_expiration = %s WHERE email = %s", [session_token, expiration_limit, email])
    conn.commit()
    conn.close()

def update_user_credentials(email, hashed_password, salt, token):
    conn, cursor = get_db_connection()

    NOW = datetime.now()
    expiration_limit = NOW + kSessionTokenExpirationTime
    cursor.execute("UPDATE users SET password_hash = %s, salt = %s, session_token = %s , session_token_expiration = %s WHERE email = %s", [hashed_password, salt, token, expiration_limit, email])

    conn.commit()
    conn.close()

def verify_password_reset_code(email, passwordResetCode):
    conn, cursor = get_db_connection()
    isVerified = False
    NOW = datetime.now()
    cursor.execute("SELECT * FROM users WHERE email = %s AND password_reset_token = %s AND password_reset_token_expiration > %s", [email, passwordResetCode, NOW])
    users = cursor.fetchall()
    if len(users) > 0:
        isVerified = True
    conn.close()
    return isVerified

def update_password_reset_token(email, generated_token):
    conn, cursor = get_db_connection()

    NOW = datetime.now()
    expiration_limit = NOW + kPasswordResetExpirationTime
    cursor.execute("UPDATE users SET password_reset_token = %s , password_reset_token_expiration = %s WHERE email = %s", [generated_token, expiration_limit, email])

    conn.commit()
    conn.close()

def paid_user_for_user_email_with_cursor(conn, cursor, user_email):
    cursor.execute('SELECT gc.paid_user FROM Subscriptions gc JOIN StripeInfo c ON c.id=gc.stripe_info_id JOIN users p ON p.id=c.user_id WHERE gc.start_date < CURRENT_TIMESTAMP AND (gc.end_date IS NULL OR gc.end_date > CURRENT_TIMESTAMP) AND p.email = %s ORDER BY gc.start_date ASC LIMIT 1', [user_email])
    paidUser = cursor.fetchone()
    if paidUser:
        return paidUser["paid_user"]
    else:
        return 0

def is_free_trial_for_user_email_with_cursor(conn, cursor, user_email):
    cursor.execute('SELECT gc.is_free_trial FROM Subscriptions gc JOIN StripeInfo c ON c.id=gc.stripe_info_id JOIN users p ON p.id=c.user_id WHERE gc.start_date < CURRENT_TIMESTAMP AND (gc.end_date IS NULL OR gc.end_date > CURRENT_TIMESTAMP) AND p.email = %s ORDER BY gc.start_date ASC LIMIT 1', [user_email])
    paidUser = cursor.fetchone()
    if paidUser:
        return (paidUser["is_free_trial"] == 1)
    else:
        return False

def end_date_for_user_email_with_cursor(conn, cursor, user_email):
    cursor.execute('SELECT gc.end_date FROM Subscriptions gc JOIN StripeInfo c ON c.id=gc.stripe_info_id JOIN users p ON p.id=c.user_id WHERE gc.start_date < CURRENT_TIMESTAMP AND (gc.end_date IS NULL OR gc.end_date > CURRENT_TIMESTAMP) AND p.email = %s ORDER BY gc.start_date ASC LIMIT 1', [user_email])
    paidUser = cursor.fetchone()
    if paidUser:
        return paidUser["end_date"]
    else:
        return None

def refresh_credits(user_email):
    conn, cursor = get_db_connection()
    cursor.execute("SELECT credits, credits_updated, id FROM users WHERE email = %s", (user_email,))
    result = cursor.fetchone()

    cursor.execute("SELECT c.anchor_date FROM StripeInfo c JOIN users p ON c.user_id=p.id WHERE p.id = %s", [result["id"]])
    anchorDateDb = cursor.fetchone()
    if (not anchorDateDb) or (not anchorDateDb["anchor_date"]):
        # If no active subscriptions -> reset, else: do nothing
        noActiveSubscriptions = True
        cursor.execute("SELECT COUNT(*) FROM Subscriptions gc JOIN StripeInfo c ON gc.stripe_info_id=c.id JOIN users p ON p.id=c.user_id WHERE p.email = %s AND gc.start_date < CURRENT_TIMESTAMP AND (gc.end_date IS NULL OR gc.end_date > CURRENT_TIMESTAMP)", (user_email,))
        subCount = cursor.fetchone()
        if subCount and subCount["COUNT(*)"] > 0:
            noActiveSubscriptions = False
        if noActiveSubscriptions:
            if result["credits"] > 0:
                cursor.execute("UPDATE users SET credits=0, credits_updated=CURRENT_TIMESTAMP WHERE id=%s", [result["id"]])
                conn.commit()
            conn.close()
            print("refresh_credits1")
            return {
                "numCredits": 0
            }
        else:
            return {
                "numCredits": result["credits"]
            }

    previousAnchorDate = previous_anchor_time_for_user_with_cursor(conn, cursor, result["id"])
    cursor.execute("""
        SELECT S.*
        FROM Subscriptions S
        JOIN StripeInfo SI ON S.stripe_info_id = SI.id
        JOIN users U ON SI.user_id = U.id
        WHERE U.email = %s
        AND S.start_date < CURRENT_TIMESTAMP AND (S.end_date IS NULL OR S.end_date > CURRENT_TIMESTAMP)
        ORDER BY S.start_date DESC
    """, (user_email,))
    subscriptions = cursor.fetchall()
    if len(subscriptions) == 0:
        if result["credits"] > 0:
             cursor.execute("UPDATE users SET credits=0, credits_updated=CURRENT_TIMESTAMP WHERE id=%s", [result["id"]])
             conn.commit()
        conn.close()
        print("refresh_credits2")
        return {
            "numCredits": 0
        }
    else:
        sub = subscriptions[0]
        if sub["is_free_trial"] == 1:
            if not result["credits_updated"] or sub["start_date"] >= result["credits_updated"]:
                numCredits = planToCredits[sub["paid_user"]]
                cursor.execute("UPDATE users SET credits=%s, credits_updated=CURRENT_TIMESTAMP WHERE id=%s", [numCredits, result["id"]])
                conn.commit()
                conn.close()
                print("refresh_credits33")
                return {
                    "numCredits": numCredits
                }
        else:
            if not result["credits_updated"] or previousAnchorDate >= result["credits_updated"]:
                numCredits = planToCredits[sub["paid_user"]]
                cursor.execute("UPDATE users SET credits=%s, credits_updated=CURRENT_TIMESTAMP WHERE id=%s", [numCredits, result["id"]])
                conn.commit()
                conn.close()
                print("refresh_credits3")
                return {
                    "numCredits": numCredits
                }
        conn.commit()
        conn.close()
        print("refresh_credits4")
        return {
            "numCredits": result["credits"]
        }

# Billing

def add_subscription(subscription, user_id, customer_id, payment_plan, free_trial_end):
    conn, cursor = get_db_connection()
    try:
        cursor.execute("SELECT id, stripe_customer_id, anchor_date FROM StripeInfo WHERE user_id=%s", [user_id])
        stripe_info_id_db = cursor.fetchone()
        if stripe_info_id_db:
            stripe_info_id = stripe_info_id_db["id"]
            if not stripe_info_id_db["stripe_customer_id"]:
                cursor.execute("UPDATE StripeInfo SET stripe_customer_id = %s WHERE id=%s", [customer_id, stripe_info_id])
        else:
            cursor.execute("INSERT INTO StripeInfo (user_id, stripe_customer_id) VALUES (%s, %s)", (user_id, customer_id))
            cursor.execute("SELECT LAST_INSERT_ID()")
            stripe_info_id = cursor.fetchone()["LAST_INSERT_ID()"]

        cursor.execute("SELECT COUNT(*) FROM Subscriptions c JOIN StripeInfo p ON c.stripe_info_id=p.id WHERE p.user_id=%s AND c.start_date < CURRENT_TIMESTAMP AND (c.end_date IS NULL OR c.end_date > CURRENT_TIMESTAMP)", [user_id])
        activePaidSubscriptions = cursor.fetchone()
        if activePaidSubscriptions["COUNT(*)"] == 0:
            if free_trial_end:
                cursor.execute("UPDATE StripeInfo SET anchor_date = %s WHERE user_id = %s", [free_trial_end, user_id])
            else:
                cursor.execute("UPDATE StripeInfo SET anchor_date = CURRENT_TIMESTAMP WHERE user_id = %s", [user_id])
        elif not stripe_info_id_db["anchor_date"]:
            cursor.execute("SELECT id FROM Subscriptions c JOIN StripeInfo p ON c.stripe_info_id=p.id WHERE p.user_id=%s AND c.start_date < CURRENT_TIMESTAMP AND (c.end_date IS NULL OR c.end_date > CURRENT_TIMESTAMP)", [user_id])
            activePaidSubscriptionDbs = cursor.fetchall()
            for activePaidSubscriptionDb in activePaidSubscriptionDbs:
                cursor.execute("UPDATE Subscriptions SET end_date = CURRENT_TIMESTAMP WHERE id = %s", [activePaidSubscriptionDb["id"]])
            cursor.execute("UPDATE StripeInfo SET anchor_date = CURRENT_TIMESTAMP WHERE user_id = %s", [user_id])

        if free_trial_end:
            cursor.execute("INSERT INTO Subscriptions (stripe_info_id, subscription_id, paid_user, is_free_trial, end_date) VALUES (%s, %s, %s, %s, %s)", [stripe_info_id, subscription['id'], int(payment_plan), 1, free_trial_end])
            cursor.execute("INSERT INTO Subscriptions (stripe_info_id, subscription_id, paid_user, is_free_trial, start_date) VALUES (%s, %s, %s, %s, %s)", [stripe_info_id, subscription['id'], int(payment_plan), 0, free_trial_end])
        else:
            cursor.execute("INSERT INTO Subscriptions (stripe_info_id, subscription_id, paid_user, is_free_trial) VALUES (%s, %s, %s, %s)", [stripe_info_id, subscription['id'], int(payment_plan), 0])

        conn.commit()
    finally:
        conn.close()

def delete_subscription(subscription):
    conn, cursor = get_db_connection()

    try:
        print(subscription['id'])
        # print("SELECT p.user_id FROM StripeInfo p JOIN Subscriptions c ON p.id=c.stripe_info_id WHERE c.subscription_id = %s" + subscription['id'])
        cursor.execute("SELECT p.user_id FROM StripeInfo p JOIN Subscriptions c ON p.id=c.stripe_info_id WHERE c.subscription_id = %s LIMIT 1", [subscription['id']])
        # cursor.execute("SELECT user_id FROM StripeInfo WHERE id = (SELECT stripe_info_id FROM Subscriptions WHERE subscription_id = %s)", (subscription['id'],))
        user_id = cursor.fetchone()["user_id"]

        cursor.execute("SELECT is_free_trial FROM Subscriptions WHERE subscription_id = %s AND start_date < CURRENT_TIMESTAMP AND (end_date IS NULL OR end_date > CURRENT_TIMESTAMP) ORDER BY start_date DESC LIMIT 1", (subscription['id'],))
        activeSubscription = cursor.fetchone()
        if activeSubscription["is_free_trial"] == 1:
            # If active subscription if free trial, make end_date of everything that starts after that Subsription NOW
            cursor.execute("""
                UPDATE Subscriptions SET Subscriptions.end_date = CURRENT_TIMESTAMP
                WHERE subscription_id = %s AND start_date < CURRENT_TIMESTAMP AND (end_date IS NULL OR end_date > CURRENT_TIMESTAMP)
            """, [subscription['id']])
        else:
            # Else, make the end_date of the current active subscripion be the next anchor date
            anchor_time = next_anchor_time_for_user_with_cursor(conn, cursor, user_id)
            cursor.execute("""
                UPDATE Subscriptions SET Subscriptions.end_date = %s
                WHERE subscription_id = %s AND start_date < CURRENT_TIMESTAMP AND (end_date IS NULL OR end_date > CURRENT_TIMESTAMP)
            """, [anchor_time, subscription['id']])

        conn.commit()
    finally:
        conn.close()

def stripe_subscription_for_user(userEmail):
    conn, cursor = get_db_connection()
    cursor.execute("""
        SELECT Subscriptions.subscription_id
        FROM users
        JOIN StripeInfo ON users.id = StripeInfo.user_id
        JOIN Subscriptions ON StripeInfo.id = Subscriptions.stripe_info_id
        WHERE users.email = %s AND (Subscriptions.end_date IS NULL OR Subscriptions.end_date > CURRENT_TIMESTAMP)
        AND Subscriptions.start_date < CURRENT_TIMESTAMP
        AND StripeInfo.anchor_date IS NOT NULL
        ORDER BY Subscriptions.start_date DESC
        LIMIT 1
    """, [userEmail])
    print("stripe_subscription_for_user1")
    subscription = cursor.fetchone()
    print("stripe_subscription_for_user2")
    if subscription:
        print("yes subscription")
        return subscription["subscription_id"]
    else:
        print("not subscription")
        return None

def stripe_customer_for_user(userEmail):
    conn, cursor = get_db_connection()
    cursor.execute("""
        SELECT StripeInfo.stripe_customer_id
        FROM StripeInfo
        JOIN users ON StripeInfo.user_id = users.id
        WHERE users.email = %s
    """, [userEmail])
    print("stripe_customer_for_user1")
    stripe_customer_id = cursor.fetchone()
    print("stripe_customer_for_user2")
    if stripe_customer_id:
        print("yes stripe_customer_id")
        return stripe_customer_id["stripe_customer_id"]
    else:
        print("not stripe_customer_id")
        return None

def next_anchor_time_for_user_with_cursor(conn, cursor, user_id):
    cursor.execute('SELECT c.anchor_date from StripeInfo c JOIN users p ON p.id=c.user_id WHERE p.id = %s', [user_id])
    result = cursor.fetchone()

    if result and result['anchor_date']:
        anchor_date = result['anchor_date']
        now = datetime.now()
        # Create a target date based on current month and anchor day
        try:
            target_date = datetime(now.year, now.month, anchor_date.day, anchor_date.hour, anchor_date.minute, anchor_date.second)
        except ValueError:  # This will be triggered when the day isn't in the current month
            # If this month doesn't have the same day as the anchor_date, get the last day of this month
            next_month_start = (now.replace(day=1) + relativedelta(months=1)).replace(hour=anchor_date.hour, minute=anchor_date.minute, second=anchor_date.second)
            target_date = next_month_start - timedelta(days=1)

        # If today's date is after the target_date, compute the next month's target_date
        if now > target_date:
            try:
                target_date = datetime(now.year, now.month + 1, anchor_date.day, anchor_date.hour, anchor_date.minute, anchor_date.second)
            except ValueError:
                next_month_start = (now.replace(day=1) + relativedelta(months=2)).replace(hour=anchor_date.hour, minute=anchor_date.minute, second=anchor_date.second)
                target_date = next_month_start - timedelta(days=1)

        return target_date
    else:
        return None

def previous_anchor_time_for_user_with_cursor(conn, cursor, user_id):
    cursor.execute('SELECT c.anchor_date from StripeInfo c JOIN users p ON p.id=c.user_id WHERE p.id = %s', [user_id])
    result = cursor.fetchone()

    if result and result['anchor_date']:
        # Ensure anchor_date is a datetime object
        if isinstance(result['anchor_date'], datetime):
            anchor_date = result['anchor_date']
        else:
            # Convert to datetime object if necessary
            # You may need to adjust this depending on the expected format of anchor_date
            anchor_date = datetime.strptime(result['anchor_date'], '%Y-%m-%d %H:%M:%S')

        now = datetime.now()

        # Create a target date based on current month and anchor day
        try:
            target_date = datetime(now.year, now.month, anchor_date.day, anchor_date.hour, anchor_date.minute, anchor_date.second)
        except ValueError:  # This will be triggered when the day isn't in the current month
            # If this month doesn't have the same day as the anchor_date, get the last day of the previous month
            target_date = datetime(now.year, now.month, 1, anchor_date.hour, anchor_date.minute, anchor_date.second) - relativedelta(days=1)

        # If the target date is still in the future, subtract a month
        if target_date > now:
            target_date = target_date - relativedelta(months=1)
        return target_date
    else:
        return None

def next_anchor_time_for_user(user_id):
    conn, cursor = get_db_connection()
    next_time = next_anchor_time_for_user_with_cursor(conn, cursor, user_id)
    conn.close()
    return next_time

def view_user(user_email):
    conn, cursor = get_db_connection()
    try:
        cursor.execute('SELECT * FROM users WHERE email = %s LIMIT 1', [user_email])
        user = cursor.fetchone()
        if not user:
            return {"error": "User not found"}, 404

        # Stripe anchor date → next credits refresh
        cursor.execute('SELECT anchor_date FROM StripeInfo WHERE user_id = %s', [user["id"]])
        stripe_info = cursor.fetchone()
        credits_refresh_str = None
        if stripe_info and stripe_info["anchor_date"]:
            refresh_date = next_anchor_time_for_user_with_cursor(conn, cursor, user["id"])
            if refresh_date:
                credits_refresh_str = refresh_date.strftime('%Y-%m-%d')

        paid_level = paid_user_for_user_email_with_cursor(conn, cursor, user_email)

        # Future plan
        cursor.execute('''
            SELECT c.paid_user
            FROM Subscriptions c
            JOIN StripeInfo p ON p.id = c.stripe_info_id
            WHERE p.user_id = %s
              AND c.end_date IS NULL
              AND c.start_date > CURRENT_TIMESTAMP
            ORDER BY c.start_date DESC
            LIMIT 1
        ''', [user["id"]])
        next_plan = (cursor.fetchone() or {}).get("paid_user")

        # End date + free trial
        end_date = end_date_for_user_email_with_cursor(conn, cursor, user_email)
        end_date_str = end_date.strftime("%Y-%m-%d") if end_date else None
        is_free_trial = is_free_trial_for_user_email_with_cursor(conn, cursor, user_email)

        return jsonify({
            "id": user["id"],
            "name": user["person_name"],
            "email": user["email"],
            "paid_user": paid_level,
            "credits": user['credits'],
            "is_free_trial": is_free_trial,
            "next_plan": next_plan,
            "end_date": end_date_str,
            "credits_refresh": credits_refresh_str,
            "profile_pic_url": user["profile_pic_url"],
        })
    finally:
        conn.close()


def config_for_payment_tiers(userEmail, newPaymentTier):
    conn, cursor = get_db_connection()
    paidLevel = paid_user_for_user_email_with_cursor(conn, cursor, userEmail)
    conn.close()
    config = ""
    upgrade_to_standard = "bpc_1Ne99AAuWN19h35KDOIITw1Z"
    upgrade_to_premier = "bpc_1Ne99AAuWN19h35K7QhZh9OY"
    downgrade_to_basic = "bpc_1Ne99BAuWN19h35KE5oEz0u9"
    downgrade_to_standard = "bpc_1Ne99BAuWN19h35KnutfEQEw"
    if newPaymentTier == PaidUserStatus.FREE_TIER:
        config = "bpc_1NZVKQAuWN19h35KGJb9PeiP"
    elif paidLevel == PaidUserStatus.BASIC_TIER:
        if newPaymentTier == PaidUserStatus.STANDARD_TIER:
            config = upgrade_to_standard
        elif newPaymentTier == PaidUserStatus.PREMIUM_TIER:
            config = upgrade_to_premier
    elif paidLevel == PaidUserStatus.STANDARD_TIER:
        if newPaymentTier == PaidUserStatus.BASIC_TIER:
            config = downgrade_to_basic
        elif newPaymentTier == PaidUserStatus.PREMIUM_TIER:
            config = upgrade_to_premier
    elif paidLevel == PaidUserStatus.PREMIUM_TIER:
        if newPaymentTier == PaidUserStatus.BASIC_TIER:
            config = downgrade_to_basic
        elif newPaymentTier == PaidUserStatus.STANDARD_TIER:
            config = downgrade_to_standard
    return config

def user_has_free_trial(userEmail, free_trial_code):
    conn, cursor = get_db_connection()

    print("user_has_free_trial1")
    inFreetrialAllowlist = False
    inFreeTrialsAccessedAlready = False
    cursor.execute('''
        SELECT id
        FROM freeTrialAllowlist
        WHERE email = %s AND token = %s AND token_expiration > CURRENT_TIMESTAMP LIMIT 1
    ''', [userEmail, free_trial_code])
    print("user_has_free_trial2")

    freeTrialAllowlist = cursor.fetchone()
    print("user_has_free_trial3")
    if freeTrialAllowlist:
        print("user_has_free_trial4")
        inFreetrialAllowlist = True
    else:
        print("user_has_free_trial5")
        cursor.execute('''
            SELECT id, max_non_email_count
            FROM freeTrialAllowlist
            WHERE token = %s AND token_expiration > CURRENT_TIMESTAMP LIMIT 1
        ''', [free_trial_code])
        print("user_has_free_trial6")
        freeTrialAllowlist = cursor.fetchone()
        print("user_has_free_trial7")
        if freeTrialAllowlist:
            print("user_has_free_trial8")
            cursor.execute('''
                SELECT COUNT(*)
                FROM freeTrialsAccessed
                WHERE free_trial_allow_list_id = %s
            ''', [freeTrialAllowlist["id"]])
            print("user_has_free_trial9")
            freeTrialAllowlistCount = cursor.fetchone()
            print("user_has_free_trial10")
            if freeTrialAllowlistCount["COUNT(*)"] < freeTrialAllowlist["max_non_email_count"]:
                print("user_has_free_trial11")
                inFreetrialAllowlist = True
        if not inFreetrialAllowlist and freeTrialAllowlist:
            cursor.execute('''
                SELECT c.id
                FROM freeTrialsAccessed c JOIN users p ON c.user_id=p.id
                WHERE c.free_trial_allow_list_id = %s AND p.email=%s LIMIT 1
            ''', [freeTrialAllowlist["id"], userEmail])
            freeTrialsAccessed = cursor.fetchone()
            if freeTrialsAccessed:
                inFreeTrialsAccessedAlready = True
    if inFreetrialAllowlist or inFreeTrialsAccessedAlready:
        print("user_has_free_trial12")
        cursor.execute('''
            SELECT gc.id
            FROM users p
            JOIN StripeInfo c ON c.user_id=p.id
            JOIN Subscriptions gc ON gc.stripe_info_id = c.id
            WHERE p.email = %s
        ''', [userEmail])
        print("user_has_free_trial13")
        subscriptions = cursor.fetchall()
        print("user_has_free_trial14")
        if len(subscriptions) > 0:
            print("user_has_free_trial15")
            conn.close()
            return False
        else:
            print("user_has_free_trial16")
            # Fetch user_id for given email
            cursor.execute('SELECT id FROM users WHERE email = %s', [userEmail])
            print("user_has_free_trial17")
            user_id = cursor.fetchone()
            print("user_has_free_trial18")
            if user_id:
                print("user_has_free_trial19")
                user_id = user_id["id"]
                print("user_has_free_trial20")
                # Insert into freeTrialsAccessed if not exists
                if not inFreeTrialsAccessedAlready:
                    cursor.execute('''
                        INSERT INTO freeTrialsAccessed (free_trial_allow_list_id, user_id)
                        VALUES (%s, %s)
                    ''', [freeTrialAllowlist["id"], user_id])
                    print("user_has_free_trial21")
                    conn.commit()

            conn.close()
            return True
    else:
        print("user_has_free_trial22")
        conn.close()
        return False

def user_email_for_id(id):
    conn, cursor = get_db_connection()
    cursor.execute("SELECT email FROM users WHERE id = %s", [id])
    email = cursor.fetchone()
    cursor.close()
    conn.close()
    return email["email"]

def user_email_for_customer_id(id):
    conn, cursor = get_db_connection()
    cursor.execute("SELECT p.email FROM Subscriptions gc JOIN StripeInfo c ON c.id=gc.stripe_info_id JOIN users p ON p.id=c.user_id WHERE c.stripe_customer_id = %s", [id])
    email = cursor.fetchone()
    cursor.close()
    conn.close()
    return email["email"]

def no_subscriptions_with_end_date_null(user_email):
    conn, cursor = get_db_connection()
    cursor.execute("SELECT COUNT(*) FROM Subscriptions gc JOIN StripeInfo c ON c.id=gc.stripe_info_id JOIN users p ON p.id=c.user_id WHERE p.email = %s AND gc.end_date IS NULL", [user_email])
    emailCount = cursor.fetchone()
    cursor.close()
    conn.close()
    if not emailCount or emailCount["COUNT(*)"] == 0:
        return True
    else:
        return False

def check_and_debit_gpt_credit_with_cursor(conn, cursor, userEmail, numCredits):
    isOk = False
    cursor.execute("SELECT num_chatgpt_requests, chat_gpt_date FROM users WHERE email=%s", [userEmail])
    numRequests = cursor.fetchone()
    chatgpt_date = numRequests["chat_gpt_date"]
    num_chatgpt_requests = numRequests["num_chatgpt_requests"]
    if (chatgpt_date.month < datetime.now().month and chatgpt_date.year <= datetime.now().year) or (chatgpt_date.year < datetime.now().year):
        cursor.execute("UPDATE users SET chat_gpt_date=%s, num_chatgpt_requests=1 WHERE email = %s", [datetime.now(), userEmail])
        return True

    if num_chatgpt_requests <= chatgptLimit:
        isOk = True
        cursor.execute("UPDATE users SET num_chatgpt_requests=%s WHERE email=%s", [num_chatgpt_requests + numCredits, userEmail])
    return isOk

def check_and_debit_gpt_credit(userEmail, numCredits):
    conn, cursor = get_db_connection()
    isOk = check_and_debit_gpt_credit_with_cursor(conn, cursor, userEmail, numCredits)
    conn.commit()
    conn.close()
    return isOk


def deduct_credits_from_user(user_email, credits_to_deduct=1):
    """
    Deduct credits from a user by email.
    
    Args:
        user_email (str): The user's email
        credits_to_deduct (int): Number of credits to deduct (default: 1)
    """
    
    if credits_to_deduct < 0:
        return False
        
    conn, cursor = get_db_connection()
    try:
        # Atomic update with credit check
        cursor.execute('''
            UPDATE users 
            SET credits = credits - %s 
            WHERE email = %s AND credits >= %s
        ''', [credits_to_deduct, user_email, credits_to_deduct])
        
        if cursor.rowcount == 0:
            return False
            
        # Get new balance for logging
        cursor.execute('SELECT credits FROM users WHERE email = %s', [user_email])
        result = cursor.fetchone()
        new_credits = result["credits"] if result else 0
        
        conn.commit()
        print(f"Deducted {credits_to_deduct} credits from user {user_email}. New balance: {new_credits}")
        return True
    finally:
        conn.close()

def generate_api_key(email, key_name=None):
    print(f"generate_api_key called with email: {email}, key_name: {key_name}")
    conn, cursor = get_db_connection()
    api_key = secrets.token_hex(16)
    
    print(f"Executing query: SELECT id from users WHERE email = '{email}'")
    cursor.execute('SELECT id from users WHERE email = %s', [email])
    userId = cursor.fetchone()
    print(f"Query result: {userId}")
    
    if userId is None:
        conn.close()
        raise ValueError(f"User with email {email} not found")
    
    userIdStr = userId["id"]
    time = datetime.now()
    
    # Use provided name or default to None
    if key_name is None:
        key_name = "Untitled Key"
    
    print(f"Inserting API key with user_id: {userIdStr}, key_name: {key_name}")
    # Insert the generated API key into the apiKeys table
    cursor.execute('INSERT INTO apiKeys (user_id, api_key, created, key_name) VALUES (%s, %s, %s, %s)', (userIdStr, api_key, time, key_name))
    cursor.execute('SELECT LAST_INSERT_ID()')
    keyId = cursor.fetchone()["LAST_INSERT_ID()"]
    conn.commit()
    conn.close()
    
    result = {
        "id": keyId,
        "key": api_key,
        "created": time,
        "last_used": None,
        "name": key_name
    }
    print(f"Returning result: {result}")
    return result

def delete_api_key(api_key_id):
    conn, cursor = get_db_connection()

    # Delete the API key from the apiKeys table based on the provided API key ID
    cursor.execute('DELETE FROM apiKeys WHERE id = %s', (api_key_id,))

    conn.commit()
    conn.close()

def get_api_keys(email):
    conn, cursor = get_db_connection()

    # Get the user ID based on the provided email
    cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
    userId = cursor.fetchone()
    userIdStr = userId["id"]

    # Get the API keys associated with the user ID from the apiKeys table
    cursor.execute('SELECT id, api_key, created, last_used, key_name FROM apiKeys WHERE user_id = %s', (userIdStr,))
    keysDb = cursor.fetchall()
    keys = []
    for keyDb in keysDb:
        keys.append({
            "id": keyDb["id"],
            "key": keyDb["api_key"],
            "created": keyDb["created"],
            "last_used": keyDb["last_used"],
            "name": keyDb["key_name"] or "Untitled Key"
        })
    conn.close()

    return {
        "keys": keys
    }


def add_chat(user_email, chat_type, model_type):
    conn, cursor = get_db_connection()
    cursor.execute("SELECT id FROM users WHERE email = %s", [user_email])
    user_id = cursor.fetchone()["id"]

    cursor.execute(
        "INSERT INTO chats (user_id, model_type, associated_task) VALUES (%s, %s, %s)",
        (user_id, model_type, chat_type),
    )
    chat_id = cursor.lastrowid
    cursor.execute("UPDATE chats SET chat_name = %s WHERE id = %s", (f"Chat {chat_id}", chat_id))

    conn.commit()
    cursor.close()
    conn.close()
    return chat_id


def update_chat_name(user_email, chat_id, new_name):
    conn, cursor = get_db_connection()
    query = """
    UPDATE chats
    JOIN users ON chats.user_id = users.id
    SET chats.chat_name = %s
    WHERE chats.id = %s AND users.email = %s;
    """
    cursor.execute(query, (new_name, chat_id, user_email))
    conn.commit()
    cursor.close()
    conn.close()


def retrieve_chats(user_email):
    conn, cursor = get_db_connection()
    query = """
        SELECT chats.id, chats.model_type, chats.chat_name, chats.associated_task, chats.custom_model_key
        FROM chats
        JOIN users ON chats.user_id = users.id
        WHERE users.email = %s;
    """
    try:
        cursor.execute(query, (user_email,))
        chat_info = cursor.fetchall()
        return [dict(row) for row in chat_info] if hasattr(cursor, "description") else chat_info
    finally:
        cursor.close()
        conn.close()


def find_most_recent_chat(user_email):
    conn, cursor = get_db_connection()
    query = """
        SELECT chats.id, chats.chat_name
        FROM chats
        JOIN users ON chats.user_id = users.id
        WHERE users.email = %s
        ORDER BY chats.created DESC
        LIMIT 1;
    """
    cursor.execute(query, [user_email])
    chat_info = cursor.fetchone()
    cursor.close()
    conn.close()
    return chat_info


def retrieve_messages(user_email, chat_id, chat_type):
    conn, cursor = get_db_connection()
    query = """
        SELECT messages.created, chats.id, messages.id, messages.reasoning, messages.message_text, messages.sent_from_user, messages.relevant_chunks
        FROM messages
        JOIN chats ON messages.chat_id = chats.id
        JOIN users ON chats.user_id = users.id
        WHERE chats.id = %s AND users.email = %s AND chats.associated_task = %s;
    """
    cursor.execute(query, (chat_id, user_email, chat_type))
    messages = cursor.fetchall()
    cursor.close()
    conn.close()

    if messages:
        processed_messages = []
        for msg in messages:
          msg_dict = dict(msg)
          if msg_dict.get("reasoning"):
              try:
                  reasoning_data = json.loads(msg_dict["reasoning"])
                  if isinstance(reasoning_data, list):
                      msg_dict["reasoning"] = reasoning_data
                  elif isinstance(reasoning_data, dict):
                      msg_dict["reasoning"] = [reasoning_data]
                  elif isinstance(reasoning_data, str):
                      msg_dict["reasoning"] = [{
                          "id": f'step-{msg_dict["id"]}',
                          "type": "llm_reasoning",
                          "thought": reasoning_data,
                          "message": "AI Reasoning",
                          "timestamp": int(time.time() * 1000),
                      }]
                  else:
                      msg_dict["reasoning"] = []

                  if msg_dict.get("reasoning") and msg_dict.get("sent_from_user") == 0:
                      final_thought = None
                      for step in reversed(msg_dict["reasoning"]):
                          if step.get("thought"):
                              final_thought = step["thought"]
                              break
                      if not final_thought and msg_dict.get("message_text"):
                          final_thought = (
                              msg_dict["message_text"][:100] + "..."
                              if len(msg_dict["message_text"]) > 100
                              else msg_dict["message_text"]
                          )
                      msg_dict["reasoning"].append({
                          "id": f'step-complete-{msg_dict["id"]}',
                          "type": "complete",
                          "thought": final_thought,
                          "message": "Response complete",
                          "timestamp": int(time.time() * 1000),
                      })
              except (json.JSONDecodeError, TypeError):
                  msg_dict["reasoning"] = []
          else:
              msg_dict["reasoning"] = []
          processed_messages.append(msg_dict)
        return processed_messages

    return None if messages is None else messages


def delete_chat(chat_id, user_email):
    conn, cursor = get_db_connection()
    cursor.execute(
        """
        DELETE chunks
        FROM chunks
        INNER JOIN documents ON chunks.document_id = documents.id
        INNER JOIN chats ON documents.chat_id = chats.id
        INNER JOIN users ON chats.user_id = users.id
        WHERE chats.id = %s AND users.email = %s;
        """,
        (chat_id, user_email),
    )
    cursor.execute(
        """
        DELETE documents
        FROM documents
        INNER JOIN chats ON documents.chat_id = chats.id
        INNER JOIN users ON chats.user_id = users.id
        WHERE chats.id = %s AND users.email = %s;
        """,
        (chat_id, user_email),
    )
    cursor.execute(
        """
        DELETE messages
        FROM messages
        INNER JOIN chats ON messages.chat_id = chats.id
        INNER JOIN users ON chats.user_id = users.id
        WHERE chats.id = %s AND users.email = %s;
        """,
        (chat_id, user_email),
    )
    cursor.execute(
        """
        DELETE chats
        FROM chats
        INNER JOIN users ON chats.user_id = users.id
        WHERE chats.id = %s AND users.email = %s;
        """,
        (chat_id, user_email),
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    cursor.close()
    conn.close()
    return "Successfully deleted" if deleted else "Could not delete"


def reset_chat(chat_id, user_email):
    conn, cursor = get_db_connection()
    cursor.execute(
        """
        DELETE messages
        FROM messages
        INNER JOIN chats ON messages.chat_id = chats.id
        INNER JOIN users ON chats.user_id = users.id
        WHERE chats.id = %s AND users.email = %s;
        """,
        (chat_id, user_email),
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    cursor.close()
    conn.close()
    return "Successfully deleted" if deleted else "Could not delete"


def reset_uploaded_docs(chat_id, user_email):
    conn, cursor = get_db_connection()
    cursor.execute(
        """
        DELETE chunks
        FROM chunks
        INNER JOIN documents ON chunks.document_id = documents.id
        INNER JOIN chats ON documents.chat_id = chats.id
        INNER JOIN users ON chats.user_id = users.id
        WHERE chats.id = %s AND users.email = %s;
        """,
        (chat_id, user_email),
    )
    cursor.execute(
        """
        DELETE documents
        FROM documents
        INNER JOIN chats ON documents.chat_id = chats.id
        INNER JOIN users ON chats.user_id = users.id
        WHERE chats.id = %s AND users.email = %s;
        """,
        (chat_id, user_email),
    )
    conn.commit()
    cursor.close()
    conn.close()


def change_chat_mode(chat_mode_to_change_to, chat_id, user_email):
    conn, cursor = get_db_connection()
    cursor.execute(
        """
        UPDATE chats
        JOIN users ON chats.user_id = users.id
        SET chats.model_type = %s
        WHERE chats.id = %s AND users.email = %s;
        """,
        (chat_mode_to_change_to, chat_id, user_email),
    )
    conn.commit()
    cursor.close()
    conn.close()


def add_document(text, document_name, chat_id=None, media_type="text", mime_type=None):
    """Insert a document record and return (doc_id, already_existed).

    ``text`` may be None for binary-only media (images, video, audio) where
    the textual representation is derived separately (e.g. via transcription).
    ``media_type`` is one of: 'text', 'image', 'video', 'audio'.
    ``mime_type`` is the MIME string (e.g. 'image/png', 'video/mp4').
    """
    if chat_id == 0:
        return None, False

    conn, cursor = get_db_connection()
    try:
        cursor.execute(
            """
            SELECT id
            FROM documents
            WHERE document_name = %s
            AND chat_id = %s
            """,
            (document_name, chat_id),
        )
        existing_doc = cursor.fetchone()
        if existing_doc:
            return existing_doc["id"], True

        storage_key = "temp"
        cursor.execute(
            """
            INSERT INTO documents (document_text, document_name, storage_key, chat_id, media_type, mime_type)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (text, document_name, storage_key, chat_id, media_type, mime_type),
        )
        doc_id = cursor.lastrowid
        conn.commit()
        return doc_id, False
    finally:
        cursor.close()
        conn.close()


def add_message(text, chat_id, is_user, reasoning=None):
    if chat_id == 0:
        return None
    conn, cursor = get_db_connection()
    cursor.execute(
        "INSERT INTO messages (message_text, chat_id, reasoning, sent_from_user) VALUES (%s,%s,%s, %s)",
        (text, chat_id, reasoning, is_user),
    )
    message_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return message_id


def add_message_attachment(message_id, media_type, mime_type, storage_key, original_filename=None):
    """Attach a media file record to an existing message row."""
    conn, cursor = get_db_connection()
    try:
        cursor.execute(
            """
            INSERT INTO message_attachments (message_id, media_type, mime_type, storage_key, original_filename)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (message_id, media_type, mime_type, storage_key, original_filename),
        )
        attachment_id = cursor.lastrowid
        conn.commit()
        return attachment_id
    finally:
        cursor.close()
        conn.close()


def get_message_attachments(message_id):
    """Return all attachment records for a given message."""
    conn, cursor = get_db_connection()
    try:
        cursor.execute(
            "SELECT * FROM message_attachments WHERE message_id = %s",
            (message_id,),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def add_chunks_with_page_numbers(chunk_data):
    conn, cursor = get_db_connection()
    cursor.executemany(
        """
        INSERT INTO chunks (start_index, end_index, document_id, embedding_vector, page_number)
        VALUES (%s, %s, %s, %s, %s)
        """,
        chunk_data,
    )
    conn.commit()
    cursor.close()
    conn.close()


def add_chunks(chunk_data):
    conn, cursor = get_db_connection()
    cursor.executemany(
        """
        INSERT INTO chunks (start_index, end_index, document_id, embedding_vector)
        VALUES (%s, %s, %s, %s)
        """,
        chunk_data,
    )
    conn.commit()
    cursor.close()
    conn.close()


def retrieve_docs(chat_id, user_email):
    conn, cursor = get_db_connection()
    cursor.execute(
        """
        SELECT documents.document_name, documents.id
        FROM documents
        JOIN chats ON documents.chat_id = chats.id
        JOIN users ON chats.user_id = users.id
        WHERE chats.id = %s AND users.email = %s;
        """,
        (chat_id, user_email),
    )
    docs = cursor.fetchall()
    cursor.close()
    conn.close()
    return docs


def delete_doc(doc_id, user_email):
    conn, cursor = get_db_connection()
    cursor.execute(
        """
        SELECT d.id
        FROM documents d
        JOIN chats c ON d.chat_id = c.id
        JOIN users u ON c.user_id = u.id
        WHERE u.email = %s AND d.id = %s
        """,
        (user_email, doc_id),
    )
    verification_result = cursor.fetchone()
    if verification_result:
        cursor.execute("DELETE FROM chunks WHERE document_id = %s", (doc_id,))
        cursor.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
        conn.commit()
    cursor.close()
    conn.close()
    return "success"


def add_model_key(model_key, chat_id, user_email):
    conn, cursor = get_db_connection()
    cursor.execute(
        """
        UPDATE chats
        JOIN users ON chats.user_id = users.id
        SET chats.custom_model_key = %s
        WHERE chats.id = %s AND users.email = %s;
        """,
        (model_key, chat_id, user_email),
    )
    conn.commit()
    cursor.close()
    conn.close()


def create_chat_shareable_url(chat_id):
    conn, cursor = get_db_connection()
    share_uuid = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO chat_shares (chat_id, share_uuid) VALUES (%s, %s)",
        (chat_id, share_uuid),
    )
    chat_share_id = cursor.lastrowid

    cursor.execute(
        """
        SELECT sent_from_user, message_text, created
        FROM messages
        WHERE chat_id = %s
        ORDER BY created ASC
        """,
        (chat_id,),
    )
    messages = cursor.fetchall()
    for message in messages:
        role = "user" if message["sent_from_user"] else "chatbot"
        cursor.execute(
            """
            INSERT INTO chat_share_messages (chat_share_id, role, message_text, created)
            VALUES (%s, %s, %s, %s)
            """,
            (chat_share_id, role, message["message_text"], message["created"]),
        )

    cursor.execute(
        """
        SELECT id, document_name, document_text, storage_key, created
        FROM documents
        WHERE chat_id = %s
        """,
        (chat_id,),
    )
    docs = cursor.fetchall()
    for doc in docs:
        cursor.execute(
            """
            INSERT INTO chat_share_documents (
                chat_share_id, document_name, document_text, storage_key, created
            ) VALUES (%s, %s, %s, %s, %s)
            """,
            (
                chat_share_id,
                doc["document_name"],
                doc["document_text"],
                doc["storage_key"],
                doc["created"],
            ),
        )
        chat_share_doc_id = cursor.lastrowid
        cursor.execute(
            """
            SELECT start_index, end_index, embedding_vector, page_number
            FROM chunks
            WHERE document_id = %s
            """,
            (doc["id"],),
        )
        chunks = cursor.fetchall()
        for chunk in chunks:
            cursor.execute(
                """
                INSERT INTO chat_share_chunks (
                    chat_share_document_id, start_index, end_index, embedding_vector, page_number
                ) VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    chat_share_doc_id,
                    chunk["start_index"],
                    chunk["end_index"],
                    chunk["embedding_vector"],
                    chunk["page_number"],
                ),
            )

    conn.commit()
    cursor.close()
    conn.close()
    return f"/playbook/{share_uuid}"


def access_shareable_chat(share_uuid, user_id=1):
    conn, cursor = get_db_connection()
    cursor.execute("SELECT * FROM chat_shares WHERE share_uuid = %s", (share_uuid,))
    share = cursor.fetchone()
    if not share:
        cursor.close()
        conn.close()
        return None

    cursor.execute(
        """
        INSERT INTO chats (user_id, model_type, chat_name, associated_task)
        VALUES (%s, %s, %s, %s)
        """,
        (user_id, 0, "Imported from share", 0),
    )
    new_chat_id = cursor.lastrowid

    cursor.execute(
        """
        SELECT role, message_text
        FROM chat_share_messages
        WHERE chat_share_id = %s
        ORDER BY created ASC
        """,
        (share["id"],),
    )
    messages = cursor.fetchall()
    for message in messages:
        sent_from_user = 1 if message["role"] == "user" else 0
        cursor.execute(
            """
            INSERT INTO messages (chat_id, message_text, sent_from_user)
            VALUES (%s, %s, %s)
            """,
            (new_chat_id, message["message_text"], sent_from_user),
        )

    cursor.execute(
        """
        SELECT id, document_name, document_text, storage_key
        FROM chat_share_documents
        WHERE chat_share_id = %s
        """,
        (share["id"],),
    )
    docs = cursor.fetchall()
    for doc in docs:
        cursor.execute(
            """
            INSERT INTO documents (chat_id, document_name, document_text, storage_key)
            VALUES (%s, %s, %s, %s)
            """,
            (new_chat_id, doc["document_name"], doc["document_text"], doc["storage_key"]),
        )
        new_doc_id = cursor.lastrowid
        cursor.execute(
            """
            SELECT start_index, end_index, embedding_vector, page_number
            FROM chat_share_chunks
            WHERE chat_share_document_id = %s
            """,
            (doc["id"],),
        )
        chunks = cursor.fetchall()
        for chunk in chunks:
            cursor.execute(
                """
                INSERT INTO chunks (
                    document_id, start_index, end_index, embedding_vector, page_number
                ) VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    new_doc_id,
                    chunk["start_index"],
                    chunk["end_index"],
                    chunk["embedding_vector"],
                    chunk["page_number"],
                ),
            )

    conn.commit()
    cursor.close()
    conn.close()
    return new_chat_id


def retrieve_messages_from_share_uuid(share_uuid):
    conn, cursor = get_db_connection()
    cursor.execute(
        """
        SELECT csm.role, csm.message_text, csm.created
        FROM chat_shares cs
        JOIN chat_share_messages csm ON cs.id = csm.chat_share_id
        WHERE cs.share_uuid = %s
        ORDER BY csm.created ASC
        """,
        (share_uuid,),
    )
    messages = cursor.fetchall()
    cursor.close()
    conn.close()
    return messages


def get_document_content(document_id, email):
    conn, cursor = get_db_connection()
    cursor.execute(
        """
        SELECT d.document_text, d.document_name, d.id
        FROM documents d
        JOIN chats c ON d.chat_id = c.id
        JOIN users u ON c.user_id = u.id
        WHERE d.id = %s AND u.email = %s
        """,
        (document_id, email),
    )
    document = cursor.fetchone()
    cursor.close()
    conn.close()
    if not document:
        return None
    return {
        "id": document["id"],
        "document_name": document["document_name"],
        "document_text": document["document_text"],
    }


def _combine_sources(sources):
    combined_sources = ""
    for source in sources:
        if isinstance(source, dict):
            chunk_text = source.get("chunk_text")
            document_name = source.get("document_name")
            if not chunk_text or not document_name:
                continue
        else:
            if len(source) < 2:
                continue
            chunk_text, document_name = source[0], source[1]
        combined_sources += f"Document: {document_name}: {chunk_text}\n\n"
    return combined_sources


def add_sources_to_message(message_id, sources):
    conn, cursor = get_db_connection()
    cursor.execute(
        "UPDATE messages SET relevant_chunks = %s WHERE id = %s",
        (_combine_sources(sources), message_id),
    )
    conn.commit()
    cursor.close()
    conn.close()


def add_sources_to_prompt(prompt_id, sources):
    conn, cursor = get_db_connection()
    cursor.execute(
        "UPDATE prompts SET relevant_chunks = %s WHERE id = %s",
        (_combine_sources(sources), prompt_id),
    )
    conn.commit()
    cursor.close()
    conn.close()


def add_prompt(prompt_text):
    conn, cursor = get_db_connection()
    cursor.execute("INSERT INTO prompts (prompt_text) VALUES (%s)", (prompt_text,))
    prompt_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return prompt_id


def add_prompt_answer(answer, citation_id):
    conn, cursor = get_db_connection()
    cursor.execute(
        "INSERT INTO prompt_answers (citation_id, answer_text) VALUES (%s, %s)",
        (citation_id, answer),
    )
    answer_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return answer_id


def _ensure_named_user_exists(user_email, person_name, credits):
    conn, cursor = get_db_connection()
    cursor.execute("SELECT id FROM users WHERE email = %s", (user_email,))
    result = cursor.fetchone()
    if result:
        cursor.close()
        conn.close()
        return result["id"]

    cursor.execute(
        """
        INSERT INTO users (email, person_name, profile_pic_url, credits)
        VALUES (%s, %s, 'url_to_default_image', %s)
        """,
        (user_email, person_name, credits),
    )
    user_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return user_id


def ensure_demo_user_exists(user_email):
    return _ensure_named_user_exists(user_email, "Demo User", 0)


def ensure_sdk_user_exists(user_email):
    return _ensure_named_user_exists(user_email, "SDK User", 0)


def get_message_info(answer_id, user_email):
    conn, cursor = get_db_connection()
    cursor.execute(
        """
        SELECT m.*, c.id as chunk_id, c.start_index, c.end_index, c.page_number
        FROM messages m
        JOIN chats ct ON m.chat_id = ct.id
        JOIN users u ON ct.user_id = u.id
        LEFT JOIN chunks c ON FIND_IN_SET(c.id, m.relevant_chunks) > 0
        WHERE m.id = %s AND u.email = %s
        """,
        (answer_id, user_email),
    )
    answer_data = cursor.fetchall()
    if not answer_data:
        cursor.close()
        conn.close()
        return None, None

    answer = answer_data[0]
    cursor.execute(
        """
        SELECT m.*
        FROM messages m
        WHERE m.id < %s AND m.chat_id = %s AND m.sent_from_user = 1
        ORDER BY m.id DESC
        LIMIT 1
        """,
        (answer_id, answer["chat_id"]),
    )
    question = cursor.fetchone()
    cursor.close()
    conn.close()
    return question, answer


def get_chat_chunks(user_email, chat_id):
    conn, cursor = get_db_connection()
    cursor.execute(
        """
        SELECT c.start_index, c.end_index, c.embedding_vector, c.document_id, d.document_name, d.document_text
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        JOIN chats ch ON d.chat_id = ch.id
        JOIN users u ON ch.user_id = u.id
        WHERE u.email = %s AND ch.id = %s
        """,
        (user_email, chat_id),
    )
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def get_chat_info(chat_id):
    conn, cursor = get_db_connection()
    cursor.execute(
        "SELECT model_type, chat_name, associated_task FROM chats WHERE id = %s",
        (chat_id,),
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if result:
        return result["model_type"], result["associated_task"], result["chat_name"]
    return None, None, None
