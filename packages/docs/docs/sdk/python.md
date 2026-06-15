# Python SDK

A Python client is available via the `anoteai` package (part of the Anote-Product repo).

## Installation

```bash
pip install anoteai
```

## Usage

```python
from anoteai import Anote

client = Anote(api_key="your-api-key")

# Classify text
result = client.classify(
    data_type="text",
    data=["This is great!", "This is terrible."],
    labels=["positive", "negative"],
)
print(result)
```

See the [Anote-Product repository](https://github.com/anote-ai/anote-product) for full SDK documentation.
