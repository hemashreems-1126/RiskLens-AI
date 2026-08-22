"""
Thin wrapper around Groq's chat-completions endpoint (OpenAI-compatible
schema, served at GROQ_BASE_URL). This is the ONLY LLM integration point
in the whole project.

MOCK MODE: if no GROQ_API_KEY is configured (or FORCE_MOCK_LLM=true),
calls fall back to a deterministic, clearly-labelled mock responder so
the rest of the pipeline (agents, graph, UI, evaluation) stays fully
demoable without a live key or network access. Every mock response is
tagged so it is never confused with a real Groq output in the UI or
audit trail.
"""
from __future__ import annotations
import json
import httpx

from app.config.settings import get_settings

settings = get_settings()


class GroqUnavailableError(RuntimeError):
    pass


def _mock_complete(system_prompt: str, user_prompt: str) -> str:
    """Deterministic, template-based stand-in for a Groq call. Not a real
    LLM output — used only when no GROQ_API_KEY is present so the system
    remains demoable. Keeps output plausible-shaped JSON when the prompt
    asks for JSON, based on simple keyword matching."""
    if "explain" in system_prompt.lower() or "explanation" in user_prompt.lower():
        return (
            "[MOCK MODE — no live Groq key configured] Based on the factual evidence "
            "gathered by the investigation agents, this transaction shows one or more "
            "anomaly signals (see evidence panel). Recommend following the deterministic "
            "risk decision shown above. This explanation is a offline placeholder, not a "
            "live Groq-generated explanation."
        )
    return json.dumps({
        "mock": True,
        "note": "GROQ_API_KEY not configured — returning a deterministic offline placeholder instead of a live reasoning trace.",
        "summary": "Evidence reviewed; see structured findings for details.",
    })


def chat_complete(system_prompt: str, user_prompt: str, json_mode: bool = False) -> tuple[str, str]:
    """Returns (content, mode) where mode is 'live' or 'mock'."""
    if settings.LLM_MOCK_MODE:
        return _mock_complete(system_prompt, user_prompt), "mock"

    try:
        payload = {
            "model": settings.GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{settings.GROQ_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"], "live"
    except Exception as exc:  # noqa: BLE001 — deliberate: any Groq failure must degrade gracefully
        # Failure-recovery path (see README "Failure Recovery"): fall back to
        # mock mode rather than crashing the investigation.
        fallback = _mock_complete(system_prompt, user_prompt)
        return (
            f"[GROQ UNAVAILABLE — AI reasoning fell back to offline mode. Error: {exc}] {fallback}",
            "mock",
        )
