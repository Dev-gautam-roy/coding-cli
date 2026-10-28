"""Model client for calling NVIDIA Nemotron or any OpenAI-compatible provider."""

from openai import OpenAI
from .config import Settings

def ask_model(
    settings: Settings,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    timeout: float = 45.0,
) -> str:
    """Call LLM hosted on Nebius Token Factory, NVIDIA NIM, OpenAI, Groq, or any compatible endpoint."""
    client = OpenAI(
        base_url=settings.base_url,
        api_key=settings.api_key,
        timeout=timeout,
        max_retries=1,
    )

    provider_label = settings.provider or "API Provider"

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
        raise RuntimeError(f"{provider_label} inference call failed: {exc}") from exc

    if not response.choices or not response.choices[0].message:
        raise RuntimeError(f"{provider_label} returned an empty response.")

    content = response.choices[0].message.content
    if not content or not content.strip():
        raise RuntimeError(f"{provider_label} returned empty message content.")

    return content
