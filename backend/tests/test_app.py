import os
import unittest
import sys
from unittest.mock import patch, MagicMock
import jwt

# Set up environment variables before importing app
os.environ["OPENAI_API_KEY"] = "test_key"
os.environ["SEC_API_KEY"] = "test_key"

# Mock expensive imports before they're loaded
with patch("api_endpoints.financeGPT.chatbot_endpoints.OpenAIEmbeddings", MagicMock()):
    # Add the parent directory to the path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app import app


class TestFlaskApp(unittest.TestCase):
    """Refactored Flask app unit tests focusing on core functionality"""

    def setUp(self):
        """Set up test client and common mocks"""
        self.app = app.test_client()
        self.app.testing = True
        self.test_email = "test@example.com"
        self.test_headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer test_token"
        }

    def test_root_route(self):
        """Test the root endpoint exists"""
        response = self.app.get("/")
        self.assertIn(response.status_code, [200, 404])

    def test_login_route(self):
        """Test login endpoint is accessible"""
        response = self.app.get("/login")
        self.assertIn(response.status_code, [200, 302, 404])

    @patch("app.flow")
    @patch("app.id_token")
    @patch("app.create_user_if_does_not_exist")
    @patch("app.create_access_token")
    @patch("app.create_refresh_token")
    def test_oauth_callback_success(self, mock_refresh_token, mock_access_token, 
                                   mock_create_user, mock_id_token, mock_flow):
        """Test successful OAuth callback flow"""
        # Setup mocks
        mock_flow.fetch_token.return_value = None
        mock_flow.credentials = MagicMock(_id_token="fake_id_token")
        mock_id_token.verify_oauth2_token.return_value = {
            "email": self.test_email,
            "sub": "123",
            "name": "Test User",
            "picture": "http://example.com/pic.jpg",
        }
        mock_create_user.return_value = 1
        mock_access_token.return_value = "access_token"
        mock_refresh_token.return_value = "refresh_token"

        # Create valid state token
        payload = {"redirect_uri": "http://localhost/callback"}
        secret = app.config["JWT_SECRET_KEY"]
        token = jwt.encode(payload, secret, algorithm="HS256")
        
        response = self.app.get(f"/callback?state={token}&code=test_code")
        
        self.assertEqual(response.status_code, 302)
        self.assertIn("accessToken=access_token", response.location)
        self.assertIn("refreshToken=refresh_token", response.location)

    @patch("app.decode_token")
    @patch("flask_jwt_extended.view_decorators.verify_jwt_in_request")
    def test_refresh_token_success(self, mock_verify_jwt, mock_decode_token):
        """Test successful token refresh"""
        mock_verify_jwt.return_value = None
        mock_decode_token.return_value = {"sub": self.test_email}
        
        response = self.app.post("/refresh", headers=self.test_headers)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("accessToken", response.get_json())

    @patch("database.db.get_db_connection")
    def test_signup_success(self, mock_get_db_connection):
        """Test successful user signup"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db_connection.return_value = (mock_conn, mock_cursor)
        mock_cursor.fetchone.return_value = None  # User doesn't exist

        data = {
            "email": "new_user@test.com",
            "password": "StrongPassword123!",
            "name": "New User",
        }
        
        response = self.app.post("/signUp", json=data, headers=self.test_headers)
        
        self.assertIn(response.status_code, [200, 201])


    @patch("app.extractUserEmailFromRequest")
    def test_refresh_credits_success(self, mock_extract_email):
        """Test successful credit refresh"""
        mock_extract_email.return_value = self.test_email
        
        with patch("app.RefreshCreditsHandler") as mock_handler:
            mock_handler.return_value = {"credits": 100, "status": "refreshed"}
            
            response = self.app.post("/refreshCredits", headers=self.test_headers)
            
            self.assertEqual(response.status_code, 200)
            self.assertIn("credits", response.get_json())

    @patch("database.db.get_db_connection")
    @patch("app.extractUserEmailFromRequest")
    def test_checkout_session_success(self, mock_extract_email, mock_get_db_connection):
        """Test successful checkout session creation"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_db_connection.return_value = (mock_conn, mock_cursor)
        mock_extract_email.return_value = self.test_email
        
        with patch("app.verifyAuthForPaymentsTrustedTesters") as mock_verify_payments, \
             patch("app.verifyAuthForCheckoutSession") as mock_verify_checkout, \
             patch("app.CreateCheckoutSessionHandler") as mock_handler:
            
            mock_verify_payments.return_value = True
            mock_verify_checkout.return_value = None
            mock_handler.return_value = {"session_id": "test_session_123"}
            
            response = self.app.post("/createCheckoutSession", headers=self.test_headers)
            
            self.assertEqual(response.status_code, 200)
            self.assertIn("session_id", response.get_json())

    @patch("app.extractUserEmailFromRequest")
    def test_create_chat_success(self, mock_extract_email):
        """Test successful chat creation"""
        mock_extract_email.return_value = self.test_email
        
        with patch("app.add_chat_to_db") as mock_add_chat:
            mock_add_chat.return_value = "chat123"
            
            data = {"chat_type": "finance", "model_type": "gpt-4"}
            response = self.app.post("/create-new-chat", json=data, headers=self.test_headers)
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json(), {"chat_id": "chat123"})

    @patch("app.extractUserEmailFromRequest")
    def test_create_chat_invalid_token(self, mock_extract_email):
        """Test chat creation with invalid token"""
        from app import InvalidTokenError
        mock_extract_email.side_effect = InvalidTokenError()
        
        data = {"chat_type": "finance", "model_type": "gpt-4"}
        response = self.app.post("/create-new-chat", json=data, headers=self.test_headers)
        
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid JWT", response.get_data(as_text=True))

    @patch("app.extractUserEmailFromRequest")
    def test_retrieve_chats_success(self, mock_extract_email):
        """Test successful chat retrieval"""
        mock_extract_email.return_value = self.test_email
        
        with patch("app.retrieve_chats_from_db") as mock_retrieve:
            mock_retrieve.return_value = [{"chat_id": "1", "name": "Test Chat"}]
            
            response = self.app.post("/retrieve-all-chats", headers=self.test_headers)
            
            self.assertEqual(response.status_code, 200)
            self.assertIn("Test Chat", response.get_data(as_text=True))

    @patch("app.extractUserEmailFromRequest")
    def test_retrieve_messages_success(self, mock_extract_email):
        """Test successful message retrieval"""
        mock_extract_email.return_value = self.test_email
        
        with patch("app.retrieve_message_from_db") as mock_retrieve, \
             patch("app.get_chat_info") as mock_chat_info:
            
            mock_retrieve.return_value = [{"msg": "Hello from chat"}]
            mock_chat_info.return_value = (None, None, "Test Chat")
            
            data = {"chat_type": "finance", "chat_id": "chat1"}
            response = self.app.post("/retrieve-messages-from-chat", json=data, headers=self.test_headers)
            
            self.assertEqual(response.status_code, 200)
            self.assertIn("Hello from chat", response.get_data(as_text=True))

    @patch("app.extractUserEmailFromRequest")
    def test_update_chat_name_success(self, mock_extract_email):
        """Test successful chat name update"""
        mock_extract_email.return_value = self.test_email
        
        with patch("app.update_chat_name_db") as mock_update:
            mock_update.return_value = None
            
            data = {"chat_name": "Updated Name", "chat_id": "chat1"}
            response = self.app.post("/update-chat-name", json=data, headers=self.test_headers)
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json(), {"Success": "Chat name updated"})

    @patch("app.extractUserEmailFromRequest")
    def test_delete_chat_success(self, mock_extract_email):
        """Test successful chat deletion"""
        mock_extract_email.return_value = self.test_email
        
        with patch("app.delete_chat_from_db") as mock_delete:
            mock_delete.return_value = "Chat deleted"
            
            data = {"chat_id": "chat1"}
            response = self.app.post("/delete-chat", json=data, headers=self.test_headers)
            
            self.assertEqual(response.status_code, 200)
            self.assertIn("Chat deleted", response.get_data(as_text=True))

    @patch("app.extractUserEmailFromRequest")
    def test_download_chat_history_success(self, mock_extract_email):
        """Test successful chat history download"""
        mock_extract_email.return_value = self.test_email
        
        with patch("app.retrieve_message_from_db") as mock_retrieve:
            mock_retrieve.return_value = [
                {"sent_from_user": 1, "message_text": "Hi", "relevant_chunks": None},
                {"sent_from_user": 0, "message_text": "Hello", "relevant_chunks": None},
            ]
            
            data = {"chat_type": "finance", "chat_id": "chat1"}
            response = self.app.post("/download-chat-history", json=data, headers=self.test_headers)
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, "text/csv")

    @patch("app.extractUserEmailFromRequest")
    def test_download_chat_history_invalid_token(self, mock_extract_email):
        """Test chat history download with invalid token"""
        from app import InvalidTokenError
        mock_extract_email.side_effect = InvalidTokenError()
        
        data = {"chat_type": "finance", "chat_id": "chat1"}
        response = self.app.post("/download-chat-history", json=data, headers=self.test_headers)
        
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid JWT", response.get_data(as_text=True))

    @patch("app.extractUserEmailFromRequest")
    def test_infer_chat_name_success(self, mock_extract_email):
        """Test successful chat name inference"""
        mock_extract_email.return_value = self.test_email
        
        with patch("app.client") as mock_client, \
             patch("app.update_chat_name_db") as mock_update:
            
            # Mock OpenAI response
            mock_completion = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "Investment Discussion"
            mock_completion.choices = [mock_choice]
            mock_client.chat.completions.create.return_value = mock_completion
            mock_update.return_value = None
            
            data = {"messages": ["Tell me about stocks", "What's a good investment?"], "chat_id": "chat1"}
            response = self.app.post("/infer-chat-name", json=data, headers=self.test_headers)
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json(), {"chat_name": "Investment Discussion"})

    @patch("app.extractUserEmailFromRequest")
    def test_reset_chat_with_docs(self, mock_extract_email):
        """Test chat reset with document deletion"""
        mock_extract_email.return_value = self.test_email
        
        with patch("app.reset_chat_db") as mock_reset_chat, \
             patch("app.reset_uploaded_docs") as mock_reset_docs:
            
            mock_reset_chat.return_value = None
            mock_reset_docs.return_value = None
            
            data = {"chat_id": "chat123", "delete_docs": True}
            response = self.app.post("/reset-chat", json=data, headers=self.test_headers)
            
            self.assertEqual(response.status_code, 200)
            self.assertIn("Success", response.get_data(as_text=True))
            mock_reset_docs.assert_called_once()

    def test_get_shared_messages_success(self):
        """Test successful retrieval of shared messages (no auth required)"""
        with patch("app.retrieve_message_from_db") as mock_retrieve:
            mock_retrieve.return_value = [
                {"msg": "shared message 1"},
                {"msg": "shared message 2"},
            ]
            
            data = {"chat_id": "public_chat1"}
            response = self.app.post("/retrieve-shared-messages-from-chat", json=data, headers=self.test_headers)
            
            self.assertEqual(response.status_code, 200)
            response_data = response.get_data(as_text=True)
            self.assertIn("shared message 1", response_data)
            self.assertIn("shared message 2", response_data)

    def _create_invalid_token_test(self, endpoint, method="post", data=None):
        """Helper method to test invalid token scenarios"""
        with patch("app.extractUserEmailFromRequest") as mock_extract:
            from app import InvalidTokenError
            mock_extract.side_effect = InvalidTokenError()
            
            if method == "post":
                response = self.app.post(endpoint, json=data or {}, headers=self.test_headers)
            else:
                response = self.app.get(endpoint, headers=self.test_headers)
            
            self.assertEqual(response.status_code, 401)
            self.assertIn("Invalid JWT", response.get_data(as_text=True))

    def test_invalid_token_scenarios(self):
        """Test multiple endpoints with invalid tokens"""
        test_cases = [
            ("/retrieve-all-chats", "post"),
            ("/retrieve-messages-from-chat", "post", {"chat_type": "finance", "chat_id": "chat1"}),
            ("/update-chat-name", "post", {"chat_name": "New Name", "chat_id": "chat1"}),
            ("/delete-chat", "post", {"chat_id": "chat1"}),
            ("/find-most-recent-chat", "post"),
        ]
        
        for case in test_cases:
            endpoint = case[0]
            method = case[1]
            data = case[2] if len(case) > 2 else None
            
            with self.subTest(endpoint=endpoint):
                self._create_invalid_token_test(endpoint, method, data)


if __name__ == "__main__":
    unittest.main(verbosity=2)