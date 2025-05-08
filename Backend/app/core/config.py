from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    MONGODB_URI: str = "mongodb+srv://user:password@cluster.mongodb.net/"
    SECRET_KEY: str = "tu_clave_secreta_aleatoria"  # ¡Cambia esto!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

settings = Settings()