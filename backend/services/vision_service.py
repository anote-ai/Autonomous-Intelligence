"""Vision service: generate rich text descriptions of images for RAG indexing.

When a user uploads an image as a document the text extraction path (Tika)
is skipped.  Instead, ``describe_image()`` is called to produce a detailed
textual description via the configured vision-capable LLM.  That description
is stored as ``document_text`` and fed into the normal chunking + embedding
pipeline, making the image fully searchable through RAG.
"""
import base64
import os
from typing import Optional

from agents.config import AgentConfig

_INDEXING_PROMPT = (
    "You are analyzing an image that has been uploaded as a document inside a "
    "RAG-based Q&A system. Your description will be the only representation of "
    "this image in the search index, so be as thorough and specific as possible.\n\n"
    "Include ALL of the following that are present:\n"
    "- Transcribe any text exactly as written (signs, labels, captions, headings, "
    "body text, code, etc.)\n"
    "- Describe charts, graphs, or diagrams: axes, data series, values, trends\n"
    "- List objects, people, animals, and their positions/relationships\n"
    "- Note colours, layout, style, and visual hierarchy\n"
    "- For screenshots: describe the UI, app name, visible controls, and content\n"
    "- For diagrams: describe the flow, nodes, edges, and labels\n\n"
    "Write in clear, structured prose so that a text-only search can find this "
    "image by its content."
)


def describe_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
    prompt: Optional[str] = None,
) -> str:
    """Return a detailed textual description of *image_bytes*.

    Uses the vision-capable LLM configured in ``AgentConfig``.
    Returns a placeholder string (never raises) so the document record is
    always created even if the vision call fails.
    """
    if not AgentConfig.ENABLE_MULTIMODAL:
        return (
            "[Multimodal support is disabled. "
            "Set ENABLE_MULTIMODAL=true to analyse images.]"
        )

    if len(image_bytes) > AgentConfig.MAX_IMAGE_BYTES:
        mb = len(image_bytes) / (1024 * 1024)
        limit_mb = AgentConfig.MAX_IMAGE_BYTES / (1024 * 1024)
        return (
            f"[Image too large for inline analysis ({mb:.1f} MB). "
            f"Limit: {limit_mb:.0f} MB.]"
        )

    effective_prompt = prompt or _INDEXING_PROMPT
    data_b64 = base64.b64encode(image_bytes).decode("utf-8")

    if AgentConfig.DEFAULT_AGENT_MODEL_TYPE == 0:
        return _describe_openai(data_b64, mime_type, effective_prompt)
    return _describe_anthropic(data_b64, mime_type, effective_prompt)


def _describe_openai(data_b64: str, mime_type: str, prompt: str) -> str:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=AgentConfig.OPENAI_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{data_b64}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            max_tokens=2048,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        return f"[Image description failed (OpenAI): {exc}]"


def _describe_anthropic(data_b64: str, mime_type: str, prompt: str) -> str:
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model=AgentConfig.ANTHROPIC_VISION_MODEL,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": data_b64,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        return response.content[0].text if response.content else ""
    except Exception as exc:
        return f"[Image description failed (Anthropic): {exc}]"
