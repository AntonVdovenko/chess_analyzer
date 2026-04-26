"""Configuration settings for Chess Analyzer."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DATABASE_URL: str = "postgresql://user:password@localhost:5432/chess_analyzer"
    STOCKFISH_PATH: str = "/usr/games/stockfish"
    CHESS_COM_API_BASE: str = "https://api.chess.com/pub"
    DEBUG: bool = False
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
