import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class AppSettings(BaseModel):
    # MongoDB
    mongodb_url: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name: str = os.getenv("DATABASE_NAME", "forgeroom")
    
    # JWT Auth
    jwt_secret_key: str = os.getenv(
        "JWT_SECRET_KEY", "9a7c36a4eb8b80b06b9cb8b9c2409f90eb7c36a4eb8b80b06b9cb8b9c2409f90"
    )
    jwt_refresh_secret_key: str = os.getenv(
        "JWT_REFRESH_SECRET_KEY", "e87c36a4eb8b80b06b9cb8b9c2409f90eb7c36a4eb8b80b06b9cb8b9c2409f90"
    )
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # NVIDIA API
    nvidia_api_key: str = os.getenv("NVIDIA_API_KEY", "")
    nvidia_api_url: str = os.getenv("NVIDIA_API_URL", "https://integrate.api.nvidia.com/v1")
    nvidia_model_name: str = os.getenv("NVIDIA_MODEL_NAME", "meta/llama-3.1-70b-instruct")
    
    # Tavily API
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")

settings = AppSettings()
