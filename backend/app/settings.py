from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "purchase-orderautomation-backend"
    backend_api_key: str = ""
    automation_target_url: str = "https://example.com"
    amazon_email: str = ""
    amazon_password: str = ""
    amazon_headless: bool = True
    amazon_screenshot_enabled: bool = True
    amazon_screenshot_dir: str = "artifacts/screenshots"


settings = Settings()
