# backend/tests/test_transcription_advanced.py

import pytest
from unittest.mock import patch, MagicMock, call
import subprocess


def test_get_whisper_model_cached():
    """Test whisper model is only loaded once."""
    from app.services import transcription

    mock_model = MagicMock()
    original = transcription._whisper_model

    transcription._whisper_model = mock_model
    result = transcription.get_whisper_model()
    assert result is mock_model

    transcription._whisper_model = original


def test_get_whisper_model_loads_once(tmp_path):
    """Test whisper model loads when None."""
    from app.services import transcription

    original = transcription._whisper_model
    transcription._whisper_model = None

    mock_model = MagicMock()
    with patch("whisper.load_model", return_value=mock_model) as mock_load:
        result = transcription.get_whisper_model()
        assert result is mock_model
        mock_load.assert_called_once_with("base")

    transcription._whisper_model = original


def test_extract_audio_ffmpeg_success(tmp_path):
    """Test successful audio extraction from video."""
    from app.services.transcription import extract_audio_from_video

    video_path = str(tmp_path / "video.mp4")
    expected_audio = str(tmp_path / "video_audio.wav")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        result = extract_audio_from_video(video_path)

    assert result == expected_audio
    mock_run.assert_called_once()
    call_args = mock_run.call_args[0][0]
    assert "ffmpeg" in call_args
    assert video_path in call_args


def test_extract_audio_ffmpeg_fails(tmp_path):
    """Test ffmpeg failure raises RuntimeError."""
    from app.services.transcription import extract_audio_from_video

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Error: invalid file"
        )
        with pytest.raises(RuntimeError, match="ffmpeg failed"):
            extract_audio_from_video(str(tmp_path / "bad.mp4"))


def test_extract_audio_timeout(tmp_path):
    """Test ffmpeg timeout raises RuntimeError."""
    from app.services.transcription import extract_audio_from_video

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ffmpeg", 300)):
        with pytest.raises(RuntimeError, match="timed out"):
            extract_audio_from_video(str(tmp_path / "long.mp4"))


def test_probe_duration_no_duration_key():
    """Test probe returns None when duration key missing."""
    from app.services.transcription import probe_audio_duration
    import json

    mock_output = json.dumps({"format": {}})
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
        result = probe_audio_duration("/fake/audio.mp3")
    assert result is None


def test_transcribe_audio_failure(tmp_path):
    """Test transcription raises RuntimeError on failure."""
    from app.services.transcription import transcribe_audio

    mock_model = MagicMock()
    mock_model.transcribe.side_effect = Exception("CUDA error")

    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake")

    with patch("app.services.transcription._whisper_model", mock_model):
        with patch("app.services.transcription.get_whisper_model", return_value=mock_model):
            with pytest.raises(RuntimeError, match="Transcription failed"):
                transcribe_audio(str(audio_file))


def test_transcribe_audio_cleans_temp_file(tmp_path):
    """Test video transcription cleans up temp audio file."""
    from app.services.transcription import transcribe

    video_path = str(tmp_path / "video.mp4")
    audio_path = str(tmp_path / "video_audio.wav")

    # Create fake audio file
    with open(audio_path, "wb") as f:
        f.write(b"fake audio")

    mock_segments = [{"text": "hello", "start": 0.0, "end": 1.0}]

    with patch("app.services.transcription.extract_audio_from_video", return_value=audio_path):
        with patch("app.services.transcription.transcribe_audio", return_value=(mock_segments, "hello")):
            import os
            with patch("os.path.exists", return_value=True):
                with patch("os.remove") as mock_remove:
                    transcribe(video_path, "video")
                    mock_remove.assert_called_once_with(audio_path)