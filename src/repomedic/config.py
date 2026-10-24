from dataclasses import dataclass
import os
from pathlib import Path
from dotenv import load_dotenv

@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str

    def masked_api_key(self) -> str:
        if not self.api_key:
            return "<not-set>"
        if len(self.api_key) <= 8:
            return "***"
        return f"{self.api_key[:4]}...{self.api_key[-4:]}"

def load_settings(env_file: Path | None = None) -> Settings:
    """Load configuration from environment or .env file."""
    if env_file and env_file.is_file():
        load_dotenv(dotenv_path=env_file)
    else:
        load_dotenv()

    key = os.getenv("NEBIUS_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "NEBIUS_API_KEY is missing. Set it in your local environment or .env file."
        )

    base_url = os.getenv(
        "NEBIUS_BASE_URL",
        "https://api.tokenfactory.us-central1.nebius.com/v1/",
    ).rstrip("/") + "/"

    model = os.getenv(
        "NEBIUS_MODEL", "nvidia/Nemotron-3_5-Lightning"
    ).strip()

    return Settings(
        api_key=key,
        base_url=base_url,
        model=model,
    )
