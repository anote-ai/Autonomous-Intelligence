# Python SDK

A Python client is available via the `anoteai` package (part of the Anote-Product repo).

## Installation

```bash
pip install anoteai
```

## Usage

```python
from anoteai import Anote

client = Anote(api_key="sk-ai-...")

# Existing public methods authenticate with Authorization: Bearer sk-ai-...
result = client.classify(document_id="doc_123", labels=["contract", "invoice"])
answer = client.answer(document_id="doc_123", question="What is the payment amount?")
```

Create API keys from Settings -> API Keys. The plaintext key is shown once; after that only the key prefix is displayed.

Credit costs:

| Operation | Credits |
| --- | ---: |
| Document upload | 1 per file or URL |
| Chat message / Q&A | 1 per request |
| OpenAI-compatible chat completion | 1 per request |

Handle API errors by status code:

| Status | Meaning |
| --- | --- |
| 401 | Missing or invalid API key |
| 402 | Insufficient credits |
| 429 | Per-key rate limit exceeded |

See the [Anote-Product repository](https://github.com/anote-ai/anote-product) for full SDK documentation.
