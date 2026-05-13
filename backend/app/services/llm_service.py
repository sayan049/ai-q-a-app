# backend/app/services/llm_service.py

import logging
import json
from typing import List, Dict, AsyncGenerator, Optional
from app.config import settings

logger = logging.getLogger(__name__)

GROQ_MODEL = "llama-3.3-70b-versatile"


# ── Exceptions ────────────────────────────────────────────────────────────────

class RateLimitError(Exception):
    pass


# ── System Prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an intelligent document and media assistant.

Answer questions ONLY based on the provided context from the uploaded file.
If the context contains timestamps (in seconds), reference them in your answer using [MM:SS] format.
If you cannot find the answer in the context, say clearly: "I couldn't find information about this in the uploaded content."

Formatting rules:
- Use markdown formatting (bold, bullets, headers where appropriate)
- For audio/video timestamps, cite as [MM:SS] — example: [02:34]
- For PDF references, cite page numbers — example: (Page 3)
- Keep answers concise but complete
- Do not make up information not present in the context
"""


# ── Helper Functions ──────────────────────────────────────────────────────────

def format_timestamp(seconds: float) -> str:
    if seconds is None:
        return ""
    total_seconds = int(seconds)
    minutes = total_seconds // 60
    secs = total_seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def build_context_string(chunks: List[Dict]) -> str:
    if not chunks:
        return "No relevant context found."

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        text      = chunk.get("text", "")
        start_time = chunk.get("start_time")
        end_time   = chunk.get("end_time")
        page_num   = chunk.get("page_num")

        if start_time is not None and end_time is not None:
            ts = f"[{format_timestamp(start_time)} - {format_timestamp(end_time)}]"
            context_parts.append(f"**Excerpt {i}** {ts}:\n{text}")
        elif page_num is not None:
            context_parts.append(f"**Excerpt {i}** (Page {page_num}):\n{text}")
        else:
            context_parts.append(f"**Excerpt {i}**:\n{text}")

    return "\n\n---\n\n".join(context_parts)


def build_messages(
    query: str,
    context: str,
    chat_history: Optional[List[Dict]] = None,
    max_history: int = 6,
) -> List[Dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if chat_history:
        for msg in chat_history[-max_history:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({
        "role": "user",
        "content": f"Context from the uploaded file:\n---\n{context}\n---\n\nUser Question: {query}",
    })
    return messages


def extract_timestamps_from_chunks(chunks: List[Dict]) -> List[Dict]:
    """
    Extract unique timestamps from retrieved chunks.
    Shows only top 3 unique non-overlapping timestamps.
    """
    timestamps = []
    seen_starts = set()

    # Sort by score if available, else keep original order
    sorted_chunks = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)

    for chunk in sorted_chunks:
        start = chunk.get("start_time")
        end   = chunk.get("end_time")

        if start is None:
            continue

        # Round to 1 decimal to catch near-duplicate timestamps
        rounded_start = round(start, 1)
        if rounded_start in seen_starts:
            continue
        seen_starts.add(rounded_start)

        text = chunk["text"]
        timestamps.append({
            "start": start,
            "end":   end if end is not None else start,
            "text":  text[:100] + "..." if len(text) > 100 else text,
        })

        if len(timestamps) >= 3:
            break

    # Sort final timestamps by time order (earliest first)
    timestamps.sort(key=lambda x: x["start"])

    return timestamps


# ── Groq Provider ─────────────────────────────────────────────────────────────

async def stream_with_groq(messages: List[Dict]) -> AsyncGenerator[str, None]:
    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=settings.groq_api_key)

        stream = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            stream=True,
            max_tokens=1024,
            temperature=0.3,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    except Exception as e:
        error_msg = str(e).lower()
        if any(k in error_msg for k in ["rate_limit", "429", "decommissioned", "model_decommissioned", "400"]):
            logger.warning(f"Groq unavailable ({e}), falling back to Ollama")
            raise RateLimitError(str(e))
        logger.error(f"Groq API error: {e}")
        raise


# ── Ollama Provider ───────────────────────────────────────────────────────────

async def stream_with_ollama(messages: List[Dict]) -> AsyncGenerator[str, None]:
    try:
        import httpx
        url = f"{settings.ollama_base_url}/api/chat"
        payload = {
            "model": settings.ollama_model,
            "messages": messages,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield content
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        logger.error(f"Ollama API error: {e}")
        raise RuntimeError(f"Ollama unavailable: {str(e)}")


# ── Main Stream Function ───────────────────────────────────────────────────────

async def stream_answer(
    query: str,
    context_chunks: List[Dict],
    chat_history: Optional[List[Dict]] = None,
) -> AsyncGenerator[str, None]:
    context  = build_context_string(context_chunks)
    messages = build_messages(query, context, chat_history)

    # Try Groq first
    if settings.groq_api_key:
        try:
            async for token in stream_with_groq(messages):
                yield token
            return
        except RateLimitError:
            logger.info("Falling back to Ollama")
        except Exception as e:
            logger.error(f"Groq failed: {e}, trying Ollama")

    # Fallback to Ollama
    try:
        async for token in stream_with_ollama(messages):
            yield token
    except Exception as e:
        logger.error(f"All LLM services failed: {e}")
        raise RuntimeError(f"LLM service unavailable: {str(e)}")


# ── Summary Generation ────────────────────────────────────────────────────────

async def generate_summary(text: str, file_type: str = "document") -> Dict:
    prompt = f"""Please provide a comprehensive summary of this {file_type} content.

Content:
---
{text[:6000]}
---

Provide:
1. A 2-3 paragraph summary
2. 5-8 key topics covered (as a bullet list)

Format your response as JSON:
{{
    "summary": "...",
    "key_topics": ["topic1", "topic2", ...]
}}"""

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that summarizes documents. Always respond with valid JSON.",
        },
        {"role": "user", "content": prompt},
    ]

    full_response = ""

    # Try Groq first
    if settings.groq_api_key:
        try:
            from groq import AsyncGroq
            client = AsyncGroq(api_key=settings.groq_api_key)
            response = await client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                stream=False,
                max_tokens=1024,
                temperature=0.3,
            )
            full_response = response.choices[0].message.content or ""
            logger.info("Summary generated with Groq")
        except Exception as e:
            logger.error(f"Groq summary failed: {e}")
            full_response = ""

    # Fallback to Ollama
    if not full_response:
        try:
            import httpx
            url = f"{settings.ollama_base_url}/api/chat"
            payload = {
                "model": settings.ollama_model,
                "messages": messages,
                "stream": False,
            }
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(url, json=payload)
                data = response.json()
                full_response = data.get("message", {}).get("content", "")
                logger.info("Summary generated with Ollama")
        except Exception as e:
            logger.error(f"Ollama summary failed: {e}")
            return {"summary": "Summary generation failed.", "key_topics": []}

    # Parse JSON response
    try:
        if "```json" in full_response:
            full_response = full_response.split("```json")[1].split("```")[0].strip()
        elif "```" in full_response:
            full_response = full_response.split("```")[1].split("```")[0].strip()

        parsed = json.loads(full_response)
        return {
            "summary": parsed.get("summary", ""),
            "key_topics": parsed.get("key_topics", []),
        }
    except json.JSONDecodeError:
        return {"summary": full_response, "key_topics": []}