import pytest
from repomedic.config import load_settings

def test_load_settings_nebius(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-nebius-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    settings = load_settings()
    assert settings.api_key == "test-nebius-key"
    assert "tokenfactory" in settings.base_url
    assert settings.provider == "Nebius Token Factory"
    assert settings.masked_api_key() == "test...-key"

def test_load_settings_nvidia_nim(monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-1234567890abcdef")

    settings = load_settings()
    assert settings.api_key == "nvapi-1234567890abcdef"
    assert "integrate.api.nvidia.com" in settings.base_url
    assert settings.provider == "NVIDIA NIM"
    assert "nemotron" in settings.model.lower()

def test_load_settings_openai(monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-1234567890abcdef")

    settings = load_settings()
    assert settings.api_key == "sk-proj-1234567890abcdef"
    assert "api.openai.com" in settings.base_url
    assert settings.provider == "OpenAI"

def test_load_settings_groq(monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk_1234567890abcdef")

    settings = load_settings()
    assert settings.api_key == "gsk_1234567890abcdef"
    assert "api.groq.com" in settings.base_url
    assert settings.provider == "Groq"

def test_load_settings_custom_generic(monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "custom-token")
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LLM_MODEL", "llama3.2")

    settings = load_settings()
    assert settings.api_key == "custom-token"
    assert settings.base_url == "http://localhost:11434/v1/"
    assert settings.model == "llama3.2"

def test_load_settings_missing_raises_error(monkeypatch):
    for key in ["NEBIUS_API_KEY", "NVIDIA_API_KEY", "NVAPI_KEY", "OPENAI_API_KEY", "GROQ_API_KEY", "LLM_API_KEY", "API_KEY"]:
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(RuntimeError, match="No API key found"):
        load_settings()
