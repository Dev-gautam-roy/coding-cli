"""Model client for calling NVIDIA Nemotron via Nebius Token Factory."""

from openai import OpenAI
from .config import Settings

def ask_model(
    settings: Settings,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    timeout: float = 45.0,
) -> str:
    """Call NVIDIA Nemotron model hosted on Nebius Token Factory via OpenAI-compatible API."""
    client = OpenAI(
        base_url=settings.base_url,
        api_key=settings.api_key,
        timeout=timeout,
        max_retries=1,
    )

    try:
        response = client.chat.completions.create(
            model=settings.model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as exc:
        raise RuntimeError(f"Nebius Token Factory inference call failed: {exc}") from exc

    if not response.choices or not response.choices[0].message:
        raise RuntimeError("Nebius Token Factory returned an empty response.")

    content = response.choices[0].message.content
    if not content or not content.strip():
        raise RuntimeError("Nebius Token Factory returned empty message content.")

    return content
