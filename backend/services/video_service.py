"""Video analysis service: extract frames + audio track for RAG indexing.

Pipeline for an uploaded video document:
  1. Write bytes to a secure temp file.
  2. Use ffmpeg to extract one JPEG frame every ``VIDEO_FRAME_INTERVAL_SECS``
     seconds (capped at ``VIDEO_MAX_FRAMES`` frames).
  3. Call ``describe_image()`` (vision_service) on each frame and tag the
     description with a timestamp.
  4. Extract the audio track with ffmpeg and call ``transcribe_audio()``
     (audio_service) on it via Whisper.
  5. Interleave frame descriptions and transcript segments into a single
     structured document that is stored as ``document_text`` and fed into the
     normal chunking + embedding pipeline.

Requires: ffmpeg on PATH.  If ffmpeg is unavailable the service falls back
gracefully, returning a placeholder string so the document record is still
created.
"""
import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from agents.config import AgentConfig
from services.audio_service import transcribe_audio
from services.vision_service import describe_image

# ffmpeg probe / frame-extraction helpers ----------------------------------------


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _get_duration(video_path: str) -> Optional[float]:
    """Return video duration in seconds using ffprobe, or None on failure."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path,
            ],
            capture_output=True, text=True, timeout=30,
        )
        return float(result.stdout.strip())
    except Exception:
        return None


def _extract_frames(video_path: str, output_dir: str, interval: int, max_frames: int) -> list[tuple[float, str]]:
    """Extract one JPEG frame every *interval* seconds into *output_dir*.

    Returns a list of (timestamp_secs, frame_path) tuples, capped at *max_frames*.
    """
    # Build a select filter: pick one frame per interval second
    select_expr = f"not(mod(t,{interval}))"
    frame_pattern = os.path.join(output_dir, "frame_%04d.jpg")

    try:
        subprocess.run(
            [
                "ffmpeg", "-i", video_path,
                "-vf", f"select='{select_expr}'",
                "-vsync", "vfr",
                "-q:v", "3",          # JPEG quality (2=best, 5=ok for indexing)
                "-frames:v", str(max_frames),
                frame_pattern,
                "-y",                 # overwrite
            ],
            capture_output=True, timeout=300,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"[video_service] ffmpeg frame extraction failed: {exc.stderr.decode()[:200]}")
        return []
    except Exception as exc:
        print(f"[video_service] ffmpeg error: {exc}")
        return []

    frames = sorted(Path(output_dir).glob("frame_*.jpg"))
    result = []
    for i, path in enumerate(frames[:max_frames]):
        timestamp = i * interval
        result.append((float(timestamp), str(path)))
    return result


def _extract_audio_track(video_path: str, output_dir: str) -> Optional[bytes]:
    """Extract the audio track as MP3 bytes, or return None."""
    audio_path = os.path.join(output_dir, "audio_track.mp3")
    try:
        subprocess.run(
            [
                "ffmpeg", "-i", video_path,
                "-vn",                # no video
                "-ar", "16000",       # 16 kHz — Whisper optimal sample rate
                "-ac", "1",           # mono
                "-b:a", "64k",
                audio_path, "-y",
            ],
            capture_output=True, timeout=300,
            check=True,
        )
        with open(audio_path, "rb") as f:
            return f.read()
    except Exception as exc:
        print(f"[video_service] audio track extraction failed: {exc}")
        return None


# Public API ----------------------------------------------------------------------


def describe_video(
    video_bytes: bytes,
    filename: str = "video.mp4",
    mime_type: str = "video/mp4",
) -> str:
    """Analyse *video_bytes* and return a structured searchable document.

    The document interleaves timestamped frame descriptions with the Whisper
    transcript of the audio track so both visual and spoken content are indexed.

    Returns a string (never raises) so the document record is always created.
    """
    if not AgentConfig.ENABLE_MULTIMODAL:
        return (
            "[Multimodal support is disabled. "
            "Set ENABLE_MULTIMODAL=true to analyse videos.]"
        )

    if len(video_bytes) > AgentConfig.MAX_VIDEO_BYTES:
        mb = len(video_bytes) / (1024 * 1024)
        limit_mb = AgentConfig.MAX_VIDEO_BYTES / (1024 * 1024)
        return (
            f"[Video file too large ({mb:.0f} MB). "
            f"Limit: {limit_mb:.0f} MB.]"
        )

    if not _ffmpeg_available():
        return (
            "[Video analysis requires ffmpeg. "
            "Install ffmpeg and add it to PATH to enable this feature.]"
        )

    tmp_dir = tempfile.mkdtemp(prefix="anote_video_")
    try:
        return _analyse(video_bytes, filename, tmp_dir)
    except Exception as exc:
        return f"[Video analysis failed: {exc}]"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _analyse(video_bytes: bytes, filename: str, tmp_dir: str) -> str:
    # Write video to disk (ffmpeg needs a seekable file)
    video_path = os.path.join(tmp_dir, filename)
    with open(video_path, "wb") as f:
        f.write(video_bytes)

    frame_dir = os.path.join(tmp_dir, "frames")
    os.makedirs(frame_dir, exist_ok=True)

    interval = AgentConfig.VIDEO_FRAME_INTERVAL_SECS
    max_frames = AgentConfig.VIDEO_MAX_FRAMES
    duration = _get_duration(video_path)

    sections: list[str] = []

    # Header
    header_parts = [f"[Video analysis — file: {filename}"]
    if duration is not None:
        m, s = divmod(int(duration), 60)
        header_parts.append(f"duration: {m}m {s}s")
    header_parts.append(f"frame interval: {interval}s]")
    sections.append(", ".join(header_parts))
    sections.append("")

    # ── Frame descriptions ──────────────────────────────────────────────────
    frames = _extract_frames(video_path, frame_dir, interval, max_frames)
    if frames:
        sections.append("## Visual content (key frames)\n")
        for timestamp, frame_path in frames:
            with open(frame_path, "rb") as f:
                frame_bytes = f.read()
            m, s = divmod(int(timestamp), 60)
            ts_label = f"{m:02d}:{s:02d}"
            description = describe_image(frame_bytes, mime_type="image/jpeg")
            sections.append(f"**[{ts_label}]** {description.strip()}\n")
    else:
        sections.append("## Visual content\n[Frame extraction produced no frames.]\n")

    # ── Audio track transcript ───────────────────────────────────────────────
    audio_bytes = _extract_audio_track(video_path, tmp_dir)
    if audio_bytes and len(audio_bytes) <= AgentConfig.MAX_AUDIO_BYTES:
        sections.append("\n## Audio transcript\n")
        transcript = transcribe_audio(audio_bytes, filename="audio_track.mp3")
        sections.append(transcript)
    elif audio_bytes:
        sections.append("\n## Audio transcript\n[Audio track too large for Whisper transcription.]\n")
    else:
        sections.append("\n## Audio transcript\n[No audio track detected or extraction failed.]\n")

    return "\n".join(sections)
