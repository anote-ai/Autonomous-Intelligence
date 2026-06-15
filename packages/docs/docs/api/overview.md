# Backend API Overview

The Anote backend is a unified Flask API serving all client surfaces.

Base URL: `http://localhost:5000` (local) or your deployed backend URL.

## Authentication

All protected endpoints require a JWT token:

```
Authorization: Bearer <token>
```

Obtain a token via `POST /auth/login` or `POST /auth/register`.

## Key Endpoints

### Agent Chat (Streaming)

```
POST /api/chat/stream          # SSE streaming chat
POST /api/chat                 # Non-streaming chat
GET  /api/chat/sessions        # List sessions
POST /api/chat/sessions        # Create session
```

### Documents

```
POST /api/documents/upload     # Upload document
GET  /api/documents            # List documents
GET  /api/documents/{id}       # Get document
DELETE /api/documents/{id}     # Delete document
POST /api/documents/{id}/ask   # Q&A on document
```

### Semantic Search

```
GET  /api/search?q=...&cwd=... # Search indexed codebase
```

### Authentication

```
POST /auth/register            # Register
POST /auth/login               # Login
POST /auth/refresh             # Refresh JWT
GET  /auth/google              # Google OAuth
```

### User & Billing

```
GET  /api/user/profile         # Get user
POST /api/payments/checkout    # Stripe checkout
POST /api/payments/portal      # Customer portal
POST /api/payments/webhook     # Stripe webhook
```
