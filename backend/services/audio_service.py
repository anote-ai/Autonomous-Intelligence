"""Audio transcription service: convert uploaded audio to text for RAG indexing.

Uses the OpenAI Whisper API (``whisper-1`` model) to transcribe audio files.
The resulting transcript is stored as ``document_text`` and fed into the
existing chunking + embedding pipeline, making the audio fully searchable.

Supported formats (Whisper API): flac, m4a, mp3, mp4, mpeg, mpga, oga,
ogg, wav, webm.  Maximum file size: 25 MB (enforced by MAX_AUDIO_BYTES).
"""
import io
import os
from typing import Optional

from agents.config import AgentConfig

# Whisper supports these extensions directly.  We pass the filename so the
# API can infer the codec — do not strip it.
_WHISPER_SUPPORTED_EXTS = {
    "flac", "m4a", "mp3", "mp4", "mpeg", "mpga",
    "oga", "ogg", "wav", "webm",
}

_PROMPT_HINT = (
    "This is a recording that may contain speech, narration, or conversation. "
    "Transcribe it accurately, preserving punctuation and paragraph breaks."
)


def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.mp3",
    language: Optional[str] = None,
) -> str:
    """Transcribe *audio_bytes* and return a plain-text transcript.

    ``filename`` is forwarded to the Whisper API so it can detect the codec
    automatically — always include the original file extension.

    ``language`` is an optional BCP-47 code (e.g. ``"en"``, ``"es"``) that
    improves accuracy when the language is known in advance.  Leave as None
    for automatic detection.

    Returns a plain string (never raises) so the document record is always
    created even if transcription fails.
    """
    if not AgentConfig.ENABLE_MULTIMODAL:
        return (
            "[Multimodal support is disabled. "
            "Set ENABLE_MULTIMODAL=true to transcribe audio.]"
        )

    if len(audio_bytes) > AgentConfig.MAX_AUDIO_BYTES:
        mb = len(audio_bytes) / (1024 * 1024)
        limit_mb = AgentConfig.MAX_AUDIO_BYTES / (1024 * 1024)
        return (
            f"[Audio file too large for transcription ({mb:.1f} MB). "
            f"Whisper API limit: {limit_mb:.0f} MB.]"
        )

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _WHISPER_SUPPORTED_EXTS:
        return (
            f"[Unsupported audio format '.{ext}'. "
            f"Supported: {', '.join(sorted(_WHISPER_SUPPORTED_EXTS))}.]"
        )

    return _transcribe_with_whisper(audio_bytes, filename, language)


def _transcribe_with_whisper(
    audio_bytes: bytes,
    filename: str,
    language: Optional[str],
) -> str:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Whisper requires a file-like object with a name attribute.
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename  # type: ignore[attr-defined]

        kwargs: dict = {
            "model": "whisper-1",
            "file": audio_file,
            "response_format": "verbose_json",  # includes segments + language
            "prompt": _PROMPT_HINT,
        }
        if language:
            kwargs["language"] = language

        result = client.audio.transcriptions.create(**kwargs)

        transcript = getattr(result, "text", None) or str(result)
        detected_lang = getattr(result, "language", "unknown")
        duration = getattr(result, "duration", None)

        # Prepend metadata so it can surface in RAG results
        header_parts = [f"[Audio transcript — language: {detected_lang}"]
        if duration is not None:
            minutes, seconds = divmod(int(duration), 60)
            header_parts.append(f"duration: {minutes}m {seconds}s")
        header = ", ".join(header_parts) + "]\n\n"

        return header + transcript.strip()

    except Exception as exc:
        return f"[Audio transcription failed: {exc}]"
