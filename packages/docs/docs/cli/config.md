# CLI Configuration

The Anote CLI can be configured via `.anote.json` in your project root or `~/.anote/config.json` globally.

## Config File

```json
{
  "model": "claude-sonnet-4-6",
  "permissionMode": "default",
  "maxTurns": 20,
  "provider": "anthropic"
}
```

## Managing Config

```bash
anote config list          # Show all settings
anote config get model     # Get a value
anote config set model claude-haiku-4-5-20251001  # Set a value
anote config unset model   # Remove a value
```
