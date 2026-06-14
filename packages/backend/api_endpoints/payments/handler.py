"""Stripe payment endpoints."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, request

payments_bp = Blueprint("payments", __name__, url_prefix="/api/payments")


@payments_bp.post("/checkout")
def create_checkout() -> tuple:
    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        return jsonify({"error": "Stripe not configured"}), 503
    try:
        import stripe
        stripe.api_key = stripe_key
        data = request.get_json(silent=True) or {}
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": data.get("priceId", ""), "quantity": 1}],
            success_url=data.get("successUrl", "http://localhost:3000/success"),
            cancel_url=data.get("cancelUrl", "http://localhost:3000/cancel"),
        )
        return jsonify({"url": session.url}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@payments_bp.post("/portal")
def create_portal() -> tuple:
    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        return jsonify({"error": "Stripe not configured"}), 503
    try:
        import stripe
        stripe.api_key = stripe_key
        data = request.get_json(silent=True) or {}
        session = stripe.billing_portal.Session.create(
            customer=data.get("customerId", ""),
            return_url=data.get("returnUrl", "http://localhost:3000"),
        )
        return jsonify({"url": session.url}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@payments_bp.post("/webhook")
def stripe_webhook() -> tuple:
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature", "")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if webhook_secret:
        try:
            import stripe
            stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
            stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400
    return jsonify({"received": True}), 200
