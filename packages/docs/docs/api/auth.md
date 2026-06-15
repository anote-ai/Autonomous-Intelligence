# Authentication API

Base path: `/auth`

## Register

```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123",
  "name": "Alice"
}
```

**Response**
```json
{ "access_token": "eyJ..." }
```

## Login

```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

## Refresh Token

```http
POST /auth/refresh
Authorization: Bearer <token>
```

## Get Current User

```http
GET /auth/me
Authorization: Bearer <token>
```

**Response**
```json
{
  "id": "1",
  "email": "user@example.com",
  "name": "Alice"
}
```
