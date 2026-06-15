# Local Models

The desktop app supports local LLM inference via [Ollama](https://ollama.ai).

## Setup

1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Pull a model:
   ```bash
   ollama pull llama3
   ollama pull mistral
   ```
3. In the desktop app, select a local model from the model dropdown (prefixed with `ollama/`)

## Supported Models

| Model | Pull Command |
|-------|--------------|
| Llama 3 | `ollama pull llama3` |
| Mistral | `ollama pull mistral` |
| Phi-3 | `ollama pull phi3` |

Local models run entirely on your hardware — no data leaves your machine.
