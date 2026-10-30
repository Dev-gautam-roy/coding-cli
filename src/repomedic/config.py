from dataclasses import dataclass
import os
from pathlib import Path
from dotenv import load_dotenv

@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str
    provider: str = "OpenAI-Compatible"

    def masked_api_key(self) -> str:
        if not self.api_key:
            return "<not-set>"
        if len(self.api_key) <= 8:
            return "***"
        return f"{self.api_key[:4]}...{self.api_key[-4:]}"

# Provider preset defaults: (api_key_env, base_url_env, model_env, default_base_url, default_model, provider_name)
PROVIDER_PRESETS = [
    ("NEBIUS_API_KEY", "NEBIUS_BASE_URL", "NEBIUS_MODEL", "https://api.tokenfactory.us-central1.nebius.com/v1/", "nvidia/Nemotron-3_5-Lightning", "Nebius Token Factory"),
    ("NVIDIA_API_KEY", "NVIDIA_BASE_URL", "NVIDIA_MODEL", "https://integrate.api.nvidia.com/v1/", "nvidia/llama-3.1-nemotron-70b-instruct", "NVIDIA NIM"),
    ("NVAPI_KEY", "NVIDIA_BASE_URL", "NVIDIA_MODEL", "https://integrate.api.nvidia.com/v1/", "nvidia/llama-3.1-nemotron-70b-instruct", "NVIDIA NIM"),
    ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL", "https://api.openai.com/v1/", "gpt-4o-mini", "OpenAI"),
    ("GROQ_API_KEY", "GROQ_BASE_URL", "GROQ_MODEL", "https://api.groq.com/openai/v1/", "llama-3.3-70b-versatile", "Groq"),
    ("OPENROUTER_API_KEY", "OPENROUTER_BASE_URL", "OPENROUTER_MODEL", "https://openrouter.ai/api/v1/", "nvidia/llama-3.1-nemotron-70b-instruct", "OpenRouter"),
    ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL", "https://api.deepseek.com/v1/", "deepseek-chat", "DeepSeek"),
    ("GEMINI_API_KEY", "GEMINI_BASE_URL", "GEMINI_MODEL", "https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-1.5-flash", "Google Gemini"),
]

def load_settings(env_file: Path | None = None) -> Settings:
    """
    Load configuration from environment or .env file.
    Supports any OpenAI-compatible provider (Nebius, NVIDIA NIM, OpenAI, Groq, OpenRouter, DeepSeek, etc.)
    """
    if env_file and env_file.is_file():
        load_dotenv(dotenv_path=env_file)
    else:
        load_dotenv()

    # Universal override keys
    generic_base_url = os.getenv("LLM_BASE_URL") or os.getenv("BASE_URL")
    generic_model = os.getenv("LLM_MODEL") or os.getenv("MODEL")
    generic_key = os.getenv("LLM_API_KEY") or os.getenv("REPOMEDIC_API_KEY") or os.getenv("API_KEY")

    chosen_key = ""
    chosen_base_url = ""
    chosen_model = ""
    provider_name = "Custom / OpenAI-Compatible"

    # Match active provider by checking non-empty API keys
    for key_env, url_env, model_env, preset_url, preset_model, name in PROVIDER_PRESETS:
        val = os.getenv(key_env, "").strip()
        if val:
            chosen_key = val
            provider_url_override = os.getenv(url_env, "").strip()
            provider_model_override = os.getenv(model_env, "").strip()
            chosen_base_url = provider_url_override or preset_url
            chosen_model = provider_model_override or preset_model
            provider_name = name
            break

    # If generic key was supplied instead
    if not chosen_key and generic_key:
        chosen_key = generic_key.strip()
        if chosen_key.startswith("nvapi-"):
            chosen_base_url = "https://integrate.api.nvidia.com/v1/"
            chosen_model = "nvidia/llama-3.1-nemotron-70b-instruct"
            provider_name = "NVIDIA NIM"
        elif chosen_key.startswith("gsk_"):
            chosen_base_url = "https://api.groq.com/openai/v1/"
            chosen_model = "llama-3.3-70b-versatile"
            provider_name = "Groq"
        elif chosen_key.startswith("sk-or-"):
            chosen_base_url = "https://openrouter.ai/api/v1/"
            chosen_model = "nvidia/llama-3.1-nemotron-70b-instruct"
            provider_name = "OpenRouter"
        elif chosen_key.startswith("sk-"):
            chosen_base_url = "https://api.openai.com/v1/"
            chosen_model = "gpt-4o-mini"
            provider_name = "OpenAI"
        else:
            chosen_base_url = "https://api.tokenfactory.us-central1.nebius.com/v1/"
            chosen_model = "nvidia/Nemotron-3_5-Lightning"
            provider_name = "Custom Provider"

    if not chosen_key:
        raise RuntimeError(
            "No API key found. Set NEBIUS_API_KEY, NVIDIA_API_KEY, OPENAI_API_KEY, "
            "GROQ_API_KEY, or LLM_API_KEY in your local environment or .env file."
        )

    # Let generic overrides take final precedence if defined
    final_base_url = (generic_base_url or chosen_base_url).strip().rstrip("/") + "/"
    final_model = (generic_model or chosen_model).strip()

    return Settings(
        api_key=chosen_key,
        base_url=final_base_url,
        model=final_model,
        provider=provider_name,
    )
