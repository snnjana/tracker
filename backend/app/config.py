"""Application configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from backend directory
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    """Application settings from environment variables."""

    # AWS Configuration (still needed for CloudWatch)
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: str | None = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_SESSION_TOKEN: str | None = os.getenv("AWS_SESSION_TOKEN")

    # Groq Configuration
    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # GitHub Configuration
    GITHUB_TOKEN: str | None = os.getenv("GITHUB_TOKEN")

    @classmethod
    def get_boto3_kwargs(cls) -> dict:
        """Get kwargs for boto3 client/resource creation with region and credentials."""
        kwargs: dict = {"region_name": cls.AWS_REGION}

        if cls.AWS_ACCESS_KEY_ID and cls.AWS_SECRET_ACCESS_KEY:
            kwargs["aws_access_key_id"] = cls.AWS_ACCESS_KEY_ID
            kwargs["aws_secret_access_key"] = cls.AWS_SECRET_ACCESS_KEY
            if cls.AWS_SESSION_TOKEN:
                kwargs["aws_session_token"] = cls.AWS_SESSION_TOKEN

        return kwargs


settings = Settings()
