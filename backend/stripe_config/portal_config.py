
import os
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

# cancel_configuration = stripe.billing_portal.Configuration.create(
#     features={
#         'subscription_cancel': {
#             'enabled': True,
#             'mode': 'at_period_end',
#             'proration_behavior': 'none',
#         },
#         # 'subscription_update': {
#         #     'enabled': False,
#         #     "default_allowed_updates": ["price"],
#         #     'products': [
#         #         {
#         #             'prices': [
#         #                 'price_1NZLvfAuWN19h35KbmQCsTDr'
#         #             ],
#         #             'product': 'prod_OM43EsZRVu46EK'
#         #         }
#         #     ]
#         # },
#     },
#     business_profile={
#         'headline': 'upreach',
#     },
# )

product_id = "prod_OM43EsZRVu46EK"
basic_price_id = "price_1Ne91bAuWN19h35KS9n8iokr"
standard_price_id = "price_1Ne91NAuWN19h35KHFQtLZsQ"
premier_price_id = "price_1Ne90vAuWN19h35Kb3DIpkfu"

def create_upgrade(price_id):
    # Create the configuration
    config = stripe.billing_portal.Configuration.create(
        features={
            "subscription_update": {
                "enabled": True,
                "products": [{"product": product_id, "prices": [price_id]}],
                "proration_behavior": "create_prorations",
                "default_allowed_updates": ["price"]
            },
            "payment_method_update": {
                "enabled": True
            }
        },
        business_profile={
            'headline': 'privategpt',  # Replace with a suitable headline for your business or product.
        },
    )

    return config

def create_downgrade(price_id):
    # Create the configuration
    config = stripe.billing_portal.Configuration.create(
        features={
            "subscription_update": {
                "enabled": True,
                "products": [{"product": product_id, "prices": [price_id]}],
                "proration_behavior": "none",
                "default_allowed_updates": ["price"]
            },
            "payment_method_update": {
                "enabled": True
            }
        },
        business_profile={
            'headline': 'privategpt',  # Replace with a suitable headline for your business or product.
        },
    )

    return config

# bpc_1Ne99AAuWN19h35KDOIITw1Z
# bpc_1Ne99AAuWN19h35K7QhZh9OY
# bpc_1Ne99BAuWN19h35KE5oEz0u9
# bpc_1Ne99BAuWN19h35KnutfEQEw
# print(cancel_configuration.id)
print(create_upgrade(standard_price_id).id)
print(create_upgrade(premier_price_id).id)
print(create_downgrade(basic_price_id).id)
print(create_downgrade(standard_price_id).id)