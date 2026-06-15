# Chat API

Base path: `/api/chat`

## Stream Chat (SSE)

```http
POST /api/chat/stream
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "Explain this codebase",
  "model": "claude-sonnet-4-6",
  "session_id": null
}
```

Returns a Server-Sent Events stream:

```
event: text
data: {"text": "This codebase..."}

event: session_id
data: {"session_id": "abc123"}

event: done
data: {}
```

## List Sessions

```http
GET /api/chat/sessions
Authorization: Bearer <token>
```

## Get Session Messages

```http
GET /api/chat/sessions/{id}
Authorization: Bearer <token>
```

## Delete Session

```http
DELETE /api/chat/sessions/{id}
Authorization: Bearer <token>
```
