# Search API

Base path: `/api/search`

## Search Codebase Index

```http
GET /api/search?q=authentication&cwd=/path/to/project&top=10
Authorization: Bearer <token>
```

**Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query (required) |
| `cwd` | string | Project directory containing `.anote/index/` |
| `top` | integer | Number of results to return (default: 10) |

**Response**
```json
{
  "results": [
    {
      "file": "src/auth/handler.py",
      "startLine": 45,
      "endLine": 72,
      "preview": "def authenticate_user(email, password)...",
      "score": 0.8432
    }
  ]
}
```

Returns `404` if no index exists at the given `cwd`. Build an index first with `anote index`.
