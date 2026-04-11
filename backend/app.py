import json
import os
import pathlib
from enum import Enum
from functools import wraps
from urllib.parse import urlparse

import google.auth.transport.requests
import jwt
import openai
import ray
import requests
import stripe
from anthropic import Anthropic
from api_endpoints.chat.handler import (
    CreateNewChatHandler,
    DeleteChatHandler,
    FindMostRecentChatHandler,
    RetrieveChatsHandler,
    RetrieveMessagesHandler,
    UpdateChatNameHandler,
)
from api_endpoints.delete_api_key.handler import DeleteAPIKeyHandler
from api_endpoints.documents.handler import (
    ChangeChatModeHandler,
    DeleteDocHandler,
    IngestDocumentsHandler,
    ResetChatHandler,
    RetrieveCurrentDocsHandler,
)
from api_endpoints.generate_api_key.handler import GenerateAPIKeyHandler
from api_endpoints.get_api_keys.handler import GetAPIKeysHandler
from api_endpoints.login.handler import (
    ForgotPasswordHandler,
    LoginHandler,
    ResetPasswordHandler,
    SignUpHandler,
)
from api_endpoints.payments.handler import (
    CreateCheckoutSessionHandler,
    CreatePortalSessionHandler,
    StripeWebhookHandler,
)
from api_endpoints.refresh_credits.handler import RefreshCreditsHandler
from api_endpoints.user.handler import ViewUserHandler
from app_helpers import (
    build_callback_redirect_url,
    build_oauth_state,
    chat_history_csv_response,
    pair_chat_messages,
    reset_local_chat_artifacts,
)
from bs4 import BeautifulSoup
from constants.global_constants import kSessionTokenExpirationTime
from database.db import (
    add_chat as add_chat_to_db,
    add_document as add_document_to_db,
    add_message as add_message_to_db,
    add_model_key as add_model_key_to_db,
    add_sources_to_message as add_sources_to_db,
    access_shareable_chat,
    create_user_if_does_not_exist,
    create_chat_shareable_url,
    ensure_demo_user_exists,
    ensure_sdk_user_exists as ensure_SDK_user_exists,
    get_chat_info,
    get_message_info,
    retrieve_messages as retrieve_message_from_db,
    retrieve_messages_from_share_uuid,
    update_chat_name as update_chat_name_in_db,
)
from database.db_auth import (
    api_key_access_invalid,
    extractUserEmailFromRequest,
    is_api_key_valid,
    user_id_for_email,
    verifyAuthForCheckoutSession,
    verifyAuthForPaymentsTrustedTesters,
    verifyAuthForPortalSession,
)
from dotenv import load_dotenv
from flask import Blueprint, Flask, Response, abort, jsonify, redirect, request
from flask_cors import CORS, cross_origin
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt_identity,
    jwt_required,
)
from flask_mail import Mail
from flask_mysql_connector import MySQL
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from jwt import InvalidTokenError
from pip._vendor import cachecontrol
from tika import parser as p

from datetime import datetime

from features import is_finance_gpt_enabled, is_agent_enabled
from agents.config import AgentConfig
from api_endpoints.languages.arabic import arabic_blueprint
from api_endpoints.languages.chinese import chinese_blueprint
from api_endpoints.languages.gtm import gpt4_blueprint
from api_endpoints.languages.japanese import japanese_blueprint
from api_endpoints.languages.korean import korean_blueprint
from api_endpoints.languages.spanish import spanish_blueprint

if is_finance_gpt_enabled():
    from services.finance_gpt import (
        _get_model,
        chunk_document,
        fetch_external_url,
        get_relevant_chunks,
        get_text_from_url,
    )
    from api_endpoints.financeGPT.chatbot_endpoints import (
        serialize_sources_for_api,
        sources_to_prompt_context,
    )
    _get_model()

if is_agent_enabled():
    from agents.autonomous_agent import AutonomousDocumentAgent
    from agents.reactive_agent import ReactiveDocumentAgent

load_dotenv(override=True)

# Backward-compatible alias while callers migrate off the legacy misspelling.
access_sharable_chat = access_shareable_chat
DEMO_USER_EMAIL = "anon@anote.ai"

app = Flask(__name__)
app.register_blueprint(gpt4_blueprint)
app.register_blueprint(chinese_blueprint)
app.register_blueprint(japanese_blueprint)
app.register_blueprint(korean_blueprint)
app.register_blueprint(spanish_blueprint)
app.register_blueprint(arabic_blueprint)

client = get_openai_client()
def ensure_ray_started():  # pragma: no cover
    if not ray.is_initialized():
        try:
            ray.init(
                logging_level="INFO",
                log_to_driver=True,
                ignore_reinit_error=True  # Helpful when running in dev
            )
        except Exception as e:
            print(f"Ray init failed: {e}")

config = {
  'ORIGINS': [
    'http://localhost:3000',  # React
    'http://localhost:5000',
    'http://localhost:8000',
    'https://chat.anote.ai', # Frontend prod URL,
    'http://localhost:5050',
    'http://dashboard.localhost:3000',  # React
    'https://anote.ai', # Frontend prod URL,
    'https://privatechatbot.ai', # Frontend prod URL,
    'https://dashboard.privatechatbot.ai', # Frontend prod URL,
  ],
}

CORS(app, resources={ r'/*': {'origins': config['ORIGINS']}}, supports_credentials=True)

_flask_secret = os.getenv("FLASK_SECRET_KEY") or os.getenv("JWT_SECRET_KEY", "")
if not _flask_secret:
    import warnings
    warnings.warn(
        "FLASK_SECRET_KEY / JWT_SECRET_KEY env var is not set. "
        "Using an insecure default — set this variable before deploying to production.",
        stacklevel=1,
    )
    _flask_secret = "change-me-in-production"

app.secret_key = _flask_secret
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_HTTPONLY'] = False
app.config["JWT_SECRET_KEY"] = _flask_secret
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = kSessionTokenExpirationTime
app.config["JWT_TOKEN_LOCATION"] = "headers"
app.config.from_object(__name__)

jwt_manager = JWTManager(app)
app.jwt_manager = jwt_manager

# Configure Flask-Mail — all values read from environment variables
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '587'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() != 'false'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME', ''))
mail = Mail(app)


#MySQL config -- could put these in a backend .env if there are different users
app.config['MYSQL_HOST'] = 'db'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DATABASE'] = 'agents'

mysql = MySQL(app)


stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

ensure_ray_started()

# ---------------------------------------------------------------------------
# Swagger / OpenAPI documentation  (available at /docs)
# ---------------------------------------------------------------------------
from flasgger import Swagger  # noqa: E402

_swagger_template = {
    "info": {
        "title": "Anote AI API",
        "description": (
            "Private document Q&A and chat completions API.  "
            "Authenticate with `Authorization: Bearer <api-key>`."
        ),
        "version": "1.0.0",
        "contact": {"name": "Anote AI", "url": "https://anote.ai"},
    },
    "securityDefinitions": {
        "BearerAuth": {"type": "apiKey", "name": "Authorization", "in": "header"}
    },
}
swagger = Swagger(
    app,
    template=_swagger_template,
    config={
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/docs",
    },
)

def valid_api_key_required(fn):
  @wraps(fn)
  def wrapper(*args, **kwargs):
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        splits = auth_header.split(' ')
        if len(splits) > 1:
          api_key = auth_header.split(' ')[1]
          if is_api_key_valid(api_key):
            # Check if the user has credits before allowing API usage
            from database.db_auth import api_key_user_has_credits
            if not api_key_user_has_credits(api_key, min_credits=1):
              return jsonify({"error": "Insufficient credits. Please add credits to your account to use the API."}), 403
            # If api key is valid and user has credits, return the decorated function
            return fn(*args, **kwargs)
    # If API key is not present or valid, return an error message or handle it as needed
    return "Unauthorized", 401
  return wrapper

def jwt_or_session_token_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
      return fn(*args, **kwargs)
    return wrapper


class ProtectedDatabaseTable(Enum):
    # PROFILE_LISTS = 1
    # PROFILES_MULTI = 2
    API_KEYS = 1

# Example of auth function.  This would be called like
# verifyAuthForIDs(ProtectedDatabaseTable.PROFILE_LISTS, request.json["id"])
# in your flask endpoints before calling business logic.  This needs to
# be modified to fit your schema.
def verifyAuthForIDs(table, non_user_id):
  try:
    user_email = extractUserEmailFromRequest(request)
  except InvalidTokenError:
    # If the JWT is invalid, return an error
    return jsonify({"error": "Invalid JWT"}), 401

  access_denied = False
  user_id = user_id_for_email(user_email)
  if table == ProtectedDatabaseTable.API_KEYS:
    access_denied = api_key_access_invalid(user_id, non_user_id)
  if access_denied:
    abort(401)

#WESLEY
@app.route('/generate-playbook/<int:chat_id>', methods = ["GET"])
@jwt_or_session_token_required
def create_shareable_playbook(chat_id):
    url = create_chat_shareable_url(chat_id)
    return jsonify({
            "url": url,
            "success": True,
            "message": "Shareable URL generated successfully"
        }), 200

@app.route('/playbook/<string:playbook_url>', methods=["POST"])
@cross_origin(supports_credentials=True)
def import_shared_chat(playbook_url):
    new_chat_id = access_sharable_chat(playbook_url)
    if isinstance(new_chat_id, Response):
        return new_chat_id
    if new_chat_id is None:
        return jsonify({"error": "Snapshot not found"}), 404
    return jsonify({"new_chat_id": new_chat_id})

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    ---
    tags:
      - System
    responses:
      200:
        description: Server is running
    """
    return "Healthy", 200

# Auth
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  #this is to set our environment to https because OAuth 2.0 only supports https environments

GOOGLE_CLIENT_ID = "261908856206-fff63nag7j793tkbapd3hugthbcp8kfn.apps.googleusercontent.com"  #enter your client id you got from Google console
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")  #set the path to where the .json file you got Google console is

flow = Flow.from_client_secrets_file(  #Flow is OAuth 2.0 a class that stores all the information on how we want to authorize our users
    client_secrets_file=client_secrets_file,
    # scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/gmail.send", "openid"],  #here we are specifing what do we get after the authorization
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],  #here we are specifing what do we get after the authorization
    # redirect_uri="http://localhost:5000/callback"  #and the redirect URI is the point where the user will end up after the authorization
    # redirect_uri="http://127.0.0.1:3000"  #and the redirect URI is the point where the user will end up after the authorization
)
# postmessage

@app.route("/login")  #the page where the user can login
@cross_origin(supports_credentials=True)
def login():
    if request.args.get('email') and len(request.args.get('email')) > 0:
      return LoginHandler(request)
    else:
      o = urlparse(request.base_url)
      netloc = o.netloc
      scheme = "https"
      if "localhost" in netloc:
        scheme = "http"

      flow.redirect_uri = f'{scheme}://{netloc}/callback'
    #   flow.redirect_uri = f'https://upreachapi.upreach.ai/callback'

      state_dict = build_oauth_state(
        flow.redirect_uri,
        request.args.get('product_hash'),
        request.args.get('free_trial_code'),
      )

      state = jwt.encode(state_dict, app.config["JWT_SECRET_KEY"], algorithm="HS256")

      # Generate the authorization URL and use the JWT as the state value
      authorization_url, _ = flow.authorization_url(state=state)

      response = Response(
          response=json.dumps({'auth_url':authorization_url}),
          status=200,
          mimetype='application/json'
      )
      response.headers.add('Access-Control-Allow-Headers',
                          'Origin, Content-Type, Accept')

      return response



@app.route("/callback")  #this is the page that will handle the callback process meaning process after the authorization
@cross_origin(supports_credentials=True)
def callback():
    try:
        decrypted_token = jwt.decode(request.args["state"], app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
        product_hash = decrypted_token.get('product_hash', None)
        free_trial_code = decrypted_token.get('free_trial_code', None)
    except jwt.exceptions.InvalidSignatureError:
        abort(500)
    flow.redirect_uri = decrypted_token["redirect_uri"]
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    default_referrer = "https://chat.anote.ai"
    if not default_referrer:
        default_referrer = "http://localhost:3000"
    user_id = create_user_if_does_not_exist(id_info.get("email"), id_info.get("sub"), id_info.get("name"), id_info.get("picture"))

    access_token = create_access_token(identity=id_info.get("email"))
    refresh_token = create_refresh_token(identity=id_info.get("email"))
    print("request.referrer")
    print(request.referrer)
    # response = redirect(
    #   (request.referrer or default_referrer) +
    #   "?accessToken=" + access_token + "&"
    #   "refreshToken=" + refresh_token
    # )
    response = redirect(
      build_callback_redirect_url(
        default_referrer,
        access_token,
        refresh_token,
        product_hash,
        free_trial_code,
      )
    )
    return response

# This route is used to refresh the JWT
@app.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    # Get the JWT refresh token from the Authorization header
    authorization_header = request.headers["Authorization"]
    authorization_header_parts = authorization_header.split(" ")

    if len(authorization_header_parts) >= 2:
      jwt_token = authorization_header_parts[1]

      try:
          # Try to decode the JWT
          decoded_jwt = decode_token(jwt_token)

          # If the JWT is valid, generate a new JWT with a refreshed expiration time
          access_token = create_access_token(identity=decoded_jwt["sub"])

          # Return the new JWT in the response
          return jsonify({"accessToken": access_token}), 200
      except InvalidTokenError:
          # If the JWT is invalid, return an error
          return jsonify({"error": "Invalid JWT"}), 401
    else:
      # If the Authorization header does not have enough elements, return an error
        return jsonify({"error": "Invalid Authorization header"}), 401

@app.route("/signUp", methods=["POST"])
@cross_origin(supports_credentials=True)
def signUp():
  return SignUpHandler(request)

@app.route("/forgotPassword", methods=["POST"])
@cross_origin(supports_credentials=True)
def forgotPassword():
  return ForgotPasswordHandler(request, mail)

@app.route("/resetPassword", methods=["POST"])
@cross_origin(supports_credentials=True)
def resetPassword():
  return ResetPasswordHandler(request)

@app.route('/refreshCredits', methods = ['POST'])
@cross_origin(supports_credentials=True)
@jwt_or_session_token_required
def RefreshCredits():
  try:
    user_email = extractUserEmailFromRequest(request)
  except InvalidTokenError:
    # If the JWT is invalid, return an error
    return jsonify({"error": "Invalid JWT"}), 401
  return jsonify(RefreshCreditsHandler(request, user_email))

@app.route('/deductCredits', methods = ['POST'])
@cross_origin(supports_credentials=True)
@jwt_or_session_token_required
def DeductCredits():
  try:
    user_email = extractUserEmailFromRequest(request)
  except InvalidTokenError:
    # If the JWT is invalid, return an error
    return jsonify({"error": "Invalid JWT"}), 401

  credits_to_deduct = request.json.get('creditsToDeduct', 1)

  # Import the deduct function and db connection
  from database.db import deduct_credits_from_user, get_db_connection

  # Try to deduct credits
  success = deduct_credits_from_user(user_email, credits_to_deduct)

  if not success:
    return jsonify({"error": "Insufficient credits"}), 400

  # Get updated credit balance directly from database
  conn, cursor = get_db_connection()
  cursor.execute('SELECT credits FROM users WHERE email = %s', [user_email])
  user = cursor.fetchone()
  conn.close()

  new_credits = user["credits"] if user else 0

  return jsonify({
    "success": True,
    "newCredits": new_credits,
    "creditsDeducted": credits_to_deduct
  })

# Billing

@app.route('/createCheckoutSession', methods=['POST'])
@jwt_or_session_token_required
def create_checkout_session():
  try:
    user_email = extractUserEmailFromRequest(request)
  except InvalidTokenError:
    # If the JWT is invalid, return an error
    return jsonify({"error": "Invalid JWT"}), 401
  if not verifyAuthForPaymentsTrustedTesters(user_email):
    abort(401)
  verifyAuthForCheckoutSession(user_email, mail)
  return CreateCheckoutSessionHandler(request, user_email)

@app.route('/createPortalSession', methods=["POST"])
@jwt_or_session_token_required
def customer_portal():
  try:
    user_email = extractUserEmailFromRequest(request)
  except InvalidTokenError:
    # If the JWT is invalid, return an error
    return jsonify({"error": "Invalid JWT"}), 401
  print("got email customer_portal")
  if not verifyAuthForPaymentsTrustedTesters(user_email):
    print("no verifyAuthForPaymentsTrustedTesters")
    abort(401)
  verifyAuthForPortalSession(request, user_email, mail)
  return CreatePortalSessionHandler(request, user_email)

STRIPE_WEBHOOK_SECRET = "whsec_Ustl52CpxewYc33WdamF06lDCjgg3a2e"

@app.route('/stripeWebhook', methods=['POST'])
def stripe_webhook():
  sig_header = request.headers.get('Stripe-Signature')
  try:
      # Verify the signature of the event
      event = stripe.Webhook.construct_event(
          request.data, sig_header, STRIPE_WEBHOOK_SECRET
      )
  except (stripe.error.SignatureVerificationError, ValueError):
      return 'Invalid signature', 400
  return StripeWebhookHandler(request, event)

@app.route('/viewUser', methods = ['GET'])
@jwt_or_session_token_required
def ViewUser():
  try:
    user_email = extractUserEmailFromRequest(request)
  except InvalidTokenError:
    # If the JWT is invalid, return an error
    return jsonify({"error": "Invalid JWT"}), 401
  return ViewUserHandler(request, user_email)

# Example of a background task that can consistently do
# some processing in the background independently of your
# actual web app.
# def background_task():
#   try:
#     print("inside background task")
#     with app.app_context():  # This is important to access Flask app resources
#       while True:
#         automation_ids = view_automations_to_process()
#         print("automation_ids", automation_ids)
#         for id in automation_ids:
#           print("in for automation_ids")
#           socketId = get_socket_for_automation(id)
#           print("socketId")
#           print(socketId)
#           trigger_automation_step.remote(id, auth, host, socketId)
#         time.sleep(60)
#   except Exception as e:
#     print(f"Exception in background_task: {e}")
# app.start_background_task(background_task)

# Helper function to scrape sub-URLs from the main website
def get_links(initial_url: str):  # pragma: no cover
    response = fetch_external_url(initial_url)

    # Parse the HTML code with BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all <a> tags and extract the href attribute (the hyperlink)
    links = []
    links_text = []
    for link in soup.find_all('a'):
        if type(link.get('href')) == str:
            if link.get('href')[0] == "/":
                web_url = initial_url.rstrip("/") + link.get('href')  # Full URL
                web_text = get_text_from_url(web_url)
                if len(web_text) > 0:
                    links.append(web_url)
                    links_text.append(web_text)
    return links, links_text

## CHATBOT SECTION
output_document_path = 'output_document'
chat_history_file = os.path.join(output_document_path, 'chat_history.csv')
vector_base_path = 'db'
source_documents_path = 'source_documents'

@app.route('/api/reset-everything', methods=['POST']) #Change this to use MYSQL db
def reset_everything():
    try:
        return reset_local_chat_artifacts(source_documents_path, output_document_path)
    except Exception as e:
        return f'Failed to delete DB folder: {str(e)}', 500

@app.route('/download-chat-history', methods=['POST'])
def download_chat_history():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
        # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    try:
        chat_type = request.json.get('chat_type')
        chat_id = request.json.get('chat_id')

        messages = retrieve_message_from_db(user_email, chat_id, chat_type)

        paired_messages = pair_chat_messages(messages)
        return chat_history_csv_response(paired_messages)
    except Exception as e:
        print("error is,", str(e))
        return jsonify({"error": str(e)}), 500


@app.route('/create-new-chat', methods=['POST'])
def create_new_chat():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    return CreateNewChatHandler(request, user_email)

@app.route('/retrieve-all-chats', methods=['POST'])
def retrieve_chats():
    #Given an input of a chat_type and user_email, it will return as a list of dictionaries all the chats of that user and chat type from the db

    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401
    return RetrieveChatsHandler(user_email)

@app.route('/retrieve-messages-from-chat', methods=['POST'])
def retrieve_messages_from_chat():
    #Getting current user not working, fix this later
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    return RetrieveMessagesHandler(request, user_email)


@app.route('/retrieve-messages-from-chat-demo', methods=['POST'])
def retrieve_messages_from_chat_demo():
    ensure_demo_user_exists(DEMO_USER_EMAIL)
    return RetrieveMessagesHandler(request, DEMO_USER_EMAIL)

@app.route('/retrieve-shared-messages-from-chat', methods=['POST'])
def get_playbook_messages():
    chat_type = 0
    body = request.get_json(force=True) or {}
    # Support both legacy chat_id lookup and UUID-based playbook lookup
    playbook_url = body.get('playbook_url')
    if playbook_url:
        messages = retrieve_messages_from_share_uuid(playbook_url)
        return jsonify(messages=[
            {"message_text": m["message_text"], "sent_from_user": 1 if m["role"] == "user" else 0}
            for m in messages
        ])
    chat_id = body.get('chat_id')
    messages = retrieve_message_from_db("anon@anote.ai", chat_id, chat_type)
    return jsonify(messages=messages)

@app.route('/update-chat-name', methods=['POST'])
def update_chat_name():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    return UpdateChatNameHandler(request, user_email)

@app.route('/infer-chat-name', methods=['POST'])
def infer_chat_name():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    chat_messages = request.json.get('messages')
    chat_id = request.json.get('chat_id')


    completion = client.chat.completions.create(
        model="llama2:latest",
        messages=[
            {"role": "user",
             "content": f"Based off these 2 messages between me and my chatbot, please infer a name for the chat. Keep it to a maximum of 4 words, 5 if you must. Do not use the word chat in it. Some good examples are, AI research paper, Apple financial report, Questions about earnings calls. Return only the chatname and nothing else. Here are the messages: {chat_messages}"}
        ]
    )
    new_name = str(completion.choices[0].message.content)

    update_chat_name_in_db(user_email, chat_id, new_name)

    return jsonify(chat_name=new_name)


@app.route('/delete-chat', methods=['POST'])
def delete_chat():
    chat_id = request.json.get('chat_id')

    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    return DeleteChatHandler(request, user_email)


@app.route('/find-most-recent-chat', methods=['POST'])
def find_most_recent_chat():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    return FindMostRecentChatHandler(user_email)


@app.route('/ingest-pdf', methods=['POST'])
def ingest_pdfs():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
        # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    return IngestDocumentsHandler(request, user_email, p, chunk_document)


@app.route('/ingest-pdf-demo', methods=['POST'])
def ingest_pdfs_demo():
    ensure_demo_user_exists(DEMO_USER_EMAIL)
    chat_id = request.form.getlist("chat_id")[0] if request.form.getlist("chat_id") else None
    if not chat_id:
        chat_id = add_chat_to_db(DEMO_USER_EMAIL, 0, 0)

    files = request.files.getlist("files[]")
    max_chunk_size = 1000
    for file in files:
        result = p.from_buffer(file)
        text = result["content"].strip()
        filename = file.filename
        doc_id, does_exist = add_document_to_db(text, filename, chat_id=chat_id)
        if not does_exist:
            chunk_document.remote(text, max_chunk_size, doc_id)

    return jsonify({"Success": "Document Uploaded", "chat_id": chat_id}), 200


    #return text, filename

@app.route('/retrieve-current-docs', methods=['POST'])
def retrieve_current_docs():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
        return jsonify({"error": "Invalid JWT"}), 401
    return RetrieveCurrentDocsHandler(request, user_email)


@app.route('/retrieve-current-docs-demo', methods=['POST'])
def retrieve_current_docs_demo():
    ensure_demo_user_exists(DEMO_USER_EMAIL)
    return RetrieveCurrentDocsHandler(request, DEMO_USER_EMAIL)

@app.route('/delete-doc', methods=['POST'])
def delete_doc():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
        return jsonify({"error": "Invalid JWT"}), 401
    return DeleteDocHandler(request, user_email)

@app.route('/change-chat-mode', methods=['POST'])
def change_chat_mode_and_reset_chat():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
        return jsonify({"error": "Invalid JWT"}), 401
    return ChangeChatModeHandler(request, user_email)

@app.route('/reset-chat', methods=['POST'])
def reset_chat():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401
    return ResetChatHandler(request, user_email)

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, '__dict__'):
            return o.__dict__
        elif hasattr(o, 'dict') and callable(o.dict):
            # For Pydantic models
            return o.dict()
        elif hasattr(o, '__dataclass_fields__'):
            # For dataclasses
            from dataclasses import asdict
            return asdict(o)
        return super().default(o)

def _parse_message_request(req):
    """Extract (message_text, chat_id, model_type, model_key, is_guest, media_attachments)
    from either a JSON body or a multipart/form-data request.

    Multipart is used when the client attaches inline image files alongside the
    chat message.  The form fields mirror the JSON keys; files are sent under
    the field name ``attachments[]``.
    """
    content_type = req.content_type or ""
    if "multipart/form-data" in content_type:
        raw_message = req.form.get("message", "")
        chat_id = req.form.get("chat_id")
        model_type = int(req.form.get("model_type", 0))
        model_key = req.form.get("model_key", "")
        is_guest = req.form.get("is_guest", "false").lower() == "true"

        media_attachments = []
        for f in req.files.getlist("attachments[]"):
            mime = (f.content_type or "application/octet-stream").split(";")[0].strip()
            media_category = "image"
            if mime.startswith("video/"):
                media_category = "video"
            elif mime.startswith("audio/"):
                media_category = "audio"
            import base64
            data_b64 = base64.b64encode(f.read()).decode("utf-8")
            media_attachments.append({
                "media_type": media_category,
                "mime_type": mime,
                "data": data_b64,
                "original_filename": f.filename,
            })
    else:
        body = req.get_json(force=True) or {}
        raw_message = body.get("message", "")
        chat_id = body.get("chat_id")
        model_type = body.get("model_type", 0)
        model_key = body.get("model_key", "")
        is_guest = body.get("is_guest", False)
        # Allow clients to pass pre-encoded attachments in JSON for small images
        media_attachments = body.get("attachments", [])

    # Normalise message to a plain string
    if isinstance(raw_message, dict):
        message_text = raw_message.get("text") or raw_message.get("content") or str(raw_message)
    else:
        message_text = str(raw_message) if raw_message is not None else ""

    return message_text, chat_id, model_type, model_key, is_guest, media_attachments


@app.route('/process-message-pdf', methods=['POST'])
def process_message_pdf():  # pragma: no cover
    print("=== DEBUG: process_message_pdf called ===")

    message_text, chat_id, model_type, model_key, is_guest, media_attachments = _parse_message_request(request)

    print(f"DEBUG: is_guest={is_guest}, model_type={model_type}, attachments={len(media_attachments)}")
    print(f"DEBUG: message_text={message_text!r}")

    # Handle user authentication based on guest status
    user_email = None
    if not is_guest:
        print("DEBUG: Not guest mode, extracting user email")
        try:
            user_email = extractUserEmailFromRequest(request)
            print(f"DEBUG: Extracted user_email = {user_email}")
        except InvalidTokenError:
            print("DEBUG: Invalid token error")
            return jsonify({"error": "Invalid JWT"}), 401
        except Exception as e:
            print(f"DEBUG: Error extracting user email: {e}")
            return jsonify({"error": "Authentication error"}), 401
    else:
        print("DEBUG: Guest mode, skipping user email extraction")

    # Check if agents are enabled
    if AgentConfig.is_agent_enabled():
        try:
            # Use the autonomous agent (tool-calling loop with optional extended thinking)
            agent = AutonomousDocumentAgent(model_type=model_type, model_key=model_key)

            # Process the query using the appropriate method based on guest status
            if is_guest:
                # Use guest-specific streaming method
                result = agent.process_query_stream_guest(message_text.strip())
            else:
                # Use regular method for authenticated users
                if not user_email or not isinstance(user_email, str):
                    return jsonify({"error": "User email is missing or invalid"}), 401
                result = agent.process_query_stream(
                    message_text.strip(),
                    chat_id,
                    user_email,
                    media_attachments=media_attachments or None,
                )

            def generate():
                for chunk in result:
                    try:
                        if isinstance(chunk, dict):
                            chunk_data = chunk
                        elif hasattr(chunk, 'dict') and callable(getattr(chunk, 'dict', None)):
                            chunk_data = chunk.dict()
                        elif hasattr(chunk, '__dict__'):
                            chunk_data = chunk.__dict__
                        else:
                            chunk_data = chunk

                        json_data = json.dumps(chunk_data, cls=CustomJSONEncoder)
                        yield f"data: {json_data}\n\n"
                        print(f"Streamed chunk: {chunk}")
                    except (TypeError, ValueError) as e:
                        print(f"Error serializing chunk {chunk}: {e}")

            return Response(generate(), status=200)


            # return jsonify({
            #     "answer": 1, # result["answer"],
            #     "message_id": 1,# result.get("message_id"),
            #     "sources": 1, # result.get("sources", []),
            #     "reasoning": 1 # result.get("agent_reasoning", []) if AgentConfig.LOG_AGENT_REASONING else []
            # })

        except Exception as e:
            print(f"Error in reactive agent processing: {str(e)}")
            # Fallback to original implementation if agent fails and fallback is enabled
            if AgentConfig.should_use_fallback():
                return _process_message_pdf_fallback(message_text, chat_id, model_type, model_key, user_email, is_guest)
            else:
                return jsonify({"error": "Agent processing failed due to an internal error."}), 500
    else:
        # Agents disabled, use original implementation
        return _process_message_pdf_fallback(message_text, chat_id, model_type, model_key, user_email, is_guest)


@app.route('/process-message-pdf-demo', methods=['POST'])
def process_message_pdf_demo():  # pragma: no cover
    ensure_demo_user_exists(DEMO_USER_EMAIL)
    message = request.json.get('message')
    chat_id = request.json.get('chat_id')
    model_type = request.json.get('model_type', 0)
    model_key = request.json.get('model_key', "")
    return _process_message_pdf_fallback(message, chat_id, model_type, model_key, DEMO_USER_EMAIL, False)

def _process_message_pdf_fallback(message, chat_id, model_type, model_key, user_email, is_guest=False):  # pragma: no cover
    """Fallback implementation using the original direct LLM approach without the ReActive Agent.

    ``message`` is already a plain string at this point (normalised upstream).
    """
    query = str(message).strip()

    # For guest users, skip database operations
    if not is_guest:
        #This adds user message to db
        add_message_to_db(query, chat_id, 1)

    # For guest users, provide a simple general knowledge response
    if is_guest:
        # Simple guest response without document access
        simple_response = "I'm currently in guest mode and cannot access uploaded documents. To use full AI document analysis features, please log in or create an account. I can answer general questions using my knowledge base."
        return jsonify({
            "answer": simple_response,
            "message_id": None,
            "sources": [],
            "reasoning": []
        })

    #Get most relevant section from the document
    sources = get_relevant_chunks(2, query, chat_id, user_email, include_metadata=True)
    sources_str = sources_to_prompt_context(sources)

    if (model_type == 0):
        if model_key:
           model_use = model_key
        else:
           model_use = "llama2:latest"

        print("using OpenAI and model is", model_use)
        try:
            completion = client.chat.completions.create(
                model=model_use,
                messages=[
                    {"role": "user",
                     "content": f"You are a factual chatbot that answers questions about uploaded documents. You only answer with answers you find in the text, no outside information. These are the sources from the text:{sources_str} And this is the question:{query}."}
                ]
            )
            print("using fine tuned model")
            answer = str(completion.choices[0].message.content)
        except openai.NotFoundError:
            print(f"The model `{model_use}` does not exist. Falling back to 'gpt-4'.")
            completion = client.chat.completions.create(
                model="llama2:latest",
                messages=[
                    {"role": "user",
                     "content": f"First, tell the user that their given model key does not exist, and that you have resorted to using GPT-4 before answering their question, then add a line break and answer their question. You are a factual chatbot that answers questions about uploaded documents. You only answer with answers you find in the text, no outside information. These are the sources from the text:{sources[0]}{sources[1]} And this is the question:{query}."}
                ]
            )
            answer = str(completion.choices[0].message.content)
    else:
        print("using Claude")

        anthropic = get_anthropic_client()

        completion = anthropic.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=700,
            system=(
                "You are a factual chatbot that answers questions about uploaded documents. "
                "You only answer with answers you find in the text, no outside information."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"These are the sources from the text: {sources_str}\n"
                        f"And this is the question: {query}."
                    ),
                }
            ],
        )
        answer = completion.content[0].text

    #This adds bot message
    message_id = add_message_to_db(answer, chat_id, 0)

    try:
        add_sources_to_db(message_id, sources)
    except:
        print("no sources")

    return jsonify(
        answer=answer,
        message_id=message_id,
        sources=serialize_sources_for_api(sources),
    )


@app.route('/add-model-key', methods=['POST'])
def add_model_key():
    model_key = request.json.get('model_key')
    chat_id = request.json.get('chat_id')

    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    add_model_key_to_db(model_key, chat_id, user_email)

    return "success"




## API Keys

@app.route("/generateAPIKey", methods=["POST"])
@jwt_or_session_token_required
def generateAPIKey():
    """
    Generate a new API key for the authenticated user.
    ---
    tags:
      - API Keys
    responses:
      200:
        description: New API key created
        schema:
          type: object
          properties:
            api_key:
              type: string
      401:
        description: Unauthorized
    """
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
        return jsonify({"error": "Invalid JWT"}), 401
    return GenerateAPIKeyHandler(request, user_email)


@app.route("/deleteAPIKey", methods=["POST"])
@jwt_or_session_token_required
def deleteAPIKey():
  verifyAuthForIDs(ProtectedDatabaseTable.API_KEYS, request.json["api_key_id"])
  return DeleteAPIKeyHandler(request)

@app.route('/getAPIKeys', methods = ['GET'])
@jwt_or_session_token_required
def getAPIKeys():
    """
    List all API keys for the authenticated user.
    ---
    tags:
      - API Keys
    responses:
      200:
        description: List of API keys
        schema:
          type: object
          properties:
            api_keys:
              type: array
              items:
                type: object
      401:
        description: Unauthorized
    """
    try:
      user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
        return jsonify({"error": "Invalid JWT"}), 401
    return GetAPIKeysHandler(request, user_email)


#For the SDK
#later will need to add @valid_api_key_required to all

USER_EMAIL_API = "api@example.com"

@app.route('/public/upload', methods = ['POST'])
@valid_api_key_required
def upload():  # pragma: no cover
    """
    Upload documents to a new chat session.
    ---
    tags:
      - Public SDK
    security:
      - BearerAuth: []
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: files[]
        type: file
        description: One or more document files (PDF, DOCX, CSV, TXT, etc.)
      - in: formData
        name: task_type
        type: string
        description: '"documents" or 0 for Q&A (default)'
      - in: formData
        name: model_type
        type: string
        description: '"gpt" / 0 for OpenAI, "claude" / 1 for Anthropic'
    responses:
      200:
        description: Upload successful — returns chat_id for subsequent /public/chat calls
        schema:
          type: object
          properties:
            chat_id:
              type: integer
            id:
              type: integer
      403:
        description: Insufficient credits
    """
    print("Form data:", request.form)
    print("Files:", request.files)

    # Extract API key for credit deduction
    auth_header = request.headers.get('Authorization')
    api_key = auth_header.split(' ')[1] if auth_header and auth_header.startswith('Bearer ') else None

    # Calculate credits needed (1 credit per file/URL)
    files = request.files.getlist('files[]')
    paths = request.form.getlist('html_paths')
    total_items = len(files) + len(paths)
    credits_needed = max(1, total_items)  # At least 1 credit, more for multiple files

    # Deduct credits before processing
    from database.db_auth import deduct_credits_from_api_key_user
    if not deduct_credits_from_api_key_user(api_key, credits_needed):
        return jsonify({"error": f"Insufficient credits. You need {credits_needed} credits for this operation."}), 403

    #chat_type = int(request.form.getlist('task_type')[0])  # Convert to int
    #model_type = int(request.form.getlist('model_type')[0])

    raw_task = request.form.getlist('task_type')
    raw_model = request.form.getlist('model_type')
    chat_type = raw_task[0] if raw_task else "documents"
    model_type = raw_model[0] if raw_model else "gpt"

    # Accept both numeric (0/1) and string ("gpt"/"claude") model_type
    _model_str_map = {"0": "gpt", "1": "claude", "2": "llama"}
    if str(model_type) in _model_str_map:
        model_type = _model_str_map[str(model_type)]

    # Accept both numeric (0) and string ("documents") task_type
    _task_str_map = {"0": "documents", "1": "edgar"}
    if str(chat_type) in _task_str_map:
        chat_type = _task_str_map[str(chat_type)]

    user_email = USER_EMAIL_API

    print("CHAT TYPE IS", chat_type)
    if chat_type == "documents": #question-answering
        print("question answer")

        print("paths is", paths)

        print("chat is is", chat_type)
        print("files are", files)

        #create a new user with user_email api@example.com
        ensure_SDK_user_exists(user_email)

        #create new chat
        model_number = 0 if model_type == "gpt" else 1 if model_type == "claude" else None
        chat_number = 0 if chat_type == "documents" else 1 if chat_type == "edgar" else None
        chat_id = add_chat_to_db(user_email, chat_number, model_number)

        #Ingest pdf
        MAX_CHUNK_SIZE = 1000

        for file in files:
            print("file is here")
            result = p.from_buffer(file)
            text = result["content"].strip()

            filename = file.filename

            doc_id, doesExist = add_document_to_db(text, filename, chat_id=chat_id)

            if not doesExist:
                #chunk_document.remote(text, MAX_CHUNK_SIZE, doc_id)
                result_id = chunk_document.remote(text, MAX_CHUNK_SIZE, doc_id)
                result = ray.get(result_id)
        for path in paths:

            text = get_text_from_url(path)

            doc_id, doesExist = add_document_to_db(text, path, chat_id=chat_id)

            if not doesExist:
                #chunk_document.remote(text, MAX_CHUNK_SIZE, doc_id)
                result_id = chunk_document.remote(text, MAX_CHUNK_SIZE, doc_id)
                result = ray.get(result_id)
    else:
        return jsonify({"error": f"Invalid task type: {chat_type!r}. Use 'documents' or 0."}), 400

    return jsonify({"chat_id": chat_id, "id": chat_id}), 200  # 'id' kept for backward compat


@app.route('/public/chat', methods=['POST'])
@valid_api_key_required
def public_ingest_pdf():  # pragma: no cover
    """
    Send a message to the chatbot and get a grounded answer.
    ---
    tags:
      - Public SDK
    security:
      - BearerAuth: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          required: [message, chat_id]
          properties:
            message:
              type: string
              example: What is the main finding in the document?
            chat_id:
              type: integer
              description: Session ID from /public/upload
            model_key:
              type: string
              description: Optional fine-tuned OpenAI key
    responses:
      200:
        description: Answer with source citations
        schema:
          type: object
          properties:
            answer:
              type: string
            message_id:
              type: integer
            sources:
              type: array
      403:
        description: Insufficient credits
    """
    user_email = USER_EMAIL_API
    ensure_SDK_user_exists(user_email)

    # Extract API key for credit deduction
    auth_header = request.headers.get('Authorization')
    api_key = auth_header.split(' ')[1] if auth_header and auth_header.startswith('Bearer ') else None

    # Deduct 1 credit for each chat message
    from database.db_auth import deduct_credits_from_api_key_user
    if not deduct_credits_from_api_key_user(api_key, 1):
        return jsonify({"error": "Insufficient credits. You need 1 credit per chat message."}), 403

    message = request.json['message']
    chat_id = request.json['chat_id']
    model_key = request.json.get('model_key')

    model_type, task_type, _ = get_chat_info(chat_id)

    if AgentConfig.is_agent_enabled():
        try:
            # Use reactive agent for public API
            agent = ReactiveDocumentAgent(model_type=model_type, model_key=model_key)
            result = agent.process_query(message.strip(), chat_id, user_email)

            sources_payload = serialize_sources_for_api(result.get("sources", []))

            return jsonify(
                message_id=result.get("message_id"),
                answer=result["answer"],
                sources=sources_payload
            )

        except Exception as e:
            print(f"Public chat agent error: {e}")
            # Fallback to original implementation if enabled
            if AgentConfig.should_use_fallback():
                return _public_chat_fallback(message, chat_id, model_type, model_key, user_email)
            else:
                return jsonify({"error": f"Agent processing failed: {str(e)}"}), 500
    else:
        # Agents disabled, use original implementation
        return _public_chat_fallback(message, chat_id, model_type, model_key, user_email)

def _public_chat_fallback(message, chat_id, model_type, model_key, user_email):  # pragma: no cover
    """Fallback implementation for public chat API"""
    query = message.strip()

    #This adds user message to db
    add_message_to_db(query, chat_id, 1)

    #Get most relevant section from the document
    sources = get_relevant_chunks(2, query, chat_id, user_email, include_metadata=True)
    sources_str = sources_to_prompt_context(sources)

    if (model_type == 0):
        if model_key:
           model_use = model_key
        else:
           model_use = "llama2:latest"

        try:
            completion = client.chat.completions.create(
                model=model_use,
                messages=[
                    {"role": "user",
                     "content": f"You are a factual chatbot that answers questions about uploaded documents. You only answer with answers you find in the text, no outside information. These are the sources from the text:{sources_str} And this is the question:{query}."}
                ]
            )
            answer = str(completion.choices[0].message.content)
        except openai.NotFoundError:
            completion = client.chat.completions.create(
                model="llama2:latest",
                messages=[
                    {"role": "user",
                     "content": f"First, tell the user that their given model key does not exist, and that you have resorted to using GPT-4 before answering their question, then add a line break and answer their question. You are a factual chatbot that answers questions about uploaded documents. You only answer with answers you find in the text, no outside information. These are the sources from the text:{sources[0]}{sources[1]} And this is the question:{query}."}
                ]
            )
            answer = str(completion.choices[0].message.content)
    else:
        if model_key:
           return jsonify({"Error": "You cannot enter a fine-tuned model key when using Claude"}), 400

        anthropic = get_anthropic_client()
        completion = anthropic.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=700,
            system=(
                "You are a factual chatbot that answers questions about uploaded documents. "
                "You only answer with answers you find in the text, no outside information."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"These are the sources from the text: {sources_str}\n"
                        f"And this is the question: {query}."
                    ),
                }
            ],
        )
        answer = completion.content[0].text

    #This adds bot message
    message_id = add_message_to_db(answer, chat_id, 0)

    try:
        add_sources_to_db(message_id, sources)
    except:
        print("no sources")

    return jsonify(
        message_id=message_id,
        answer=answer,
        sources=serialize_sources_for_api(sources),
    )

@app.route('/public/evaluate', methods = ['POST'])
@valid_api_key_required
def evaluate():
    from api_endpoints.schemas import EvaluateRequest
    from pydantic import ValidationError as _ValidationError
    try:
        req = EvaluateRequest.model_validate(request.get_json(force=True) or {})
    except _ValidationError as exc:
        return jsonify({"error": {"message": str(exc), "type": "validation_error"}}), 422
    message_id = req.message_id
    user_email = USER_EMAIL_API

    question_json, answer_json = get_message_info(message_id, user_email)

    question = question_json['message_text']
    answer = answer_json['message_text']
    context = answer_json['relevant_chunks']

    #get it in the corret data format to put in ragas
    if not isinstance(context, list):
        context = [context]

    contexts = [context]

    data = {
        "question": [question],
        "answer": [answer],
        "contexts": contexts
    }

    result = data

    return result

@app.route('/api/companies', methods=['GET'])
def get_companies():
    cursor = mysql.connection.cursor(dictionary=True)
    cursor.execute("SELECT id, name, path FROM companies")
    companies = cursor.fetchall()
    cursor.close()
    return jsonify(companies)


def get_user_from_token(token):
    if not token:
        return None

    cursor = mysql.connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM users WHERE session_token = %s
    """, (token,))
    user = cursor.fetchone()

    if user and user.get("session_token_expiration"):
        # session_token_expiration is usually stored as a datetime string
        expiration = user["session_token_expiration"]
        # Convert expiration string to datetime object (assuming ISO format)
        expiration_dt = datetime.strptime(expiration, "%Y-%m-%d %H:%M:%S")
        if expiration_dt > datetime.utcnow():
            return user
    return None


@app.route("/api/user/companies", methods=["GET"])
@jwt_required()
def get_user_companies():
    user_email = get_jwt_identity()

    cursor = mysql.connection.cursor(dictionary=True)

    # Get user ID from email
    cursor.execute("SELECT id FROM users WHERE email = %s", (user_email,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        return jsonify({"error": "Invalid user"}), 401

    user_id = user["id"]

    # Get companies for this user
    cursor.execute("SELECT name, path FROM user_company_chatbots WHERE user_id = %s", (user_id,))
    companies = cursor.fetchall()

    cursor.close()
    return jsonify(companies)


api = Blueprint('api', __name__)
app.register_blueprint(api)


# ---------------------------------------------------------------------------
# OpenAI-compatible Chat Completions API  (/v1/*)
# ---------------------------------------------------------------------------
# These endpoints let any OpenAI-compatible client (e.g. the openai Python
# SDK, LangChain, etc.) talk directly to this server:
#
#   client = OpenAI(base_url="http://localhost:5000/v1", api_key="<your-key>")
#   client.chat.completions.create(
#       model="gpt-4o",
#       messages=[{"role": "user", "content": "What is in my documents?"}],
#   )
#
# Pass `chat_id` inside the optional `extra_body` / `extra_params` dict to
# ground the answer in previously-uploaded documents.  Omit it (or set it to
# null) for a plain, document-free chat-completion.
# ---------------------------------------------------------------------------

_SUPPORTED_MODELS = [
    # OpenAI
    "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo",
    # Anthropic
    "claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001",
    "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
    "claude-3-opus-20240229",
    # Local / Ollama
    "llama3", "llama2", "mistral",
]


@app.route("/v1/account", methods=["GET"])
@valid_api_key_required
def v1_account():
    """Return account, subscription, and credit information for the caller.

    This is an Anote-specific extension to the OpenAI-compatible API surface.
    The response mirrors the shape returned by ``GET /viewUser`` but lives under
    the ``/v1/`` namespace so SDK clients can reach it without a separate host.

    Returns 200 with JSON:
        id            – numeric user ID
        email         – user email
        plan          – string plan name (free / basic / standard / premium / enterprise)
        plan_level    – integer 0-4 (matches PaidUserStatus enum)
        credits_remaining – integer credits left this period
        credits_monthly   – integer credits granted per billing period (0 = pay-as-you-go)
        credits_refresh_date – ISO date of next credit reset, or null
        subscription_status  – "active" | "trialing" | "canceled" | "none"
        subscription_end_date – ISO date subscription expires, or null
        is_free_trial – boolean
        limits        – object with per-plan quotas
    """
    from database.db import view_user
    from constants.global_constants import planToCredits

    api_key = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    user_email = user_email_for_api_key(api_key)
    result = view_user(user_email)

    # view_user returns a Flask Response — unwrap it
    if hasattr(result, "get_json"):
        user_data = result.get_json()
    elif isinstance(result, tuple):
        user_data = result[0].get_json() if hasattr(result[0], "get_json") else {}
    else:
        user_data = {}

    plan_level = int(user_data.get("paid_user") or 0)
    plan_names = {0: "free", 1: "basic", 2: "standard", 3: "premium", 4: "enterprise"}

    # Determine subscription status
    end_date = user_data.get("end_date")
    is_free_trial = bool(user_data.get("is_free_trial"))
    if is_free_trial:
        status = "trialing"
    elif plan_level > 0:
        status = "active" if not end_date else "canceled"
    else:
        status = "none"

    monthly_credits = planToCredits.get(plan_level, 0)

    return jsonify({
        "object": "account",
        "id": user_data.get("id"),
        "email": user_data.get("email"),
        "name": user_data.get("name"),
        "plan": plan_names.get(plan_level, "free"),
        "plan_level": plan_level,
        "credits_remaining": user_data.get("credits", 0),
        "credits_monthly": monthly_credits,
        "credits_refresh_date": user_data.get("credits_refresh"),
        "subscription_status": status,
        "subscription_end_date": end_date,
        "is_free_trial": is_free_trial,
        "next_plan": user_data.get("next_plan"),
        "limits": {
            "credits_per_month": monthly_credits,
            "models": _SUPPORTED_MODELS,
        },
    })


@app.route("/v1/usage", methods=["GET"])
@valid_api_key_required
def v1_usage():
    """Return API usage history and summary for the caller.

    Query parameters:
        start_date – ISO date string YYYY-MM-DD (optional, inclusive)
        end_date   – ISO date string YYYY-MM-DD (optional, inclusive)
        limit      – max rows to return (default 100, max 1000)

    Returns 200 with JSON shaped like::

        {
          "object": "list",
          "data": [
            {
              "id": 1,
              "endpoint": "/v1/chat/completions",
              "model": "gpt-4o",
              "prompt_tokens": 120,
              "completion_tokens": 85,
              "total_tokens": 205,
              "credits_used": 1,
              "created": "2024-01-15T10:30:00"
            },
            …
          ],
          "summary": {
            "total_requests": 42,
            "prompt_tokens": 5100,
            "completion_tokens": 3600,
            "total_tokens": 8700,
            "credits_used": 42,
            "period_start": "2024-01-01",
            "period_end": "2024-01-31"
          }
        }
    """
    from database.usage import get_usage_rows, get_usage_summary, user_and_key_ids_for_api_key

    api_key = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    user_id, _ = user_and_key_ids_for_api_key(api_key)
    if user_id is None:
        return jsonify({"error": "API key not found"}), 401

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    try:
        limit = int(request.args.get("limit", 100))
    except (TypeError, ValueError):
        limit = 100

    rows = get_usage_rows(user_id, start_date=start_date, end_date=end_date, limit=limit)
    summary = get_usage_summary(user_id, start_date=start_date, end_date=end_date)

    # Serialize datetimes to ISO strings
    serialized = []
    for row in rows:
        r = dict(row)
        if hasattr(r.get("created"), "isoformat"):
            r["created"] = r["created"].isoformat()
        serialized.append(r)

    return jsonify({
        "object": "list",
        "data": serialized,
        "summary": {
            **summary,
            "period_start": start_date,
            "period_end": end_date,
        },
    })


@app.route("/v1/models", methods=["GET"])
@valid_api_key_required
def v1_list_models():
    """Return the list of models that this server supports (OpenAI format)."""
    now = int(__import__("time").time())
    data = [
        {
            "id": m,
            "object": "model",
            "created": now,
            "owned_by": "anote-ai",
        }
        for m in _SUPPORTED_MODELS
    ]
    return jsonify({"object": "list", "data": data})


@app.route("/v1/chat/completions", methods=["POST"])
@valid_api_key_required
def v1_chat_completions():  # pragma: no cover
    """OpenAI-compatible chat completions endpoint.

    Required body fields:
        model    – model name (any value from /v1/models)
        messages – list of {"role": "user"|"assistant"|"system", "content": "…"}

    Optional body fields:
        chat_id  – integer chat / session ID.  When provided the answer is
                   grounded in the documents that were uploaded to that chat.
        stream   – boolean (default false).  Streaming is not yet supported
                   through this compatibility shim; set to false.
    """
    import time
    from api_endpoints.schemas import ChatCompletionsRequest
    from pydantic import ValidationError as _ValidationError

    try:
        req = ChatCompletionsRequest.model_validate(request.get_json(force=True) or {})
    except _ValidationError as exc:
        return jsonify({"error": {"message": str(exc), "type": "validation_error"}}), 422

    model = req.model
    messages: list[dict] = [m.model_dump() for m in req.messages]
    chat_id = req.chat_id
    stream = req.stream

    if not messages:
        return jsonify({"error": {"message": "messages is required", "type": "invalid_request_error"}}), 400

    # Extract the last user message as the primary query
    user_message = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            content = m.get("content", "")
            if isinstance(content, list):
                # Multimodal content blocks – concatenate text parts
                user_message = " ".join(
                    block.get("text", "") for block in content if block.get("type") == "text"
                )
            else:
                user_message = str(content)
            break

    if not user_message:
        return jsonify({"error": {"message": "No user message found in messages", "type": "invalid_request_error"}}), 400

    # Build conversation history for context (all but the last user turn)
    history_pairs: list[dict] = []
    for m in messages[:-1]:
        if m.get("role") in ("user", "assistant"):
            history_pairs.append({"role": m["role"], "content": m.get("content", "")})

    # Determine which provider / model to use
    is_anthropic = model.startswith("claude")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

    answer = ""
    prompt_tokens = 0
    completion_tokens = 0

    try:
        if chat_id:
            # ------------------------------------------------------------------
            # Grounded answer: retrieve relevant document chunks first
            # ------------------------------------------------------------------
            user_email = USER_EMAIL_API
            ensure_SDK_user_exists(user_email)

            add_message_to_db(user_message, chat_id, 1)
            sources = get_relevant_chunks(2, user_message, chat_id, user_email, include_metadata=True)
            sources_str = sources_to_prompt_context(sources)

            system_prompt = (
                "You are a helpful assistant that answers questions grounded in the "
                "provided document context.  Only use facts from the context below.  "
                "If the answer is not in the context, say you don't know.\n\n"
                f"Context:\n{sources_str}"
            )

            if is_anthropic:
                from anthropic import Anthropic as _Anthropic
                _client = _Anthropic(api_key=anthropic_api_key)
                resp = _client.messages.create(
                    model=model,
                    max_tokens=1024,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )
                answer = resp.content[0].text
                prompt_tokens = resp.usage.input_tokens
                completion_tokens = resp.usage.output_tokens
            else:
                import openai as _openai
                _client = _openai.OpenAI(api_key=openai_api_key)
                resp = _client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                )
                answer = resp.choices[0].message.content
                if resp.usage:
                    prompt_tokens = resp.usage.prompt_tokens
                    completion_tokens = resp.usage.completion_tokens

            message_id = add_message_to_db(answer, chat_id, 0)
            try:
                add_sources_to_db(message_id, sources)
            except Exception:
                pass

            sources_payload = serialize_sources_for_api(sources)
        else:
            # ------------------------------------------------------------------
            # Plain chat completion (no document grounding)
            # ------------------------------------------------------------------
            sources_payload = []
            message_id = None

            # Convert history + system messages into provider format
            formatted: list[dict] = []
            for m in messages:
                role = m.get("role", "user")
                content = m.get("content", "")
                if isinstance(content, list):
                    content = " ".join(
                        block.get("text", "") for block in content if block.get("type") == "text"
                    )
                formatted.append({"role": role, "content": content})

            if is_anthropic:
                from anthropic import Anthropic as _Anthropic
                _client = _Anthropic(api_key=anthropic_api_key)
                # Separate system messages from the conversation
                system_msgs = [m["content"] for m in formatted if m["role"] == "system"]
                conv_msgs = [m for m in formatted if m["role"] != "system"]
                system_text = "\n".join(system_msgs) if system_msgs else "You are a helpful assistant."
                resp = _client.messages.create(
                    model=model,
                    max_tokens=1024,
                    system=system_text,
                    messages=conv_msgs,
                )
                answer = resp.content[0].text
                prompt_tokens = resp.usage.input_tokens
                completion_tokens = resp.usage.output_tokens
            else:
                import openai as _openai
                _client = _openai.OpenAI(api_key=openai_api_key)
                resp = _client.chat.completions.create(model=model, messages=formatted)
                answer = resp.choices[0].message.content
                if resp.usage:
                    prompt_tokens = resp.usage.prompt_tokens
                    completion_tokens = resp.usage.completion_tokens

    except Exception as exc:
        return jsonify({
            "error": {
                "message": str(exc),
                "type": "server_error",
                "code": "internal_error",
            }
        }), 500

    # ------------------------------------------------------------------
    # Log usage (best-effort — never fails the request)
    # ------------------------------------------------------------------
    try:
        from database.usage import log_api_usage, user_and_key_ids_for_api_key as _uid_kid
        _raw_key = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
        _uid, _kid = _uid_kid(_raw_key)
        log_api_usage(
            user_id=_uid,
            api_key_id=_kid,
            endpoint="/v1/chat/completions",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            credits_used=1,
        )
    except Exception:
        pass

    # ------------------------------------------------------------------
    # Build OpenAI-compatible response envelope
    # ------------------------------------------------------------------
    completion_id = f"chatcmpl-anote-{int(time.time())}"
    response_body = {
        "id": completion_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": answer,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        # Anote-specific extension fields
        "anote": {
            "message_id": message_id,
            "sources": sources_payload,
        },
    }

    if stream:
        # Return a minimal SSE stream with a single data chunk + [DONE]
        def _stream():
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [{"index": 0, "delta": {"role": "assistant", "content": answer}, "finish_reason": "stop"}],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return Response(_stream(), mimetype="text/event-stream")

    return jsonify(response_body)


@app.route("/v1/question-answer", methods=["POST"])
@valid_api_key_required
def v1_question_answer():  # pragma: no cover
    """Simple stateless Q&A endpoint — no chat session required.

    Upload documents via /public/upload first to get a chat_id, then call
    this endpoint to ask questions against those documents.

    Body:
        question  (str)  – the question to answer
        chat_id   (int)  – session ID from /public/upload
        model     (str)  – optional model name (default: gpt-4o)
    """
    body = request.get_json(force=True) or {}
    question = body.get("question", "").strip()
    chat_id = body.get("chat_id")
    model = body.get("model", "gpt-4o")

    if not question:
        return jsonify({"error": "question is required"}), 400
    if not chat_id:
        return jsonify({"error": "chat_id is required — upload documents first via /public/upload"}), 400

    # Delegate to the chat completions handler logic
    request_body = {
        "model": model,
        "messages": [{"role": "user", "content": question}],
        "chat_id": chat_id,
        "stream": False,
    }
    # Temporarily swap request JSON so v1_chat_completions can read it
    with app.test_request_context(
        "/v1/question-answer",
        method="POST",
        json=request_body,
        headers={"Authorization": request.headers.get("Authorization", "")},
    ):
        from flask import g as _g
        pass

    # Direct implementation (avoids nested request context complexity)
    user_email = USER_EMAIL_API
    ensure_SDK_user_exists(user_email)

    add_message_to_db(question, chat_id, 1)
    sources = get_relevant_chunks(2, question, chat_id, user_email, include_metadata=True)
    sources_str = sources_to_prompt_context(sources)

    is_anthropic = model.startswith("claude")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    system_prompt = (
        "You are a helpful assistant that answers questions grounded in the "
        "provided document context. Only use facts from the context below. "
        "If the answer is not in the context, say you don't know.\n\n"
        f"Context:\n{sources_str}"
    )

    try:
        if is_anthropic:
            from anthropic import Anthropic as _Anthropic
            _client = _Anthropic(api_key=anthropic_api_key)
            resp = _client.messages.create(
                model=model,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": question}],
            )
            answer = resp.content[0].text
        else:
            import openai as _openai
            _client = _openai.OpenAI(api_key=openai_api_key)
            resp = _client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ],
            )
            answer = resp.choices[0].message.content
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    message_id = add_message_to_db(answer, chat_id, 0)
    try:
        add_sources_to_db(message_id, sources)
    except Exception:
        pass

    return jsonify({
        "answer": answer,
        "message_id": message_id,
        "sources": serialize_sources_for_api(sources),
        "model": model,
        "question": question,
    })


if __name__ == '__main__':
    debug_mode = os.getenv("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
