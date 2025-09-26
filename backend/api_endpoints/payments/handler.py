
from flask import jsonify
from database.db import add_subscription, delete_subscription, stripe_subscription_for_user, config_for_payment_tiers, user_has_free_trial, stripe_customer_for_user
import stripe
from constants.global_constants import productHashMap
from constants.global_constants import priceToPaymentPlan
from constants.global_constants import PaidUserStatus
from database.db import user_has_free_trial, refresh_credits, user_email_for_id, user_email_for_customer_id, no_subscriptions_with_end_date_null
from database.db_auth import user_id_for_email
from datetime import datetime


def CreateCheckoutSessionHandler(request, userEmail):
    print(f"CreateCheckoutSessionHandler called with userEmail: {userEmail}")
    user_id = user_id_for_email(userEmail)
    print(f"User ID retrieved: {user_id}")

    # Check if user exists
    if user_id is None:
        print(f"User not found for email: {userEmail}")
        return jsonify({'error': 'User not found'}), 404

    new_price_id = productHashMap[request.json["product_hash"]]
    print(f"Price ID: {new_price_id}")

    # Check if user has an existing active subscription
    existing_subscription_id = stripe_subscription_for_user(userEmail)  # Adjust this function to return the subscription ID, not the session ID

    if existing_subscription_id:
        return jsonify({'message': 'Subscription exists already for user.'}), 200
    else:
        subscription_data = {}
        print("before free_trial_code")
        if "free_trial_code" in request.json:
            print("in free_trial_code")
            if user_has_free_trial(userEmail, request.json["free_trial_code"]):
                print("user_has_free_trial success")
                subscription_data['trial_period_days'] = 30
                if priceToPaymentPlan[new_price_id] != PaidUserStatus.BASIC_TIER:
                    print("price fail")
                    return "Server error", 401
            else:
                print("user_has_free_trial fail")
                return "Server error", 401
        try:
            # User doesn't have an active subscription or is starting anew
            checkout_session = stripe.checkout.Session.create(
                line_items=[
                    {
                        'price': new_price_id,
                        'quantity': 1,
                    },
                ],
                mode='subscription',
                success_url="https://chat.anote.ai/account",
                cancel_url="https://chat.anote.ai/account",
                metadata={
                    'user_id': user_id
                },
                subscription_data=subscription_data
            )
            return jsonify({'url': checkout_session.url}), 200
        except Exception as e:
            print('Error creating checkout session:', e)
            return "Server error", 500

def CreatePortalSessionHandler(request, userEmail):
    print("CreatePortalSessionHandler1")
    subscription_id = stripe_subscription_for_user(userEmail)
    print("subscription_id")
    print(subscription_id)
    if not subscription_id:
        print("not subscription_id")
        return jsonify({'status': "No Stripe session for user."}), 400

    customer_id = stripe_customer_for_user(userEmail)
    print("customer_id")
    print(customer_id)
    if not customer_id:
        print("not customer_id")
        return jsonify({'status': "No Stripe customer for user."}), 400

    if no_subscriptions_with_end_date_null(userEmail):
        return jsonify({'status': "Already canceled."}), 400

    return_url = "https://chat.anote.ai/account"
    print("return_url")
    config = config_for_payment_tiers(userEmail, request.json["paymentTier"])
    print("config")
    print(config)

    portalSession = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
        configuration=config
    )

    print("portalSession")
    print(portalSession)

    return jsonify({'url': portalSession.url}), 200

def StripeWebhookHandler(request, event):
    print("event")
    print(event)
    subscription = event['data']['object']
    eventType = event['type']
    print("subscription")
    print(subscription)
    print("eventType")
    print(eventType)

    # Handle the checkout.session.completed event
    if eventType == 'checkout.session.completed':
        print("path112")
        customer_id = subscription['customer']
        subscription_details = stripe.Subscription.retrieve(subscription["subscription"])

        # Extract the price ID from the fetched subscription details
        price_id = subscription_details['items']['data'][0]['price']['id']

        print("customer_id")
        print(customer_id)
        print("price_id")
        print(price_id)

        if price_id in priceToPaymentPlan:
            print("path11")
            payment_plan = priceToPaymentPlan[price_id]

        free_trial_end = None
        if subscription_details["trial_end"] is not None:
            free_trial_end = datetime.fromtimestamp(subscription_details["trial_end"]).strftime('%Y-%m-%d %H:%M:%S')

        user_id = subscription['metadata']['user_id']
        print("user_id")
        print(user_id)

        add_subscription(subscription_details, user_id, customer_id, payment_plan, free_trial_end)
        user_email = user_email_for_id(user_id)
        refresh_credits(user_email)

    elif eventType == 'customer.subscription.updated':
        print("path1")
        customer_id = subscription['customer']
        cancellation_reason = event['data']['object'].get('cancellation_details', {}).get('reason')
        if cancellation_reason == "cancellation_requested":
            # Handle subscription cancellation
            print("Subscription cancellation detected.")
            delete_subscription(subscription)
            user_email = user_email_for_customer_id(customer_id)
            refresh_credits(user_email)

    # Handle the customer.subscription.deleted event
    # I don't think this event fires, but we can leave it for now just in case.
    elif eventType == 'customer.subscription.deleted':
        print("path2")
        delete_subscription(subscription)

    return '', 200