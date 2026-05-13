# backend/app/services/transcription.py

import os
import subprocess
import logging
import tempfile
from typing import List, Dict, Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Lazy-load Whisper to avoid slow startup
_whisper_model = None


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
            logger.info("Loading Whisper model (base)...")
            _whisper_model = whisper.load_model("base")
            logger.info("Whisper model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise RuntimeError(f"Whisper model unavailable: {str(e)}")
    return _whisper_model


def extract_audio_from_video(video_path: str) -> str:
    """
    Use ffmpeg to extract audio from video file.
    Returns path to extracted audio (.wav file).
    """
    audio_path = video_path.rsplit(".", 1)[0] + "_audio.wav"

    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vn",                    # No video
        "-acodec", "pcm_s16le",  # PCM 16-bit LE (WAV)
        "-ar", "16000",           # 16kHz sample rate (Whisper optimal)
        "-ac", "1",               # Mono
        "-y",                     # Overwrite if exists
        audio_path,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr}")
        return audio_path
    except subprocess.TimeoutExpired:
        raise RuntimeError("Audio extraction timed out (5 minutes)")
    except FileNotFoundError:
        raise RuntimeError(
            "ffmpeg not found. Please install ffmpeg: https://ffmpeg.org/download.html"
        )


def probe_audio_duration(file_path: str) -> Optional[float]:
    """Use ffprobe to get audio/video duration in seconds."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        file_path,
    ]
    try:
        import json
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            duration = data.get("format", {}).get("duration")
            if duration:
                return float(duration)
    except Exception as e:
        logger.warning(f"Could not probe duration: {e}")
    return None


def transcribe_audio(file_path: str) -> Tuple[List[Dict], str]:
    """
    Transcribe audio file using Whisper.
    Handles long files (>30 min) by processing in segments.

    Returns:
        segments: [{text, start, end}, ...]
        full_text: complete transcription
    """
    model = get_whisper_model()

    # Check duration for very long files
    duration = probe_audio_duration(file_path)
    logger.info(f"Transcribing audio: {file_path} (duration: {duration}s)")

    try:
        result = model.transcribe(
            file_path,
            verbose=False,
            word_timestamps=False,  # Segment-level timestamps are enough
            fp16=False,  # Use float32 for better accuracy (if GPU available)
            language="en",  # Assuming English; can be made dynamic if needed
        )
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        raise RuntimeError(f"Transcription failed: {str(e)}")

    segments = []
    full_text_parts = []

    for seg in result.get("segments", []):
        text = seg.get("text", "").strip()
        if not text:
            continue

        segments.append({
            "text": text,
            "start": round(seg.get("start", 0.0), 2),
            "end": round(seg.get("end", 0.0), 2),
        })
        full_text_parts.append(text)

    full_text = " ".join(full_text_parts)

    if not full_text.strip():
        logger.warning(f"Whisper returned empty transcription for {file_path}")

    return segments, full_text


def transcribe(file_path: str, file_type: str = "audio") -> Tuple[List[Dict], str]:
    """
    Main transcription entry point.
    Handles both audio and video files.

    Returns:
        segments: [{text, start, end}, ...]
        full_text: complete transcription
    """
    audio_path = file_path
    temp_audio_created = False

    try:
        if file_type == "video":
            logger.info(f"Extracting audio from video: {file_path}")
            audio_path = extract_audio_from_video(file_path)
            temp_audio_created = True

        segments, full_text = transcribe_audio(audio_path)
        return segments, full_text

    finally:
        # Clean up temporary audio file extracted from video
        if temp_audio_created and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass