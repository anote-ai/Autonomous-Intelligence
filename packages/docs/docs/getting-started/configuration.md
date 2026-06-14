# Configuration

## CLI Configuration

Configuration is stored in `~/.anote/config.json`:

```json
{
  "model": "claude-sonnet-4-6",
  "provider": "anthropic",
  "apiKey": "sk-ant-...",
  "serverUrl": "http://localhost:5000",
  "maxTurns": 30,
  "permissionMode": "default"
}
```

Manage via:

```bash
anote config set model claude-opus-4-8
anote config get model
anote config list
```

## Environment Variables

All settings can be overridden with environment variables:

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `ANOTE_MODEL` | Default model |
| `ANOTE_SERVER_URL` | Anote backend URL |

## Backend Configuration

Copy `packages/backend/.env.example` to `packages/backend/.env` and fill in:

```bash
# LLM Providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...

# Database
DB_HOST=localhost
DB_NAME=anote
DB_USER=anote
DB_PASSWORD=anote

# Auth
JWT_SECRET_KEY=your-secret-key

# Payments (optional)
STRIPE_SECRET_KEY=sk_...
```
