from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "purchase-orderautomation-backend"
    backend_api_key: str = Field(
        default="",
        description="API key for authenticating requests. Required for production.",
    )
    automation_target_url: str = "https://example.com"
    amazon_email: str = Field(
        default="",
        description="Amazon account email. Required for automation.",
    )
    amazon_password: str = Field(
        default="",
        description="Amazon account password. Required for automation.",
    )
    amazon_headless: bool = True
    amazon_screenshot_enabled: bool = True
    amazon_screenshot_dir: str = "artifacts/screenshots"

    @field_validator("backend_api_key", "amazon_email", "amazon_password", mode="before")
    @classmethod
    def validate_required_fields(cls, v: str, info) -> str:
        """Validate that critical settings are not empty at startup."""
        field_name = info.field_name
        if field_name in ("backend_api_key", "amazon_email", "amazon_password"):
            if isinstance(v, str) and not v.strip():
                raise ValueError(f"{field_name} must be set (got empty value)")
        return v


settings = Settings()
