from flask import Flask, request, jsonify, Response, abort, redirect, stream_with_context, Blueprint, send_file
from flask_cors import CORS, cross_origin
from api_endpoints.login.handler import LoginHandler, SignUpHandler, ForgotPasswordHandler, ResetPasswordHandler
import os
import pathlib
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from pip._vendor import cachecontrol
import google.auth.transport.requests
import json
import jwt
import requests
from database.db_auth import api_key_access_invalid
from flask_jwt_extended import jwt_required, create_access_token, create_refresh_token, decode_token, JWTManager, get_jwt_identity
from flask_mail import Mail
from jwt import InvalidTokenError
from urllib.parse import urlparse
from database.db import create_user_if_does_not_exist
from constants.global_constants import kSessionTokenExpirationTime
from database.db_auth import extractUserEmailFromRequest, is_api_key_valid, user_id_for_email, verifyAuthForPaymentsTrustedTesters, verifyAuthForCheckoutSession, verifyAuthForPortalSession
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request
from api_endpoints.payments.handler import CreateCheckoutSessionHandler, CreatePortalSessionHandler, StripeWebhookHandler
from api_endpoints.refresh_credits.handler import RefreshCreditsHandler
from api_endpoints.user.handler import ViewUserHandler
from api_endpoints.generate_api_key.handler import GenerateAPIKeyHandler
from api_endpoints.delete_api_key.handler import DeleteAPIKeyHandler
from api_endpoints.get_api_keys.handler import GetAPIKeysHandler
from enum import Enum
import stripe
from dotenv import load_dotenv
import ray
import csv
import openai
import shutil
import io
from tika import parser as p
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
import re
from bs4 import BeautifulSoup
from flask_mysql_connector import MySQL
import MySQLdb.cursors
from nltk.translate.bleu_score import sentence_bleu
from datasets import load_dataset
import nltk

from database.db import get_db_connection

#WESLEY
from api_endpoints.financeGPT.chatbot_endpoints import \
    add_chat_to_db, add_message_to_db, chunk_document, add_document_to_db, get_relevant_chunks, \
    retrieve_chats_from_db, create_chat_shareable_url, access_sharable_chat, _get_model, \
    delete_chat_from_db, retrieve_message_from_db, retrieve_docs_from_db, add_sources_to_db, delete_doc_from_db, reset_chat_db, change_chat_mode_db, update_chat_name_db, \
    reset_uploaded_docs, add_model_key_to_db, \
    add_chat_to_db, add_message_to_db, chunk_document, add_document_to_db, get_relevant_chunks, \
    retrieve_chats_from_db, delete_chat_from_db, retrieve_message_from_db, retrieve_docs_from_db, add_sources_to_db, delete_doc_from_db, reset_chat_db, \
    change_chat_mode_db, update_chat_name_db, find_most_recent_chat_from_db, \
    ensure_SDK_user_exists, get_chat_info, get_message_info, get_text_from_url

_get_model()
from agents.reactive_agent import ReactiveDocumentAgent
from agents.config import AgentConfig

from datetime import datetime

from api_endpoints.languages.gtm import gpt4_blueprint
from api_endpoints.languages.chinese import chinese_blueprint
from api_endpoints.languages.japanese import japanese_blueprint
from api_endpoints.languages.korean import korean_blueprint
from api_endpoints.languages.spanish import spanish_blueprint
from api_endpoints.languages.arabic import arabic_blueprint
from datetime import datetime

load_dotenv(override=True)

app = Flask(__name__)
app.register_blueprint(gpt4_blueprint)
app.register_blueprint(chinese_blueprint)
app.register_blueprint(japanese_blueprint)
app.register_blueprint(korean_blueprint)
app.register_blueprint(spanish_blueprint)
app.register_blueprint(arabic_blueprint)

#if ray.is_initialized() == False:
   #ray.init(logging_level="INFO", log_to_driver=True)
   
# Initialize OpenAI client with fallback for missing API key
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    client = openai.OpenAI(api_key=openai_api_key, base_url="http://host.docker.internal:11434/v1")
else:
    print("Warning: OPENAI_API_KEY not set. Some features may not work.")
    client = None
def ensure_ray_started():
    if not ray.is_initialized():
        try:
            ray.init(
                logging_level="INFO",
                log_to_driver=True,
                ignore_reinit_error=True  # Helpful when running in dev
            )
        except Exception as e:
            print(f"Ray init failed: {e}")

# ensure_ray_started()
# TODO: Replace with your URLs.
config = {
  'ORIGINS': [
    'http://localhost:3000',  # React
    'http://localhost:3001',  # React on port 3001
    'http://localhost:5000',
    'http://localhost:8000',
    'http://localhost:5050',
    'http://dashboard.localhost:3000',  # React
    'https://anote.ai', # Frontend prod URL,
    'https://privatechatbot.ai', # Frontend prod URL,
    'https://dashboard.privatechatbot.ai', # Frontend prod URL,
  ],
}

CORS(app, resources={ r'/*': {'origins': config['ORIGINS']}}, supports_credentials=True)

app.secret_key = '6cac159dd02c902f822635ee0a6c3078'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_HTTPONLY'] = False
app.config["JWT_SECRET_KEY"] = "6cac159dd02c902f822635ee0a6c3078"
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = kSessionTokenExpirationTime
app.config["JWT_TOKEN_LOCATION"] = "headers"
app.config.from_object(__name__)

jwt_manager = JWTManager(app)
app.jwt_manager = jwt_manager

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'vidranatan@gmail.com'
app.config['MAIL_PASSWORD'] = 'fhytlgpsjyzutlnm'
app.config['MAIL_DEFAULT_SENDER'] = 'vidranatan@gmail.com'
mail = Mail(app)


#MySQL config -- could put these in a backend .env if there are different users
app.config['MYSQL_HOST'] = 'db'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DATABASE'] = 'agents'

mysql = MySQL(app)

# Initialize Stripe with fallback for missing API key
stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
if stripe_secret_key:
    stripe.api_key = stripe_secret_key
else:
    print("Warning: STRIPE_SECRET_KEY not set. Payment features will not work.")

ensure_ray_started()

def valid_api_key_required(fn):
  @wraps(fn)
  def wrapper(*args, **kwargs):
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        splits = auth_header.split(' ')
        if len(splits) > 1:
          api_key = auth_header.split(' ')[1]
          if is_api_key_valid(api_key):
            # If api key is valid, return the decorated function
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
    return access_sharable_chat(playbook_url)

@app.route('/health', methods=['GET'])
def health_check():
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

      state_dict = {
        "redirect_uri": flow.redirect_uri
      }

      if request.args.get('product_hash'):
        print("during checking product hash")
        state_dict["product_hash"] = request.args.get('product_hash')
      if request.args.get('free_trial_code'):
        print("during checking free_trial_code")
        state_dict["free_trial_code"] = request.args.get('free_trial_code')

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

    # TODO: COMMENT OUT WHEN DEPLOY TO PROD
    default_referrer = os.getenv("DEFAULT_REFERRER")
    # default_referrer = "https://dashboard.privatechatbot.ai"
    if not default_referrer:
        default_referrer = "http://dashboard.localhost:3000"
    user_id = create_user_if_does_not_exist(id_info.get("email"), id_info.get("sub"), id_info.get("name"), id_info.get("picture"))

    access_token = create_access_token(identity=id_info.get("email"))
    refresh_token = create_refresh_token(identity=id_info.get("email"))
    productGetParam = ""
    if product_hash is not None:
      productGetParam = "&" + "product_hash=" + product_hash
    freeTrialCodeGetParam = ""
    if free_trial_code is not None:
      freeTrialCodeGetParam = "&" + "free_trial_code=" + free_trial_code

    print("request.referrer")
    print(request.referrer)
    # response = redirect(
    #   (request.referrer or default_referrer) +
    #   "?accessToken=" + access_token + "&"
    #   "refreshToken=" + refresh_token
    # )
    response = redirect(
      (default_referrer) +
      "?accessToken=" + access_token + "&"
      "refreshToken=" + refresh_token + productGetParam + freeTrialCodeGetParam
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
@jwt_or_session_token_required
def RefreshCredits():
  try:
    user_email = extractUserEmailFromRequest(request)
  except InvalidTokenError:
    # If the JWT is invalid, return an error
    return jsonify({"error": "Invalid JWT"}), 401
  return jsonify(RefreshCreditsHandler(request, user_email))

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
def get_links(initial_url: str):
    # Send a GET request to the website's URL
    response = requests.get(initial_url)

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

# Helper function to extract text from a URL
def get_text_from_url(web_url):
    response = requests.get(web_url)
    result = p.from_buffer(response.content)
    text = result.get("content", "").strip()
    return text.replace("\n", "").replace("\t", "")

## CHATBOT SECTION
output_document_path = 'output_document'
chat_history_file = os.path.join(output_document_path, 'chat_history.csv')
vector_base_path = 'db'
source_documents_path = 'source_documents'

@app.route('/api/reset-everything', methods=['POST']) #Change this to use MYSQL db
def reset_everything():
    try:
        # Delete vector database
        #shutil.rmtree(vector_base_path)
        # Delete user input documents
        if os.path.exists(source_documents_path):
            shutil.rmtree(source_documents_path)
        # Delete chat history
        if os.path.exists(output_document_path):
            shutil.rmtree(output_document_path)
            # Recreate the output folder
            os.makedirs(output_document_path)

        # Create an empty chat history CSV file
        chat_history_file_path = os.path.join(output_document_path, 'chat_history.csv')
        with open(chat_history_file_path, 'w', newline='') as csvfile:
            print("test1")
            writer = csv.writer(csvfile)
            writer.writerow(['query', 'response'])

        return 'Reset was successful!'
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

        paired_messages = []

        for i in range(len(messages) - 1):
            if messages[i]['sent_from_user'] == 1 and messages[i+1]['sent_from_user'] == 0:
                regex = re.compile(r"Document:\s*[^:]+:\s*(.*?)(?=Document:|$)", re.DOTALL)
                if messages[i+1]["relevant_chunks"]:
                    found = re.findall(regex, messages[i+1]["relevant_chunks"])
                    paragraphs = [paragraph.strip() for paragraph in found]
                    if len(paragraphs) > 1:
                        paired_messages.append((messages[i]['message_text'], messages[i+1]['message_text'], paragraphs[0], paragraphs[1]))
                    elif len(paragraphs) == 1:
                        paired_messages.append((messages[i]['message_text'],  messages[i+1]['message_text'], paragraphs[0], None))
                else:
                    paired_messages.append((messages[i]['message_text'], messages[i+1]['message_text'], None, None))


        csv_output = io.StringIO()
        writer = csv.writer(csv_output)
        writer.writerow(['query', 'response', 'chunk1', 'chunk2'])  # Write header
        writer.writerows(paired_messages)
        csv_output.seek(0)  # Go back to the start of the StringIO object

        return Response(
            csv_output.getvalue(),
            mimetype='text/csv',
            headers={"Content-disposition": "attachment; filename=chat_history.csv"}
        )
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

    chat_type = request.json.get('chat_type')
    model_type = request.json.get('model_type')

    chat_id = add_chat_to_db(user_email, chat_type, model_type) #for now hardcode the model type as being 0

    return jsonify(chat_id=chat_id)

@app.route('/retrieve-all-chats', methods=['POST'])
def retrieve_chats():
    #Given an input of a chat_type and user_email, it will return as a list of dictionaries all the chats of that user and chat type from the db

    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401
    #chat_type = request.json.get('chat_type')

    chat_info = retrieve_chats_from_db(user_email)

    return jsonify(chat_info=chat_info)

@app.route('/retrieve-messages-from-chat', methods=['POST'])
def retrieve_messages_from_chat():
    #Getting current user not working, fix this later
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    chat_type = request.json.get('chat_type')
    chat_id = request.json.get('chat_id')

    messages = retrieve_message_from_db(user_email, chat_id, chat_type)
    chat_name = get_chat_info(chat_id)[2]
    print("chat_name", chat_name[2])
    return jsonify({
        "messages": messages,
        "chat_name": chat_name
    })

@app.route('/retrieve-shared-messages-from-chat', methods=['POST'])
def get_playbook_messages():
    chat_type = 0
    chat_id = request.json.get('chat_id')

    messages = retrieve_message_from_db("anon@anote.ai", chat_id, chat_type)

    return jsonify(messages=messages)

@app.route('/update-chat-name', methods=['POST'])
def update_chat_name():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    chat_name = request.json.get('chat_name')
    chat_id = request.json.get('chat_id')

    print("chat_name", chat_name)

    update_chat_name_db(user_email, chat_id, chat_name)

    return jsonify({"Success": "Chat name updated"}), 200

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

    update_chat_name_db(user_email, chat_id, new_name)

    return jsonify(chat_name=new_name)


@app.route('/delete-chat', methods=['POST'])
def delete_chat():
    chat_id = request.json.get('chat_id')

    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    return delete_chat_from_db(chat_id, user_email)


@app.route('/find-most-recent-chat', methods=['POST'])
def find_most_recent_chat():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    chat_info = find_most_recent_chat_from_db(user_email)

    return jsonify(chat_info=chat_info)


@app.route('/ingest-pdf', methods=['POST'])
def ingest_pdfs():
    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
        # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    start_time = datetime.now()
    print("start time is", start_time)

    chat_id = request.form.getlist('chat_id')[0]
    files = request.files.getlist('files[]')

    MAX_CHUNK_SIZE = 1000

    print("before files loop time is", datetime.now() - start_time)
    for file in files:
        #text = get_text_from_single_file(file)
        #text_pages = get_text_pages_from_single_file(file)

        result = p.from_buffer(file)
        text = result["content"].strip()

        filename = file.filename

        doc_id, doesExist = add_document_to_db(text, filename, chat_id=chat_id)

        if not doesExist:
            chunk_document.remote(text, MAX_CHUNK_SIZE, doc_id)


    return jsonify({"Success": "Document Uploaded"}), 200


    #return text, filename

@app.route('/retrieve-current-docs', methods=['POST'])
def retrieve_current_docs():
    chat_id = request.json.get('chat_id')

    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    doc_info = retrieve_docs_from_db(chat_id, user_email)

    return jsonify(doc_info=doc_info)

@app.route('/delete-doc', methods=['POST'])
def delete_doc():
    doc_id = request.json.get('doc_id')

    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    delete_doc_from_db(doc_id, user_email)

    return "success"

@app.route('/change-chat-mode', methods=['POST'])
def change_chat_mode_and_reset_chat():
    chat_mode_to_change_to = request.json.get('model_type')
    chat_id = request.json.get('chat_id')

    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    try:
        reset_chat_db(chat_id, user_email)
        change_chat_mode_db(chat_mode_to_change_to, chat_id, user_email)

        return "Success"
    except:
        return "Error"

@app.route('/reset-chat', methods=['POST'])
def reset_chat():
    chat_id = request.json.get('chat_id')
    delete_docs = request.json.get('delete_docs')

    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
    # If the JWT is invalid, return an error
        return jsonify({"error": "Invalid JWT"}), 401

    if delete_docs:
        reset_uploaded_docs(chat_id, user_email)

    reset_chat_db(chat_id, user_email)

    return jsonify({"Success": "Success"}), 200

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

@app.route('/process-message-pdf', methods=['POST'])
def process_message_pdf():
    message = request.json.get('message')
    chat_id = request.json.get('chat_id')
    model_type = request.json.get('model_type', 0)
    model_key = request.json.get('model_key')

    try:
        user_email = extractUserEmailFromRequest(request)
    except InvalidTokenError:
        return jsonify({"error": "Invalid JWT"}), 401

    # Check if agents are enabled
    if AgentConfig.is_agent_enabled():
        try:
            # Initialize the reactive agent
            agent = ReactiveDocumentAgent(model_type=model_type, model_key=model_key)

            # Process the query using the reactive agent
            if not user_email or not isinstance(user_email, str):
                return jsonify({"error": "User email is missing or invalid"}), 401

            result = agent.process_query_stream(message.strip(), chat_id, user_email)
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
                return _process_message_pdf_fallback(message, chat_id, model_type, model_key, user_email)
            else:
                return jsonify({"error": "Agent processing failed due to an internal error."}), 500
    else:
        # Agents disabled, use original implementation
        return _process_message_pdf_fallback(message, chat_id, model_type, model_key, user_email)

def _process_message_pdf_fallback(message, chat_id, model_type, model_key, user_email):
    """Fallback implementation using the original direct LLM approach without the ReActive Agent"""
    query = message.strip()

    #This adds user message to db
    add_message_to_db(query, chat_id, 1)

    #Get most relevant section from the document
    sources = get_relevant_chunks(2, query, chat_id, user_email)
    sources_str = " ".join([", ".join(str(elem) for elem in source) for source in sources])

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

        anthropic = Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )

        completion = anthropic.completions.create(
            model="claude-2",
            max_tokens_to_sample=700,
            prompt = (
              f"{HUMAN_PROMPT} "
              f"You are a factual chatbot that answers questions about uploaded documents. You only answer with answers you find in the text, no outside information. "
              f"please address the question: {query}. "
              f"Consider the provided text as evidence: {sources_str}. "
              f"{AI_PROMPT}")
        )
        answer = completion.completion

    #This adds bot message
    message_id = add_message_to_db(answer, chat_id, 0)

    try:
        add_sources_to_db(message_id, sources)
    except:
        print("no sources")

    return jsonify(answer=answer)

# Only for demo purposes
chat_to_document_mapping = {}
#DEMO_CHAT_ID = 99999
DEMO_USER_EMAIL = "demo@example.com"
chat_id = 0

@app.route('/process-message-pdf-demo', methods=['POST'])
def process_message_pdf_demo():
    message = request.json.get('message')
    query = message.strip()

    global chat_id
    user_email = DEMO_USER_EMAIL

    print("CHAT ID IS", chat_id)

    add_message_to_db(query, chat_id, 1)

    sources = get_relevant_chunks(2, query, chat_id, user_email)
    print('sources is', sources)
    sources_str = " ".join([", ".join(str(elem) for elem in source) for source in sources])
    print('sources_str is', sources_str)



    completion = client.chat.completions.create(
        model="llama2:latest",
        messages=[
            {"role": "user",
             "content": f"You are a factual chatbot that answers questions about uploaded documents. You only answer with answers you find in the text, no outside information. These are the sources from the text:{sources_str} And this is the question:{query}."}
        ]
    )
    answer = str(completion.choices[0].message.content)

    message_id = add_message_to_db(answer, chat_id, 0)

    try:
        add_sources_to_db(message_id, sources)
    except:
        print("no sources")

    return jsonify(answer=answer)


@app.route('/ingest-pdf-demo', methods=['POST'])
def ingest_pdfs_demo():
    global chat_id
    user_email = DEMO_USER_EMAIL

    #create_new_demo_chat(chat_id, user_email)

    files = request.files.getlist('files[]')
    MAX_CHUNK_SIZE = 1000

    for file in files:
        result = p.from_buffer(file)  # Ensure your PDF extraction works as expected
        text = result["content"].strip()
        filename = file.filename

        # Assuming add_document_to_db and chunk_document.remote are implemented
        doc_id, doesExist = add_document_to_db(text, filename, chat_id=chat_id)
        if not doesExist:
            chunk_document.remote(text, MAX_CHUNK_SIZE, doc_id)

    # This mapping is now redundant since we're using a static demo_chat_id, but you could maintain it if you plan to extend functionality
    chat_to_document_mapping[chat_id] = doc_id

    return jsonify({"message": "Document processed successfully"}), 200

# @app.route('/reset-chat-demo', methods=['POST'])
# def reset_chat_demo():
#     global chat_id
#     user_email = DEMO_USER_EMAIL

#     ensure_demo_user_exists(user_email)

#     delete_chat_from_db(chat_id, user_email)

#     #create_new_demo_chat(chat_id, user_email)
#     chat_id = add_chat_to_db(user_email, 0, 0)

#     #reset_uploaded_docs(chat_id, user_email)

#     #reset_chat_db(chat_id, user_email)

#     return jsonify({"Success": "Success"}), 200

@app.route('/download-chat-history-demo', methods=['POST'])
def download_chat_history_demo():
    global chat_id
    user_email = DEMO_USER_EMAIL

    try:
        chat_type = 0

        messages = retrieve_message_from_db(user_email, chat_id, chat_type)

        print("messages", messages)

        paired_messages = []
        for i in range(len(messages) - 1):
            if messages[i]['sent_from_user'] == 1 and messages[i+1]['sent_from_user'] == 0:
                regex = re.compile(r"Document:\s*[^:]+:\s*(.*?)(?=Document:|$)", re.DOTALL)
                if messages[i+1]["relevant_chunks"]:
                    found = re.findall(regex, messages[i+1]["relevant_chunks"])
                    paragraphs = [paragraph.strip() for paragraph in found]
                    if len(paragraphs) > 1:
                        paired_messages.append((messages[i]['message_text'], messages[i+1]['message_text'], paragraphs[0], paragraphs[1]))
                    elif len(paragraphs) == 1:
                        paired_messages.append((messages[i]['message_text'],  messages[i+1]['message_text'], paragraphs[0], None))
                else:
                    paired_messages.append((messages[i]['message_text'], messages[i+1]['message_text'], None, None))

        csv_output = io.StringIO()
        writer = csv.writer(csv_output)
        writer.writerow(['query', 'response', 'chunk1', 'chunk2'])
        writer.writerows(paired_messages)
        csv_output.seek(0)

        # Return the CSV content as a response
        return Response(
            csv_output.getvalue(),
            mimetype='text/csv',
            headers={"Content-disposition": "attachment; filename=chat_history.csv"}
        )
    except Exception as e:
        print("error is,", str(e))
        return jsonify({"error": str(e)}), 500


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


#Edgar
@app.route('/temp-test', methods=['POST'])
def temp_test():

    anthropic = Anthropic(
      api_key=os.getenv("ANTHROPIC_API_KEY")
    )


    query = "What are some of the risk factors from the company?"

    sources = ["The Company’s business, reputation, results of operations, financial condition and stock price can be affected by a number of factors, whether currently known or unknown, including those described below. When any one or more of these risks materialize from time to time, the Company’s business, reputation, results of operations, financial condition and stock price can be materially and adversely affected. Because of the following factors, as well as other factors affecting the Company’s results of operations and financial condition, past financial performance should not be considered to be a reliable indicator of future performance, and investors should not use historical trends to anticipate results or trends in future periods. This discussion of risk factors contains forward-looking statements. This section should be read in conjunction with Part II, Item 7, “Management’s Discussion and Analysis of Financial Condition and Results of Operations” and the consolidated financial statements and accompanying notes in Part II, Item 8, “Financial Statements and Supplementary Data” of this Form 10-K.", "The Company’s operations and performance depend significantly on global and regional economic conditions and adverse economic conditions can materially adversely affect the Company’s business, results of operations and financial condition. The Company has international operations with sales outside the U.S. representing a majority of the Company’s total net sales. In addition, the Company’s global supply chain is large and complex and a majority of the Company’s supplier facilities, including manufacturing and assembly sites, are located outside the U.S. As a result, the Company’s operations and performance depend significantly on global and regional economic conditions."]

    completion = anthropic.completions.create(
      model="claude-2",
      max_tokens_to_sample=700,
      prompt = (
        f"{HUMAN_PROMPT} "
        f"You are a factual chatbot that answers questions about 10-K documents. You only answer with answers you find in the text, no outside information. "
        f"please address the question: {query}. "
        f"Consider the provided text as evidence: {sources[0]}{sources[1]}. "
        f"{AI_PROMPT}")
    )

    print("anthropic result", completion.completion)

    return 'success'



## API Keys

@app.route("/generateAPIKey", methods=["POST"])
@jwt_or_session_token_required
def generateAPIKey():
  try:
    user_email = extractUserEmailFromRequest(request)
  except InvalidTokenError:
    # If the JWT is invalid, return an error
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
  try:
    user_email = extractUserEmailFromRequest(request)
  except InvalidTokenError:
    # If the JWT is invalid, return an error
    return jsonify({"error": "Invalid JWT"}), 401
  return GetAPIKeysHandler(request, user_email)


#For the SDK
#later will need to add @valid_api_key_required to all

USER_EMAIL_API = "api@example.com"

@app.route('/public/upload', methods = ['POST'])
@valid_api_key_required
def upload():
    print("Form data:", request.form)
    print("Files:", request.files)

    #chat_type = int(request.form.getlist('task_type')[0])  # Convert to int
    #model_type = int(request.form.getlist('model_type')[0])

    chat_type = request.form.getlist('task_type')[0]
    model_type = request.form.getlist('model_type')[0]

    user_email = USER_EMAIL_API

    print("CHAT TYPE IS", chat_type)
    if chat_type == "documents": #question-answering
        print("question answer")
        files = request.files.getlist('files[]')
        paths = request.form.getlist('html_paths')

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
        return jsonify({"id": "Please enter a valid task type"}), 400

    return jsonify({"id": chat_id}), 200


@app.route('/public/chat', methods=['POST'])
@valid_api_key_required
def public_ingest_pdf():
    user_email = USER_EMAIL_API
    ensure_SDK_user_exists(user_email)

    message = request.json['message']
    chat_id = request.json['chat_id']
    model_key = request.json.get('model_key')

    model_type, task_type = get_chat_info(chat_id)

    if AgentConfig.is_agent_enabled():
        try:
            # Use reactive agent for public API
            agent = ReactiveDocumentAgent(model_type=model_type, model_key=model_key)
            result = agent.process_query(message.strip(), chat_id, user_email)

            # Format sources for compatibility
            sources_swapped = [[str(elem) for elem in source[::-1]] for source in result.get("sources", [])]

            return jsonify(
                message_id=result.get("message_id"),
                answer=result["answer"],
                sources=sources_swapped
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

def _public_chat_fallback(message, chat_id, model_type, model_key, user_email):
    """Fallback implementation for public chat API"""
    query = message.strip()

    #This adds user message to db
    add_message_to_db(query, chat_id, 1)

    #Get most relevant section from the document
    sources = get_relevant_chunks(2, query, chat_id, user_email)
    sources_str = " ".join([", ".join(str(elem) for elem in source) for source in sources])

    sources_swapped = [[str(elem) for elem in source[::-1]] for source in sources]

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

        anthropic = Anthropic(api_key = os.getenv("ANTHROPIC_API_KEY"))
        completion = anthropic.completions.create(
            model="claude-2",
            max_tokens_to_sample=700,
            prompt = (
              f"{HUMAN_PROMPT} "
              f"You are a factual chatbot that answers questions about uploaded documents. You only answer with answers you find in the text, no outside information. "
              f"please address the question: {query}. "
              f"Consider the provided text as evidence: {sources_str}. "
              f"{AI_PROMPT}")
        )
        answer = completion.completion

    #This adds bot message
    message_id = add_message_to_db(answer, chat_id, 0)

    try:
        add_sources_to_db(message_id, sources)
    except:
        print("no sources")

    return jsonify(message_id=message_id, answer=answer, sources=sources_swapped)

@app.route('/public/evaluate', methods = ['POST'])
@valid_api_key_required
def evaluate():
    message_id = request.json['message_id']
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

# Leaderboard functionality
def get_bleu(translations, references, weights=(0.5, 0.5, 0, 0)):
    """Calculate BLEU score for translation evaluation"""
    bleu_scores = [
        sentence_bleu([ref.split()], trans.split(), weights=weights)
        for ref, trans in zip(references, translations)
    ]
    return sum(bleu_scores) / len(bleu_scores)

def get_bertscore(predictions, references):
    """Calculate BERTScore F1 for translation evaluation"""
    try:
        from bert_score import BERTScorer
        scorer = BERTScorer(model_type='bert-base-multilingual-cased')
        P, R, F1 = scorer.score(predictions, references)
        return F1.mean().item()
    except ImportError:
        print("Warning: bert_score not installed. Install with: pip install bert_score")
        return 0.0
    except Exception as e:
        print(f"Error calculating BERTScore: {str(e)}")
        return 0.0

@app.route('/public/get_leaderboard', methods=['GET'])
def get_leaderboard():
    """Get leaderboard showing model submissions and scores"""
    try:
        dataset_name = request.args.get('dataset')
        limit = int(request.args.get('limit', 100))
        
        conn, cursor = get_db_connection()
        
        try:
            # First, get all active datasets to ensure we show them all
            cursor.execute("SELECT name, task_type, evaluation_metric FROM benchmark_datasets WHERE active = TRUE ORDER BY name")
            all_datasets = cursor.fetchall()
            
            if dataset_name:
                query = """
                    SELECT 
                        ms.model_name,
                        bd.name as dataset_name,
                        bd.task_type,
                        bd.evaluation_metric,
                        er.score,
                        ms.created as submitted_at
                    FROM model_submissions ms
                    JOIN benchmark_datasets bd ON ms.benchmark_dataset_id = bd.id
                    JOIN evaluation_results er ON er.model_submission_id = ms.id
                    WHERE bd.name = %s AND bd.active = TRUE
                    ORDER BY er.score DESC
                    LIMIT %s
                """
                cursor.execute(query, (dataset_name, limit))
            else:
                query = """
                    SELECT 
                        ms.model_name,
                        bd.name as dataset_name,
                        bd.task_type,
                        bd.evaluation_metric,
                        er.score,
                        ms.created as submitted_at
                    FROM model_submissions ms
                    JOIN benchmark_datasets bd ON ms.benchmark_dataset_id = bd.id
                    JOIN evaluation_results er ON er.model_submission_id = ms.id
                    WHERE bd.active = TRUE
                    ORDER BY bd.name, er.score DESC
                    LIMIT %s
                """
                cursor.execute(query, (limit,))
            
            results = cursor.fetchall()
            
            # Create a comprehensive leaderboard that includes all datasets
            leaderboard = []
            
            # Add submissions with scores
            for i, row in enumerate(results):
                leaderboard.append({
                    "rank": i + 1,
                    "model_name": row['model_name'],
                    "dataset_name": row['dataset_name'],
                    "task_type": row['task_type'],
                    "evaluation_metric": row['evaluation_metric'],
                    "score": float(row['score']),
                    "submitted_at": row['submitted_at'].isoformat() if row['submitted_at'] else None
                })
            
            # Add empty datasets (datasets with no submissions)
            submitted_dataset_names = {row['dataset_name'] for row in results}
            for dataset in all_datasets:
                if dataset['name'] not in submitted_dataset_names:
                    # Add placeholder entry for empty dataset
                    leaderboard.append({
                        "rank": None,
                        "model_name": None,
                        "dataset_name": dataset['name'],
                        "task_type": dataset['task_type'],
                        "evaluation_metric": dataset['evaluation_metric'],
                        "score": None,
                        "submitted_at": None,
                        "is_empty": True  # Flag to indicate no submissions
                    })
            
            return jsonify({
                "success": True,
                "leaderboard": leaderboard,
                "total_datasets": len(all_datasets)
            })
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f"Error in get_leaderboard: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

@app.route('/public/submit_model', methods=['POST'])
def submit_model():
    """
    Submit a model's results to a benchmark dataset for evaluation
    
    Expected JSON input:  
    {
        "benchmarkDatasetName": "flores_spanish_translation",
        "modelName": "my-model-v1", 
        "modelResults": ["Traducción 1", "Traducción 2", ...],
        "sentence_ids": [0, 1, 2, 3, 4]  // Required: specify which FLORES+ sentences were translated
    }
    
    Returns:
    {
        "success": true/false,
        "score": 0.543,
        "submission_id": 123,
        "error": "error message if any"
    }
    """
    try:
        # Parse request data
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400
        
        benchmark_dataset_name = data.get('benchmarkDatasetName')
        model_name = data.get('modelName')
        model_results = data.get('modelResults')
        sentence_ids = data.get('sentence_ids')  # Required: specific FLORES+ sentence positions
        
        # Validate required fields
        if not all([benchmark_dataset_name, model_name, model_results, sentence_ids]):
            return jsonify({
                "success": False,
                "error": "Missing required fields: benchmarkDatasetName, modelName, modelResults, sentence_ids"
            }), 400
        
        if not isinstance(model_results, list):
            return jsonify({
                "success": False,
                "error": "modelResults must be a list"
            }), 400
        
        # Get database connection
        conn, cursor = get_db_connection()
        
        try:
            # Check if benchmark dataset exists
            cursor.execute(
                "SELECT id, task_type, evaluation_metric, reference_data FROM benchmark_datasets WHERE name = %s AND active = TRUE",
                (benchmark_dataset_name,)
            )
            dataset = cursor.fetchone()
            
            if not dataset:
                return jsonify({
                    "success": False,
                    "error": f"Benchmark dataset '{benchmark_dataset_name}' not found"
                }), 404
            
            dataset_id = dataset['id']
            task_type = dataset['task_type']
            evaluation_metric = dataset['evaluation_metric']
            reference_data_str = dataset['reference_data']
            
            # Store model submission
            cursor.execute("""
                INSERT INTO model_submissions (benchmark_dataset_id, model_name, submitted_by, model_results)
                VALUES (%s, %s, %s, %s)
            """, (dataset_id, model_name, USER_EMAIL_API, json.dumps(model_results)))
            
            submission_id = cursor.lastrowid
            
            # Run evaluation based on the dataset type and metric
            if task_type == 'translation' and evaluation_metric in ['bleu', 'bertscore']:
                try:
                    # Handle FLORES+ datasets (Spanish, Japanese, Arabic, Chinese, Korean)
                    flores_datasets = {
                        'flores_spanish_translation': 'spa_Latn',
                        'flores_japanese_translation': 'jpn_Jpan', 
                        'flores_arabic_translation': 'arb_Arab',
                        'flores_chinese_translation': 'cmn_Hans',
                        'flores_korean_translation': 'kor_Hang'
                    }
                    
                    # BERTScore datasets (same language mappings)
                    flores_bertscore_datasets = {
                        'flores_spanish_translation_bertscore': 'spa_Latn',
                        'flores_japanese_translation_bertscore': 'jpn_Jpan',
                        'flores_arabic_translation_bertscore': 'arb_Arab', 
                        'flores_chinese_translation_bertscore': 'cmn_Hans',
                        'flores_korean_translation_bertscore': 'kor_Hang'
                    }
                    
                    all_flores_datasets = {**flores_datasets, **flores_bertscore_datasets}
                    
                    if benchmark_dataset_name in all_flores_datasets:
                        # FLORES+ evaluation logic for all supported languages
                        # Set HF token for dataset access (environment variable approach)
                        import os
                        hf_token = os.getenv("HF_TOKEN")
                        if hf_token:
                            os.environ["HF_TOKEN"] = hf_token
                        
                        # Load FLORES+ reference sentences for the target language
                        target_lang = all_flores_datasets[benchmark_dataset_name]
                        target_dataset = load_dataset("openlanguagedata/flores_plus", target_lang, split="devtest")
                        
                        # Use specific sentence positions (now required)
                        if len(sentence_ids) != len(model_results):
                            return jsonify({
                                "success": False,
                                "error": "Length of sentence_ids must match length of modelResults"
                            }), 400
                        reference_sentences = [target_dataset[idx]["text"] for idx in sentence_ids]
                        
                    else:
                        # Custom dataset evaluation logic
                        # Parse the reference data from database
                        reference_data = json.loads(reference_data_str)
                        
                        if 'reference_translations' not in reference_data:
                            return jsonify({
                                "success": False,
                                "error": "Dataset does not have reference translations"
                            }), 400
                        
                        all_reference_sentences = reference_data['reference_translations']
                        
                        # Use sentence_ids to get specific reference sentences
                        if len(sentence_ids) != len(model_results):
                            return jsonify({
                                "success": False,
                                "error": "Length of sentence_ids must match length of modelResults"
                            }), 400
                        
                        # Validate sentence_ids are within bounds
                        max_id = len(all_reference_sentences) - 1
                        for sid in sentence_ids:
                            if sid < 0 or sid > max_id:
                                return jsonify({
                                    "success": False,
                                    "error": f"sentence_id {sid} is out of range (0-{max_id})"
                                }), 400
                        
                        reference_sentences = [all_reference_sentences[idx] for idx in sentence_ids]
                    
                    # Calculate score based on evaluation metric
                    if evaluation_metric == 'bleu':
                        score = get_bleu(model_results, reference_sentences)
                    elif evaluation_metric == 'bertscore':
                        score = get_bertscore(model_results, reference_sentences)
                    
                except Exception as e:
                    print(f"{evaluation_metric.upper()} evaluation failed: {str(e)}")
                    return jsonify({
                        "success": False,
                        "error": f"{evaluation_metric.upper()} evaluation failed"
                    }), 500
            else:
                return jsonify({
                    "success": False,
                    "error": "Only translation tasks with BLEU or BERTScore metrics supported"
                }), 400
            
            # Store evaluation result
            cursor.execute("""
                INSERT INTO evaluation_results (model_submission_id, score, evaluation_details)
                VALUES (%s, %s, %s)
            """, (submission_id, score, json.dumps({"metric": evaluation_metric})))
            
            # Commit the transaction
            conn.commit()
            
            # Return spec-compliant response: success boolean + score
            return jsonify({
                "success": True,
                "score": score
            })
            
        finally:
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f"Error in submit_model: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

if __name__ == '__main__':
    debug_mode = os.getenv("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
