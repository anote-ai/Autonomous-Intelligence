# VS Code Extension Settings

Configure the extension in VS Code's settings UI or `settings.json`.

| Setting | Default | Description |
|---------|---------|-------------|
| `anote.model` | `claude-sonnet-4-6` | Default model to use |
| `anote.apiKey` | `""` | Anthropic API key (or use env var) |
| `anote.permissionMode` | `default` | Tool permission mode: `default`, `auto`, `manual` |
| `anote.showToolUse` | `true` | Show tool calls in the chat panel |

```json
{
  "anote.model": "claude-sonnet-4-6",
  "anote.permissionMode": "default"
}
```
