# Documents API

Base path: `/api/documents`

## Upload Document

```http
POST /api/documents/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=@document.pdf
```

Supported formats: `.pdf`, `.txt`, `.md`, `.docx`, `.csv`

**Response**
```json
{
  "id": "doc_abc123",
  "filename": "document.pdf",
  "size": 102400,
  "chunks": 42
}
```

## List Documents

```http
GET /api/documents
Authorization: Bearer <token>
```

## Ask a Question

```http
POST /api/documents/{id}/ask
Authorization: Bearer <token>
Content-Type: application/json

{ "question": "What is the main topic?" }
```

## Delete Document

```http
DELETE /api/documents/{id}
Authorization: Bearer <token>
```
