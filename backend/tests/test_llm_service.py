# backend/tests/test_llm_service.py

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.llm_service import (
    format_timestamp,
    build_context_string,
    build_messages,
    extract_timestamps_from_chunks,
    RateLimitError,
)


# ── format_timestamp ──────────────────────────────────────────────────────────

def test_format_timestamp():
    assert format_timestamp(0)     == "00:00"
    assert format_timestamp(60)    == "01:00"
    assert format_timestamp(90)    == "01:30"
    assert format_timestamp(3661)  == "61:01"
    assert format_timestamp(150.7) == "02:30"

def test_format_timestamp_none():
    assert format_timestamp(None) == ""


# ── build_context_string ──────────────────────────────────────────────────────

def test_build_context_with_timestamps():
    chunks = [
        {"text": "Machine learning.", "start_time": 120.0, "end_time": 125.0, "page_num": None},
        {"text": "Python is used.",   "start_time": 200.0, "end_time": 205.0, "page_num": None},
    ]
    ctx = build_context_string(chunks)
    assert "[02:00 - 02:05]" in ctx
    assert "[03:20 - 03:25]" in ctx
    assert "Machine learning" in ctx

def test_build_context_with_page_numbers():
    chunks = [{"text": "Introduction.", "start_time": None, "end_time": None, "page_num": 3}]
    ctx = build_context_string(chunks)
    assert "Page 3" in ctx
    assert "Introduction" in ctx

def test_build_context_empty():
    assert "No relevant context" in build_context_string([])

def test_build_context_no_timestamps_no_page():
    chunks = [{"text": "plain text", "start_time": None, "end_time": None, "page_num": None}]
    ctx = build_context_string(chunks)
    assert "plain text" in ctx
    assert "Excerpt 1" in ctx

def test_build_context_multiple_chunks():
    chunks = [
        {"text": f"chunk {i}", "start_time": float(i*10),
         "end_time": float(i*10+5), "page_num": None}
        for i in range(3)
    ]
    ctx = build_context_string(chunks)
    assert "Excerpt 1" in ctx
    assert "Excerpt 2" in ctx
    assert "Excerpt 3" in ctx


# ── build_messages ────────────────────────────────────────────────────────────

def test_build_messages_structure():
    ctx = build_context_string([{"text": "test", "start_time": None,
                                  "end_time": None, "page_num": 1}])
    msgs = build_messages("What is this?", ctx)
    assert len(msgs) >= 2
    assert msgs[0]["role"] == "system"
    assert msgs[-1]["role"] == "user"
    assert "What is this?" in msgs[-1]["content"]

def test_build_messages_with_history():
    history = [
        {"role": "user",      "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"},
    ]
    msgs = build_messages("New question", "context", history)
    assert any(m["content"] == "Previous question" for m in msgs)
    assert any(m["content"] == "Previous answer"   for m in msgs)

def test_build_messages_history_limit():
    history = [{"role": "user", "content": f"q{i}"} for i in range(20)]
    msgs = build_messages("latest", "ctx", history, max_history=6)
    user_msgs = [m for m in msgs
                 if m["role"] == "user" and m["content"].startswith("q")]
    assert len(user_msgs) <= 6

def test_build_messages_no_history():
    msgs = build_messages("query", "context", None)
    assert len(msgs) == 2


# ── extract_timestamps_from_chunks ────────────────────────────────────────────

def test_extract_timestamps():
    chunks = [
        {"text": "Hello", "start_time": 0.0,  "end_time": 5.0,  "chunk_index": 0},
        {"text": "World", "start_time": None,  "end_time": None,  "chunk_index": 1},
        {"text": "More",  "start_time": 10.0, "end_time": 15.0, "chunk_index": 2},
    ]
    ts = extract_timestamps_from_chunks(chunks)
    assert len(ts) == 2
    assert ts[0]["start"] == 0.0
    assert ts[1]["start"] == 10.0

def test_extract_timestamps_empty():
    assert extract_timestamps_from_chunks([]) == []

def test_extract_timestamps_none_start():
    chunks = [{"text": "no time", "start_time": None, "end_time": None}]
    assert extract_timestamps_from_chunks(chunks) == []

def test_extract_timestamps_max_3():
    chunks = [
        {"text": f"chunk {i}", "start_time": float(i*10),
         "end_time": float(i*10+5), "score": 1.0}
        for i in range(10)
    ]
    assert len(extract_timestamps_from_chunks(chunks)) <= 3

def test_extract_timestamps_text_truncation():
    long_text = "word " * 200
    chunks = [{"text": long_text, "start_time": 0.0, "end_time": 5.0, "score": 1.0}]
    ts = extract_timestamps_from_chunks(chunks)
    assert ts[0]["text"].endswith("...")
    assert len(ts[0]["text"]) <= 103

def test_extract_timestamps_deduplication():
    chunks = [
        {"text": "chunk 1", "start_time": 0.0,  "end_time": 5.0,  "score": 0.9},
        {"text": "chunk 2", "start_time": 0.0,  "end_time": 5.0,  "score": 0.8},
        {"text": "chunk 3", "start_time": 30.0, "end_time": 40.0, "score": 0.7},
    ]
    result = extract_timestamps_from_chunks(chunks)
    starts = [r["start"] for r in result]
    assert starts.count(0.0) == 1
    assert 30.0 in starts

def test_extract_timestamps_sorted_by_time():
    chunks = [
        {"text": "late",  "start_time": 50.0, "end_time": 60.0, "score": 0.9},
        {"text": "early", "start_time": 10.0, "end_time": 20.0, "score": 0.8},
    ]
    ts = extract_timestamps_from_chunks(chunks)
    assert ts[0]["start"] < ts[1]["start"]


# ── stream_with_groq ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stream_with_groq_rate_limit():
    from app.services.llm_service import stream_with_groq, RateLimitError
    with patch("groq.AsyncGroq") as MockGroq:
        mock_client = AsyncMock()
        MockGroq.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("rate_limit exceeded")
        with pytest.raises(RateLimitError):
            async for _ in stream_with_groq([{"role": "user", "content": "hi"}]):
                pass

@pytest.mark.asyncio
async def test_stream_with_groq_decommissioned():
    from app.services.llm_service import stream_with_groq, RateLimitError
    with patch("groq.AsyncGroq") as MockGroq:
        mock_client = AsyncMock()
        MockGroq.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("model_decommissioned")
        with pytest.raises(RateLimitError):
            async for _ in stream_with_groq([{"role": "user", "content": "hi"}]):
                pass

@pytest.mark.asyncio
async def test_stream_with_groq_other_error():
    from app.services.llm_service import stream_with_groq
    with patch("groq.AsyncGroq") as MockGroq:
        mock_client = AsyncMock()
        MockGroq.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("network error")
        with pytest.raises(Exception, match="network error"):
            async for _ in stream_with_groq([{"role": "user", "content": "hi"}]):
                pass


# ── stream_answer ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stream_answer_groq_success():
    from app.services.llm_service import stream_answer
    chunks = [{"text": "content", "start_time": None, "end_time": None, "page_num": 1}]

    async def mock_groq(messages):
        for t in ["Hello ", "world!"]:
            yield t

    with patch("app.services.llm_service.stream_with_groq", side_effect=mock_groq):
        tokens = []
        async for token in stream_answer("Test query", chunks):
            tokens.append(token)
    assert tokens == ["Hello ", "world!"]

@pytest.mark.asyncio
async def test_stream_answer_falls_back_to_ollama():
    from app.services.llm_service import stream_answer, RateLimitError
    chunks = [{"text": "content", "start_time": None, "end_time": None, "page_num": 1}]

    async def mock_groq_fail(messages):
        raise RateLimitError("rate limit")
        yield

    async def mock_ollama(messages):
        yield "Ollama response"

    with patch("app.services.llm_service.stream_with_groq", side_effect=mock_groq_fail):
        with patch("app.services.llm_service.stream_with_ollama", side_effect=mock_ollama):
            tokens = []
            async for token in stream_answer("Test", chunks):
                tokens.append(token)
    assert "Ollama response" in tokens

@pytest.mark.asyncio
async def test_stream_answer_groq_exception_tries_ollama():
    from app.services.llm_service import stream_answer
    chunks = [{"text": "content", "start_time": None, "end_time": None}]

    async def mock_groq_exc(messages):
        raise Exception("network error")
        yield

    async def mock_ollama(messages):
        yield "fallback"

    with patch("app.services.llm_service.stream_with_groq", side_effect=mock_groq_exc):
        with patch("app.services.llm_service.stream_with_ollama", side_effect=mock_ollama):
            tokens = []
            async for token in stream_answer("Test", chunks):
                tokens.append(token)
    assert "fallback" in tokens

@pytest.mark.asyncio
async def test_stream_answer_no_groq_key():
    from app.services.llm_service import stream_answer
    chunks = [{"text": "content", "start_time": None, "end_time": None}]

    async def mock_ollama(messages):
        yield "Ollama only"

    with patch("app.services.llm_service.settings") as mock_s:
        mock_s.groq_api_key = ""
        mock_s.ollama_base_url = "http://localhost:11434"
        mock_s.ollama_model = "llama3"
        with patch("app.services.llm_service.stream_with_ollama", side_effect=mock_ollama):
            tokens = []
            async for token in stream_answer("Test", chunks):
                tokens.append(token)
    assert "Ollama only" in tokens

@pytest.mark.asyncio
async def test_stream_answer_all_fail():
    from app.services.llm_service import stream_answer, RateLimitError
    chunks = [{"text": "content", "start_time": None, "end_time": None}]

    async def mock_groq_fail(messages):
        raise RateLimitError("rate limit")
        yield

    async def mock_ollama_fail(messages):
        raise RuntimeError("Ollama unavailable")
        yield

    with patch("app.services.llm_service.stream_with_groq", side_effect=mock_groq_fail):
        with patch("app.services.llm_service.stream_with_ollama", side_effect=mock_ollama_fail):
            with pytest.raises(RuntimeError):
                async for _ in stream_answer("Test", chunks):
                    pass


# ── generate_summary ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_summary_groq():
    from app.services.llm_service import generate_summary

    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({
        "summary": "Test summary",
        "key_topics": ["topic1", "topic2"],
    })

    with patch("groq.AsyncGroq") as MockGroq:
        mock_client = AsyncMock()
        MockGroq.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        result = await generate_summary("Some text content", "audio")

    assert result["summary"] == "Test summary"
    assert "topic1" in result["key_topics"]

@pytest.mark.asyncio
async def test_generate_summary_json_in_code_block():
    from app.services.llm_service import generate_summary

    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        "```json\n"
        + json.dumps({"summary": "Summary text", "key_topics": ["a", "b"]})
        + "\n```"
    )

    with patch("groq.AsyncGroq") as MockGroq:
        mock_client = AsyncMock()
        MockGroq.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        result = await generate_summary("text")

    assert result["summary"] == "Summary text"

@pytest.mark.asyncio
async def test_generate_summary_json_in_plain_code_block():
    from app.services.llm_service import generate_summary

    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        "```\n"
        + json.dumps({"summary": "Plain block", "key_topics": ["x"]})
        + "\n```"
    )

    with patch("groq.AsyncGroq") as MockGroq:
        mock_client = AsyncMock()
        MockGroq.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        result = await generate_summary("text")

    assert result["summary"] == "Plain block"

@pytest.mark.asyncio
async def test_generate_summary_invalid_json_fallback():
    from app.services.llm_service import generate_summary

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "This is not JSON at all"

    with patch("groq.AsyncGroq") as MockGroq:
        mock_client = AsyncMock()
        MockGroq.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        result = await generate_summary("text")

    assert result["summary"] == "This is not JSON at all"
    assert result["key_topics"] == []


@pytest.mark.asyncio
async def test_generate_summary_groq_fails_ollama_fallback():
    from app.services.llm_service import generate_summary

    ollama_response = json.dumps({
        "summary": "Ollama summary",
        "key_topics": ["ollama topic"],
    })

    with patch("groq.AsyncGroq") as MockGroq:
        mock_client = AsyncMock()
        MockGroq.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Groq failed")

        with patch("app.services.llm_service.settings") as mock_s:
            mock_s.groq_api_key = "test-key"
            mock_s.ollama_base_url = "http://localhost:11434"
            mock_s.ollama_model = "llama3"

            mock_ollama_resp = AsyncMock()
            mock_ollama_resp.json = MagicMock(return_value={
                "message": {"content": ollama_response}
            })

            with patch("httpx.AsyncClient") as MockHTTP:
                http_instance = AsyncMock()
                MockHTTP.return_value.__aenter__ = AsyncMock(return_value=http_instance)
                MockHTTP.return_value.__aexit__ = AsyncMock(return_value=None)
                http_instance.post = AsyncMock(return_value=mock_ollama_resp)

                result = await generate_summary("text", "audio")

    assert result["summary"] == "Ollama summary"

@pytest.mark.asyncio
async def test_generate_summary_both_fail():
    from app.services.llm_service import generate_summary

    with patch("groq.AsyncGroq") as MockGroq:
        mock_client = AsyncMock()
        MockGroq.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Groq failed")

        with patch("httpx.AsyncClient") as MockHTTP:
            http_instance = AsyncMock()
            MockHTTP.return_value.__aenter__ = AsyncMock(return_value=http_instance)
            MockHTTP.return_value.__aexit__ = AsyncMock(return_value=None)
            http_instance.post.side_effect = Exception("Ollama failed")

            result = await generate_summary("text")

    assert result["summary"] == "Summary generation failed."
    assert result["key_topics"] == []


# ── stream_with_ollama ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stream_with_ollama_success():
    from app.services.llm_service import stream_with_ollama

    lines = [
        json.dumps({"message": {"content": "hello"}, "done": False}),
        json.dumps({"message": {"content": " world"}, "done": True}),
    ]

    async def fake_aiter():
        for line in lines:
            yield line

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.aiter_lines = fake_aiter
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        tokens = []
        async for token in stream_with_ollama([{"role": "user", "content": "hi"}]):
            tokens.append(token)

    assert "hello" in tokens
    assert " world" in tokens

@pytest.mark.asyncio
async def test_stream_with_ollama_error():
    from app.services.llm_service import stream_with_ollama

    with patch("httpx.AsyncClient") as MockHTTP:
        instance = AsyncMock()
        MockHTTP.return_value.__aenter__ = AsyncMock(return_value=instance)
        MockHTTP.return_value.__aexit__ = AsyncMock(return_value=None)
        instance.stream.side_effect = Exception("connection refused")

        with pytest.raises(RuntimeError, match="Ollama unavailable"):
            async for _ in stream_with_ollama([{"role": "user", "content": "hi"}]):
                pass

@pytest.mark.asyncio
async def test_stream_with_ollama_skips_malformed_json():
    from app.services.llm_service import stream_with_ollama

    lines = [
        "not json at all",
        json.dumps({"message": {"content": "valid"}, "done": True}),
    ]

    async def fake_aiter():
        for line in lines:
            yield line

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.aiter_lines = fake_aiter
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=None)

    mock_client = MagicMock()
    mock_client.stream = MagicMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        tokens = []
        async for token in stream_with_ollama([{"role": "user", "content": "hi"}]):
            tokens.append(token)

    assert "valid" in tokens