# backend/tests/test_transcription.py

import pytest
import os
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_whisper_model():
    model = MagicMock()
    model.transcribe.return_value = {
        "segments": [
            {"text": " Hello world", "start": 0.0, "end": 2.5},
            {"text": " This is a test", "start": 2.5, "end": 5.0},
            {"text": " Machine learning is fascinating", "start": 5.0, "end": 8.0},
        ],
        "text": " Hello world This is a test Machine learning is fascinating",
    }
    return model


def test_transcribe_audio_success(mock_whisper_model, tmp_path):
    from app.services.transcription import transcribe_audio

    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake wav data")

    with patch("app.services.transcription._whisper_model", mock_whisper_model):
        with patch("app.services.transcription.get_whisper_model", return_value=mock_whisper_model):
            segments, full_text = transcribe_audio(str(audio_file))

    assert len(segments) == 3
    assert segments[0]["text"] == "Hello world"
    assert segments[0]["start"] == 0.0
    assert segments[0]["end"] == 2.5
    assert "Hello world" in full_text


def test_transcribe_returns_correct_format(mock_whisper_model, tmp_path):
    from app.services.transcription import transcribe_audio

    audio_file = tmp_path / "audio.wav"
    audio_file.write_bytes(b"fake data")

    with patch("app.services.transcription._whisper_model", mock_whisper_model):
        with patch("app.services.transcription.get_whisper_model", return_value=mock_whisper_model):
            segments, _ = transcribe_audio(str(audio_file))

    for seg in segments:
        assert "text" in seg
        assert "start" in seg
        assert "end" in seg
        assert isinstance(seg["start"], float)
        assert isinstance(seg["end"], float)


def test_transcribe_empty_result(tmp_path):
    from app.services.transcription import transcribe_audio

    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"segments": [], "text": ""}

    audio_file = tmp_path / "silence.wav"
    audio_file.write_bytes(b"fake silence data")

    with patch("app.services.transcription._whisper_model", mock_model):
        with patch("app.services.transcription.get_whisper_model", return_value=mock_model):
            segments, full_text = transcribe_audio(str(audio_file))

    assert segments == []
    assert full_text == ""


def test_transcribe_filters_empty_segments(tmp_path):
    from app.services.transcription import transcribe_audio

    mock_model = MagicMock()
    mock_model.transcribe.return_value = {
        "segments": [
            {"text": " Hello", "start": 0.0, "end": 1.0},
            {"text": "   ", "start": 1.0, "end": 2.0},  # empty after strip
            {"text": " World", "start": 2.0, "end": 3.0},
        ],
        "text": " Hello World",
    }

    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake")

    with patch("app.services.transcription._whisper_model", mock_model):
        with patch("app.services.transcription.get_whisper_model", return_value=mock_model):
            segments, full_text = transcribe_audio(str(audio_file))

    assert len(segments) == 2
    assert segments[0]["text"] == "Hello"
    assert segments[1]["text"] == "World"


def test_transcribe_video_routes_to_audio_extraction(mock_whisper_model, tmp_path):
    from app.services.transcription import transcribe

    video_file = tmp_path / "test.mp4"
    video_file.write_bytes(b"fake mp4 data")
    audio_path = str(video_file).replace(".mp4", "_audio.wav")

    with patch("app.services.transcription.extract_audio_from_video") as mock_extract:
        mock_extract.return_value = audio_path
        with patch("app.services.transcription.transcribe_audio") as mock_trans:
            mock_trans.return_value = (
                [{"text": "test", "start": 0.0, "end": 1.0}],
                "test"
            )
            with patch("os.path.exists", return_value=True):
                with patch("os.remove"):
                    segments, text = transcribe(str(video_file), "video")

    mock_extract.assert_called_once_with(str(video_file))
    assert text == "test"


def test_timestamp_precision(tmp_path):
    from app.services.transcription import transcribe_audio

    mock_model = MagicMock()
    mock_model.transcribe.return_value = {
        "segments": [
            {"text": "Hello", "start": 1.23456789, "end": 3.98765432},
        ],
        "text": "Hello",
    }

    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"fake")

    with patch("app.services.transcription._whisper_model", mock_model):
        with patch("app.services.transcription.get_whisper_model", return_value=mock_model):
            segments, _ = transcribe_audio(str(audio_file))

    assert segments[0]["start"] == round(1.23456789, 2)
    assert segments[0]["end"] == round(3.98765432, 2)


def test_extract_audio_ffmpeg_not_found():
    from app.services.transcription import extract_audio_from_video

    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(RuntimeError, match="ffmpeg not found"):
            extract_audio_from_video("/fake/video.mp4")


def test_probe_audio_duration_success():
    from app.services.transcription import probe_audio_duration
    import json

    mock_output = json.dumps({"format": {"duration": "102.5"}})

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=mock_output)
        duration = probe_audio_duration("/fake/audio.mp3")

    assert duration == 102.5


def test_probe_audio_duration_failure():
    from app.services.transcription import probe_audio_duration

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        duration = probe_audio_duration("/fake/audio.mp3")

    assert duration is None