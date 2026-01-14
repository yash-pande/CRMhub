from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Default to sqlite, but easy to override with env var DATABASE_URL
    DATABASE_URL: str
    SECRET_KEY: str
    
    # JWT
    ALGORITHM: str 
    ACCESS_TOKEN_EXPIRE_MINUTES: int
     
    # Good practice: App metadata in config
    APP_TITLE: str = "Resume CRM"
    APP_VERSION: str = "0.1.0"

    class Config:
        env_file = ".env"

settings = Settings()

