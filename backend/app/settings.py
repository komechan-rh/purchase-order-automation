from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "purchase-orderautomation-backend"
    backend_api_key: str = ""
    automation_target_url: str = "https://example.com"
    google_sheet_id: str = ""
    google_sheet_range: str = "catalog!A:B"
    google_sheets_api_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"


settings = Settings()
